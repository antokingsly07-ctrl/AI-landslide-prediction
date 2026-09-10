"""Prediction + alert orchestration service."""
import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml.risk_engine import RiskEngine
from app.ml.risk_utils import risk_level_for_score
from app.ml.model_manager import model_manager
from app.models.environment import LandslideHistory, RainfallRecord
from app.models.risk import Alert, AuditLog, RiskPrediction, RiskZone
from app.services.notification_service import notification_service
from app.core.config import settings


def _get_thresholds(db: Session | None = None):
    """Thresholds are configurable; currently defaults from settings, persisted in DB."""
    if db is not None:
        from app.services.config_service import get_risk_thresholds
        return get_risk_thresholds(db)
    return settings.RISK_LEVELS


def get_risk_engine(db: Session | None = None):
    md = model_manager.load()
    engine = RiskEngine(model=md, thresholds=_get_thresholds(db))
    return engine


def predict(features: dict, db: Session, district_id=None, lat=None, lon=None) -> RiskPrediction:
    """Compute a risk prediction, persist it, and return the model row."""
    engine = get_risk_engine(db)
    result = engine.predict(features)
    pred = RiskPrediction(
        latitude=lat,
        longitude=lon,
        district_id=district_id,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        confidence=result.confidence,
        factors=json.dumps(result.factors),
        factor_contributions=json.dumps(result.factor_contributions),
        recommended_action=result.recommended_action,
        model="explainable"
        if model_manager.model is None
        else getattr(model_manager, "model_name", "ml"),
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


def create_alert(
    db: Session,
    *,
    title: str,
    message: str,
    severity: str,
    alert_type: str,
    risk_level: str | None = None,
    cause: str | None = None,
    recommended_action: str | None = None,
    district_id: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    affected_villages: list | None = None,
    affected_roads: list | None = None,
    affected_infrastructure: list | None = None,
) -> Alert:
    alert = Alert(
        title=title,
        message=message,
        severity=severity,
        alert_type=alert_type,
        status="active",
        risk_level=risk_level,
        cause=cause,
        recommended_action=recommended_action,
        district_id=district_id,
        latitude=lat,
        longitude=lon,
        affected_villages=json.dumps(affected_villages or []),
        affected_roads=json.dumps(affected_roads or []),
        affected_infrastructure=json.dumps(affected_infrastructure or []),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    # in-app notification log
    from app.models.risk import NotificationLog

    notification_service.send("in_app", "", title, message)
    db.add(NotificationLog(
        alert_id=alert.id,
        channel="in_app",
        provider="in_app",
        status="sent",
        recipient="all",
    ))
    db.commit()
    # Real-time push to connected dashboards
    try:
        from app.realtime import broadcast_alert
        broadcast_alert({
            "id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity,
            "alert_type": alert.alert_type,
            "status": alert.status,
            "triggered_at": str(alert.triggered_at),
        })
    except Exception as e:  # pragma: no cover
        print(f"realtime broadcast error: {e}")
    return alert


def _cooldown_ok(db: Session, alert_type: str, district_id: str | None) -> bool:
    """Prevent alert spam using cooldown window."""
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.ALERT_COOLDOWN_MINUTES
    )
    recent = db.scalar(
        select(func.count(Alert.id)).where(
            Alert.alert_type == alert_type,
            Alert.triggered_at >= cutoff,
            (Alert.district_id == district_id) if district_id else Alert.district_id.is_(None),
        )
    )
    return (recent or 0) < 1


def evaluate_auto_alerts(db: Session, district_id: str | None = None) -> list[Alert]:
    """Check latest risk predictions and rainfall, generating alerts if thresholds hit."""
    from app.services.i18n import translate
    from app.models.environment import RainfallRecord

    thresholds = _get_thresholds(db)
    high_min = thresholds.get("HIGH", (61, 80))
    if isinstance(high_min, (tuple, list)):
        high_min = high_min[0]
    else:
        high_min = high_min.get("lower", 61)
    critical_min = thresholds.get("CRITICAL", (81, 100))
    if isinstance(critical_min, (tuple, list)):
        critical_min = critical_min[0]
    else:
        critical_min = critical_min.get("lower", 81)

    created = []

    # Highest recent risk prediction
    latest_risk = db.execute(
        select(RiskPrediction).order_by(RiskPrediction.predicted_at.desc()).limit(5)
    ).scalars().all()

    for pred in latest_risk:
        if pred.risk_score >= high_min and _cooldown_ok(db, "risk", pred.district_id):
            level = pred.risk_level
            sev = "warning" if pred.risk_score < critical_min else "critical"
            title = translate("risk_title", "en", severity=SEV_SHORT[sev].upper(), level=level)
            msg = translate("risk_message", "en",
                            level=level, location=f"({pred.latitude}, {pred.longitude})",
                            risk_score=int(pred.risk_score), action=pred.recommended_action)
            alert = create_alert(
                db,
                title=title,
                message=msg,
                severity=sev,
                alert_type="risk",
                risk_level=level,
                cause="AI risk prediction exceeded threshold",
                recommended_action=pred.recommended_action,
                district_id=pred.district_id,
                lat=pred.latitude,
                lon=pred.longitude,
            )
            created.append(alert)

    return created


SEV_SHORT = {"advisory": "Advisory", "watch": "Watch", "warning": "Warning", "critical": "Critical"}


def check_rainfall_alert(db: Session, district_id: str | None = None):
    """Create rainfall alert if latest rainfall is extreme (>= 200 mm/24h)."""
    from app.services.i18n import translate

    EXTREME_RAINFALL_MM = 200
    latest = db.execute(
        select(RainfallRecord).order_by(RainfallRecord.observed_at.desc()).limit(1)
    ).scalars().first()
    if latest and latest.rain_24h >= EXTREME_RAINFALL_MM and _cooldown_ok(db, "rainfall", latest.district_id):
        title = translate("rainfall_title", "en")
        msg = translate("rainfall_message", "en", rain=int(latest.rain_24h),
                        location=f"({latest.latitude}, {latest.longitude})")
        return create_alert(
            db, title=title, message=msg, severity="warning", alert_type="rainfall",
            risk_level="HIGH", cause="Extreme 24-hour rainfall",
            recommended_action="Monitor for flooding and slope failure",
            district_id=latest.district_id, lat=latest.latitude, lon=latest.longitude,
        )
    return None
