"""
SecureIoT-X ORM Models — Network Event.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NetworkEvent(Base):
    """Raw network / telemetry event ingested from IoT devices."""

    __tablename__ = "network_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    dest_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    source_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dest_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    packet_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    byte_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flow_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), default="telemetry")
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    def __repr__(self) -> str:
        return f"<NetworkEvent(event_id={self.event_id!r}, device={self.device_id!r})>"
