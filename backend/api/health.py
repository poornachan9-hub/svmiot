"""Health check endpoint — monitors all services including MongoDB and Ganache."""

from fastapi import APIRouter
from backend.core.config import settings

router = APIRouter()


@router.get("/health", summary="System Health Check")
async def health_check():
    """Check health of all system components."""
    from pathlib import Path

    # Check MongoDB (PRIMARY application database)
    mongodb_connected = False
    mongodb_error = None
    mongodb_detail = {}
    try:
        from backend.core.mongodb import check_mongodb_health
        mongodb_detail = await check_mongodb_health()
        mongodb_connected = mongodb_detail.get("connected", False)
        if not mongodb_connected:
            mongodb_error = mongodb_detail.get("error", "Unknown error")
    except Exception as e:
        mongodb_error = str(e)

    # Check AI model
    model_status = "ONLINE"
    models_dir = Path(settings.project_root) / settings.ml_models_dir
    if not models_dir.exists() or not list(models_dir.glob("**/*.joblib")):
        model_status = "NO_MODEL_TRAINED"

    # Check Ganache (real Ethereum blockchain — the ONLY blockchain backend)
    ganache_connected = False
    ganache_error = None
    ganache_detail = {}
    try:
        from blockchain.ganache_client import get_ganache_client
        client = get_ganache_client()
        ganache_detail = client.get_status()
        ganache_connected = ganache_detail.get("connected", False)
        if not ganache_connected:
            ganache_error = ganache_detail.get("error", "Cannot connect to Ganache RPC")
    except Exception as e:
        ganache_error = str(e)

    # SDN status
    sdn_status = "SIMULATED" if settings.sdn_mode == "mock" else "ONLINE"

    # Telegram notification status
    telegram_configured = bool(
        settings.telegram_bot_token and settings.telegram_chat_id
    )

    # MQTT status
    mqtt_status = "NOT CONNECTED"
    try:
        from backend.services.mqtt_service import mqtt_service
        mqtt_info = mqtt_service.get_status()
        mqtt_status = mqtt_info.get("status", "NOT CONNECTED")
    except Exception:
        pass

    overall = "healthy"
    if not mongodb_connected:
        overall = "degraded"
    if not ganache_connected:
        overall = "degraded"

    return {
        "status": overall,
        "mongodb": "CONNECTED" if mongodb_connected else "NOT CONNECTED",
        "ganache": "CONNECTED" if ganache_connected else "NOT CONNECTED",
        "services": {
            "backend": "ONLINE",
            "mongodb": {
                "status": "CONNECTED" if mongodb_connected else "NOT CONNECTED",
                "connected": mongodb_connected,
                **({} if not mongodb_error else {"error": mongodb_error}),
                **{k: v for k, v in mongodb_detail.items() if k not in ("status", "connected", "error")},
            },
            "mqtt": mqtt_status,
            "ai_model": model_status,
            "ganache": {
                "status": "CONNECTED" if ganache_connected else "NOT CONNECTED",
                "connected": ganache_connected,
                **({} if not ganache_error else {"error": ganache_error}),
                **{k: v for k, v in ganache_detail.items() if k not in ("status", "connected", "error")},
            },
            "sdn": sdn_status,
            "websocket": "ONLINE",
            "telegram": "CONFIGURED" if telegram_configured else "NOT_CONFIGURED",
        },
        "version": "1.0.0",
        "mode": settings.active_mode,
    }
