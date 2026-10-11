"""Family-edition help tickets to Rafael's personal Max.

Juan (Max-e / amp) and Camilo (Maxine) can file a ticket. The ticket
is stored in a dedicated help inbox — never in Workroom business
tables. Family processes may only create tickets for their own
edition and read replies to those tickets. They cannot open the
other edition's store or any Workroom path.

Personal Max (founder / workroom process) reads the inbox by scanning
per-edition stores (shared FAMILY_HELP_INBOX_DIR and/or peer dirs
under /data/amp and /data/maxine). Replies are written back into the
originating edition's store so the family chat can show them.

Max may draft a reply. Sending it requires Rafael's explicit yes.
This module never mutates Juan's or Camilo's business data or code.
Suggested code fixes are text only and must go through a cloud-agent
PR.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from app.edition import (
    AMP_COACH_NAME,
    EDITION_PROFILES,
    FAMILY_EDITIONS,
    MAXINE_OWNER_NAME,
    assistant_name,
    edition_name,
    is_family_edition,
    is_founder_edition,
    require_data_root,
)

HELP_EDITIONS = frozenset({"amp", "maxine"})
# Founder inbox hides these until Rafael clicks «Abrir adjuntos».
# Their files must never ride the notify email.
HIDDEN_ATTACHMENT_EDITIONS = frozenset({"maxine"})
STATUSES = ("new", "answered", "closed")
DEFAULT_DAILY_LIMIT = 20
CONTEXT_TURNS = 8
MAX_FILES = 5
MAX_FILE_BYTES = 8 * 1024 * 1024  # 8 MiB
MAX_VOICE_BYTES = 12 * 1024 * 1024  # 12 MiB
# Gmail/SMTP often choke near 10–25 MiB. Attach small files; mention the rest.
EMAIL_ATTACH_MAX_BYTES = 6 * 1024 * 1024
EMAIL_ATTACH_TOTAL_MAX_BYTES = 8 * 1024 * 1024

ALLOWED_FILE_EXT = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".txt", ".md",
    ".csv", ".doc", ".docx", ".xls", ".xlsx",
})
ALLOWED_VOICE_EXT = frozenset({
    ".webm", ".mp4", ".m4a", ".mp3", ".wav", ".ogg", ".aac", ".flac",
})
ALLOWED_FILE_MIME = frozenset({
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "application/pdf", "text/plain", "text/markdown", "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})
ALLOWED_VOICE_MIME = frozenset({
    "audio/webm", "audio/mp4", "audio/mpeg", "audio/wav", "audio/ogg",
    "audio/aac", "audio/flac", "audio/x-m4a", "audio/x-wav",
    "video/webm", "video/mp4",
})

FOUNDER_NOTIFY_EMAIL = "empirebox2026@gmail.com"
SHARED_INBOX_DEFAULT = Path("/data/family-help")
UI_CONFIRM_HEADER = "x-family-help-confirm"
UI_CONFIRM_VALUE = "si-enviar"
USAGE_ESTIMATE_NOTE = (
    "El tope del 20% usa una estimación de tokens "
    "(caracteres ÷ 4 + sobrecosto de archivo/voz), no el conteo del proveedor."
)
HTML_LIKE_EXT = frozenset({
    ".html", ".htm", ".shtml", ".xhtml", ".svg", ".xml", ".js", ".mjs",
})
HTML_LIKE_MIME = frozenset({
    "text/html", "application/xhtml+xml", "image/svg+xml",
    "text/xml", "application/xml", "text/javascript",
    "application/javascript", "application/x-javascript",
})
MIME_ALIASES = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
    "image/x-png": "image/png",
    "image/x-citrix-pjpeg": "image/jpeg",
    "application/x-pdf": "application/pdf",
    "application/acrobat": "application/pdf",
    "application/x-csv": "text/csv",
    "text/x-markdown": "text/markdown",
    "text/x-csv": "text/csv",
    "audio/wave": "audio/wav",
    "audio/x-wav": "audio/wav",
    "audio/vnd.wave": "audio/wav",
}
UNKNOWN_MIME = frozenset({
    "",
    "application/octet-stream",
    "binary/octet-stream",
    "application/download",
    "application/force-download",
})
EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".webm": "audio/webm",
    ".mp4": "audio/mp4",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
}
INBOX_AUTH_PREFIXES = ("/api/v1/family-help/inbox",)
TOOL_EXPLICIT_YES_SOURCES = frozenset({
    "max_tool", "llm", "tool_executor", "chat", "openclaw", "telegram",
})

WORKROOM_LEAKS = (
    "5124 Frolich", "Frolich", "Hyattsville", "workroom@empirebox.store",
    "workroom@", "woodcraft@empirebox.store", "woodcraft@",
    "Nelma's Workroom", "Nelma's", "Nelma", "Dahlia = Nehal Elrefai",
    "Nehal Elrefai", "Dahlia", "The Willard Hotel", "The Willard",
    "McLean Whittington", "9408 old courthouse", "Empire Workroom",
    "RG's Drapery", "empire-box-memory", "~/empire-repo", "empire-repo",
    "/home/rg", "/data/empire",
)

# Maxine must never put Argos Campestre legal/company details on a ticket.
ARGOS_LEGAL_PATTERNS = (
    re.compile(r"\bNIT[\s:#-]*\d[\d.\-]{4,}", re.I),
    re.compile(r"\braz[oó]n\s+social\b[:\s].{0,120}", re.I),
    re.compile(r"\b(matr[ií]cula(?:\s+mercantil)?|c[aá]mara\s+de\s+comercio)\b[:\s].{0,120}", re.I),
    re.compile(r"\b(representante\s+legal|escritura\s+p[uú]blica|estatutos?)\b[:\s].{0,120}", re.I),
    re.compile(r"\bgrupo\s+argos\s+campestre\b.{0,80}", re.I),
    re.compile(r"\bargos\s+campestre\b.{0,80}", re.I),
)

HELP_INTENT_RE = re.compile(
    r"(?:"
    r"pide(?:r|le)?\s+ayuda\s+a\s+max"
    r"|pedir\s+ayuda\s+a\s+max"
    r"|ask(?:\s+for)?\s+help(?:\s+from)?\s+(?:to\s+)?max"
    r"|ask\s+max\s+for\s+help"
    r"|help\s+from\s+max"
    r")",
    re.I,
)

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\s().-]?){8,15}\d(?!\w)")
_PIN_RE = re.compile(r"\b(?:pin|founder[_-]?pin|c[oó]digo)\s*[:#]?\s*\d{4,8}\b", re.I)
_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|jwt)\s*[:=]\s*\S+"
)
_PATH_RE = re.compile(
    r"(?:"
    r"/home/rg\S*"
    r"|~/empire\S*"
    r"|/data/(?:amp|maxine|empire|images|backups)\S*"
    r"|empire-repo\S*"
    r")"
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def daily_limit() -> int:
    raw = os.getenv("FAMILY_HELP_DAILY_LIMIT", "").strip()
    try:
        value = int(raw) if raw else DEFAULT_DAILY_LIMIT
    except ValueError:
        value = DEFAULT_DAILY_LIMIT
    return max(1, value)


def founder_notify_email() -> str:
    raw = (os.getenv("FAMILY_HELP_NOTIFY_EMAIL") or "").strip()
    if raw.lower() == FOUNDER_NOTIFY_EMAIL:
        return FOUNDER_NOTIFY_EMAIL
    # Hard rule: help-ticket mail only goes to the founder inbox.
    return FOUNDER_NOTIFY_EMAIL


def edition_owner_name(edition: Optional[str] = None) -> str:
    key = (edition or edition_name() or "").strip().lower()
    if key == "amp":
        return AMP_COACH_NAME
    if key == "maxine":
        return MAXINE_OWNER_NAME
    return "Owner"


def _fold_accents(text: str) -> str:
    import unicodedata
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text or "")
        if unicodedata.category(ch) != "Mn"
    )


def is_help_intent(message: str) -> bool:
    text = _fold_accents((message or "").strip())
    if not text:
        return False
    return bool(HELP_INTENT_RE.search(text))


def leftover_after_intent(message: str) -> str:
    text = (message or "").strip()
    folded = _fold_accents(text)
    match = HELP_INTENT_RE.search(folded)
    if not match:
        return text
    # Map folded span back approximately by using the regex on folded text
    # and slicing the original by the same offsets (accents are rare in the cue).
    cleaned = HELP_INTENT_RE.sub(" ", folded)
    return re.sub(r"\s+", " ", cleaned).strip(" .,;:-")


def redact_text(text: str, *, edition: Optional[str] = None) -> str:
    """Strip Workroom, Argos legal (Maxine), secrets, and host paths."""
    if not text:
        return ""
    out = str(text)
    for leak in WORKROOM_LEAKS:
        out = re.sub(re.escape(leak), "[oculto]", out, flags=re.I)
    key = (edition or "").strip().lower()
    if key == "maxine" or (key == "" and edition_name() == "maxine"):
        for pat in ARGOS_LEGAL_PATTERNS:
            out = pat.sub("[oculto:argos]", out)
    out = _SECRET_RE.sub("[oculto]", out)
    out = _PIN_RE.sub("[oculto]", out)
    out = _EMAIL_RE.sub("[oculto]", out)
    out = _PHONE_RE.sub("[oculto]", out)
    out = _PATH_RE.sub("[oculto]", out)
    return out


def sanitize_context_turns(
    history: Optional[Iterable[dict]],
    *,
    edition: Optional[str] = None,
    limit: int = CONTEXT_TURNS,
) -> list[dict]:
    rows = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "user").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "")
        if content.startswith("[Context from previous sessions]") or content == "Context loaded. Ready.":
            continue
        if content.startswith("[Family help"):
            continue
        cleaned = redact_text(content, edition=edition).strip()
        if not cleaned:
            continue
        rows.append({"role": role, "content": cleaned[:2000]})
    return rows[-max(1, limit):]


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for raw in paths:
        try:
            resolved = raw.expanduser().resolve()
        except OSError:
            resolved = Path(raw)
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        out.append(resolved)
    return out


def _secure_mkdir(path: Path) -> Path:
    """Create ``path`` and chmod 700 so sibling edition users cannot peek."""
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def inbox_base() -> Path:
    """Shared tree ``FAMILY_HELP_INBOX_DIR`` (prod: ``/data/family-help``).

    All three processes must set the same base. Per-edition subfolders
    (``amp/``, ``maxine/``) are chmod 700 so sibling OS users cannot peek.
    Unset in tests: family instances stay under ``EMPIRE_DATA_DIR``.
    """
    raw = os.getenv("FAMILY_HELP_INBOX_DIR", "").strip()
    if raw:
        return _secure_mkdir(Path(raw).expanduser())
    if is_family_edition():
        return _secure_mkdir(require_data_root() / "family-help")
    founder = (os.getenv("FAMILY_HELP_FOUNDER_INBOX") or "").strip()
    path = Path(founder or str(SHARED_INBOX_DEFAULT)).expanduser()
    try:
        return _secure_mkdir(path)
    except OSError:
        return path


def edition_store_dir(edition: str) -> Path:
    key = (edition or "").strip().lower()
    if key not in HELP_EDITIONS:
        raise ValueError("edición de ayuda no válida")
    return _secure_mkdir(inbox_base() / key)


def _peer_store_dirs() -> dict[str, Path]:
    """Founder-only: every edition store we are allowed to open."""
    found: dict[str, Path] = {}

    def add(edition: str, path: Path) -> None:
        key = edition.strip().lower()
        if key not in HELP_EDITIONS:
            return
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            resolved = path
        if key not in found:
            found[key] = resolved

    base = inbox_base()
    for edition in HELP_EDITIONS:
        add(edition, base / edition)

    raw = os.getenv("FAMILY_HELP_PEER_DIRS", "").strip()
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "=" in item:
            edition, path = item.split("=", 1)
            add(edition, Path(path.strip()))
            continue
        path = Path(item)
        name = path.name.lower()
        if name in HELP_EDITIONS:
            add(name, path)
        else:
            # `{data}/family-help` from a family instance
            parent = path.parent.name.lower()
            if parent in HELP_EDITIONS:
                add(parent, path)

    for edition, profile in EDITION_PROFILES.items():
        if edition not in HELP_EDITIONS:
            continue
        data_dir = profile.get("data_dir")
        if data_dir:
            add(edition, Path(data_dir) / "family-help" / edition)
            add(edition, Path(data_dir) / "family-help")

    return found


def store_dir_for(edition: str) -> Path:
    key = (edition or "").strip().lower()
    if is_family_edition():
        mine = edition_name()
        if key != mine:
            raise PermissionError("esta edición no puede abrir el buzón de otra")
        return edition_store_dir(mine)
    if not is_founder_edition():
        raise PermissionError("sin acceso al buzón de ayuda familiar")
    peers = _peer_store_dirs()
    if key not in peers:
        return edition_store_dir(key)
    path = peers[key]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _db_path(edition: str) -> Path:
    folder = store_dir_for(edition)
    return folder / "help.db"


def _connect(edition: str) -> sqlite3.Connection:
    path = _db_path(edition)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            transcript TEXT,
            context_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attachments (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT,
            size INTEGER NOT NULL DEFAULT 0,
            stored_name TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS replies (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            draft INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_help_tickets_day ON tickets(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_help_att_ticket ON attachments(ticket_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_help_reply_ticket ON replies(ticket_id)")
    ticket_cols = {row[1] for row in conn.execute("PRAGMA table_info(tickets)")}
    if "attachments_revealed" not in ticket_cols:
        conn.execute(
            "ALTER TABLE tickets ADD COLUMN attachments_revealed INTEGER NOT NULL DEFAULT 0"
        )
    if "transcript_pending" not in ticket_cols:
        conn.execute(
            "ALTER TABLE tickets ADD COLUMN transcript_pending INTEGER NOT NULL DEFAULT 0"
        )
    reply_cols = {row[1] for row in conn.execute("PRAGMA table_info(replies)")}
    if "usage_tokens" not in reply_cols:
        conn.execute(
            "ALTER TABLE replies ADD COLUMN usage_tokens INTEGER NOT NULL DEFAULT 0"
        )
    return conn


def _files_dir(edition: str, ticket_id: str) -> Path:
    folder = store_dir_for(edition) / "files" / ticket_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _remember_usage_root(edition: str) -> None:
    """Family process writes its EMPIRE_DATA_DIR so a founder reply can meter usage."""
    if not is_family_edition():
        return
    try:
        marker = store_dir_for(edition) / "usage_root"
        marker.write_text(str(require_data_root()), encoding="utf-8")
    except Exception:
        pass


def _usage_root_for(edition: str) -> Optional[Path]:
    try:
        marker = store_dir_for(edition) / "usage_root"
        if marker.is_file():
            raw = marker.read_text(encoding="utf-8").strip()
            if raw:
                return Path(raw)
    except Exception:
        pass
    return None


def _safe_filename(name: str, fallback: str) -> str:
    raw = Path(name or "").name.strip() or fallback
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._") or fallback
    return cleaned[:120]


def _norm_mime(content_type: str) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def infer_mime(filename: str, content_type: str) -> str:
    """Normalize browser aliases and infer from extension when MIME is empty/generic."""
    mime = MIME_ALIASES.get(_norm_mime(content_type), _norm_mime(content_type))
    if mime not in UNKNOWN_MIME:
        return mime
    ext = Path(filename or "").suffix.lower()
    return EXT_TO_MIME.get(ext, mime if mime not in UNKNOWN_MIME else "")


MIME_TO_EXT = {mime: ext for ext, mime in EXT_TO_MIME.items()}
MIME_TO_EXT["image/jpeg"] = ".jpg"


def fallback_filename(name: str, content_type: str, kind: str = "file") -> str:
    """Keep uploads that arrive without a name (some Android browsers)."""
    raw = Path(name or "").name.strip() or kind
    if Path(raw).suffix:
        return raw
    mime = infer_mime(raw, content_type)
    ext = MIME_TO_EXT.get(mime) or ""
    if ext:
        return f"{raw}{ext}"
    return raw


def attachments_hidden_until_reveal(edition: Optional[str]) -> bool:
    """True for Maxine (and any edition marked hidden-attachments)."""
    return (edition or "").strip().lower() in HIDDEN_ATTACHMENT_EDITIONS


def inbox_path_requires_founder_studio_auth(path: str) -> bool:
    """``/inbox*`` is founder-only and sits behind studio / family auth."""
    clean = (path or "").split("?", 1)[0]
    return any(clean == prefix or clean.startswith(prefix + "/") for prefix in INBOX_AUTH_PREFIXES)


def explicit_yes_from_ui(request, body_flag: bool = False) -> bool:
    """True only when the inbox «Sí, enviar» button sent the confirm header.

    JSON ``explicit_yes`` from Max's LLM / tool path is ignored.
    """
    header = ""
    if request is not None:
        header = (request.headers.get(UI_CONFIRM_HEADER) or "").strip().lower()
    return header == UI_CONFIRM_VALUE


def tool_source_can_set_explicit_yes(source: str) -> bool:
    return (source or "").strip().lower() not in TOOL_EXPLICIT_YES_SOURCES


async def read_upload_limited(
    upload,
    *,
    limit: int,
    content_length: Optional[int] = None,
) -> bytes:
    """Read an UploadFile while enforcing ``limit``. Never slurp past the cap."""
    declared = content_length
    if declared is None:
        size = getattr(upload, "size", None)
        if size is not None:
            try:
                declared = int(size)
            except (TypeError, ValueError):
                declared = None
    if declared is not None and declared > limit:
        raise ValueError("el archivo supera el tamaño permitido")
    buf = bytearray()
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > limit:
            raise ValueError("el archivo supera el tamaño permitido")
    return bytes(buf)


def validate_upload(
    *,
    filename: str,
    content_type: str,
    data: bytes,
    kind: str,
) -> str:
    """Require BOTH an allowed extension AND an allowed MIME. HTML/SVG never pass."""
    if not data:
        raise ValueError("archivo vacío")
    limit = MAX_VOICE_BYTES if kind == "voice" else MAX_FILE_BYTES
    if len(data) > limit:
        raise ValueError("el archivo supera el tamaño permitido")
    ext = Path(filename or "").suffix.lower()
    mime = infer_mime(filename, content_type)
    if ext in HTML_LIKE_EXT or mime in HTML_LIKE_MIME:
        raise ValueError("tipo de archivo no permitido")
    if kind == "voice":
        if ext not in ALLOWED_VOICE_EXT or mime not in ALLOWED_VOICE_MIME:
            raise ValueError("tipo de audio no permitido")
        return "voice"
    if ext not in ALLOWED_FILE_EXT or mime not in ALLOWED_FILE_MIME:
        raise ValueError("tipo de archivo no permitido")
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return "image"
    if ext == ".pdf":
        return "pdf"
    return "file"


def safe_download_headers(filename: str, content_type: str) -> dict[str, str]:
    """Never serve uploads inline as HTML. Force download + nosniff."""
    mime = infer_mime(filename, content_type)
    if mime in HTML_LIKE_MIME or not mime or mime.startswith("text/html"):
        mime = "application/octet-stream"
    safe_name = _safe_filename(filename, "download")
    return {
        "Content-Disposition": f'attachment; filename="{safe_name}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Type": mime,
    }


def tickets_today(edition: str) -> int:
    day = _now().strftime("%Y-%m-%d")
    conn = _connect(edition)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM tickets WHERE edition = ? AND created_at LIKE ?",
            (edition, f"{day}%"),
        ).fetchone()
        return int(row["n"] if row else 0)
    finally:
        conn.close()


def rate_limit_ok(edition: str) -> bool:
    return tickets_today(edition) < daily_limit()


def estimate_help_tokens(*, text: str = "", transcript: str = "", files: int = 0, voice: bool = False) -> int:
    chars = len(text or "") + len(transcript or "")
    tokens = max(80, chars // 4)
    tokens += 200 * max(0, files)
    if voice:
        tokens += 400
    return tokens


def check_help_cap(
    *,
    text: str = "",
    transcript: str = "",
    kind: str = "family_help",
) -> Optional[str]:
    from app.services.instance_usage import enforce_usage_cap

    return enforce_usage_cap(
        kind=kind,
        text=text or transcript or "help",
        source="family_help",
        tools=True,
    )


def record_help_usage(
    *,
    edition: str,
    text: str = "",
    transcript: str = "",
    files: int = 0,
    voice: bool = False,
    kind: str = "family_help",
    check_cap: bool = True,
) -> Optional[str]:
    from app.services.instance_usage import record_usage

    if check_cap:
        refusal = check_help_cap(text=text, transcript=transcript, kind=kind)
        if refusal:
            return refusal
    tokens = estimate_help_tokens(text=text, transcript=transcript, files=files, voice=voice)
    record_usage(
        input_tokens=tokens,
        output_tokens=0,
        model="family-help",
        provider="family-help",
        kind=kind,
    )
    return None


def _row_ticket(row: sqlite3.Row, *, include_private: bool = False) -> dict:
    context = []
    try:
        context = json.loads(row["context_json"] or "[]")
    except json.JSONDecodeError:
        context = []
    keys = row.keys()
    payload = {
        "id": row["id"],
        "edition": row["edition"],
        "sender": row["sender"],
        "message": row["message"],
        "transcript": row["transcript"] or "",
        "transcript_pending": bool(row["transcript_pending"]) if "transcript_pending" in keys else False,
        "attachments_revealed": bool(row["attachments_revealed"]) if "attachments_revealed" in keys else False,
        "context": context,
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "attachments": [],
        "replies": [],
        "usage": {
            "reply_tokens": 0,
            "charged_to": row["edition"],
            "note": USAGE_ESTIMATE_NOTE,
        },
    }
    if not include_private:
        return payload
    return payload


def _load_children(conn: sqlite3.Connection, ticket: dict) -> dict:
    ticket_id = ticket["id"]
    atts = conn.execute(
        "SELECT id, kind, filename, content_type, size FROM attachments WHERE ticket_id = ? ORDER BY filename",
        (ticket_id,),
    ).fetchall()
    hide_attachments = (
        is_founder_edition()
        and attachments_hidden_until_reveal(ticket.get("edition"))
        and not ticket.get("attachments_revealed")
    )
    ticket["attachment_count"] = len(atts)
    ticket["attachments_hidden"] = bool(hide_attachments and atts)
    if hide_attachments:
        ticket["attachments"] = []
    else:
        ticket["attachments"] = [
            {
                "id": a["id"],
                "kind": a["kind"],
                "filename": a["filename"],
                "content_type": a["content_type"],
                "size": a["size"],
            }
            for a in atts
        ]
    reply_cols = {row[1] for row in conn.execute("PRAGMA table_info(replies)")}
    has_usage = "usage_tokens" in reply_cols
    usage_sql = (
        "SELECT id, author, body, draft, created_at, usage_tokens FROM replies "
        if has_usage
        else "SELECT id, author, body, draft, created_at FROM replies "
    )
    replies = conn.execute(
        usage_sql + "WHERE ticket_id = ? AND draft = 0 ORDER BY created_at",
        (ticket_id,),
    ).fetchall()
    reply_tokens = 0
    ticket["replies"] = []
    for r in replies:
        tokens = int(r["usage_tokens"]) if has_usage else 0
        reply_tokens += tokens
        ticket["replies"].append(
            {
                "id": r["id"],
                "author": r["author"],
                "body": r["body"],
                "created_at": r["created_at"],
                "usage_tokens": tokens,
            }
        )
    ticket["usage"] = {
        "reply_tokens": reply_tokens,
        "charged_to": ticket.get("edition"),
        "note": USAGE_ESTIMATE_NOTE,
    }
    drafts = conn.execute(
        "SELECT id, author, body, created_at FROM replies WHERE ticket_id = ? AND draft = 1 ORDER BY created_at DESC LIMIT 3",
        (ticket_id,),
    ).fetchall()
    ticket["drafts"] = [
        {
            "id": r["id"],
            "author": r["author"],
            "body": r["body"],
            "created_at": r["created_at"],
        }
        for r in drafts
    ]
    return ticket


def get_ticket(ticket_id: str, *, edition: Optional[str] = None) -> Optional[dict]:
    if edition:
        editions = [edition]
    elif is_family_edition():
        editions = [edition_name()]
    else:
        editions = list(HELP_EDITIONS)
    for ed in editions:
        try:
            conn = _connect(ed)
        except PermissionError:
            continue
        try:
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            if not row:
                continue
            if is_family_edition() and row["edition"] != edition_name():
                return None
            return _load_children(conn, _row_ticket(row, include_private=True))
        finally:
            conn.close()
    return None


def list_tickets(*, edition: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
    if is_family_edition():
        editions = [edition_name()]
    elif edition:
        if edition not in HELP_EDITIONS:
            return []
        editions = [edition]
    else:
        editions = list(HELP_EDITIONS)
    out = []
    for ed in editions:
        try:
            conn = _connect(ed)
        except PermissionError:
            continue
        try:
            sql = "SELECT * FROM tickets WHERE edition = ?"
            args: list[Any] = [ed]
            if status:
                sql += " AND status = ?"
                args.append(status)
            sql += " ORDER BY created_at DESC"
            for row in conn.execute(sql, args):
                out.append(_load_children(conn, _row_ticket(row, include_private=True)))
        finally:
            conn.close()
    out.sort(key=lambda t: t.get("created_at") or "", reverse=True)
    return out


def create_ticket(
    *,
    message: str,
    sender: Optional[str] = None,
    history: Optional[list[dict]] = None,
    transcript: Optional[str] = None,
    attachments: Optional[list[dict]] = None,
    edition: Optional[str] = None,
    notify: bool = True,
) -> dict:
    if not is_family_edition():
        raise PermissionError("solo Max-e y Maxine pueden crear tickets de ayuda")
    mine = edition_name()
    if mine not in HELP_EDITIONS:
        raise PermissionError("esta edición no envía tickets de ayuda")
    if edition and edition != mine:
        raise PermissionError("no puedes crear un ticket como otra edición")

    text = redact_text((message or "").strip(), edition=mine)
    voice_text = redact_text((transcript or "").strip(), edition=mine)
    if not text and not voice_text and not attachments:
        raise ValueError("escribe un mensaje, graba voz o adjunta un archivo")

    if not rate_limit_ok(mine):
        raise PermissionError(
            f"llegaste al límite de {daily_limit()} pedidos de ayuda por día"
        )

    files = list(attachments or [])
    if len(files) > MAX_FILES + 1:  # +1 voice
        raise ValueError(f"máximo {MAX_FILES} archivos más un audio")

    prepared = []
    for item in files:
        data = item.get("data") or b""
        raw_name = fallback_filename(
            item.get("filename") or "",
            item.get("content_type") or "",
            item.get("kind") or "file",
        )
        kind = validate_upload(
            filename=raw_name,
            content_type=item.get("content_type") or "",
            data=data,
            kind=item.get("kind") or "file",
        )
        redacted_name = redact_text(raw_name or kind, edition=mine) or kind
        display = _safe_filename(redacted_name, kind)
        prepared.append({
            "data": data,
            "kind": kind,
            "filename": display,
            "content_type": infer_mime(raw_name, item.get("content_type") or ""),
        })

    if not text and not voice_text and not prepared:
        raise ValueError("escribe un mensaje, graba voz o adjunta un archivo")

    has_voice = any(item["kind"] == "voice" for item in prepared)
    pending = bool(has_voice and not voice_text)

    refusal = check_help_cap(text=text, transcript=voice_text, kind="family_help_request")
    if refusal:
        raise PermissionError(refusal)

    _remember_usage_root(mine)
    ticket_id = f"fh-{uuid.uuid4().hex[:12]}"
    now = _iso()
    sender_name = (sender or "").strip() or edition_owner_name(mine)
    context = sanitize_context_turns(history, edition=mine)
    files_root = None
    conn = _connect(mine)
    saved_files = []
    try:
        conn.execute(
            """
            INSERT INTO tickets (
                id, edition, sender, message, transcript, context_json,
                status, created_at, updated_at, attachments_revealed, transcript_pending
            ) VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?, 0, ?)
            """,
            (
                ticket_id, mine, sender_name, text, voice_text,
                json.dumps(context, ensure_ascii=False), now, now,
                1 if pending else 0,
            ),
        )
        for item in prepared:
            att_id = f"fa-{uuid.uuid4().hex[:10]}"
            stored = _safe_filename(item["filename"], f"{item['kind']}-{att_id}")
            files_root = _files_dir(mine, ticket_id)
            dest = files_root / f"{att_id}-{stored}"
            dest.write_bytes(item["data"])
            conn.execute(
                """
                INSERT INTO attachments (
                    id, ticket_id, kind, filename, content_type, size, stored_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    att_id, ticket_id, item["kind"], stored,
                    (item["content_type"] or "")[:120],
                    len(item["data"]), dest.name,
                ),
            )
            saved_files.append({
                "id": att_id,
                "kind": item["kind"],
                "filename": stored,
                "content_type": item["content_type"],
                "size": len(item["data"]),
            })
        conn.commit()
    except Exception:
        conn.rollback()
        if files_root is not None:
            shutil.rmtree(files_root, ignore_errors=True)
        raise
    finally:
        conn.close()

    record_help_usage(
        edition=mine,
        text=text,
        transcript=voice_text,
        files=len(prepared),
        voice=has_voice,
        kind="family_help_request",
        check_cap=False,
    )

    ticket = get_ticket(ticket_id, edition=mine) or {
        "id": ticket_id,
        "edition": mine,
        "sender": sender_name,
        "message": text,
        "transcript": voice_text,
        "context": context,
        "status": "new",
        "created_at": now,
        "updated_at": now,
        "attachments": saved_files,
        "replies": [],
    }
    if notify:
        notify_new_ticket(ticket)
    return ticket


def attachment_path(ticket_id: str, attachment_id: str, *, edition: Optional[str] = None) -> Optional[Path]:
    ticket = get_ticket(ticket_id, edition=edition)
    if not ticket:
        return None
    ed = ticket["edition"]
    if is_family_edition() and ed != edition_name():
        return None
    conn = _connect(ed)
    try:
        row = conn.execute(
            "SELECT stored_name FROM attachments WHERE id = ? AND ticket_id = ?",
            (attachment_id, ticket_id),
        ).fetchone()
        if not row:
            return None
        path = _files_dir(ed, ticket_id) / row["stored_name"]
        if not path.is_file():
            return None
        return path
    finally:
        conn.close()


def add_reply(
    ticket_id: str,
    body: str,
    *,
    author: str = "Max",
    draft: bool = False,
    explicit_yes: bool = False,
    source: str = "api",
) -> dict:
    if is_family_edition():
        raise PermissionError("las ediciones familiares no responden el buzón de Max")
    if not is_founder_edition():
        raise PermissionError("solo el Max personal de Rafael puede responder")
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise FileNotFoundError("ticket no encontrado")
    text = redact_text((body or "").strip(), edition=ticket["edition"])
    if not text:
        raise ValueError("la respuesta está vacía")
    if not draft:
        if not tool_source_can_set_explicit_yes(source):
            raise PermissionError(
                "Max no envía ni aplica cambios desde una herramienta o el LLM"
            )
        if source != "ui_confirm_button" or not explicit_yes:
            raise PermissionError(
                "Max no envía ni aplica cambios sin el sí explícito de Rafael"
            )

    tokens = 0
    if not draft:
        # Charge the family edition's 20% cap, not Workroom's meter.
        tokens = estimate_help_tokens(text=text)
        _record_peer_usage(ticket["edition"], text)

    now = _iso()
    reply_id = f"fr-{uuid.uuid4().hex[:10]}"
    conn = _connect(ticket["edition"])
    try:
        conn.execute(
            """
            INSERT INTO replies (id, ticket_id, author, body, draft, created_at, usage_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (reply_id, ticket_id, author, text, 1 if draft else 0, now, tokens),
        )
        if not draft:
            conn.execute(
                "UPDATE tickets SET status = 'answered', updated_at = ? WHERE id = ?",
                (now, ticket_id),
            )
        else:
            conn.execute(
                "UPDATE tickets SET updated_at = ? WHERE id = ?",
                (now, ticket_id),
            )
        conn.commit()
    finally:
        conn.close()
    return get_ticket(ticket_id) or ticket


def reveal_attachments(ticket_id: str) -> dict:
    """Founder-only: Rafael opens Maxine attachments after the warning."""
    if is_family_edition() or not is_founder_edition():
        raise PermissionError("solo el Max personal de Rafael puede abrir adjuntos")
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise FileNotFoundError("ticket no encontrado")
    now = _iso()
    conn = _connect(ticket["edition"])
    try:
        conn.execute(
            "UPDATE tickets SET attachments_revealed = 1, updated_at = ? WHERE id = ?",
            (now, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_ticket(ticket_id) or ticket


def voice_attachment(ticket: dict) -> Optional[dict]:
    for item in ticket.get("attachments") or []:
        if item.get("kind") == "voice":
            return item
    if ticket.get("attachments_hidden"):
        # Founder may retry STT without revealing other files.
        ed = ticket["edition"]
        conn = _connect(ed)
        try:
            row = conn.execute(
                "SELECT id, kind, filename, content_type, size FROM attachments "
                "WHERE ticket_id = ? AND kind = 'voice' LIMIT 1",
                (ticket["id"],),
            ).fetchone()
        finally:
            conn.close()
        if row:
            return {
                "id": row["id"],
                "kind": row["kind"],
                "filename": row["filename"],
                "content_type": row["content_type"],
                "size": row["size"],
            }
    return None


def set_transcript(ticket_id: str, text: str, *, pending: bool) -> dict:
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise FileNotFoundError("ticket no encontrado")
    ed = ticket["edition"]
    if is_family_edition() and ed != edition_name():
        raise PermissionError("esta edición no puede abrir el buzón de otra")
    cleaned = redact_text((text or "").strip(), edition=ed)
    now = _iso()
    conn = _connect(ed)
    try:
        conn.execute(
            "UPDATE tickets SET transcript = ?, transcript_pending = ?, updated_at = ? WHERE id = ?",
            (cleaned, 1 if pending else 0, now, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_ticket(ticket_id, edition=ed) or ticket


def close_ticket(ticket_id: str) -> dict:
    if is_family_edition():
        raise PermissionError("las ediciones familiares no cierran tickets del buzón de Max")
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise FileNotFoundError("ticket no encontrado")
    now = _iso()
    conn = _connect(ticket["edition"])
    try:
        conn.execute(
            "UPDATE tickets SET status = 'closed', updated_at = ? WHERE id = ?",
            (now, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_ticket(ticket_id) or ticket


def draft_reply(ticket_id: str) -> dict:
    """Suggest a reply. Never changes family data or code."""
    if is_family_edition():
        raise PermissionError("solo el Max personal de Rafael puede redactar")
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise FileNotFoundError("ticket no encontrado")
    who = ticket.get("sender") or edition_owner_name(ticket["edition"])
    edition_label = "Max-e" if ticket["edition"] == "amp" else "Maxine"
    voice = (ticket.get("transcript") or "").strip()
    msg = (ticket.get("message") or "").strip()
    body = (
        f"Hola {who.split()[0] if who else ''},\n\n"
        f"Vi tu pedido de ayuda desde {edition_label}. "
    ).strip() + "\n\n"
    if msg:
        body += f"Entendí esto: {msg[:400]}\n\n"
    if voice:
        body += f"Y en el audio: {voice[:400]}\n\n"
    body += (
        "Te propongo el siguiente paso en tu propia edición. "
        "No voy a cambiar tus datos ni tu código desde este ticket. "
        "Si hay un arreglo de código, va por un PR de cloud-agent para que Rafael lo revise.\n\n"
        "¿Quieres que Rafael envíe esta respuesta?"
    )
    saved = add_reply(
        ticket_id,
        body,
        author="Max (borrador)",
        draft=True,
        explicit_yes=False,
        source="draft",
    )
    latest = (saved.get("drafts") or [{}])[0]
    return {
        "ticket_id": ticket_id,
        "draft": latest.get("body") or body,
        "requires_explicit_yes": True,
        "can_apply_automatically": False,
        "code_fix_path": "cloud-agent PR",
        "ticket": saved,
    }


def apply_change_from_ticket(*, ticket_id: str, explicit_yes: bool = False) -> dict:
    """Hard stop: tickets never mutate family data/code in-process."""
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise FileNotFoundError("ticket no encontrado")
    if not explicit_yes:
        raise PermissionError("hace falta el sí explícito de Rafael")
    return {
        "applied": False,
        "reason": "code_or_data_changes_require_cloud_agent_pr",
        "ticket_id": ticket_id,
        "next": "Abre un cloud-agent PR para que Rafael lo revise. Este ticket no escribe en la edición familiar.",
    }


def _record_peer_usage(edition: str, text: str) -> None:
    """Charge the family edition's usage.db even from the founder process."""
    from app.services.instance_usage import estimate_cost

    tokens = estimate_help_tokens(text=text)
    roots = []
    remembered = _usage_root_for(edition)
    if remembered is not None:
        roots.append(remembered)
    profile = EDITION_PROFILES.get(edition) or {}
    if profile.get("data_dir"):
        roots.append(Path(profile["data_dir"]))
    try:
        store = store_dir_for(edition)
        if store.parent.name == "family-help":
            roots.append(store.parent.parent)
        raw = os.getenv("FAMILY_HELP_PEER_DIRS", "")
        for part in raw.split(","):
            item = part.strip()
            if not item:
                continue
            path = Path(item.split("=", 1)[-1].strip())
            if path.name == edition or path.parent.name == edition:
                roots.append(path if path.name != "family-help" else path.parent)
            if (path / "usage").is_dir():
                roots.append(path)
    except Exception:
        pass
    seen = set()
    for root in roots:
        try:
            resolved = root.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        usage_dir = resolved / "usage"
        try:
            usage_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        db = usage_dir / "usage.db"
        try:
            conn = sqlite3.connect(str(db))
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    day TEXT NOT NULL,
                    month TEXT NOT NULL,
                    model TEXT,
                    provider TEXT,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    kind TEXT,
                    blocked INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            now = _now()
            conn.execute(
                """
                INSERT INTO llm_usage (
                    created_at, day, month, model, provider,
                    input_tokens, output_tokens, cost_usd, kind, blocked
                ) VALUES (?,?,?,?,?,?,?,?,?,0)
                """,
                (
                    now.isoformat(),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%Y-%m"),
                    "family-help",
                    "family-help",
                    int(tokens),
                    0,
                    estimate_cost(tokens, 0) if callable(estimate_cost) else 0.0,
                    "family_help_reply",
                ),
            )
            conn.commit()
            conn.close()
            return
        except Exception:
            continue


def format_byte_size(n: int) -> str:
    try:
        size = int(n or 0)
    except (TypeError, ValueError):
        size = 0
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _raw_attachment_rows(ticket_id: str, edition: str) -> list[sqlite3.Row]:
    """DB rows even when the founder inbox still hides Maxine files."""
    conn = _connect(edition)
    try:
        return list(
            conn.execute(
                "SELECT id, kind, filename, content_type, size, stored_name "
                "FROM attachments WHERE ticket_id = ? ORDER BY filename",
                (ticket_id,),
            )
        )
    finally:
        conn.close()


def load_notify_files(ticket: dict) -> list[dict]:
    """Read stored attachment bytes for the founder email. No URLs."""
    ticket_id = str(ticket.get("id") or "")
    edition = str(ticket.get("edition") or "")
    if not ticket_id or edition not in HELP_EDITIONS:
        return []
    out = []
    try:
        rows = _raw_attachment_rows(ticket_id, edition)
    except PermissionError:
        return []
    for row in rows:
        path = _files_dir(edition, ticket_id) / row["stored_name"]
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        out.append({
            "id": row["id"],
            "kind": row["kind"],
            "filename": row["filename"],
            "content_type": row["content_type"] or infer_mime(row["filename"], ""),
            "size": int(row["size"] or len(data)),
            "data": data,
        })
    return out


def split_email_attachments(
    files: list[dict],
    *,
    allow_attach: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Attach small files when allowed; mention the rest. Never emit a URL.

    Hidden-attachment editions (Maxine) always take the mention path so
    file bytes never leave the inbox until Rafael clicks «Abrir adjuntos».
    """
    attach: list[dict] = []
    mention: list[dict] = []
    total = 0
    for item in files:
        data = item.get("data") or b""
        size = int(item.get("size") or len(data) or 0)
        filename = item.get("filename") or "archivo"
        mime = infer_mime(filename, item.get("content_type") or "")
        ext = Path(filename).suffix.lower()
        unsafe = ext in HTML_LIKE_EXT or mime in HTML_LIKE_MIME
        payload = {
            "filename": filename,
            "content_type": mime or "application/octet-stream",
            "size": size,
            "kind": item.get("kind") or "file",
        }
        if (
            allow_attach
            and not unsafe
            and data
            and size <= EMAIL_ATTACH_MAX_BYTES
            and total + size <= EMAIL_ATTACH_TOTAL_MAX_BYTES
        ):
            attach.append({**payload, "data": data})
            total += size
        else:
            mention.append(payload)
    return attach, mention


def _notify_mention_note(*, hidden: bool, oversized: bool) -> str:
    if hidden:
        return (
            "— Ábrelo en el Max personal → Ayuda de ediciones familiares "
            "(Abrir adjuntos). No hay enlace público."
        )
    if oversized:
        return (
            "— demasiado grande para el correo. Ábrelo en el Max personal → "
            "Ayuda de ediciones familiares. No hay enlace público."
        )
    return (
        "— Ábrelo en el Max personal → Ayuda de ediciones familiares. "
        "No hay enlace público."
    )


def build_notify_email(ticket: dict) -> dict:
    """Founder-only notify: text + attachment bytes or an inbox mention. No URLs."""
    edition = ticket.get("edition")
    hidden = attachments_hidden_until_reveal(edition)
    label = "Max-e" if edition == "amp" else "Maxine"
    title = f"Ayuda de {label}: {ticket.get('sender') or edition_owner_name(edition)}"
    preview = (ticket.get("message") or ticket.get("transcript") or "").strip()[:400]
    if hidden:
        # Metadata only — do not read Maxine file bytes for email.
        stored = []
        try:
            for row in _raw_attachment_rows(str(ticket.get("id") or ""), str(edition or "")):
                stored.append({
                    "filename": row["filename"],
                    "size": int(row["size"] or 0),
                    "kind": row["kind"],
                    "content_type": row["content_type"] or "",
                    "data": b"",
                })
        except PermissionError:
            stored = []
        attach, mention = [], stored
    else:
        stored = load_notify_files(ticket)
        attach, mention = split_email_attachments(stored, allow_attach=True)
    if not attach and not mention and stored:
        mention = [
            {
                "filename": item.get("filename") or "archivo",
                "size": int(item.get("size") or 0),
                "kind": item.get("kind") or "file",
            }
            for item in stored
        ]

    rows_html = []
    for item in attach:
        rows_html.append(
            "<li>"
            f"{html.escape(str(item['filename']), quote=True)} "
            f"({html.escape(format_byte_size(item['size']), quote=True)}) "
            "— incluido en este correo."
            "</li>"
        )
    for item in mention:
        size = int(item.get("size") or 0)
        rows_html.append(
            "<li>"
            f"{html.escape(str(item['filename']), quote=True)} "
            f"({html.escape(format_byte_size(size), quote=True)}) "
            f"{_notify_mention_note(hidden=hidden, oversized=size > EMAIL_ATTACH_MAX_BYTES)}"
            "</li>"
        )
    if stored and not rows_html:
        rows_html.append("<li>Hay un adjunto. Ábrelo en el buzón de ayuda familiar. No hay enlace público.</li>")

    att_block = ""
    if rows_html:
        att_block = (
            "<p><strong>Adjuntos</strong></p><ul>"
            + "".join(rows_html)
            + "</ul>"
        )
    elif ticket.get("attachment_count") or ticket.get("attachments"):
        att_block = (
            "<p><strong>Adjuntos</strong></p>"
            "<p>Hay un archivo en el ticket. Ábrelo en el Max personal → "
            "Ayuda de ediciones familiares. No hay enlace público.</p>"
        )

    html_body = (
        f"<p><strong>{html.escape(title, quote=True)}</strong></p>"
        f"<p>Ticket <code>{html.escape(str(ticket.get('id') or ''), quote=True)}</code></p>"
        f"<p>{html.escape(preview or 'Audio o archivo adjunto.', quote=True)}</p>"
        f"{att_block}"
        "<p>Responde desde el Max personal (no el módulo Workroom). Sin Telegram. "
        "Sin enlace público ni URL firmada.</p>"
    )
    return {
        "subject": title,
        "html": html_body,
        "attachments": [
            {
                "filename": item["filename"],
                "content_type": item.get("content_type") or "application/octet-stream",
                "data": item["data"],
            }
            for item in attach
        ],
        "mentioned": mention,
        "preview": preview,
        "label": label,
    }


def notify_new_ticket(ticket: dict) -> dict:
    """In-app notice + email to empirebox2026@gmail.com only."""
    result = {"notification": None, "email": "skipped", "email_attachments": 0, "email_mentioned": 0}
    built = build_notify_email(ticket)
    edition = ticket.get("edition")
    label = built["label"]
    title = built["subject"]
    preview = built["preview"]
    message = (
        f"{label} · ticket {ticket.get('id')}\n"
        f"{preview or '(audio o archivo sin texto)'}\n"
        "Abre el chat de Max → Ayuda de ediciones familiares."
    )
    try:
        from app.routers.notifications import notify_founder
        result["notification"] = notify_founder(
            "MAX",
            "decision_needed",
            title,
            message,
            "high",
            {
                "ticket_id": ticket.get("id"),
                "edition": edition,
                "surface": "family_help",
            },
        )
    except Exception:
        pass

    to = founder_notify_email()
    if to != FOUNDER_NOTIFY_EMAIL:
        result["email"] = "blocked_non_founder"
        return result
    try:
        from app.services.max.email_recipient_whitelist import is_recipient_authorized
        if not is_recipient_authorized(to):
            result["email"] = "blocked_whitelist"
            return result
    except Exception:
        if to != FOUNDER_NOTIFY_EMAIL:
            result["email"] = "blocked"
            return result

    html_body = built["html"]
    email_atts = built["attachments"]
    result["email_attachments"] = len(email_atts)
    result["email_mentioned"] = len(built["mentioned"])
    try:
        import asyncio
        from app.services.email.sender import send_email

        async def _send():
            return await send_email(to, title, html_body, attachments=email_atts)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            result["email"] = "queued"
            loop.create_task(_send())
        else:
            sent = asyncio.run(_send())
            result["email"] = "sent" if sent else "not_configured"
    except Exception as exc:
        result["email"] = f"error:{type(exc).__name__}"
    return result


def handle_chat_intent(
    message: str,
    *,
    history: Optional[list[dict]] = None,
    sender: Optional[str] = None,
    attachments: Optional[list[dict]] = None,
) -> Optional[dict]:
    """If the chat text is a help-to-Max command, file the ticket."""
    if not is_family_edition() or not is_help_intent(message):
        return None
    leftover = leftover_after_intent(message)
    body = leftover or "El usuario pidió ayuda a Max desde el chat."
    kept = []
    for item in attachments or []:
        try:
            validate_upload(
                filename=item.get("filename") or "",
                content_type=item.get("content_type") or "",
                data=item.get("data") or b"",
                kind=item.get("kind") or "file",
            )
            kept.append(item)
        except ValueError:
            continue
    ticket = create_ticket(
        message=body,
        sender=sender,
        history=history,
        attachments=kept or None,
        notify=True,
    )
    locale_es = True
    first = ticket["id"]
    reply = (
        f"Listo. Envié tu pedido a Max (ticket {first}). "
        "Rafael o Max te responden aquí cuando haya una respuesta. "
        "No cambié tus datos."
        if locale_es
        else f"Sent your request to Max (ticket {first}). Rafael or Max will reply here."
    )
    return {"ticket": ticket, "response": reply}


def public_status() -> dict:
    ed = edition_name()
    family = is_family_edition() and ed in HELP_EDITIONS
    used = tickets_today(ed) if family else 0
    return {
        "enabled": family or is_founder_edition(),
        "edition": ed,
        "family": family,
        "founder_inbox": is_founder_edition(),
        "can_create": family,
        "can_read_inbox": is_founder_edition(),
        "daily_limit": daily_limit(),
        "daily_used": used,
        "daily_remaining": max(0, daily_limit() - used) if family else None,
        "assistant": assistant_name(),
    }
