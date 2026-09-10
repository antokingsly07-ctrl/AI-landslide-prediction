"""Incident management endpoints with lifecycle + emergency prioritisation."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_min_role
from app.db.session import get_db
from app.models.geo import User
from app.models.risk import EmergencyResponse, FieldReport, Incident
from app.schemas.domain import IncidentCreate, IncidentOut, IncidentUpdate
from app.services.audit_service import audit
from app.services.i18n import translate
from app.services.prediction_service import create_alert

router = APIRouter()

INCIDENT_STATUSES = ["reported", "verified", "monitoring", "response", "resolved"]
VALID_TYPES = ["slope_crack", "slope_movement", "rockfall", "blocked_road", "flooding", "other"]


def incident_to_out(inc: Incident, db: Session) -> IncidentOut:
    er = db.scalar(select(EmergencyResponse).where(EmergencyResponse.incident_id == inc.id))
    reports_count = db.scalar(
        select(__import__("sqlalchemy").func.count(FieldReport.id)).where(FieldReport.incident_id == inc.id)
    ) or 0
    return IncidentOut(
        id=inc.id, incident_type=inc.incident_type, status=inc.status,
        severity=inc.severity, verification_status=inc.verification_status,
        description=inc.description, latitude=inc.latitude, longitude=inc.longitude,
        reported_by=inc.reported_by,
        reporter_name=inc.reporter.full_name if inc.reporter else None,
        assigned_to=inc.assigned_to,
        assignee_name=inc.assignee.full_name if inc.assignee else None,
        district_id=inc.district_id,
        reported_at=inc.reported_at, resolved_at=inc.resolved_at,
        priority_score=er.priority_score if er else None,
        priority_class=er.priority_class if er else None,
    )


def compute_priority(inc: Incident, db: Session) -> dict:
    """Score 0-100 for emergency response prioritisation."""
    er = db.scalar(select(EmergencyResponse).where(EmergencyResponse.incident_id == inc.id))
    reports_count = db.scalar(
        select(__import__("sqlalchemy").func.count(FieldReport.id)).where(FieldReport.incident_id == inc.id)
    ) or 0

    sev_score = {"low": 10, "medium": 30, "high": 55, "critical": 80}.get(inc.severity, 30)
    status_score = {"reported": 35, "verified": 45, "monitoring": 55, "response": 70, "resolved": 5}.get(inc.status, 30)
    pop_score = min(20, (er.population_affected if er else 0) / 10000 * 20)
    report_score = min(15, reports_count * 3)
    score = min(100, sev_score * 0.5 + status_score * 0.2 + pop_score + report_score)

    level = "low"
    if score >= 80:
        level = "immediate"
    elif score >= 60:
        level = "high"
    elif score >= 40:
        level = "medium"
    return {"priority_score": round(score, 1), "priority_class": level}


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    district_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Incident).options(
        joinedload(Incident.reporter), joinedload(Incident.assignee)
    )
    if district_id:
        q = q.where(Incident.district_id == district_id)
    if status:
        q = q.where(Incident.status == status)
    q = q.order_by(Incident.reported_at.desc())
    rows = db.scalars(q).all()
    return [incident_to_out(inc, db) for inc in rows]


@router.get("/emergency-priorities")
def emergency_priorities(db: Session = Depends(get_db),
                         user: User = Depends(require_min_role("district_admin"))):
    rows = db.scalars(
        select(Incident).where(Incident.status != "resolved")
        .order_by(Incident.reported_at.desc()).limit(50)
    ).all()
    out = []
    from app.models.risk import RiskPrediction

    for inc in rows:
        er = db.scalar(select(EmergencyResponse).where(EmergencyResponse.incident_id == inc.id))
        pred = db.scalar(
            select(RiskPrediction).where(RiskPrediction.latitude == inc.latitude)
            .order_by(RiskPrediction.predicted_at.desc()).limit(1)
        ) if inc.latitude else None
        reports_count = db.scalar(
            select(__import__("sqlalchemy").func.count(FieldReport.id)).where(FieldReport.incident_id == inc.id)
        ) or 0
        out.append({
            "incident_id": inc.id,
            "location": f"({inc.latitude}, {inc.longitude})" if inc.latitude else "Unknown",
            "incident_type": inc.incident_type,
            "risk_score": pred.risk_score if pred else (er.priority_score if er else 0),
            "risk_level": pred.risk_level if pred else "LOW",
            "population_affected": er.population_affected if er else 0,
            "infrastructure_affected": [],
            "road_accessibility": inc.incident_type,
            "num_reports": reports_count,
            "priority_score": er.priority_score if er else 0,
            "priority_class": er.priority_class if er else "low",
            "recommended_response": "Dispatch assessment team" if (er and er.priority_score >= 60) else "Monitor",
        })
    return sorted(out, key=lambda x: x["priority_score"], reverse=True)


@router.post("", response_model=IncidentOut, status_code=201)
def create_incident(payload: IncidentCreate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if payload.incident_type not in VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"incident_type must be one of {VALID_TYPES}")
    inc = Incident(
        incident_type=payload.incident_type, severity=payload.severity,
        latitude=payload.latitude, longitude=payload.longitude,
        description=payload.description, district_id=payload.district_id or user.district_id,
        reported_by=user.id, status="reported", verification_status="pending",
    )
    db.add(inc)
    db.flush()
    # auto-prioritise
    prio = compute_priority(inc, db)
    db.add(EmergencyResponse(
        incident_id=inc.id, priority_score=prio["priority_score"],
        priority_class=prio["priority_class"], population_affected=0,
    ))
    audit(db, "incident.create", "incident", inc.id, f"Created {inc.incident_type}", user.id)
    db.commit()
    db.refresh(inc)
    return incident_to_out(inc, db)


@router.patch("/{id}", response_model=IncidentOut)
def update_incident(id: str, payload: IncidentUpdate, user: User = Depends(require_min_role("field_official")),
                    db: Session = Depends(get_db)):
    inc = db.get(Incident, id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if payload.status is not None:
        if payload.status not in INCIDENT_STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of {INCIDENT_STATUSES}")
        inc.status = payload.status
        if payload.status == "resolved":
            inc.resolved_at = datetime.now(timezone.utc)
    if payload.severity is not None:
        inc.severity = payload.severity
    if payload.assigned_to is not None:
        inc.assigned_to = payload.assigned_to
    if payload.verification_status is not None:
        inc.verification_status = payload.verification_status
        if payload.verification_status == "verified":
            # raise alert for confirmed report
            lang = user.preferred_language or "en"
            title = translate("report_title", lang, type=inc.incident_type.replace("_", " "))
            msg = translate("report_message", lang, severity=inc.severity,
                            type=inc.incident_type.replace("_", " "),
                            location=f"({inc.latitude}, {inc.longitude})")
            create_alert(
                db, title=title, message=msg, severity="watch", alert_type="confirmed_report",
                risk_level="MODERATE", cause="Confirmed field report",
                recommended_action="Dispatch assessment team",
                district_id=inc.district_id, lat=inc.latitude, lon=inc.longitude,
            )
    if payload.description is not None:
        inc.description = payload.description
    db.add(inc)

    # recompute priority when severity/status change
    prio = compute_priority(inc, db)
    er = db.scalar(select(EmergencyResponse).where(EmergencyResponse.incident_id == inc.id))
    if er:
        er.priority_score = prio["priority_score"]
        er.priority_class = prio["priority_class"]
        db.add(er)

    audit(db, "incident.update", "incident", inc.id, f"Updated incident: status={inc.status}", user.id)
    db.commit()
    db.refresh(inc)
    return incident_to_out(inc, db)
