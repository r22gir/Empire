"""Owner-uploaded swatch photos. Vendor images are never fetched or stored."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}


def photos_dir() -> Path:
    raw = os.getenv("FINE_FABRICS_PHOTOS_DIR") or os.getenv("EMPIRE_PHOTOS_DIR")
    if raw:
        root = Path(raw)
    else:
        root = Path(os.getenv("EMPIRE_TASK_DB", ".")).resolve().parent / "fine_fabrics_photos"
    dest = root / "fine_fabrics" if raw and Path(raw).name != "fine_fabrics" else root
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def save_owner_photo(product_id: int, filename: str, content: bytes) -> str:
    suffix = Path(filename or "swatch.jpg").suffix.lower() or ".jpg"
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Only image uploads are accepted (owner photos, never vendor scrapes)")
    if not content:
        raise ValueError("Empty upload")
    stored = f"{product_id}_{uuid.uuid4().hex[:10]}{suffix}"
    path = photos_dir() / stored
    path.write_bytes(content)
    return stored


def read_photo(filename: str) -> Path | None:
    name = Path(filename).name
    if name != filename or ".." in filename:
        return None
    path = photos_dir() / name
    if not path.is_file():
        return None
    return path
