"""Edition-local Cursor request queue. Launches nothing.

Juan (or Max-e) files a coding/build request. It lands in this edition's
SQLite on ``resolve_task_db_path()``. Chief e picks it up with the local
CLI. No outbound email / WhatsApp / SMS.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

STATUSES = (
    "queued",
    "in_progress",
    "pr_open",
    "owner_approved",
    "changes_requested",
    "done",
    "declined",
)
CLI_STATUSES = frozenset({"in_progress", "pr_open", "done", "declined"})
TRANSITIONS = {
    "queued": frozenset({"in_progress", "declined"}),
    "in_progress": frozenset({"pr_open", "declined"}),
    "pr_open": frozenset({"owner_approved", "changes_requested", "declined"}),
    "owner_approved": frozenset({"in_progress", "done", "declined"}),
    "changes_requested": frozenset({"in_progress", "done", "declined"}),
    "done": frozenset(),
    "declined": frozenset(),
}
PR_URL_RE = re.compile(r"^https://github\.com/r22gir/Empire/pull/\d+$")
ALLOWED_IMAGE_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp"})
MAX_FILES = 5
MAX_FILE_BYTES = 5 * 1024 * 1024
TITLE_MAX = 120
BODY_MAX = 4000
DEFAULT_EST_TOKENS = 60_000
MENSAJE_PAUSED = (
    "Manito, ya usaste tu 20% del mes y Rafael está usando Max ahora. "
    "Guárdalo y lo mandas en un rato."
)
MENSAJE_APPROVED = (
    "Listo, manito. Ya quedó aprobado de tu lado; Rafael da el sí final para desplegar."
)
MENSAJE_CHANGES = (
    "Listo, manito. Pediste cambios. Chief e lo vuelve a revisar."
)
EXPECTED_DATA_DIRS = {"amp": "/data/amp"}


class CursorRequestError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def edition_id() -> str:
    from app.edition import edition_name

    return edition_name()


def est_tokens() -> int:
    raw = (os.getenv("CURSOR_REQUEST_EST_TOKENS") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_EST_TOKENS


def connect() -> sqlite3.Connection:
    from app.db.database import resolve_task_db_path

    path = resolve_task_db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cursor_requests (
            id TEXT PRIMARY KEY,
            edition TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            screenshots TEXT,
            status TEXT NOT NULL CHECK(status IN (
                'queued','in_progress','pr_open','owner_approved',
                'changes_requested','done','declined'
            )),
            pr_url TEXT,
            note_es TEXT,
            owner_note TEXT,
            est_tokens INTEGER,
            cap_state TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            history TEXT
        )
        """
    )
    return conn


def _row(row: sqlite3.Row) -> dict:
    data = dict(row)
    for key in ("screenshots", "history"):
        raw = data.get(key)
        if isinstance(raw, str) and raw:
            try:
                data[key] = json.loads(raw)
            except json.JSONDecodeError:
                data[key] = []
        elif raw is None:
            data[key] = []
    return data


def validate_edition_data_dir() -> None:
    """CLI: EMPIRE_DATA_DIR must match EMPIRE_EDITION. Amp only."""
    edition = (os.getenv("EMPIRE_EDITION") or "").strip().lower()
    data = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    expected = EXPECTED_DATA_DIRS.get(edition)
    if not expected:
        raise CursorRequestError("EMPIRE_EDITION debe ser amp (esta cola es de la edición).")
    if not data:
        raise CursorRequestError("EMPIRE_DATA_DIR es obligatorio.")
    resolved = str(Path(data).expanduser().resolve())
    try:
        expected_resolved = str(Path(expected).resolve())
    except OSError:
        expected_resolved = expected
    if resolved == expected_resolved:
        return
    raise CursorRequestError(
        f"EMPIRE_DATA_DIR debe ser {expected} para EMPIRE_EDITION={edition}."
    )


def _magic_ok(data: bytes, ext: str) -> bool:
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def strip_exif(data: bytes, ext: str) -> bytes:
    if ext not in {".jpg", ".jpeg"} or not data.startswith(b"\xff\xd8"):
        return data
    out = bytearray(b"\xff\xd8")
    i = 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            out.extend(data[i:])
            break
        marker = data[i + 1]
        if marker == 0xDA:
            out.extend(data[i:])
            break
        if marker in {0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0x01, 0xD8, 0xD9}:
            out.extend(data[i : i + 2])
            i += 2
            continue
        if i + 3 >= len(data):
            out.extend(data[i:])
            break
        seglen = int.from_bytes(data[i + 2 : i + 4], "big")
        payload_start = i + 4
        if marker == 0xE1 and data[payload_start : payload_start + 4] == b"Exif":
            i += 2 + seglen
            continue
        out.extend(data[i : i + 2 + seglen])
        i += 2 + seglen
    return bytes(out)


def screenshot_dir(request_id: str) -> Path:
    from app.edition import require_data_root

    folder = require_data_root() / "cursor-requests" / request_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_screenshots(request_id: str, files: list[tuple[str, bytes]]) -> list[str]:
    if len(files) > MAX_FILES:
        raise CursorRequestError("Máximo 5 capturas, manito.")
    stored: list[str] = []
    folder = screenshot_dir(request_id)
    for index, (name, data) in enumerate(files):
        ext = Path(name or "").suffix.lower()
        if ext == ".jpeg":
            ext = ".jpg"
        if ext not in ALLOWED_IMAGE_EXT:
            raise CursorRequestError("Solo imágenes png, jpg o webp.")
        if not data or len(data) > MAX_FILE_BYTES:
            raise CursorRequestError("Cada captura puede pesar hasta 5 MB.")
        if not _magic_ok(data, ".jpeg" if ext == ".jpg" else ext):
            raise CursorRequestError("Ese archivo no parece una imagen válida.")
        clean = strip_exif(data, ext)
        rel = f"cursor-requests/{request_id}/{index:02d}{ext}"
        dest = folder / f"{index:02d}{ext}"
        dest.write_bytes(clean)
        stored.append(rel)
    return stored


def create_gate() -> Optional[str]:
    """Soft cap from brief 8a. None = accept."""
    from app.services.instance_usage import cap_percent, family_overage_allowed, usage_summary

    summary = usage_summary()
    used = float(summary.get("used_percent") or 0)
    if used < cap_percent():
        return None
    if family_overage_allowed(used):
        return None
    return MENSAJE_PAUSED


def _cap_state() -> str:
    from app.services.instance_usage import cap_percent, usage_summary

    used = float(usage_summary().get("used_percent") or 0)
    return "overage" if used >= cap_percent() else "base"


def create(
    *,
    title: str,
    body: str,
    files: Optional[list[tuple[str, bytes]]] = None,
    created_by: str = "",
) -> dict:
    from app.edition import is_family_edition
    from app.services.instance_usage import record_usage

    if not is_family_edition():
        raise CursorRequestError("Solo Max-e puede pedir esto aquí.", status_code=403)
    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        raise CursorRequestError("Ponle un título, manito.")
    if len(title) > TITLE_MAX:
        raise CursorRequestError(f"El título puede tener hasta {TITLE_MAX} caracteres.")
    if not body:
        raise CursorRequestError("Cuéntame qué necesitas y por qué.")
    if len(body) > BODY_MAX:
        raise CursorRequestError(f"El detalle puede tener hasta {BODY_MAX} caracteres.")
    refused = create_gate()
    if refused:
        raise CursorRequestError(refused, status_code=429)
    req_id = str(uuid.uuid4())
    paths = save_screenshots(req_id, files or [])
    tokens = est_tokens()
    cap_state = _cap_state()
    now = _now()
    history = [{"status": "queued", "at": now, "by": created_by or "owner"}]
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO cursor_requests (
                id, edition, title, body, screenshots, status, pr_url, note_es,
                owner_note, est_tokens, cap_state, created_by, created_at,
                updated_at, history
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                req_id,
                edition_id(),
                title,
                body,
                json.dumps(paths),
                "queued",
                None,
                None,
                None,
                tokens,
                cap_state,
                created_by or "owner",
                now,
                now,
                json.dumps(history),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    record_usage(
        input_tokens=tokens,
        output_tokens=0,
        model="cloud-agent",
        provider="cursor",
        kind="cursor_request",
    )
    return get(req_id)


def list_requests(*, status: Optional[str] = None) -> list[dict]:
    conn = connect()
    try:
        edition = edition_id()
        if status:
            rows = conn.execute(
                "SELECT * FROM cursor_requests WHERE edition = ? AND status = ? "
                "ORDER BY created_at DESC",
                (edition, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cursor_requests WHERE edition = ? ORDER BY created_at DESC",
                (edition,),
            ).fetchall()
        return [_row(r) for r in rows]
    finally:
        conn.close()


def get(req_id: str) -> dict:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM cursor_requests WHERE id = ? AND edition = ?",
            (req_id, edition_id()),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise CursorRequestError("No encuentro ese pedido.", status_code=404)
    return _row(row)


def screenshot_abs_paths(item: dict) -> list[str]:
    from app.edition import require_data_root

    root = require_data_root()
    paths = []
    for rel in item.get("screenshots") or []:
        paths.append(str((root / rel).resolve()))
    return paths


def _apply_status(
    req_id: str,
    new_status: str,
    *,
    by: str,
    pr_url: Optional[str] = None,
    note_es: Optional[str] = None,
    owner_note: Optional[str] = None,
) -> dict:
    if new_status not in STATUSES:
        raise CursorRequestError("Estado inválido.")
    item = get(req_id)
    allowed = TRANSITIONS.get(item["status"], frozenset())
    if new_status not in allowed:
        raise CursorRequestError(
            f"No se puede pasar de {item['status']} a {new_status}."
        )
    if pr_url is not None:
        if not PR_URL_RE.match(pr_url):
            raise CursorRequestError(
                "El PR tiene que ser https://github.com/r22gir/Empire/pull/<n>."
            )
    now = _now()
    history = list(item.get("history") or [])
    history.append({"status": new_status, "at": now, "by": by})
    fields = ["status = ?", "updated_at = ?", "history = ?"]
    values: list[Any] = [new_status, now, json.dumps(history)]
    if pr_url is not None:
        fields.append("pr_url = ?")
        values.append(pr_url)
    if note_es is not None:
        fields.append("note_es = ?")
        values.append(note_es)
    if owner_note is not None:
        fields.append("owner_note = ?")
        values.append(owner_note)
    values.extend([req_id, edition_id()])
    conn = connect()
    try:
        conn.execute(
            f"UPDATE cursor_requests SET {', '.join(fields)} WHERE id = ? AND edition = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()
    if new_status == "declined":
        _refund_estimate(item)
    return get(req_id)


def _refund_estimate(item: dict) -> None:
    """Undo the create-time token estimate when Chief e declines."""
    from app.services.instance_usage import record_usage

    tokens = int(item.get("est_tokens") or 0)
    if tokens <= 0:
        return
    history = item.get("history") or []
    if any(isinstance(h, dict) and h.get("status") == "declined" for h in history[:-1]):
        return
    record_usage(
        input_tokens=-tokens,
        output_tokens=0,
        model="cloud-agent",
        provider="cursor",
        kind="cursor_request",
    )


def set_status_cli(
    req_id: str,
    status: str,
    *,
    pr_url: Optional[str] = None,
    note_es: Optional[str] = None,
) -> dict:
    if status not in CLI_STATUSES:
        raise CursorRequestError(
            "El CLI solo puede poner in_progress, pr_open, done o declined."
        )
    return _apply_status(req_id, status, by="chief_e", pr_url=pr_url, note_es=note_es)


def owner_decision(req_id: str, decision: str, note: str = "", *, by: str = "owner") -> dict:
    item = get(req_id)
    if item["status"] != "pr_open":
        raise CursorRequestError("Ese pedido todavía no tiene un PR listo para revisar.")
    if decision == "approve":
        return _apply_status(req_id, "owner_approved", by=by, owner_note=note)
    if decision == "changes":
        return _apply_status(req_id, "changes_requested", by=by, owner_note=note)
    raise CursorRequestError("La decisión es approve o changes.")


def can_launch(req_id: str) -> dict:
    item = get(req_id)
    refused = create_gate()
    return {
        "id": req_id,
        "can_launch": refused is None,
        "reason": refused or "",
        "status": item["status"],
        "cap_state": item.get("cap_state"),
    }
