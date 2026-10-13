"""Read-only family-help tickets from edition help.db files.

Live layout (Studio / founder Max)::

    /data/amp/family-help/amp/help.db
    /data/maxine/family-help/maxine/help.db

A shared inbox tree is also accepted (Dell symlink layout)::

    /data/family-help/amp/help.db
    /data/family-help/maxine/help.db

This module never writes, never sends, and never imports the amp/maxine
product line. Opens each store with ``file:<path>?mode=ro``.

Under pytest / EMPIRE_TEST_GUARD the path is forced to a temp tree and
live ``/data/{amp,maxine,family-help}`` roots are refused.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

HELP_EDITIONS = ("amp", "maxine")
EDITION_WHO = {
    "amp": {"who": "Juan", "assistant": "Max-e", "label": "Juan / Max-e"},
    "maxine": {"who": "Camilo", "assistant": "Maxine", "label": "Camilo / Maxine"},
}
LIVE_ROOTS = ("/data/amp", "/data/maxine", "/data/family-help")


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


def _data_root_for_edition(edition: str) -> Path:
    env_key = f"FAMILY_HELP_{edition.upper()}_DIR"
    raw = (os.getenv(env_key) or "").strip()
    if raw:
        return Path(raw).expanduser()
    if _under_test():
        data = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
        return Path(data or "/tmp/empire-test-family-help") / edition / "family-help" / edition
    return Path(f"/data/{edition}/family-help/{edition}")


def process_family_editions() -> tuple[str, ...]:
    raw = (os.getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")
    if raw in ("amp", "max_e", "maxe"):
        return ("amp",)
    if raw == "maxine":
        return ("maxine",)
    if raw in ("", "main", "workroom", "empire"):
        return HELP_EDITIONS
    return ()


def _refuse_live(path: Path) -> bool:
    if not _under_test():
        return False
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    text = str(resolved)
    return any(text == root or text.startswith(root + "/") for root in LIVE_ROOTS)


def _candidate_dbs(edition: str, *, base: Path | None = None) -> list[Path]:
    """Possible help.db locations for one edition. First existing file wins."""
    if edition not in HELP_EDITIONS:
        return []
    shared = (base or inbox_base()) / edition / "help.db"
    edition_tree = _data_root_for_edition(edition) / "help.db"
    # edition_tree is /data/{ed}/family-help/{ed}/help.db (or test equivalent).
    # Also accept a folder that already *is* the store dir.
    extra = _data_root_for_edition(edition)
    if extra.name != "help.db":
        extra = extra / "help.db"
    seen: list[Path] = []
    for path in (edition_tree, extra, shared):
        if path not in seen:
            seen.append(path)
    return seen


def help_db_path(edition: str, *, base: Path | None = None) -> Optional[Path]:
    for path in _candidate_dbs(edition, base=base):
        if _refuse_live(path):
            continue
        if path.is_file():
            return path
    return None


def _open_ro(path: Path) -> Optional[sqlite3.Connection]:
    if _refuse_live(path) or not path.is_file():
        return None
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    if _refuse_live(resolved):
        return None
    try:
        conn = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    conn.row_factory = sqlite3.Row
    return conn


def _row_ticket(row: sqlite3.Row, edition: str) -> dict:
    keys = row.keys()
    context: list = []
    if "context_json" in keys:
        try:
            parsed = json.loads(row["context_json"] or "[]")
            if isinstance(parsed, list):
                context = parsed
        except (json.JSONDecodeError, TypeError):
            context = []
    who = EDITION_WHO.get(edition, {"who": "Family", "assistant": edition, "label": edition})
    message = row["message"] or ""
    transcript = (row["transcript"] or "") if "transcript" in keys else ""
    summary = (message or transcript or row["id"]).strip()
    return {
        "id": row["id"],
        "edition": row["edition"] if "edition" in keys and row["edition"] else edition,
        "sender": row["sender"] or who["who"],
        "who": who["who"],
        "assistant": who["assistant"],
        "who_label": who["label"],
        "message": message,
        "transcript": transcript,
        "summary": summary[:240],
        "context": context,
        "status": row["status"] if "status" in keys else "new",
        "created_at": row["created_at"] if "created_at" in keys else "",
        "updated_at": row["updated_at"] if "updated_at" in keys else "",
        "attachments": [],
        "replies": [],
    }


def _load_children(conn: sqlite3.Connection, ticket: dict) -> dict:
    ticket_id = ticket["id"]
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.Error:
        return ticket
    if "attachments" in tables:
        try:
            atts = conn.execute(
                "SELECT id, kind, filename, content_type, size FROM attachments "
                "WHERE ticket_id = ? ORDER BY filename",
                (ticket_id,),
            ).fetchall()
        except sqlite3.Error:
            atts = []
        ticket["attachments"] = [
            {
                "id": a["id"],
                "kind": a["kind"],
                "filename": a["filename"],
                "content_type": a["content_type"] if "content_type" in a.keys() else "",
                "size": a["size"] if "size" in a.keys() else 0,
            }
            for a in atts
        ]
    ticket["attachment_count"] = len(ticket.get("attachments") or [])
    if "replies" in tables:
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(replies)")}
            usage_sql = ", usage_tokens" if "usage_tokens" in cols else ""
            draft_clause = " AND draft = 0" if "draft" in cols else ""
            rows = conn.execute(
                f"SELECT id, author, body, created_at{usage_sql} FROM replies "
                f"WHERE ticket_id = ?{draft_clause} ORDER BY created_at",
                (ticket_id,),
            ).fetchall()
        except sqlite3.Error:
            rows = []
        ticket["replies"] = [
            {
                "id": r["id"],
                "author": r["author"],
                "body": r["body"],
                "created_at": r["created_at"],
                "usage_tokens": int(r["usage_tokens"]) if "usage_tokens" in r.keys() else 0,
            }
            for r in rows
        ]
    return ticket


def list_tickets(
    editions: Iterable[str] | None = None,
    *,
    status: Optional[str] = None,
    base: Path | None = None,
) -> list[dict]:
    allowed = set(process_family_editions())
    want = list(editions or allowed)
    findings: list[dict] = []
    for edition in want:
        if allowed and edition not in allowed:
            continue
        if edition not in HELP_EDITIONS:
            continue
        db = help_db_path(edition, base=base)
        if db is None:
            continue
        conn = _open_ro(db)
        if conn is None:
            continue
        try:
            sql = "SELECT * FROM tickets"
            args: list = []
            if status:
                sql += " WHERE status = ?"
                args.append(status)
            sql += " ORDER BY created_at DESC"
            try:
                rows = conn.execute(sql, args).fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                ticket = _load_children(conn, _row_ticket(row, edition))
                findings.append(ticket)
        finally:
            conn.close()
    findings.sort(key=lambda t: t.get("created_at") or "", reverse=True)
    return findings


def get_ticket(ticket_id: str, *, edition: Optional[str] = None, base: Path | None = None) -> Optional[dict]:
    editions = (edition,) if edition else process_family_editions()
    for ed in editions:
        if ed not in HELP_EDITIONS:
            continue
        db = help_db_path(ed, base=base)
        if db is None:
            continue
        conn = _open_ro(db)
        if conn is None:
            continue
        try:
            try:
                row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            except sqlite3.Error:
                continue
            if not row:
                continue
            return _load_children(conn, _row_ticket(row, ed))
        finally:
            conn.close()
    return None


def attachment_file(
    ticket_id: str,
    attachment_id: str,
    *,
    edition: Optional[str] = None,
    base: Path | None = None,
) -> Optional[tuple[Path, dict]]:
    ticket = get_ticket(ticket_id, edition=edition, base=base)
    if not ticket:
        return None
    ed = ticket["edition"]
    db = help_db_path(ed, base=base)
    if db is None:
        return None
    conn = _open_ro(db)
    if conn is None:
        return None
    try:
        try:
            row = conn.execute(
                "SELECT id, kind, filename, content_type, size, stored_name "
                "FROM attachments WHERE id = ? AND ticket_id = ?",
                (attachment_id, ticket_id),
            ).fetchone()
        except sqlite3.Error:
            return None
        if not row:
            return None
        stored = row["stored_name"] if "stored_name" in row.keys() else ""
        candidates = []
        if stored:
            candidates.append(db.parent / "files" / ticket_id / stored)
            candidates.append(db.parent / ticket_id / stored)
            candidates.append(db.parent / "attachments" / ticket_id / stored)
        for path in candidates:
            if _refuse_live(path):
                continue
            if path.is_file():
                return path, {
                    "id": row["id"],
                    "filename": row["filename"],
                    "content_type": row["content_type"] or "application/octet-stream",
                    "size": row["size"] if "size" in row.keys() else 0,
                    "kind": row["kind"],
                }
        return None
    finally:
        conn.close()


def write_ticket_for_tests(
    *,
    edition: str,
    ticket_id: str,
    sender: str,
    message: str,
    status: str = "new",
    created_at: str,
    transcript: str = "",
    attachments: Optional[list[dict]] = None,
    replies: Optional[list[dict]] = None,
    base: Path | None = None,
) -> Path:
    """Test helper: write one ticket into a temp family-help store."""
    if not _under_test():
        raise RuntimeError("write_ticket_for_tests is test-only")
    root = base or inbox_base()
    path = root / edition / "help.db"
    if _refuse_live(path):
        raise RuntimeError("refusing to write a live family-help path")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(
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
            );
            CREATE TABLE IF NOT EXISTS attachments (
                id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT,
                size INTEGER NOT NULL DEFAULT 0,
                stored_name TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS replies (
                id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                author TEXT NOT NULL,
                body TEXT NOT NULL,
                draft INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """INSERT OR REPLACE INTO tickets
               (id, edition, sender, message, transcript, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticket_id, edition, sender, message, transcript, status, created_at, created_at),
        )
        for att in attachments or []:
            conn.execute(
                """INSERT OR REPLACE INTO attachments
                   (id, ticket_id, kind, filename, content_type, size, stored_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    att["id"],
                    ticket_id,
                    att.get("kind") or "file",
                    att.get("filename") or "file",
                    att.get("content_type") or "",
                    int(att.get("size") or 0),
                    att.get("stored_name") or att.get("filename") or "file",
                ),
            )
            stored = att.get("stored_name") or att.get("filename")
            data = att.get("data")
            if stored and data is not None:
                dest = path.parent / "files" / ticket_id / stored
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data if isinstance(data, (bytes, bytearray)) else str(data).encode())
        for reply in replies or []:
            conn.execute(
                """INSERT OR REPLACE INTO replies
                   (id, ticket_id, author, body, draft, created_at)
                   VALUES (?, ?, ?, ?, 0, ?)""",
                (
                    reply["id"],
                    ticket_id,
                    reply.get("author") or "Max",
                    reply.get("body") or "",
                    reply.get("created_at") or created_at,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return path
