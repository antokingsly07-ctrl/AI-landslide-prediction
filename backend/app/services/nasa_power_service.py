"""Real environmental reanalysis via NASA POWER (MERRA-2, keyless).

POWER exposes daily satellite-assimilated reanalysis — precipitation
(PRECTOTCORR), root-zone soil wetness (GWETROOT, which assimilates satellite
soil moisture retrievals), 2 m temperature (T2M) and relative humidity (RH2M)
— back to 1981 with near-real-time updates.
"""
from datetime import date, timedelta

import httpx

from app.core.config import settings

_DEFAULT_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
_PARAMS = "PRECTOTCORR,GWETROOT,GWETPROF,T2M,RH2M"


def _series(lat: float, lon: float, start: date, end: date) -> dict:
    if end < start:
        return {}
    base = (settings.NASA_POWER_BASE_URL or _DEFAULT_BASE_URL).rstrip("/")
    params = {
        "parameters": _PARAMS,
        "community": "AG",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    with httpx.Client(timeout=45) as client:
        resp = client.get(base, params=params)
        resp.raise_for_status()
        body = resp.json()
    return (body.get("properties") or {}).get("parameter") or {}


def _num(val) -> float | None:
    if val in (None, "", -999.0, -999):
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f


def get_daily_series(
    lat: float, lon: float, days: int
) -> list[dict]:
    """Real daily environmental series for the last `days` days (oldest first)."""
    today = date.today()
    end = today - timedelta(days=1)  # POWER lags one day behind 'today'
    start = end - timedelta(days=days - 1)
    raw = _series(lat, lon, start, end)
    rain_map = raw.get("PRECTOTCORR") or {}
    root_map = raw.get("GWETROOT") or {}
    prof_map = raw.get("GWETPROF") or {}
    temp_map = raw.get("T2M") or {}
    rh_map = raw.get("RH2M") or {}

    rows = []
    d = start
    while d <= end:
        key = d.strftime("%Y%m%d")
        rain = _num(rain_map.get(key))
        root = _num(root_map.get(key))
        prof = _num(prof_map.get(key))
        temp = _num(temp_map.get(key))
        rh = _num(rh_map.get(key))
        if rain is None and root is None and temp is None:
            d += timedelta(days=1)
            continue
        rows.append({
            "date": d.isoformat(),
            "rain_mm": round(rain, 1) if rain is not None else None,
            "soil_moisture_pct": round(root * 100.0, 1) if root is not None else None,
            "soil_moisture_prof_pct": round(prof * 100.0, 1) if prof is not None else None,
            "temperature_c": round(temp - 273.15, 1) if temp is not None else None,
            "humidity_pct": round(rh, 1) if rh is not None else None,
        })
        d += timedelta(days=1)
    return rows


def get_recent(lat: float, lon: float, days: int = 7) -> dict | None:
    """Aggregate the last `days` days into one summary (for alerts/risk)."""
    rows = get_daily_series(lat, lon, days)
    if not rows:
        return None
    rains = [r["rain_mm"] for r in rows if r["rain_mm"] is not None]
    soils = [r["soil_moisture_pct"] for r in rows if r["soil_moisture_pct"] is not None]
    temps = [r["temperature_c"] for r in rows if r["temperature_c"] is not None]
    rh = [r["humidity_pct"] for r in rows if r["humidity_pct"] is not None]
    return {
        "rain_3d": round(sum(rains[-3:]), 1) if len(rains) >= 3 else None,
        "rain_7d": round(sum(rains), 1) if rains else None,
        "soil_moisture_pct": round(sum(soils) / len(soils), 1) if soils else None,
        "temperature_c": round(sum(temps) / len(temps), 1) if temps else None,
        "humidity_pct": round(sum(rh) / len(rh), 1) if rh else None,
    }