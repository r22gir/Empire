"""D44 — single writer for job images.

Every image channel (MAX chat web, Telegram, quote /photos/upload, LuxeForge
intake) lands bytes through this function. Email inbound is intentionally
NOT wired here — see D44 STEP 0/STOP 1 finding 3.

Storage shape:
    ~/empire-data/photos/job/<key>/<safe-stem>-<uuid8>.<ext>

    <key> = job_id            (when caller has one)
          | quote_<quote_id>  (when only quote is known)
          | "unassigned"      (when neither is known — PENDING bucket)

Validation:
    Reuses the D43 decode-verify guard (vision.decode_image_input) so
    non-image payloads are rejected at the boundary with HTTP 400.
    We re-encode bytes -> base64 -> decode so the guard sees a string in
    the same form it was designed for. No reimplementation.

DB row written to job_documents:
    job_id           nullable per STOP 1 ruling #1 (kept working for
                     jobs_unified paths)
    quote_id         new column, nullable; keys documents off the quote
                     when no job row exists
    source_channel   new column; one of max_chat|telegram|email|
                     quote_ui|luxeforge_intake
    document_type    "photo" (default), "scan_3d", or "drawing"
    item_key         optional per-item linkage from quote room items
    route_to         business routing ("workroom"|"woodcraft") —
                     preserved with its prior semantics
    filename         on-disk filename under the landing dir
    url              served path: /api/v1/photos/job/<key>/
    revision         1 on first write
    visible_to_client 0 — the permissive default is what produced H74
                     and is not repeated here.
"""
from __future__ import annotations

import base64
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from app.services.drawing.canonical_path import (
    canonical_empire_db_path,
    canonical_photos_dir,
)

logger = logging.getLogger(__name__)

# Source-channel enumeration (matches D44 STOP 1 ruling #6).
SOURCE_CHANNELS = frozenset({
    "max_chat", "telegram", "email", "quote_ui", "luxeforge_intake",
})

DOCUMENT_TYPES = frozenset({"photo", "scan_3d", "drawing"})

_UNASSIGNED_KEY = "unassigned"


def _safe_segment(text: str, max_len: int = 60) -> str:
    """Sanitize a string for use as a filesystem segment or DB key suffix."""
    keep = "".join(c for c in text if c.isalnum() or c in "._-")
    return keep[:max_len] or "x"


def _resolve_key(job_id: Optional[str], quote_id: Optional[str]) -> str:
    """Pick the directory key under photos/job/ for this document."""
    if job_id:
        return _safe_segment(job_id)
    if quote_id:
        return f"quote_{_safe_segment(quote_id)}"
    return _UNASSIGNED_KEY


def _landing_dir(key: str) -> Path:
    base = Path(canonical_photos_dir()) / "job" / key
    base.mkdir(parents=True, exist_ok=True)
    return base


def _full_path(key: str, filename: str) -> Path:
    """Resolve a (key, filename) pair to an absolute path on disk."""
    safe = Path(filename).name  # strip any path components
    return Path(canonical_photos_dir()) / "job" / key / safe


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(canonical_empire_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def _validate_payload(raw_bytes: bytes) -> tuple[bytes, str]:
    """Run the D43 decode-verify guard on raw image bytes.

    Returns (validated_bytes, ext). Raises ValueError on rejection.
    """
    # Late import: the guard lives in a router module; importing at module
    # scope would force circular imports during pytest collection.
    from app.routers.vision import decode_image_input
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    try:
        validated, ext = decode_image_input(b64)
    except HTTPException as exc:
        raise ValueError(f"image rejected: {exc.detail}") from exc
    if not validated or len(validated) < 32:
        raise ValueError("image payload is too small")
    return validated, ext


def store_job_image(
    raw_bytes: bytes,
    *,
    source_channel: str,
    document_type: str = "photo",
    job_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    item_key: Optional[str] = None,
    route_to: Optional[str] = None,
    original_filename: Optional[str] = None,
) -> dict:
    """Validate, store, and record a job image. Returns the job_documents row.

    Raises ValueError on validation failure (no row inserted, no file written).
    Raises ValueError on unknown source_channel / document_type.
    """
    if source_channel not in SOURCE_CHANNELS:
        raise ValueError(
            f"unknown source_channel: {source_channel!r}; "
            f"must be one of {sorted(SOURCE_CHANNELS)}"
        )
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(
            f"unknown document_type: {document_type!r}; "
            f"must be one of {sorted(DOCUMENT_TYPES)}"
        )

    validated, ext = _validate_payload(raw_bytes)

    key = _resolve_key(job_id, quote_id)
    stem_src = original_filename or "image"
    safe_stem = _safe_segment(Path(stem_src).stem or "image")
    fname = f"{safe_stem}-{uuid.uuid4().hex[:8]}{ext}"
    out_dir = _landing_dir(key)
    out_path = out_dir / fname
    out_path.write_bytes(validated)

    now_iso = datetime.now(timezone.utc).isoformat()
    url = f"/api/v1/photos/job/{key}/{fname}"

    conn = _open_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO job_documents (
                job_id, quote_id, document_type, item_key,
                url, filename, revision, visible_to_client,
                route_to, source_channel, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?)
            """,
            (
                job_id, quote_id, document_type, item_key,
                url, fname, route_to, source_channel, now_iso,
            ),
        )
        # id is TEXT (randomblob hex); lastrowid is the SQLite rowid.
        # Query back via rowid to fetch the inserted row.
        new_rowid = cur.lastrowid
        conn.commit()
        cur.execute("SELECT * FROM job_documents WHERE rowid = ?", (new_rowid,))
        row = dict(cur.fetchone())
    finally:
        conn.close()

    logger.info(
        "job_image_stored id=%s key=%s file=%s bytes=%d channel=%s type=%s",
        row.get("id"), key, fname, len(validated), source_channel, document_type,
    )
    return row


def list_job_documents(
    *,
    job_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    unassigned: bool = False,
    limit: int = 50,
) -> list[dict]:
    """List job_documents filtered by job_id, quote_id, or unassigned bucket.

    The three filters are mutually exclusive; callers pass at most one.
    Returns rows ordered by created_at DESC.
    """
    conn = _open_db()
    try:
        if unassigned:
            sql = (
                "SELECT * FROM job_documents "
                "WHERE job_id IS NULL AND quote_id IS NULL "
                "ORDER BY created_at DESC LIMIT ?"
            )
            cur = conn.execute(sql, (limit,))
        elif job_id:
            cur = conn.execute(
                "SELECT * FROM job_documents WHERE job_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (job_id, limit),
            )
        elif quote_id:
            cur = conn.execute(
                "SELECT * FROM job_documents WHERE quote_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (quote_id, limit),
            )
        else:
            # No filter — caller should pass one. Refuse rather than scan all.
            raise ValueError(
                "list_job_documents requires job_id, quote_id, or unassigned=True"
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_job_document(document_id: str) -> Optional[dict]:
    """Look up a single job_documents row by its primary key."""
    conn = _open_db()
    try:
        cur = conn.execute("SELECT * FROM job_documents WHERE id = ?", (document_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def resolve_document_path(row: dict) -> Path:
    """Resolve the on-disk path for a job_documents row. Does not check existence."""
    job_id = row.get("job_id")
    quote_id = row.get("quote_id")
    key = _resolve_key(job_id, quote_id)
    return _full_path(key, row.get("filename") or "")


def read_and_validate_job_image(row: dict) -> bytes:
    """Read the file for a job_documents row and re-validate it via the D43 guard.

    Returns validated bytes. Raises FileNotFoundError or ValueError on failure.
    """
    path = resolve_document_path(row)
    if not path.exists():
        raise FileNotFoundError(f"job_documents row {row.get('id')} missing file: {path}")
    raw = path.read_bytes()
    _validate_payload(raw)  # raises ValueError on bad bytes
    return raw
