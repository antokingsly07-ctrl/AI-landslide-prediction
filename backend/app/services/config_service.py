"""Application configuration service backed by the persistent SystemConfig store.

Falls back to env/settings defaults when no row has been set yet.
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.risk import SystemConfig

CONFIG_KEY_THRESHOLDS = "risk_thresholds"


def get_risk_thresholds(db: Session) -> dict:
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == CONFIG_KEY_THRESHOLDS))
    if row is None:
        return settings.RISK_LEVELS
    try:
        return json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return settings.RISK_LEVELS


def set_risk_thresholds(db: Session, risk_levels: dict, user_id: str | None = None) -> dict:
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == CONFIG_KEY_THRESHOLDS))
    if row is None:
        row = SystemConfig(key=CONFIG_KEY_THRESHOLDS, value=json.dumps(risk_levels),
                           description="Risk level score ranges", updated_by=user_id)
        db.add(row)
    else:
        row.value = json.dumps(risk_levels)
        row.updated_by = user_id
    db.commit()
    return risk_levels