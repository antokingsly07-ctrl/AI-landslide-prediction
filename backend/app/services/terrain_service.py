"""Real terrain data (SRTM elevation) via the Open-Meteo elevation API (keyless).

Computes elevation, slope and aspect by sampling SRTM elevation at a central
point plus four offset neighbours (~90 m apart) and resolving the surface
gradient, exactly as terrain analysts do from a DEM.
"""
import math

import httpx

from app.core.config import settings

_DEFAULT_BASE_URL = "https://api.open-meteo.com/v1/elevation"
# ~90 m in degrees at NE-India latitudes
_OFFSETS = [(-0.0008, 0.0), (0.0008, 0.0), (0.0, -0.0008), (0.0, 0.0008)]


def _fetch_elevations(points: list[tuple[float, float]]) -> list[float]:
    base = (settings.TERRAIN_BASE_URL or _DEFAULT_BASE_URL).rstrip("/")
    params = {
        "latitude": ",".join(f"{lat:.5f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.5f}" for _, lon in points),
    }
    with httpx.Client(timeout=30) as client:
        resp = client.get(base, params=params)
        resp.raise_for_status()
        body = resp.json()
    return [float(e) for e in body.get("elevation", [])]


def get_terrain(lat: float, lon: float) -> dict:
    """Real SRTM elevation + derived slope (deg) and aspect for a coordinate."""
    points = [(lat, lon)] + [(lat + dlat, lon + dlon) for dlat, dlon in _OFFSETS]
    elevs = _fetch_elevations(points)
    center = elevs[0]
    if len(elevs) < 5:
        raise RuntimeError("Incomplete SRTM elevation response")

    def _g(dlat: float, dlon: float) -> float:
        # Find the neighbour matching this offset and scale metre / ~90 m
        for (plat, plon), e in zip(points, elevs):
            if abs(plat - (lat + dlat)) < 1e-6 and abs(plon - (lon + dlon)) < 1e-6:
                return (e - center) / 90.0
        return 0.0

    s_n = _g(-_OFFSETS[0][0], 0.0)  # slope along latitude (north-south)
    e_w = _g(0.0, _OFFSETS[2][1])   # slope along longitude (east-west)
    slope_rad = math.atan(math.sqrt(s_n**2 + e_w**2))
    slope_deg = math.degrees(slope_rad)
    aspect = math.degrees(math.atan2(-e_w, -s_n)) % 360.0
    return {
        "elevation_m": round(center, 1),
        "slope_deg": round(slope_deg, 1),
        "aspect": round(aspect, 1),
        "source": "srtm",
    }