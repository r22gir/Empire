"""Read-only family-help tickets from /data/family-help/<ed>/help.db.

The live Dell store is ``/data/family-help/<ed>`` (symlinks onto the amp
and maxine data dirs). This module never writes, never sends, and never
imports the amp/maxine product line.

Under pytest / EMPIRE_TEST_GUARD, the path is forced to a temp tree.
Family editions only see their own store; Rafael's Max (main) reads both.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

HELP_EDITIONS = ("amp", "maxine")
CLOSED = frozenset({"done", "closed", "resolved", "cancelled"})
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
    """Which family stores this process may open."""
    raw = (os.getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")
    if raw in ("amp", "max_e", "maxe"):
        return ("amp",)
    if raw == "maxine":
        return ("maxine",)
    if raw in ("", "main", "workroom", "empire"):
        return HELP_EDITIONS
    return ()


def edition_store_dir(edition: str, *, base: Path | None = None) -> Path:
    return (base or inbox_base()) / edition


def _help_db(edition: str, *, base: Path | None = None) -> Path:
    return edition_store_dir(edition, base=base) / "help.db"


def write_ticket_for_tests(
    *,
    edition: str,
    ticket_id: str,
    sender: str,
    message: str,
    status: str = "new",
    created_at: str,
    base: Path | None = None,
) -> Path:
    """Test helper: write one ticket into a temp family-help store."""
    if not _under_test():
        raise RuntimeError("write_ticket_for_tests is test-only")
    path = _help_db(edition, base=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(TICKETS_DDL)
        conn.execute(
            """INSERT OR REPLACE INTO tickets
               (id, edition, sender, message, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ticket_id, edition, sender, message, status, created_at, created_at),
        )
        conn.commit()
    finally:
        conn.close()
    return path


def list_open_tickets(
    editions: Iterable[str] | None = None,
    *,
    base: Path | None = None,
) -> list[dict]:
    allowed = set(process_family_editions())
    want = list(editions or allowed)
    findings: list[dict] = []
    root = base or inbox_base()
    for edition in want:
        if edition not in allowed and allowed:
            continue
        if edition not in HELP_EDITIONS:
            continue
        db = _help_db(edition, base=root)
        if not db.is_file():
            continue
        try:
            resolved = db.resolve()
        except OSError:
            resolved = db
        # Never follow a symlink into a live family data tree during tests.
        if _under_test() and any(
            str(resolved).startswith(p) for p in ("/data/amp", "/data/maxine", "/data/family-help")
        ):
            continue
        try:
            conn = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """SELECT id, edition, sender, message, status, created_at
                       FROM tickets
                       WHERE status NOT IN ('done','closed','resolved','cancelled')
                       ORDER BY created_at ASC"""
                ).fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                findings.append({
                    "kind": "family_ticket",
                    "id": row["id"],
                    "name": (row["message"] or row["id"])[:80],
                    "customer": row["sender"] or "Family",
                    "status": row["status"],
                    "area": "family",
                    "edition": row["edition"] or edition,
                    "created_at": row["created_at"],
                    "isolated": True,
                })
        finally:
            conn.close()
    return findings
