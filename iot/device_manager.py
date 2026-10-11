"""
SecureIoT-X — Device Manager.

Tracks IoT device state: online/offline, isolated, last-seen, threat counts.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("secureiot.devices")


@dataclass
class DeviceState:
    """Runtime state of an IoT device."""
    device_id: str
    device_type: str = "ESP32"
    ip_address: str = "192.168.1.100"
    mac_address: str = "AA:BB:CC:DD:EE:FF"
    is_online: bool = True
    is_isolated: bool = False
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    threat_count: int = 0
    total_events: int = 0
    firmware_version: str = "1.0.0"
    location: str = "Zone-A"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "is_online": self.is_online,
            "is_isolated": self.is_isolated,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "threat_count": self.threat_count,
            "total_events": self.total_events,
            "firmware_version": self.firmware_version,
            "location": self.location,
            "uptime": time.time() - self.first_seen,
        }


class DeviceManager:
    """Manages IoT device inventory and runtime state."""

    # Default demo devices
    DEFAULT_DEVICES = [
        {"device_id": "ESP32_001", "device_type": "Temperature Sensor",      "ip": "192.168.1.101", "location": "Zone-A"},
        {"device_id": "ESP32_002", "device_type": "Motion Sensor",           "ip": "192.168.1.102", "location": "Zone-A"},
        {"device_id": "ESP32_003", "device_type": "Camera Gateway",          "ip": "192.168.1.103", "location": "Zone-B"},
        {"device_id": "ESP32_004", "device_type": "Smart Lock",              "ip": "192.168.1.104", "location": "Zone-B"},
        {"device_id": "ESP32_005", "device_type": "HVAC Controller",         "ip": "192.168.1.105", "location": "Zone-C"},
        {"device_id": "ESP32_006", "device_type": "Light Controller",        "ip": "192.168.1.106", "location": "Zone-C"},
        {"device_id": "ESP32_007", "device_type": "Air Quality Monitor",     "ip": "192.168.1.107", "location": "Zone-D"},
        {"device_id": "ESP32_008", "device_type": "Water Meter",             "ip": "192.168.1.108", "location": "Zone-D"},
        {"device_id": "ESP32_009", "device_type": "Power Monitor",           "ip": "192.168.1.109", "location": "Zone-E"},
        {"device_id": "ESP32_010", "device_type": "Industrial Pump Gateway", "ip": "192.168.1.110", "location": "Zone-E"},
    ]

    def __init__(self, auto_register: bool = True):
        self.devices: Dict[str, DeviceState] = {}
        if auto_register:
            self._register_defaults()
        logger.info("DeviceManager initialized (%d devices)", len(self.devices))

    def _register_defaults(self) -> None:
        for d in self.DEFAULT_DEVICES:
            self.register_device(
                device_id=d["device_id"],
                device_type=d["device_type"],
                ip_address=d["ip"],
                location=d["location"],
            )

    def register_device(self, device_id: str, device_type: str = "ESP32",
                        ip_address: str = "0.0.0.0", **kwargs) -> DeviceState:
        state = DeviceState(
            device_id=device_id,
            device_type=device_type,
            ip_address=ip_address,
            location=kwargs.get("location", "Unknown"),
            firmware_version=kwargs.get("firmware_version", "1.0.0"),
        )
        self.devices[device_id] = state
        return state

    def update_heartbeat(self, device_id: str) -> None:
        if device_id in self.devices:
            self.devices[device_id].last_seen = time.time()
            self.devices[device_id].is_online = True
            self.devices[device_id].total_events += 1

    def isolate_device(self, device_id: str) -> bool:
        if device_id in self.devices:
            self.devices[device_id].is_isolated = True
            self.devices[device_id].threat_count += 1
            logger.warning("Device %s ISOLATED", device_id)
            return True
        return False

    def release_device(self, device_id: str) -> bool:
        if device_id in self.devices:
            self.devices[device_id].is_isolated = False
            logger.info("Device %s released from isolation", device_id)
            return True
        return False

    def get_device(self, device_id: str) -> Optional[DeviceState]:
        return self.devices.get(device_id)

    def get_all_devices(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self.devices.values()]

    def get_online_devices(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self.devices.values() if d.is_online]

    def get_isolated_devices(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self.devices.values() if d.is_isolated]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total": len(self.devices),
            "online": sum(1 for d in self.devices.values() if d.is_online),
            "isolated": sum(1 for d in self.devices.values() if d.is_isolated),
            "offline": sum(1 for d in self.devices.values() if not d.is_online),
            "total_threats": sum(d.threat_count for d in self.devices.values()),
        }
