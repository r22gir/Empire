"""
Unified Photo Storage API.
All photos from all sources (intake, quote builder, telegram, web) go through here.

Storage layout: backend/data/photos/{entity_type}/{entity_id}/
Entity types: quote, intake, telegram, craftforge, general
"""
import json
import os
import uuid
import shutil
import logging
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["photos"])

PHOTOS_BASE = Path(os.path.expanduser("~/empire-repo/backend/data/photos"))
PHOTOS_BASE.mkdir(parents=True, exist_ok=True)

# Legacy paths for migration/linking
INTAKE_UPLOADS = Path(os.path.expanduser("~/empire-repo/backend/data/intake_uploads"))
TELEGRAM_UPLOADS = Path(os.path.expanduser("~/empire-repo/uploads/images"))

VALID_ENTITY_TYPES = {"quote", "intake", "telegram", "craftforge", "general"}


def _entity_dir(entity_type: str, entity_id: str) -> Path:
    """Get the directory for an entity's photos."""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(400, f"Invalid entity_type: {entity_type}. Must be one of {VALID_ENTITY_TYPES}")
    # Sanitize entity_id
    safe_id = entity_id.replace("/", "_").replace("..", "_")
    d = PHOTOS_BASE / entity_type / safe_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _extract_zip(
    zip_bytes: bytes,
    dest_dir: Path,
    source: str,
    entity_type: str,
    entity_id: str,
    allowed_exts: set,
) -> list[dict]:
    """Extract useful files from a ZIP archive into dest_dir.

    Returns list of saved file dicts (same shape as normal uploads).
    Skips hidden files, __MACOSX, and unsupported extensions.
    """
    saved = []
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    seq = 0  # sequence counter for files within this zip

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "upload.zip"
        zip_path.write_bytes(zip_bytes)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for info in zf.infolist():
                    # Skip directories and Mac resource forks
                    if info.is_dir():
                        continue
                    name = info.filename
                    if "__MACOSX" in name or name.startswith("."):
                        continue

                    ext = Path(name).suffix.lower()
                    if ext not in allowed_exts:
                        logger.debug(f"Skipping unsupported file in ZIP: {name}")
                        continue

                    # Extract to temp, then save with our naming
                    seq += 1
                    data = zf.read(name)
                    original_name = Path(name).name
                    # Include sequence number so duplicate filenames are distinguishable
                    out_name = f"{source}_{ts}_{seq:03d}_{uuid.uuid4().hex[:6]}{ext}"
                    out_path = dest_dir / out_name
                    out_path.write_bytes(data)

                    # Build a human-friendly display name:
                    # e.g. "3_23_2026.glb" → "#001 — 3_23_2026.glb"
                    display_name = f"#{seq:03d} — {original_name}"

                    # Metadata sidecar
                    meta = {
                        "original_name": original_name,
                        "display_name": display_name,
                        "sequence": seq,
                        "source": source,
                        "size": len(data),
                        "content_type": _guess_mime(ext),
                        "uploaded_at": datetime.utcnow().isoformat(),
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "extracted_from_zip": True,
                    }
                    with open(str(out_path) + ".meta.json", "w") as mf:
                        json.dump(meta, mf, indent=2)

                    saved.append({
                        "filename": out_name,
                        "path": f"/api/v1/photos/serve/{entity_type}/{entity_id}/{out_name}",
                        "size": len(data),
                        "source": source,
                        "original_name": original_name,
                        "display_name": display_name,
                        "sequence": seq,
                    })
                    logger.info(f"Extracted from ZIP: {original_name} → {out_name} ({len(data)} bytes)")

        except zipfile.BadZipFile:
            logger.error("Uploaded file is not a valid ZIP")
            raise HTTPException(400, "Uploaded file is not a valid ZIP archive")

    return saved


def _guess_mime(ext: str) -> str:
    """Map file extension to MIME type."""
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".heic": "image/heic", ".gif": "image/gif",
        ".bmp": "image/bmp", ".tiff": "image/tiff",
        ".glb": "model/gltf-binary", ".gltf": "model/gltf+json",
        ".obj": "model/obj", ".stl": "model/stl", ".fbx": "model/fbx",
        ".ply": "application/x-ply", ".usdz": "model/vnd.usdz+zip",
    }
    return mime_map.get(ext, "application/octet-stream")


@router.post("/upload")
async def upload_photos(
    entity_type: str = Form(default="general"),
    entity_id: str = Form(default=""),
    source: str = Form(default="web"),
    files: list[UploadFile] = File(...),
):
    """
    Upload photos from any source.
    entity_type: quote | intake | telegram | craftforge | general
    entity_id: quote UUID, intake project ID, etc.
    source: web | telegram | intake | cc (for display badge)
    """
    if not entity_id:
        entity_id = uuid.uuid4().hex[:12]

    dest_dir = _entity_dir(entity_type, entity_id)
    saved = []

    # File extensions we extract from zip archives
    EXTRACTABLE = {".glb", ".gltf", ".obj", ".ply", ".usdz", ".stl", ".fbx",
                   ".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".bmp", ".tiff"}

    for f in files:
        suffix = Path(f.filename or "photo.jpg").suffix.lower() or ".jpg"
        content = await f.read()

        # ── ZIP handling: extract known file types ──
        if suffix == ".zip":
            logger.info(f"ZIP upload detected: {f.filename} ({len(content)} bytes)")
            extracted = _extract_zip(content, dest_dir, source, entity_type, entity_id, EXTRACTABLE)
            saved.extend(extracted)
            logger.info(f"Extracted {len(extracted)} files from {f.filename}")
            continue

        # ── Normal file ──
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{ts}_{uuid.uuid4().hex[:6]}{suffix}"
        filepath = dest_dir / filename
        with open(filepath, "wb") as out:
            out.write(content)

        # Write metadata sidecar
        meta = {
            "original_name": f.filename,
            "source": source,
            "size": len(content),
            "content_type": f.content_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "entity_type": entity_type,
            "entity_id": entity_id,
        }
        with open(str(filepath) + ".meta.json", "w") as mf:
            json.dump(meta, mf, indent=2)

        saved.append({
            "filename": filename,
            "path": f"/api/v1/photos/serve/{entity_type}/{entity_id}/{filename}",
            "size": len(content),
            "source": source,
        })
        logger.info(f"Photo saved: {entity_type}/{entity_id}/{filename} ({len(content)} bytes, source={source})")

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "photos": saved,
        "total": len(saved),
    }


@router.get("/{entity_type}/{entity_id}")
async def list_photos(entity_type: str, entity_id: str):
    """List all photos for an entity, from all sources."""
    photos = []

    # Primary unified storage
    dest_dir = PHOTOS_BASE / entity_type / entity_id.replace("/", "_").replace("..", "_")
    if dest_dir.exists():
        for f in sorted(dest_dir.iterdir()):
            if f.is_file() and not f.name.endswith(".meta.json"):
                meta = _read_meta(f)
                photos.append({
                    "filename": f.name,
                    "path": f"/api/v1/photos/serve/{entity_type}/{entity_id}/{f.name}",
                    "size": f.stat().st_size,
                    "source": meta.get("source", "unknown"),
                    "uploaded_at": meta.get("uploaded_at"),
                    "original_name": meta.get("original_name"),
                    "display_name": meta.get("display_name"),
                    "sequence": meta.get("sequence"),
                })

    # For quotes, also check if there are linked intake photos
    if entity_type == "quote":
        link_file = dest_dir / "_intake_link.txt" if dest_dir.exists() else None
        if link_file and link_file.exists():
            intake_id = link_file.read_text().strip()
            intake_dir = PHOTOS_BASE / "intake" / intake_id
            if intake_dir.exists():
                for f in sorted(intake_dir.iterdir()):
                    if f.is_file() and not f.name.endswith(".meta.json"):
                        photos.append({
                            "filename": f.name,
                            "path": f"/api/v1/photos/serve/intake/{intake_id}/{f.name}",
                            "size": f.stat().st_size,
                            "source": "intake",
                            "uploaded_at": None,
                            "original_name": f.name,
                            "linked": True,
                        })

    # For intake entities, check legacy intake_uploads too
    if entity_type == "intake" and not photos:
        legacy_dir = INTAKE_UPLOADS / entity_id
        if legacy_dir.exists():
            for f in sorted(legacy_dir.iterdir()):
                if f.is_file():
                    photos.append({
                        "filename": f.name,
                        "path": f"/api/v1/photos/serve/intake/{entity_id}/{f.name}",
                        "size": f.stat().st_size,
                        "source": "intake_legacy",
                        "uploaded_at": None,
                        "original_name": f.name,
                    })

    return {"entity_type": entity_type, "entity_id": entity_id, "photos": photos, "total": len(photos)}


@router.get("/serve/{entity_type}/{entity_id}/{filename}")
async def serve_photo(entity_type: str, entity_id: str, filename: str):
    """Serve a photo file. Works via localhost and api.empirebox.store."""
    # Sanitize
    safe_id = entity_id.replace("/", "_").replace("..", "_")
    safe_name = Path(filename).name  # strip any path components

    # Try unified storage first
    filepath = PHOTOS_BASE / entity_type / safe_id / safe_name
    if filepath.exists() and filepath.is_file():
        return FileResponse(filepath)

    # Fallback: legacy intake_uploads
    if entity_type == "intake":
        legacy = INTAKE_UPLOADS / safe_id / safe_name
        if legacy.exists():
            return FileResponse(legacy)

    # Fallback: telegram uploads
    if entity_type == "telegram":
        tg = TELEGRAM_UPLOADS / safe_name
        if tg.exists():
            return FileResponse(tg)

    raise HTTPException(404, f"Photo not found: {entity_type}/{entity_id}/{filename}")


@router.delete("/{entity_type}/{entity_id}/{filename}")
async def delete_photo(entity_type: str, entity_id: str, filename: str):
    """Delete a photo."""
    safe_id = entity_id.replace("/", "_").replace("..", "_")
    safe_name = Path(filename).name
    filepath = PHOTOS_BASE / entity_type / safe_id / safe_name

    if not filepath.exists():
        raise HTTPException(404, "Photo not found")

    filepath.unlink()
    meta_file = Path(str(filepath) + ".meta.json")
    if meta_file.exists():
        meta_file.unlink()

    return {"deleted": filename, "entity_type": entity_type, "entity_id": entity_id}


@router.post("/link")
async def link_photos(
    source_type: str = Form(...),
    source_id: str = Form(...),
    target_type: str = Form(...),
    target_id: str = Form(...),
    copy: bool = Form(default=False),
):
    """
    Link photos from one entity to another.
    E.g., link intake photos to a quote, or telegram photos to a quote.
    If copy=True, physically copies files. Otherwise creates a reference link.
    """
    source_dir = _entity_dir(source_type, source_id)
    target_dir = _entity_dir(target_type, target_id)

    linked = 0
    if copy:
        for f in source_dir.iterdir():
            if f.is_file() and not f.name.endswith(".meta.json"):
                dest = target_dir / f"linked_{source_type}_{f.name}"
                if not dest.exists():
                    shutil.copy2(str(f), str(dest))
                    # Write meta
                    meta = {
                        "original_name": f.name,
                        "source": source_type,
                        "linked_from": f"{source_type}/{source_id}",
                        "uploaded_at": datetime.utcnow().isoformat(),
                        "entity_type": target_type,
                        "entity_id": target_id,
                    }
                    with open(str(dest) + ".meta.json", "w") as mf:
                        json.dump(meta, mf, indent=2)
                    linked += 1
    else:
        # Create a symlink reference file
        link_file = target_dir / f"_{source_type}_link.txt"
        link_file.write_text(source_id)
        linked = 1

    return {
        "linked": linked,
        "source": f"{source_type}/{source_id}",
        "target": f"{target_type}/{target_id}",
        "method": "copy" if copy else "reference",
    }


def _read_meta(photo_path: Path) -> dict:
    """Read metadata sidecar for a photo."""
    meta_path = Path(str(photo_path) + ".meta.json")
    if meta_path.exists():
        import json
        with open(meta_path) as f:
            return json.load(f)
    return {}
