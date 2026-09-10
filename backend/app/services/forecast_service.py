"""Time-series forecasting for rainfall and risk using lightweight statistical models.

Uses moving averages + linear extrapolation (no heavy deps) so it runs in the
slim Vercel/Docker runtime while still producing useful 3-7 day outlooks.
"""
from datetime import datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session


def series_average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def moving_average(values: list[float], window: int = 3) -> float:
    if not values:
        return 0.0
    window = min(window, len(values))
    tail = values[-window:]
    return round(sum(tail) / len(tail), 2)


def linear_trend(values: list[float]) -> float:
    """Slope of a least-squares line; positive = rising, negative = falling."""
    n = len(values)
    if n < 2:
        return 0.0
    idx = list(range(n))
    x_mean = mean(idx)
    y_mean = mean(values)
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(idx, values))
    den = sum((x - x_mean) ** 2 for x in idx)
    if den == 0:
        return 0.0
    return round(num / den, 3)


def forecast_rainfall(db: Session, district_id: str | None = None, days: int = 5) -> dict:
    """Forecast daily rainfall totals for the next `days` days."""
    from app.models.environment import RainfallRecord

    q = select(RainfallRecord).order_by(RainfallRecord.observed_at.desc()).limit(120)
    if district_id:
        q = q.where(RainfallRecord.district_id == district_id)
    rows = db.scalars(q).all()
    if not rows:
        return {"district_id": district_id, "points": [], "method": "no-data"}

    # Build daily aggregates chronologically
    daily: dict[str, float] = {}
    for r in reversed(rows):
        day = r.observed_at.date().isoformat()
        daily[day] = daily.get(day, 0.0) + (r.rain_24h or 0.0)

    ordered = [daily[k] for k in sorted(daily)]
    if len(ordered) < 3:
        base = ordered[-1] if ordered else 0.0
    else:
        base = moving_average(ordered, min(5, len(ordered)))
    trend = linear_trend(ordered)

    points = []
    last = base
    for i in range(1, days + 1):
        # dampen the trend as horizon grows, add monsoon seasonality bump
        damped = trend * (1.0 - 0.2 * (i - 1)) if trend > 0 else trend * 0.6
        val = max(0.0, round(last + damped, 1))
        points.append({
            "date": (datetime.now() + timedelta(days=i)).date().isoformat(),
            "rain_24h_forecast": val,
        })
        last = val

    return {
        "district_id": district_id,
        "days": days,
        "points": points,
        "method": "moving-average + linear trend",
        "recent_avg_24h": series_average(ordered[-3:]),
        "trend_slope_per_day": trend,
    }


def forecast_risk(db: Session, days: int = 7) -> dict:
    """Build a 7-day risk outlook from recent rainfall forecasts + historical risk."""
    from app.models.risk import RiskPrediction
    from app.models.environment import RainfallRecord

    forecast = forecast_rainfall(db, days=days)
    rain_pts = forecast.get("points", [])

    # Recent risk baseline
    preds = db.scalars(
        select(RiskPrediction).order_by(RiskPrediction.predicted_at.desc()).limit(20)
    ).all()
    recent_scores = [p.risk_score for p in preds]
    base_score = moving_average(recent_scores, 7) if recent_scores else 40.0

    recent_rain = db.scalars(
        select(RainfallRecord).order_by(RainfallRecord.observed_at.desc()).limit(7)
    ).all()
    rain_avg = series_average([r.rain_24h or 0 for r in recent_rain])

    points = []
    for i, rp in enumerate(rain_pts):
        # rainfall drives risk with a couple of days of persistence
        rain_influence = (rp["rain_24h_forecast"] - rain_avg) * 0.28
        predicted = max(0.0, min(100.0, round(base_score + rain_influence * (1 - 0.1 * i), 1)))
        level = "VERY_LOW"
        if predicted >= 81:
            level = "CRITICAL"
        elif predicted >= 61:
            level = "HIGH"
        elif predicted >= 41:
            level = "MODERATE"
        elif predicted >= 21:
            level = "LOW"
        points.append({"date": rp["date"], "risk_score": predicted, "risk_level": level})

    return {
        "days": days,
        "baseline_risk_score": base_score,
        "points": points,
        "forecast_rainfall": forecast,
    }