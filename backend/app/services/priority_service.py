"""Emergency-response priority scoring shared by incident endpoints and the
news automation pipeline."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.risk import EmergencyResponse, FieldReport, Incident


def compute_priority(inc: Incident, db: Session) -> dict:
    """Score 0-100 for emergency response prioritisation."""
    er = db.scalar(select(EmergencyResponse).where(EmergencyResponse.incident_id == inc.id))
    reports_count = db.scalar(
        select(func.count(FieldReport.id)).where(FieldReport.incident_id == inc.id)
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