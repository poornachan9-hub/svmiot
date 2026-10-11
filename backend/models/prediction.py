"""
SecureIoT-X ORM Models — AI Prediction.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Prediction(Base):
    """AI model prediction result for a network event."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # AI result
    prediction: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(20), default="LOW")
    recommended_action: Mapped[str] = mapped_column(String(30), default="ALLOW")

    # Model info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=True)

    # Anomaly detection
    is_anomaly: Mapped[bool] = mapped_column(default=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Explainability
    top_features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    def __repr__(self) -> str:
        return f"<Prediction(id={self.prediction_id!r}, pred={self.prediction!r}, conf={self.confidence:.2f})>"
