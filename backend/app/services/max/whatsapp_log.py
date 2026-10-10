"""Durable per-edition WhatsApp chat log.

Stores inbound and outbound turns (text, voice-note markers/transcripts,
document-sent markers, call events) plus Cloud API delivery status.
The SQLite file lives under this edition's data_root()/whatsapp so family
editions never share Rafael's log.

Never logs access tokens, app secrets, or API keys.
Inbound media is stored under this edition's whatsapp/media (URLs expire).
Photos and documents are copied into ~/jobs/<slug>/photos|received when the
job is known; otherwise they park in whatsapp/inbox until the sender answers.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

from app.services.data_paths import data_root
from app.services.max.doc_lookup import existing_job_slug, jobs_root, list_job_folders, probe_job_text, resolve_job_folder

logger = logging.getLogger("max.whatsapp_log")

_lock = threading.Lock()

_SECRET_ENVS = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "FOUNDER_PIN",
)

DEFAULT_MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024
DEFAULT_RETENTION_DAYS = 365
DEFAULT_JOB_ANSWER_TIMEOUT = 1800
JOB_ASK_TEXT = (
    "Which job should I file this under? Reply with the client name, nickname, "
    "job address, or quote number. I will not guess. Reply skip to leave it in the inbox."
)
JOB_SKIP_WORDS = {"skip", "cancel"}
FILEABLE_TYPES = {"image", "photo", "document"}
UNSAFE_MEDIA_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "image/svg+xml",
    "text/xml",
    "application/xml",
    "text/javascript",
    "application/javascript",
}
SAFE_INLINE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
}


def get_max_attachment_size() -> int:
    try:
        val = os.getenv("WHATSAPP_MAX_ATTACHMENT_SIZE_BYTES")
        if val and val.strip():
            return int(val.strip())
    except Exception:
        pass
    return DEFAULT_MAX_ATTACHMENT_SIZE


def get_job_answer_timeout() -> int:
    try:
        val = os.getenv("WHATSAPP_JOB_ANSWER_TIMEOUT_SECONDS")
        if val and val.strip():
            return max(30, int(val.strip()))
    except Exception:
        pass
    return DEFAULT_JOB_ANSWER_TIMEOUT


def get_retention_days() -> int:
    try:
        val = os.getenv("WHATSAPP_RETENTION_DAYS")
        if val and val.strip():
            return int(val.strip())
    except Exception:
        pass
    return DEFAULT_RETENTION_DAYS


def whatsapp_data_dir() -> Path:
    """Edition-scoped WhatsApp directory under data_root()."""
    base = data_root() / "whatsapp"
    base.mkdir(parents=True, exist_ok=True)
    return base


def media_dir() -> Path:
    d = whatsapp_data_dir() / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def inbox_dir() -> Path:
    d = whatsapp_data_dir() / "inbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL REFERENCES whatsapp_messages(id) ON DELETE CASCADE,
                    wa_media_id TEXT,
                    filename TEXT NOT NULL,
                    mime_type TEXT,
                    size_bytes INTEGER,
                    local_path TEXT,
                    media_type TEXT NOT NULL,
                    doc_id TEXT,
                    job_slug TEXT,
                    filed_path TEXT,
                    filed_at TEXT,
                    filing_status TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_active_jobs (
                    wa_id TEXT PRIMARY KEY,
                    job_slug TEXT NOT NULL,
                    client_name TEXT,
                    folder_path TEXT,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_pending_filings (
                    wa_id TEXT PRIMARY KEY,
                    attachment_ids TEXT NOT NULL,
                    asked_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_waa_msg ON whatsapp_attachments(message_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_waa_job ON whatsapp_attachments(job_slug)")
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


def _phonebook_paths() -> list[Path]:
    paths: list[Path] = []
    env = (os.getenv("WHATSAPP_LABELS") or "").strip()
    if env:
        paths.append(Path(env))
    try:
        paths.append(whatsapp_data_dir() / "labels.json")
    except Exception:
        pass
    return paths


def load_whatsapp_phonebook() -> list[dict[str, str]]:
    """Founder names/phones from edition data or WHATSAPP_LABELS. Not committed."""
    rows: list[dict[str, str]] = []
    for path in _phonebook_paths():
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        phones = data.get("phones") if isinstance(data, dict) else data
        if isinstance(phones, dict):
            phones = [{"name": name, "phone": phone} for name, phone in phones.items()]
        if not isinstance(phones, list):
            continue
        for item in phones:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("label") or "").strip()
                phone = _phone_from_entry(item)
                if phone:
                    rows.append({"name": name, "phone": phone})
            elif item:
                rows.append({"name": "", "phone": str(item)})
        if rows:
            break
    data = _load_business()
    for key in ("founder_phones", "owner_phones"):
        extra = data.get(key) or []
        if isinstance(extra, dict):
            extra = [{"name": name, "phone": phone} for name, phone in extra.items()]
        if not isinstance(extra, list):
            continue
        for item in extra:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("label") or "").strip()
                phone = _phone_from_entry(item)
                if phone:
                    rows.append({"name": name, "phone": phone})
            elif item:
                rows.append({"name": "", "phone": str(item)})
    env_phones = os.getenv("WHATSAPP_FOUNDER_PHONES") or ""
    for part in env_phones.split(","):
        if part.strip():
            rows.append({"name": "", "phone": part.strip()})
    return rows


def _labels_from_phonebook() -> dict[str, str]:
    """Map last-10 phone digits -> display name from the edition phonebook."""
    labels: dict[str, str] = {}
    for item in load_whatsapp_phonebook():
        name = str(item.get("name") or "").strip()
        tail = _digits(item.get("phone") or "")[-10:]
        if name and len(tail) == 10:
            labels[tail] = name
    data = _load_business()
    owner = str(data.get("owner_name") or "").strip()
    biz = _digits(str(data.get("business_phone") or ""))[-10:]
    if owner and len(biz) == 10 and biz not in labels:
        labels[biz] = owner
    return labels


def get_display_label(wa_id: str) -> str:
    """Map a WhatsApp id to a phonebook name. No hardcoded founder numbers."""
    digits = _digits(wa_id)
    if not digits:
        return "Unknown"
    tail10 = digits[-10:]
    labels = _labels_from_phonebook()
    if tail10 in labels:
        return labels[tail10]
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
    attachments: Optional[List[dict]] = None,
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
            msg_id = int(cursor.lastrowid)
            now_file = datetime.now(timezone.utc).isoformat()
            for att in attachments or []:
                conn.execute(
                    """INSERT INTO whatsapp_attachments (
                        message_id, wa_media_id, filename, mime_type, size_bytes,
                        local_path, media_type, doc_id, job_slug, filed_path,
                        filed_at, filing_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        msg_id,
                        att.get("wa_media_id", ""),
                        att.get("filename", "file"),
                        att.get("mime_type", ""),
                        att.get("size_bytes", 0),
                        att.get("local_path", ""),
                        att.get("media_type", "document"),
                        att.get("doc_id", ""),
                        att.get("job_slug", ""),
                        att.get("filed_path", ""),
                        att.get("filed_at") or (now_file if att.get("filed_path") else None),
                        att.get("filing_status", ""),
                    ),
                )
            conn.commit()
            return msg_id
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


def _public_attachment(row: sqlite3.Row | dict) -> dict[str, Any]:
    att = dict(row)
    return {
        "id": att.get("id"),
        "filename": att.get("filename"),
        "mime_type": att.get("mime_type"),
        "size_bytes": att.get("size_bytes"),
        "media_type": att.get("media_type"),
        "doc_id": att.get("doc_id") or "",
        "job_slug": att.get("job_slug") or "",
        "filed_path": att.get("filed_path") or "",
        "filing_status": att.get("filing_status") or "",
        "has_file": bool(att.get("local_path") and Path(str(att.get("local_path"))).is_file()),
    }


def _attachments_for(conn: sqlite3.Connection, message_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM whatsapp_attachments WHERE message_id = ?",
        (message_id,),
    ).fetchall()
    return [_public_attachment(r) for r in rows]


def _row_to_message(row: sqlite3.Row, attachments: Optional[list] = None) -> dict[str, Any]:
    item = dict(row)
    try:
        item["metadata"] = json.loads(item["metadata_json"]) if item.get("metadata_json") else {}
    except Exception:
        item["metadata"] = {}
    item["attachments"] = attachments or []
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
                    "active_job": get_active_job(wa_id),
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
        return [_row_to_message(r, _attachments_for(conn, r["id"])) for r in rows], int(total)
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
        return [_row_to_message(r, _attachments_for(conn, r["id"])) for r in rows]
    finally:
        conn.close()


def sanitize_filename(filename: str, max_len: int = 120) -> str:
    """Strip controls, path separators, and over-long names."""
    raw = str(filename or "attachment").replace("\x00", "")
    raw = "".join(ch for ch in raw if ch.isprintable() and ord(ch) >= 32)
    raw = raw.replace("\\", "/").split("/")[-1]
    raw = re.sub(r'[<>:"|?*]', "", raw).strip(" .")
    if not raw or raw in {".", ".."}:
        raw = "attachment"
    suffix = Path(raw).suffix
    if suffix.lower() in {".html", ".htm", ".svg", ".shtml", ".xhtml"}:
        raw = f"{Path(raw).stem or 'attachment'}.bin"
        suffix = ".bin"
    if len(raw) > max_len:
        stem = Path(raw).stem
        keep = max(1, max_len - len(suffix))
        raw = f"{stem[:keep]}{suffix}"
    return raw or "attachment"


def media_serve_headers(mime_type: str, filename: str) -> tuple[str, dict[str, str]]:
    """Safe Content-Type + nosniff. Non-image/PDF always download as attachment."""
    clean_name = sanitize_filename(filename)
    raw_mime = (mime_type or "").split(";")[0].strip().lower()
    headers = {"X-Content-Type-Options": "nosniff"}
    if raw_mime in UNSAFE_MEDIA_TYPES or raw_mime not in SAFE_INLINE_TYPES:
        headers["Content-Disposition"] = f'attachment; filename="{clean_name}"'
        return "application/octet-stream", headers
    headers["Content-Disposition"] = f'inline; filename="{clean_name}"'
    return raw_mime or "application/octet-stream", headers


def unique_dest(directory: Path, filename: str) -> Path:
    """Never overwrite: add a UTC timestamp suffix when the name exists."""
    directory.mkdir(parents=True, exist_ok=True)
    clean = sanitize_filename(filename)
    stem = Path(clean).stem or "attachment"
    suffix = Path(clean).suffix or ".bin"
    dest = directory / f"{stem}{suffix}"
    if dest.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = directory / f"{stem}_{stamp}{suffix}"
    if dest.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        dest = directory / f"{stem}_{stamp}{suffix}"
    return dest


def store_edition_media(
    content: bytes,
    filename: str,
    mime_type: str,
    media_type: str,
) -> dict[str, Any]:
    """Save bytes under this edition's media dir. Honors the size cap."""
    cap = get_max_attachment_size()
    size = len(content or b"")
    if size > cap:
        return {
            "filename": Path(filename or "attachment").name,
            "mime_type": mime_type,
            "media_type": media_type,
            "size_bytes": size,
            "local_path": "",
            "skipped": True,
            "reason": "over_size_cap",
        }
    dest = unique_dest(media_dir(), filename)
    dest.write_bytes(content or b"")
    purge_expired_media()
    return {
        "filename": dest.name,
        "mime_type": mime_type,
        "media_type": media_type,
        "size_bytes": size,
        "local_path": str(dest),
        "skipped": False,
    }


def file_into_job(
    content: bytes,
    filename: str,
    media_type: str,
    job_slug: str,
) -> str:
    """Copy into ~/jobs/<slug>/photos or received. Never overwrites."""
    sub = "photos" if media_type in ("image", "photo") else "received"
    dest = unique_dest(jobs_root() / job_slug / sub, filename)
    dest.write_bytes(content or b"")
    return str(dest)


def park_in_inbox(content: bytes, filename: str) -> str:
    dest = unique_dest(inbox_dir(), filename)
    dest.write_bytes(content or b"")
    return str(dest)


def get_active_job(wa_id: str) -> Optional[dict[str, Any]]:
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT wa_id, job_slug, client_name, folder_path, updated_at "
            "FROM whatsapp_active_jobs WHERE wa_id = ?",
            (str(wa_id or "").strip(),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_active_job(wa_id: str, job_slug: str, client_name: str = "", folder_path: str = "") -> None:
    init_db()
    now_str = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO whatsapp_active_jobs (wa_id, job_slug, client_name, folder_path, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                   job_slug=excluded.job_slug,
                   client_name=excluded.client_name,
                   folder_path=excluded.folder_path,
                   updated_at=excluded.updated_at""",
                (str(wa_id or "").strip(), job_slug, client_name, folder_path, now_str),
            )
            conn.commit()
        finally:
            conn.close()


def choose_job_for_inbound(text: str, wa_id: str) -> dict[str, Any]:
    """Named unique match only. A text with no job name never uses a sticky job."""
    probed = probe_job_text(text)
    status = probed.get("status")
    if status == "unique":
        match = probed["match"]
        set_active_job(wa_id, match["slug"], match.get("client_name", ""), match.get("folder_path", ""))
        return {"status": "unique", "job": match}
    if status == "ambiguous":
        return {"status": "ambiguous", "job": None, "matches": probed.get("matches") or []}
    return {"status": "unknown", "job": None}


def prepare_inbound_attachment(
    content: bytes,
    *,
    filename: str,
    mime_type: str,
    media_type: str,
    wa_id: str,
    hint_text: str = "",
    wa_media_id: str = "",
    doc_id: str = "",
    file_to_job: bool = True,
) -> dict[str, Any]:
    """Store under the edition media dir and file photos/docs when the job is known."""
    stored = store_edition_media(content, filename, mime_type, media_type)
    record = {
        "wa_media_id": wa_media_id,
        "filename": stored.get("filename") or filename,
        "mime_type": mime_type,
        "size_bytes": stored.get("size_bytes") or len(content or b""),
        "local_path": stored.get("local_path") or "",
        "media_type": media_type,
        "doc_id": doc_id,
        "job_slug": "",
        "filed_path": "",
        "filing_status": "stored",
        "needs_job_ask": False,
        "skipped": bool(stored.get("skipped")),
    }
    if stored.get("skipped"):
        record["filing_status"] = "skipped"
        return record
    if not file_to_job or media_type not in FILEABLE_TYPES:
        return record
    choice = choose_job_for_inbound(hint_text, wa_id)
    if choice.get("job"):
        filed = file_into_job(content, record["filename"], media_type, choice["job"]["slug"])
        record["job_slug"] = choice["job"]["slug"]
        record["filed_path"] = filed
        record["filing_status"] = "filed"
        record["filed_at"] = datetime.now(timezone.utc).isoformat()
        return record
    parked = park_in_inbox(content, record["filename"])
    record["filed_path"] = parked
    record["filing_status"] = "inbox"
    record["needs_job_ask"] = True
    return record


def get_pending_filing_state(wa_id: str) -> dict[str, Any]:
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT attachment_ids, asked_at FROM whatsapp_pending_filings WHERE wa_id = ?",
            (str(wa_id or "").strip(),),
        ).fetchone()
        if not row:
            return {"ids": [], "asked_at": ""}
        try:
            ids = json.loads(row["attachment_ids"] or "[]")
        except Exception:
            ids = []
        return {
            "ids": [int(i) for i in ids if str(i).isdigit() or isinstance(i, int)],
            "asked_at": str(row["asked_at"] or ""),
        }
    finally:
        conn.close()


def get_pending_filings(wa_id: str) -> list[int]:
    return get_pending_filing_state(wa_id)["ids"]


def set_pending_filings(wa_id: str, attachment_ids: list[int]) -> None:
    init_db()
    existing = get_pending_filings(wa_id)
    merged = sorted(set(existing + [int(i) for i in attachment_ids]))
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO whatsapp_pending_filings (wa_id, attachment_ids, asked_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                   attachment_ids=excluded.attachment_ids,
                   asked_at=excluded.asked_at""",
                (str(wa_id or "").strip(), json.dumps(merged), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()


def clear_pending_filings(wa_id: str) -> None:
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM whatsapp_pending_filings WHERE wa_id = ?", (str(wa_id or "").strip(),))
            conn.commit()
        finally:
            conn.close()


def get_attachment(attachment_id: int) -> Optional[dict[str, Any]]:
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM whatsapp_attachments WHERE id = ?", (attachment_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def attachment_file_path(attachment_id: int) -> Optional[Path]:
    att = get_attachment(attachment_id)
    if not att:
        return None
    for key in ("local_path", "filed_path"):
        raw = att.get(key) or ""
        if raw and Path(raw).is_file() and _path_is_allowed(Path(raw)):
            return Path(raw)
    return None


def _path_is_allowed(path: Path) -> bool:
    resolved = path.resolve()
    allowed = [media_dir().resolve(), inbox_dir().resolve(), jobs_root().resolve()]
    return any(resolved == root or root in resolved.parents for root in allowed)


def refile_attachment(attachment_id: int, job_slug: str) -> dict[str, Any]:
    """Move a parked or filed attachment into a job folder. Founder write."""
    slug = slug_ok(job_slug)
    if not slug:
        raise ValueError("job folder does not exist under this edition's jobs root")
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT * FROM whatsapp_attachments WHERE id = ?", (attachment_id,)).fetchone()
            if not row:
                raise ValueError(f"Attachment {attachment_id} not found")
            att = dict(row)
            source = att.get("local_path") or att.get("filed_path")
            if not source or not Path(source).is_file():
                raise FileNotFoundError("attachment bytes are not on disk")
            content = Path(source).read_bytes()
            new_path = file_into_job(content, att.get("filename") or "file", att.get("media_type") or "document", slug)
            old_filed = att.get("filed_path") or ""
            try:
                if old_filed and str(inbox_dir()) in old_filed:
                    Path(old_filed).unlink(missing_ok=True)
            except Exception:
                pass
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """UPDATE whatsapp_attachments
                   SET job_slug = ?, filed_path = ?, filed_at = ?, filing_status = ?
                   WHERE id = ?""",
                (slug, new_path, now_str, "filed", attachment_id),
            )
            conn.commit()
            msg = conn.execute(
                "SELECT wa_id FROM whatsapp_messages WHERE id = ?",
                (att["message_id"],),
            ).fetchone()
        finally:
            conn.close()
    if msg and msg["wa_id"]:
        set_active_job(msg["wa_id"], slug, folder_path=str(jobs_root() / slug))
        remaining = [i for i in get_pending_filings(msg["wa_id"]) if i != attachment_id]
        _replace_pending(msg["wa_id"], remaining)
    return {"ok": True, "attachment_id": attachment_id, "job_slug": slug, "filed_path": new_path}


def _replace_pending(wa_id: str, attachment_ids: list[int]) -> None:
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            if attachment_ids:
                conn.execute(
                    """INSERT INTO whatsapp_pending_filings (wa_id, attachment_ids, asked_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(wa_id) DO UPDATE SET attachment_ids=excluded.attachment_ids""",
                    (str(wa_id).strip(), json.dumps(attachment_ids), datetime.now(timezone.utc).isoformat()),
                )
            else:
                conn.execute("DELETE FROM whatsapp_pending_filings WHERE wa_id = ?", (str(wa_id).strip(),))
            conn.commit()
        finally:
            conn.close()


def slug_ok(job_slug: str) -> str:
    """Sanitized slug that already exists as a folder under this edition's jobs root."""
    return existing_job_slug(job_slug)


def _pending_ask_expired(asked_at: str) -> bool:
    if not asked_at:
        return False
    try:
        parsed = datetime.fromisoformat(str(asked_at).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
        return age.total_seconds() > get_job_answer_timeout()
    except ValueError:
        return False


def consume_job_answer(wa_id: str, text: str) -> Optional[dict[str, Any]]:
    """Consume a parked-file reply only when it clearly names one job, or skip/timeout."""
    state = get_pending_filing_state(wa_id)
    pending = state.get("ids") or []
    if not pending:
        return None
    if _pending_ask_expired(state.get("asked_at") or ""):
        clear_pending_filings(wa_id)
        return None
    stripped = (text or "").strip().lower().rstrip(".!")
    if stripped in JOB_SKIP_WORDS:
        clear_pending_filings(wa_id)
        return {
            "handled": True,
            "status": "skipped",
            "reply": "Left in the inbox. Say the job name later or move it from WhatsApp Chats.",
        }
    probed = probe_job_text(text)
    if probed.get("status") == "unique":
        match = probed["match"]
        results = []
        named = (jobs_root() / match["slug"]).resolve()
        root = jobs_root().resolve()
        if named.parent == root:
            named.mkdir(parents=True, exist_ok=True)
        for att_id in pending:
            try:
                results.append(refile_attachment(att_id, match["slug"]))
            except Exception as exc:
                logger.warning("refile on job answer failed for %s: %s", att_id, exc)
        clear_pending_filings(wa_id)
        set_active_job(wa_id, match["slug"], match.get("client_name", ""), match.get("folder_path", ""))
        return {
            "handled": True,
            "status": "filed",
            "job": match,
            "reply": f"Filed under {match.get('client_name') or match['slug']} ({match['slug']}).",
            "results": results,
        }
    return None


def note_inbox_ask(wa_id: str, attachments: list[dict]) -> bool:
    """Record parked attachments and tell the caller to have Max ask."""
    ids = [int(a["id"]) for a in attachments if a.get("id") and a.get("needs_job_ask")]
    # ids are assigned after insert — use returned lastrowids from caller
    pending_ids = [int(a["id"]) for a in attachments if a.get("id") and a.get("filing_status") == "inbox"]
    if not pending_ids:
        return False
    set_pending_filings(wa_id, pending_ids)
    return True


def last_attachment_ids(message_id: int) -> list[dict[str, Any]]:
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM whatsapp_attachments WHERE message_id = ?",
            (message_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def purge_expired_media() -> int:
    """Delete edition media older than WHATSAPP_RETENTION_DAYS. Does not touch ~/jobs."""
    days = get_retention_days()
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    removed = 0
    for folder in (media_dir(), inbox_dir()):
        try:
            for path in folder.iterdir():
                if not path.is_file():
                    continue
                try:
                    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                except OSError:
                    continue
                if mtime < cutoff:
                    path.unlink(missing_ok=True)
                    removed += 1
        except OSError:
            continue
    return removed


def conversation_copy_text(wa_id: str) -> str:
    messages, _ = get_conversation_messages(wa_id, limit=200, offset=0)
    lines = []
    for m in messages:
        who = "Max" if m.get("direction") == "outbound" else m.get("display_label") or m.get("wa_id")
        when = m.get("timestamp") or ""
        body = m.get("body") or m.get("caption") or f"[{m.get('message_type')}]"
        lines.append(f"{when} {who}: {body}")
        for att in m.get("attachments") or []:
            where = att.get("filed_path") or att.get("job_slug") or att.get("filing_status")
            extra = f" → {where}" if where else ""
            lines.append(f"  [attachment {att.get('filename')}{extra}]")
    return "\n".join(lines).strip()


def conversation_export_pdf(wa_id: str) -> bytes:
    """Printable PDF of this conversation. No client send."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    text = conversation_copy_text(wa_id) or "(empty conversation)"
    buf = io.BytesIO()
    page = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 48
    page.setFont("Helvetica-Bold", 12)
    page.drawString(48, y, f"WhatsApp chat {get_display_label(wa_id)}")
    y -= 18
    page.setFont("Helvetica", 9)
    for raw_line in text.splitlines() or [""]:
        line = sanitize_no_secrets(raw_line)[:110]
        if y < 48:
            page.showPage()
            page.setFont("Helvetica", 9)
            y = height - 48
        page.drawString(48, y, line)
        y -= 12
    page.save()
    return buf.getvalue()

