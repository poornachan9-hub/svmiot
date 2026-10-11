"""
SecureIoT-X WebSocket Manager.

Handles real-time event broadcasting to connected dashboard clients.
Supports multiple concurrent connections.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("secureiot.websocket")


class WebSocketManager:
    """Manage WebSocket connections and broadcast events to dashboards."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info("WebSocket client connected. Total: %d", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        async with self._lock:
            self._connections.discard(ws)
        logger.info("WebSocket client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send an event to all connected clients."""
        if not self._connections:
            return

        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, default=str)

        stale: List[WebSocket] = []
        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    stale.append(ws)

            for ws in stale:
                self._connections.discard(ws)

    async def send_personal(self, ws: WebSocket, event_type: str, data: Dict[str, Any]) -> None:
        """Send a message to a specific client."""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, default=str)
        try:
            await ws.send_text(message)
        except Exception:
            await self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton instance
ws_manager = WebSocketManager()
