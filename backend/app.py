"""
SecureIoT-X Backend — FastAPI Application Factory.

Central API server providing:
- REST API (auth, devices, predictions, threats, blockchain, analytics)
- WebSocket for real-time dashboard updates
- Health monitoring for all services
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is importable
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.core.config import settings
from backend.core.mongodb import init_mongodb, close_mongodb
from backend.core.websocket import ws_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("secureiot.backend")


# ── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting SecureIoT-X Backend...")

    # Initialize MongoDB (PRIMARY and ONLY application datastore — REQUIRED)
    # This also seeds all 10 devices and creates the default admin user in MongoDB.
    try:
        await init_mongodb()
        logger.info("MongoDB initialized — devices seeded, admin user ensured")
    except Exception as e:
        logger.error("MongoDB initialization FAILED: %s", e)
        logger.error("MongoDB is REQUIRED. Ensure MongoDB is running and accessible.")
        # Don't raise — allow backend to start so health endpoint can report the issue

    # Start MQTT Ingestion Service (connects to Mosquitto broker in background)
    try:
        from backend.services.mqtt_service import mqtt_service
        await mqtt_service.start()
        logger.info("MQTT Ingestion Service started")
    except Exception as e:
        logger.warning("Could not start MQTT service: %s", e)

    # Restore active physical device isolation enforcements from MongoDB across restarts
    try:
        from security.network_enforcer import network_enforcer
        restored = await network_enforcer.restore_enforcements_on_startup()
        if restored > 0:
            logger.info("Restored %d active network enforcements from MongoDB", restored)
    except Exception as e:
        logger.warning("Could not restore network enforcements: %s", e)

    logger.info("SecureIoT-X Backend ready on port %d", settings.backend_port)
    yield
    try:
        from backend.services.mqtt_service import mqtt_service
        await mqtt_service.stop()
    except Exception:
        pass
    await close_mongodb()
    logger.info("Shutting down SecureIoT-X Backend")


# ── App Factory ────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from fastapi.responses import RedirectResponse

    app = FastAPI(
        title="SecureIoT-X API",
        description="AI-Driven Decentralized IDS for IoT Networks",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Route /api/docs -> /docs for convenience
    @app.get("/api/docs", include_in_schema=False)
    async def redirect_api_docs():
        return RedirectResponse(url="/docs")

    @app.get("/api/openapi.json", include_in_schema=False)
    async def redirect_openapi():
        return RedirectResponse(url="/openapi.json")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    _register_routes(app)

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws_manager.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                # Echo for keep-alive
                await ws_manager.send_personal(ws, "pong", {"message": "alive"})
        except WebSocketDisconnect:
            await ws_manager.disconnect(ws)

    return app


def _register_routes(app: FastAPI) -> None:
    """Register all API routers."""
    from backend.api.health import router as health_router
    from backend.api.auth import router as auth_router
    from backend.api.devices import router as devices_router
    from backend.api.predictions import router as predictions_router
    from backend.api.threats import router as threats_router
    from backend.api.blockchain_api import router as blockchain_router
    from backend.api.models_api import router as models_router
    from backend.api.analytics import router as analytics_router
    from backend.api.system import router as system_router
    from backend.api.simulation_api import router as simulation_router

    app.include_router(health_router, prefix="/api", tags=["Health"])
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(devices_router, prefix="/api/devices", tags=["Devices"])
    app.include_router(predictions_router, prefix="/api", tags=["Predictions"])
    app.include_router(threats_router, prefix="/api/threats", tags=["Threats"])
    app.include_router(blockchain_router, prefix="/api/blockchain", tags=["Blockchain"])
    app.include_router(models_router, prefix="/api/models", tags=["AI Models"])
    app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
    app.include_router(system_router, prefix="/api/system", tags=["System"])
    app.include_router(simulation_router, prefix="/api/simulate", tags=["Simulation"])


# Create the app instance
app = create_app()
