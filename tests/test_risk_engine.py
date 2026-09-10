"""Unit tests for the ML/risk engine helpers."""
from app.ml.risk_engine import RiskEngine
from app.ml.risk_utils import risk_color, risk_level_for_score


def test_risk_level_boundaries():
    assert risk_level_for_score(0) == "VERY_LOW"
    assert risk_level_for_score(20) == "VERY_LOW"
    assert risk_level_for_score(21) == "LOW"
    assert risk_level_for_score(61) == "HIGH"
    assert risk_level_for_score(81) == "CRITICAL"
    assert risk_level_for_score(100) == "CRITICAL"


def test_risk_level_custom_thresholds():
    custom = {"LOW": (0, 50), "HIGH": (51, 100)}
    assert risk_level_for_score(25, custom) == "LOW"
    assert risk_level_for_score(80, custom) == "HIGH"


def test_risk_color_palette():
    assert risk_color("CRITICAL") == "#a855f7"
    assert risk_color("VERY_LOW") == "#22c55e"
    # Unknown levels get a neutral fallback
    assert risk_color("WHATEVER") == "#64748b"


def test_explainable_engine_high_rainfall():
    engine = RiskEngine(model=None)
    features = {
        "rainfall_24h": 260, "soil_moisture": 92, "slope_deg": 42,
        "elevation_m": 900, "historical_frequency": 5,
        "distance_to_roads_m": 80, "deformation_mm": 25,
        "rainfall_6h": 90, "rainfall_1h": 30, "rain_3d": 350, "rain_7d": 550,
        "vegetation_change": 0.05,
    }
    res = engine.predict(features)
    assert res.risk_score >= 60
    assert res.factors  # explainable factors populated
    assert res.confidence > 0


def test_explainable_engine_calm():
    engine = RiskEngine(model=None)
    features = {
        "rainfall_24h": 5, "soil_moisture": 20, "slope_deg": 3,
        "elevation_m": 60, "historical_frequency": 0,
        "distance_to_roads_m": 900, "deformation_mm": 0,
        "rainfall_6h": 2, "rainfall_1h": 0, "rain_3d": 8, "rain_7d": 15,
        "vegetation_change": 0,
    }
    res = engine.predict(features)
    assert res.risk_score <= 40