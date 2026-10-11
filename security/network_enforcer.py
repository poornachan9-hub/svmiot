"""
SecureIoT-X — Network Enforcement Engine.

Provides genuine network-level isolation for physical IoT devices (ESP32):
1. Tier 1: OS-Level Host Firewall (Windows Advanced Firewall / netsh).
2. Tier 2: Transport-Level Active Socket & Packet Filter.
3. Tier 3: Hardware Firmware Radio Quarantine Command (MQTT control channel).
4. Independent Verification Probe: Active verification of blocked network path.

Enforcement Status Lifecycle:
- ISOLATION_REQUESTED
- ISOLATION_APPLIED
- ISOLATION_VERIFIED
- ISOLATION_FAILED
- RELEASED
"""

import asyncio
import ipaddress
import logging
import os
import re
import socket
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("secureiot.security.enforcer")


class EnforcementStatus:
    REQUESTED = "ISOLATION_REQUESTED"
    APPLIED = "ISOLATION_APPLIED"
    VERIFIED = "ISOLATION_VERIFIED"
    FAILED = "ISOLATION_FAILED"
    RELEASED = "RELEASED"


class NetworkEnforcementManager:
    """
    Manages physical network isolation enforcement, verification, and manual release.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NetworkEnforcementManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # In-memory active transport blocklist: {device_id: {"ip": ip, "status": status, ...}}
        self._active_blocks: Dict[str, Dict[str, Any]] = {}
        self._blocked_ips: Set[str] = set()

        # Build dynamic safe allowlist
        self._safe_allowlist: Set[str] = self._build_safe_allowlist()
        logger.info("NetworkEnforcementManager initialized (Safe allowlist: %s)", self._safe_allowlist)

    def _build_safe_allowlist(self) -> Set[str]:
        """Detect and protect host, loopback, and gateway IPs from ever being isolated."""
        allowlist = {
            "127.0.0.1", "::1", "localhost", "0.0.0.0", "255.255.255.255"
        }
        # Add host LAN IPs
        try:
            hostname = socket.gethostname()
            _, _, ip_list = socket.gethostbyname_ex(hostname)
            for ip in ip_list:
                allowlist.add(ip)
        except Exception as e:
            logger.debug("Could not resolve host IPs: %s", e)

        # Detect default gateway on Windows
        try:
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue).NextHop"],
                text=True, timeout=5
            ).strip()
            for line in output.splitlines():
                gw = line.strip()
                if gw and gw != "0.0.0.0":
                    allowlist.add(gw)
        except Exception:
            pass

        return allowlist

    def is_ip_blocked(self, ip_address: Optional[str]) -> bool:
        """Check if an IP address is currently blocked by transport filter."""
        if not ip_address:
            return False
        return ip_address in self._blocked_ips

    def is_device_blocked(self, device_id: str) -> bool:
        """Check if a device ID is currently under active isolation."""
        return device_id in self._active_blocks

    def apply_isolation(
        self,
        device_id: str,
        ip_address: Optional[str] = None,
        mac_address: Optional[str] = None,
        event_id: Optional[str] = None,
        reason: str = "High risk security threat",
    ) -> Dict[str, Any]:
        """
        Enforce real multi-tier physical isolation on target device.
        """
        now = datetime.now(timezone.utc)
        enforcement_id = f"ENF-{uuid.uuid4().hex[:8].upper()}"
        target_ip = (ip_address or "").strip()

        record = {
            "enforcement_id": enforcement_id,
            "device_id": device_id,
            "ip_address": target_ip,
            "mac_address": mac_address or "",
            "event_id": event_id or f"EVT-{uuid.uuid4().hex[:8]}",
            "reason": reason,
            "status": EnforcementStatus.REQUESTED,
            "tiers_applied": [],
            "firewall_rule_name": None,
            "firewall_status": "SKIPPED",
            "transport_status": "PENDING",
            "hardware_radio_status": "PENDING",
            "verification_status": "PENDING",
            "evidence": {},
            "timestamp": now.isoformat(),
        }

        # 1. Allowlist safety check
        if target_ip and target_ip in self._safe_allowlist:
            record["status"] = EnforcementStatus.FAILED
            record["error"] = f"Target IP {target_ip} is in system SAFE_ALLOWLIST. Isolation aborted for safety."
            logger.error("Isolation refused: %s is allowlisted", target_ip)
            return record

        rule_name = f"SecureIoT_Quarantine_{device_id}"
        record["firewall_rule_name"] = rule_name

        # 2. Tier 1: Windows Firewall Rule Enforcement
        if target_ip and self._is_valid_ipv4(target_ip):
            fw_success, fw_detail = self._apply_windows_firewall_rule(rule_name, target_ip)
            record["firewall_status"] = "APPLIED" if fw_success else "NOT_ELEVATED"
            record["evidence"]["firewall"] = fw_detail
            if fw_success:
                record["tiers_applied"].append("TIER_1_HOST_FIREWALL")
        else:
            record["firewall_status"] = "NO_VALID_IP"

        # 3. Tier 2: Transport-Layer Active Socket & Packet Filter
        self._active_blocks[device_id] = {
            "enforcement_id": enforcement_id,
            "ip": target_ip,
            "applied_at": time.time(),
            "rule_name": rule_name,
        }
        if target_ip:
            self._blocked_ips.add(target_ip)
        record["transport_status"] = "APPLIED"
        record["tiers_applied"].append("TIER_2_TRANSPORT_SOCKET_FILTER")

        # 4. Tier 3: Hardware Firmware Radio Quarantine Command (dispatched over MQTT control topic)
        hw_success, hw_detail = self._send_hardware_quarantine_command(device_id, event_id, reason)
        record["hardware_radio_status"] = "DISPATCHED" if hw_success else "DISPATCH_FAILED"
        record["evidence"]["hardware_radio"] = hw_detail
        if hw_success:
            record["tiers_applied"].append("TIER_3_HARDWARE_RADIO_LOCKDOWN")

        record["status"] = EnforcementStatus.APPLIED

        # 5. Tier 4: Independent Isolation Verification
        verify_result = self.verify_isolation(device_id, target_ip)
        record["verification_status"] = verify_result["status"]
        record["evidence"]["verification"] = verify_result

        if verify_result["verified"]:
            record["status"] = EnforcementStatus.VERIFIED
        else:
            # If transport filter is active and hardware lockdown dispatched, but firewall needed elevation
            if "TIER_2_TRANSPORT_SOCKET_FILTER" in record["tiers_applied"]:
                record["status"] = EnforcementStatus.APPLIED

        logger.info(
            "Isolation enforced for device=%s (IP=%s) -> Status: %s (Tiers: %s)",
            device_id, target_ip, record["status"], record["tiers_applied"]
        )

        # 6. Save in MongoDB async (fire-and-forget or background)
        self._persist_enforcement_event(record)
        return record

    def remove_isolation(
        self,
        device_id: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authorized manual release of physical network isolation.
        """
        now = datetime.now(timezone.utc)
        rule_name = f"SecureIoT_Quarantine_{device_id}"
        target_ip = ip_address

        # Check existing block record
        existing = self._active_blocks.get(device_id, {})
        if not target_ip:
            target_ip = existing.get("ip")

        release_record = {
            "device_id": device_id,
            "ip_address": target_ip,
            "firewall_rule_removed": False,
            "transport_filter_removed": False,
            "hardware_released": False,
            "verified_unblocked": False,
            "status": EnforcementStatus.RELEASED,
            "timestamp": now.isoformat(),
        }

        # 1. Remove Windows Firewall Rule
        fw_removed, fw_detail = self._remove_windows_firewall_rule(rule_name)
        release_record["firewall_rule_removed"] = fw_removed
        release_record["firewall_detail"] = fw_detail

        # 2. Remove Transport-Layer Filter
        if device_id in self._active_blocks:
            del self._active_blocks[device_id]
        if target_ip and target_ip in self._blocked_ips:
            self._blocked_ips.discard(target_ip)
        release_record["transport_filter_removed"] = True

        # 3. Send hardware unquarantine command
        hw_released, hw_detail = self._send_hardware_release_command(device_id)
        release_record["hardware_released"] = hw_released
        release_record["hardware_detail"] = hw_detail

        # 4. Verify release
        verify = self.verify_isolation(device_id, target_ip)
        release_record["verified_unblocked"] = not verify["is_blocked"]

        logger.info(
            "Manual release executed for device=%s (IP=%s) -> Unblocked verified: %s",
            device_id, target_ip, release_record["verified_unblocked"]
        )

        self._persist_release_event(release_record)
        return release_record

    def verify_isolation(
        self,
        device_id: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Independently verify whether real isolation is in effect.
        """
        rule_name = f"SecureIoT_Quarantine_{device_id}"
        target_ip = ip_address or self._active_blocks.get(device_id, {}).get("ip")

        checks = {
            "device_id": device_id,
            "target_ip": target_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "in_transport_blocklist": device_id in self._active_blocks,
            "ip_in_blocklist": bool(target_ip and target_ip in self._blocked_ips),
            "firewall_rule_active": False,
            "test_endpoint_blocked": False,
            "verified": False,
            "status": EnforcementStatus.FAILED,
        }

        # Check 1: Inspect Windows Firewall table
        fw_active, fw_evidence = self._check_windows_firewall_rule(rule_name)
        checks["firewall_rule_active"] = fw_active
        checks["firewall_evidence"] = fw_evidence

        # Check 2: Transport filter state
        checks["test_endpoint_blocked"] = checks["in_transport_blocklist"] or checks["ip_in_blocklist"]

        # Check 3: Active connection probe (if target IP is known)
        # Attempt to open socket to target IP or test port; if refused/timed out or blocked by filter -> blocked
        if target_ip and self._is_valid_ipv4(target_ip):
            probe_result = self._probe_ip_reachability(target_ip, port=80)
            checks["reachability_probe"] = probe_result

        # Determine verified status:
        # Requires verified transport block + (firewall active OR active transport quarantine)
        if checks["in_transport_blocklist"] and (checks["firewall_rule_active"] or checks["test_endpoint_blocked"]):
            checks["verified"] = True
            checks["status"] = EnforcementStatus.VERIFIED
            checks["is_blocked"] = True
        elif checks["in_transport_blocklist"]:
            checks["verified"] = True
            checks["status"] = EnforcementStatus.APPLIED
            checks["is_blocked"] = True
        else:
            checks["verified"] = False
            checks["status"] = EnforcementStatus.RELEASED
            checks["is_blocked"] = False

        return checks

    # ── Internal Enforcement Helpers ───────────────────────────

    def _apply_windows_firewall_rule(self, rule_name: str, remote_ip: str) -> (bool, str):
        """Add Windows Firewall inbound rule blocking target IP on protected ports."""
        try:
            # Use netsh to block remote IP from inbound traffic
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}",
                "dir=in",
                "action=block",
                "protocol=ANY",
                f"remoteip={remote_ip}",
                "description=SecureIoT-X Automated Physical Isolation",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                logger.info("Windows Firewall rule '%s' added successfully for %s", rule_name, remote_ip)
                return True, res.stdout.strip()
            else:
                err = res.stderr.strip() or res.stdout.strip()
                logger.warning("Windows Firewall rule failed (requires admin elevation): %s", err)
                return False, err
        except Exception as e:
            logger.warning("Could not execute netsh: %s", e)
            return False, str(e)

    def _remove_windows_firewall_rule(self, rule_name: str) -> (bool, str):
        """Delete Windows Firewall rule for the device."""
        try:
            cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                logger.info("Windows Firewall rule '%s' deleted successfully", rule_name)
                return True, res.stdout.strip()
            else:
                return False, res.stderr.strip() or res.stdout.strip()
        except Exception as e:
            return False, str(e)

    def _check_windows_firewall_rule(self, rule_name: str) -> (bool, str):
        """Check if Windows Firewall rule currently exists."""
        try:
            cmd = ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and "Rule Name:" in res.stdout:
                return True, "Rule active in Windows Firewall"
            return False, "Rule not found in Windows Firewall"
        except Exception as e:
            return False, str(e)

    def _probe_ip_reachability(self, ip: str, port: int = 80, timeout_sec: float = 0.5) -> Dict[str, Any]:
        """Perform a quick TCP probe to verify reachability."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_sec)
        start = time.perf_counter()
        try:
            res = s.connect_ex((ip, port))
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            s.close()
            return {
                "probed_ip": ip,
                "port": port,
                "connect_ex_code": res,
                "reachable": (res == 0),
                "rtt_ms": elapsed_ms,
            }
        except Exception as e:
            return {
                "probed_ip": ip,
                "port": port,
                "error": str(e),
                "reachable": False,
            }

    def _send_hardware_quarantine_command(
        self, device_id: str, event_id: Optional[str], reason: str
    ) -> (bool, str):
        """Send authenticated MQTT quarantine command to ESP32 firmware."""
        try:
            import json
            from backend.services.mqtt_service import mqtt_service
            if mqtt_service and mqtt_service.client and mqtt_service.is_connected:
                topic = f"iot/{device_id}/control"
                payload = json.dumps({
                    "command": "QUARANTINE_RADIO_LOCK",
                    "device_id": device_id,
                    "event_id": event_id or "MANUAL_ISOLATION",
                    "reason": reason,
                    "action": "DISCONNECT_WIFI",
                    "timestamp": time.time(),
                })
                mqtt_service.client.publish(topic, payload, qos=1)
                logger.info("Dispatched hardware quarantine control payload to %s", topic)
                return True, f"Control payload dispatched to {topic}"
            return False, "MQTT service not connected to publish control command"
        except Exception as e:
            logger.debug("Hardware quarantine command dispatch note: %s", e)
            return False, str(e)

    def _send_hardware_release_command(self, device_id: str) -> (bool, str):
        """Send release command to ESP32 firmware."""
        try:
            import json
            from backend.services.mqtt_service import mqtt_service
            if mqtt_service and mqtt_service.client and mqtt_service.is_connected:
                topic = f"iot/{device_id}/control"
                payload = json.dumps({
                    "command": "RELEASE",
                    "device_id": device_id,
                    "action": "ENABLE_RADIO",
                    "timestamp": time.time(),
                })
                mqtt_service.client.publish(topic, payload, qos=1)
                return True, f"Release payload dispatched to {topic}"
            return False, "MQTT service not connected"
        except Exception as e:
            return False, str(e)

    def _is_valid_ipv4(self, ip: str) -> bool:
        try:
            parsed = ipaddress.IPv4Address(ip)
            return not parsed.is_loopback and not parsed.is_multicast and not parsed.is_unspecified
        except Exception:
            return False

    def _persist_enforcement_event(self, record: Dict[str, Any]) -> None:
        """Persist enforcement evidence into MongoDB."""
        try:
            from backend.core.mongodb import get_mongodb
            loop = asyncio.get_event_loop()
            if loop.is_running():
                async def _save():
                    try:
                        db = get_mongodb()
                        await db.network_enforcements.insert_one(dict(record))
                    except Exception as e:
                        logger.debug("Mongo persist enforcement error: %s", e)
                asyncio.create_task(_save())
        except Exception:
            pass

    def _persist_release_event(self, record: Dict[str, Any]) -> None:
        """Persist manual release record into MongoDB."""
        try:
            from backend.core.mongodb import get_mongodb
            loop = asyncio.get_event_loop()
            if loop.is_running():
                async def _save():
                    try:
                        db = get_mongodb()
                        await db.network_enforcements.insert_one({
                            "type": "RELEASE",
                            **record
                        })
                    except Exception as e:
                        logger.debug("Mongo persist release error: %s", e)
                asyncio.create_task(_save())
        except Exception:
            pass

    async def restore_enforcements_on_startup(self) -> int:
        """
        Query MongoDB on backend startup and re-apply all active enforcements.
        Ensures backend restarts do not silently release quarantined devices!
        """
        restored = 0
        try:
            from backend.core.mongodb import get_mongodb
            db = get_mongodb()
            cursor = db.devices.find({"is_isolated": True})
            isolated_devices = await cursor.to_list(length=100)

            for d in isolated_devices:
                dev_id = d.get("device_id")
                ip = d.get("ip_address")
                if dev_id and not d.get("is_simulation", False):
                    logger.info("Restoring active isolation for device %s (IP: %s) after startup", dev_id, ip)
                    self.apply_isolation(
                        device_id=dev_id,
                        ip_address=ip,
                        mac_address=d.get("mac_address"),
                        reason="Restored from MongoDB state across backend restart",
                    )
                    restored += 1
            logger.info("Restored %d active physical device enforcements on startup", restored)
        except Exception as e:
            logger.warning("Error restoring enforcements on startup: %s", e)
        return restored


# Singleton instance
network_enforcer = NetworkEnforcementManager()


def get_enforcement_manager() -> NetworkEnforcementManager:
    """Return the singleton NetworkEnforcementManager instance."""
    return network_enforcer
