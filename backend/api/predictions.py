"""
Predictions API — run AI inference, list prediction history.

ALL prediction data stored in MongoDB `predictions` collection.
SQLite is NO LONGER used for predictions.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from backend.core.config import settings
from backend.core.mongodb import get_mongodb
from backend.core.websocket import ws_manager
from security.risk_engine import RiskEngine
from security.response_engine import ResponseEngine

router = APIRouter()
logger = logging.getLogger(__name__)
risk_engine = RiskEngine()
response_engine = ResponseEngine()


class PredictRequest(BaseModel):
    device_id: str = "ESP32_001"
    features: Dict[str, Any] = {}


@router.post("/predict", summary="Run AI Prediction")
async def predict(req: PredictRequest):
    """Run AI inference on network features; store result in MongoDB."""
    from pathlib import Path

    # Inference must use the evaluated production artifact; never fabricate a
    # success-shaped prediction when the model or its preprocessing is missing.
    try:
        from ai_engine.predict import PredictionEngine
        from ai_engine.model_registry import ModelRegistry

        registry = ModelRegistry(
            str(Path(settings.project_root) / settings.ml_models_dir / "registry.json")
        )
        prod_model = registry.get_production_model()

        if not prod_model or not prod_model.get("validated"):
            raise HTTPException(
                status_code=503,
                detail="No evaluated production model is available for inference",
            )
        engine = PredictionEngine(
            model_path=prod_model["model_path"],
            preprocessing_path=prod_model["preprocessing_path"],
            config=settings.confidence_thresholds,
        )
        if not engine.is_loaded or engine.preprocessing is None:
            raise HTTPException(
                status_code=503,
                detail="The production model or its preprocessing artifact could not be loaded",
            )
        try:
            result = engine.predict(req.features, req.device_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=503,
            detail=f"Production model inference failed: {e}",
        ) from e

    # Risk assessment
    risk = risk_engine.calculate_risk(
        ai_confidence=result.get("confidence", 0),
        attack_type=result.get("prediction", "Normal"),
        device_criticality=50,
    )
    result["risk_score"] = risk["risk_score"]
    result["severity"] = risk["severity"]

    # Response decision
    response = response_engine.decide_response(
        severity=risk["severity"],
        risk_score=risk["risk_score"],
        event_id=result.get("prediction_id", uuid.uuid4().hex[:16]),
        device_id=req.device_id,
        attack_type=result.get("prediction", "Unknown"),
    )
    result["recommended_action"] = response["action"]

    # Save to MongoDB
    now = datetime.now(timezone.utc)
    pred_doc = {
        "prediction_id": result.get("prediction_id", uuid.uuid4().hex[:16]),
        "event_id": result.get("prediction_id", ""),
        "device_id": req.device_id,
        "prediction": result["prediction"],
        "confidence": result["confidence"],
        "risk_score": risk["risk_score"],
        "severity": risk["severity"],
        "recommended_action": response["action"],
        "model_name": result.get("model_name", "simulated"),
        "model_version": result.get("model_version", "v0"),
        "timestamp": now,
    }
    try:
        db = get_mongodb()
        await db["predictions"].insert_one(pred_doc)
    except PyMongoError as exc:
        logger.exception("Could not persist prediction %s", result["prediction_id"])
        raise HTTPException(
            status_code=503,
            detail="Prediction was generated but could not be persisted",
        ) from exc

    # Broadcast via WebSocket
    await ws_manager.broadcast("prediction_made", result)
    if risk["severity"] in ("HIGH", "CRITICAL"):
        await ws_manager.broadcast("threat_detected", result)

    return result


@router.get("/predictions", summary="List Predictions")
async def list_predictions(limit: int = 50):
    """Get recent predictions from MongoDB (both direct API and simulation pipeline)."""
    db = get_mongodb()
    cursor = db["predictions"].find({}).sort("timestamp", -1).limit(limit)
    preds = await cursor.to_list(length=limit)
    result = []
    for p in preds:
        p.pop("_id", None)
        result.append({
            "prediction_id": p.get("prediction_id", ""),
            "event_id": p.get("event_id", ""),
            "device_id": p.get("device_id", ""),
            "prediction": p.get("prediction", ""),
            "confidence": p.get("confidence", 0),
            "risk_score": p.get("risk_score", 0),
            "severity": p.get("severity", ""),
            "recommended_action": p.get("recommended_action", ""),
            "model_name": p.get("model_name", p.get("model", "")),
            "timestamp": p.get("timestamp"),
        })
    return result
