"""
SecureIoT-X — MongoDB Core Connection and Operations Module.

MongoDB is the PRIMARY and ONLY application datastore for:
- users (authentication)
- devices
- telemetry
- attack_events
- predictions
- risk_scores
- isolation_events
- response_actions
- audit_logs
- blockchain_records
- threats
- system_logs
"""

import logging
import time
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database

from backend.core.config import settings

logger = logging.getLogger("secureiot.mongodb")

_async_client: Optional[AsyncIOMotorClient] = None
_sync_client: Optional[MongoClient] = None

# Default 10 simulation devices
DEFAULT_SIMULATION_DEVICES = [
    {"device_id": "ESP32_001", "device_type": "Temperature Sensor", "ip_address": "192.168.1.101", "mac_address": "AA:BB:CC:DD:01:01", "location": "Zone-A", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_002", "device_type": "Motion Sensor", "ip_address": "192.168.1.102", "mac_address": "AA:BB:CC:DD:01:02", "location": "Zone-A", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_003", "device_type": "Camera Gateway", "ip_address": "192.168.1.103", "mac_address": "AA:BB:CC:DD:01:03", "location": "Zone-B", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_004", "device_type": "Smart Lock", "ip_address": "192.168.1.104", "mac_address": "AA:BB:CC:DD:01:04", "location": "Zone-B", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_005", "device_type": "HVAC Controller", "ip_address": "192.168.1.105", "mac_address": "AA:BB:CC:DD:01:05", "location": "Zone-C", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_006", "device_type": "Light Controller", "ip_address": "192.168.1.106", "mac_address": "AA:BB:CC:DD:01:06", "location": "Zone-C", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_007", "device_type": "Air Quality Monitor", "ip_address": "192.168.1.107", "mac_address": "AA:BB:CC:DD:01:07", "location": "Zone-D", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_008", "device_type": "Water Meter", "ip_address": "192.168.1.108", "mac_address": "AA:BB:CC:DD:01:08", "location": "Zone-D", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_009", "device_type": "Power Monitor", "ip_address": "192.168.1.109", "mac_address": "AA:BB:CC:DD:01:09", "location": "Zone-E", "firmware_version": "1.0.0", "is_simulation": True},
    {"device_id": "ESP32_010", "device_type": "Industrial Pump Gateway", "ip_address": "192.168.1.110", "mac_address": "AA:BB:CC:DD:01:10", "location": "Zone-E", "firmware_version": "1.0.0", "is_simulation": True},
]


def get_db_name() -> str:
    uri = settings.mongodb_uri
    # extract database name from uri, default to secureiot_x
    if "/" in uri.split("://")[-1]:
        part = uri.split("://")[-1].split("/")[-1]
        db_name = part.split("?")[0]
        if db_name:
            return db_name
    return "secureiot_x"


def get_sync_mongodb() -> Database:
    """Get synchronous PyMongo Database handle."""
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    return _sync_client[get_db_name()]


def get_mongodb() -> AsyncIOMotorDatabase:
    """Get async Motor Database handle (FastAPI dependency)."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    return _async_client[get_db_name()]


async def init_mongodb() -> None:
    """Initialize MongoDB: verify connection, build indexes, seed simulation devices."""
    db = get_mongodb()
    try:
        await db.command("ping")
        logger.info("MongoDB connected successfully to %s", get_db_name())
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", e)
        raise

    # Create indexes
    try:
        await db.devices.create_index("device_id", unique=True)
        await db.telemetry.create_index([("device_id", 1), ("timestamp", -1)])
        await db.attack_events.create_index([("device_id", 1), ("timestamp", -1)])
        await db.predictions.create_index([("device_id", 1), ("timestamp", -1)])
        await db.risk_scores.create_index([("device_id", 1), ("timestamp", -1)])
        await db.isolation_events.create_index([("device_id", 1), ("timestamp", -1)])
        await db.response_actions.create_index([("device_id", 1), ("timestamp", -1)])
        await db.blockchain_records.create_index("tx_hash", unique=True, sparse=True)
        logger.info("MongoDB indexes verified.")
    except Exception as e:
        logger.warning("Error creating indexes in MongoDB: %s", e)

    # Seed default simulation devices if not already seeded
    now = time.time()
    for d in DEFAULT_SIMULATION_DEVICES:
        existing = await db.devices.find_one({"device_id": d["device_id"]})
        if not existing:
            doc = {
                **d,
                "is_simulation": True,
                "is_online": True,
                "is_isolated": False,
                "security_status": "NORMAL",
                "threat_count": 0,
                "total_events": 0,
                "first_seen": now,
                "last_seen": now,
                "uptime": 0.0,
            }
            await db.devices.insert_one(doc)
            logger.info("Seeded simulation device into MongoDB: %s", d["device_id"])
        else:
            # Ensure existing simulation device has is_simulation flag set
            if "is_simulation" not in existing:
                await db.devices.update_one(
                    {"device_id": d["device_id"]},
                    {"$set": {"is_simulation": True}}
                )

    logger.info("MongoDB initialization complete.")

    # Ensure default admin user exists in MongoDB `users` collection
    try:
        await db["users"].create_index("username", unique=True)
        existing_admin = await db["users"].find_one({"username": settings.default_admin_username})
        if not existing_admin:
            from backend.core.security import hash_password
            import datetime as _dt
            admin_doc = {
                "username": settings.default_admin_username,
                "email": settings.default_admin_email,
                "hashed_password": hash_password(settings.default_admin_password),
                "role": "ADMIN",
                "is_active": True,
                "created_at": _dt.datetime.now(_dt.timezone.utc),
                "last_login": None,
            }
            await db["users"].insert_one(admin_doc)
            logger.info("Default admin user created in MongoDB: %s", settings.default_admin_username)
        else:
            logger.info("Admin user already exists in MongoDB: %s", settings.default_admin_username)
    except Exception as e:
        logger.warning("Could not ensure admin user in MongoDB: %s", e)

    # Create indexes for migrated collections
    try:
        await db["threats"].create_index("threat_id", unique=True, sparse=True)
        await db["threats"].create_index([("created_at", -1)])
        await db["system_logs"].create_index([("timestamp", -1)])
        await db["audit_logs"].create_index([("timestamp", -1)])
    except Exception as e:
        logger.warning("Non-critical: could not create indexes for threats/logs: %s", e)

    logger.info("MongoDB fully initialized.")


async def close_mongodb() -> None:
    """Close MongoDB client connections."""
    global _async_client, _sync_client
    if _async_client:
        _async_client.close()
        _async_client = None
    if _sync_client:
        _sync_client.close()
        _sync_client = None
    logger.info("MongoDB connections closed.")


async def check_mongodb_health() -> Dict[str, Any]:
    """Check MongoDB health and statistics."""
    try:
        db = get_mongodb()
        res = await db.command("ping")
        device_count = await db.devices.count_documents({})
        attack_count = await db.attack_events.count_documents({})
        isolated_count = await db.devices.count_documents({"is_isolated": True})
        return {
            "status": "healthy" if res.get("ok") == 1.0 else "degraded",
            "database": get_db_name(),
            "connected": True,
            "device_count": device_count,
            "isolated_count": isolated_count,
            "attack_count": attack_count,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": get_db_name(),
            "connected": False,
            "error": str(e),
        }
