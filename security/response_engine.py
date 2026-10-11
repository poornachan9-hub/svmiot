"""
SecureIoT-X Security — Response Engine.

Automated response decisions based on risk level:
  LOW → ALLOW | MEDIUM → MONITOR | HIGH → ISOLATE | CRITICAL → ISOLATE+ALERT+BLOCK

Every response creates an event record.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import yaml
from pathlib import Path

logger = logging.getLogger("secureiot.security.response")


class ResponseEngine:
    """Decide and execute security responses based on risk assessment."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        if config is None:
            config = self._load_config()
        self.rules = config.get("response_rules", {
            "LOW": "ALLOW",
            "MEDIUM": "MONITOR",
            "HIGH": "ISOLATE",
            "CRITICAL": "ISOLATE_ALERT_BLOCK",
        })

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        config_path = Path(__file__).resolve().parent.parent / "config" / "security.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def decide_response(
        self,
        severity: str,
        risk_score: float,
        event_id: str,
        device_id: str,
        attack_type: str = "Unknown",
        prediction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decide the appropriate response action.

        Returns a response record ready for execution and logging.
        """
        action_str = self.rules.get(severity, "MONITOR")

        # Parse compound actions
        actions = action_str.split("_")
        primary_action = actions[0]  # ALLOW, MONITOR, ISOLATE, BLOCK
        should_alert = "ALERT" in actions
        should_block = "BLOCK" in actions

        response = {
            "response_id": uuid.uuid4().hex[:16],
            "event_id": event_id,
            "prediction_id": prediction_id,
            "device_id": device_id,
            "action": primary_action,
            "reason": f"{severity}_RISK_{attack_type}",
            "risk_score": risk_score,
            "severity": severity,
            "should_alert": should_alert,
            "should_block": should_block,
            "status": "PENDING",
            "triggered_by": "AI_ENGINE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("Response decision: %s for device=%s (risk=%.1f, severity=%s)",
                     primary_action, device_id, risk_score, severity)

        return response

    def execute_response(
        self,
        response: Dict[str, Any],
        sdn_controller: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute a response decision.

        Uses SDN controller if available, otherwise simulates.
        """
        action = response["action"]
        device_id = response["device_id"]

        try:
            if sdn_controller:
                result = sdn_controller.execute_action(action, device_id)
                response["sdn_mode"] = "real"
                response["sdn_flow_id"] = result.get("flow_id")
            else:
                # Simulated execution
                result = self._simulate_execution(action, device_id)
                response["sdn_mode"] = "mock"

            # Multi-tier Network Enforcement hook
            if action in ("ISOLATE", "BLOCK"):
                try:
                    from security.network_enforcer import get_enforcement_manager
                    enforcer = get_enforcement_manager()
                    enf_res = enforcer.apply_isolation(
                        device_id=device_id,
                        reason=response.get("reason", "AUTOMATED_RESPONSE"),
                    )
                    response["network_enforcement"] = enf_res
                except Exception as enf_err:
                    logger.warning("Network enforcer hook encountered non-fatal error: %s", enf_err)
            elif action in ("ALLOW", "RELEASE"):
                try:
                    from security.network_enforcer import get_enforcement_manager
                    enforcer = get_enforcement_manager()
                    if enforcer.is_device_blocked(device_id):
                        enforcer.remove_isolation(device_id)
                except Exception as enf_err:
                    logger.warning("Network enforcer release hook encountered non-fatal error: %s", enf_err)

            response["status"] = "SUCCESS"
            response["success"] = True
            response["executed_at"] = datetime.now(timezone.utc).isoformat()

            logger.info("Response executed: %s on %s — %s (%s mode)",
                        action, device_id, response["status"], response["sdn_mode"])

        except Exception as e:
            response["status"] = "FAILED"
            response["success"] = False
            response["error_message"] = str(e)
            logger.error("Response execution failed: %s on %s — %s", action, device_id, e)

        return response

    @staticmethod
    def _simulate_execution(action: str, device_id: str) -> Dict[str, Any]:
        """Simulate response execution (mock SDN mode)."""
        return {
            "action": action,
            "device_id": device_id,
            "mode": "SIMULATED",
            "flow_id": f"SIM_{uuid.uuid4().hex[:8]}",
            "message": f"[SIMULATED] {action} applied to {device_id}",
        }
