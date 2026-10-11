"""
SecureIoT-X Blockchain — Threat Intelligence Layer.

Simulates multi-node threat intelligence sharing.
Nodes: NODE-A, NODE-B, NODE-C
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("secureiot.blockchain.threat_intel")


class ThreatIntelRecord:
    """A single threat intelligence record."""

    def __init__(
        self,
        attack_type: str,
        indicator: str,
        severity: str,
        confidence: float,
        source_node: str = "NODE-A",
        threat_id: Optional[str] = None,
    ) -> None:
        self.threat_id = threat_id or uuid.uuid4().hex[:16]
        self.attack_type = attack_type
        self.indicator = indicator
        self.severity = severity
        self.confidence = confidence
        self.source_node = source_node
        self.first_seen = datetime.now(timezone.utc).isoformat()
        self.last_seen = self.first_seen
        self.is_verified = False
        self.is_trusted = True
        self.shared_with: List[str] = []
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        data = f"{self.threat_id}{self.attack_type}{self.indicator}{self.severity}{self.source_node}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify(self) -> bool:
        """Verify the integrity of this record."""
        return self.hash == self._compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_id": self.threat_id,
            "attack_type": self.attack_type,
            "indicator": self.indicator,
            "severity": self.severity,
            "confidence": self.confidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "source_node": self.source_node,
            "is_verified": self.is_verified,
            "is_trusted": self.is_trusted,
            "shared_with": self.shared_with,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreatIntelRecord":
        record = cls(
            attack_type=data["attack_type"],
            indicator=data["indicator"],
            severity=data["severity"],
            confidence=data["confidence"],
            source_node=data.get("source_node", "NODE-A"),
            threat_id=data.get("threat_id"),
        )
        record.first_seen = data.get("first_seen", record.first_seen)
        record.last_seen = data.get("last_seen", record.last_seen)
        record.is_verified = data.get("is_verified", False)
        record.is_trusted = data.get("is_trusted", True)
        record.shared_with = data.get("shared_with", [])
        record.hash = data.get("hash", record._compute_hash())
        return record


class ThreatIntelligenceNetwork:
    """
    Simulated multi-node threat intelligence sharing.
    Supports: create, verify, share, receive, search, trust management.
    """

    NODES = ["NODE-A", "NODE-B", "NODE-C"]

    def __init__(self) -> None:
        # Each node has its own threat database
        self._databases: Dict[str, List[ThreatIntelRecord]] = {
            node: [] for node in self.NODES
        }

    def create_threat(
        self,
        attack_type: str,
        indicator: str,
        severity: str,
        confidence: float,
        source_node: str = "NODE-A",
    ) -> ThreatIntelRecord:
        """Create a new threat intelligence record on a source node."""
        if source_node not in self.NODES:
            raise ValueError(f"Unknown node: {source_node}. Available: {self.NODES}")

        record = ThreatIntelRecord(
            attack_type=attack_type,
            indicator=indicator,
            severity=severity,
            confidence=confidence,
            source_node=source_node,
        )
        self._databases[source_node].append(record)
        logger.info("[%s] Created threat: %s (%s)", source_node, record.threat_id, attack_type)
        return record

    def verify_threat(self, threat_id: str, node: str = "NODE-A") -> Dict[str, Any]:
        """Verify a threat record's integrity."""
        for record in self._databases.get(node, []):
            if record.threat_id == threat_id:
                is_valid = record.verify()
                record.is_verified = is_valid
                return {
                    "threat_id": threat_id,
                    "node": node,
                    "valid": is_valid,
                    "hash": record.hash,
                }
        return {"threat_id": threat_id, "node": node, "error": "Not found"}

    def share_threat(self, threat_id: str, from_node: str, to_nodes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Share a threat from one node to others."""
        source_record = None
        for record in self._databases.get(from_node, []):
            if record.threat_id == threat_id:
                source_record = record
                break

        if source_record is None:
            return {"error": f"Threat {threat_id} not found on {from_node}"}

        targets = to_nodes or [n for n in self.NODES if n != from_node]
        shared_to = []

        for target in targets:
            if target == from_node:
                continue
            # Check if already shared
            existing = [r for r in self._databases[target] if r.threat_id == threat_id]
            if not existing:
                received = ThreatIntelRecord.from_dict(source_record.to_dict())
                self._databases[target].append(received)
                source_record.shared_with.append(target)
                shared_to.append(target)
                logger.info("[%s] → [%s] Shared threat: %s", from_node, target, threat_id)

        return {
            "threat_id": threat_id,
            "from": from_node,
            "shared_to": shared_to,
            "total_nodes": len(shared_to),
        }

    def receive_threat(self, node: str, threat_data: Dict[str, Any]) -> ThreatIntelRecord:
        """Receive a threat record from another node."""
        record = ThreatIntelRecord.from_dict(threat_data)
        self._databases[node].append(record)
        logger.info("[%s] Received threat: %s from %s", node, record.threat_id, record.source_node)
        return record

    def search_threats(
        self,
        node: str = "NODE-A",
        attack_type: Optional[str] = None,
        severity: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search threat records on a node."""
        results = []
        for record in self._databases.get(node, []):
            if attack_type and record.attack_type != attack_type:
                continue
            if severity and record.severity != severity:
                continue
            if record.confidence < min_confidence:
                continue
            results.append(record.to_dict())
        return results

    def mark_trusted(self, threat_id: str, node: str, trusted: bool = True) -> Dict[str, Any]:
        """Mark a threat as trusted or untrusted."""
        for record in self._databases.get(node, []):
            if record.threat_id == threat_id:
                record.is_trusted = trusted
                return {"threat_id": threat_id, "node": node, "trusted": trusted}
        return {"error": f"Threat {threat_id} not found on {node}"}

    def get_all_threats(self, node: str = "NODE-A") -> List[Dict[str, Any]]:
        """Get all threats on a node."""
        return [r.to_dict() for r in self._databases.get(node, [])]

    def get_network_status(self) -> Dict[str, Any]:
        """Get status of the entire threat intelligence network."""
        return {
            "nodes": self.NODES,
            "threats_per_node": {
                node: len(records) for node, records in self._databases.items()
            },
            "total_threats": sum(len(r) for r in self._databases.values()),
        }
