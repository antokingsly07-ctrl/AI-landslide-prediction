"""Satellite observation endpoints using the modular satellite source."""
from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.deps import get_current_user
from app.models.geo import User
from app.services.satellite_service import (
    MockSatelliteSource,
    get_satellite_source,
)

router = APIRouter()


@router.get("")
async def satellite_observation(
    lat: float = Query(...),
    lon: float = Query(...),
    user: User = Depends(get_current_user),
):
    source = get_satellite_source()
    try:
        data = await run_in_threadpool(source.get_observation, lat, lon)
        return {"provider": source.name, "is_demo": source.name == "mock", **data}
    except Exception as e:
        mock = await run_in_threadpool(MockSatelliteSource().get_observation, lat, lon)
        mock["note"] = f"Live satellite provider unavailable: {str(e)}"
        return mock