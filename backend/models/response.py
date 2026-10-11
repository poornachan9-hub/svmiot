"""
SecureIoT-X ORM Models — Response Action.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Response(Base):
    """Automated or manual security response action."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    response_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prediction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    threat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Response details
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # ALLOW, MONITOR, ISOLATE, BLOCK
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(20), default="LOW")

    # Execution status
    status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PENDING, EXECUTING, SUCCESS, FAILED
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # SDN integration
    sdn_mode: Mapped[str] = mapped_column(String(20), default="mock")  # mock | real
    sdn_flow_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Blockchain reference
    blockchain_block: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Who triggered
    triggered_by: Mapped[str] = mapped_column(String(50), default="AI_ENGINE")  # AI_ENGINE | ADMIN | ANALYST

    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:
        return f"<Response(id={self.response_id!r}, action={self.action!r}, status={self.status!r})>"
