"""Sensor management + readings ingestion endpoints."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_min_role
from app.db.session import get_db
from app.models.environment import Sensor, SensorReading
from app.models.geo import User
from app.schemas.domain import (
    SensorCreate,
    SensorOut,
    SensorReadingIn,
    SensorReadingOut,
)
from app.services.prediction_service import create_alert
from app.services.i18n import translate

router = APIRouter()


def _compute_health(sensor: Sensor, now: datetime) -> str:
    if sensor.last_reading_at is None:
        return "offline"
    age = now - sensor.last_reading_at
    if age > timedelta(hours=6):
        return "offline"
    if age > timedelta(hours=1):
        return "warning"
    return "online"


@router.get("", response_model=list[SensorOut])
def list_sensors(
    district_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Sensor).options(joinedload(Sensor.district))
    if district_id:
        q = q.where(Sensor.district_id == district_id)
    sensors = db.scalars(q).all()
    now = datetime.now(timezone.utc)
    out = []
    for s in sensors:
        s.status = _compute_health(s, now)
        out.append(SensorOut(
            id=s.id, name=s.name, sensor_type=s.sensor_type, status=s.status,
            latitude=s.latitude, longitude=s.longitude,
            district_id=s.district_id,
            district_name=s.district.name if s.district else None,
            last_reading_at=s.last_reading_at,
        ))
    return out


@router.post("", response_model=SensorOut, status_code=201)
def create_sensor(payload: SensorCreate, user: User = Depends(require_min_role("district_admin")),
                  db: Session = Depends(get_db)):
    sensor = Sensor(
        name=payload.name, sensor_type=payload.sensor_type,
        latitude=payload.latitude, longitude=payload.longitude,
        district_id=payload.district_id, api_token=f"tok_{__import__('uuid').uuid4().hex[:16]}",
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return SensorOut.model_validate(sensor)


@router.post("/readings", response_model=SensorReadingOut, status_code=201)
def ingest_reading(payload: SensorReadingIn, db: Session = Depends(get_db)):
    sensor = db.get(Sensor, payload.sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    if sensor.api_token and payload.api_token and sensor.api_token != payload.api_token:
        raise HTTPException(status_code=401, detail="Invalid sensor token")

    read_at = payload.read_at or datetime.now(timezone.utc)
    if read_at > datetime.now(timezone.utc) + timedelta(minutes=10):
        raise HTTPException(status_code=422, detail="Timestamp is in the future")

    # anomaly detection thresholds per type
    anomaly_limits = {
        "soil_moisture": (0, 100),
        "tilt": (0, 45),
        "ground_movement": (0, 500),
        "temperature": (-20, 80),
        "rain_gauge": (0, 500),
    }
    is_anomaly = False
    lo, hi = anomaly_limits.get(payload.reading_type, (None, None))
    if lo is not None and not (lo <= payload.value <= hi):
        is_anomaly = True

    reading = SensorReading(
        sensor_id=sensor.id, reading_type=payload.reading_type,
        value=payload.value, unit=payload.unit, read_at=read_at, is_anomaly=is_anomaly,
    )
    db.add(reading)
    sensor.last_reading_at = read_at

    # update sensor health
    min_age = datetime.now(timezone.utc) - read_at
    if min_age <= timedelta(minutes=10):
        sensor.status = "critical" if is_anomaly else "online"

    db.add(sensor)

    # raise alert on anomaly
    if is_anomaly:
        lang = getattr(user, "preferred_language", "en") if "user" in locals() else "en"
        title = translate("sensor_anomaly_title", lang)
        msg = translate("sensor_anomaly_message", lang, sensor=sensor.name,
                        type=payload.reading_type, value=payload.value, unit=payload.unit)
        create_alert(
            db, title=title, message=msg, severity="warning", alert_type="sensor_anomaly",
            cause=f"Anomalous {payload.reading_type} reading",
            recommended_action="Verify sensor and monitor for ground movement",
            district_id=sensor.district_id, lat=sensor.latitude, lon=sensor.longitude,
        )

    db.commit()
    db.refresh(reading)
    return SensorReadingOut.model_validate(reading)


@router.get("/{id}/readings", response_model=list[SensorReadingOut])
def sensor_readings(id: str, limit: int = Query(default=50), db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(SensorReading).where(SensorReading.sensor_id == id)
        .order_by(SensorReading.read_at.desc()).limit(limit)
    ).all()
    return [SensorReadingOut.model_validate(r) for r in rows]
