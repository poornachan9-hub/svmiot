"""
SecureIoT-X ORM Models — Audit Log.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Immutable audit trail for all administrative and security actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Action types: LOGIN, LOGOUT, DEVICE_ISOLATE, DEVICE_RELEASE,
    # MODEL_CHANGED, THREAT_VERIFIED, BLOCKCHAIN_VERIFIED, CONFIG_CHANGED
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # user, device, model, etc.
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog(action={self.action!r}, user={self.user_id!r}, ts={self.timestamp})>"


class ModelRun(Base):
    """Record of ML model training/evaluation runs."""

    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset: Mapped[str] = mapped_column(String(100), nullable=False)
    features_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    # Metrics (JSON)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(nullable=True)
    precision: Mapped[float | None] = mapped_column(nullable=True)
    recall: Mapped[float | None] = mapped_column(nullable=True)
    f1_score: Mapped[float | None] = mapped_column(nullable=True)
    training_time: Mapped[float | None] = mapped_column(nullable=True)  # seconds
    inference_time: Mapped[float | None] = mapped_column(nullable=True)  # ms
    model_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # bytes
    model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preprocessing_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_production: Mapped[bool] = mapped_column(default=False)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    train_test_split: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:
        return f"<ModelRun(model={self.model_name!r}, v={self.model_version!r}, f1={self.f1_score})>"


class SystemLog(Base):
    """Structured system log entry."""

    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(50), nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    def __repr__(self) -> str:
        return f"<SystemLog(level={self.level!r}, service={self.service!r})>"
