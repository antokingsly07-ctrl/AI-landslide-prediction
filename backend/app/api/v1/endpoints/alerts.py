"""Alert endpoints: list, acknowledge, resolve."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_min_role
from app.db.session import get_db
from app.models.geo import User
from app.models.risk import Alert, NotificationLog
from app.schemas.domain import AlertOut
from app.services.audit_service import audit
from app.services.prediction_service import evaluate_auto_alerts

router = APIRouter()


def alert_to_out(a: Alert) -> AlertOut:
    def _json(s):
        import json

        try:
            return json.loads(s or "[]")
        except Exception:
            return []
    return AlertOut(
        id=a.id, title=a.title, message=a.message, severity=a.severity,
        alert_type=a.alert_type, status=a.status, risk_level=a.risk_level,
        cause=a.cause, recommended_action=a.recommended_action,
        affected_villages=_json(a.affected_villages),
        affected_roads=_json(a.affected_roads),
        affected_infrastructure=_json(a.affected_infrastructure),
        district_id=a.district_id, latitude=a.latitude, longitude=a.longitude,
        triggered_at=a.triggered_at, acknowledged_at=a.acknowledged_at,
    )


@router.get("", response_model=list[AlertOut])
def list_alerts(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    district_id: str | None = Query(default=None),
    limit: int = Query(default=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Alert)
    if status:
        q = q.where(Alert.status == status)
    if severity:
        q = q.where(Alert.severity == severity)
    if district_id:
        q = q.where(Alert.district_id == district_id)
    q = q.order_by(Alert.triggered_at.desc()).limit(limit)
    return [alert_to_out(a) for a in db.scalars(q).all()]


@router.get("/generate")
def generate_alerts(db: Session = Depends(get_db), user: User = Depends(require_min_role("disaster_mgmt"))):
    created = evaluate_auto_alerts(db)
    return {"created": len(created), "alerts": [alert_to_out(a) for a in created]}


@router.post("/{id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(id: str, user: User = Depends(require_min_role("field_official")),
                      db: Session = Depends(get_db)):
    alert = db.get(Alert, id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_by = user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.add(alert)
    db.add(NotificationLog(
        user_id=user.id, alert_id=alert.id, channel="in_app", provider="in_app",
        status="sent", recipient=user.email,
    ))
    audit(db, "alert.acknowledge", "alert", alert.id, f"Acknowledged alert", user.id)
    db.commit()
    db.refresh(alert)
    return alert_to_out(alert)


@router.post("/{id}/resolve", response_model=AlertOut)
def resolve_alert(id: str, user: User = Depends(require_min_role("district_admin")),
                  db: Session = Depends(get_db)):
    alert = db.get(Alert, id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert_to_out(alert)
