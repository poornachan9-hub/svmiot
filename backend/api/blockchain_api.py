"""Blockchain API — Ganache is the ONLY real blockchain backend.

Primary endpoints (/status, /record, /verify, /blocks) use Ganache (real Ethereum)
and MongoDB blockchain_records.
The old SecurityBlockchain (JSON ledger) is kept ONLY for the tamper-test demo
(educational: hash-chain integrity concepts).
"""

import logging
from fastapi import APIRouter
from backend.core.config import settings
from backend.core.mongodb import get_mongodb
from blockchain.chain import SecurityBlockchain

logger = logging.getLogger("secureiot.blockchain_api")

router = APIRouter()

# Old chain kept ONLY for tamper-test educational demo
_demo_blockchain = SecurityBlockchain(
    difficulty=settings.blockchain_difficulty,
    ledger_path=str(settings.project_root / settings.blockchain_db_path),
)


def _ganache_client():
    """Get or create Ganache client singleton."""
    from blockchain.ganache_client import get_ganache_client
    return get_ganache_client()


# ── Primary Blockchain Endpoints (Ganache) ─────────────────────

@router.get("/status", summary="Blockchain Status")
async def blockchain_status():
    """Return Ganache (real Ethereum) status as the primary blockchain."""
    try:
        client = _ganache_client()
        ganache = client.get_status()
    except Exception as e:
        ganache = {"connected": False, "error": str(e)}

    # Count blockchain records in MongoDB
    db = get_mongodb()
    total_records = await db.blockchain_records.count_documents({})

    return {
        "blockchain": "ganache",
        "ganache": ganache,
        "total_blocks": total_records,
        "is_valid": ganache.get("connected", False),
        "status": "VALID" if ganache.get("connected", False) else "NOT CONNECTED",
        "difficulty": 0,
        "errors": 0,
        "demo_chain_blocks": _demo_blockchain.length,
    }


@router.get("/blocks", summary="List Blockchain Records")
async def list_blocks(limit: int = 20):
    """Get blockchain records (real Ganache transactions) from MongoDB."""
    db = get_mongodb()
    cursor = db.blockchain_records.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    records = await cursor.to_list(length=limit)

    # Format as block-like objects for the frontend
    blocks = []
    for i, rec in enumerate(records):
        blocks.append({
            "index": i,
            "timestamp": rec.get("timestamp", "").isoformat() if hasattr(rec.get("timestamp", ""), "isoformat") else str(rec.get("timestamp", "")),
            "data": {
                "event_id": rec.get("event_id", ""),
                "device_id": rec.get("device_id", ""),
                "attack_type": rec.get("attack_type", ""),
                "severity": rec.get("severity", ""),
                "risk_score": rec.get("risk_score", 0),
                "action": rec.get("action", ""),
            },
            "hash": rec.get("tx_hash", ""),
            "previous_hash": rec.get("block_hash", ""),
            "block_number": rec.get("block_number"),
            "tx_hash": rec.get("tx_hash", ""),
            "status": rec.get("status", ""),
            "gas_used": rec.get("gas_used"),
            "chain_id": rec.get("chain_id"),
            "is_valid": rec.get("status") == "SUCCESS",
            "nonce": 0,
            "difficulty": 0,
        })
    return blocks


@router.post("/verify", summary="Verify Blockchain Connectivity")
async def verify_chain():
    """Verify Ganache is connected and operational."""
    try:
        client = _ganache_client()
        if not client.is_connected():
            return {"valid": False, "status": "✗ GANACHE NOT CONNECTED", "errors": ["Cannot reach Ganache RPC"]}
        status = client.get_status()
        return {
            "valid": True,
            "status": "✓ GANACHE CONNECTED",
            "block_number": status.get("block_number"),
            "chain_id": status.get("chain_id"),
            "accounts_count": status.get("accounts_count"),
            "errors": [],
        }
    except Exception as e:
        return {"valid": False, "status": "✗ ERROR", "errors": [str(e)]}


@router.post("/record", summary="Record Security Event on Ganache")
async def record_event(
    event_id: str, device_id: str, attack_type: str,
    severity: str, risk_score: float, action: str,
):
    """Record a security event on the real Ganache blockchain."""
    from backend.core.websocket import ws_manager
    try:
        client = _ganache_client()
        if not client.is_connected():
            return {"error": "Ganache not connected", "connected": False}

        record = client.record_security_event({
            "event_id": event_id,
            "device_id": device_id,
            "attack_type": attack_type,
            "severity": severity,
            "risk_score": risk_score,
            "action": action,
        })
        await ws_manager.broadcast("block_created", record)
        return record
    except Exception as e:
        logger.error("Failed to record event on Ganache: %s", e)
        return {"error": str(e), "connected": False}


# ── Ganache Query Endpoints ────────────────────────────────────

@router.get("/ganache/status", summary="Ganache Blockchain Status")
async def ganache_status():
    """Get the real Ganache Ethereum node status via Web3."""
    try:
        client = _ganache_client()
        return client.get_status()
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.get("/ganache/verify/{tx_hash}", summary="Verify Ganache Transaction")
async def verify_ganache_tx(tx_hash: str):
    """Verify a real transaction exists on Ganache and decode its payload."""
    try:
        client = _ganache_client()
        if not client.is_connected():
            return {"verified": False, "error": "Ganache not connected"}
        return client.verify_transaction(tx_hash)
    except Exception as e:
        return {"verified": False, "error": str(e)}


# ── Demo-Only Endpoints (old SecurityBlockchain for education) ─

@router.get("/demo/blocks", summary="Demo Chain — List Blocks")
async def list_demo_blocks():
    """List blocks from the demo hash-chain (educational only, not real blockchain)."""
    return _demo_blockchain.get_all_blocks()


@router.get("/demo/blocks/{index}", summary="Demo Chain — Get Block")
async def get_demo_block(index: int):
    block = _demo_blockchain.get_block(index)
    if block is None:
        return {"error": "Block not found"}
    return block


@router.post("/tamper-test", summary="Demo: Tamper Detection")
async def tamper_test():
    """Demonstrate tamper detection using the educational hash-chain (not Ganache)."""
    if _demo_blockchain.length < 3:
        _demo_blockchain.record_event("TEST_1", "ESP32_001", "DDoS", "HIGH", 85.0, "ISOLATE")
        _demo_blockchain.record_event("TEST_2", "ESP32_002", "Normal", "LOW", 10.0, "ALLOW")
        _demo_blockchain.record_event("TEST_3", "ESP32_003", "DoS", "CRITICAL", 92.0, "BLOCK")

    valid_before, _ = _demo_blockchain.validate_chain()
    tamper_result = _demo_blockchain.simulate_tamper(1)
    valid_after, errors = _demo_blockchain.validate_chain()

    return {
        "chain_valid_before": valid_before,
        "tamper_action": tamper_result,
        "chain_valid_after": valid_after,
        "tamper_detected": not valid_after,
        "errors": errors,
        "note": "This uses the educational demo chain, not Ganache",
    }
