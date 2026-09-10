"""Risk zones and risk data endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.environment import LandslideHistory
from app.models.geo import District, User
from app.models.risk import RiskZone
from app.schemas.domain import RiskZoneOut

router = APIRouter()


@router.get("/zones", response_model=list[RiskZoneOut])
def risk_zones(
    district_id: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    limit: int = Query(default=500, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(RiskZone).options(joinedload(RiskZone.district), joinedload(RiskZone.village))
    if district_id:
        q = q.where(RiskZone.district_id == district_id)
    if risk_level:
        q = q.where(RiskZone.risk_level == risk_level)
    q = q.order_by(RiskZone.risk_score.desc()).limit(limit)
    rows = db.scalars(q).all()
    return [
        RiskZoneOut(
            id=r.id, name=r.name, risk_score=r.risk_score, risk_level=r.risk_level,
            latitude=r.latitude, longitude=r.longitude,
            district_id=r.district_id,
            district_name=r.district.name if r.district else None,
            village_id=r.village_id,
            village_name=r.village.name if r.village else None,
            population=r.population, area_km2=r.area_km2, last_update=r.last_update,
        )
        for r in rows
    ]


@router.get("/{id}", response_model=RiskZoneOut)
def risk_zone_detail(id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(RiskZone, id)
    if not r:
        raise HTTPException(status_code=404, detail="Risk zone not found")
    return RiskZoneOut(
        id=r.id, name=r.name, risk_score=r.risk_score, risk_level=r.risk_level,
        latitude=r.latitude, longitude=r.longitude,
        district_id=r.district_id,
        district_name=r.district.name if r.district else None,
        village_id=r.village_id, village_name=r.village.name if r.village else None,
        population=r.population, area_km2=r.area_km2, last_update=r.last_update,
    )


@router.get("/historical/landslides")
def historical_landslides(
    district_id: str | None = Query(default=None),
    limit: int = Query(default=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(LandslideHistory).order_by(LandslideHistory.occurred_on.desc()).limit(limit)
    if district_id:
        q = q.where(LandslideHistory.district_id == district_id)
    rows = db.scalars(q).all()
    return [
        {
            "id": r.id, "latitude": r.latitude, "longitude": r.longitude,
            "year": r.year, "severity": r.severity, "cause": r.cause,
            "description": r.description, "occurred_on": r.occurred_on.isoformat() if r.occurred_on else None,
            "district_id": r.district_id,
        }
        for r in rows
    ]
