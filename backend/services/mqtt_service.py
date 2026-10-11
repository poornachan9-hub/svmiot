"""
SecureIoT-X — MQTT Ingestion Service.

Manages the background MQTT connection to the Mosquitto broker.
Subscribes to external and simulated device topics:
  - iot/{device_id}/telemetry
  - iot/{device_id}/status
  - iot/{device_id}/heartbeat
  - iot/{device_id}/security

Enforces:
  1. Device identity validation against MongoDB device registry.
  2. Anti-spoofing / anti-impersonation checks (topic device_id vs payload device_id).
  3. Device isolation containment (quarantine enforcement).
  4. Message de-duplication and malformed payload protection.
  5. Telemetry persistence in MongoDB and real-time dashboard WebSocket broadcast.
"""

import asyncio
import json
import logging
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from backend.core.config import settings
from backend.core.mongodb import get_mongodb
from backend.core.websocket import ws_manager
from iot.mqtt_client import MQTTMessage, RealMQTTClient, SimulatedMQTTClient

logger = logging.getLogger("secureiot.mqtt_service")


class MQTTIngestionService:
    """Production MQTT service bridging Mosquitto and SecureIoT-X backend."""

    def __init__(self):
        self.client: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running: bool = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._dedup_cache: OrderedDict[str, float] = OrderedDict()  # key -> timestamp
        self._dedup_max_size: int = 1000
        self._dedup_ttl_seconds: float = 10.0

        # Performance & telemetry statistics
        self.stats = {
            "connected": False,
            "broker": f"{settings.mqtt_host}:{settings.mqtt_port}",
            "messages_received": 0,
            "telemetry_processed": 0,
            "status_updates": 0,
            "heartbeats": 0,
            "security_events": 0,
            "rejected_unregistered": 0,
            "rejected_spoofed": 0,
            "rejected_isolated": 0,
            "rejected_malformed": 0,
            "rejected_duplicate": 0,
            "last_message_time": None,
        }

    async def start(self) -> None:
        """Initialize and connect the MQTT client in background."""
        if self._running:
            return

        self._running = True
        self._loop = asyncio.get_running_loop()

        # Instantiate RealMQTTClient pointing to configured broker
        self.client = RealMQTTClient(
            broker_host=settings.mqtt_host,
            broker_port=settings.mqtt_port,
            username=settings.mqtt_username or None,
            password=settings.mqtt_password or None,
            client_id=f"secureiot-backend-{uuid.uuid4().hex[:6]}",
        )

        # Register subscriptions
        self.client.subscribe("iot/+/telemetry", self._on_message_sync)
        self.client.subscribe("iot/+/status", self._on_message_sync)
        self.client.subscribe("iot/+/heartbeat", self._on_message_sync)
        self.client.subscribe("iot/+/security", self._on_message_sync)

        # Attempt initial connection in background
        self._reconnect_task = asyncio.create_task(self._connection_loop())
        logger.info("MQTT Ingestion Service started (broker: %s:%d)", settings.mqtt_host, settings.mqtt_port)

    async def stop(self) -> None:
        """Gracefully disconnect and shut down MQTT ingestion."""
        self._running = False
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        if self.client:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.warning("Error disconnecting MQTT client: %s", e)

        self.stats["connected"] = False
        logger.info("MQTT Ingestion Service stopped")

    async def _connection_loop(self) -> None:
        """Background loop ensuring continuous connection to MQTT broker."""
        retry_delay = 3
        while self._running:
            if not self.client.connected:
                try:
                    logger.info("Connecting to MQTT broker at %s:%d...", settings.mqtt_host, settings.mqtt_port)
                    connected = await self.client.connect()
                    if connected:
                        self.stats["connected"] = True
                        logger.info("Successfully connected to Mosquitto MQTT broker")
                        retry_delay = 3
                    else:
                        self.stats["connected"] = False
                        logger.warning("Could not reach MQTT broker at %s:%d. Will retry in %ds",
                                       settings.mqtt_host, settings.mqtt_port, retry_delay)
                except Exception as e:
                    self.stats["connected"] = False
                    logger.warning("MQTT connection attempt failed: %s. Will retry in %ds", e, retry_delay)

            await asyncio.sleep(retry_delay)
            # Exponential backoff capped at 30 seconds
            if not self.client or not self.client.connected:
                retry_delay = min(retry_delay * 2, 30)

    def _on_message_sync(self, msg: MQTTMessage) -> None:
        """Synchronous callback dispatched by Paho MQTT thread; schedules on asyncio loop."""
        if not self._running or not self._loop or self._loop.is_closed():
            return

        asyncio.run_coroutine_threadsafe(self._handle_message_async(msg), self._loop)

    async def _handle_message_async(self, msg: MQTTMessage) -> None:
        """Asynchronously validate and process an incoming MQTT message."""
        self.stats["messages_received"] += 1
        self.stats["last_message_time"] = time.time()

        # 1. Parse topic structure: iot/{device_id}/{subtopic}
        parts = msg.topic.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "iot":
            logger.warning("Ignored message on non-standard topic: %s", msg.topic)
            self.stats["rejected_malformed"] += 1
            return

        topic_device_id, subtopic = parts[1], parts[2]
        payload = msg.payload

        if not isinstance(payload, dict):
            logger.warning("Malformed non-dict payload on topic %s", msg.topic)
            self.stats["rejected_malformed"] += 1
            return

        # 2. Anti-spoofing check: device_id in payload must match topic device_id if present
        payload_device_id = payload.get("device_id")
        if payload_device_id and str(payload_device_id) != topic_device_id:
            logger.warning(
                "Spoofing attempt detected! Topic device_id '%s' != payload device_id '%s'. Message dropped.",
                topic_device_id, payload_device_id
            )
            self.stats["rejected_spoofed"] += 1
            return

        # 3. Message de-duplication check
        msg_key = f"{topic_device_id}:{payload.get('message_id', payload.get('timestamp', time.time()))}"
        if self._is_duplicate(msg_key):
            logger.debug("Duplicate MQTT message dropped: %s", msg_key)
            self.stats["rejected_duplicate"] += 1
            return

        # 4. Device registration check against MongoDB
        db = get_mongodb()
        device = await db.devices.find_one({"device_id": topic_device_id})
        if not device:
            logger.warning(
                "Unauthorized unregistered device '%s' attempted to publish to %s. Message rejected.",
                topic_device_id, msg.topic
            )
            self.stats["rejected_unregistered"] += 1
            return

        # 5. Quarantine / Isolation containment enforcement
        from security.network_enforcer import network_enforcer
        client_ip = payload.get("ip_address") or (device.get("ip_address") if device else None)
        if device.get("is_isolated", False) or network_enforcer.is_device_blocked(topic_device_id) or network_enforcer.is_ip_blocked(client_ip):
            logger.warning("Device '%s' (IP: %s) is ISOLATED — message dropped by NetworkEnforcer.", topic_device_id, client_ip)
            self.stats["rejected_isolated"] += 1
            await ws_manager.broadcast("device_event_quarantined", {
                "device_id": topic_device_id,
                "topic": msg.topic,
                "reason": "Device is in active physical quarantine / isolation state",
                "enforcement": "NETWORK_ENFORCER_DROP",
            })
            return

        # 6. Route by subtopic
        now_dt = datetime.now(timezone.utc)
        now_ts = time.time()

        if subtopic == "telemetry":
            await self._process_telemetry(db, topic_device_id, payload, now_dt, now_ts)
        elif subtopic == "status":
            await self._process_status(db, topic_device_id, payload, now_ts)
        elif subtopic == "heartbeat":
            await self._process_heartbeat(db, topic_device_id, now_ts)
        elif subtopic == "security":
            await self._process_security_event(db, topic_device_id, payload, now_dt, now_ts)
        else:
            logger.debug("Unhandled subtopic '%s' for device %s", subtopic, topic_device_id)

    async def _process_telemetry(self, db, device_id: str, payload: Dict[str, Any],
                                 now_dt: datetime, now_ts: float) -> None:
        """Process valid sensor telemetry and persist into MongoDB."""
        self.stats["telemetry_processed"] += 1

        # Sanitize sensor values
        temp = self._sanitize_float(payload.get("temperature"), -50.0, 150.0)
        humidity = self._sanitize_float(payload.get("humidity"), 0.0, 100.0)
        motion = bool(payload.get("motion")) if "motion" in payload else None
        rssi = self._sanitize_float(payload.get("rssi"), -120.0, 0.0)
        uptime = self._sanitize_float(payload.get("uptime"), 0.0, 1e9)

        # Store telemetry record in MongoDB `telemetry` collection
        telemetry_doc = {
            "telemetry_id": str(uuid.uuid4())[:16],
            "device_id": device_id,
            "temperature": temp,
            "humidity": humidity,
            "motion": motion,
            "rssi": rssi,
            "uptime": uptime,
            "raw_data": payload,
            "timestamp": now_dt,
        }
        await db.telemetry.insert_one(telemetry_doc)

        # Update latest device state in `devices` collection
        update_fields: Dict[str, Any] = {
            "last_seen": now_ts,
            "is_online": True,
            "mqtt_connected": True,
        }
        if temp is not None:
            update_fields["temperature"] = temp
        if humidity is not None:
            update_fields["humidity"] = humidity
        if motion is not None:
            update_fields["motion"] = motion

        await db.devices.update_one(
            {"device_id": device_id},
            {"$set": update_fields, "$inc": {"total_events": 1}}
        )

        # Real-time WebSocket push to frontend
        await ws_manager.broadcast("telemetry_update", {
            "device_id": device_id,
            "temperature": temp,
            "humidity": humidity,
            "motion": motion,
            "rssi": rssi,
            "last_seen": now_ts,
            "is_online": True,
        })
        logger.debug("Ingested telemetry for device %s: temp=%s, hum=%s", device_id, temp, humidity)

    async def _process_status(self, db, device_id: str, payload: Dict[str, Any], now_ts: float) -> None:
        """Process connection status updates (e.g., LWT messages)."""
        self.stats["status_updates"] += 1
        status_str = str(payload.get("status", "online")).lower()
        is_online = status_str not in ("offline", "disconnected", "dead")

        await db.devices.update_one(
            {"device_id": device_id},
            {"$set": {
                "is_online": is_online,
                "mqtt_connected": is_online,
                "last_seen": now_ts,
            }}
        )

        await ws_manager.broadcast("device_status", {
            "device_id": device_id,
            "status": "online" if is_online else "offline",
            "is_online": is_online,
            "last_seen": now_ts,
        })
        logger.info("Device %s status updated: %s", device_id, "ONLINE" if is_online else "OFFLINE")

    async def _process_heartbeat(self, db, device_id: str, now_ts: float) -> None:
        """Process heartbeat beacon."""
        self.stats["heartbeats"] += 1
        await db.devices.update_one(
            {"device_id": device_id},
            {"$set": {
                "last_seen": now_ts,
                "is_online": True,
                "mqtt_connected": True,
            }}
        )
        logger.debug("Heartbeat received from device %s", device_id)

    async def _process_security_event(self, db, device_id: str, payload: Dict[str, Any],
                                      now_dt: datetime, now_ts: float) -> None:
        """Forward external device security event into the detection and response pipeline."""
        self.stats["security_events"] += 1
        logger.info("External device security event received from %s", device_id)

        # Ensure event_id is preserved or generated
        event_id = payload.get("event_id") or uuid.uuid4().hex[:16]

        try:
            from iot.telemetry_handler import TelemetryHandler
            from blockchain.ganache_client import get_ganache_client
            # Instantiate or invoke TelemetryHandler
            handler = TelemetryHandler(blockchain=None, ws_manager=ws_manager)
            handler.load_ai_engine()

            msg = MQTTMessage(
                topic=f"iot/{device_id}/security",
                payload=payload,
                device_id=device_id,
                timestamp=now_ts,
                message_id=event_id,
            )
            # Run processing
            result = handler.process_message(msg)

            # If qualifying HIGH/CRITICAL, record on Ganache and dispatch Telegram
            severity = result.get("risk", {}).get("severity", "LOW")
            action = result.get("response", {}).get("action", "ALLOW")
            predicted_label = result.get("prediction", {}).get("prediction", "Unknown")
            risk_score = result.get("risk", {}).get("risk_score", 0.0)

            tx_hash = None
            block_number = None

            if severity in ("HIGH", "CRITICAL"):
                # 1. Real Ganache transaction
                try:
                    ganache = get_ganache_client()
                    if ganache.is_connected():
                        bc_record = ganache.record_security_event({
                            "event_id": event_id,
                            "device_id": device_id,
                            "attack_type": predicted_label,
                            "risk_score": risk_score,
                            "action": action,
                            "severity": severity,
                            "timestamp": now_dt.isoformat(),
                        })
                        tx_hash = bc_record.get("tx_hash")
                        block_number = bc_record.get("block_number")

                        # Store in MongoDB blockchain_records
                        await db.blockchain_records.insert_one({
                            "event_id": event_id,
                            "device_id": device_id,
                            "tx_hash": tx_hash,
                            "block_number": block_number,
                            "block_hash": bc_record.get("block_hash"),
                            "event_hash": bc_record.get("event_hash"),
                            "status": bc_record.get("status"),
                            "gas_used": bc_record.get("gas_used"),
                            "chain_id": bc_record.get("chain_id"),
                            "timestamp": now_dt,
                        })
                except Exception as _bce:
                    logger.warning("Ganache recording error for external security event: %s", _bce)

                # 2. Isolate device in NetworkEnforcer & MongoDB
                if action in ("ISOLATE", "BLOCK"):
                    from security.network_enforcer import network_enforcer
                    device_doc = await db.devices.find_one({"device_id": device_id})
                    client_ip = payload.get("ip_address") or (device_doc.get("ip_address") if device_doc else None)
                    client_mac = payload.get("mac_address") or (device_doc.get("mac_address") if device_doc else None)
                    enf_rec = network_enforcer.apply_isolation(
                        device_id=device_id,
                        ip_address=client_ip,
                        mac_address=client_mac,
                        event_id=event_id,
                        reason=f"Security event {predicted_label} classified as {severity}",
                    )
                    enf_status = enf_rec.get("status", "ISOLATION_APPLIED")
                    enf_mech = ", ".join(enf_rec.get("tiers_applied", ["TRANSPORT_FILTER"]))

                    await db.devices.update_one(
                        {"device_id": device_id},
                        {"$set": {
                            "is_isolated": True,
                            "security_status": "ISOLATED",
                            "enforcement_status": enf_status,
                            "enforcement_mechanism": enf_mech,
                            "enforcement_evidence": enf_rec.get("evidence", {}),
                            "last_seen": now_ts,
                        }, "$inc": {"threat_count": 1, "total_events": 1}}
                    )
                    await db.isolation_events.insert_one({
                        "event_id": event_id,
                        "device_id": device_id,
                        "action": "ISOLATE",
                        "attack_type": predicted_label,
                        "risk_score": risk_score,
                        "severity": severity,
                        "enforcement_status": enf_status,
                        "enforcement_id": enf_rec.get("enforcement_id"),
                        "timestamp": now_dt,
                    })

                # 3. Telegram alert
                try:
                    from security.telegram_service import send_security_alert
                    await send_security_alert(
                        event_id=event_id,
                        device_id=device_id,
                        attack_type=payload.get("attack_type", predicted_label),
                        prediction=predicted_label,
                        risk_score=round(risk_score, 2),
                        severity=severity,
                        action=action,
                        is_isolated=True,
                        tx_hash=tx_hash,
                        block_number=block_number,
                        timestamp=now_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    )
                except Exception as _tge:
                    logger.warning("Telegram alert failed: %s", _tge)

            # Store security event in MongoDB attack_events
            await db.attack_events.insert_one({
                "event_id": event_id,
                "device_id": device_id,
                "attack_type": payload.get("attack_type", predicted_label),
                "predicted_attack": predicted_label,
                "confidence": result.get("prediction", {}).get("confidence", 0.0),
                "model": result.get("prediction", {}).get("model", "SVM"),
                "risk_score": risk_score,
                "severity": severity,
                "action": action,
                "tx_hash": tx_hash,
                "block_number": block_number,
                "timestamp": now_dt,
            })

            # Store prediction in MongoDB predictions
            pred_info = result.get("prediction", {})
            await db.predictions.insert_one({
                "prediction_id": uuid.uuid4().hex[:16],
                "event_id": event_id,
                "device_id": device_id,
                "prediction": predicted_label,
                "confidence": pred_info.get("confidence", 0.0),
                "model": pred_info.get("model", "SVM"),
                "model_version": pred_info.get("model_version", "v1"),
                "risk_score": risk_score,
                "severity": severity,
                "recommended_action": action,
                "timestamp": now_dt,
            })

            # Store risk score in MongoDB risk_scores
            risk_info = result.get("risk", {})
            await db.risk_scores.insert_one({
                "event_id": event_id,
                "device_id": device_id,
                "risk_score": risk_score,
                "severity": severity,
                "factors": risk_info.get("factors", {}),
                "timestamp": now_dt,
            })

            # Store response action in MongoDB response_actions
            resp_info = result.get("response", {})
            await db.response_actions.insert_one({
                "response_id": uuid.uuid4().hex[:16],
                "event_id": event_id,
                "device_id": device_id,
                "action": action,
                "reason": resp_info.get("reason", ""),
                "risk_score": risk_score,
                "severity": severity,
                "status": "EXECUTED" if severity in ("HIGH", "CRITICAL") else "LOGGED",
                "timestamp": now_dt,
            })

            # Real-time WebSocket broadcast to dashboard
            await ws_manager.broadcast("security_event", {
                "event_id": event_id,
                "device_id": device_id,
                "attack_type": payload.get("attack_type", predicted_label),
                "prediction": predicted_label,
                "confidence": pred_info.get("confidence", 0.0),
                "risk_score": risk_score,
                "severity": severity,
                "action": action,
                "is_isolated": action in ("ISOLATE", "BLOCK") and severity in ("HIGH", "CRITICAL"),
                "tx_hash": tx_hash,
                "block_number": block_number,
                "timestamp": now_dt.isoformat(),
            })

        except Exception as e:
            logger.error("Error processing security event from %s: %s", device_id, e)

    def _is_duplicate(self, key: str) -> bool:
        """Check and update LRU de-duplication cache."""
        now = time.time()
        # Evict expired entries
        while self._dedup_cache and (now - next(iter(self._dedup_cache.values()))) > self._dedup_ttl_seconds:
            self._dedup_cache.popitem(last=False)

        if key in self._dedup_cache:
            return True

        self._dedup_cache[key] = now
        if len(self._dedup_cache) > self._dedup_max_size:
            self._dedup_cache.popitem(last=False)
        return False

    @staticmethod
    def _sanitize_float(val: Any, min_val: float, max_val: float) -> Optional[float]:
        """Convert and clamp numeric value within reasonable bounds."""
        if val is None:
            return None
        try:
            f = float(val)
            if min_val <= f <= max_val:
                return round(f, 2)
            logger.warning("Value %s outside valid range [%s, %s]", f, min_val, max_val)
            return None
        except (ValueError, TypeError):
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get live health and statistics for the MQTT ingestion service."""
        is_conn = bool(self.client and self.client.connected)
        self.stats["connected"] = is_conn
        return {
            "status": "CONNECTED" if is_conn else "NOT CONNECTED",
            **self.stats,
        }


# Singleton service instance
mqtt_service = MQTTIngestionService()
