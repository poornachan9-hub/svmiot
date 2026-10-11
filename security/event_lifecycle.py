"""
SecureIoT-X Security — Event Lifecycle State Machine.

DETECTED → ANALYZING → CLASSIFIED → RISK_ASSESSED → RESPONSE_PENDING
→ RESPONSE_EXECUTED → LOGGED → VERIFIED → RESOLVED

Each stage has a timestamp.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("secureiot.security.lifecycle")


LIFECYCLE_STATES = [
    "DETECTED",
    "ANALYZING",
    "CLASSIFIED",
    "RISK_ASSESSED",
    "RESPONSE_PENDING",
    "RESPONSE_EXECUTED",
    "LOGGED",
    "VERIFIED",
    "RESOLVED",
]


class SecurityEvent:
    """
    Security event with full lifecycle tracking.
    Timestamps are recorded for each state transition.
    """

    def __init__(self, event_id: Optional[str] = None, device_id: str = "unknown") -> None:
        self.event_id = event_id or uuid.uuid4().hex[:16]
        self.device_id = device_id
        self.state = "DETECTED"
        self.timestamps: Dict[str, str] = {
            "DETECTED": datetime.now(timezone.utc).isoformat(),
        }
        self.data: Dict[str, Any] = {}

    def transition(self, new_state: str) -> bool:
        """Transition to a new state. Returns False if transition is invalid."""
        if new_state not in LIFECYCLE_STATES:
            logger.error("Invalid state: %s", new_state)
            return False

        current_idx = LIFECYCLE_STATES.index(self.state)
        new_idx = LIFECYCLE_STATES.index(new_state)

        if new_idx <= current_idx:
            logger.warning("Cannot transition backwards: %s → %s", self.state, new_state)
            return False

        self.state = new_state
        self.timestamps[new_state] = datetime.now(timezone.utc).isoformat()
        logger.debug("Event %s: %s → %s", self.event_id, LIFECYCLE_STATES[current_idx], new_state)
        return True

    def set_data(self, key: str, value: Any) -> None:
        """Attach data to this event."""
        self.data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "device_id": self.device_id,
            "state": self.state,
            "timestamps": self.timestamps,
            "data": self.data,
        }

    @property
    def is_resolved(self) -> bool:
        return self.state == "RESOLVED"

    def __repr__(self) -> str:
        return f"<SecurityEvent({self.event_id}, state={self.state})>"


class EventLifecycleManager:
    """Manage multiple security events through their lifecycle."""

    def __init__(self) -> None:
        self._events: Dict[str, SecurityEvent] = {}

    def create_event(self, device_id: str) -> SecurityEvent:
        """Create a new security event."""
        event = SecurityEvent(device_id=device_id)
        self._events[event.event_id] = event
        return event

    def get_event(self, event_id: str) -> Optional[SecurityEvent]:
        return self._events.get(event_id)

    def transition_event(self, event_id: str, new_state: str) -> bool:
        event = self._events.get(event_id)
        if event is None:
            logger.warning("Event not found: %s", event_id)
            return False
        return event.transition(new_state)

    def get_active_events(self) -> List[Dict[str, Any]]:
        """Get all non-resolved events."""
        return [e.to_dict() for e in self._events.values() if not e.is_resolved]

    def get_all_events(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._events.values()]

    def process_full_lifecycle(
        self,
        device_id: str,
        prediction: Dict[str, Any],
        risk: Dict[str, Any],
        response: Dict[str, Any],
        blockchain_block: Optional[int] = None,
    ) -> SecurityEvent:
        """Process an event through its complete lifecycle in one call."""
        event = self.create_event(device_id)

        # ANALYZING
        event.transition("ANALYZING")
        event.set_data("raw_event", prediction.get("event_id"))

        # CLASSIFIED
        event.transition("CLASSIFIED")
        event.set_data("prediction", prediction.get("prediction"))
        event.set_data("confidence", prediction.get("confidence"))
        event.set_data("model", prediction.get("model_name"))

        # RISK_ASSESSED
        event.transition("RISK_ASSESSED")
        event.set_data("risk_score", risk.get("risk_score"))
        event.set_data("severity", risk.get("severity"))

        # RESPONSE_PENDING
        event.transition("RESPONSE_PENDING")
        event.set_data("recommended_action", response.get("action"))

        # RESPONSE_EXECUTED
        event.transition("RESPONSE_EXECUTED")
        event.set_data("action", response.get("action"))
        event.set_data("response_status", response.get("status"))

        # LOGGED
        event.transition("LOGGED")
        if blockchain_block is not None:
            event.set_data("blockchain_block", blockchain_block)

        # VERIFIED
        event.transition("VERIFIED")

        return event
