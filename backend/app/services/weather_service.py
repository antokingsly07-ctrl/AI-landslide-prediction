"""Modular weather provider with IMD + Mock implementations."""
import math
import re
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
    """India Meteorological Department integration via the official IMD API portal.

    Endpoints (https://api.imd.gov.in/public/api_reference.html):
      * /api/v1/aws_data        - live AWS/ARG station observations; nearest
                                  station to (lat, lon) is selected by distance
      * /api/v1/districtrainfall - daily actual district rainfall (24h)
      * /api/v1/state_district_rainfall_forecast - 5-day rainfall outlook
      * /api/v1/current_wx      - single-station current weather fallback
                                  (used when IMD_STATION_ID is set)

    Auth: a JWT bearer token (IMD_API_TOKEN) or the portal API key
    (IMD_API_KEY, sent as a bearer credential). If IMD_TOKEN_URL is configured
    the key is exchanged for a JWT first.
    """

    name = "imd"

    def __init__(self, api_key: str = "", token: str = "", base_url: str = "",
                 state_id: int = 0, station_id: str = ""):
        self.api_key = api_key or settings.IMD_API_KEY
        self.token = token or settings.IMD_API_TOKEN
        self.base_url = (base_url or settings.IMD_BASE_URL
                         or "https://api.imd.gov.in").rstrip("/")
        self.state_id = state_id or settings.IMD_STATE_ID or 24
        self.station_id = station_id or settings.IMD_STATION_ID or ""
        self.token_url = settings.IMD_TOKEN_URL or ""
        self._jwt: Optional[str] = None
        self._last_district = ""

    # ------------------------------------------------------------------ auth
    async def _bearer(self) -> str:
        if self.token:
            return self.token
        if self._jwt:
            return self._jwt
        if not self.api_key:
            raise RuntimeError("IMD_API_KEY / IMD_API_TOKEN not configured")
        if self.token_url:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        self.token_url,
                        data={"grant_type": "client_credentials",
                              "client_id": self.api_key},
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                self._jwt = (payload.get("access_token") or payload.get("token")
                             or payload.get("jwt") or "")
            except Exception:
                self._jwt = ""
        self._jwt = self._jwt or self.api_key
        return self._jwt

    async def _get(self, client, path: str, params: Optional[dict] = None) -> dict:
        resp = await client.get(
            f"{self.base_url}{path}",
            params=params,
            headers={"Authorization": f"Bearer {await self._bearer()}"},
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------- parsing
    @staticmethod
    def _norm(key) -> str:
        return re.sub(r"[^a-z0-9]", "", (key or "").lower())

    @classmethod
    def _flat(cls, row: dict) -> dict:
        return {cls._norm(k): v for k, v in row.items()}

    @staticmethod
    def _rows(payload) -> list:
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            for key in ("data", "records", "result", "list"):
                val = payload.get(key)
                if isinstance(val, list):
                    return [r for r in val if isinstance(r, dict)]
            return [payload]
        return []

    @staticmethod
    def _num(row: dict, *keys: str) -> float:
        for key in keys:
            val = row.get(key)
            if val is None:
                continue
            if isinstance(val, (int, float)):
                return float(val)
            try:
                return float(str(val).strip())
            except (TypeError, ValueError):
                continue
        return 0.0

    @staticmethod
    def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        a = min(1.0, max(0.0, a))
        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _dist_to_mm(text: str) -> float:
        t = (text or "").strip().lower()
        if not t or t in ("none", "nil", "dry", "no rain", "fair"):
            return 0.0
        if "fairly widespread" in t:
            return 7.0
        if "widespread" in t:
            return 12.0
        if "scattered" in t:
            return 3.0
        if "isolated" in t:
            return 1.0
        m = re.search(r"\d+(?:\.\d+)?", t)
        return float(m.group(0)) if m else 0.0

    @staticmethod
    def _prob(text) -> int:
        nums = [int(x) for x in re.findall(r"\d+", str(text or ""))]
        if len(nums) >= 2:
            return (nums[0] + nums[1]) // 2
        return nums[0] if nums else 0

    # ----------------------------------------------------------- data source
    async def _nearest_aws(self, client, lat: float, lon: float) -> Optional[dict]:
        payload = await self._get(client, "/api/v1/aws_data",
                                  {"sid": self.state_id})
        best: Optional[dict] = None
        best_dist = float("inf")
        for row in self._rows(payload):
            flat = self._flat(row)
            rlat = self._num(flat, "latitude")
            rlon = self._num(flat, "longitude")
            if not math.isfinite(rlat) or not math.isfinite(rlon):
                continue
            dist = self._distance_km(lat, lon, rlat, rlon)
            if dist < best_dist:
                best_dist, best = dist, row
        return best

    async def _district_rain_24h(self, client, district: str) -> float:
        target = (district or "").strip().upper()
        if not target:
            return 0.0
        try:
            payload = await self._get(client, "/api/v1/districtrainfall", {})
        except Exception:
            return 0.0
        for row in self._rows(payload):
            flat = self._flat(row)
            if str(flat.get("district") or "").strip().upper() == target:
                return self._num(flat, "dailyactual")
        return 0.0

    # -------------------------------------------------------------- endpoints
    async def fetch_current(self, lat: float, lon: float) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            aws = None
            try:
                aws = await self._nearest_aws(client, lat, lon)
            except Exception:
                aws = None
            flat = self._flat(aws) if aws else {}
            self._last_district = str(flat.get("district") or "")
            rain_24h = await self._district_rain_24h(client, self._last_district)

        out = {
            **self._base(lat, lon),
            "rainfall_mm": round(rain_24h, 2),
            "rain_1h": None,
            "rain_6h": None,
            "rain_24h": round(rain_24h, 2),
            "temperature_c": round(self._num(flat, "currtemp", "temperature"), 1),
            "humidity_percent": round(self._num(flat, "rh", "humidity"), 1),
            "pressure_hpa": round(self._num(flat, "mslp"), 1),
            "wind_speed": round(self._num(flat, "windspeed"), 1),
            "station": str(flat.get("station") or ""),
            "district": self._last_district or str(flat.get("state") or ""),
            "forecast": "Monsoon conditions" if rain_24h > 0 else "Fair",
            "warning": ("watch" if rain_24h >= 100
                        else "advisory" if rain_24h >= 40 else "none"),
            "is_demo": False,
        }
        slat = self._num(flat, "latitude")
        slon = self._num(flat, "longitude")
        out["station_lat"] = slat if math.isfinite(slat) else None
        out["station_lon"] = slon if math.isfinite(slon) else None

        if aws is None and self.station_id:
            async with httpx.AsyncClient(timeout=20) as client:
                payload = await self._get(client, "/api/v1/current_wx",
                                          {"id": self.station_id})
            rec = self._flat(self._rows(payload)[0]) if self._rows(payload) else {}
            rain = self._num(rec, "last24hrsrainfall")
            out.update({
                "temperature_c": round(self._num(rec, "temperature"), 1),
                "humidity_percent": round(self._num(rec, "humidity"), 1),
                "pressure_hpa": round(self._num(rec, "mslp"), 1),
                "wind_speed": round(self._num(rec, "windspeed"), 1),
                "rainfall_mm": round(rain, 2),
                "rain_24h": round(rain, 2),
                "station": str(rec.get("station") or ""),
            })
        if aws is None and not self.station_id:
            raise RuntimeError(
                "IMD aws_data returned no usable stations "
                "(check IMD_STATE_ID / API access)")
        return out

    async def fetch_forecast(self, lat: float, lon: float) -> list[dict]:
        async with httpx.AsyncClient(timeout=20) as client:
            payload = await self._get(
                client, "/api/v1/state_district_rainfall_forecast", {})
        rows = self._rows(payload)
        if not rows:
            raise RuntimeError("IMD forecast returned no rows")
        rec = rows[0]
        if self._last_district:
            rec = next(
                (r for r in rows
                 if str(self._flat(r).get("district") or "").upper()
                 == self._last_district.upper()),
                rec,
            )
        flat = self._flat(rec)
        base = str(flat.get("dateobs") or "")
        try:
            anchor = datetime.strptime(base[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            anchor = datetime.now(timezone.utc).date()
        out = []
        for i in range(1, 8):
            dist = str(flat.get(f"day{i}distribution") or "Fair")
            out.append({
                "date": (anchor + timedelta(days=i - 1)).isoformat(),
                "rainfall_mm": round(self._dist_to_mm(dist), 1),
                "temperature_c": None,
                "precipitation_prob": round(
                    self._prob(flat.get(f"day{i}distributionpercentage")), 0),
                "conditions": dist.strip() or "Fair",
            })
        return out


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
    if settings.IMD_API_KEY or settings.IMD_API_TOKEN:
        return IMDWeatherProvider()
    return OpenMeteoProvider()
