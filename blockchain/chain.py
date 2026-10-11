"""
SecureIoT-X Blockchain — Chain Management & Validation.

Implements: create_block, add_block, validate_chain, verify_block, tamper_detection.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from blockchain.block import Block

logger = logging.getLogger("secureiot.blockchain")


class SecurityBlockchain:
    """Lightweight permissioned blockchain for IoT security events."""

    def __init__(self, difficulty: int = 2, ledger_path: str = "blockchain_ledger.json") -> None:
        self.difficulty = difficulty
        self.ledger_path = Path(ledger_path)
        self.chain: List[Block] = []
        self._load_or_create()

    # ── Chain creation ─────────────────────────────────────────

    def _load_or_create(self) -> None:
        """Load existing chain from disk or create genesis block."""
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            try:
                with open(self.ledger_path, "r") as f:
                    data = json.load(f)
                self.chain = [Block.from_dict(b) for b in data]
                logger.info("Loaded blockchain: %d blocks", len(self.chain))
                return
            except Exception as e:
                logger.warning("Failed to load blockchain: %s — creating new", e)

        # Create genesis block
        genesis = self._create_genesis()
        self.chain = [genesis]
        self._persist()
        logger.info("Created new blockchain with genesis block")

    def _create_genesis(self) -> Block:
        """Create the genesis (first) block."""
        genesis = Block(
            index=0,
            event_id="GENESIS",
            device_id="SYSTEM",
            attack_type="NONE",
            severity="INFO",
            risk_score=0.0,
            action="INIT",
            previous_hash="0" * 64,
        )
        genesis.mine(self.difficulty)
        return genesis

    # ── Block operations ───────────────────────────────────────

    def create_block(
        self,
        event_id: str,
        device_id: str,
        attack_type: str,
        severity: str,
        risk_score: float,
        action: str,
    ) -> Block:
        """Create a new block (not yet added to chain)."""
        previous_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            event_id=event_id,
            device_id=device_id,
            attack_type=attack_type,
            severity=severity,
            risk_score=risk_score,
            action=action,
            previous_hash=previous_block.hash,
        )
        new_block.mine(self.difficulty)
        return new_block

    def add_block(self, block: Block) -> bool:
        """Add a block to the chain after validation."""
        if not self._is_valid_new_block(block, self.chain[-1]):
            logger.error("Invalid block rejected: #%d", block.index)
            return False

        self.chain.append(block)
        self._persist()
        logger.info("Block #%d added (event=%s, device=%s, action=%s)",
                     block.index, block.event_id, block.device_id, block.action)
        return True

    def record_event(
        self,
        event_id: str,
        device_id: str,
        attack_type: str,
        severity: str,
        risk_score: float,
        action: str,
    ) -> Block:
        """Create and add a block in one step."""
        block = self.create_block(event_id, device_id, attack_type, severity, risk_score, action)
        self.add_block(block)
        return block

    # ── Validation ─────────────────────────────────────────────

    def validate_chain(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate the entire blockchain.
        Returns (is_valid, list_of_errors).
        """
        errors = []

        if len(self.chain) == 0:
            return False, [{"error": "Chain is empty"}]

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Check hash integrity
            recalculated = current.calculate_hash()
            if current.hash != recalculated:
                errors.append({
                    "block": i,
                    "error": "HASH_MISMATCH",
                    "expected": recalculated,
                    "actual": current.hash,
                })

            # Check previous hash link
            if current.previous_hash != previous.hash:
                errors.append({
                    "block": i,
                    "error": "PREVIOUS_HASH_MISMATCH",
                    "expected": previous.hash,
                    "actual": current.previous_hash,
                })

            # Check index sequence
            if current.index != previous.index + 1:
                errors.append({
                    "block": i,
                    "error": "INDEX_SEQUENCE_BROKEN",
                    "expected": previous.index + 1,
                    "actual": current.index,
                })

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("Blockchain validation: ✓ VALID (%d blocks)", len(self.chain))
        else:
            logger.warning("Blockchain validation: ✗ TAMPERED (%d errors)", len(errors))

        return is_valid, errors

    def verify_block(self, index: int) -> Dict[str, Any]:
        """Verify a single block's integrity."""
        if index < 0 or index >= len(self.chain):
            return {"valid": False, "error": "Block index out of range"}

        block = self.chain[index]
        recalculated = block.calculate_hash()
        is_valid = block.hash == recalculated

        result = {
            "block_index": index,
            "valid": is_valid,
            "hash": block.hash,
            "recalculated_hash": recalculated,
        }

        if index > 0:
            previous = self.chain[index - 1]
            result["previous_hash_valid"] = block.previous_hash == previous.hash

        return result

    def tamper_detection(self) -> Dict[str, Any]:
        """Run tamper detection and return a status report."""
        is_valid, errors = self.validate_chain()
        status = "VALID" if is_valid else "TAMPER_DETECTED"

        block_statuses = []
        for i, block in enumerate(self.chain):
            block_valid = not any(e["block"] == i for e in errors) if errors else True
            block_statuses.append({
                "index": i,
                "event_id": block.event_id,
                "status": "✓" if block_valid else "✗ INVALID",
            })

        return {
            "status": status,
            "total_blocks": len(self.chain),
            "errors": errors,
            "blocks": block_statuses,
        }

    # ── Tampering demo (for testing) ───────────────────────────

    def simulate_tamper(self, block_index: int) -> Dict[str, Any]:
        """
        Deliberately tamper with a block for demonstration purposes.
        Modifies a historical event to show tamper detection works.
        """
        if block_index <= 0 or block_index >= len(self.chain):
            return {"error": "Cannot tamper genesis block or invalid index"}

        block = self.chain[block_index]
        original_event = block.attack_type
        block.attack_type = "TAMPERED_EVENT"
        # Don't recalculate hash — this IS the tamper

        return {
            "tampered_block": block_index,
            "original_value": original_event,
            "tampered_value": "TAMPERED_EVENT",
            "message": "Block tampered. Run validate_chain() to detect.",
        }

    # ── Queries ────────────────────────────────────────────────

    def get_block(self, index: int) -> Optional[Dict[str, Any]]:
        if 0 <= index < len(self.chain):
            return self.chain[index].to_dict()
        return None

    def get_all_blocks(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.chain]

    def get_latest_block(self) -> Dict[str, Any]:
        return self.chain[-1].to_dict()

    def get_status(self) -> Dict[str, Any]:
        is_valid, errors = self.validate_chain()
        return {
            "status": "VALID" if is_valid else "TAMPER_DETECTED",
            "is_valid": is_valid,
            "chain_valid": is_valid,
            "total_blocks": len(self.chain),
            "latest_block": self.chain[-1].index if self.chain else -1,
            "difficulty": self.difficulty,
            "errors": len(errors),
        }

    @property
    def length(self) -> int:
        return len(self.chain)

    # ── Helpers ────────────────────────────────────────────────

    def _is_valid_new_block(self, new_block: Block, previous_block: Block) -> bool:
        """Validate a new block before adding."""
        if new_block.index != previous_block.index + 1:
            return False
        if new_block.previous_hash != previous_block.hash:
            return False
        if new_block.hash != new_block.calculate_hash():
            return False
        return True

    def _persist(self) -> None:
        """Save chain to disk."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "w") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)
