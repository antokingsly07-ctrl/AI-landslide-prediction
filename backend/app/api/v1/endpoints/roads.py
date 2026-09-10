"""Road endpoints: list, update status, connectivity."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_min_role
from app.db.session import get_db
from app.models.geo import User, Village
from app.models.risk import Road, RoadStatusHistory
from app.schemas.domain import RoadOut, RoadStatusUpdate
from app.services.audit_service import audit
from app.services.i18n import ROAD_STATUS_LABELS, translate
from app.services.prediction_service import create_alert

router = APIRouter()

VALID_STATUSES = ["open", "restricted", "blocked", "severely_blocked", "unknown"]


@router.get("", response_model=list[RoadOut])
def list_roads(
    status: str | None = Query(default=None),
    district_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Road).options(joinedload(Road.district))
    if status:
        q = q.where(Road.status == status)
    if district_id:
        q = q.where(Road.district_id == district_id)
    rows = db.scalars(q).all()
    return [
        RoadOut(
            id=r.id, name=r.name, road_type=r.road_type, status=r.status,
            population_served=r.population_served, alternative_route=r.alternative_route,
            priority_score=r.priority_score, latitude=r.latitude, longitude=r.longitude,
            district_id=r.district_id, last_status_update=r.last_status_update,
        )
        for r in rows
    ]


@router.get("/connectivity")
def connectivity(
    district_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Road)
    if district_id:
        q = q.where(Road.district_id == district_id)
    roads = db.scalars(q).all()
    blocked = [r for r in roads if r.status in ("blocked", "severely_blocked")]
    # villages that are in districts with blocked roads (isolation proxy)
    isolated_villages = 0
    if blocked:
        district_ids = {r.district_id for r in blocked}
        isolated_villages = db.scalar(
            select(__import__("sqlalchemy").func.count(Village.id)).where(Village.district_id.in_(district_ids))
        ) or 0
    return {
        "total_roads": len(roads),
        "open": sum(1 for r in roads if r.status == "open"),
        "restricted": sum(1 for r in roads if r.status == "restricted"),
        "blocked": len(blocked),
        "sev_blocked": sum(1 for r in roads if r.status == "severely_blocked"),
        "unknown": sum(1 for r in roads if r.status == "unknown"),
        "isolated_villages_estimate": isolated_villages,
    }


@router.patch("/{id}/status", response_model=RoadOut)
def update_road_status(id: str, payload: RoadStatusUpdate,
                       user: User = Depends(require_min_role("field_official")),
                       db: Session = Depends(get_db)):
    road = db.get(Road, id)
    if not road:
        raise HTTPException(status_code=404, detail="Road not found")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Status must be one of {VALID_STATUSES}")
    old_status = road.status
    road.status = payload.status
    road.last_status_update = datetime.now(timezone.utc)
    db.add(road)
    db.add(RoadStatusHistory(
        road_id=road.id, status=payload.status,
        changed_by=user.id, reason=payload.reason,
    ))
    audit(db, "road.status", "road", road.id, f"{old_status} -> {payload.status}", user.id)

    # alert on road blockage
    if payload.status in ("blocked", "severely_blocked"):
        lang = user.preferred_language or "en"
        status_label = ROAD_STATUS_LABELS.get(payload.status, {}).get(lang, ROAD_STATUS_LABELS.get(payload.status, {}).get("en", payload.status))
        title = translate("road_title", lang, road=road.name)
        msg = translate("road_message", lang, road=road.name, status=status_label)
        create_alert(
            db, title=title, message=msg, severity="warning", alert_type="road",
            risk_level="HIGH", cause="Road blocked",
            recommended_action="Reroute traffic and deploy clearance team",
            district_id=road.district_id, lat=road.latitude, lon=road.longitude,
            affected_roads=[road.name],
        )

    db.commit()
    db.refresh(road)
    return RoadOut(
        id=road.id, name=road.name, road_type=road.road_type, status=road.status,
        population_served=road.population_served, alternative_route=road.alternative_route,
        priority_score=road.priority_score, latitude=road.latitude, longitude=road.longitude,
        district_id=road.district_id, last_status_update=road.last_status_update,
    )
