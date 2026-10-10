"""Durable per-edition WhatsApp chat log.

Stores inbound and outbound turns (text, voice-note markers/transcripts,
document-sent markers, call events) plus Cloud API delivery status.
The SQLite file lives under this edition's data_root()/whatsapp so family
editions never share Rafael's log.

Never logs access tokens, app secrets, or API keys.
Inbound media is stored under this edition's whatsapp/media (URLs expire).
Photos, PDFs, and 3D files are copied into this edition's jobs root
(<slug>/photos|received|scans) when the folder is known — a client job
or personal / insurance / store / luxeforge. Otherwise they park in
whatsapp/inbox until the sender answers. Phase 0 never writes a
LuxeForge job, lead, or estimate.
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
from app.services.max.doc_lookup import (
    existing_job_slug,
    jobs_root,
    list_job_folders,
    probe_job_text,
    resolve_job_folder,
    suggest_jobs,
)
from app.services.max.whatsapp_folders import (
    FILEABLE_MEDIA,
    append_job_record,
    consume_created_job_flag,
    ensure_reserved_folders,
    filing_subdir,
    folder_kind_for_slug,
    parse_new_job_name,
    resolve_folder,
    resolve_or_create_folder,
    safe_folder_slug,
    sounds_like_purchase,
)

logger = logging.getLogger("max.whatsapp_log")

_lock = threading.Lock()

_SECRET_ENVS = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "FOUNDER_PIN",
)

# 256 MB: Meta documents cap near 100 MB; Polycam room / USDZ / mesh
# zips commonly land 50–200 MB. 50 MB silently dropped those scans.
# Override with WHATSAPP_MAX_ATTACHMENT_SIZE_BYTES.
DEFAULT_MAX_ATTACHMENT_SIZE = 256 * 1024 * 1024
DEFAULT_RETENTION_DAYS = 365
DEFAULT_JOB_ANSWER_TIMEOUT = 1800
DEFAULT_PHOTO_BATCH_SECONDS = 120
DEFAULT_JOB_HINT_SECONDS = 600
JOB_ASK_TEXT = (
    "Which folder should I file this under? Reply with the client name, "
    "nickname, job address, quote number, or personal / insurance / store / "
    "luxeforge. I will not guess. Reply skip to leave it in the inbox."
)
JOB_SKIP_WORDS = {"skip", "cancel"}
CHAT_NOT_JOB_RE = re.compile(
    r"(?:"
    r"^you online\b|"
    r"^are you\b|"
    r"\bvetting\b|"
    r"\b(?:did you|do you) get my (?:pictures?|photos?)\b|"
    r"^hello\b|^hi\b|^hey\b|"
    r"^thanks\b|^thank you\b|"
    r"^next \d+ months?\b|"
    r"\bneed to buy\b|\bhave to buy\b|\bwant to buy\b|\bbuy a\b|"
    r"^ok\b|^okay\b|^yes\b|^no\b|^yep\b|^nope\b|"
    r"^\[voice|"
    r"^\[photo"
    r")",
    re.IGNORECASE,
)
PHOTO_STATUS_ASK_RE = re.compile(
    r"\b(?:vetting my (?:pictures?|photos?)|"
    r"(?:did you|do you) get my (?:pictures?|photos?)|"
    r"got my (?:pictures?|photos?)|"
    r"see my (?:pictures?|photos?)|"
    r"received my (?:pictures?|photos?))\b",
    re.IGNORECASE,
)
QUOTE_ASK_RE = re.compile(
    r"\b(quote|quotes|estimate|estimates|price|pricing|cost|costs|"
    r"cotizaci[oó]n|cotizacion|presupuesto|presupuestos|how\s+much)\b",
    re.IGNORECASE,
)
FILEABLE_TYPES = set(FILEABLE_MEDIA)
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


def photo_batch_window_seconds() -> float:
    try:
        val = os.getenv("WHATSAPP_PHOTO_BATCH_SECONDS")
        if val is not None and str(val).strip() != "":
            return max(0.0, float(val))
    except Exception:
        pass
    return float(DEFAULT_PHOTO_BATCH_SECONDS)


def job_hint_window_seconds() -> float:
    try:
        val = os.getenv("WHATSAPP_JOB_HINT_SECONDS")
        if val is not None and str(val).strip() != "":
            return max(60.0, float(val))
    except Exception:
        pass
    return float(DEFAULT_JOB_HINT_SECONDS)


def wants_photo_quote(*texts: str) -> bool:
    """True only when THIS photo's caption/body asks to price/quote.

    Pass only the same message's caption (or that message's own text).
    Never pass nearby turns, album siblings, or combined_job_hint — those
    would turn a later album of photos into drafts.
    """
    blob = " ".join(str(t or "") for t in texts)
    return bool(QUOTE_ASK_RE.search(blob))


def format_job_ask(*, matches: Optional[list] = None, hint: str = "", count: int = 0) -> str:
    """One-line ask. Do not dump closest client names for a purchase or unknown batch."""
    n = int(count or 0)
    noun = "photo" if n == 1 else "photos"
    prefix = f"Got {n} {noun}. " if n else ""
    if sounds_like_purchase(hint):
        return f"{prefix}Personal or store folder?".strip()
    if n:
        return (
            f"{prefix}Which job? "
            "(reply with the name, personal, insurance, store, or skip)"
        )
    names = []
    for row in matches or suggest_jobs(hint):
        label = str(row.get("client_name") or row.get("slug") or "").strip()
        if label and label not in names:
            names.append(label)
    if names:
        listed = ", ".join(names[:5])
        return (
            f"I don't have a unique job for that. Closest: {listed}. "
            "Reply with the client name, nickname, address, quote number, "
            "or personal / insurance / store / luxeforge, or skip."
        )
    return JOB_ASK_TEXT


def is_chat_not_job(text: str) -> bool:
    blob = " ".join(str(text or "").split()).strip()
    if not blob:
        return True
    if parse_new_job_name(blob):
        return False
    if resolve_folder(blob):
        return False
    if "?" in blob:
        return True
    return bool(CHAT_NOT_JOB_RE.search(blob))


def is_job_hint_text(text: str) -> bool:
    """True only for captions/texts that can name a folder. Chat and questions are out."""
    blob = " ".join(str(text or "").split()).strip()
    if not blob or is_chat_not_job(blob):
        return False
    if parse_new_job_name(blob):
        return True
    if resolve_folder(blob):
        return True
    probed = probe_job_text(blob)
    if probed.get("status") in {"unique", "ambiguous"}:
        return True
    words = [w for w in re.findall(r"[a-zA-Z0-9']+", blob) if len(w) > 1]
    return len(words) >= 2


def isolate_job_hints(text: str) -> list[str]:
    """Pull only the job-naming fragments out of a mixed blob."""
    found: list[str] = []
    named = parse_new_job_name(text)
    if named:
        found.append(f"New job {named}")
    blob = " ".join(str(text or "").split()).strip().rstrip(".!?")
    if (
        blob
        and "?" not in blob
        and not CHAT_NOT_JOB_RE.search(blob)
        and is_job_hint_text(blob)
        and blob not in found
    ):
        found.append(blob)
    return found


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_media_batches (
                    wa_id TEXT PRIMARY KEY,
                    attachment_ids TEXT NOT NULL,
                    last_at TEXT NOT NULL,
                    hint_text TEXT DEFAULT '',
                    asked INTEGER DEFAULT 0,
                    asked_at TEXT DEFAULT '',
                    quoted INTEGER DEFAULT 0
                )
                """
            )
            _ensure_batch_columns(conn)
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
    mime_type: str = "",
) -> str:
    """Copy into <jobs-root>/<slug>/photos|received|scans. Never overwrites.

    Slug is validated here (not only in callers): a single safe path
    segment whose resolved path stays under this edition's jobs root.
    """
    slug = safe_folder_slug(job_slug)
    ensure_reserved_folders()
    sub = filing_subdir(media_type, filename, mime_type)
    dest = unique_dest(jobs_root() / slug / sub, filename)
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
    """Named unique client, reserved folder, or 'new job <name>'.

    Does not use a sticky job from an old conversation. An open photo
    batch may hold a resolved slug for later photos in the same window.
    """
    match = resolve_or_create_folder(text) if is_job_hint_text(text) or parse_new_job_name(text or "") else None
    if match:
        set_active_job(wa_id, match["slug"], match.get("client_name", ""), match.get("folder_path", ""))
        return {"status": "unique", "job": match}
    held = batch_resolved_job(wa_id)
    if held and (held.get("slug") and (text or "").strip() == ""):
        return {"status": "unique", "job": held}
    probed = probe_job_text(text)
    if probed.get("status") == "ambiguous":
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
        slug = choice["job"]["slug"]
        filed = file_into_job(
            content, record["filename"], media_type, slug, mime_type=mime_type,
        )
        record["job_slug"] = slug
        record["folder_kind"] = folder_kind_for_slug(slug)
        record["filed_path"] = filed
        record["filing_status"] = "filed"
        record["filed_at"] = datetime.now(timezone.utc).isoformat()
        append_job_record(slug, record, content=content)
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


def set_pending_filings(wa_id: str, attachment_ids: list[int], *, mark_asked: bool = False) -> None:
    """Park attachment ids. asked_at is set only when an ask was actually sent."""
    init_db()
    state = get_pending_filing_state(wa_id)
    merged = sorted(set(list(state.get("ids") or []) + [int(i) for i in attachment_ids]))
    asked_at = datetime.now(timezone.utc).isoformat() if mark_asked else (state.get("asked_at") or "")
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO whatsapp_pending_filings (wa_id, attachment_ids, asked_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                   attachment_ids=excluded.attachment_ids,
                   asked_at=excluded.asked_at""",
                (str(wa_id or "").strip(), json.dumps(merged), asked_at),
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
            new_path = file_into_job(
                content,
                att.get("filename") or "file",
                att.get("media_type") or "document",
                slug,
                mime_type=str(att.get("mime_type") or ""),
            )
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
    filed = {
        "ok": True,
        "attachment_id": attachment_id,
        "job_slug": slug,
        "folder_kind": folder_kind_for_slug(slug),
        "filed_path": new_path,
        "filename": att.get("filename") or "file",
        "media_type": att.get("media_type") or "document",
        "whatsapp_attachment_id": attachment_id,
    }
    append_job_record(slug, filed, content=content)
    return filed


def _replace_pending(wa_id: str, attachment_ids: list[int]) -> None:
    init_db()
    asked_at = get_pending_filing_state(wa_id).get("asked_at") or ""
    with _lock:
        conn = _get_conn()
        try:
            if attachment_ids:
                conn.execute(
                    """INSERT INTO whatsapp_pending_filings (wa_id, attachment_ids, asked_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(wa_id) DO UPDATE SET attachment_ids=excluded.attachment_ids""",
                    (str(wa_id).strip(), json.dumps(attachment_ids), asked_at),
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
    """True when a real ask timestamp is older than the job-answer window.

    Empty asked_at means no ask was sent — that is not an open question.
    Callers must not treat an empty stamp as a pending ask.
    """
    if not asked_at:
        return False
    age = _iso_age_seconds(asked_at)
    if age is None:
        return True
    return age > get_job_answer_timeout()


def _iso_age_seconds(stamp: str) -> Optional[float]:
    try:
        parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
    except ValueError:
        return None


def _ensure_batch_columns(conn: sqlite3.Connection) -> None:
    cols = {str(row[1]) for row in conn.execute("PRAGMA table_info(whatsapp_media_batches)").fetchall()}
    if "asked_at" not in cols:
        conn.execute("ALTER TABLE whatsapp_media_batches ADD COLUMN asked_at TEXT DEFAULT ''")
    if "quoted" not in cols:
        conn.execute("ALTER TABLE whatsapp_media_batches ADD COLUMN quoted INTEGER DEFAULT 0")
    if "resolved_slug" not in cols:
        conn.execute("ALTER TABLE whatsapp_media_batches ADD COLUMN resolved_slug TEXT DEFAULT ''")
    if "resolved_name" not in cols:
        conn.execute("ALTER TABLE whatsapp_media_batches ADD COLUMN resolved_name TEXT DEFAULT ''")
    if "created_job" not in cols:
        conn.execute("ALTER TABLE whatsapp_media_batches ADD COLUMN created_job INTEGER DEFAULT 0")


def _batch_row_expired(last_at: str, asked: int, asked_at: str) -> bool:
    if int(asked or 0):
        stamp = asked_at or last_at
        if not stamp:
            return True
        age = _iso_age_seconds(stamp)
        return age is None or age > get_job_answer_timeout()
    age = _iso_age_seconds(last_at)
    if age is None:
        return True
    return age > max(photo_batch_window_seconds(), 1.0)


def recent_inbound_texts(
    wa_id: str,
    *,
    seconds: Optional[float] = None,
    job_hints_only: bool = True,
) -> list[str]:
    """Inbound captions/bodies from this sender in the photo-batch window.

    Default: only texts that can name a job. Chat and questions are dropped.
    """
    window = photo_batch_window_seconds() if seconds is None else seconds
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max(0.0, window if window > 0 else 1.0))
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT body, caption, timestamp, message_type
            FROM whatsapp_messages
            WHERE wa_id = ? AND direction = 'inbound'
            ORDER BY timestamp DESC, id DESC
            LIMIT 40
            """,
            (str(wa_id or "").strip(),),
        ).fetchall()
    finally:
        conn.close()
    found: list[str] = []
    for row in rows:
        ts = iso_from_wa_timestamp(row["timestamp"])
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < cutoff:
                continue
        except ValueError:
            continue
        parts = [row["caption"], row["body"]]
        if str(row["message_type"] or "") in {"image", "photo", "document", "scan"}:
            # Photo captions are first-class hints unless they are chat.
            pass
        for part in parts:
            text = str(part or "").strip()
            if not text or text in found:
                continue
            if job_hints_only and not is_job_hint_text(text):
                continue
            found.append(text)
    return found


def combined_job_hint(wa_id: str, *extra: str) -> str:
    parts: list[str] = []
    for raw in extra:
        for text in isolate_job_hints(raw):
            if text not in parts:
                parts.append(text)
    for text in recent_inbound_texts(wa_id):
        for piece in isolate_job_hints(text):
            if piece not in parts:
                parts.append(piece)
    return " ".join(parts)


def expire_stale_batches(wa_id: Optional[str] = None) -> int:
    """Drop stale photo-batch rows from SQLite. Survives process restart.

    The in-memory flush task is not the source of truth. last_at / asked_at
    are checked on every load so a restarted worker still expires old rows.
    """
    init_db()
    removed = 0
    with _lock:
        conn = _get_conn()
        try:
            _ensure_batch_columns(conn)
            if wa_id:
                rows = conn.execute(
                    "SELECT wa_id, last_at, asked, asked_at FROM whatsapp_media_batches WHERE wa_id = ?",
                    (str(wa_id).strip(),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT wa_id, last_at, asked, asked_at FROM whatsapp_media_batches"
                ).fetchall()
            for row in rows:
                asked = int(row["asked"] or 0)
                asked_at = str(row["asked_at"] or "")
                if not _batch_row_expired(str(row["last_at"] or ""), asked, asked_at):
                    continue
                conn.execute("DELETE FROM whatsapp_media_batches WHERE wa_id = ?", (row["wa_id"],))
                if asked or asked_at:
                    conn.execute("DELETE FROM whatsapp_pending_filings WHERE wa_id = ?", (row["wa_id"],))
                removed += 1
            conn.commit()
        finally:
            conn.close()
    return removed


def _empty_batch() -> dict[str, Any]:
    return {
        "ids": [],
        "last_at": "",
        "hint_text": "",
        "asked": 0,
        "asked_at": "",
        "quoted": 0,
        "resolved_slug": "",
        "resolved_name": "",
        "created_job": 0,
    }


def _load_batch(wa_id: str) -> dict[str, Any]:
    """Load the open photo batch for this sender.

    Single-worker assumption: WhatsApp inbound, `_schedule_batch_flush`,
    and this SQLite row are safe only with one process writing
    `whatsapp_media_batches`. A second worker would race on last_at/asked
    and could send a second ask. Expiry is stored on the row (last_at /
    asked_at) so a restart still drops stale batches; the in-memory flush
    task is not the source of truth.
    """
    expire_stale_batches(wa_id)
    init_db()
    conn = _get_conn()
    try:
        _ensure_batch_columns(conn)
        row = conn.execute(
            """SELECT wa_id, attachment_ids, last_at, hint_text, asked, asked_at, quoted,
                      resolved_slug, resolved_name, created_job
               FROM whatsapp_media_batches WHERE wa_id = ?""",
            (str(wa_id or "").strip(),),
        ).fetchone()
        if not row:
            return _empty_batch()
        try:
            ids = json.loads(row["attachment_ids"] or "[]")
        except Exception:
            ids = []
        return {
            "ids": [int(i) for i in ids if str(i).isdigit() or isinstance(i, int)],
            "last_at": str(row["last_at"] or ""),
            "hint_text": str(row["hint_text"] or ""),
            "asked": int(row["asked"] or 0),
            "asked_at": str(row["asked_at"] or ""),
            "quoted": int(row["quoted"] or 0),
            "resolved_slug": str(row["resolved_slug"] or ""),
            "resolved_name": str(row["resolved_name"] or ""),
            "created_job": int(row["created_job"] or 0),
        }
    finally:
        conn.close()


def photo_batch_quoted(wa_id: str) -> bool:
    return int(_load_batch(wa_id).get("quoted") or 0) == 1


def mark_photo_batch_quoted(wa_id: str) -> None:
    """Cap photo-to-quote at one draft for the open batch."""
    existing = _load_batch(wa_id)
    now = datetime.now(timezone.utc).isoformat()
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            _ensure_batch_columns(conn)
            conn.execute(
                """INSERT INTO whatsapp_media_batches
                   (wa_id, attachment_ids, last_at, hint_text, asked, asked_at, quoted,
                    resolved_slug, resolved_name, created_job)
                   VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET quoted=1""",
                (
                    str(wa_id or "").strip(),
                    json.dumps(existing.get("ids") or []),
                    existing.get("last_at") or now,
                    existing.get("hint_text") or "",
                    int(existing.get("asked") or 0),
                    existing.get("asked_at") or "",
                    existing.get("resolved_slug") or "",
                    existing.get("resolved_name") or "",
                    int(existing.get("created_job") or 0),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def record_media_batch(wa_id: str, attachment_ids: list[int], hint_text: str = "") -> None:
    """Add fileable items to the open batch (same sender, within the batch window)."""
    if not attachment_ids:
        return
    now = datetime.now(timezone.utc)
    existing = _load_batch(wa_id)
    keep = False
    if existing.get("last_at"):
        age = _iso_age_seconds(str(existing["last_at"]))
        window = max(photo_batch_window_seconds(), 1.0)
        keep = age is not None and age <= window
    ids = list(existing["ids"]) if keep else []
    for att_id in attachment_ids:
        if int(att_id) not in ids:
            ids.append(int(att_id))
    hint = existing["hint_text"] if keep else ""
    for piece in isolate_job_hints(hint_text):
        if piece and piece not in hint:
            hint = f"{hint} {piece}".strip()
    quoted = int(existing.get("quoted") or 0) if keep else 0
    resolved_slug = existing.get("resolved_slug") or "" if keep else ""
    resolved_name = existing.get("resolved_name") or "" if keep else ""
    created_job = int(existing.get("created_job") or 0) if keep else 0
    if hint:
        named = resolve_or_create_folder(hint)
        if named:
            resolved_slug = named["slug"]
            resolved_name = named.get("client_name") or named["slug"]
            created_job = 1 if named.get("created") or created_job else 0
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            _ensure_batch_columns(conn)
            conn.execute(
                """INSERT INTO whatsapp_media_batches
                   (wa_id, attachment_ids, last_at, hint_text, asked, asked_at, quoted,
                    resolved_slug, resolved_name, created_job)
                   VALUES (?, ?, ?, ?, 0, '', ?, ?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                   attachment_ids=excluded.attachment_ids,
                   last_at=excluded.last_at,
                   hint_text=excluded.hint_text,
                   asked=0,
                   asked_at='',
                   quoted=excluded.quoted,
                   resolved_slug=excluded.resolved_slug,
                   resolved_name=excluded.resolved_name,
                   created_job=excluded.created_job""",
                (
                    str(wa_id or "").strip(),
                    json.dumps(ids),
                    now.isoformat(),
                    hint,
                    quoted,
                    resolved_slug,
                    resolved_name,
                    created_job,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def remember_batch_job(
    wa_id: str,
    slug: str,
    name: str = "",
    *,
    created: bool = False,
) -> None:
    existing = _load_batch(wa_id)
    now = datetime.now(timezone.utc).isoformat()
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            _ensure_batch_columns(conn)
            conn.execute(
                """INSERT INTO whatsapp_media_batches
                   (wa_id, attachment_ids, last_at, hint_text, asked, asked_at, quoted,
                    resolved_slug, resolved_name, created_job)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                   resolved_slug=excluded.resolved_slug,
                   resolved_name=excluded.resolved_name,
                   created_job=MAX(whatsapp_media_batches.created_job, excluded.created_job),
                   last_at=excluded.last_at""",
                (
                    str(wa_id or "").strip(),
                    json.dumps(existing.get("ids") or []),
                    existing.get("last_at") or now,
                    existing.get("hint_text") or "",
                    int(existing.get("asked") or 0),
                    existing.get("asked_at") or "",
                    int(existing.get("quoted") or 0),
                    slug,
                    name or slug,
                    1 if created else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def batch_resolved_job(wa_id: str) -> Optional[dict[str, Any]]:
    batch = _load_batch(wa_id)
    slug = str(batch.get("resolved_slug") or "").strip()
    if not slug:
        return None
    return {
        "slug": slug,
        "client_name": batch.get("resolved_name") or slug,
        "folder_path": str(jobs_root() / slug),
        "kind": folder_kind_for_slug(slug),
        "created": bool(int(batch.get("created_job") or 0)),
        "match_reason": "batch resolved job",
    }


def clear_media_batch(wa_id: str) -> None:
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM whatsapp_media_batches WHERE wa_id = ?", (str(wa_id or "").strip(),))
            conn.commit()
        finally:
            conn.close()


def _file_pending_ids(wa_id: str, match: dict[str, Any], pending: list[int]) -> list[dict[str, Any]]:
    results = []
    named = (jobs_root() / match["slug"]).resolve()
    root = jobs_root().resolve()
    if named.parent == root:
        named.mkdir(parents=True, exist_ok=True)
    for att_id in pending:
        try:
            existing = get_attachment(att_id) or {}
            if (
                existing.get("job_slug") == match["slug"]
                and existing.get("filing_status") == "filed"
                and existing.get("filed_path")
            ):
                results.append({
                    "ok": True,
                    "attachment_id": att_id,
                    "job_slug": match["slug"],
                    "filed_path": existing.get("filed_path"),
                    "already_filed": True,
                })
                continue
            results.append(refile_attachment(att_id, match["slug"]))
        except Exception as exc:
            logger.warning("refile on job answer failed for %s: %s", att_id, exc)
    return results


def _filed_confirmation(count: int, match: dict[str, Any], *, created: bool = False) -> str:
    name = match.get("client_name") or match.get("slug") or "the job"
    noun = "photo" if count == 1 else "photos"
    if created or match.get("created"):
        return f"Created job {name} and filed {count} {noun}"
    return f"Got {count} {noun}. Filed under {name}."


def finalize_photo_batch(wa_id: str, *, hint_text: str = "", force_ask: bool = False) -> Optional[dict[str, Any]]:
    """One confirmation or one ask for the open photo batch. Never silent when there are photos."""
    batch = _load_batch(wa_id)
    pending_ids = list(get_pending_filings(wa_id))
    ids = list(dict.fromkeys((batch.get("ids") or []) + pending_ids))
    if not ids and not force_ask:
        return None
    hint = combined_job_hint(wa_id, hint_text, batch.get("hint_text") or "")
    match = resolve_or_create_folder(hint) if hint else None
    if not match:
        match = batch_resolved_job(wa_id)
    if match:
        results = _file_pending_ids(wa_id, match, ids)
        created = bool(
            match.get("created")
            or int(batch.get("created_job") or 0)
            or consume_created_job_flag(match.get("slug") or "")
        )
        remember_batch_job(wa_id, match["slug"], match.get("client_name", ""), created=created)
        clear_pending_filings(wa_id)
        _keep_resolved_batch(wa_id, match, created=False)
        set_active_job(wa_id, match["slug"], match.get("client_name", ""), match.get("folder_path", ""))
        filed_n = len(results) or len(ids)
        return {
            "handled": True,
            "status": "filed",
            "job": match,
            "reply": _filed_confirmation(filed_n, match, created=created),
            "results": results,
        }
    if batch.get("asked") and not force_ask:
        return None
    purchase = sounds_like_purchase(hint) or any(
        sounds_like_purchase(t)
        for t in recent_inbound_texts(wa_id, job_hints_only=False)
    )
    ask = format_job_ask(
        matches=probe_job_text(hint).get("matches") or suggest_jobs(hint),
        hint="need to buy a case" if purchase else hint,
        count=len(ids),
    )
    if ids:
        set_pending_filings(wa_id, ids, mark_asked=True)
    asked_at = datetime.now(timezone.utc).isoformat()
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            _ensure_batch_columns(conn)
            conn.execute(
                "UPDATE whatsapp_media_batches SET asked = 1, asked_at = ? WHERE wa_id = ?",
                (asked_at, str(wa_id or "").strip()),
            )
            conn.commit()
        finally:
            conn.close()
    return {"handled": True, "status": "need_job", "reply": ask, "matches": suggest_jobs(hint)}


def _keep_resolved_batch(wa_id: str, match: dict[str, Any], *, created: bool = False) -> None:
    """Clear filed ids but keep the resolved slug for later photos in the window."""
    now = datetime.now(timezone.utc).isoformat()
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            _ensure_batch_columns(conn)
            conn.execute(
                """INSERT INTO whatsapp_media_batches
                   (wa_id, attachment_ids, last_at, hint_text, asked, asked_at, quoted,
                    resolved_slug, resolved_name, created_job)
                   VALUES (?, '[]', ?, ?, 0, '', 0, ?, ?, ?)
                   ON CONFLICT(wa_id) DO UPDATE SET
                   attachment_ids='[]',
                   last_at=excluded.last_at,
                   hint_text=excluded.hint_text,
                   asked=0,
                   asked_at='',
                   resolved_slug=excluded.resolved_slug,
                   resolved_name=excluded.resolved_name,
                   created_job=excluded.created_job""",
                (
                    str(wa_id or "").strip(),
                    now,
                    match.get("client_name") or match.get("slug") or "",
                    match.get("slug") or "",
                    match.get("client_name") or match.get("slug") or "",
                    1 if created else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def consume_job_answer(wa_id: str, text: str) -> Optional[dict[str, Any]]:
    """Consume text only when a real ask was sent. Unresolved text falls through.

    A real ask is batch.asked==1 or a pending filing with asked_at set.
    Open photo batches without an ask are file state, not a pending question —
    'hello' / 'what's on my schedule today?' must reach Max chat.
    """
    state = get_pending_filing_state(wa_id)
    batch = _load_batch(wa_id)
    asked = bool(int(batch.get("asked") or 0)) or bool(state.get("asked_at"))
    if not asked:
        return None
    pending = list(state.get("ids") or []) or list(batch.get("ids") or [])
    if not pending:
        return None
    ask_stamp = state.get("asked_at") or batch.get("asked_at") or ""
    if _pending_ask_expired(ask_stamp) or (
        not ask_stamp and _batch_row_expired(batch.get("last_at") or "", 1, "")
    ):
        clear_pending_filings(wa_id)
        clear_media_batch(wa_id)
        return None
    stripped = (text or "").strip().lower().rstrip(".!")
    if stripped in JOB_SKIP_WORDS:
        clear_pending_filings(wa_id)
        clear_media_batch(wa_id)
        return {
            "handled": True,
            "status": "skipped",
            "reply": "Left in the inbox. Say the job name later or move it from WhatsApp Chats.",
        }
    match = resolve_or_create_folder(text)
    if match:
        results = _file_pending_ids(wa_id, match, pending)
        clear_pending_filings(wa_id)
        clear_media_batch(wa_id)
        set_active_job(wa_id, match["slug"], match.get("client_name", ""), match.get("folder_path", ""))
        return {
            "handled": True,
            "status": "filed",
            "job": match,
            "reply": _filed_confirmation(
                len(results) or len(pending), match, created=bool(match.get("created")),
            ),
            "results": results,
        }
    return None



def photo_filing_status(wa_id: str) -> dict[str, Any]:
    """Inbox / open-batch / recently filed photos for this sender."""
    pending = list(get_pending_filings(wa_id))
    batch = _load_batch(wa_id)
    waiting = list(dict.fromkeys(pending + list(batch.get("ids") or [])))
    filed: list[dict[str, Any]] = []
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT a.id, a.filename, a.job_slug, a.filing_status, a.filed_path, m.timestamp
            FROM whatsapp_attachments a
            JOIN whatsapp_messages m ON m.id = a.message_id
            WHERE m.wa_id = ? AND a.media_type IN ('image', 'photo', 'document', 'scan', 'model')
            ORDER BY m.timestamp DESC, a.id DESC
            LIMIT 40
            """,
            (str(wa_id or "").strip(),),
        ).fetchall()
    finally:
        conn.close()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    for row in rows:
        status = str(row["filing_status"] or "")
        if status == "inbox" and int(row["id"]) not in waiting:
            waiting.append(int(row["id"]))
        if status != "filed":
            continue
        try:
            parsed = datetime.fromisoformat(str(row["timestamp"] or "").replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < cutoff:
                continue
        except ValueError:
            continue
        filed.append({
            "id": row["id"],
            "job_slug": row["job_slug"] or batch.get("resolved_slug") or "",
            "filename": row["filename"],
        })
    slug = (filed[0]["job_slug"] if filed else "") or batch.get("resolved_slug") or ""
    name = batch.get("resolved_name") or (slug.replace("-", " ").title() if slug else "")
    return {
        "waiting": len(waiting),
        "waiting_ids": waiting,
        "filed_count": len(filed),
        "filed_slug": slug,
        "filed_name": name,
    }


def parked_photos_note(wa_id: str) -> str:
    if not wa_id:
        return ""
    status = photo_filing_status(wa_id)
    if status["waiting"]:
        n = status["waiting"]
        noun = "photo" if n == 1 else "photos"
        return (
            f"{n} {noun} from the user are waiting to be filed; "
            "ask which job if relevant."
        )
    if status["filed_count"] and status["filed_name"]:
        n = status["filed_count"]
        noun = "photo" if n == 1 else "photos"
        return f"{n} {noun} from the user were filed under {status['filed_name']}."
    return ""


def photo_status_reply(wa_id: str, text: str) -> Optional[str]:
    """Truthful one-liner for 'did you get my photos' / 'are you vetting my pictures'."""
    if not PHOTO_STATUS_ASK_RE.search(str(text or "")):
        return None
    status = photo_filing_status(wa_id)
    waiting = status["waiting"]
    filed = status["filed_count"]
    total = waiting + filed
    if total <= 0:
        return "I don't have any photos from you waiting right now."
    noun = "photo" if total == 1 else "photos"
    if waiting and not filed:
        return (
            f"Yes — I received {total} {noun}. They're waiting for a job name "
            "(reply with the name, personal, insurance, store, or skip)."
        )
    if filed and not waiting:
        where = status["filed_name"] or status["filed_slug"] or "the job"
        return f"Yes — I received {total} {noun}. Filed under {where}."
    where = status["filed_name"] or status["filed_slug"] or "a job"
    return (
        f"Yes — I received {total} {noun}. {filed} filed under {where}, "
        f"{waiting} still waiting for a job name."
    )


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

