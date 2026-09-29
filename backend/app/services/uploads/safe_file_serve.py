"""Safe serving/storage helpers for user-uploaded intake files.

LuxeForge intake designers upload arbitrary file types: PDFs, CAD (dwg,
dxf, skp, rvt, 3dm), 3D scans (usdz, obj, ply, glb, gltf, fbx, stl, e57),
office docs, spreadsheets, zip archives, video. Two rules govern how those
bytes are stored and served back:

  1. Storage never trusts the client-supplied filename for the on-disk
     path — only a sanitized extension is kept, the stem is always a
     fresh UUID. This is what makes path-traversal and null-byte tricks
     unreachable regardless of what the browser sends as `filename`.
  2. Serving never lets the browser execute or render an uploaded file
     as a page. Only a short allowlist of raster image types gets
     `Content-Type: image/...` with inline rendering (needed so the
     "Photos, Drawings & Scans" grid can preview them in <img> tags).
     Everything else — explicitly including any HTML or SVG a designer
     might upload — is served as `application/octet-stream` with
     `Content-Disposition: attachment`, so a direct hit on the URL
     always downloads, never executes in the origin's security context.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse

# ~200MB per file by default. Raise via env if a future upload class needs
# more; keep the frontend proxy's body-size cap (next.config.ts
# proxyClientMaxBodySize) in sync with this value.
MAX_UPLOAD_BYTES = int(os.getenv("INTAKE_MAX_UPLOAD_MB", "200")) * 1024 * 1024

# Raster types safe to render inline in an <img> tag. Deliberately never
# includes text/html or image/svg+xml — SVG can carry <script> and would
# execute in the page's origin if ever rendered inline.
_INLINE_IMAGE_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    ".tiff": "image/tiff", ".heic": "image/heic", ".heif": "image/heif",
}

_SAFE_EXT_RE = re.compile(r"[^A-Za-z0-9.]")


def is_inline_image_extension(ext: str) -> bool:
    return ext.lower() in _INLINE_IMAGE_MIME


def safe_extension(filename: Optional[str], default: str = ".bin") -> str:
    """Return a sanitized, storage-safe extension (with leading dot).

    Only the extension is ever derived from a client-supplied filename;
    the on-disk stem is always a fresh UUID (see callers in intake_auth.py).
    Strips any character that isn't alphanumeric or a dot, and caps length
    so a crafted filename can't smuggle a path or an oversized string into
    a directory entry.
    """
    raw = os.path.splitext(filename or "")[1] or default
    cleaned = _SAFE_EXT_RE.sub("", raw)
    if not cleaned.startswith("."):
        cleaned = f".{cleaned}"
    cleaned = cleaned[:20]
    if cleaned in ("", "."):
        return default
    return cleaned.lower()


def enforce_upload_size_limit(content: bytes, *, limit: int = MAX_UPLOAD_BYTES) -> None:
    """Raise HTTP 413 when uploaded bytes exceed the size cap."""
    if len(content) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content)} bytes); limit is {limit} bytes",
        )


def safe_download_response(
    base_dir: Path, *parts: str, original_name: Optional[str] = None,
) -> FileResponse:
    """Serve a file under `base_dir` with traversal protection and safe
    Content-Disposition/Content-Type headers.

    Every path segment is reduced to its basename before joining, so
    ``..`` / absolute-path segments in `parts` can never escape `base_dir`.
    Any extension not in the small inline-image allowlist — including
    html/svg — is served as `application/octet-stream` with
    `Content-Disposition: attachment`, so it downloads instead of
    executing/rendering in the browser.
    """
    base_dir = base_dir.resolve()
    candidate = base_dir
    for part in parts:
        candidate = candidate / Path(part).name  # basename only — no traversal

    resolved = candidate.resolve()
    if resolved != base_dir and base_dir not in resolved.parents:
        raise HTTPException(status_code=404, detail="Not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    ext = resolved.suffix.lower()
    download_name = Path(original_name).name if original_name else resolved.name

    headers = {"X-Content-Type-Options": "nosniff"}
    if is_inline_image_extension(ext):
        return FileResponse(resolved, media_type=_INLINE_IMAGE_MIME[ext], headers=headers)

    headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return FileResponse(resolved, media_type="application/octet-stream", headers=headers)
