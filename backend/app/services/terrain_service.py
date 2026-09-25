"""Real terrain data (SRTM elevation) via the Open-Meteo elevation API (keyless).

Computes elevation, slope and aspect by sampling SRTM elevation at a central
point plus four offset neighbours (~90 m apart) and resolving the surface
gradient, exactly as terrain analysts do from a DEM.

Requests are throttled, batched (<= 40 locations per call) and retried with
backoff so keyless rate limits (HTTP 429) are handled gracefully.
"""
import math
import threading
import time

import httpx

from app.core.config import settings

_DEFAULT_BASE_URL = "https://api.open-meteo.com/v1/elevation"
# ~90 m in degrees at NE-India latitudes
_OFFSETS = [(-0.0008, 0.0), (0.0008, 0.0), (0.0, -0.0008), (0.0, 0.0008)]
_MAX_PER_REQUEST = 40
_MIN_GAP_SECONDS = 0.1
_ATTEMPTS = 5
_BACKOFF_BASE_SECONDS = 2.0
_MAX_BACKOFF_SECONDS = 60.0

_lock = threading.Lock()
_last_request_at = 0.0


def _throttle():
    global _last_request_at
    with _lock:
        wait = _MIN_GAP_SECONDS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    ra = resp.headers.get("Retry-After")
    if ra and ra.isdigit():
        return min(float(ra), _MAX_BACKOFF_SECONDS)
    return None


def _retry_get(client: httpx.Client, url: str, params: dict) -> httpx.Response:
    last = None
    for attempt in range(1, _ATTEMPTS + 1):
        resp = client.get(url, params=params)
        if resp.status_code == 200:
            return resp
        if resp.status_code == 429:
            wait = _retry_after_seconds(resp) or min(
                _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), _MAX_BACKOFF_SECONDS
            )
        else:
            wait = min(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), _MAX_BACKOFF_SECONDS)
        print(f"Terrain API {resp.status_code} - retrying in {wait:.1f}s ({attempt}/{_ATTEMPTS})")
        time.sleep(wait)
        last = resp
    raise RuntimeError(f"Terrain API failed after {_ATTEMPTS} attempts: {last.status_code}")


def _fetch_elevations(points: list[tuple[float, float]]) -> list[float]:
    base = (settings.TERRAIN_BASE_URL or _DEFAULT_BASE_URL).rstrip("/")
    params = {
        "latitude": ",".join(f"{lat:.5f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.5f}" for _, lon in points),
    }
    _throttle()
    with httpx.Client(timeout=30) as client:
        resp = _retry_get(client, base, params)
        body = resp.json()
    return [float(e) for e in body.get("elevation", [])]


def _slope_aspect(center: float, north: float, west: float) -> tuple[float, float]:
    s_n = (north - center) / 90.0
    e_w = (west - center) / 90.0
    slope_deg = math.degrees(math.atan(math.sqrt(s_n**2 + e_w**2)))
    aspect = math.degrees(math.atan2(-e_w, -s_n)) % 360.0
    return slope_deg, aspect


def get_terrain(lat: float, lon: float) -> dict:
    """Real SRTM elevation + derived slope (deg) and aspect for a coordinate."""
    keys = [(round(lat, 5), round(lon, 5))]
    keys += [(round(lat + dlat, 5), round(lon + dlon, 5)) for dlat, dlon in _OFFSETS]
    elevs = _fetch_elevations(keys)
    if len(elevs) < 5:
        raise RuntimeError("Incomplete SRTM elevation response")
    slope_deg, aspect = _slope_aspect(elevs[0], elevs[1], elevs[3])
    return {
        "elevation_m": round(elevs[0], 1),
        "slope_deg": round(slope_deg, 1),
        "aspect": round(aspect, 1),
        "source": "srtm",
    }


def get_terrain_many(lat_lons: list[tuple[float, float]]) -> list[dict | None]:
    """Bulk SRTM slope/elevation for many coordinates using few HTTP calls.

    Sample coordinates are deduped and fetched in chunks of <= _MAX_PER_REQUEST.
    Returns one dict per input coordinate (aligned), or None for points whose
    sample batch could not be fetched (already retried).
    """
    rounded: dict[tuple[float, float], float | None] = {}
    order: list[list[tuple[float, float]]] = []
    for lat, lon in lat_lons:
        keys = [(round(lat, 5), round(lon, 5))]
        keys += [(round(lat + dlat, 5), round(lon + dlon, 5)) for dlat, dlon in _OFFSETS]
        for k in keys:
            rounded.setdefault(k, None)
        order.append(keys)

    coords = list(rounded.keys())
    failed: set[tuple[float, float]] = set()
    for i in range(0, len(coords), _MAX_PER_REQUEST):
        chunk = coords[i : i + _MAX_PER_REQUEST]
        try:
            elevs = _fetch_elevations(chunk)
            if len(elevs) != len(chunk):
                raise RuntimeError("Elevation response length mismatch")
            for c, e in zip(chunk, elevs):
                rounded[c] = e
        except Exception as exc:  # pragma: no cover - network failure
            print(f"Terrain batch chunk skipped ({len(chunk)} locations): {exc}")
            failed.update(chunk)

    out: list[dict | None] = []
    for keys in order:
        if any(k in failed or rounded.get(k) is None for k in keys):
            out.append(None)
            continue
        center = rounded[keys[0]]
        slope_deg, aspect = _slope_aspect(center, rounded[keys[1]], rounded[keys[3]])
        out.append({
            "elevation_m": round(center, 1),
            "slope_deg": round(slope_deg, 1),
            "aspect": round(aspect, 1),
            "source": "srtm",
        })
    return out