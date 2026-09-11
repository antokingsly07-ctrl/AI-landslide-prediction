"""Satellite data abstraction (Sentinel-2 via STAC) with mock fallback."""
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings


class SatelliteSource(ABC):
    name = "base"

    @abstractmethod
    def get_observation(self, lat: float, lon: float) -> dict:
        """Return a satellite-derived observation dict."""


class StacSentinel2Source(SatelliteSource):
    """Real Sentinel-2 coverage from the Microsoft Planetary Computer STAC catalog.

    Queries the most recent Sentinel-2 L2A scene acquired over the requested
    coordinates (keyless catalog search; SATELLITE_API_KEY optional). Returns
    genuine scene metadata (platform, acquisition time, cloud cover). Derived
    indices (vegetation change, deformation, moisture) require on-demand raster
    analysis and are left null; the record is real, not simulated.
    """

    name = "stac-sentinel2"

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or settings.SATELLITE_API_KEY
        self.base_url = (base_url or settings.SATELLITE_BASE_URL
                         or "https://planetarycomputer.microsoft.com/api/stac/v1/search")

    def _search_url(self) -> str:
        return self.base_url.rstrip("/")

    def get_observation(self, lat: float, lon: float) -> dict:
        buf = 0.2  # ~20 km search box
        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": [lon - buf, lat - buf, lon + buf, lat + buf],
            "datetime": "2020-01-01T00:00:00Z/..",
            "limit": 1,
            "sortby": [{"field": "datetime", "direction": "desc"}],
        }
        headers: dict = {}
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
        with httpx.Client(timeout=30) as client:
            resp = client.post(self._search_url(), json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
        features = body.get("features") or []
        if not features:
            raise RuntimeError("No recent Sentinel-2 scene found for this location")
        feat = features[0]
        props = feat.get("properties") or {}
        cloud = props.get("eo:cloud_cover")
        return {
            "latitude": lat,
            "longitude": lon,
            "source": self.name,
            "scene_id": str(feat.get("id") or ""),
            "satellite": str(props.get("platform") or "sentinel-2").upper(),
            "captured_at": str(props.get("datetime") or ""),
            "cloud_cover": float(cloud) if cloud is not None else None,
            "vegetation_change": None,
            "land_cover": "unknown",
            "deformation_mm": None,
            "moisture_index": None,
            "note": "Real Sentinel-2 STAC coverage metadata; derived indices require on-demand raster analysis",
            "is_demo": False,
        }


class MockSatelliteSource(SatelliteSource):
    """Simulated satellite observation clearly flagged as demo data."""

    name = "mock"

    def get_observation(self, lat: float, lon: float) -> dict:
        import random
        from datetime import datetime, timezone

        rng = random.Random(int(lat * 100) + int(lon * 100))
        return {
            "latitude": lat,
            "longitude": lon,
            "source": "mock",
            "vegetation_change": round(rng.uniform(-0.3, 0.3), 3),
            "land_cover": rng.choice(["forest", "shrubland", "cropland", "barren"]),
            "deformation_mm": round(max(0, rng.gauss(3, 6)), 2),
            "moisture_index": round(rng.uniform(0.2, 0.9), 3),
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "is_demo": True,
        }


def get_satellite_source() -> SatelliteSource:
    """Select satellite source: explicit SATELLITE_SOURCE, else real STAC (keyless)."""
    mode = (settings.SATELLITE_SOURCE or "auto").strip().lower()
    if mode == "mock":
        return MockSatelliteSource()
    if mode in ("auto", "stac", ""):
        return StacSentinel2Source()
    return MockSatelliteSource()