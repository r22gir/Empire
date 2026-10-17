"""Family 'Pedir a Cursor' queue. Plain sqlite3, no FastAPI, no auto-launch."""
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
OWNER_DECISIONS = {"approve": "owner_approved", "changes": "changes_requested"}
CLI_STATUSES = frozenset({"in_progress", "pr_open", "done", "declined"})
TRANSITIONS = {
    "queued": frozenset({"in_progress", "declined"}),
    "in_progress": frozenset({"pr_open", "declined"}),
    "pr_open": frozenset({"owner_approved", "changes_requested", "declined"}),
    "owner_approved": frozenset({"in_progress", "done", "declined"}),
    "changes_requested": frozenset({"in_progress", "done", "declined"}),
    "done": frozenset({"declined"}),
    "declined": frozenset(),
}
PR_URL_RE = re.compile(r"^https://github\.com/r22gir/Empire/pull/\d+$")
MSG_CURSOR_PAUSED = (
    "Manito, ya usaste tu 20% del mes y Rafael está usando Max ahora. "
    "Guárdalo y lo mandas en un rato."
)
MSG_APPROVED = (
    "Listo, manito. Ya quedó aprobado de tu lado; Rafael da el sí final para desplegar."
)
MAX_TITLE = 120
MAX_BODY = 4000
MAX_FILES = 5
MAX_FILE_BYTES = 5 * 1024 * 1024
DEFAULT_EST_TOKENS = 60_000
CANONICAL_DATA_DIR = {
    "maxine": Path("/data/maxine"),
}
_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_WEBP = b"WEBP"


class CursorRequestError(ValueError):
    """User-facing validation error."""


def estimated_tokens() -> int:
    raw = os.getenv("CURSOR_REQUEST_EST_TOKENS", "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return DEFAULT_EST_TOKENS


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_family_edition() -> str:
    from app.edition import edition_name, is_family_edition

    if not is_family_edition():
        raise CursorRequestError("Pedir a Cursor solo aplica a esta edición.")
    return edition_name()


def assert_edition_data_dir(*, allow_tmp: bool | None = None) -> Path:
    """Refuse anything other than this edition's real data dir.

    Maxine's live path is ``/data/maxine``. A folder that merely happens
    to be named ``maxine`` (for example ``/tmp/foo/maxine``) is not enough.
    Tests may opt in with *allow_tmp* or ``PYTEST_CURRENT_TEST``.
    """
    from app.edition import data_root_or_none, edition_name, is_family_edition

    if not is_family_edition():
        raise CursorRequestError("CLI only runs on a family edition")
    edition = edition_name()
    root = data_root_or_none()
    if root is None:
        raise CursorRequestError("EMPIRE_DATA_DIR is required")
    expected = CANONICAL_DATA_DIR.get(edition, Path(f"/data/{edition}")).resolve()
    if root.resolve() == expected:
        return root
    if allow_tmp is None:
        allow_tmp = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if allow_tmp:
        return root
    raise CursorRequestError(f"EMPIRE_DATA_DIR must be {expected} (got {root})")


def _connect() -> sqlite3.Connection:
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
            created_at TEXT,
            updated_at TEXT,
            history TEXT
        )
        """
    )
    return conn


def _row(row: sqlite3.Row) -> dict[str, Any]:
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


def _image_kind(name: str, data: bytes) -> Optional[str]:
    lower = (name or "").lower()
    if data.startswith(_PNG) or lower.endswith(".png"):
        if data.startswith(_PNG):
            return ".png"
    if data.startswith(_JPEG) or lower.endswith((".jpg", ".jpeg")):
        if data.startswith(_JPEG):
            return ".jpg"
    if (data[:4] == b"RIFF" and data[8:12] == _WEBP) or lower.endswith(".webp"):
        if data[:4] == b"RIFF" and data[8:12] == _WEBP:
            return ".webp"
    return None


def _strip_jpeg_exif(data: bytes) -> bytes:
    if not data.startswith(b"\xff\xd8"):
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
        if marker in (0xD8, 0xD9):
            out.extend(data[i : i + 2])
            i += 2
            continue
        if i + 3 >= len(data):
            break
        seglen = int.from_bytes(data[i + 2 : i + 4], "big")
        if marker == 0xE1:
            i += 2 + seglen
            continue
        out.extend(data[i : i + 2 + seglen])
        i += 2 + seglen
    return bytes(out)


def normalize_image(name: str, data: bytes) -> tuple[str, bytes]:
    if len(data) > MAX_FILE_BYTES:
        raise CursorRequestError("Cada captura puede pesar hasta 5 MB.")
    kind = _image_kind(name, data)
    if not kind:
        raise CursorRequestError("Solo imágenes png, jpg o webp.")
    try:
        from io import BytesIO
        from PIL import Image

        img = Image.open(BytesIO(data))
        img = img.convert("RGB") if kind != ".png" and img.mode not in {"RGB", "L"} else img
        buf = BytesIO()
        if kind == ".jpg":
            img.save(buf, format="JPEG", quality=90, exif=b"")
        elif kind == ".webp":
            img.save(buf, format="WEBP")
        else:
            img.save(buf, format="PNG")
        return kind, buf.getvalue()
    except CursorRequestError:
        raise
    except Exception:
        blob = _strip_jpeg_exif(data) if kind == ".jpg" else data
        return kind, blob


def save_screenshots(req_id: str, files: list[tuple[str, bytes]]) -> list[str]:
    from app.edition import require_data_root

    if len(files) > MAX_FILES:
        raise CursorRequestError("Máximo 5 capturas.")
    root = require_data_root()
    folder = root / "cursor-requests" / req_id
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for i, (name, data) in enumerate(files):
        ext, blob = normalize_image(name, data)
        rel = f"cursor-requests/{req_id}/{i}{ext}"
        dest = root / rel
        dest.write_bytes(blob)
        paths.append(rel)
    return paths


def screenshot_abs_paths(row: dict[str, Any]) -> list[str]:
    from app.edition import data_root_or_none

    root = data_root_or_none()
    if root is None:
        return []
    out = []
    for rel in row.get("screenshots") or []:
        out.append(str((root / str(rel)).resolve()))
    return out


def cap_gate(*, title: str = "") -> Optional[str]:
    """None to proceed. Spanish refusal otherwise. Interactive (not background)."""
    from app.services.instance_usage import MSG_ABSOLUTE, MSG_PAUSED, enforce_usage_cap

    refusal = enforce_usage_cap(
        kind="cursor_request",
        text=title or "pedir a cursor",
        source="owner",
    )
    if not refusal:
        return None
    if refusal == MSG_ABSOLUTE:
        return refusal
    if refusal == MSG_PAUSED or "pausa" in (refusal or ""):
        return MSG_CURSOR_PAUSED
    return refusal


def _cap_state() -> str:
    from app.services.instance_usage import cap_percent, family_overage_allowed, usage_summary

    summary = usage_summary()
    used = float(summary.get("used_percent") or 0)
    if used >= float(summary.get("cap_percent") or cap_percent()):
        return "overage" if family_overage_allowed(used_percent=used) else "paused"
    return "base"


def create_request(
    *,
    title: str,
    body: str,
    files: Optional[list[tuple[str, bytes]]] = None,
    created_by: str = "",
) -> dict[str, Any]:
    edition = require_family_edition()
    title_c = (title or "").strip()
    body_c = (body or "").strip()
    if not title_c:
        raise CursorRequestError("Ponle un título, manito.")
    if len(title_c) > MAX_TITLE:
        raise CursorRequestError(f"El título puede tener hasta {MAX_TITLE} caracteres.")
    if not body_c:
        raise CursorRequestError("Cuéntame qué necesitas y por qué.")
    if len(body_c) > MAX_BODY:
        raise CursorRequestError(f"El detalle puede tener hasta {MAX_BODY} caracteres.")
    blocked = cap_gate(title=title_c)
    if blocked:
        raise CursorRequestError(blocked)
    req_id = str(uuid.uuid4())
    shots = save_screenshots(req_id, files or [])
    now = _now()
    est = estimated_tokens()
    cap_state = _cap_state()
    history = [{"status": "queued", "at": now, "by": created_by or "owner"}]
    conn = _connect()
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
                edition,
                title_c,
                body_c,
                json.dumps(shots),
                "queued",
                None,
                None,
                None,
                est,
                cap_state,
                created_by or "",
                now,
                now,
                json.dumps(history),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    _record_cursor_estimate(est)
    return get_request(req_id)


def _record_cursor_estimate(est: int) -> None:
    from app.services.instance_usage import record_usage

    record_usage(
        input_tokens=max(0, int(est)),
        output_tokens=0,
        kind="cursor_request",
        provider="cursor",
        model="cloud-agent",
    )


def _refund_cursor_estimate(est: int) -> None:
    """Drop the create-time estimate so a declined request does not keep the share."""
    tokens = int(est or 0)
    if tokens <= 0:
        return
    from app.services.instance_usage import record_usage

    record_usage(
        input_tokens=-tokens,
        output_tokens=0,
        kind="cursor_request",
        provider="cursor",
        model="cloud-agent",
        cost_usd=0.0,
    )


def list_requests(*, status: Optional[str] = None) -> list[dict[str, Any]]:
    edition = require_family_edition()
    conn = _connect()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM cursor_requests WHERE edition = ? AND status = ? ORDER BY created_at DESC",
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


def get_request(req_id: str) -> dict[str, Any]:
    edition = require_family_edition()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM cursor_requests WHERE id = ? AND edition = ?",
            (req_id, edition),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise CursorRequestError("No encontré ese pedido.")
    return _row(row)


def owner_decision(req_id: str, *, decision: str, note: str = "", by: str = "") -> dict[str, Any]:
    mapped = OWNER_DECISIONS.get((decision or "").strip().lower())
    if not mapped:
        raise CursorRequestError("La decisión es approve o changes.")
    row = get_request(req_id)
    if row["status"] != "pr_open":
        raise CursorRequestError("Ese pedido todavía no tiene un PR listo para revisar.")
    return _set_status(req_id, mapped, note_es=None, owner_note=note, pr_url=None, by=by or "owner")


def set_status(
    req_id: str,
    *,
    status: str,
    pr_url: Optional[str] = None,
    note_es: Optional[str] = None,
    by: str = "chief-e",
) -> dict[str, Any]:
    status_c = (status or "").strip().lower()
    if status_c not in CLI_STATUSES:
        raise CursorRequestError("Ese estado solo lo cambia Chief e por CLI.")
    if pr_url:
        if not PR_URL_RE.match(pr_url.strip()):
            raise CursorRequestError("pr-url must be https://github.com/r22gir/Empire/pull/<n>")
        pr_url = pr_url.strip()
    if status_c == "pr_open" and not pr_url:
        current = get_request(req_id)
        if not current.get("pr_url"):
            raise CursorRequestError("pr-url is required for pr_open")
    return _set_status(req_id, status_c, note_es=note_es, owner_note=None, pr_url=pr_url, by=by)


def _set_status(
    req_id: str,
    status: str,
    *,
    note_es: Optional[str],
    owner_note: Optional[str],
    pr_url: Optional[str],
    by: str,
) -> dict[str, Any]:
    row = get_request(req_id)
    allowed = TRANSITIONS.get(row["status"], frozenset())
    if status not in allowed:
        raise CursorRequestError(f"No se puede pasar de {row['status']} a {status}.")
    now = _now()
    history = list(row.get("history") or [])
    history.append({"status": status, "at": now, "by": by})
    fields = {"status": status, "updated_at": now, "history": json.dumps(history)}
    if note_es is not None:
        fields["note_es"] = note_es
    if owner_note is not None:
        fields["owner_note"] = owner_note
    if pr_url:
        fields["pr_url"] = pr_url
    assignments = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [req_id, require_family_edition()]
    conn = _connect()
    try:
        conn.execute(
            f"UPDATE cursor_requests SET {assignments} WHERE id = ? AND edition = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()
    if status == "declined" and row.get("status") != "declined":
        _refund_cursor_estimate(row.get("est_tokens") or 0)
    return get_request(req_id)


def can_launch(req_id: str) -> dict[str, Any]:
    row = get_request(req_id)
    blocked = cap_gate(title=row.get("title") or "")
    return {
        "id": req_id,
        "ok": blocked is None,
        "reason": blocked or "ok",
        "status": row["status"],
        "cap_state": row.get("cap_state"),
    }
