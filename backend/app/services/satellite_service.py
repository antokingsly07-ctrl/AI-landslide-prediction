"""Satellite data abstraction (Sentinel/Landsat) with mock fallback."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.core.config import settings


class SatelliteSource(ABC):
    name = "base"

    @abstractmethod
    def get_observation(self, lat: float, lon: float) -> dict:
        """Return a satellite-derived observation dict."""


class SentinelSource(SatelliteSource):
    """Sentinel-1/2 integration placeholder. Requires external connection."""

    name = "sentinel"

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or settings.SATELLITE_API_KEY
        self.base_url = base_url or settings.SATELLITE_BASE_URL

    def get_observation(self, lat: float, lon: float) -> dict:
        if not self.api_key:
            raise RuntimeError("SATELLITE_API_KEY not configured")
        # Real implementation would query the satellite catalog API.
        raise NotImplementedError("Sentinel live feed requires external connectivity")


class MockSatelliteSource(SatelliteSource):
    """Simulated satellite observation clearly flagged as demo data."""

    name = "mock"

    def get_observation(self, lat: float, lon: float) -> dict:
        import random

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
    if settings.SATELLITE_API_KEY:
        return SentinelSource()
    return MockSatelliteSource()
