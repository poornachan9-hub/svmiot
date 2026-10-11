"""
SecureIoT-X — Ganache Real Web3 Blockchain Client.

Interacts with Ganache Ethereum testnet using Web3.py.
Sends real immutable on-chain transactions for security events and isolation records.
No fake hashes or mock fallbacks.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional
from web3 import Web3
from web3.exceptions import Web3Exception

from backend.core.config import settings

logger = logging.getLogger("secureiot.blockchain.ganache")


class GanacheClient:
    """Real Web3 client connected to local Ganache instance."""

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.ganache_rpc_url
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 1.0}))
        self.private_key = settings.ganache_private_key
        logger.info("GanacheClient initialized with RPC %s (connected=%s)", self.rpc_url, self.is_connected())

    def is_connected(self) -> bool:
        """Check if Web3 is connected to Ganache RPC."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get status and details of Ganache node."""
        connected = self.is_connected()
        if not connected:
            return {
                "connected": False,
                "rpc_url": self.rpc_url,
                "error": "Cannot connect to Ganache RPC at " + self.rpc_url,
            }

        try:
            accounts = self.w3.eth.accounts
            block_num = self.w3.eth.block_number
            default_acct = accounts[0] if accounts else None
            balance = 0.0
            if default_acct:
                balance_wei = self.w3.eth.get_balance(default_acct)
                balance = float(self.w3.from_wei(balance_wei, "ether"))

            chain_id = self.w3.eth.chain_id

            return {
                "connected": True,
                "rpc_url": self.rpc_url,
                "chain_id": chain_id,
                "block_number": block_num,
                "accounts_count": len(accounts),
                "default_account": default_acct,
                "balance_eth": round(balance, 4),
            }
        except Exception as e:
            logger.error("Error retrieving Ganache status: %s", e)
            return {
                "connected": True,
                "rpc_url": self.rpc_url,
                "error": str(e),
            }

    def record_security_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a security event on Ganache blockchain via a real transaction.
        Embeds the SHA-256 event hash and metadata into the transaction data payload.
        """
        if not self.is_connected():
            raise ConnectionError(f"Ganache is not reachable at {self.rpc_url}")

        accounts = self.w3.eth.accounts
        if not accounts and not self.private_key:
            raise RuntimeError("No unlocked accounts available in Ganache and no private key configured.")

        # Compute SHA-256 hash of event data
        canonical_str = json.dumps(event_data, sort_keys=True, default=str)
        event_sha256 = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        # Build data payload for transaction
        payload_dict = {
            "app": "SecureIoT-X",
            "event_id": event_data.get("event_id", ""),
            "device_id": event_data.get("device_id", ""),
            "attack_type": event_data.get("attack_type", event_data.get("predicted_attack", "Unknown")),
            "risk_score": event_data.get("risk_score", 0),
            "action": event_data.get("action", "ISOLATE"),
            "event_hash": event_sha256,
            "timestamp": event_data.get("timestamp", time.time()),
        }
        data_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")

        # Send transaction
        if self.private_key:
            account = self.w3.eth.account.from_key(self.private_key)
            from_addr = account.address
            nonce = self.w3.eth.get_transaction_count(from_addr)
            tx = {
                "nonce": nonce,
                "to": from_addr,
                "value": 0,
                "gas": 100000,
                "gasPrice": self.w3.eth.gas_price,
                "data": data_bytes,
                "chainId": self.w3.eth.chain_id,
            }
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash_bytes = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        else:
            from_addr = accounts[0]
            tx = {
                "from": from_addr,
                "to": from_addr,
                "value": 0,
                "data": data_bytes,
            }
            tx_hash_bytes = self.w3.eth.send_transaction(tx)

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=15)
        tx_hash_hex = receipt.transactionHash.hex()
        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = "0x" + tx_hash_hex

        block_hash_hex = receipt.blockHash.hex()
        if not block_hash_hex.startswith("0x"):
            block_hash_hex = "0x" + block_hash_hex

        record = {
            "tx_hash": tx_hash_hex,
            "block_number": receipt.blockNumber,
            "block_hash": block_hash_hex,
            "from": from_addr,
            "to": from_addr,
            "gas_used": receipt.gasUsed,
            "status": "SUCCESS" if receipt.status == 1 else "FAILED",
            "event_hash": event_sha256,
            "timestamp": time.time(),
            "chain_id": self.w3.eth.chain_id,
        }
        logger.info("Security event recorded on Ganache! Block %d, Tx: %s", receipt.blockNumber, tx_hash_hex)
        return record

    def verify_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Verify transaction exists on the Ganache blockchain and decode its payload."""
        if not self.is_connected():
            raise ConnectionError(f"Ganache is not reachable at {self.rpc_url}")

        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        tx = self.w3.eth.get_transaction(tx_hash)
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)

        # Decode data payload
        payload = None
        input_data = tx.get("input", b"")
        if input_data:
            try:
                if isinstance(input_data, str) and input_data.startswith("0x"):
                    decoded_bytes = bytes.fromhex(input_data[2:])
                else:
                    decoded_bytes = bytes(input_data)
                payload = json.loads(decoded_bytes.decode("utf-8"))
            except Exception:
                payload = str(input_data)

        return {
            "verified": True,
            "tx_hash": tx_hash,
            "block_number": receipt.blockNumber,
            "block_hash": receipt.blockHash.hex(),
            "from": tx["from"],
            "to": tx["to"],
            "gas_used": receipt.gasUsed,
            "status": "SUCCESS" if receipt.status == 1 else "FAILED",
            "payload": payload,
        }


# Global singleton client
_ganache_client: Optional[GanacheClient] = None


def get_ganache_client() -> GanacheClient:
    """Get or create singleton GanacheClient instance."""
    global _ganache_client
    if _ganache_client is None:
        _ganache_client = GanacheClient()
    return _ganache_client
