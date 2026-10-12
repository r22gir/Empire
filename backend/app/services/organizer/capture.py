"""Capture inbox: voice, type, email, WhatsApp files. Edition-isolated store."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from app.services.data_paths import data_root
from app.services.organizer.edition import process_edition
from app.services.organizer.parse import parse_quick_add
from app.services.organizer.resolve import attach_matches, search_jobs, search_resources

MAX_BYTES = 25 * 1024 * 1024
ALLOWED_MIME = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/heif",
    "application/pdf",
    "text/plain", "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "audio/ogg", "audio/mpeg", "audio/mp4", "audio/webm", "audio/wav", "audio/x-wav",
    "video/mp4", "application/octet-stream",
}
ALLOWED_EXT = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif",
    ".pdf", ".txt", ".csv", ".doc", ".docx",
    ".ogg", ".mp3", ".m4a", ".webm", ".wav", ".mp4",
}


class CaptureRejected(ValueError):
    pass


def edition_store(edition: Optional[str] = None) -> Path:
    ed = edition or process_edition()
    root = data_root() / "organizer" / ed / "captures"
    root.mkdir(parents=True, exist_ok=True)
    # Refuse to write outside this edition folder.
    resolved = root.resolve()
    expected = (data_root() / "organizer" / ed).resolve()
    if expected not in resolved.parents and resolved != expected / "captures":
        raise CaptureRejected("edition store path escaped its root")
    return resolved


def _safe_name(name: str) -> str:
    base = Path(name or "file").name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:80]
    return base or "file"


def validate_payload(raw: bytes, filename: str, mime: Optional[str]) -> tuple[str, str]:
    if not raw:
        raise CaptureRejected("empty file")
    if len(raw) > MAX_BYTES:
        raise CaptureRejected(f"file too large ({len(raw)} bytes; max {MAX_BYTES})")
    ext = Path(filename or "").suffix.lower()
    guessed, _ = mimetypes.guess_type(filename or "")
    mime = (mime or guessed or "application/octet-stream").split(";")[0].strip().lower()
    if ext and ext not in ALLOWED_EXT:
        raise CaptureRejected(f"file type not allowed ({ext})")
    if mime not in ALLOWED_MIME and ext not in ALLOWED_EXT:
        raise CaptureRejected(f"mime type not allowed ({mime})")
    return mime, ext or ".bin"


def write_bytes(raw: bytes, *, filename: str, mime: Optional[str], edition: Optional[str] = None) -> dict:
    mime, ext = validate_payload(raw, filename, mime)
    cap_id = str(uuid.uuid4())[:12]
    safe = _safe_name(filename)
    if not Path(safe).suffix:
        safe += ext
    folder = edition_store(edition) / cap_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "id": cap_id,
        "filename": safe,
        "mime": mime,
        "bytes": len(raw),
        "sha256": digest,
        "relpath": f"{cap_id}/{safe}",
        "edition": edition or process_edition(),
        "public_url": None,
    }


def read_file(edition: str, relpath: str) -> Path:
    store = edition_store(edition)
    path = (store / relpath).resolve()
    if store not in path.parents and path != store:
        raise CaptureRejected("path escaped edition store")
    if not path.is_file():
        raise FileNotFoundError(relpath)
    return path


def guess_links(conn, text: str) -> dict:
    draft = parse_quick_add(text or "")
    draft = attach_matches(conn, draft)
    return draft


def ingest_whatsapp_media(
    conn,
    *,
    raw: bytes,
    filename: str,
    mime: str,
    caption: str,
    wa_id: str,
    message_id: str,
    kind: str,
) -> dict:
    from app.services.organizer.store import insert_item, now_iso, new_id, ensure_schema
    ensure_schema(conn)
    edition = process_edition()
    stored = write_bytes(raw, filename=filename, mime=mime, edition=edition)
    draft = guess_links(conn, caption or "")
    cap_id = new_id()
    stamp = now_iso()
    conn.execute(
        """
        INSERT INTO organizer_captures (
            id, edition, source, source_ref, filename, mime, bytes, sha256, relpath,
            job_id, resource_id, event_id, item_id, caption, public_url_blocked,
            created_at
        ) VALUES (?, ?, 'whatsapp', ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, 1, ?)
        """,
        (
            cap_id, edition, message_id or wa_id, stored["filename"], stored["mime"],
            stored["bytes"], stored["sha256"], stored["relpath"],
            draft.get("job_id"), draft.get("resource_id"), caption, stamp,
        ),
    )
    if caption and draft.get("kind"):
        insert_item(conn, {
            **{k: draft.get(k) for k in (
                "kind", "title", "job_id", "customer_id", "start_time", "end_time",
                "due_at", "phone", "location_address", "notes",
            )},
            "created_by": "max",
            "notes": f"From WhatsApp capture {cap_id}. Draft only.",
        })
    return {"capture_id": cap_id, "stored": stored, "draft": draft, "filed": True}
