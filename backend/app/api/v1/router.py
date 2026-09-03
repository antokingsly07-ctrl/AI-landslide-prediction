"""API v1 router aggregating all endpoint modules."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    alerts,
    auth,
    dashboard,
    incidents,
    media,
    predictions,
    reports,
    risk,
    roads,
    sensors,
    sync,
    weather,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
api_router.include_router(risk.router, prefix="/risk", tags=["Risk"])
api_router.include_router(weather.router, prefix="/weather", tags=["Weather"])
api_router.include_router(sensors.router, prefix="/sensors", tags=["Sensors"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(roads.router, prefix="/roads", tags=["Roads"])
api_router.include_router(sync.router, prefix="/sync", tags=["Offline Sync"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
