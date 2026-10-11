"""
SecureIoT-X Blockchain — Block Structure & Hashing.

Lightweight permissioned blockchain for security event metadata.
Stores hashes, not full datasets.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class Block:
    """A single block in the security event blockchain."""

    def __init__(
        self,
        index: int,
        event_id: str,
        device_id: str,
        attack_type: str,
        severity: str,
        risk_score: float,
        action: str,
        previous_hash: str,
        nonce: int = 0,
        timestamp: Optional[str] = None,
    ) -> None:
        self.index = index
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.event_id = event_id
        self.device_id = device_id
        self.attack_type = attack_type
        self.severity = severity
        self.risk_score = risk_score
        self.action = action
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.event_hash = self._compute_event_hash()
        self.hash = self.calculate_hash()

    def _compute_event_hash(self) -> str:
        """Hash the event data (without block metadata)."""
        event_data = f"{self.event_id}{self.device_id}{self.attack_type}{self.severity}{self.risk_score}{self.action}"
        return hashlib.sha256(event_data.encode()).hexdigest()

    def calculate_hash(self) -> str:
        """Calculate the full block hash (SHA-256)."""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "device_id": self.device_id,
            "attack_type": self.attack_type,
            "severity": self.severity,
            "risk_score": self.risk_score,
            "action": self.action,
            "event_hash": self.event_hash,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine(self, difficulty: int = 2) -> None:
        """Simple proof-of-work mining."""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize block to dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "device_id": self.device_id,
            "attack_type": self.attack_type,
            "severity": self.severity,
            "risk_score": self.risk_score,
            "action": self.action,
            "event_hash": self.event_hash,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        """Deserialize block from dictionary."""
        block = cls(
            index=data["index"],
            event_id=data["event_id"],
            device_id=data["device_id"],
            attack_type=data["attack_type"],
            severity=data["severity"],
            risk_score=data["risk_score"],
            action=data["action"],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            timestamp=data["timestamp"],
        )
        block.event_hash = data.get("event_hash", block._compute_event_hash())
        block.hash = data.get("hash", block.calculate_hash())
        return block

    def __repr__(self) -> str:
        return f"<Block #{self.index} hash={self.hash[:16]}… event={self.event_id}>"
