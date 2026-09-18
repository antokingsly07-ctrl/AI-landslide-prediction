"""Emergency-response priority scoring shared by incident endpoints and the
news automation pipeline."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.risk import EmergencyResponse, FieldReport, Incident


def priority_reasons(inc: Incident, reports_count: int, population_affected: int) -> list[str]:
    """Human-readable justification for an incident's emergency priority."""
    reasons: list[str] = []

    sev_names = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}
    if inc.severity in sev_names:
        reasons.append(
            f"{sev_names[inc.severity]} severity {inc.incident_type.replace('_', ' ')} incident"
        )

    status_reasons = {
        "reported": "Incident newly reported",
        "verified": "Incident verified",
        "monitoring": "Under active monitoring",
        "response": "Emergency response phase in progress",
    }
    if inc.status in status_reasons:
        reasons.append(status_reasons[inc.status])

    if population_affected > 0:
        reasons.append(f"~{population_affected:,} people potentially affected")

    if reports_count > 0:
        reasons.append(
            f"{reports_count} field report{'s' if reports_count != 1 else ''} "
            f"corroborate{'s' if reports_count == 1 else ''} this incident"
        )

    hazard_hints = {
        "blocked_road": "Road accessibility disrupted",
        "flooding": "Flooding affects inhabited area",
        "slope_crack": "Active slope cracking",
        "slope_movement": "Ongoing slope movement",
        "rockfall": "Rockfall hazard on hillside",
        "sinkhole": "Ground collapse risk",
    }
    if inc.incident_type in hazard_hints:
        reasons.append(hazard_hints[inc.incident_type])

    if not reasons:
        reasons.append("Routine situational monitoring")
    return reasons


def compute_priority(inc: Incident, db: Session) -> dict:
    """Score 0-100 for emergency response prioritisation."""
    er = db.scalar(select(EmergencyResponse).where(EmergencyResponse.incident_id == inc.id))
    reports_count = db.scalar(
        select(func.count(FieldReport.id)).where(FieldReport.incident_id == inc.id)
    ) or 0

    sev_score = {"low": 10, "medium": 25, "high": 50, "critical": 75}.get(inc.severity, 25)
    status_score = {"reported": 30, "verified": 45, "monitoring": 60, "response": 75, "resolved": 5}.get(inc.status, 30)
    pop_score = min(20, (er.population_affected if er else 0) / 10000 * 20)
    report_score = min(15, reports_count * 3)
    score = min(100, sev_score * 0.7 + status_score * 0.3 + pop_score + report_score)

    level = "low"
    if score >= 80:
        level = "immediate"
    elif score >= 60:
        level = "high"
    elif score >= 40:
        level = "medium"
    return {
        "priority_score": round(score, 1),
        "priority_class": level,
        "reasons": priority_reasons(inc, reports_count, er.population_affected if er else 0),
    }