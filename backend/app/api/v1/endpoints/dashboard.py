"""Dashboard summary and analytics endpoints."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, require_min_role
from app.db.session import get_db
from app.models.environment import RainfallRecord, Sensor, SoilMoistureRecord
from app.models.geo import District, User, Village
from app.models.risk import (
    Alert,
    EmergencyResponse,
    Incident,
    RiskPrediction,
    RiskZone,
    Road,
)
from app.schemas.domain import DashboardSummary

router = APIRouter()


def _day_expr(col):
    """Portable date truncation: func.date() works on SQLite, CAST works on Postgres."""
    if settings.is_sqlite:
        return func.date(col)
    return cast(col, Date)


def _day_key(value) -> str:
    """Normalize a date/datetime/string value to YYYY-MM-DD for chart grouping."""
    if value is None:
        return ""
    s = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return s[:10]


@router.get("/summary", response_model=DashboardSummary)
def summary(
    district_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    def rfilter(col):
        return col == district_id if district_id else col.isnot(None)

    critical = db.scalar(select(func.count(RiskZone.id)).where(
        RiskZone.risk_level == "CRITICAL", rfilter(RiskZone.district_id)
    )) or 0
    high = db.scalar(select(func.count(RiskZone.id)).where(
        RiskZone.risk_level == "HIGH", rfilter(RiskZone.district_id)
    )) or 0
    active_incidents = db.scalar(select(func.count(Incident.id)).where(
        Incident.status.in_(["reported", "verified", "monitoring", "response"]),
        rfilter(Incident.district_id),
    )) or 0
    roads_blocked = db.scalar(select(func.count(Road.id)).where(
        Road.status.in_(["blocked", "severely_blocked"]), rfilter(Road.district_id)
    )) or 0
    villages_at_risk = db.scalar(select(func.count(Village.id)).where(
        Village.risk_score >= 61, rfilter(Village.district_id)
    )) or 0
    alerts = db.scalar(select(func.count(Alert.id)).where(
        Alert.status == "active", rfilter(Alert.district_id)
    )) or 0
    max_risk = db.scalar(select(func.max(RiskZone.risk_score)).where(
        rfilter(RiskZone.district_id)
    )) or 0.0

    base = select(RiskZone)
    if district_id:
        base = base.where(RiskZone.district_id == district_id)
    total_districts = db.scalar(select(func.count(District.id))) or 0
    total_sensors = db.scalar(select(func.count(Sensor.id)).where(
        Sensor.district_id.isnot(None) if not district_id else Sensor.district_id == district_id
    )) or 0

    return DashboardSummary(
        critical_zones=critical,
        high_risk_zones=high,
        active_incidents=active_incidents,
        roads_blocked=roads_blocked,
        villages_at_risk=villages_at_risk,
        active_alerts=alerts,
        total_districts=total_districts,
        total_sensors=total_sensors,
        max_risk_score=round(float(max_risk), 1),
        updated_at=datetime.now(timezone.utc),
    )


@router.get("/charts/rainfall")
def rainfall_trend(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    rows = db.execute(
        select(
            _day_expr(RainfallRecord.observed_at),
            func.avg(RainfallRecord.rain_24h),
            func.avg(RainfallRecord.rain_6h),
        ).where(RainfallRecord.observed_at >= cutoff)
        .group_by(_day_expr(RainfallRecord.observed_at))
    ).all()
    return [
        {
            "date": _day_key(r[0]),
            "rain_24h": round(float(r[1] or 0), 1),
            "rain_6h": round(float(r[2] or 0), 1),
        }
        for r in rows
    ]


@router.get("/charts/soil_moisture")
def soil_moisture_trend(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    rows = db.execute(
        select(
            _day_expr(SoilMoistureRecord.observed_at),
            func.avg(SoilMoistureRecord.moisture_percent),
        ).where(SoilMoistureRecord.observed_at >= cutoff)
        .group_by(_day_expr(SoilMoistureRecord.observed_at))
    ).all()
    return [
        {"date": _day_key(r[0]), "moisture": round(float(r[1] or 0), 1)}
        for r in rows
    ]


@router.get("/charts/district_risk")
def district_risk(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(District.name, District.risk_score, District.id).order_by(District.risk_score.desc())
    ).all()
    return [{"district": r[0], "risk_score": round(float(r[1] or 0), 1), "id": r[2]} for r in rows]


@router.get("/charts/risk_trend")
def risk_trend(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    rows = db.execute(
        select(
            _day_expr(RiskPrediction.predicted_at),
            func.avg(RiskPrediction.risk_score),
        ).where(RiskPrediction.predicted_at >= cutoff)
        .group_by(_day_expr(RiskPrediction.predicted_at))
    ).all()
    return [
        {"date": _day_key(r[0]), "risk": round(float(r[1] or 0), 1)}
        for r in rows
    ]


@router.get("/charts/incidents")
def incidents_trend(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    rows = db.execute(
        select(
            _day_expr(Incident.reported_at),
            func.count(Incident.id),
        ).where(Incident.reported_at >= cutoff)
        .group_by(_day_expr(Incident.reported_at))
    ).all()
    return [
        {"date": _day_key(r[0]), "count": int(r[1])}
        for r in rows
    ]


@router.get("/charts/road_connectivity")
def road_connectivity(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Road.status, func.count(Road.id)).group_by(Road.status)
    ).all()
    return [{"status": r[0], "count": int(r[1])} for r in rows]


@router.get("/charts/alerts")
def alert_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)
    ).all()
    return [{"severity": r[0], "count": int(r[1])} for r in rows]


@router.get("/emergency/priorities")
def emergency_priorities(
    db: Session = Depends(get_db),
    user: User = Depends(require_min_role("district_admin")),
):
    rows = db.execute(
        select(EmergencyResponse, Incident)
        .join(Incident, EmergencyResponse.incident_id == Incident.id)
        .order_by(EmergencyResponse.priority_score.desc())
    ).all()
    out = []
    for er, inc in rows:
        out.append({
            "incident_id": er.incident_id,
            "location": f"({inc.latitude}, {inc.longitude})" if inc.latitude else "Unknown",
            "incident_type": inc.incident_type,
            "severity": inc.severity,
            "population_affected": er.population_affected,
            "priority_score": round(er.priority_score, 1),
            "priority_class": er.priority_class,
            "status": er.status,
            "incident_status": inc.status,
        })
    return out
