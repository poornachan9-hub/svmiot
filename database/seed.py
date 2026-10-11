"""
SecureIoT-X Demo Seed Data.

Populates the database with 10 virtual devices, historical events,
threats, responses, and sample blockchain records for demonstration.

All seeded data is clearly labelled as DEMO DATA.
"""

import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.core.database import get_sync_db, init_db_sync
from backend.core.security import hash_password

# Force model registration
import backend.models  # noqa: F401

from backend.models.user import User
from backend.models.device import Device
from backend.models.event import NetworkEvent
from backend.models.prediction import Prediction
from backend.models.threat import Threat
from backend.models.response import Response
from backend.models.audit import AuditLog, ModelRun

# Deterministic demo data
random.seed(42)
_now = datetime.now(timezone.utc)


# ── Demo Devices ───────────────────────────────────────────────

DEMO_DEVICES = [
    {"device_id": "ESP32_001", "name": "Living Room Sensor", "device_type": "sensor", "ip_address": "192.168.1.101", "mac_address": "AA:BB:CC:DD:EE:01", "criticality": 30},
    {"device_id": "ESP32_002", "name": "Kitchen Sensor", "device_type": "sensor", "ip_address": "192.168.1.102", "mac_address": "AA:BB:CC:DD:EE:02", "criticality": 30},
    {"device_id": "ESP32_003", "name": "Main Gateway", "device_type": "gateway", "ip_address": "192.168.1.1", "mac_address": "AA:BB:CC:DD:EE:03", "criticality": 90},
    {"device_id": "ESP32_004", "name": "Security Camera", "device_type": "camera", "ip_address": "192.168.1.104", "mac_address": "AA:BB:CC:DD:EE:04", "criticality": 70},
    {"device_id": "ESP32_005", "name": "Door Actuator", "device_type": "actuator", "ip_address": "192.168.1.105", "mac_address": "AA:BB:CC:DD:EE:05", "criticality": 60},
    {"device_id": "ESP32_006", "name": "Garage Sensor", "device_type": "sensor", "ip_address": "192.168.1.106", "mac_address": "AA:BB:CC:DD:EE:06", "criticality": 30},
    {"device_id": "ESP32_007", "name": "Server Room Monitor", "device_type": "sensor", "ip_address": "192.168.1.107", "mac_address": "AA:BB:CC:DD:EE:07", "criticality": 80},
    {"device_id": "ESP32_008", "name": "HVAC Controller", "device_type": "actuator", "ip_address": "192.168.1.108", "mac_address": "AA:BB:CC:DD:EE:08", "criticality": 50},
    {"device_id": "ESP32_009", "name": "Perimeter Sensor", "device_type": "sensor", "ip_address": "192.168.1.109", "mac_address": "AA:BB:CC:DD:EE:09", "criticality": 40},
    {"device_id": "ESP32_010", "name": "Smart Lock", "device_type": "actuator", "ip_address": "192.168.1.110", "mac_address": "AA:BB:CC:DD:EE:10", "criticality": 85},
]

ATTACK_TYPES = ["Normal", "DDoS", "DoS", "Reconnaissance", "Brute_Force", "Spoofing", "MITM"]
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _uid() -> str:
    return uuid.uuid4().hex[:16]


def seed_database() -> None:
    """Populate database with demo data."""
    print("=" * 60)
    print("SecureIoT-X Demo Data Seeding")
    print("=" * 60)
    print("NOTE: All data is labelled as DEMO DATA\n")

    init_db_sync()
    session = get_sync_db()

    try:
        # 1. Demo users
        print("[1/6] Seeding users...")
        _seed_users(session)

        # 2. Demo devices
        print("[2/6] Seeding devices...")
        _seed_devices(session)

        # 3. Demo events
        print("[3/6] Seeding network events...")
        _seed_events(session)

        # 4. Demo predictions
        print("[4/6] Seeding predictions...")
        _seed_predictions(session)

        # 5. Demo threats
        print("[5/6] Seeding threats...")
        _seed_threats(session)

        # 6. Demo audit logs
        print("[6/6] Seeding audit logs...")
        _seed_audit_logs(session)

        session.commit()
        print("\n✓ Demo data seeded successfully!")
    except Exception as e:
        session.rollback()
        print(f"\n✗ Seeding failed: {e}")
        raise
    finally:
        session.close()

    print("=" * 60)


def _seed_users(session) -> None:
    from sqlalchemy import select
    existing = session.execute(select(User).where(User.username == "analyst")).scalar_one_or_none()
    if existing:
        print("  ✓ Demo users already exist")
        return

    users = [
        User(username="analyst", email="analyst@secureiot.local",
             hashed_password=hash_password("Analyst2024!"), role="ANALYST", is_active=True),
        User(username="viewer", email="viewer@secureiot.local",
             hashed_password=hash_password("Viewer2024!"), role="VIEWER", is_active=True),
    ]
    session.add_all(users)
    print(f"  ✓ Created {len(users)} demo users")


def _seed_devices(session) -> None:
    from sqlalchemy import select
    existing = session.execute(select(Device).where(Device.device_id == "ESP32_001")).scalar_one_or_none()
    if existing:
        print("  ✓ Demo devices already exist")
        return

    devices = []
    for d in DEMO_DEVICES:
        dev = Device(
            device_id=d["device_id"],
            name=d["name"],
            device_type=d["device_type"],
            ip_address=d["ip_address"],
            mac_address=d["mac_address"],
            criticality=d["criticality"],
            firmware_version="1.0.0-demo",
            mqtt_connected=True,
            approved=True,
            security_status="NORMAL",
            temperature=round(random.uniform(20, 35), 1),
            humidity=round(random.uniform(40, 80), 1),
            motion=random.choice([True, False]),
            last_seen=_now - timedelta(minutes=random.randint(0, 30)),
        )
        devices.append(dev)
    session.add_all(devices)
    print(f"  ✓ Created {len(devices)} demo devices")


def _seed_events(session) -> None:
    events = []
    for i in range(50):
        dev = random.choice(DEMO_DEVICES)
        evt = NetworkEvent(
            event_id=f"DEMO_EVT_{_uid()}",
            device_id=dev["device_id"],
            source_ip=dev["ip_address"],
            dest_ip="192.168.1.1",
            source_port=random.randint(1024, 65535),
            dest_port=random.choice([80, 443, 1883, 8080, 8883]),
            protocol=random.choice(["TCP", "UDP", "MQTT"]),
            packet_count=random.randint(1, 10000),
            byte_count=random.randint(64, 1000000),
            flow_duration=round(random.uniform(0.01, 300.0), 3),
            event_type=random.choice(["telemetry", "heartbeat", "network"]),
            timestamp=_now - timedelta(hours=random.randint(0, 48)),
        )
        events.append(evt)
    session.add_all(events)
    print(f"  ✓ Created {len(events)} demo network events")


def _seed_predictions(session) -> None:
    predictions = []
    for i in range(20):
        dev = random.choice(DEMO_DEVICES)
        attack = random.choice(ATTACK_TYPES)
        conf = round(random.uniform(0.5, 0.99), 3)
        risk = round(random.uniform(10, 95), 1)
        sev = "CRITICAL" if risk > 80 else "HIGH" if risk > 60 else "MEDIUM" if risk > 30 else "LOW"
        action = "ISOLATE" if sev in ("CRITICAL", "HIGH") else "MONITOR" if sev == "MEDIUM" else "ALLOW"

        pred = Prediction(
            prediction_id=f"DEMO_PRED_{_uid()}",
            event_id=f"DEMO_EVT_{_uid()}",
            device_id=dev["device_id"],
            prediction=attack,
            confidence=conf,
            risk_score=risk,
            severity=sev,
            recommended_action=action,
            model_name="RandomForest",
            model_version="demo-v1",
            is_anomaly=(attack == "Normal" and conf < 0.6),
            timestamp=_now - timedelta(hours=random.randint(0, 24)),
        )
        predictions.append(pred)
    session.add_all(predictions)
    print(f"  ✓ Created {len(predictions)} demo predictions")


def _seed_threats(session) -> None:
    threats = []
    for i in range(8):
        dev = random.choice(DEMO_DEVICES)
        attack = random.choice([a for a in ATTACK_TYPES if a != "Normal"])
        threat = Threat(
            threat_id=f"DEMO_THR_{_uid()}",
            event_id=f"DEMO_EVT_{_uid()}",
            device_id=dev["device_id"],
            attack_type=attack,
            indicator=f"Suspicious traffic pattern from {dev['ip_address']}",
            severity=random.choice(["HIGH", "CRITICAL"]),
            confidence=round(random.uniform(0.7, 0.99), 3),
            source_node=random.choice(["NODE-A", "NODE-B", "NODE-C"]),
            is_verified=random.choice([True, False]),
            is_shared=True,
            first_seen=_now - timedelta(hours=random.randint(1, 48)),
            last_seen=_now - timedelta(minutes=random.randint(0, 60)),
        )
        threats.append(threat)
    session.add_all(threats)
    print(f"  ✓ Created {len(threats)} demo threats")


def _seed_audit_logs(session) -> None:
    logs = []
    actions = ["LOGIN", "DEVICE_ISOLATE", "DEVICE_RELEASE", "THREAT_VERIFIED", "BLOCKCHAIN_VERIFIED"]
    for i in range(15):
        log = AuditLog(
            audit_id=f"DEMO_AUD_{_uid()}",
            action=random.choice(actions),
            entity_type=random.choice(["user", "device", "threat"]),
            entity_id=random.choice(DEMO_DEVICES)["device_id"],
            user_id="admin",
            details=json.dumps({"source": "DEMO_DATA"}),
            severity="INFO",
            timestamp=_now - timedelta(hours=random.randint(0, 72)),
        )
        logs.append(log)
    session.add_all(logs)
    print(f"  ✓ Created {len(logs)} demo audit logs")


if __name__ == "__main__":
    seed_database()
