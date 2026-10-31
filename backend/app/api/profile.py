import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models import User
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])

# Validate by magic bytes, not by the client-supplied content type or filename.
_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
}


def _sniff(data: bytes) -> str | None:
    for sig, ext in _SIGNATURES.items():
        if data.startswith(sig):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    return profile_service.to_out(user)


@router.put("", response_model=ProfileOut)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile_service.update(db, user, data)


@router.post("/photo", response_model=ProfileOut)
async def upload_photo(file: UploadFile, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_settings()
    data = await file.read(s.MAX_PHOTO_BYTES + 1)
    if len(data) > s.MAX_PHOTO_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Photo must be under {s.MAX_PHOTO_BYTES // 1024 // 1024} MB")
    ext = _sniff(data)
    if ext is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Photo must be a PNG, JPEG or WebP image")
    folder = Path(s.UPLOAD_DIR) / "photos"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{user.id}-{uuid.uuid4().hex}.{ext}"  # server-generated name: no path traversal
    (folder / name).write_bytes(data)
    user.profile.photo_url = name  # internal file name; clients only ever see the authenticated /profile/photo URL
    db.commit()
    return profile_service.to_out(user)


@router.get("/photo")
def get_photo(user: User = Depends(get_current_user)):
    """Serves ONLY the authenticated user's own photo. Uploads are not publicly mounted."""
    name = user.profile.photo_url
    if not name:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile photo")
    path = Path(get_settings().UPLOAD_DIR) / "photos" / Path(name).name
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile photo")
    media = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}.get(path.suffix.lstrip("."), "application/octet-stream")
    return FileResponse(path, media_type=media, headers={"Cache-Control": "private, no-store"})
