"""Persist founder WhatsApp turns to chats/founder/whatsapp.json.

The Command Center chat list reads ``<chats_dir>/founder/*.json``.
SQLite (whatsapp_log) is the durable media/status log; this file is the
founder-visible thread, including link-only, media, and attachments.

Path honors EMPIRE_DATA_DIR via chats_dir() so tests never touch live data.
Never stores access tokens, app secrets, or FOUNDER_PIN.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.data_paths import chats_dir
from app.services.max.whatsapp_log import sanitize_no_secrets

logger = logging.getLogger("max.whatsapp")

_lock = threading.Lock()
FOUNDER_CHAT_ID = "whatsapp"
FOUNDER_USER = "founder"


def founder_whatsapp_path() -> Path:
    return chats_dir() / FOUNDER_USER / f"{FOUNDER_CHAT_ID}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_chat() -> dict[str, Any]:
    now = _now()
    return {
        "id": FOUNDER_CHAT_ID,
        "title": "WhatsApp (founder)",
        "created_at": now,
        "updated_at": now,
        "pinned": True,
        "preview": "",
        "channel": "whatsapp",
        "messages": [],
    }


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty_chat()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        logger.warning("founder whatsapp.json unreadable; starting a fresh file")
        return _empty_chat()
    if not isinstance(data, dict):
        return _empty_chat()
    data.setdefault("id", FOUNDER_CHAT_ID)
    data.setdefault("title", "WhatsApp (founder)")
    data.setdefault("channel", "whatsapp")
    data.setdefault("messages", [])
    if not isinstance(data["messages"], list):
        data["messages"] = []
    return data


def _preview(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        text = str(msg.get("content") or "").strip()
        if text:
            return text[:120]
    return ""


def append_founder_whatsapp(
    *,
    direction: str,
    body: str,
    message_type: str = "text",
    timestamp: Optional[str] = None,
    attachments: Optional[list[dict[str, Any]]] = None,
    wa_message_id: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> Path:
    """Append one inbound or outbound turn. Best-effort; never raises to callers."""
    path = founder_whatsapp_path()
    role = "assistant" if (direction or "").lower() == "outbound" else "user"
    clean_body = sanitize_no_secrets(body or "")
    atts = []
    for att in attachments or []:
        if not isinstance(att, dict):
            continue
        atts.append({
            "filename": att.get("filename") or "",
            "mime_type": att.get("mime_type") or att.get("mime") or "",
            "media_type": att.get("media_type") or att.get("kind") or "",
            "size_bytes": att.get("size_bytes") or 0,
            "doc_id": att.get("doc_id") or "",
            "filing_status": att.get("filing_status") or "",
        })
    entry = {
        "role": role,
        "content": clean_body,
        "timestamp": timestamp or _now(),
        "channel": "whatsapp",
        "message_type": message_type or "text",
        "wa_message_id": wa_message_id or "",
        "attachments": atts,
        "metadata": metadata or {},
    }
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _load(path)
        data["messages"].append(entry)
        data["updated_at"] = _now()
        data["preview"] = _preview(data["messages"])
        data["message_count"] = len(data["messages"])
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
    return path


def load_founder_whatsapp() -> dict[str, Any]:
    return _load(founder_whatsapp_path())
