"""
LuxeForge Images API router.
Handles image upload, listing, retrieval, and deletion.
"""
import logging
import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.luxeforge_image import LuxeForgeImage

router = APIRouter()

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join("uploads", "luxeforge")
THUMBNAIL_DIR = os.path.join("uploads", "luxeforge", "thumbnails")
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)


def _make_thumbnail(src_path: str, thumb_path: str) -> bool:
    """Create a thumbnail using Pillow if available, otherwise copy original."""
    try:
        from PIL import Image  # type: ignore

        with Image.open(src_path) as img:
            img.thumbnail((256, 256))
            img.save(thumb_path)
        return True
    except Exception as exc:
        logger.warning("Thumbnail generation failed for %s: %s. Falling back to copy.", src_path, exc)
        shutil.copy2(src_path, thumb_path)
        return False


class ImageResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    file_path: str
    thumbnail_path: Optional[str]
    size: int
    mime_type: str
    project_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post(
    "/upload",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image",
)
async def upload_image(
    file: UploadFile = File(...),
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Upload an image file and persist its metadata."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type: {file.content_type}. Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    _ensure_dirs()

    # Read file contents and enforce size limit
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 10 MB limit.",
        )

    file_id = uuid.uuid4()
    ext = os.path.splitext(file.filename or "image")[1] or ".bin"
    unique_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as out:
        out.write(contents)

    # Generate thumbnail
    thumb_filename = f"thumb_{unique_filename}"
    thumb_path = os.path.join(THUMBNAIL_DIR, thumb_filename)
    _make_thumbnail(file_path, thumb_path)

    proj_uuid = None
    if project_id:
        try:
            proj_uuid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id format.")

    image = LuxeForgeImage(
        id=file_id,
        filename=unique_filename,
        original_name=file.filename or unique_filename,
        file_path=file_path,
        thumbnail_path=thumb_path,
        size=len(contents),
        mime_type=file.content_type,
        project_id=proj_uuid,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return _to_response(image)


@router.get(
    "",
    response_model=List[ImageResponse],
    summary="List all images",
)
def list_images(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return all stored LuxeForge images, optionally filtered by project."""
    query = db.query(LuxeForgeImage)
    if project_id:
        try:
            proj_uuid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id format.")
        query = query.filter(LuxeForgeImage.project_id == proj_uuid)
    images = query.order_by(LuxeForgeImage.created_at.desc()).all()
    return [_to_response(img) for img in images]


@router.get(
    "/{image_id}",
    response_model=ImageResponse,
    summary="Get a single image",
)
def get_image(image_id: str, db: Session = Depends(get_db)):
    """Return metadata for a single image."""
    image = _get_or_404(image_id, db)
    return _to_response(image)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an image",
)
def delete_image(image_id: str, db: Session = Depends(get_db)):
    """Delete an image and its associated files."""
    image = _get_or_404(image_id, db)

    for path in (image.file_path, image.thumbnail_path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError as exc:
                logger.warning("Failed to remove file %s: %s", path, exc)

    db.delete(image)
    db.commit()


@router.get(
    "/file/{image_id}",
    summary="Serve image file",
    response_class=FileResponse,
)
def serve_image_file(image_id: str, db: Session = Depends(get_db)):
    """Serve the actual image binary for display."""
    image = _get_or_404(image_id, db)
    if not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="Image file not found on disk.")
    return FileResponse(image.file_path, media_type=image.mime_type)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(image_id: str, db: Session) -> LuxeForgeImage:
    try:
        img_uuid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image_id format.")
    image = db.query(LuxeForgeImage).filter(LuxeForgeImage.id == img_uuid).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found.")
    return image


def _to_response(image: LuxeForgeImage) -> ImageResponse:
    return ImageResponse(
        id=str(image.id),
        filename=image.filename,
        original_name=image.original_name,
        file_path=image.file_path,
        thumbnail_path=image.thumbnail_path,
        size=image.size,
        mime_type=image.mime_type,
        project_id=str(image.project_id) if image.project_id else None,
        created_at=image.created_at,
    )
