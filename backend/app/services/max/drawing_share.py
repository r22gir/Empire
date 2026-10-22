"""Just-generated drawing share links — never an older file, never a relative path.

When Max returns a drawing link it must be the file written for THIS request
(path + mtime verified) as a full absolute studio share URL.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Optional

_LAST: dict[str, dict[str, Any]] = {}

_SHOW_LINK = re.compile(
    r"(?i)\b(?:"
    r"done\??|is it done|are you done|finished\??|"
    r"show it|show me(?: it| the (?:drawing|link|pdf|file|mockup))?|"
    r"give me(?: the)?(?: (?:drawing|link|pdf|file|share(?: link)?|studio(?: link)?))?|"
    r"where is it|where(?:'s| is) the (?:drawing|link|pdf|file|mockup)|"
    r"send me(?: the)? (?:link|drawing|studio link)|"
    r"studio(?: share)? link|share(?: me)?(?: the)? link"
    r")\b"
)

_VOICE_STUDIO = re.compile(r"(?i)\b(?:studio|share\s+link)\b")
_VOICE_LINK = re.compile(r"(?i)\b(?:give|send|get|show|the|a)\s+(?:me\s+)?(?:the\s+)?link\b|\blink\b")
_VOICE_SEND_CHANNEL = re.compile(r"(?i)\b(?:whatsapp|whats\s*app|e-?mail|gmail|text me|sms)\b")


def remember_key(conversation_id: str | None, job_hint: str | None, history: Any = None) -> Optional[str]:
    if conversation_id:
        return f"cid:{conversation_id}"
    hint = (job_hint or "").strip()
    if hint:
        return f"job:{hint.lower()}"
    try:
        from app.services.max.job_drawing_intent import extract_job_hint, _history_blob
        hint = extract_job_hint(_history_blob(history)) or ""
    except Exception:
        hint = ""
    return f"job:{hint.lower()}" if hint else None


def remember_drawing(key: str | None, result: dict[str, Any]) -> None:
    if not key or not result or not result.get("success"):
        return
    _LAST[key] = dict(result)


def last_drawing(key: str | None) -> Optional[dict[str, Any]]:
    if not key:
        return None
    return _LAST.get(key)


def clear_drawings() -> None:
    _LAST.clear()


def is_show_link_request(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw or len(raw) > 160:
        return False
    return bool(_SHOW_LINK.search(raw))


def is_drawing_ready_followup(text: str | None, history: Any = None) -> bool:
    """'done? show it / give me link' while a drawing/doc is in this chat."""
    if not is_show_link_request(text):
        return False
    try:
        from app.services.max.job_drawing_intent import history_has_drawing_job_context
        if history_has_drawing_job_context(history):
            return True
    except Exception:
        pass
    blob = ""
    for item in list(history or [])[-8:]:
        if isinstance(item, dict):
            blob += " " + str(item.get("content") or "")
        else:
            blob += " " + str(getattr(item, "content", "") or "")
    return bool(re.search(r"\b(?:drawing|drawings|mockup|shop drawing|layout)\b", blob, re.I))


def wants_studio_share(text: str | None) -> bool:
    """Voice/chat: 'studio' or 'link' means a studio share URL, not WhatsApp/email."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _VOICE_STUDIO.search(raw):
        return True
    if _VOICE_LINK.search(raw) and not _VOICE_SEND_CHANNEL.search(raw):
        return True
    return False


def verify_generated_file(path: str | Path, *, min_mtime: float, min_size: int = 80) -> dict[str, Any]:
    """Confirm the path exists, is the just-written file, and is large enough."""
    p = Path(path)
    abs_path = str(p.resolve()) if p.exists() else str(p)
    if not p.is_file():
        return {"ok": False, "path": abs_path, "error": "missing"}
    st = p.stat()
    if st.st_size < min_size:
        return {"ok": False, "path": abs_path, "size": st.st_size, "error": "too_small"}
    # Clock skew: allow 2s before min_mtime. Reject files older than the write start.
    if st.st_mtime + 2.0 < min_mtime:
        return {
            "ok": False,
            "path": abs_path,
            "mtime": st.st_mtime,
            "min_mtime": min_mtime,
            "error": "stale_mtime",
        }
    return {
        "ok": True,
        "path": abs_path,
        "mtime": st.st_mtime,
        "size": st.st_size,
    }


def absolute_share_url(path: str | Path) -> str:
    """Full https://studio.empirebox.store/api/v1/files/found?t=... or ''."""
    try:
        from app.services.max.doc_links import studio_found_url
        return studio_found_url(str(path)) or ""
    except Exception:
        return ""


def attach_share_proof(result: dict[str, Any], path: str | Path, *, min_mtime: float) -> dict[str, Any]:
    proof = verify_generated_file(path, min_mtime=min_mtime)
    result["pdf_path"] = proof.get("path") or str(path)
    result["pdf_mtime"] = proof.get("mtime")
    result["pdf_verified"] = bool(proof.get("ok"))
    if not proof.get("ok"):
        result["verify_error"] = proof.get("error")
        return result
    url = absolute_share_url(result["pdf_path"])
    result["share_url"] = url
    if url:
        name = Path(result["pdf_path"]).name
        result["markdown_link"] = f"[{name}]({url})"
    return result
