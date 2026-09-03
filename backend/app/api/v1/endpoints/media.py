"""Media upload endpoint with validation + thumbnail generation."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.geo import User
from app.models.risk import UploadedMedia
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    incident_id: str | None = None,
    report_id: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        info = storage_service.store(data, file.content_type or "application/octet-stream", file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    media = UploadedMedia(
        media_type=info["media_type"], file_key=info["file_key"],
        thumbnail_key=info["thumbnail_key"], original_name=file.filename or "",
        mime_type=info["mime_type"], size_bytes=info["size_bytes"],
        latitude=latitude, longitude=longitude,
        uploaded_by=user.id, incident_id=incident_id, report_id=report_id,
        is_public=False,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return {
        "id": media.id, "media_type": media.media_type,
        "url": storage_service.public_url(media.file_key),
        "thumb": storage_service.thumb_url(media.thumbnail_key) if media.thumbnail_key else None,
        "size_bytes": media.size_bytes,
    }
