"""
SecureIoT-X — Telemetry Handler.

Processes incoming MQTT telemetry through the full security pipeline:
  MQTT message → AI inference → Risk assessment → Response → Blockchain → Dashboard
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional

from iot.mqtt_client import MQTTMessage
from iot.device_manager import DeviceManager
from security.risk_engine import RiskEngine
from security.response_engine import ResponseEngine
from security.event_lifecycle import EventLifecycleManager
from blockchain.chain import SecurityBlockchain

logger = logging.getLogger("secureiot.telemetry")


class TelemetryHandler:
    """Processes IoT telemetry through the complete security pipeline."""

    def __init__(self, blockchain: Optional[SecurityBlockchain] = None,
                 ws_manager=None,
                 device_manager: Optional[DeviceManager] = None):
        self.risk_engine = RiskEngine()
        self.response_engine = ResponseEngine()
        self.lifecycle = EventLifecycleManager()
        self.blockchain = blockchain
        self.ws_manager = ws_manager
        self.device_manager = device_manager or DeviceManager()
        self.prediction_engine = None

        # Statistics
        self.stats = {
            "total_processed": 0,
            "threats_detected": 0,
            "anomalies_detected": 0,
            "events_blocked": 0,
            "devices_isolated": 0,
            "last_event_time": None,
        }

        logger.info("TelemetryHandler initialized")

    def load_ai_engine(self, model_name: Optional[str] = None) -> bool:
        """Load the AI prediction engine (lazy initialization)."""
        try:
            from ai_engine.predict import PredictionEngine
            self.prediction_engine = PredictionEngine(model_name=model_name)
            logger.info("AI prediction engine loaded (model: %s)", self.prediction_engine.model_name)
            return True
        except Exception as e:
            logger.warning("AI engine not available: %s (using rule-based fallback)", e)
            return False

    def process_message(self, msg: MQTTMessage) -> Dict[str, Any]:
        """
        Process a single MQTT telemetry message through the pipeline.

        Pipeline: Parse → Predict → Risk → Response → Blockchain → Dashboard
        """
        self.stats["total_processed"] += 1
        self.stats["last_event_time"] = time.time()
        # Carry event_id from payload if present, else generate
        event_id = msg.payload.get("event_id") or str(uuid.uuid4())[:12]

        result = {
            "event_id": event_id,
            "device_id": msg.device_id,
            "topic": msg.topic,
            "timestamp": msg.timestamp,
        }

        # ── Step 1: AI Prediction ──────────────────────────────
        prediction = self._predict(msg.payload)
        result["prediction"] = prediction

        # ── Step 2: Risk Assessment ────────────────────────────
        packet_count = msg.payload.get("packet_count", 0)
        attack_hint = msg.payload.get("attack_type") or msg.payload.get("label")
        is_major_attack = (
            prediction.get("prediction") in ("DDoS", "DoS", "Mirai", "Ransomware", "Backdoor")
            or attack_hint in ("DDoS", "DoS", "Mirai", "Ransomware", "Backdoor")
            or packet_count > 1000
        )
        anomaly_score = -0.8 if is_major_attack else 0.0
        freq = 3 if is_major_attack else msg.payload.get("attack_frequency", 0)
        dev_crit = 70 if is_major_attack else msg.payload.get("device_criticality", 50)
        effective_attack_type = prediction.get("prediction", "Unknown")
        if effective_attack_type in ("Unknown", "SUSPICIOUS_UNKNOWN", "Normal") and attack_hint:
            effective_attack_type = attack_hint

        risk = self.risk_engine.calculate_risk(
            ai_confidence=prediction.get("confidence", 0.5),
            attack_type=effective_attack_type,
            attack_frequency=freq,
            device_criticality=dev_crit,
            anomaly_score=anomaly_score,
        )
        result["risk"] = risk

        # ── Step 3: Response Decision ──────────────────────────
        response = self.response_engine.decide_response(
            severity=risk["severity"],
            risk_score=risk["risk_score"],
            event_id=event_id,
            device_id=msg.device_id,
            attack_type=effective_attack_type,
        )
        result["response"] = response

        # ── Step 4: Execute Response ───────────────────────────
        if risk["severity"] in ("HIGH", "CRITICAL"):
            executed = self.response_engine.execute_response(response)
            result["execution"] = executed
            self.stats["threats_detected"] += 1

            if executed.get("action") in ("ISOLATE", "BLOCK"):
                self.device_manager.isolate_device(msg.device_id)
                result["device_isolated"] = True
                logger.warning("Device %s ISOLATED via DeviceManager", msg.device_id)
                self.stats["devices_isolated"] += 1
            if executed.get("action") == "BLOCK":
                self.stats["events_blocked"] += 1

        # ── Step 5: Blockchain Record ──────────────────────────
        if self.blockchain and risk["severity"] in ("HIGH", "CRITICAL"):
            try:
                block = self.blockchain.record_event(
                    event_id=event_id,
                    device_id=msg.device_id,
                    attack_type=prediction.get("prediction", "Unknown"),
                    severity=risk["severity"],
                    risk_score=risk["risk_score"],
                    action=response["action"],
                )
                result["blockchain_block"] = block.index
                logger.info("Threat recorded in blockchain: block #%d", block.index)
            except Exception as e:
                logger.error("Blockchain record failed: %s", e)

        # ── Step 6: Lifecycle Tracking ─────────────────────────
        sec_event = self.lifecycle.process_full_lifecycle(
            device_id=msg.device_id,
            prediction=prediction,
            risk=risk,
            response=response,
            blockchain_block=result.get("blockchain_block"),
        )
        result["lifecycle_state"] = sec_event.state

        # Log severity-based
        if risk["severity"] == "CRITICAL":
            logger.critical("CRITICAL: %s on %s (risk=%.1f)",
                          prediction.get("prediction"), msg.device_id, risk["risk_score"])
        elif risk["severity"] == "HIGH":
            logger.warning("HIGH: %s on %s (risk=%.1f)",
                         prediction.get("prediction"), msg.device_id, risk["risk_score"])

        # ── Step 7: Dashboard push ─────────────────────────────
        if self.ws_manager and risk["severity"] in ("HIGH", "CRITICAL"):
            try:
                import asyncio
                asyncio.get_event_loop().create_task(
                    self.ws_manager.broadcast({"type": "security_event", "data": result})
                )
            except Exception:
                pass  # Dashboard push is best-effort

        return result

    def _predict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run AI prediction or fall back to rule-based."""
        has_network_features = any(k in payload for k in (
            "flow_duration", "fwd_pkts_tot", "bwd_pkts_tot", "fwd_pkts_per_sec",
            "packet_rate", "proto", "dst_port", "flow_pkts_per_sec"
        ))
        if has_network_features and self.prediction_engine and self.prediction_engine.is_loaded:
            try:
                pred = self.prediction_engine.predict(
                    payload,
                    device_id=payload.get("device_id", "unknown"),
                )
                if pred.get("prediction") != "SUSPICIOUS_UNKNOWN":
                    return pred
            except Exception as e:
                logger.warning("AI prediction failed: %s, using fallback", e)

        # Rule-based fallback
        return self._rule_based_prediction(payload)

    @staticmethod
    def _rule_based_prediction(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simple rule-based classification fallback."""
        label = payload.get("label") or payload.get("attack_type", "Normal")
        event_type = payload.get("event_type", "")

        if label not in ("Normal", "normal", "NORMAL"):
            return {
                "prediction": label,
                "confidence": 0.85,
                "model_name": "rule_based",
                "is_anomaly": True,
            }

        # Check for suspicious patterns
        packet_count = payload.get("packet_count", 0)
        if packet_count > 5000:
            return {
                "prediction": "Suspicious_High_Traffic",
                "confidence": 0.65,
                "model_name": "rule_based",
                "is_anomaly": True,
            }

        return {
            "prediction": "Normal",
            "confidence": 0.15,
            "model_name": "rule_based",
            "is_anomaly": False,
        }

    def release_device(self, device_id: str) -> bool:
        """Release a device from isolation."""
        released = self.device_manager.release_device(device_id)
        if released:
            logger.info("Device %s released from isolation", device_id)
        return released

    def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current device state."""
        dev = self.device_manager.get_device(device_id)
        return dev.to_dict() if dev else None

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "total_events": self.stats["total_processed"],
            "attacks_detected": self.stats["threats_detected"],
            "ai_engine_loaded": self.prediction_engine is not None,
            "device_summary": self.device_manager.get_summary(),
        }
