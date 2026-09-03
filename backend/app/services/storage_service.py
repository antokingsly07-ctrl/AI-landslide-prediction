"""Media/storage service with configurable backend (local now, object storage later)."""
import os
import uuid
from io import BytesIO

from PIL import Image

from app.core.config import settings

ALLOWED_IMAGES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEOS = {"video/mp4", "video/quicktime", "video/webm"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100 MB
THUMBNAIL_SIZE = (320, 320)


class StorageService:
    def __init__(self):
        self.base_dir = settings.LOCAL_STORAGE_DIR
        os.makedirs(self.base_dir, exist_ok=True)
        self.image_subdir = os.path.join(self.base_dir, "images")
        self.thumb_subdir = os.path.join(self.base_dir, "thumbs")
        self.video_subdir = os.path.join(self.base_dir, "videos")
        os.makedirs(self.image_subdir, exist_ok=True)
        os.makedirs(self.thumb_subdir, exist_ok=True)
        os.makedirs(self.video_subdir, exist_ok=True)

    def validate(self, content_type: str, size_bytes: int) -> str:
        if size_bytes <= 0:
            raise ValueError("Empty file")
        if content_type in ALLOWED_IMAGES:
            if size_bytes > MAX_IMAGE_BYTES:
                raise ValueError("Image exceeds 8MB limit")
            return "image"
        if content_type in ALLOWED_VIDEOS:
            if size_bytes > MAX_VIDEO_BYTES:
                raise ValueError("Video exceeds 100MB limit")
            return "video"
        raise ValueError("Unsupported file type")

    def _ext(self, content_type: str) -> str:
        mapping = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
            "video/mp4": "mp4",
            "video/quicktime": "mov",
            "video/webm": "webm",
        }
        return mapping.get(content_type, "bin")

    def store(self, data: bytes, content_type: str, original_name: str = "") -> dict:
        media_type = self.validate(content_type, len(data))
        key = str(uuid.uuid4())
        ext = self._ext(content_type)
        thumb_key = None

        if media_type == "image":
            fname = f"{key}.{ext}"
            path = os.path.join(self.image_subdir, fname)
            with open(path, "wb") as f:
                f.write(data)
            # thumbnail
            try:
                img = Image.open(BytesIO(data))
                img.thumbnail(THUMBNAIL_SIZE)
                thumb_name = f"{key}_thumb.jpg"
                thumb_path = os.path.join(self.thumb_subdir, thumb_name)
                img.convert("RGB").save(thumb_path, "JPEG", quality=70)
                thumb_key = thumb_name
            except Exception:
                thumb_key = None
        else:
            fname = f"{key}.{ext}"
            path = os.path.join(self.video_subdir, fname)
            with open(path, "wb") as f:
                f.write(data)

        return {
            "media_type": media_type,
            "file_key": fname,
            "thumbnail_key": thumb_key,
            "mime_type": content_type,
            "size_bytes": len(data),
        }

    def public_url(self, file_key: str) -> str:
        base = settings.LOCAL_STORAGE_PUBLIC_URL.rstrip("/")
        return f"{base}/{file_key}"

    def thumb_url(self, thumb_key: str) -> str:
        base = settings.LOCAL_STORAGE_PUBLIC_URL.rstrip("/")
        return f"{base}/{thumb_key}"


storage_service = StorageService()
