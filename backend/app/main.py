"""FastAPI application entrypoint."""
import os
import sys

# Ensure repo root is on sys.path so database.seed and other top-level packages are importable
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket, WebSocketDisconnect

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.session import Base
from app import models  # noqa: F401
from app.realtime import register as ws_register, unregister as ws_unregister


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="AI-powered Landslide Early Warning and Monitoring Platform for North-Eastern India",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    media_dir = os.path.abspath(settings.LOCAL_STORAGE_DIR)
    os.makedirs(media_dir, exist_ok=True)
    if os.path.isdir(media_dir):
        app.mount("/media", StaticFiles(directory=media_dir), name="media")

    @app.on_event("startup")
    async def on_startup():
        from app.db.session import init_db

        init_db()
        from database.seed.seed_db import (
            ensure_bootstrap_admin,
            run_migration,
            run_real_data_fill,
        )
        from database.seed.seed_ml import ensure_model

        # One-time sync migration (fast): purge demo data + reference geo.
        # Then the heavy real-data fill (SRTM / NASA POWER / NASA GLC) runs in
        # a background thread so the API stays responsive on first boot.
        try:
            run_migration()
        except Exception as e:  # pragma: no cover
            print(f"Migration warning: {e}")
        try:
            import threading

            threading.Thread(
                target=run_real_data_fill, daemon=True, name="real-data-fill"
            ).start()
        except Exception as e:  # pragma: no cover
            print(f"Real-data fill scheduling warning: {e}")
        try:
            ensure_bootstrap_admin()
        except Exception as e:  # pragma: no cover
            print(f"Bootstrap admin warning: {e}")
        try:
            ensure_model()
        except Exception as e:  # pragma: no cover
            print(f"ML ensure warning: {e}")
        # Start background risk monitor
        try:
            from app.tasks.monitor import monitor
            monitor.start()
            print("RiskMonitor background task started")
        except Exception as e:  # pragma: no cover
            print(f"Monitor start warning: {e}")

    @app.get("/")
    def root():
        return {"name": settings.APP_NAME, "docs": "/docs", "api_v1": settings.API_V1_PREFIX}

    @app.get("/health")
    def health():
        return {"status": "ok", "api": "up"}

    # WebSocket endpoint for real-time alerts (auth required)
    @app.websocket("/ws/alerts")
    async def alerts_ws(websocket: WebSocket):
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4401, reason="missing token")
            return
        from app.core.security import decode_token

        try:
            payload = decode_token(token)
            if not payload.get("sub"):
                await websocket.close(code=4401)
                return
        except Exception:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        ws_register(websocket)
        try:
            while True:
                # Keep connection alive; client can send pings
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_text('{"type":"pong"}')
        except WebSocketDisconnect:
            ws_unregister(websocket)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
