"""Durable per-edition WhatsApp chat log.

Stores inbound and outbound turns (text, voice-note markers/transcripts,
document-sent markers, call events) plus Cloud API delivery status.
The SQLite file lives under this edition's data_root()/whatsapp so family
editions never share Rafael's log.

Never logs access tokens, app secrets, or API keys.
Attachment bytes and ~/jobs filing are deferred to a later step.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

from app.services.data_paths import data_root

logger = logging.getLogger("max.whatsapp_log")

_lock = threading.Lock()

_SECRET_ENVS = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "FOUNDER_PIN",
)

# Last-10 fallbacks if business.json has no founder_phones names.
_KNOWN_LABELS = {
    "2022996975": "Rafael",
    "7036239203": "Nelma",
}


def whatsapp_data_dir() -> Path:
    """Edition-scoped WhatsApp directory under data_root()."""
    base = data_root() / "whatsapp"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _db_path() -> Path:
    return whatsapp_data_dir() / "whatsapp_chat_log.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_id TEXT NOT NULL,
                    display_label TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    wa_message_id TEXT,
                    message_type TEXT NOT NULL,
                    body TEXT,
                    caption TEXT,
                    transcript TEXT,
                    delivery_status TEXT DEFAULT 'sent',
                    error_code TEXT,
                    error_message TEXT,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_wam_wa_id ON whatsapp_messages(wa_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_wam_msg_id ON whatsapp_messages(wa_message_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_wam_time ON whatsapp_messages(timestamp)"
            )
            conn.commit()
        finally:
            conn.close()


def _digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _phone_from_entry(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("phone") or item.get("number") or item.get("wa_id") or "")
    return str(item or "")


def _load_business() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "config" / "business.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _labels_from_business() -> dict[str, str]:
    """Map last-10 phone digits -> display name from founder_phones / owner_phones."""
    data = _load_business()
    labels: dict[str, str] = {}
    for key in ("founder_phones", "owner_phones"):
        extra = data.get(key) or []
        if isinstance(extra, dict):
            extra = [
                {"name": name, "phone": phone}
                for name, phone in extra.items()
            ]
        if not isinstance(extra, list):
            continue
        for item in extra:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("label") or "").strip()
            phone = _phone_from_entry(item)
            tail = _digits(phone)[-10:]
            if name and len(tail) == 10:
                labels[tail] = name
    owner = str(data.get("owner_name") or "").strip()
    biz = _digits(str(data.get("business_phone") or ""))[-10:]
    if owner and len(biz) == 10 and biz not in labels:
        labels[biz] = owner
    return labels


def get_display_label(wa_id: str) -> str:
    """Map a WhatsApp id to Rafael / Nelma / a founder_phones name."""
    digits = _digits(wa_id)
    if not digits:
        return "Unknown"
    tail10 = digits[-10:]
    labels = _labels_from_business()
    if tail10 in labels:
        return labels[tail10]
    if tail10 in _KNOWN_LABELS:
        return _KNOWN_LABELS[tail10]
    return f"+{digits}" if not str(wa_id).startswith("+") else str(wa_id)


def sanitize_no_secrets(text: str) -> str:
    """Strip bearer tokens and known WhatsApp / founder secrets from stored text."""
    if not text:
        return ""
    sanitized = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.IGNORECASE)
    sanitized = re.sub(
        r"(access_token|app_secret|verify_token|api[_-]?key)\s*[:=]\s*\S+",
        r"\1=[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )
    for secret_env in _SECRET_ENVS:
        val = os.getenv(secret_env)
        if val and len(val) > 3:
            sanitized = sanitized.replace(val, "[REDACTED]")
    return sanitized


def iso_from_wa_timestamp(value: Any) -> str:
    if value is None or value == "":
        return datetime.now(timezone.utc).isoformat()
    text = str(value).strip()
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def log_message(
    wa_id: str,
    direction: str,
    message_type: str,
    *,
    body: str = "",
    caption: str = "",
    transcript: str = "",
    wa_message_id: str = "",
    delivery_status: str = "sent",
    error_code: str = "",
    error_message: str = "",
    metadata: Optional[dict] = None,
    timestamp: Optional[str] = None,
) -> int:
    """Append one inbound or outbound turn. Never stores secrets."""
    init_db()
    norm_id = str(wa_id or "").strip()
    display_label = get_display_label(norm_id)
    now_ts = timestamp or datetime.now(timezone.utc).isoformat()
    clean_body = sanitize_no_secrets(body)
    clean_caption = sanitize_no_secrets(caption)
    clean_transcript = sanitize_no_secrets(transcript)
    meta_json = sanitize_no_secrets(json.dumps(metadata or {}, default=str))

    with _lock:
        conn = _get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO whatsapp_messages (
                    wa_id, display_label, direction, timestamp, wa_message_id,
                    message_type, body, caption, transcript, delivery_status,
                    error_code, error_message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    norm_id,
                    display_label,
                    direction,
                    now_ts,
                    wa_message_id,
                    message_type,
                    clean_body,
                    clean_caption,
                    clean_transcript,
                    delivery_status,
                    error_code,
                    error_message,
                    meta_json,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            conn.close()


def update_delivery_status(
    wa_message_id: str,
    status: str,
    *,
    error_code: str = "",
    error_message: str = "",
) -> bool:
    """Apply a Cloud API status webhook (sent, delivered, read, failed)."""
    if not wa_message_id:
        return False
    allowed = {"sent", "delivered", "read", "failed"}
    clean_status = (status or "").strip().lower()
    if clean_status not in allowed:
        return False
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                """UPDATE whatsapp_messages
                   SET delivery_status = ?, error_code = ?, error_message = ?
                   WHERE wa_message_id = ?""",
                (
                    clean_status,
                    str(error_code or ""),
                    sanitize_no_secrets(str(error_message or "")),
                    wa_message_id,
                ),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def _row_to_message(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    try:
        item["metadata"] = json.loads(item["metadata_json"]) if item.get("metadata_json") else {}
    except Exception:
        item["metadata"] = {}
    return item


def list_conversations() -> List[dict[str, Any]]:
    """Conversations grouped by sender, newest last message first."""
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                wa_id,
                display_label,
                COUNT(*) as total_messages,
                MAX(timestamp) as last_timestamp
            FROM whatsapp_messages
            GROUP BY wa_id
            ORDER BY last_timestamp DESC
            """
        ).fetchall()
        conversations = []
        for r in rows:
            wa_id = r["wa_id"]
            last = conn.execute(
                """
                SELECT body, caption, transcript, message_type, direction,
                       delivery_status, error_code, error_message, timestamp
                FROM whatsapp_messages
                WHERE wa_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (wa_id,),
            ).fetchone()
            preview = ""
            if last:
                preview = (
                    last["body"]
                    or last["caption"]
                    or last["transcript"]
                    or f"[{last['message_type']}]"
                )
            conversations.append(
                {
                    "wa_id": wa_id,
                    "display_label": r["display_label"],
                    "total_messages": r["total_messages"],
                    "last_timestamp": r["last_timestamp"],
                    "last_message": preview,
                    "last_direction": last["direction"] if last else "inbound",
                    "last_status": last["delivery_status"] if last else "sent",
                    "last_error_code": last["error_code"] if last else "",
                    "last_error": last["error_message"] if last else None,
                }
            )
        return conversations
    finally:
        conn.close()


def get_conversation_messages(
    wa_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
) -> Tuple[List[dict[str, Any]], int]:
    """Paginated messages for one sender, optional text filter."""
    init_db()
    norm_id = str(wa_id or "").strip()
    conn = _get_conn()
    try:
        where = ["wa_id = ?"]
        params: List[Any] = [norm_id]
        if search and search.strip():
            pat = f"%{search.strip()}%"
            where.append(
                "(body LIKE ? OR caption LIKE ? OR transcript LIKE ? OR message_type LIKE ?)"
            )
            params.extend([pat, pat, pat, pat])
        where_sql = " AND ".join(where)
        total = conn.execute(
            f"SELECT COUNT(*) FROM whatsapp_messages WHERE {where_sql}",
            params,
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT * FROM whatsapp_messages
            WHERE {where_sql}
            ORDER BY timestamp ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            params + [max(1, min(int(limit), 200)), max(0, int(offset))],
        ).fetchall()
        return [_row_to_message(r) for r in rows], int(total)
    finally:
        conn.close()


def search_all_messages(query_text: str, *, limit: int = 50) -> List[dict[str, Any]]:
    """Simple text search across every conversation in this edition."""
    init_db()
    if not query_text or not query_text.strip():
        return []
    pat = f"%{query_text.strip()}%"
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT * FROM whatsapp_messages
            WHERE body LIKE ? OR caption LIKE ? OR transcript LIKE ?
               OR display_label LIKE ? OR wa_id LIKE ? OR message_type LIKE ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (pat, pat, pat, pat, pat, pat, max(1, min(int(limit), 200))),
        ).fetchall()
        return [_row_to_message(r) for r in rows]
    finally:
        conn.close()
