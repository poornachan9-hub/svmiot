"""
SecureIoT-X Security — Risk Engine.

Calculates configurable risk scores from:
- AI confidence, attack severity, frequency, device criticality, anomaly score, threat history
Thresholds loaded from config/security.yaml.
"""

import logging
from typing import Any, Dict, Optional

import yaml
from pathlib import Path

logger = logging.getLogger("secureiot.security.risk")


class RiskEngine:
    """Calculate security risk scores for IoT events."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        if config is None:
            config = self._load_config()
        self.weights = config.get("severity_weights", {
            "ai_confidence": 0.35,
            "attack_severity": 0.25,
            "attack_frequency": 0.15,
            "device_criticality": 0.10,
            "anomaly_score": 0.10,
            "threat_history": 0.05,
        })
        self.thresholds = config.get("risk_thresholds", {
            "low": {"min": 0, "max": 30, "label": "LOW"},
            "medium": {"min": 31, "max": 60, "label": "MEDIUM"},
            "high": {"min": 61, "max": 80, "label": "HIGH"},
            "critical": {"min": 81, "max": 100, "label": "CRITICAL"},
        })
        self.attack_scores = config.get("attack_severity_scores", {
            "Normal": 0, "DoS": 70, "DDoS": 90, "Reconnaissance": 40,
            "Brute_Force": 60, "Spoofing": 50, "MITM": 75, "Unknown": 50,
        })

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        config_path = Path(__file__).resolve().parent.parent / "config" / "security.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def calculate_risk(
        self,
        ai_confidence: float = 0.0,
        attack_type: str = "Normal",
        attack_frequency: int = 1,
        device_criticality: int = 50,
        anomaly_score: float = 0.0,
        threat_history_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Calculate risk score (0-100) from multiple factors.

        Returns: {"risk_score": float, "severity": str, "factors": dict}
        """
        # Normalize factors to 0-100 scale
        conf_score = ai_confidence * 100
        attack_sev = self.attack_scores.get(attack_type, self.attack_scores.get("Unknown", 50))
        freq_score = min(attack_frequency * 10, 100)
        device_score = min(device_criticality, 100)
        anomaly_norm = min(abs(anomaly_score) * 50, 100) if anomaly_score < 0 else 0
        history_score = min(threat_history_count * 15, 100)

        # Weighted sum
        risk_score = (
            self.weights.get("ai_confidence", 0.35) * conf_score +
            self.weights.get("attack_severity", 0.25) * attack_sev +
            self.weights.get("attack_frequency", 0.15) * freq_score +
            self.weights.get("device_criticality", 0.10) * device_score +
            self.weights.get("anomaly_score", 0.10) * anomaly_norm +
            self.weights.get("threat_history", 0.05) * history_score
        )

        # Clamp to 0-100
        risk_score = max(0.0, min(100.0, round(risk_score, 1)))

        # Determine severity
        severity = self.classify_severity(risk_score)

        return {
            "risk_score": risk_score,
            "severity": severity,
            "factors": {
                "ai_confidence": round(conf_score, 1),
                "attack_severity": attack_sev,
                "attack_frequency": round(freq_score, 1),
                "device_criticality": device_score,
                "anomaly_score": round(anomaly_norm, 1),
                "threat_history": round(history_score, 1),
            },
        }

    def classify_severity(self, risk_score: float) -> str:
        """Classify risk score into severity label."""
        for level in ["critical", "high", "medium", "low"]:
            t = self.thresholds.get(level, {})
            if t.get("min", 0) <= risk_score <= t.get("max", 100):
                return t.get("label", level.upper())

        # Default classification
        if risk_score > 80:
            return "CRITICAL"
        elif risk_score > 60:
            return "HIGH"
        elif risk_score > 30:
            return "MEDIUM"
        return "LOW"
