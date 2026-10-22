"""In-memory last-generated drawing for the current chat.

Used so 'done? show it / give me link' returns the file just produced
for this request — never an older find_files hit. No live I/O.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

_LAST: dict[str, dict[str, Any]] = {}


def _key(conversation_id: str | None, channel: str | None = None) -> str:
    conv = (conversation_id or "").strip() or "_anon"
    ch = (channel or "").strip() or "web"
    return f"{ch}:{conv}"


def remember_drawing(
    conversation_id: str | None,
    record: dict[str, Any],
    *,
    channel: str | None = None,
) -> dict[str, Any]:
    stored = dict(record or {})
    stored.setdefault("remembered_at", time.time())
    _LAST[_key(conversation_id, channel)] = stored
    return stored


def recall_drawing(
    conversation_id: str | None,
    *,
    channel: str | None = None,
) -> Optional[dict[str, Any]]:
    rec = _LAST.get(_key(conversation_id, channel))
    return dict(rec) if rec else None


def clear_drawing(conversation_id: str | None, *, channel: str | None = None) -> None:
    _LAST.pop(_key(conversation_id, channel), None)


def verify_generated_file(
    path: str | None,
    *,
    expected_mtime: float | None = None,
    generated_at: float | None = None,
    min_size: int = 80,
    max_age_s: float = 6 * 3600,
) -> dict[str, Any]:
    """Confirm path exists, is the just-written file, and mtime is fresh."""
    if not path:
        return {"ok": False, "error": "no path"}
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "missing", "path": str(path)}
    st = p.stat()
    if st.st_size < min_size:
        return {"ok": False, "error": "too_small", "path": str(p), "size": st.st_size}
    now = time.time()
    if expected_mtime is not None and abs(st.st_mtime - float(expected_mtime)) > 2.0:
        return {"ok": False, "error": "mtime_mismatch", "path": str(p), "mtime": st.st_mtime}
    if generated_at is not None and st.st_mtime + 2.0 < float(generated_at):
        return {"ok": False, "error": "older_than_generation", "path": str(p), "mtime": st.st_mtime}
    if now - st.st_mtime > max_age_s:
        return {"ok": False, "error": "stale", "path": str(p), "mtime": st.st_mtime}
    return {
        "ok": True,
        "path": str(p.resolve()),
        "mtime": st.st_mtime,
        "size": st.st_size,
        "filename": p.name,
    }


def verify_record(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {"ok": False, "error": "no_record"}
    return verify_generated_file(
        record.get("pdf_path"),
        expected_mtime=record.get("mtime"),
        generated_at=record.get("generated_at") or record.get("remembered_at"),
    )
