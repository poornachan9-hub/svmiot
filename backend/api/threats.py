"""
Threats API — threat intelligence CRUD.

ALL data stored in MongoDB `threats` collection.
SQLite is NO LONGER used for threats.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.mongodb import get_mongodb
from blockchain.threat_intel import ThreatIntelligenceNetwork

router = APIRouter()
threat_network = ThreatIntelligenceNetwork()


class ThreatCreate(BaseModel):
    attack_type: str
    indicator: str
    severity: str
    confidence: float = 0.8
    source_node: str = "NODE-A"
    device_id: Optional[str] = None


@router.get("", summary="List Threats")
async def list_threats(limit: int = 50):
    """Return recent threats from MongoDB."""
    db = get_mongodb()
    cursor = db["threats"].find({}).sort("created_at", -1).limit(limit)
    threats = await cursor.to_list(length=limit)
    for t in threats:
        t.pop("_id", None)
    return threats


@router.post("", summary="Create Threat")
async def create_threat(req: ThreatCreate):
    """Create a new threat record in MongoDB and propagate through threat network."""
    db = get_mongodb()
    record = threat_network.create_threat(
        attack_type=req.attack_type,
        indicator=req.indicator,
        severity=req.severity,
        confidence=req.confidence,
        source_node=req.source_node,
    )
    now = datetime.now(timezone.utc)
    doc = {
        "threat_id": record.threat_id,
        "device_id": req.device_id,
        "attack_type": req.attack_type,
        "indicator": req.indicator,
        "severity": req.severity,
        "confidence": req.confidence,
        "source_node": req.source_node,
        "is_verified": False,
        "is_shared": False,
        "blockchain_block": None,
        "response_action": None,
        "first_seen": now,
        "last_seen": now,
        "created_at": now,
    }
    await db["threats"].insert_one(doc)
    return record.to_dict()


@router.post("/{threat_id}/verify", summary="Verify Threat")
async def verify_threat(threat_id: str, node: str = "NODE-A"):
    result = threat_network.verify_threat(threat_id, node)
    # Update in MongoDB
    db = get_mongodb()
    await db["threats"].update_one(
        {"threat_id": threat_id},
        {"$set": {"is_verified": True, "last_seen": datetime.now(timezone.utc)}},
    )
    return result


@router.post("/{threat_id}/share", summary="Share Threat")
async def share_threat(threat_id: str, from_node: str = "NODE-A"):
    result = threat_network.share_threat(threat_id, from_node)
    db = get_mongodb()
    await db["threats"].update_one(
        {"threat_id": threat_id},
        {"$set": {"is_shared": True, "last_seen": datetime.now(timezone.utc)}},
    )
    return result


@router.get("/network/status", summary="Threat Network Status")
async def network_status():
    return threat_network.get_network_status()


@router.get("/node/{node}", summary="Node Threats")
async def node_threats(node: str):
    return threat_network.get_all_threats(node)
