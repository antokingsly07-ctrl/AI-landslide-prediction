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


class OpenMeteoProvider(WeatherProvider):
    """Real weather from Open-Meteo (free, no API key required)."""

    name = "openmeteo"

    def __init__(self, base_url: str = "https://api.open-meteo.com/v1"):
        self.base_url = base_url

    @staticmethod
    def _at(arr: list, i: int, default: float = 0.0) -> float:
        try:
            v = arr[i]
            return float(v) if v is not None else default
        except (IndexError, TypeError, ValueError):
            return default

    def _warning(self, rain_mm: float, prob: float) -> str:
        if rain_mm >= 100 or prob >= 90:
            return "watch"
        if rain_mm >= 40:
            return "advisory"
        return "none"

    async def fetch_current(self, lat: float, lon: float) -> dict:
        params = {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,pressure_msl",
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": "1",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.base_url}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
        c = data.get("current") or {}
        d = data.get("daily") or {}
        pnow = self._at([c.get("precipitation"), c.get("rain")], 0)
        today_rain = self._at(d.get("precipitation_sum") or [], 0)
        today_prob = self._at(d.get("precipitation_probability_max") or [], 0)
        return {
            **self._base(lat, lon),
            "rainfall_mm": round(pnow, 2),
            "rain_1h": round(pnow, 2),
            "rain_6h": round(pnow * 6, 2),
            "rain_24h": round(today_rain, 2),
            "temperature_c": round(self._at([c.get("temperature_2m")], 0), 1),
            "humidity_percent": round(self._at([c.get("relative_humidity_2m")], 0), 1),
            "pressure_hpa": round(self._at([c.get("pressure_msl")], 0), 1),
            "wind_speed": round(self._at([c.get("wind_speed_10m")], 0), 1),
            "forecast": "Monsoon conditions" if today_rain > 0 else "Fair",
            "warning": self._warning(today_rain, today_prob),
            "is_demo": False,
        }

    async def fetch_forecast(self, lat: float, lon: float) -> list[dict]:
        params = {
            "latitude": lat, "longitude": lon,
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": "7",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.base_url}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
        d = data.get("daily") or {}
        times = d.get("time") or []
        out = []
        for i, day in enumerate(times):
            out.append({
                "date": day,
                "rainfall_mm": round(self._at(d.get("precipitation_sum") or [], i), 1),
                "temperature_c": round(self._at(d.get("temperature_2m_max") or [], i), 1),
                "temp_min": round(self._at(d.get("temperature_2m_min") or [], i), 1),
                "precipitation_prob": round(self._at(d.get("precipitation_probability_max") or [], i), 0),
            })
        return out


class OpenWeatherMapProvider(WeatherProvider):
    """Real weather from OpenWeatherMap (requires OPENWEATHER_API_KEY)."""

    name = "openweather"

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or settings.OPENWEATHER_API_KEY
        self.base_url = base_url or settings.OPENWEATHER_BASE_URL

    async def _get(self, client, path: str, lat: float, lon: float, extra: dict | None = None) -> dict:
        params: dict = {"lat": lat, "lon": lon, "units": "metric", "appid": self.api_key}
        if extra:
            params.update(extra)
        resp = await client.get(f"{self.base_url}/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _warning(self, rain24: float) -> str:
        return "watch" if rain24 >= 100 else "advisory" if rain24 >= 40 else "none"

    async def fetch_current(self, lat: float, lon: float) -> dict:
        if not self.api_key:
            raise RuntimeError("OPENWEATHER_API_KEY not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            data = await self._get(client, "weather", lat, lon)
            try:
                fc = await self._get(client, "forecast", lat, lon)
            except Exception:
                fc = {"list": []}
        rain1 = float(((data.get("rain") or {}).get("1h") or 0)) or 0.0
        rain3 = float(((data.get("rain") or {}).get("3h") or 0)) or 0.0
        rain24 = sum(
            float(((x.get("rain") or {}).get("3h") or 0)) for x in fc.get("list", [])[:8]
        )
        main = data.get("main") or {}
        weath = (data.get("weather") or [{}])[0] or {}
        return {
            **self._base(lat, lon),
            "rainfall_mm": round(rain1, 2),
            "rain_1h": round(rain1, 2),
            "rain_6h": round(rain3 * 2 if rain3 else rain1 * 6, 2),
            "rain_24h": round(rain24 or rain1 * 14, 2),
            "temperature_c": round(float(main.get("temp") or 0), 1),
            "humidity_percent": round(float(main.get("humidity") or 0), 1),
            "pressure_hpa": round(float(main.get("pressure") or 0), 1),
            "wind_speed": round(float((data.get("wind") or {}).get("speed") or 0), 1),
            "forecast": weath.get("description") or "Fair",
            "warning": self._warning(rain24 or rain1 * 14),
            "is_demo": False,
        }

    async def fetch_forecast(self, lat: float, lon: float) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("OPENWEATHER_API_KEY not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            fc = await self._get(client, "forecast", lat, lon)
        daily: dict[str, dict] = {}
        for item in fc.get("list", []):
            day = (item.get("dt_txt") or "")[:10]
            if not day:
                continue
            entry = daily.setdefault(day, {"rain": 0.0, "temps": []})
            entry["rain"] += float(((item.get("rain") or {}).get("3h") or 0))
            entry["temps"].append(float((item.get("main") or {}).get("temp") or 0))
        out = []
        for day, entry in daily.items():
            temps = entry["temps"]
            out.append({
                "date": day,
                "rainfall_mm": round(entry["rain"], 1),
                "temperature_c": round(max(temps) if temps else 0, 1),
                "temp_min": round(min(temps) if temps else 0, 1),
                "precipitation_prob": 0,
            })
        return out


def get_weather_provider() -> WeatherProvider:
    """Select provider based on configuration.

    Preference: explicit WEATHER_PROVIDER env choice, then auto-detect
    (OpenWeatherMap if a key is set, IMD if configured, otherwise Open-Meteo).
    """
    mode = (settings.WEATHER_PROVIDER or "auto").strip().lower()
    if mode == "mock":
        return MockWeatherProvider()
    if mode == "openweather":
        return OpenWeatherMapProvider()
    if mode == "openmeteo":
        return OpenMeteoProvider()
    if mode == "imd":
        return IMDWeatherProvider()
    if settings.OPENWEATHER_API_KEY:
        return OpenWeatherMapProvider()
    if settings.IMD_API_KEY and settings.IMD_BASE_URL:
        return IMDWeatherProvider()
    return OpenMeteoProvider()
