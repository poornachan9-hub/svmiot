"""
SecureIoT-X — MQTT Client.

Provides dual-mode MQTT connectivity:
  1. REAL mode: connects to an actual MQTT broker (Mosquitto / HiveMQ)
  2. SIMULATED mode: internal event loop that mimics MQTT without a broker

All incoming telemetry is fed to:
  AI inference → Risk assessment → Response engine → Blockchain → Dashboard
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("secureiot.mqtt")


# ── Message Model ──────────────────────────────────────────────

@dataclass
class MQTTMessage:
    """Normalized MQTT message."""
    topic: str
    payload: Dict[str, Any]
    device_id: str
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    qos: int = 1
    retain: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "topic": self.topic,
            "device_id": self.device_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "qos": self.qos,
        }


# ── Callbacks ──────────────────────────────────────────────────

MessageCallback = Callable[[MQTTMessage], None]


# ── Simulated MQTT Client ─────────────────────────────────────

class SimulatedMQTTClient:
    """In-memory MQTT broker simulation for development/demo mode."""

    def __init__(self):
        self.connected = False
        self.subscriptions: Dict[str, List[MessageCallback]] = {}
        self.published_messages: List[MQTTMessage] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        logger.info("SimulatedMQTTClient initialized (no broker needed)")

    async def connect(self) -> bool:
        self.connected = True
        logger.info("Simulated MQTT connected")
        return True

    async def disconnect(self) -> None:
        self.connected = False
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Simulated MQTT disconnected")

    def subscribe(self, topic: str, callback: MessageCallback) -> None:
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(callback)
        logger.info("Subscribed to simulated topic: %s", topic)

    async def publish(self, topic: str, payload: Dict[str, Any],
                      device_id: str = "SYSTEM", qos: int = 1) -> MQTTMessage:
        msg = MQTTMessage(topic=topic, payload=payload, device_id=device_id, qos=qos)
        self.published_messages.append(msg)

        # Dispatch to subscribers
        for pattern, callbacks in self.subscriptions.items():
            if self._topic_matches(pattern, topic):
                for cb in callbacks:
                    try:
                        cb(msg)
                    except Exception as e:
                        logger.error("Callback error on %s: %s", topic, e)

        return msg

    async def start_simulation_loop(self, traffic_generator, interval: float = 2.0) -> None:
        """Generate synthetic traffic at regular intervals."""
        self._running = True
        logger.info("Starting simulated traffic loop (%.1fs interval)", interval)

        while self._running:
            try:
                event = traffic_generator.generate_normal()
                await self.publish(
                    topic=f"iot/telemetry/{event['device_id']}",
                    payload=event,
                    device_id=event["device_id"],
                )
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Simulation loop error: %s", e)
                await asyncio.sleep(1)

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """Simple MQTT topic matching with # and + wildcards."""
        if pattern == "#":
            return True
        p_parts = pattern.split("/")
        t_parts = topic.split("/")
        for i, pp in enumerate(p_parts):
            if pp == "#":
                return True
            if i >= len(t_parts):
                return False
            if pp != "+" and pp != t_parts[i]:
                return False
        return len(p_parts) == len(t_parts)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "mode": "simulated",
            "connected": self.connected,
            "subscriptions": list(self.subscriptions.keys()),
            "messages_published": len(self.published_messages),
        }


# ── Real MQTT Client ──────────────────────────────────────────

class RealMQTTClient:
    """Production MQTT client wrapping paho-mqtt."""

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883,
                 username: Optional[str] = None, password: Optional[str] = None,
                 client_id: str = "secureiot-x-server"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.connected = False
        self._callbacks: Dict[str, List[MessageCallback]] = {}
        self._client = None
        logger.info("RealMQTTClient initialized (broker=%s:%d)", broker_host, broker_port)

    async def connect(self) -> bool:
        try:
            import paho.mqtt.client as mqtt

            self._client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
            )

            if self.username:
                self._client.username_pw_set(self.username, self.password)

            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.on_disconnect = self._on_disconnect

            self._client.connect(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()
            self.connected = True
            logger.info("Connected to MQTT broker at %s:%d", self.broker_host, self.broker_port)
            return True

        except Exception as e:
            logger.error("Failed to connect to MQTT broker: %s", e)
            self.connected = False
            return False

    async def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
        self.connected = False
        logger.info("Disconnected from MQTT broker")

    def subscribe(self, topic: str, callback: MessageCallback) -> None:
        if topic not in self._callbacks:
            self._callbacks[topic] = []
        self._callbacks[topic].append(callback)
        if self._client and self.connected:
            self._client.subscribe(topic, qos=1)
        logger.info("Subscribed to real topic: %s", topic)

    async def publish(self, topic: str, payload: Dict[str, Any],
                      device_id: str = "SYSTEM", qos: int = 1) -> MQTTMessage:
        msg = MQTTMessage(topic=topic, payload=payload, device_id=device_id, qos=qos)
        if self._client and self.connected:
            self._client.publish(topic, json.dumps(payload), qos=qos)
        return msg

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        logger.info("MQTT connected with result code: %s", rc)
        self.connected = True
        # Re-subscribe to all topics
        for topic in self._callbacks:
            client.subscribe(topic, qos=1)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            device_id = payload.get("device_id", "unknown")
            mqtt_msg = MQTTMessage(
                topic=msg.topic, payload=payload, device_id=device_id, qos=msg.qos,
            )
            # Dispatch callbacks
            for pattern, callbacks in self._callbacks.items():
                if SimulatedMQTTClient._topic_matches(pattern, msg.topic):
                    for cb in callbacks:
                        try:
                            cb(mqtt_msg)
                        except Exception as e:
                            logger.error("Callback error: %s", e)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON on topic %s", msg.topic)

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.connected = False
        logger.warning("MQTT disconnected (rc=%s), will auto-reconnect", rc)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "mode": "real",
            "connected": self.connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "subscriptions": list(self._callbacks.keys()),
        }


# ── Factory ────────────────────────────────────────────────────

def create_mqtt_client(mode: str = "simulation", **kwargs):
    """Factory to create the appropriate MQTT client."""
    if mode in ("simulation", "full_simulation"):
        return SimulatedMQTTClient()
    elif mode in ("local", "local_development"):
        return RealMQTTClient(
            broker_host=kwargs.get("broker_host", "localhost"),
            broker_port=kwargs.get("broker_port", 1883),
            username=kwargs.get("username"),
            password=kwargs.get("password"),
        )
    elif mode in ("esp32", "real_esp32"):
        return RealMQTTClient(
            broker_host=kwargs.get("broker_host", "localhost"),
            broker_port=kwargs.get("broker_port", 1883),
            username=kwargs.get("username"),
            password=kwargs.get("password"),
            client_id=kwargs.get("client_id", "secureiot-x-esp32"),
        )
    else:
        logger.warning("Unknown MQTT mode '%s', defaulting to simulation", mode)
        return SimulatedMQTTClient()
