"""Offline sync endpoint - client pushes pending reports to server.

Clients queue reports in IndexedDB while offline and POST them here when
connectivity is restored. Client-generated unique IDs prevent duplicates.
"""
import base64

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.geo import User
from app.models.risk import FieldReport, Incident, UploadedMedia
from app.schemas.domain import ReportOut
from app.services.audit_service import audit
from app.services.storage_service import storage_service

router = APIRouter()


class SyncItem(BaseModel):
    client_id: str
    report_type: str
    severity: str = "medium"
    description: str | None = None
    latitude: float
    longitude: float
    device_location_manual: bool = False
    reported_at: str | None = None
    photos: list[str] = []  # base64 data URLs
    incident_type: str | None = None  # optionally create an incident


def _serialize(r: FieldReport, db: Session) -> dict:
    media = db.scalars(select(UploadedMedia).where(UploadedMedia.report_id == r.id)).all()
    return {
        "id": r.id,
        "client_id": r.client_id,
        "report_type": r.report_type,
        "severity": r.severity,
        "description": r.description,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "sync_status": r.sync_status,
        "reported_at": r.reported_at.isoformat() if r.reported_at else None,
        "media": [{"id": m.id, "url": storage_service.public_url(m.file_key),
                   "thumb": storage_service.thumb_url(m.thumbnail_key) if m.thumbnail_key else None}
                  for m in media],
    }


@router.post("")
def sync_pending(payload: list[SyncItem], user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    results = {"synced": [], "duplicates": [], "created_incidents": 0}
    for item in payload:
        # prevent duplicate submission via client-generated ID
        existing = db.scalar(select(FieldReport).where(FieldReport.client_id == item.client_id))
        if existing:
            results["duplicates"].append(item.client_id)
            results["synced"].append(_serialize(existing, db))
            continue

        report = FieldReport(
            report_type=item.report_type, severity=item.severity,
            description=item.description, latitude=item.latitude, longitude=item.longitude,
            reported_by=user.id, client_id=item.client_id,
            device_location_manual=item.device_location_manual,
            sync_status="synced",
        )
        db.add(report)
        db.flush()

        incident_type = item.incident_type or item.report_type
        inc = Incident(
            incident_type=incident_type, severity=item.severity,
            latitude=item.latitude, longitude=item.longitude,
            description=item.description, reported_by=user.id,
            district_id=user.district_id, status="reported", verification_status="pending",
        )
        db.add(inc)
        db.flush()
        report.incident_id = inc.id
        results["created_incidents"] += 1

        for b64 in item.photos:
            try:
                header, _, content = b64.partition(",")
                data = base64.b64decode(content)
                mime = header.replace("data:", "").split(";")[0] if header else "image/jpeg"
                info = storage_service.store(data, mime, "photo")
                db.add(UploadedMedia(
                    media_type=info["media_type"], file_key=info["file_key"],
                    thumbnail_key=info["thumbnail_key"], original_name="photo",
                    mime_type=info["mime_type"], size_bytes=info["size_bytes"],
                    latitude=item.latitude, longitude=item.longitude,
                    uploaded_by=user.id, incident_id=inc.id, report_id=report.id,
                ))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid media for {item.client_id}: {str(e)}")

        audit(db, "report.sync", "report", report.id, f"Synced offline report", user.id)
        db.commit()
        results["synced"].append(_serialize(report, db))

    return results
