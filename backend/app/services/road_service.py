"""Road status automation + landslide blockage prediction.

* ``apply_road_status_from_news`` matches news articles about a Meghalaya road
  and updates its live status (open / restricted / blocked) with history,
  audit log and alert — the same status flow field officials use manually.
* ``recompute_road_prediction`` scores every road for likely landslide blockage
  from nearby risk zones, recent rainfall, district risk and fresh news-driven
  incidents near the route.
"""
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.environment import RainfallRecord
from app.models.risk import Alert, Incident, Road, RoadStatusHistory, RiskZone
from app.services.audit_service import audit
from app.services.prediction_service import create_alert

VALID_STATUSES = ["open", "restricted", "blocked", "severely_blocked", "unknown"]

BLOCKED_HINTS = ("block", "cut off", "cut-off", "closed", "landslide", "mudslide",
                 "landslip", "buried", "caved", "disrupt", "obstruct", "wash away",
                 "swept away", "damaged", "broken")
OPEN_HINTS = ("reopen", "re-opened", "cleared", "clear for traffic", "open to traffic",
              "restored", "traffic resumed", "movement restored", "fully restored")
RESTRICTED_HINTS = ("restricted", "one way", "partial", "caution", "single lane",
                    "slow movement", "heavy vehicle", "divert")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip("-–— "))


def _road_keys(name: str) -> list[str]:
    """Match keys extracted from a road name, longest-first."""
    keys = []
    name_l = _norm(name)
    stem = name_l.split(" (")[0].strip()
    keys.append(name_l)
    keys.append(stem)
    road_no = re.findall(r"nh[- ]?(\d+)|ph[- ]?(\d+)|sh[- ]?(\d+)|highway[- ]?(\d+)", name_l, re.I)
    for n in road_no:
        n = next((x for x in n if x), "")
        if n:
            keys.append(f"nh-{n}")
            keys.append(f"nh {n}")
            keys.append(f"national highway {n}")
            keys.append(f"highway {n}")
    for sep in ("-", "–", "—"):
        keys.append(name_l.replace(sep, " "))
    keys = sorted(dict.fromkeys(k for k in keys if k), key=len, reverse=True)
    return keys


def match_road_from_text(db: Session, text: str) -> Road | None:
    if not text:
        return None
    t = _norm(text)
    for road in db.scalars(select(Road)).all():
        for key in _road_keys(road.name):
            if key in t and len(key) >= 4:
                return road
    return None


def _direction_from_text(text: str) -> str | None:
    t = _norm(text)
    if any(h in t for h in OPEN_HINTS):
        return "open"
    if any(h in t for h in RESTRICTED_HINTS):
        return "restricted"
    if any(h in t for h in BLOCKED_HINTS):
        return "blocked"
    return None


def apply_road_status_from_news(db: Session, *, title: str, description: str) -> dict | None:
    """Update a matched road's status from a news article. No-op otherwise."""
    if not settings.NEWS_ROAD_STATUS_ENABLED:
        return None
    text = f"{title or ''} {description or ''}"
    road = match_road_from_text(db, text)
    if road is None:
        return None
    direction = _direction_from_text(text)
    if direction is None or direction == road.status:
        return None
    old_status = road.status
    road.status = direction
    road.last_status_update = datetime.now(timezone.utc)
    db.add(road)
    db.add(RoadStatusHistory(
        road_id=road.id, status=direction,
        changed_by=None,
        reason=f"News auto-update: {_norm(title)[:180]}",
    ))
    audit(db, "road.status", "road", road.id, f"{old_status} -> {direction} (news)", None)
    create_alert(
        db, title=f"Road status changed: {road.name}",
        message=f"{road.name} is now {direction} (per news reports).",
        severity="warning" if direction != "open" else "advisory",
        alert_type="road", risk_level="HIGH" if direction != "open" else "NORMAL",
        cause=f"News report flagged route as {direction}",
        recommended_action="Verify on ground and reroute traffic",
        district_id=road.district_id, lat=road.latitude, lon=road.longitude,
        affected_roads=[road.name],
    )
    db.commit()
    return {"road": road.name, "status": direction, "old_status": old_status}


def _distance_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5


def recompute_road_prediction(db: Session) -> list[dict]:
    """Score each road for probable landslide blockage (0-100)."""
    zones = db.scalars(select(RiskZone)).all()
    incidents = db.scalars(
        select(Incident).where(Incident.status != "resolved",
                               Incident.source == "auto_news")
    ).all()
    rainfalls = {}
    for rr in db.scalars(
        select(RainfallRecord).order_by(RainfallRecord.observed_at.desc()).limit(200)
    ):
        if rr.district_id and rr.district_id not in rainfalls:
            rainfalls[rr.district_id] = rr.rain_24h or 0.0

    results = []
    for road in db.scalars(select(Road)).all():
        lat, lon = road.latitude, road.longitude
        zone_score = road.district.risk_score if road.district else 0.0
        near_incidents = 0
        for inc in incidents:
            if inc.latitude and inc.longitude and lat and lon \
                    and _distance_deg(lat, lon, inc.latitude, inc.longitude) <= 0.30:
                near_incidents += 1
        nearest_zone = None
        if lat and lon:
            nearest_zone = min(
                zones,
                key=lambda z: _distance_deg(lat, lon, z.latitude or 0, z.longitude or 0),
                default=None,
            )
            if nearest_zone is not None and nearest_zone.latitude:
                if _distance_deg(lat, lon, nearest_zone.latitude, nearest_zone.longitude) > 0.40:
                    nearest_zone = None
        if nearest_zone is not None:
            zone_score = nearest_zone.risk_score
        rain24 = rainfalls.get(road.district_id, 0.0)

        zone_c = min(100.0, zone_score)
        rain_c = min(100.0, rain24 / 200.0 * 100.0)
        inc_c = min(100.0, near_incidents * 25.0)
        score = round(min(100.0, 0.40 * zone_c + 0.30 * rain_c + 0.20 * zone_c + 0.10 * inc_c), 1)
        if score >= 75:
            level = "critical"
        elif score >= 55:
            level = "high"
        elif score >= 35:
            level = "moderate"
        else:
            level = "low"

        road.prediction_score = score
        road.prediction_level = level
        road.last_prediction_at = datetime.now(timezone.utc)
        db.add(road)
        results.append({
            "id": road.id, "name": road.name, "road_type": road.road_type,
            "status": road.status, "district_id": road.district_id,
            "district_name": road.district.name if road.district else None,
            "latitude": road.latitude, "longitude": road.longitude,
            "prediction_score": score, "prediction_level": level,
            "factors": {
                "zone_risk_score": round(zone_c, 1),
                "rain_24h_mm": round(rain24, 1),
                "nearby_incidents": near_incidents,
            },
        })
    db.commit()
    results.sort(key=lambda r: r["prediction_score"], reverse=True)
    return results


def raise_road_prediction_alerts(db: Session) -> int:
    """Empower the monitoring loop: alert when a route risks landslide blockage."""
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.ALERT_COOLDOWN_MINUTES
    )
    raised = 0
    for road in db.scalars(select(Road).where(Road.prediction_level.in_(["high", "critical"]))):
        recent = db.scalar(
            select(func.count(Alert.id)).where(
                Alert.alert_type == "road_prediction",
                Alert.triggered_at >= cutoff,
                Alert.affected_roads.like(f"%{road.name}%"),
            )
        )
        if recent:
            continue
        critical = road.prediction_level == "critical"
        create_alert(
            db, title=f"Possible landslide blockage: {road.name}",
            message=(f"{road.name} has a {road.prediction_score:.0f}/100 "
                     f"{road.prediction_level} risk of landslide blockage "
                     "from slope instability and recent rainfall."),
            severity="critical" if critical else "warning",
            alert_type="road_prediction",
            risk_level=road.prediction_level.upper(),
            cause="Predictive road blockage model",
            recommended_action="Inspect slope, position clearance crew, communicate with district control",
            district_id=road.district_id, lat=road.latitude, lon=road.longitude,
            affected_roads=[road.name],
        )
        raised += 1
    return raised