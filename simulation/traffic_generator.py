"""
SecureIoT-X Simulation — Synthetic Traffic Generator & Demo Runner.

Generates realistic IoT traffic events for testing without real hardware.
All events are controlled feature records — no offensive tooling.
"""

import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("secureiot.simulation")


class TrafficGenerator:
    """Generate synthetic IoT traffic events."""

    NORMAL_EVENTS = [
        {"type": "temperature_telemetry", "protocol": "MQTT", "risk": "low"},
        {"type": "humidity_telemetry", "protocol": "MQTT", "risk": "low"},
        {"type": "device_heartbeat", "protocol": "MQTT", "risk": "low"},
        {"type": "mqtt_publish", "protocol": "MQTT", "risk": "low"},
        {"type": "mqtt_subscribe", "protocol": "MQTT", "risk": "low"},
        {"type": "normal_tcp_connection", "protocol": "TCP", "risk": "low"},
    ]

    SUSPICIOUS_EVENTS = [
        {"type": "abnormal_connection_frequency", "protocol": "TCP", "risk": "medium"},
        {"type": "unusual_packet_rate", "protocol": "UDP", "risk": "medium"},
        {"type": "unexpected_protocol", "protocol": "ICMP", "risk": "medium"},
        {"type": "repeated_auth_failure", "protocol": "TCP", "risk": "medium"},
    ]

    ATTACK_EVENTS = [
        {"type": "DDoS", "protocol": "UDP", "risk": "critical", "attack_type": "DDoS"},
        {"type": "port_scan", "protocol": "TCP", "risk": "high", "attack_type": "Reconnaissance"},
        {"type": "brute_force", "protocol": "TCP", "risk": "high", "attack_type": "Brute_Force"},
        {"type": "spoofing", "protocol": "ARP", "risk": "high", "attack_type": "Spoofing"},
        {"type": "DoS_flood", "protocol": "TCP", "risk": "critical", "attack_type": "DoS"},
        {"type": "MITM", "protocol": "TCP", "risk": "critical", "attack_type": "MITM"},
    ]

    DEVICE_IDS = [f"ESP32_{i:03d}" for i in range(1, 11)]

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def generate_normal(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a normal IoT traffic event."""
        template = self.rng.choice(self.NORMAL_EVENTS)
        return self._build_event(template, device_id or self.rng.choice(self.DEVICE_IDS), "Normal")

    def generate_suspicious(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a suspicious traffic event."""
        template = self.rng.choice(self.SUSPICIOUS_EVENTS)
        return self._build_event(template, device_id or self.rng.choice(self.DEVICE_IDS), "Suspicious")

    def generate_attack(self, attack_type: Optional[str] = None, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a controlled attack-pattern traffic event."""
        if attack_type:
            templates = [e for e in self.ATTACK_EVENTS if e.get("attack_type") == attack_type]
            template = templates[0] if templates else self.rng.choice(self.ATTACK_EVENTS)
        else:
            template = self.rng.choice(self.ATTACK_EVENTS)
        return self._build_event(template, device_id or self.rng.choice(self.DEVICE_IDS),
                                 template.get("attack_type", "Unknown"))

    def _build_event(self, template: Dict[str, Any], device_id: str, label: str) -> Dict[str, Any]:
        """Build a complete event record."""
        is_attack = label not in ("Normal", "Suspicious")

        event = {
            "event_id": uuid.uuid4().hex[:16],
            "device_id": device_id,
            "event_type": template["type"],
            "protocol": template["protocol"],
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_ip": f"192.168.1.{self.rng.randint(100, 200)}",
            "dest_ip": f"192.168.1.{self.rng.randint(1, 10)}",
            "source_port": self.rng.randint(1024, 65535),
            "dest_port": self.rng.choice([80, 443, 1883, 8080, 22, 23, 53]),
            # Network features
            "packet_count": self.rng.randint(10, 50000) if is_attack else self.rng.randint(1, 100),
            "byte_count": self.rng.randint(640, 5000000) if is_attack else self.rng.randint(64, 10000),
            "flow_duration": round(self.rng.uniform(0.001, 5.0) if is_attack else self.rng.uniform(0.1, 300.0), 3),
            "fwd_pkts_per_sec": round(self.rng.uniform(500, 5000) if is_attack else self.rng.uniform(1, 50), 2),
            "bwd_pkts_per_sec": round(self.rng.uniform(0, 100), 2),
            # Sensor data (for IoT telemetry)
            "temperature": round(self.rng.uniform(18, 40), 1),
            "humidity": round(self.rng.uniform(30, 90), 1),
            "motion": self.rng.choice([True, False]),
        }

        # Compatible network features for SVM and AI pipeline
        proto_num = 6 if template.get("protocol") == "TCP" else (17 if template.get("protocol") == "UDP" else 1)
        total_p = event["packet_count"]
        fwd_p = int(total_p * (0.8 if is_attack else 0.5))
        bwd_p = max(0, total_p - fwd_p)
        flow_dur = max(event["flow_duration"], 0.001)
        fwd_rate = event["fwd_pkts_per_sec"]
        bwd_rate = event["bwd_pkts_per_sec"]
        flow_rate = fwd_rate + bwd_rate
        fwd_bytes_sec = round((event["byte_count"] * 0.8) / flow_dur, 2)
        bwd_bytes_sec = round((event["byte_count"] * 0.2) / flow_dur, 2)

        event.update({
            "fwd_pkts_tot": fwd_p,
            "bwd_pkts_tot": bwd_p,
            "fwd_data_pkts_tot": int(fwd_p * 0.9),
            "bwd_data_pkts_tot": int(bwd_p * 0.9),
            "flow_pkts_per_sec": flow_rate,
            "fwd_byts_per_sec": fwd_bytes_sec,
            "bwd_byts_per_sec": bwd_bytes_sec,
            "fwd_pkts_payload_avg": round(event["byte_count"] / max(total_p, 1), 2),
            "bwd_pkts_payload_avg": round((event["byte_count"] * 0.2) / max(bwd_p, 1), 2),
            "proto": proto_num,
            "dst_port": event["dest_port"],
            "conn_state_num": 1 if is_attack else 4,
            "packet_rate": round(total_p / flow_dur, 2),
            "fwd_bwd_ratio": round(fwd_p / (bwd_p + 1), 2),
            "total_pkts": total_p,
            "traffic_asymmetry": round((fwd_rate - bwd_rate) / (fwd_rate + bwd_rate + 1e-6), 4),
        })

        return event

    def generate_scenario_sequence(self, scenario: str = "ddos_attack") -> List[Dict[str, Any]]:
        """Generate a predefined scenario sequence."""
        events = []

        if scenario == "normal_operation":
            for _ in range(10):
                events.append(self.generate_normal())

        elif scenario == "suspicious_behavior":
            for _ in range(5):
                events.append(self.generate_normal())
            for _ in range(3):
                events.append(self.generate_suspicious())

        elif scenario == "ddos_attack":
            for _ in range(5):
                events.append(self.generate_normal())
            for _ in range(2):
                events.append(self.generate_suspicious("ESP32_003"))
            events.append(self.generate_attack("DDoS", "ESP32_003"))

        elif scenario == "repeated_malicious":
            for _ in range(3):
                events.append(self.generate_normal())
            for _ in range(4):
                events.append(self.generate_attack(device_id="ESP32_005"))

        elif scenario == "unknown_anomaly":
            for _ in range(8):
                events.append(self.generate_normal())
            event = self.generate_suspicious("ESP32_007")
            event["label"] = "SUSPICIOUS_UNKNOWN"
            event["event_type"] = "unknown_pattern"
            events.append(event)

        elif scenario == "full_demo":
            # Complete demo: normal → suspicious → attack → response cycle
            for _ in range(10):
                events.append(self.generate_normal())
            for _ in range(3):
                events.append(self.generate_suspicious("ESP32_003"))
            events.append(self.generate_attack("DDoS", "ESP32_003"))
            events.append(self.generate_attack("Brute_Force", "ESP32_005"))

        else:
            logger.warning("Unknown scenario: %s, generating normal traffic", scenario)
            for _ in range(5):
                events.append(self.generate_normal())

        return events


# ── Predefined Scenarios ────────────────────────────────────────

DEMO_SCENARIOS = {
    "scenario_1": {
        "name": "Normal IoT Operation",
        "description": "10 normal telemetry events",
        "scenario": "normal_operation",
        "expected": "All events classified NORMAL, risk LOW, action ALLOW",
    },
    "scenario_2": {
        "name": "Suspicious Device Behavior",
        "description": "Normal traffic followed by suspicious patterns",
        "scenario": "suspicious_behavior",
        "expected": "Suspicious events flagged, risk MEDIUM, action MONITOR",
    },
    "scenario_3": {
        "name": "DDoS Pattern Detection",
        "description": "Normal traffic → suspicious → DDoS attack on ESP32_003",
        "scenario": "ddos_attack",
        "expected": "DDoS detected, risk CRITICAL, ESP32_003 ISOLATED, blockchain record",
    },
    "scenario_4": {
        "name": "Repeated Malicious Behavior",
        "description": "Multiple attacks from same device",
        "scenario": "repeated_malicious",
        "expected": "Multiple threats, high risk score, device blocked",
    },
    "scenario_5": {
        "name": "Unknown Anomaly",
        "description": "Unusual traffic not matching known patterns",
        "scenario": "unknown_anomaly",
        "expected": "SUSPICIOUS_UNKNOWN classification, anomaly flagged",
    },
    "scenario_6": {
        "name": "Blockchain Tampering",
        "description": "Verify blockchain integrity, then tamper and detect",
        "scenario": "normal_operation",
        "expected": "Chain valid → tamper block → chain INVALID detected",
    },
    "scenario_7": {
        "name": "Threat Intelligence Sharing",
        "description": "Threat detected, shared across nodes",
        "scenario": "ddos_attack",
        "expected": "NODE-A detects → shares to NODE-B, NODE-C → verified",
    },
    "scenario_8": {
        "name": "Device Disconnect/Reconnect",
        "description": "Device goes offline then reconnects",
        "scenario": "normal_operation",
        "expected": "Device marked OFFLINE → reconnects → status NORMAL",
    },
}
