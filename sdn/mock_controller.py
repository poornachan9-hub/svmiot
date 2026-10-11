"""
SecureIoT-X SDN — Mock Controller.

Provides a simulated SDN interface when Mininet/Ryu is unavailable.
Dashboard clearly shows "SIMULATED RESPONSE MODE".
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger("secureiot.sdn.mock")


class MockSDNController:
    """Simulated SDN controller for development/demo without Mininet."""

    def __init__(self) -> None:
        self.mode = "SIMULATED"
        self._flows: List[Dict[str, Any]] = []

    @property
    def is_real(self) -> bool:
        return False

    def execute_action(self, action: str, device_id: str, **kwargs) -> Dict[str, Any]:
        """Execute a network action (simulated)."""
        flow = {
            "flow_id": f"MOCK_{uuid.uuid4().hex[:8]}",
            "action": action,
            "device_id": device_id,
            "mode": "SIMULATED",
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"[SIMULATED RESPONSE MODE] {action} applied to {device_id}",
        }
        self._flows.append(flow)
        logger.info("[MOCK SDN] %s → %s", action, device_id)
        return flow

    def allow(self, device_id: str) -> Dict[str, Any]:
        return self.execute_action("ALLOW", device_id)

    def block(self, device_id: str) -> Dict[str, Any]:
        return self.execute_action("BLOCK", device_id)

    def isolate(self, device_id: str) -> Dict[str, Any]:
        return self.execute_action("ISOLATE", device_id)

    def reroute(self, device_id: str) -> Dict[str, Any]:
        return self.execute_action("REROUTE", device_id)

    def get_flows(self) -> List[Dict[str, Any]]:
        return self._flows.copy()

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "is_real": False,
            "active_flows": len(self._flows),
            "message": "SDN running in SIMULATED RESPONSE MODE. Install Mininet/Ryu for real SDN.",
        }
