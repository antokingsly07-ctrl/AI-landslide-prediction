"""Field report endpoints supporting offline sync."""
import base64
import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.geo import User
from app.models.risk import FieldReport, Incident, RiskPrediction, UploadedMedia
from app.schemas.domain import ReportCreate, ReportOut, ReportUpdate
from app.services.audit_service import audit
from app.services.storage_service import storage_service, ALLOWED_IMAGES, ALLOWED_VIDEOS

router = APIRouter()


def report_to_out(r: FieldReport, db: Session) -> ReportOut:
    media = db.scalars(select(UploadedMedia).where(UploadedMedia.report_id == r.id)).all()
    return ReportOut(
        id=r.id, report_type=r.report_type, severity=r.severity,
        description=r.description, latitude=r.latitude, longitude=r.longitude,
        reported_by=r.reported_by,
        reporter_name=r.reporter.full_name if r.reporter else None,
        incident_id=r.incident_id, client_id=r.client_id, sync_status=r.sync_status,
        reported_at=r.reported_at,
        media=[{
            "id": m.id, "media_type": m.media_type,
            "url": storage_service.public_url(m.file_key),
            "thumb": storage_service.thumb_url(m.thumbnail_key) if m.thumbnail_key else None,
        } for m in media],
    )


@router.get("", response_model=list[ReportOut])
def list_reports(
    district_id: str | None = Query(default=None),
    sync_status: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(FieldReport).where(FieldReport.reported_by == user.id)
    if sync_status:
        q = q.where(FieldReport.sync_status == sync_status)
    if client_id:
        q = q.where(FieldReport.client_id == client_id)
    q = q.order_by(FieldReport.reported_at.desc())
    rows = db.scalars(q).all()
    return [report_to_out(r, db) for r in rows]


@router.post("", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    # offline dedupe
    if payload.client_id:
        existing = db.scalar(select(FieldReport).where(FieldReport.client_id == payload.client_id))
        if existing:
            return report_to_out(existing, db)

    report = FieldReport(
        report_type=payload.report_type, severity=payload.severity,
        description=payload.description, latitude=payload.latitude, longitude=payload.longitude,
        reported_by=user.id, incident_id=payload.incident_id, client_id=payload.client_id,
        device_location_manual=payload.device_location_manual, sync_status="synced",
    )
    db.add(report)
    db.flush()

    # auto-create incident for report
    if not payload.incident_id:
        inc = Incident(
            incident_type=payload.report_type, severity=payload.severity,
            latitude=payload.latitude, longitude=payload.longitude,
            description=payload.description, reported_by=user.id,
            district_id=user.district_id, status="reported", verification_status="pending",
        )
        db.add(inc)
        db.flush()
        report.incident_id = inc.id

    # process base64 photos
    for b64 in payload.photos:
        try:
            header, _, content = b64.partition(",")
            data = base64.b64decode(content)
            mime = header.replace("data:", "").split(";")[0] if header else "image/jpeg"
            info = storage_service.store(data, mime, "photo")
            db.add(UploadedMedia(
                media_type=info["media_type"], file_key=info["file_key"],
                thumbnail_key=info["thumbnail_key"], original_name="photo",
                mime_type=info["mime_type"], size_bytes=info["size_bytes"],
                latitude=payload.latitude, longitude=payload.longitude,
                uploaded_by=user.id, incident_id=report.incident_id, report_id=report.id,
            ))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid media: {str(e)}")

    audit(db, "report.create", "report", report.id, f"Created {report.report_type}", user.id)
    db.commit()
    db.refresh(report)
    return report_to_out(report, db)


@router.patch("/{id}", response_model=ReportOut)
def update_report(id: str, payload: ReportUpdate, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    report = db.get(FieldReport, id)
    if not report or report.reported_by != user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    if payload.severity is not None:
        report.severity = payload.severity
    if payload.description is not None:
        report.description = payload.description
    if payload.sync_status is not None:
        report.sync_status = payload.sync_status
    db.add(report)
    db.commit()
    db.refresh(report)
    return report_to_out(report, db)


@router.get("/export/csv")
def export_reports_csv(
    scope: str = Query(default="own", pattern="^(own|all)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export field reports as CSV for offline/analytical use."""
    q = select(FieldReport).order_by(FieldReport.reported_at.desc())
    if scope == "own":
        q = q.where(FieldReport.reported_by == user.id)
    rows = db.scalars(q).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "report_type", "severity", "description",
                     "latitude", "longitude", "reporter", "sync_status",
                     "reported_at"])

    for r in rows:
        writer.writerow([
            r.id, r.report_type, r.severity,
            (r.description or "").replace("\n", " "),
            r.latitude, r.longitude,
            r.reporter.full_name if r.reporter else "",
            r.sync_status, r.reported_at.isoformat() if r.reported_at else "",
        ])

    buf.seek(0)
    filename = f"field_reports_{user.id[:8]}_{__import__('datetime').date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/predictions-csv")
def export_predictions_csv(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export recent risk predictions as CSV."""
    rows = db.scalars(
        select(RiskPrediction).order_by(RiskPrediction.predicted_at.desc()).limit(500)
    ).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["latitude", "longitude", "risk_score", "risk_level",
                     "confidence", "model", "predicted_at"])
    for r in rows:
        writer.writerow([
            r.latitude, r.longitude, r.risk_score, r.risk_level,
            r.confidence, r.model,
            r.predicted_at.isoformat() if r.predicted_at else "",
        ])
    buf.seek(0)
    filename = f"risk_predictions_{__import__('datetime').date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
