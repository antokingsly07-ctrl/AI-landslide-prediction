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

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.session import Base
from app import models  # noqa: F401


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

    # Serve local media (private uploads protected by auth via API; static for demo thumbs)
    import os

    media_dir = os.path.abspath(settings.LOCAL_STORAGE_DIR)
    os.makedirs(media_dir, exist_ok=True)
    if os.path.isdir(media_dir):
        app.mount("/media", StaticFiles(directory=media_dir), name="media")

    @app.on_event("startup")
    def on_startup():
        # Create tables in dev (use Alembic in production)
        from app.db.session import init_db

        init_db()
        from database.seed.seed_db import run_seed
        from database.seed.seed_ml import ensure_model

        try:
            run_seed()
        except Exception as e:  # pragma: no cover
            print(f"Seed warning: {e}")
        try:
            ensure_model()
        except Exception as e:  # pragma: no cover
            print(f"ML ensure warning: {e}")

    @app.get("/")
    def root():
        return {"name": settings.APP_NAME, "docs": "/docs", "api_v1": settings.API_V1_PREFIX}

    @app.get("/health")
    def health():
        return {"status": "ok", "api": "up"}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
