"""Audit logging helper."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.risk import AuditLog


def audit(
    db: Session,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    details: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        user_id=user_id,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry
