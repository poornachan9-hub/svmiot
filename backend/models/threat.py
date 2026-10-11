"""
SecureIoT-X ORM Models — Threat Intelligence.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Threat(Base):
    """Threat intelligence record — shared across security nodes."""

    __tablename__ = "threats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    threat_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    attack_type: Mapped[str] = mapped_column(String(100), nullable=False)
    indicator: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Intelligence metadata
    source_node: Mapped[str] = mapped_column(String(50), default="NODE-A")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Blockchain reference
    blockchain_block: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Response taken
    response_action: Mapped[str | None] = mapped_column(String(30), nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:
        return f"<Threat(threat_id={self.threat_id!r}, type={self.attack_type!r})>"
