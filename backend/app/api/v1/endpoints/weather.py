"""Weather endpoints using the modular weather provider."""
from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.models.geo import User
from app.services.weather_service import get_weather_provider

router = APIRouter()


@router.get("")
async def current_weather(
    lat: float = Query(...),
    lon: float = Query(...),
    user: User = Depends(get_current_user),
):
    provider = get_weather_provider()
    try:
        data = await provider.fetch_current(lat, lon)
        return {"provider": provider.name, "is_demo": provider.name == "mock", **data}
    except Exception as e:
        # Fallback to mock if provider unavailable
        from app.services.weather_service import MockWeatherProvider

        mock = await MockWeatherProvider().fetch_current(lat, lon)
        mock["note"] = f"Live provider unavailable: {str(e)}"
        return mock


@router.get("/forecast")
async def forecast(
    lat: float = Query(...),
    lon: float = Query(...),
    user: User = Depends(get_current_user),
):
    provider = get_weather_provider()
    try:
        data = await provider.fetch_forecast(lat, lon)
        return {"provider": provider.name, "is_demo": provider.name == "mock", "forecast": data}
    except Exception as e:
        from app.services.weather_service import MockWeatherProvider

        return {"provider": "mock", "is_demo": True,
                "note": f"Live provider unavailable: {str(e)}",
                "forecast": await MockWeatherProvider().fetch_forecast(lat, lon)}
