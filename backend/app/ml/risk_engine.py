"""Explainable risk scoring engine.

Produces a 0-100 risk score from environmental + terrain features, with per-factor
contributions so officials can understand *why* a location is at risk.
"""
import math
from dataclasses import dataclass, field


@dataclass
class RiskResult:
    risk_score: float
    risk_level: str
    confidence: float
    factors: list[str]
    factor_contributions: list[dict]
    recommended_action: str


class RiskEngine:
    """Heuristic + ML-ready risk engine.

    When an ML model is available it is used to produce the score; otherwise a
    transparent weighted explainable model is used so the system works without
    a trained artifact.
    """

    def __init__(self, model=None, thresholds: dict | None = None):
        self.model = model
        self.thresholds = thresholds
        from app.ml.risk_utils import risk_level_for_score, recommended_action_for

        self._level_fn = risk_level_for_score
        self._action_fn = recommended_action_for

    # --- explainable heuristic scoring ---
    def _explainable_scoring(self, features: dict) -> dict:
        """Weighted additive scoring that is fully explainable."""
        contribs = {}

        # Rainfall (dominant trigger in North East monsoon climates)
        rain24 = features.get("rainfall_24h", 0.0) or features.get("rain_24h", 0.0)
        rain6 = features.get("rainfall_6h", 0.0) or features.get("rain_6h", 0.0)
        rain1 = features.get("rainfall_1h", 0.0) or features.get("rain_1h", 0.0)
        rain3d = features.get("rain_3d", 0.0)
        rain7d = features.get("rain_7d", 0.0)

        # Heavy 24h rainfall scoring
        if rain24 >= 250:
            rain_contrib = 30
            rain_factor = "Extreme 24-hour rainfall"
        elif rain24 >= 150:
            rain_contrib = 25
            rain_factor = "Heavy 24-hour rainfall"
        elif rain24 >= 100:
            rain_contrib = 18
            rain_factor = "High 24-hour rainfall"
        elif rain24 >= 50:
            rain_contrib = 10
            rain_factor = "Moderate 24-hour rainfall"
        else:
            rain_contrib = max(0.0, rain24 / 50.0 * 8)
            rain_factor = "Rainfall" if rain24 > 0 else ""
        contribs[rain_factor or "Rainfall"] = rain_contrib

        # Short-duration intense rainfall
        if rain1 >= 40 or rain6 >= 100:
            contribs["Intense short-duration rainfall"] = 10
        elif rain6 >= 60:
            contribs["Intense short-duration rainfall"] = 6

        # Cumulative rainfall
        if rain3d >= 300 or rain7d >= 500:
            contribs["High cumulative rainfall"] = 12
        elif rain3d >= 150 or rain7d >= 250:
            contribs["Cumulative rainfall"] = 7

        # Soil moisture
        sm = features.get("soil_moisture", 0.0)
        if sm >= 90:
            contribs["Saturated soil (very high moisture)"] = 25
        elif sm >= 75:
            contribs["High soil moisture"] = 20
        elif sm >= 55:
            contribs["Elevated soil moisture"] = 12
        elif sm >= 35:
            contribs["Rising soil moisture"] = 5

        # Slope
        slope = features.get("slope_deg", 0.0)
        if slope >= 40:
            contribs["Very steep slope"] = 20
        elif slope >= 30:
            contribs["Steep slope"] = 16
        elif slope >= 20:
            contribs["Moderate slope"] = 8
        elif slope >= 12:
            contribs["Gentle slope"] = 3

        # Elevation
        elev = features.get("elevation_m", 0.0)
        if elev >= 1500:
            contribs["High elevation terrain"] = 6
        elif elev >= 800:
            contribs["Elevated terrain"] = 3

        # Historical landslide activity
        hist = features.get("historical_frequency", 0.0)
        if hist >= 5:
            contribs["Frequent historical landslide activity"] = 15
        elif hist >= 3:
            contribs["Historical landslide activity"] = 10
        elif hist >= 1:
            contribs["Past landslide activity"] = 5

        # Distance to roads (cut slopes)
        dist = features.get("distance_to_roads_m", 500.0)
        if dist is not None and dist < 150:
            contribs["Close to road cut slopes"] = 8
        elif dist is not None and dist < 300:
            contribs["Near roads"] = 4

        # Satellite change detection
        veg = features.get("vegetation_change", 0.0)
        deform = features.get("deformation_mm", 0.0)
        if deform and deform >= 20:
            contribs["Recent terrain deformation"] = 14
        elif deform and deform >= 8:
            contribs["Minor terrain deformation"] = 7
        if abs(veg) >= 0.25:
            contribs["Significant vegetation change"] = 8

        total = sum(contribs.values())
        score = min(100.0, max(0.0, total))

        factors = [k for k, v in contribs.items() if v > 0]
        factor_contribs = [{"factor": k, "contribution": round(v, 1)} for k, v in contribs.items()]
        confidence = self._estimate_confidence(features)
        action = self._action_fn(self._level_fn(score, self.thresholds))
        return {
            "score": score,
            "factors": factors,
            "contributions": factor_contribs,
            "confidence": confidence,
            "action": action,
        }

    @staticmethod
    def _estimate_confidence(features: dict) -> float:
        """Confidence grows with data completeness."""
        keys = [
            "rainfall_24h", "soil_moisture", "slope_deg", "elevation_m",
            "historical_frequency",
        ]
        present = sum(1 for k in keys if features.get(k) is not None)
        base = 0.55 + 0.08 * present
        return round(min(0.97, base), 2)

    def predict(self, features: dict) -> RiskResult:
        """Return a RiskResult either from ML model or explainable engine."""
        if self.model is not None:
            try:
                score = self._ml_score(features)
            except Exception:
                score = None
            if score is not None:
                contribs = self._explainable_scoring(features)
                level = self._level_fn(score, self.thresholds)
                return RiskResult(
                    risk_score=round(min(100, max(0, score)), 1),
                    risk_level=level,
                    confidence=contribs["confidence"],
                    factors=contribs["factors"],
                    factor_contributions=contribs["contributions"],
                    recommended_action=self._action_fn(level),
                )
        res = self._explainable_scoring(features)
        return RiskResult(
            risk_score=round(res["score"], 1),
            risk_level=self._level_fn(res["score"], self.thresholds),
            confidence=res["confidence"],
            factors=res["factors"],
            factor_contributions=res["contributions"],
            recommended_action=res["action"],
        )

    def _ml_score(self, features: dict) -> float:
        import numpy as np

        features = dict(features)
        features.setdefault("rain_24h", features.get("rainfall_24h", 0.0))
        features.setdefault("rain_6h", features.get("rainfall_6h", 0.0))
        features.setdefault("rain_1h", features.get("rainfall_1h", 0.0))
        feature_names = getattr(self.model.feature_names_in_, None)
        expected = list(feature_names) if feature_names is not None else list(self.model.named_steps.get("clf", self.model).feature_names_in_ or [])
        row = []
        for name in expected:
            row.append(features.get(name, 0.0))
        X = np.array([row])
        p = self.model.predict_proba(X)[0]
        return float(p[1] * 100.0 if p.shape[0] > 1 else self.model.predict(X)[0])


def build_sample_features_from_context(
    rainfall: dict | None = None,
    soil_moisture: float | None = None,
    slope: float | None = None,
    elevation: float | None = None,
    historical: float | None = None,
    distance_road: float | None = None,
    vegetation_change: float | None = None,
    deformation: float | None = None,
) -> dict:
    """Assemble a feature dict combining live + terrain data."""
    rf = rainfall or {}
    return {
        "rainfall_1h": rf.get("rain_1h") or rf.get("rainfall_1h") or 0.0,
        "rainfall_6h": rf.get("rain_6h") or rf.get("rainfall_6h") or 0.0,
        "rainfall_24h": rf.get("rain_24h") or rf.get("rainfall_24h") or 0.0,
        "rain_3d": rf.get("rain_3d") or 0.0,
        "rain_7d": rf.get("rain_7d") or 0.0,
        "soil_moisture": soil_moisture or 0.0,
        "slope_deg": slope or 0.0,
        "elevation_m": elevation or 0.0,
        "historical_frequency": historical or 0.0,
        "distance_to_roads_m": distance_road if distance_road is not None else 0.0,
        "vegetation_change": vegetation_change or 0.0,
        "deformation_mm": deformation or 0.0,
    }
