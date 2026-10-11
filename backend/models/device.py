"""
SecureIoT-X ORM Models — IoT Device.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    """Registered IoT device."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    device_type: Mapped[str] = mapped_column(String(50), default="sensor")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # MQTT status
    mqtt_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Sensor data (latest)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    motion: Mapped[bool] = mapped_column(Boolean, default=False)

    # Security state: PENDING | AUTHORIZED | NORMAL | MONITORING | ISOLATION_PENDING | ISOLATED
    security_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_isolated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Approval workflow
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Criticality (from config)
    criticality: Mapped[int] = mapped_column(Integer, default=50)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def __repr__(self) -> str:
        return f"<Device(device_id={self.device_id!r}, status={self.security_status!r})>"
