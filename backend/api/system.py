"""
System API — logs, audit trail, and settings.

ALL log and audit data stored in MongoDB `system_logs` and `audit_logs` collections.
SQLite is NO LONGER used for system data.
"""

from fastapi import APIRouter, Depends

from backend.core.mongodb import get_mongodb
from backend.core.security import get_current_user
from backend.core.websocket import ws_manager

router = APIRouter()


@router.get("/logs", summary="System Logs")
async def system_logs(limit: int = 100):
    """Return recent system logs from MongoDB."""
    db = get_mongodb()
    cursor = db["system_logs"].find({}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    result = []
    for log in logs:
        log.pop("_id", None)
        result.append({
            "id": str(log.get("_id", log.get("id", ""))),
            "level": log.get("level", "INFO"),
            "service": log.get("service", ""),
            "message": log.get("message", ""),
            "device_id": log.get("device_id"),
            "timestamp": log.get("timestamp"),
        })
    return result


@router.get("/audit", summary="Audit Trail")
async def audit_trail(limit: int = 100):
    """Return recent audit events from MongoDB."""
    db = get_mongodb()
    cursor = db["audit_logs"].find({}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    result = []
    for log in logs:
        log.pop("_id", None)
        result.append({
            "audit_id": log.get("audit_id", ""),
            "action": log.get("action", ""),
            "entity_type": log.get("entity_type", ""),
            "entity_id": log.get("entity_id", ""),
            "user_id": log.get("user_id", ""),
            "details": log.get("details", ""),
            "severity": log.get("severity", ""),
            "timestamp": log.get("timestamp"),
        })
    return result


@router.get("/settings", summary="System Settings")
async def system_settings(user=Depends(get_current_user)):
    from backend.core.config import settings
    return {
        "app_name": settings.app_name,
        "mode": settings.active_mode,
        "sdn_mode": settings.sdn_mode,
        "websocket_connections": ws_manager.connection_count,
        "debug": settings.debug,
        "telegram_configured": bool(settings.telegram_bot_token and settings.telegram_chat_id),
    }
