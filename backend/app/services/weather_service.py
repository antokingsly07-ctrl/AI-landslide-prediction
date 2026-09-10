"""Modular weather provider with IMD + Mock implementations."""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.core.config import settings


class WeatherProvider(ABC):
    name = "base"

    @abstractmethod
    async def fetch_current(self, lat: float, lon: float) -> dict:
        """Return current weather dict."""

    @abstractmethod
    async def fetch_forecast(self, lat: float, lon: float) -> list[dict]:
        """Return forecast list."""

    def _base(self, lat: float, lon: float) -> dict:
        return {"latitude": lat, "longitude": lon, "provider": self.name}


class IMDWeatherProvider(WeatherProvider):
    """India Meteorological Department integration (configurable)."""

    name = "imd"

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or settings.IMD_API_KEY
        self.base_url = base_url or settings.IMD_BASE_URL

    async def fetch_current(self, lat: float, lon: float) -> dict:
        if not self.api_key:
            raise RuntimeError("IMD_API_KEY not configured")
        url = f"{self.base_url}/weather/current"
        params = {"lat": lat, "lon": lon, "apikey": self.api_key}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        data.update(self._base(lat, lon))
        return data

    async def fetch_forecast(self, lat: float, lon: float) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("IMD_API_KEY not configured")
        url = f"{self.base_url}/weather/forecast"
        params = {"lat": lat, "lon": lon, "apikey": self.api_key}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        rows = data.get("list", []) if isinstance(data, dict) else data
        return rows


class MockWeatherProvider(WeatherProvider):
    """Realistic simulated weather for development when no external API."""

    name = "mock"

    def __init__(self, seed: int = 7):
        self.seed = seed

    async def fetch_current(self, lat: float, lon: float) -> dict:
        import random

        rng = random.Random(self.seed + int(lat * 10) + int(lon * 10))
        # monsoon-like rainfall pattern for North East
        rain_now = round(rng.uniform(0, 18), 2)
        hour = datetime.now(timezone.utc).hour
        drizzle_factor = 1.4 if 14 <= hour <= 20 else 0.8
        rain1 = round(rain_now * drizzle_factor, 2)
        return {
            **self._base(lat, lon),
            "rainfall_mm": rain_now,
            "rain_1h": rain1,
            "rain_6h": round(rain1 * rng.uniform(3.2, 5.5), 2),
            "rain_24h": round(rain1 * rng.uniform(9, 15), 2),
            "temperature_c": round(rng.uniform(18, 30), 1),
            "humidity_percent": round(rng.uniform(65, 98), 1),
            "pressure_hpa": round(rng.uniform(990, 1015), 1),
            "wind_speed": round(rng.uniform(1, 12), 1),
            "forecast": "Prevalent monsoon showers",
            "warning": "none" if rain1 < 40 else "watch",
            "is_demo": True,
        }

    async def fetch_forecast(self, lat: float, lon: float) -> list[dict]:
        import random

        rng = random.Random(self.seed + int(lat))
        now = datetime.now(timezone.utc)
        out = []
        for i in range(7):
            d = now + timedelta(days=i)
            out.append({
                "date": d.date().isoformat(),
                "rainfall_mm": round(max(0, rng.gauss(30, 18)), 1),
                "temperature_c": round(rng.uniform(18, 30), 1),
                "precipitation_prob": round(rng.uniform(40, 95), 1),
            })
        return out


def get_weather_provider() -> WeatherProvider:
    """Select provider based on configuration; default to mock for offline/dev."""
    if settings.IMD_API_KEY and settings.IMD_BASE_URL:
        return IMDWeatherProvider()
    return MockWeatherProvider()
