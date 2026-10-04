"""MAX session journal — full, append-only record of every Max turn.

Added 2026-10-04 (max-sessions). Why a separate store:

  * ``unified_messages`` keeps text, but tool results are reduced to
    ``{tool, success}`` (no error, no summary), many early-return paths
    in /max/chat and /max/chat/stream never write to it (guardrail
    refusals, link intelligence, direct routes, GPU guard, "what's new",
    inventory clarification, IMAGE_NOT_AVAILABLE), and an image is only a
    filename that points into an upload folder that can be renamed or
    deleted (``/files/delete``).
  * ``chat_session_turns`` is pruned to the last 10 turns per conversation.
  * ``data/chats/founder/*.json`` is overwritten by the portal auto-save
    and never carried the image.

This journal records, for studio chat (/max/chat, /max/chat/stream),
Telegram (in-process ``_chat_with_max_service``) and live voice:
user text, Max's reply as shown, tool calls with a short result summary
and error, timestamps (UTC + America/New_York date), channel, model,
and a *copy* of every image/file the founder sent (content-addressed
under ``<data_root>/max-sessions-archive/attachments``).

Writes are best-effort: a journal failure never breaks a chat turn.
Family editions run their own checkouts with their own EMPIRE_DATA_DIR;
rows are also stamped with ``edition`` and the exporter only reads
``edition='main'``.

Under pytest the journal is OFF unless ``EMPIRE_MAX_JOURNAL_DB`` points
at a test database, so test traffic never lands in Rafael's log.
"""
from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

logger = logging.getLogger("max.session_journal")

LOCAL_TZ_NAME = "America/New_York"
SECRET_KEY_RE = re.compile(r"(pin|password|passwd|secret|token|api[_-]?key|authorization|cookie)", re.I)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif", ".bmp", ".svg"}


# ── paths ────────────────────────────────────────────────────────────────
def _data_root() -> Path:
    try:
        from app.services.data_paths import data_root
        return Path(data_root())
    except Exception:
        return Path(os.getenv("EMPIRE_DATA_DIR", Path.home() / "empire-data"))


def journal_db_path() -> Path:
    explicit = os.getenv("EMPIRE_MAX_JOURNAL_DB")
    if explicit:
        return Path(explicit)
    return _data_root() / "brain" / "max_session_journal.db"


def archive_root() -> Path:
    explicit = os.getenv("EMPIRE_MAX_JOURNAL_ARCHIVE")
    if explicit:
        return Path(explicit)
    return journal_db_path().parent.parent / "max-sessions-archive" / "attachments"


def edition() -> str:
    return (os.getenv("EMPIRE_EDITION") or "main").strip().lower() or "main"


def is_enabled() -> bool:
    if os.getenv("EMPIRE_MAX_JOURNAL_DISABLED") == "1":
        return False
    if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("EMPIRE_MAX_JOURNAL_DB"):
        return False
    return True


def _local_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(LOCAL_TZ_NAME)
    except Exception:  # pragma: no cover
        return timezone.utc


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_local_tz())


def parse_ts(value: Any) -> Optional[datetime]:
    """Parse ISO or SQLite 'YYYY-MM-DD HH:MM:SS' (naive = UTC)."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text.replace(" ", "T", 1) if "T" not in text else text)
    except Exception:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── db ───────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS max_session_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_uid TEXT NOT NULL UNIQUE,
    exchange_uid TEXT,
    conversation_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    input_channel TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    model TEXT,
    tool_calls_json TEXT NOT NULL DEFAULT '[]',
    attachments_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'ok',
    endpoint TEXT,
    latency_ms INTEGER,
    edition TEXT NOT NULL DEFAULT 'main',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    local_date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mst_conv ON max_session_turns(conversation_id, id);
CREATE INDEX IF NOT EXISTS idx_mst_date ON max_session_turns(local_date, edition);
"""

_initialized: set[str] = set()


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else journal_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    key = str(path)
    if key not in _initialized:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        conn.commit()
        try:  # chat contents: owner-only, like memories.db
            os.chmod(path, 0o600)
        except OSError:
            pass
        _initialized.add(key)
    return conn


# ── channel / tool / attachment helpers ──────────────────────────────────
def normalize_channel(raw: Optional[str]) -> str:
    value = (raw or "").strip().lower()
    if value in {"telegram", "telegram_bot"}:
        return "telegram"
    if value in {"voice", "voice_live", "live_voice", "phone"}:
        return "voice"
    if value == "whatsapp":
        return "whatsapp"
    return "studio"


def _redact(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "…"
    if isinstance(value, dict):
        return {k: ("[redacted]" if SECRET_KEY_RE.search(str(k)) else _redact(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, depth + 1) for v in value[:50]]
    return value


def _short(text: Any, n: int) -> str:
    s = re.sub(r"\s+", " ", str(text if text is not None else "")).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def summarize_result(result: Any, n: int = 400) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        for key in ("summary", "message", "status", "text", "answer"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                rest = [k for k in result.keys() if k != key][:6]
                return _short(f"{val}" + (f" (keys: {', '.join(map(str, rest))})" if rest else ""), n)
        return _short(json.dumps(_redact(result), default=str), n)
    if isinstance(result, list):
        head = json.dumps(_redact(result[:3]), default=str)
        return _short(f"[{len(result)} items] {head}", n)
    return _short(result, n)


def summarize_tool_call(tr: Any) -> Optional[dict]:
    if not isinstance(tr, dict):
        return None
    tool = tr.get("tool") or tr.get("name") or "unknown"
    success = tr.get("success")
    if success is None:
        success = tr.get("ok")
    error = tr.get("error")
    out: dict[str, Any] = {
        "tool": str(tool),
        "success": bool(success) if success is not None else None,
        "error": _short(error, 500) if error else None,
        "summary": summarize_result(tr.get("result") if "result" in tr else tr.get("note") or tr.get("result_preview")),
    }
    args = tr.get("args") or tr.get("arguments") or tr.get("input")
    if isinstance(args, dict) and args:
        out["args"] = _redact({k: v for k, v in args.items() if not str(k).startswith("_")})
    return out


def summarize_tool_calls(tool_results: Optional[Iterable[Any]]) -> list[dict]:
    out = []
    for tr in tool_results or []:
        s = summarize_tool_call(tr)
        if s:
            out.append(s)
    return out


def upload_candidates(filename: str) -> list[Path]:
    safe = Path(filename).name
    root = _data_root()
    home = Path.home()
    return [
        root / "uploads" / "images" / safe,
        root / "uploads" / safe,
        root / "uploads" / "documents" / safe,
        root / "uploads" / "other" / safe,
        home / "empire-repo" / "backend" / "data" / "uploads" / "images" / safe,
        home / "empire-repo" / "backend" / "data" / "uploads" / "documents" / safe,
        home / "empire-repo" / "backend" / "data" / "uploads" / "other" / safe,
        home / "empire-repo" / "backend" / "data" / "uploads" / safe,
        home / "empire-repo" / "uploads" / "images" / safe,
        Path(__file__).resolve().parents[3] / "data" / "uploads" / "images" / safe,
    ]


def resolve_upload(filename: Optional[str]) -> Optional[Path]:
    if not filename:
        return None
    direct = Path(filename)
    if direct.is_absolute() and direct.is_file():
        return direct
    return next((p for p in upload_candidates(filename) if p.is_file()), None)


def archive_attachment(filename: Optional[str], *, kind: str = "image", source: str = "upload",
                       path: Optional[Path] = None) -> Optional[dict]:
    """Copy the file into the journal archive and return an attachment record.

    The record is still returned (``archived: False``) when the file
    cannot be found, so the turn keeps the reference.
    """
    if not filename and not path:
        return None
    name = Path(str(filename or path)).name
    src = Path(path) if path else resolve_upload(filename)
    rec: dict[str, Any] = {"kind": kind, "source": source, "original_name": name, "archived": False}
    if not src or not src.is_file():
        rec["missing"] = True
        return rec
    try:
        h = hashlib.sha256()
        with open(src, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        digest = h.hexdigest()
        ext = src.suffix.lower() or ".bin"
        dest_dir = archive_root() / digest[:2]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{digest[:24]}{ext}"
        if not dest.exists():
            shutil.copy2(src, dest)
        if ext not in IMAGE_EXTS and kind == "image":
            rec["kind"] = "file"
        rec.update({
            "archived": True,
            "sha256": digest,
            "archive_path": str(dest),
            "source_path": str(src),
            "size": dest.stat().st_size,
            "mime": mimetypes.guess_type(dest.name)[0] or "application/octet-stream",
        })
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}"
        logger.warning("session_journal: archive failed for %s: %s", name, exc)
    return rec


# ── writes ───────────────────────────────────────────────────────────────
def record_turn(
    conversation_id: Optional[str],
    channel: Optional[str],
    role: str,
    content: Optional[str],
    *,
    model: Optional[str] = None,
    tool_calls: Optional[list[dict]] = None,
    attachments: Optional[list[dict]] = None,
    status: str = "ok",
    endpoint: Optional[str] = None,
    latency_ms: Optional[int] = None,
    created_at: Optional[datetime] = None,
    exchange_uid: Optional[str] = None,
    input_channel: Optional[str] = None,
    metadata: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> Optional[str]:
    if not is_enabled() and db_path is None:
        return None
    try:
        ts = created_at or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        turn_uid = uuid.uuid4().hex
        conn = _connect(db_path)
        try:
            conn.execute(
                """INSERT INTO max_session_turns
                   (turn_uid, exchange_uid, conversation_id, channel, input_channel, role, content, model,
                    tool_calls_json, attachments_json, status, endpoint, latency_ms, edition,
                    metadata_json, created_at, local_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    turn_uid, exchange_uid, conversation_id or f"anon-{turn_uid[:12]}",
                    normalize_channel(channel),
                    input_channel or channel, role, content or "", model,
                    json.dumps(tool_calls or [], default=str), json.dumps(attachments or [], default=str),
                    status, endpoint, latency_ms, edition(), json.dumps(metadata or {}, default=str),
                    ts.astimezone(timezone.utc).isoformat(), to_local(ts).date().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return turn_uid
    except Exception as exc:
        logger.warning("session_journal: record failed: %s", exc)
        return None


def record_exchange(
    *,
    conversation_id: Optional[str],
    channel: Optional[str],
    user_text: Optional[str],
    assistant_text: Optional[str],
    image_filename: Optional[str] = None,
    tool_results: Optional[list[Any]] = None,
    model: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    endpoint: Optional[str] = None,
    status: str = "ok",
    user_metadata: Optional[dict] = None,
    assistant_metadata: Optional[dict] = None,
    extra_attachments: Optional[list[dict]] = None,
) -> Optional[str]:
    """Record one user→Max exchange (two rows sharing exchange_uid)."""
    if not is_enabled():
        return None
    try:
        exchange_uid = uuid.uuid4().hex
        start = started_at or datetime.now(timezone.utc)
        end = finished_at or datetime.now(timezone.utc)
        attachments: list[dict] = []
        if image_filename:
            rec = archive_attachment(image_filename, kind="image", source=normalize_channel(channel))
            if rec:
                attachments.append(rec)
        attachments.extend(extra_attachments or [])
        latency = int((end - start).total_seconds() * 1000) if started_at else None
        record_turn(conversation_id, channel, "user", user_text, attachments=attachments, endpoint=endpoint,
                    created_at=start, exchange_uid=exchange_uid, input_channel=channel, metadata=user_metadata)
        record_turn(conversation_id, channel, "assistant", assistant_text, model=model,
                    tool_calls=summarize_tool_calls(tool_results), status=status, endpoint=endpoint,
                    latency_ms=latency, created_at=end, exchange_uid=exchange_uid, input_channel=channel,
                    metadata=assistant_metadata)
        return exchange_uid
    except Exception as exc:
        logger.warning("session_journal: exchange failed: %s", exc)
        return None


# ── SSE capture for /max/chat/stream ─────────────────────────────────────
class StreamCapture:
    """Accumulates what the founder actually saw from an SSE stream."""

    def __init__(self) -> None:
        self._buf = ""
        self.text = ""
        self.tool_results: list[dict] = []
        self.model: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self.errors: list[str] = []
        self.done = False
        self.events: dict[str, int] = {}

    def feed(self, chunk: Any) -> None:
        try:
            if isinstance(chunk, (bytes, bytearray)):
                chunk = chunk.decode("utf-8", "replace")
            self._buf += str(chunk)
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                if line.startswith("data: "):
                    self._event(line[6:])
        except Exception:  # never break the stream
            pass

    def _event(self, payload: str) -> None:
        try:
            ev = json.loads(payload)
        except Exception:
            return
        if not isinstance(ev, dict):
            return
        typ = ev.get("type") or "?"
        self.events[typ] = self.events.get(typ, 0) + 1
        if typ == "text" and ev.get("content"):
            self.text += str(ev["content"])
        elif typ == "gpu_safety_replace" and ev.get("replacement"):
            self.text = str(ev["replacement"])
        elif typ == "tool_result":
            self.tool_results.append({k: v for k, v in ev.items() if k != "type"})
        elif typ == "pin_required":
            self.tool_results.append({"tool": ev.get("tool") or "pin_required", "success": False,
                                      "error": "founder PIN required"})
        elif typ == "error":
            msg = str(ev.get("content") or "Unknown error")
            self.errors.append(msg)
            self.text += f"\n\n*Error: {msg}*"
        elif typ == "done":
            self.done = True
            self.model = ev.get("model_used") or self.model
            self.conversation_id = ev.get("conversation_id") or self.conversation_id


async def journal_stream(body_iterator, *, request: Any, endpoint: str = "/max/chat/stream",
                         started_at: Optional[datetime] = None):
    """Wrap a StreamingResponse body: pass every chunk through unchanged,
    then journal the exchange when the stream ends (or is cut off)."""
    cap = StreamCapture()
    start = started_at or datetime.now(timezone.utc)
    interrupted = True
    try:
        async for chunk in body_iterator:
            cap.feed(chunk)
            yield chunk
        interrupted = False
    finally:
        try:
            status = "ok"
            if cap.errors:
                status = "error"
            elif interrupted and not cap.done:
                status = "interrupted"
            record_exchange(
                conversation_id=cap.conversation_id or getattr(request, "conversation_id", None)
                or f"studio-{uuid.uuid4().hex[:12]}",
                channel=getattr(request, "channel", None) or "web",
                user_text=getattr(request, "message", ""),
                assistant_text=cap.text if cap.text else ("[stream ended before any reply]" if status != "ok" else ""),
                image_filename=getattr(request, "image_filename", None),
                tool_results=cap.tool_results,
                model=cap.model,
                started_at=start,
                endpoint=endpoint,
                status=status,
                user_metadata={"desk": getattr(request, "desk", None), "raw_channel": getattr(request, "channel", None)},
                assistant_metadata={"events": cap.events, "errors": cap.errors[:5]},
            )
        except Exception as exc:
            logger.warning("session_journal: stream journal failed: %s", exc)


# ── reads ────────────────────────────────────────────────────────────────
def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for key in ("tool_calls_json", "attachments_json", "metadata_json"):
        try:
            d[key.replace("_json", "")] = json.loads(d.pop(key) or ("{}" if key == "metadata_json" else "[]"))
        except Exception:
            d[key.replace("_json", "")] = {} if key == "metadata_json" else []
    return d


def turns_for_date(local_date: str, *, db_path: Optional[Path] = None, edition_name: str = "main") -> list[dict]:
    path = Path(db_path) if db_path else journal_db_path()
    if not path.exists():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            "SELECT * FROM max_session_turns WHERE local_date = ? AND edition = ? ORDER BY created_at, id",
            (local_date, edition_name),
        ).fetchall()
    finally:
        conn.close()
    return [_row(r) for r in rows]


def list_sessions(days: int = 7, limit: int = 100, *, db_path: Optional[Path] = None) -> list[dict]:
    path = Path(db_path) if db_path else journal_db_path()
    if not path.exists():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            """SELECT conversation_id, MIN(channel) AS channel, MIN(created_at) AS started_at,
                      MAX(created_at) AS updated_at, COUNT(*) AS turns,
                      SUM(CASE WHEN attachments_json NOT IN ('[]','') THEN 1 ELSE 0 END) AS with_attachments,
                      (SELECT content FROM max_session_turns t2 WHERE t2.conversation_id = t.conversation_id
                         AND t2.role = 'user' ORDER BY id LIMIT 1) AS first_user_text
                 FROM max_session_turns t
                WHERE edition = 'main' AND local_date >= date('now', ?)
                GROUP BY conversation_id
                ORDER BY updated_at DESC
                LIMIT ?""",
            (f"-{max(1, int(days))} days", max(1, min(int(limit), 500))),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_session(conversation_id: str, *, db_path: Optional[Path] = None, limit: int = 2000) -> list[dict]:
    path = Path(db_path) if db_path else journal_db_path()
    if not path.exists():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            "SELECT * FROM max_session_turns WHERE conversation_id = ? AND edition = 'main' ORDER BY created_at, id LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_row(r) for r in rows]


def attachment_path(sha: str) -> Optional[Path]:
    if not re.fullmatch(r"[0-9a-f]{24,64}", sha or ""):
        return None
    d = archive_root() / sha[:2]
    if not d.is_dir():
        return None
    return next((p for p in d.iterdir() if p.is_file() and p.name.startswith(sha[:24])), None)
