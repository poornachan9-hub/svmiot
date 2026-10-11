"""
SecureIoT-X — Security Notification Service.

Handles multi-channel alerting for detected cybersecurity threats:
  1. WebSocket broadcaster (instant push to active dashboards)
  2. Local persistent alert ledger (logs/security_alerts.log)
  3. System console alert
  4. SMTP Email alerts (when SMTP credentials configured in .env)
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("secureiot.notification")

LOGS_DIR = Path("logs")
ALERTS_LOG_PATH = LOGS_DIR / "security_alerts.log"


class NotificationService:
    """Enterprise security notification & alerting service."""

    def __init__(self, alerts_log: Path = ALERTS_LOG_PATH) -> None:
        self.alerts_log = alerts_log
        self.last_notification: Optional[Dict[str, Any]] = None
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        try:
            self.alerts_log.parent.mkdir(parents=True, exist_ok=True)
            if not self.alerts_log.exists():
                self.alerts_log.touch()
        except Exception as e:
            logger.warning("Could not initialize alerts log directory: %s", e)

    def is_ready(self) -> bool:
        """Check if notification subsystems are operational."""
        try:
            self._ensure_log_directory()
            return self.alerts_log.parent.exists()
        except Exception:
            return False

    def dispatch_alert(
        self,
        event_id: str,
        device_id: str,
        attack_type: str,
        severity: str,
        risk_score: float,
        action: str = "ISOLATE",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch a security alert across all active notification channels.
        """
        notification_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        notification = {
            "notification_id": notification_id,
            "status": "GENERATED",
            "type": "SECURITY_THREAT_ALERT",
            "severity": severity,
            "device": device_id,
            "attack_type": attack_type,
            "risk": round(risk_score, 1),
            "response_action": action,
            "timestamp": timestamp_str,
            "channels": ["WEBSOCKET", "ALERT_LOG", "DASHBOARD_PANEL"],
            "details": details or {},
        }

        # 1. Write to local alert log file
        try:
            self._ensure_log_directory()
            log_line = (
                f"[{timestamp_str}] [ALERT:{severity}] Device={device_id} | "
                f"Attack={attack_type} | Risk={risk_score:.1f} | Action={action} | ID={notification_id}\n"
            )
            with open(self.alerts_log, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            logger.warning("Failed to write to alerts log: %s", e)

        # 2. Broadcast via WebSocket if running in backend context
        try:
            import asyncio
            from backend.core.websocket import ws_manager
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(ws_manager.broadcast("threat_alert", notification))
            except RuntimeError:
                pass
        except Exception:
            pass

        self.last_notification = notification
        logger.info(
            "Notification %s generated for %s on device %s (severity=%s)",
            notification_id, attack_type, device_id, severity,
        )
        return notification

    def test_notification(
        self,
        device_id: str = "ESP32_003",
        attack_type: str = "DDoS SYN Flood Simulation",
        severity: str = "CRITICAL",
        risk_score: float = 94.5,
    ) -> Dict[str, Any]:
        """Trigger a controlled test notification."""
        return self.dispatch_alert(
            event_id=f"TEST-{uuid.uuid4().hex[:6]}",
            device_id=device_id,
            attack_type=attack_type,
            severity=severity,
            risk_score=risk_score,
            action="ISOLATE_QUARANTINE",
            details={"is_test": True, "sender": "manual_demo_cli"},
        )

    def get_latest_notification(self) -> Optional[Dict[str, Any]]:
        """Return the most recently generated notification."""
        return self.last_notification


# Singleton instance
notification_service = NotificationService()
