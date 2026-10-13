"""Studio-side family request log.

Stores type, status, work log, and Organizer task links keyed by
``edition + ticket_id``. Never opens or writes a family ``help.db``.

Type enum is the PR #124 Sprint J model (``adjust`` / ``fix`` / ``create``).
Status is the founder request-log lifecycle, mapped from PR #124 proposal
states so we do not invent a second type/status vocabulary.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.services.supportforge_proposed_action import (
    VALID_KINDS,
    classify_proposed_action,
    propose_action,
)

# Founder-facing request-log statuses. Mapped from PR #124 proposal status.
LOG_STATUSES = ("new", "planned", "in_progress", "done", "declined")
VALID_LOG_STATUSES = frozenset(LOG_STATUSES)

# PR #124 proposal status → request-log status
LOG_STATUS_FROM_PROPOSAL = {
    "proposed": "new",
    "accepted": "planned",
    "rejected": "declined",
    "completed": "done",
}
# request-log status → PR #124 proposal status (for overlap / SupportForge)
PROPOSAL_STATUS_FROM_LOG = {
    "new": "proposed",
    "planned": "accepted",
    "in_progress": "accepted",
    "done": "completed",
    "declined": "rejected",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS family_request_meta (
    edition TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    request_type TEXT NOT NULL DEFAULT 'adjust',
    status TEXT NOT NULL DEFAULT 'new',
    type_suggested TEXT,
    type_edited INTEGER NOT NULL DEFAULT 0,
    seen_at TEXT,
    organizer_task_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (edition, ticket_id)
);
CREATE TABLE IF NOT EXISTS family_request_log (
    id TEXT PRIMARY KEY,
    edition TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    href TEXT,
    href_label TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_family_request_log_ticket
    ON family_request_log(edition, ticket_id, created_at);
"""


def _under_test() -> bool:
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("EMPIRE_TEST_GUARD_LOG")
        or os.getenv("EMPIRE_TEST_GUARD")
    )


def log_db_path() -> Path:
    raw = (os.getenv("FAMILY_REQUEST_LOG_DB") or "").strip()
    if raw:
        return Path(raw).expanduser()
    data = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    if data:
        return Path(data) / "family_request_log.db"
    from app.services.data_paths import data_root
    return data_root() / "family_request_log.db"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect() -> sqlite3.Connection:
    path = log_db_path()
    if _under_test():
        text = str(path.resolve()) if path.exists() or path.parent.exists() else str(path)
        if text.startswith("/data/amp") or text.startswith("/data/maxine") or text.startswith("/data/family-help"):
            raise RuntimeError("refusing to open a family help.db path for the Studio log")
        if text.endswith("help.db"):
            raise RuntimeError("Studio request log must not use help.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _validate_type(value: str) -> str:
    kind = (value or "").strip().lower()
    if kind not in VALID_KINDS:
        raise ValueError(f"type must be one of {sorted(VALID_KINDS)}")
    return kind


def _validate_status(value: str) -> str:
    status = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "inprogress": "in_progress",
        "progress": "in_progress",
        "declined": "declined",
        "rejected": "declined",
        "completed": "done",
        "proposed": "new",
        "accepted": "planned",
    }
    status = aliases.get(status, status)
    if status not in VALID_LOG_STATUSES:
        raise ValueError(f"status must be one of {list(LOG_STATUSES)}")
    return status


def suggest_type(message: str, transcript: str = "", edition: str = "") -> dict:
    proposed = propose_action(message or transcript, transcript, edition or None)
    return {
        "kind": proposed["kind"],
        "summary": proposed["summary"],
        "status": proposed["status"],
        "auto_build": False,
    }


def _row_meta(row: sqlite3.Row | None, *, edition: str, ticket_id: str, suggested: Optional[str] = None) -> dict:
    if row is None:
        kind = suggested or "adjust"
        return {
            "edition": edition,
            "ticket_id": ticket_id,
            "request_type": kind,
            "type": kind,
            "type_suggested": kind,
            "type_edited": False,
            "status": "new",
            "proposal_status": PROPOSAL_STATUS_FROM_LOG["new"],
            "seen_at": None,
            "organizer_task_id": None,
            "unread": True,
            "log": [],
        }
    kind = row["request_type"]
    status = row["status"]
    return {
        "edition": row["edition"],
        "ticket_id": row["ticket_id"],
        "request_type": kind,
        "type": kind,
        "type_suggested": row["type_suggested"] or kind,
        "type_edited": bool(row["type_edited"]),
        "status": status,
        "proposal_status": PROPOSAL_STATUS_FROM_LOG.get(status, "proposed"),
        "seen_at": row["seen_at"],
        "organizer_task_id": row["organizer_task_id"],
        "unread": row["seen_at"] is None,
        "log": [],
    }


def _log_rows(conn: sqlite3.Connection, edition: str, ticket_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT id, kind, body, href, href_label, created_at
           FROM family_request_log
           WHERE edition = ? AND ticket_id = ?
           ORDER BY created_at ASC""",
        (edition, ticket_id),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "kind": r["kind"],
            "body": r["body"],
            "href": r["href"],
            "href_label": r["href_label"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_meta(edition: str, ticket_id: str, *, suggested_type: Optional[str] = None) -> dict:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM family_request_meta WHERE edition = ? AND ticket_id = ?",
            (edition, ticket_id),
        ).fetchone()
        meta = _row_meta(row, edition=edition, ticket_id=ticket_id, suggested=suggested_type)
        meta["log"] = _log_rows(conn, edition, ticket_id)
        return meta
    finally:
        conn.close()


def ensure_meta(edition: str, ticket_id: str, *, message: str = "", transcript: str = "") -> dict:
    """Create the Studio row on first touch. Does not mark the request read."""
    suggested = classify_proposed_action(message, transcript)
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM family_request_meta WHERE edition = ? AND ticket_id = ?",
            (edition, ticket_id),
        ).fetchone()
        if row is None:
            now = _now()
            conn.execute(
                """INSERT INTO family_request_meta
                   (edition, ticket_id, request_type, status, type_suggested, type_edited,
                    seen_at, organizer_task_id, created_at, updated_at)
                   VALUES (?, ?, ?, 'new', ?, 0, NULL, NULL, ?, ?)""",
                (edition, ticket_id, suggested, suggested, now, now),
            )
            conn.commit()
        return get_meta(edition, ticket_id, suggested_type=suggested)
    finally:
        conn.close()


def mark_seen(edition: str, ticket_id: str, *, message: str = "", transcript: str = "") -> dict:
    ensure_meta(edition, ticket_id, message=message, transcript=transcript)
    conn = _connect()
    try:
        now = _now()
        conn.execute(
            """UPDATE family_request_meta
               SET seen_at = COALESCE(seen_at, ?), updated_at = ?
               WHERE edition = ? AND ticket_id = ?""",
            (now, now, edition, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_meta(edition, ticket_id)


def update_meta(
    edition: str,
    ticket_id: str,
    *,
    request_type: Optional[str] = None,
    status: Optional[str] = None,
    message: str = "",
    transcript: str = "",
) -> dict:
    ensure_meta(edition, ticket_id, message=message, transcript=transcript)
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM family_request_meta WHERE edition = ? AND ticket_id = ?",
            (edition, ticket_id),
        ).fetchone()
        now = _now()
        new_type = row["request_type"]
        new_status = row["status"]
        edited = row["type_edited"]
        if request_type is not None:
            new_type = _validate_type(request_type)
            if new_type != row["request_type"]:
                edited = 1
                _append_log(
                    conn,
                    edition,
                    ticket_id,
                    kind="type",
                    body=f"Type set to {new_type}",
                    created_at=now,
                )
        if status is not None:
            new_status = _validate_status(status)
            if new_status != row["status"]:
                _append_log(
                    conn,
                    edition,
                    ticket_id,
                    kind="status",
                    body=f"Status set to {new_status}",
                    created_at=now,
                )
        conn.execute(
            """UPDATE family_request_meta
               SET request_type = ?, status = ?, type_edited = ?, updated_at = ?
               WHERE edition = ? AND ticket_id = ?""",
            (new_type, new_status, int(edited), now, edition, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_meta(edition, ticket_id)


def _append_log(
    conn: sqlite3.Connection,
    edition: str,
    ticket_id: str,
    *,
    kind: str,
    body: str,
    href: Optional[str] = None,
    href_label: Optional[str] = None,
    created_at: Optional[str] = None,
) -> dict:
    entry = {
        "id": f"log-{uuid.uuid4().hex[:12]}",
        "kind": kind,
        "body": (body or "").strip(),
        "href": href,
        "href_label": href_label,
        "created_at": created_at or _now(),
    }
    if not entry["body"]:
        raise ValueError("log body is required")
    conn.execute(
        """INSERT INTO family_request_log
           (id, edition, ticket_id, kind, body, href, href_label, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            entry["id"],
            edition,
            ticket_id,
            entry["kind"],
            entry["body"],
            entry["href"],
            entry["href_label"],
            entry["created_at"],
        ),
    )
    return entry


def add_log(
    edition: str,
    ticket_id: str,
    *,
    body: str,
    kind: str = "note",
    href: Optional[str] = None,
    href_label: Optional[str] = None,
    message: str = "",
    transcript: str = "",
) -> dict:
    ensure_meta(edition, ticket_id, message=message, transcript=transcript)
    conn = _connect()
    try:
        entry = _append_log(
            conn,
            edition,
            ticket_id,
            kind=kind or "note",
            body=body,
            href=href,
            href_label=href_label,
        )
        conn.execute(
            "UPDATE family_request_meta SET updated_at = ? WHERE edition = ? AND ticket_id = ?",
            (entry["created_at"], edition, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    meta = get_meta(edition, ticket_id)
    meta["entry"] = entry
    return meta


def unread_ticket_ids() -> set[tuple[str, str]]:
    """Studio keys that have been marked seen. Caller subtracts from inbox."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT edition, ticket_id FROM family_request_meta WHERE seen_at IS NOT NULL"
        ).fetchall()
        return {(r["edition"], r["ticket_id"]) for r in rows}
    finally:
        conn.close()


def meta_map() -> dict[tuple[str, str], dict]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM family_request_meta").fetchall()
        out = {}
        for row in rows:
            key = (row["edition"], row["ticket_id"])
            meta = _row_meta(row, edition=row["edition"], ticket_id=row["ticket_id"])
            meta["log"] = _log_rows(conn, row["edition"], row["ticket_id"])
            out[key] = meta
        return out
    finally:
        conn.close()


def _ensure_tasks_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'normal',
            desk TEXT NOT NULL,
            business TEXT,
            assigned_to TEXT,
            created_by TEXT DEFAULT 'founder',
            due_date TEXT,
            tags TEXT,
            metadata TEXT,
            parent_task_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS task_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )"""
    )


def create_organizer_task(
    edition: str,
    ticket_id: str,
    *,
    title: str,
    description: str = "",
    message: str = "",
    transcript: str = "",
) -> dict:
    """Create an Organizer / Empire task. Writes Studio empire.db only, never help.db."""
    ensure_meta(edition, ticket_id, message=message, transcript=transcript)
    from app.db.database import get_db

    href = None
    task_id = None
    with get_db() as conn:
        _ensure_tasks_table(conn)
        payload = {
            "source": "family-help",
            "edition": edition,
            "ticket_id": ticket_id,
            "area": "Empire",
        }
        conn.execute(
            """INSERT INTO tasks
               (id, title, description, status, priority, desk, business, assigned_to,
                created_by, tags, metadata)
               VALUES (lower(hex(randomblob(8))), ?, ?, 'todo', 'normal', 'empire', 'empire',
                       'founder', 'founder', ?, ?)""",
            (
                title.strip() or f"Family request {ticket_id}",
                description.strip(),
                json.dumps(["family-help", "empire", edition]),
                json.dumps(payload),
            ),
        )
        row = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 1").fetchone()
        task_id = row["id"] if row else None
        if task_id:
            conn.execute(
                """INSERT INTO task_activity (task_id, actor, action, detail, metadata)
                   VALUES (?, 'founder', 'created', ?, ?)""",
                (task_id, f"Created from family request {edition}/{ticket_id}", json.dumps(payload)),
            )
    href = f"/?screen=tasks&id={task_id}" if task_id else "/?screen=tasks"
    conn = _connect()
    try:
        now = _now()
        conn.execute(
            """UPDATE family_request_meta
               SET organizer_task_id = ?, updated_at = ?
               WHERE edition = ? AND ticket_id = ?""",
            (task_id, now, edition, ticket_id),
        )
        _append_log(
            conn,
            edition,
            ticket_id,
            kind="organizer_task",
            body=f"Created Organizer task ({task_id}) — area Empire",
            href=href,
            href_label="Open Organizer task",
            created_at=now,
        )
        conn.commit()
    finally:
        conn.close()
    meta = get_meta(edition, ticket_id)
    meta["organizer_task"] = {"id": task_id, "href": href, "area": "Empire"}
    return meta
