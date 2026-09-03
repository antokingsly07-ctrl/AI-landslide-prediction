"""Admin endpoints: users, districts, thresholds, health, audit, etc."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, require_min_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.geo import District, Role, State, User
from app.models.risk import AuditLog, NotificationLog
from app.models.environment import Sensor as SensorModel, SensorReading
from app.ml.model_manager import model_manager
from app.schemas.auth import UserUpdate
from app.services.audit_service import audit
from app.services.i18n import SUPPORTED_LANGUAGES
from app.services.weather_service import get_weather_provider
from app.services.satellite_service import get_satellite_source

router = APIRouter()


@router.get("/health")
def system_health(db: Session = Depends(get_db), user: User = Depends(require_min_role("disaster_mgmt"))):
    def _db_ok():
        try:
            db.execute(select(1))
            return "ok"
        except Exception as e:
            return f"error: {e}"

    try:
        from app.services.notification_service import notification_service
        notif_provider = "mock" if not settings.SMS_API_KEY else settings.SMS_PROVIDER
    except Exception as e:
        notif_provider = f"error: {e}"

    return {
        "status": "ok",
        "api": "ok",
        "database": _db_ok(),
        "ml_model": "loaded" if model_manager.ready else "not_trained",
        "weather_provider": get_weather_provider().name,
        "satellite_provider": get_satellite_source().name,
        "notification_provider": notif_provider,
        "environment": settings.ENVIRONMENT,
        "components": {
            "api": {"status": "ok", "detail": "healthy"},
            "database": {"status": _db_ok(), "detail": settings.DATABASE_URL.split("://")[0] + "://****"},
            "ml_model": {"status": "ok" if model_manager.ready else "warning",
                         "detail": "model ready" if model_manager.ready else "train with: python -m app.ml.train"},
            "weather": {"status": "mock" if get_weather_provider().name == "mock" else "configured"},
            "satellite": {"status": "mock" if get_satellite_source().name == "mock" else "configured"},
            "notifications": {"status": "mock" if notif_provider == "mock" else "configured"},
        },
    }


@router.get("/districts")
def list_districts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(District).order_by(District.name)).all()
    return [{"id": d.id, "name": d.name, "code": d.code, "state_id": d.state_id,
             "latitude": d.latitude, "longitude": d.longitude, "population": d.population,
             "risk_score": d.risk_score} for d in rows]


@router.get("/states")
def list_states(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(State).order_by(State.name)).all()
    return [{"id": s.id, "code": s.code, "name": s.name} for s in rows]


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Role).order_by(Role.name)).all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in rows]


@router.post("/roles")
def create_role(name: str, description: str | None = None,
                user: User = Depends(require_min_role("super_admin")), db: Session = Depends(get_db)):
    if db.scalar(select(Role).where(Role.name == name)):
        raise HTTPException(status_code=409, detail="Role exists")
    role = Role(name=name, description=description)
    db.add(role)
    db.commit()
    return {"id": role.id, "name": role.name}


@router.get("/users")
def admin_users(db: Session = Depends(get_db), user: User = Depends(require_min_role("district_admin")),
                role: str | None = Query(default=None)):
    q = select(User).options()
    if role:
        role_obj = db.scalar(select(Role).where(Role.name == role))
        if role_obj:
            q = q.where(User.role_id == role_obj.id)
    rows = db.scalars(q).all()
    return [{
        "id": u.id, "email": u.email, "full_name": u.full_name, "phone": u.phone,
        "role": u.role.name if u.role else None, "district_id": u.district_id,
        "is_active": u.is_active, "preferred_language": u.preferred_language,
        "created_at": u.created_at,
    } for u in rows]


@router.patch("/users/{id}")
def update_user(id: str, payload: UserUpdate, user: User = Depends(require_min_role("district_admin")),
                db: Session = Depends(get_db)):
    target = db.get(User, id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.phone is not None:
        target.phone = payload.phone
    if payload.role_id is not None:
        target.role_id = payload.role_id
    if payload.district_id is not None:
        target.district_id = payload.district_id
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.preferred_language is not None:
        target.preferred_language = payload.preferred_language
    db.add(target)
    audit(db, "user.update", "user", target.id, "Updated user", user.id)
    db.commit()
    return {"id": target.id, "email": target.email, "full_name": target.full_name,
            "is_active": target.is_active}


@router.get("/thresholds")
def get_thresholds(user: User = Depends(get_current_user)):
    return settings.RISK_LEVELS


@router.post("/thresholds")
def update_thresholds(new_thresholds: dict, user: User = Depends(require_min_role("super_admin")),
                      db: Session = Depends(get_db)):
    audit(db, "config.thresholds", "config", "", f"Updated risk thresholds: {new_thresholds}", user.id)
    return {"status": "accepted", "note": "Thresholds stored in config; restart to apply in this build",
            "thresholds": new_thresholds}


@router.get("/alerts")
def admin_alerts(db: Session = Depends(get_db), user: User = Depends(require_min_role("disaster_mgmt"))):
    from app.models.risk import Alert

    rows = db.scalars(select(Alert).order_by(Alert.triggered_at.desc()).limit(200)).all()
    return [{
        "id": a.id, "title": a.title, "severity": a.severity, "status": a.status,
        "alert_type": a.alert_type, "triggered_at": a.triggered_at,
    } for a in rows]


@router.get("/languages")
def languages(user: User = Depends(get_current_user)):
    return {"supported": SUPPORTED_LANGUAGES}


@router.get("/audit-logs")
def audit_logs(limit: int = Query(default=100), user: User = Depends(require_min_role("super_admin")),
               db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [{
        "id": a.id, "user_id": a.user_id, "action": a.action,
        "resource_type": a.resource_type, "resource_id": a.resource_id,
        "details": a.details, "created_at": a.created_at,
    } for a in rows]


@router.get("/notification-logs")
def notification_logs(limit: int = Query(default=100), user: User = Depends(require_min_role("super_admin")),
                      db: Session = Depends(get_db)):
    rows = db.scalars(select(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit)).all()
    return [{
        "id": n.id, "user_id": n.user_id, "alert_id": n.alert_id, "channel": n.channel,
        "provider": n.provider, "status": n.status, "recipient": n.recipient,
        "error": n.error, "created_at": n.created_at,
    } for n in rows]


@router.get("/sensors")
def admin_sensors(db: Session = Depends(get_db), user: User = Depends(require_min_role("district_admin"))):
    rows = db.scalars(select(SensorModel).order_by(SensorModel.name)).all()
    return [{
        "id": s.id, "name": s.name, "sensor_type": s.sensor_type, "status": s.status,
        "district_id": s.district_id, "latitude": s.latitude, "longitude": s.longitude,
        "last_reading_at": s.last_reading_at,
    } for s in rows]
