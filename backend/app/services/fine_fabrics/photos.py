"""Swatch photos — owner uploads and vendor image attachments.

Vendor image URLs from the import CSV are stored and shown. Remote files
are not fetched here; the store either serves a local file or redirects
to the vendor URL.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
_REMOTE_RE = re.compile(r"^https?://", re.I)
_OWNER_RE = re.compile(r"^\d+_[0-9a-f]{10}\.")


def photos_dir() -> Path:
    raw = os.getenv("FINE_FABRICS_PHOTOS_DIR") or os.getenv("EMPIRE_PHOTOS_DIR")
    if raw:
        root = Path(raw)
    else:
        root = Path(os.getenv("EMPIRE_TASK_DB", ".")).resolve().parent / "fine_fabrics_photos"
    dest = root / "fine_fabrics" if raw and Path(raw).name != "fine_fabrics" else root
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def is_remote_url(value: str | None) -> bool:
    return bool(_REMOTE_RE.match((value or "").strip()))


def is_owner_photo_name(filename: str | None) -> bool:
    return bool(_OWNER_RE.match(Path(filename or "").name))


def save_owner_photo(product_id: int, filename: str, content: bytes) -> str:
    suffix = Path(filename or "swatch.jpg").suffix.lower() or ".jpg"
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Only image uploads are accepted")
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


def resolve_product_image(row: dict) -> dict:
    """Pick the public image: owner file, then vendor URL / image_path."""
    local = (row.get("image_path") or "").strip()
    vendor_url = (row.get("vendor_image_url") or "").strip()
    product_id = row.get("id")
    if local and not is_remote_url(local):
        stored = Path(local).name
        if read_photo(stored) or (photos_dir() / stored).is_file():
            return {
                "image_url": f"/api/v1/fine-fabrics/photos/{product_id}" if product_id else stored,
                "has_owner_photo": is_owner_photo_name(stored),
                "has_vendor_image": bool(vendor_url) or not is_owner_photo_name(stored),
                "placeholder": False,
                "local_name": stored,
                "redirect_url": None,
            }
        if (Path(local).is_file()):
            return {
                "image_url": f"/api/v1/fine-fabrics/photos/{product_id}" if product_id else local,
                "has_owner_photo": False,
                "has_vendor_image": True,
                "placeholder": False,
                "local_name": local,
                "redirect_url": None,
            }
    remote = vendor_url if is_remote_url(vendor_url) else local if is_remote_url(local) else ""
    if remote:
        return {
            "image_url": remote,
            "has_owner_photo": False,
            "has_vendor_image": True,
            "placeholder": False,
            "local_name": None,
            "redirect_url": remote,
        }
    return {
        "image_url": None,
        "has_owner_photo": False,
        "has_vendor_image": False,
        "placeholder": True,
        "local_name": None,
        "redirect_url": None,
    }


_COLOR_HINTS = {
    "navy": (28, 52, 92),
    "natural": (214, 196, 164),
    "charcoal": (62, 62, 66),
    "sand": (196, 168, 122),
    "shade": (138, 142, 132),
    "fog": (168, 172, 176),
    "sage": (122, 142, 110),
    "ivory": (236, 226, 206),
    "spruce": (46, 86, 68),
    "teak": (138, 94, 58),
    "saddle": (126, 78, 46),
    "cocoa": (92, 62, 46),
    "harbor": (58, 92, 118),
    "flint": (110, 108, 104),
    "oat": (198, 176, 142),
    "fennel": (118, 132, 72),
    "emerald": (28, 92, 70),
    "brindle": (122, 92, 62),
    "terracotta": (168, 86, 58),
    "cream": (236, 228, 208),
    "indigo": (42, 58, 102),
}


def _hint_rgb(text: str) -> tuple[int, int, int]:
    key = re.sub(r"[^a-z]+", " ", (text or "").lower()).strip()
    for name, rgb in _COLOR_HINTS.items():
        if name in key:
            return rgb
    digest = sum(ord(ch) for ch in key) or 90
    return (70 + digest % 120, 60 + (digest * 3) % 110, 50 + (digest * 7) % 100)


def _write_png(path: Path, width: int, height: int, pixel) -> None:
    import struct
    import zlib

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixel(x, y))
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def generate_preview_swatch(row: dict, dest: Path | None = None, size: int = 420) -> str:
    """Write a small mock mill swatch. Used for demo/preview catalogs only."""
    dest = dest or photos_dir()
    dest.mkdir(parents=True, exist_ok=True)
    sku = re.sub(r"[^A-Za-z0-9]+", "", (row.get("sku") or row.get("empire_code") or "swatch"))
    name = f"preview_{sku or row.get('id') or 'swatch'}.png"
    path = dest / name
    base = _hint_rgb(f"{row.get('color')} {row.get('pattern')}")
    weave = _hint_rgb((row.get("pattern") or "weave") + "x")
    kind = sum(ord(ch) for ch in sku) % 4

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        if kind == 0:
            band = (x // 18) % 2
            tone = base if band == 0 else weave
        elif kind == 1:
            tone = base if ((x // 16) + (y // 16)) % 2 == 0 else weave
        elif kind == 2:
            tone = weave if (x + y) % 28 < 8 else base
        else:
            tone = weave if (x % 22 < 6 and y % 22 < 6) else base
        drift = ((x * 3 + y * 5) % 17) - 8
        return tuple(max(0, min(255, c + drift)) for c in tone)

    _write_png(path, size, size, pixel)
    return name


def generate_room_photo(dest: Path | None = None) -> Path:
    """A simple interior stand-in for the upload-photo mockup screenshot."""
    dest = dest or photos_dir()
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "preview_room.jpg"
    png = dest / "preview_room.png"

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        if y < 90:
            return (214, 208, 196)
        if y > 230:
            return (118, 96, 78)
        if 70 < x < 330 and 70 < y < 210:
            return (186, 176, 158)
        return (168, 156, 140)

    _write_png(png, 400, 300, pixel)
    return png
