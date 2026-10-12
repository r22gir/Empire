"""Read-only family-help tickets from inbox_base()/<ed>/help.db.

Mirrors ``family_help.list_tickets(status="new")`` without importing that
module (its ``_connect`` creates tables). Opens each store with
``file:<path>?mode=ro``.

Live layout::

    /data/family-help/amp    → /data/amp/family-help/amp/help.db
    /data/family-help/maxine → /data/maxine/family-help/maxine/help.db

Schema (family-help-max): tickets(id, edition, sender, message, transcript,
context_json, status, created_at, updated_at, …) plus attachments(ticket_id,
kind, filename) and replies. There is no title column.

Never writes, never sends, never imports the amp/maxine product line.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

from app.services.max.brief_filters import family_ticket_title, is_test_family_ticket

HELP_EDITIONS = ("amp", "maxine")
EDITION_LABELS = {"amp": "Max-e", "maxine": "Maxine"}
TICKETS_DDL = """
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
ATTACHMENTS_DDL = """
CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    size INTEGER NOT NULL DEFAULT 0,
    stored_name TEXT NOT NULL DEFAULT ''
)
"""


def _under_test() -> bool:
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("EMPIRE_TEST_GUARD_LOG")
        or os.getenv("EMPIRE_TEST_GUARD")
    )


def inbox_base() -> Path:
    raw = (os.getenv("FAMILY_HELP_INBOX_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser()
    if _under_test():
        data = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
        return Path(data or "/tmp/empire-test-family-help") / "family-help"
    return Path("/data/family-help")


def process_family_editions() -> tuple[str, ...]:
    raw = (os.getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")
    if raw in ("amp", "max_e", "maxe"):
        return ("amp",)
    if raw == "maxine":
        return ("maxine",)
    if raw in ("", "main", "workroom", "empire"):
        return HELP_EDITIONS
    return ()


def edition_store_dir(edition: str, *, base: Path | None = None) -> Path:
    folder = (base or inbox_base()) / edition
    try:
        return folder.resolve()
    except OSError:
        return folder


def _help_db(edition: str, *, base: Path | None = None) -> Path:
    return edition_store_dir(edition, base=base) / "help.db"


def _blocked_live_path(path: Path) -> bool:
    if not _under_test():
        return False
    text = str(path)
    return any(text.startswith(p) for p in ("/data/amp", "/data/maxine", "/data/family-help"))


def write_ticket_for_tests(
    *,
    edition: str,
    ticket_id: str,
    sender: str,
    message: str,
    status: str = "new",
    created_at: str,
    base: Path | None = None,
    filename: str = "help.db",
    transcript: str = "",
    attachments: list[dict] | None = None,
) -> Path:
    """Test helper: write one ticket into a temp family-help store."""
    if not _under_test():
        raise RuntimeError("write_ticket_for_tests is test-only")
    folder = edition_store_dir(edition, base=base)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(TICKETS_DDL)
        conn.execute(ATTACHMENTS_DDL)
        conn.execute(
            """INSERT OR REPLACE INTO tickets
               (id, edition, sender, message, transcript, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticket_id, edition, sender, message, transcript or "", status, created_at, created_at),
        )
        for i, att in enumerate(attachments or []):
            conn.execute(
                """INSERT OR REPLACE INTO attachments
                   (id, ticket_id, kind, filename, stored_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    att.get("id") or f"{ticket_id}-att-{i}",
                    ticket_id,
                    att.get("kind") or "file",
                    att.get("filename") or "file",
                    att.get("stored_name") or att.get("filename") or "file",
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return path


def _read_new_tickets(path: Path, edition: str) -> list[dict]:
    if _blocked_live_path(path) or not path.is_file():
        return []
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """SELECT id, edition, sender, message, transcript, status, created_at
                   FROM tickets
                   WHERE status = 'new'
                   ORDER BY created_at ASC"""
            ).fetchall()
        except sqlite3.Error:
            return []
        items: list[dict] = []
        for raw in rows:
            row = dict(raw)
            kinds: list[str] = []
            try:
                atts = conn.execute(
                    "SELECT kind, filename FROM attachments WHERE ticket_id = ? ORDER BY filename",
                    (row["id"],),
                ).fetchall()
                kinds = [str(a["kind"] or a["filename"] or "").strip() for a in atts]
                kinds = [k for k in kinds if k]
            except sqlite3.Error:
                kinds = []
            ed = (row.get("edition") or edition or "").strip().lower()
            title = family_ticket_title(
                transcript=row.get("transcript") or "",
                message=row.get("message") or "",
                attachment_kinds=kinds,
            )
            item = {
                "kind": "family_ticket",
                "id": row.get("id"),
                "name": title,
                "message": row.get("message") or "",
                "transcript": row.get("transcript") or "",
                "customer": EDITION_LABELS.get(ed, ed or "Family"),
                "sender": row.get("sender") or "",
                "status": "new",
                "area": "family",
                "edition": ed,
                "edition_label": EDITION_LABELS.get(ed, ed),
                "attachment_kinds": kinds,
                "created_at": row.get("created_at"),
                "isolated": True,
            }
            if is_test_family_ticket(item):
                continue
            items.append(item)
        return items
    finally:
        conn.close()


def list_open_tickets(
    editions: Iterable[str] | None = None,
    *,
    base: Path | None = None,
) -> list[dict]:
    """Founder-facing ``status='new'`` tickets only. Read-only help.db."""
    allowed = set(process_family_editions())
    want = list(editions or allowed)
    findings: list[dict] = []
    seen_ids: set[str] = set()
    root = base or inbox_base()
    for edition in want:
        if edition not in allowed and allowed:
            continue
        if edition not in HELP_EDITIONS:
            continue
        path = _help_db(edition, base=root)
        for item in _read_new_tickets(path, edition):
            key = str(item.get("id") or "")
            if key and key in seen_ids:
                continue
            if key:
                seen_ids.add(key)
            findings.append(item)
    return findings
