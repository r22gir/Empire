"""Read-only family-help tickets from the founder inbox stores.

The live Dell layout is::

    /data/family-help/amp    → /data/amp/family-help/amp
    /data/family-help/maxine → /data/maxine/family-help/maxine

Official family-help-max writes ``help.db`` (``tickets`` table) in that
resolved folder. This reader also opens sibling sqlite/json files in the
same store directory in case the live filename is not ``help.db``.

Never writes, never sends, never imports the amp/maxine product line.
Under pytest / EMPIRE_TEST_GUARD the path is forced to a temp tree.
Family editions only see their own store; Rafael's Max (main) reads both.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Iterable

from app.services.max.brief_filters import is_test_family_ticket

HELP_EDITIONS = ("amp", "maxine")
CLOSED = frozenset({"done", "closed", "resolved", "cancelled"})
STORE_FILENAMES = (
    "help.db",
    "tickets.db",
    "family.db",
    "inbox.db",
    "help.sqlite",
    "tickets.json",
    "inbox.json",
)
TICKET_TABLES = ("tickets", "family_help_tickets", "help_tickets", "requests")
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


def _blocked_live_path(path: Path) -> bool:
    if not _under_test():
        return False
    text = str(path)
    return any(text.startswith(p) for p in ("/data/amp", "/data/maxine", "/data/family-help"))


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path


def _edition_store_dirs(edition: str, *, base: Path | None = None) -> list[Path]:
    """Follow /data/family-help/<ed> onto /data/{amp,maxine}/family-help/<ed>."""
    root = base or inbox_base()
    link = root / edition
    guesses = [link]
    resolved = _safe_resolve(link)
    if resolved != link:
        guesses.append(resolved)
    if not _under_test():
        guesses.extend([
            Path(f"/data/{edition}/family-help/{edition}"),
            Path(f"/data/{edition}/family-help"),
        ])
    found: list[Path] = []
    seen: set[str] = set()
    for path in guesses:
        real = _safe_resolve(path) if path.exists() else path
        if _blocked_live_path(real):
            continue
        if not real.exists():
            continue
        key = str(real)
        if key in seen:
            continue
        seen.add(key)
        found.append(real)
    return found


def _store_files(store_dir: Path) -> list[Path]:
    if store_dir.is_file():
        return [store_dir]
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        if not path.is_file():
            return
        if _blocked_live_path(path):
            return
        key = str(_safe_resolve(path))
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    for name in STORE_FILENAMES:
        add(store_dir / name)
    if store_dir.is_dir():
        for path in store_dir.glob("*.db"):
            add(path)
        for path in store_dir.glob("*.sqlite"):
            add(path)
        for path in store_dir.glob("*.json"):
            add(path)
        tickets_dir = store_dir / "tickets"
        if tickets_dir.is_dir():
            for path in tickets_dir.glob("*.json"):
                add(path)
    return found


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
) -> Path:
    """Test helper: write one ticket into a temp family-help store."""
    if not _under_test():
        raise RuntimeError("write_ticket_for_tests is test-only")
    folder = edition_store_dir(edition, base=base)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    if path.suffix.lower() == ".json":
        payload = {
            "id": ticket_id,
            "edition": edition,
            "sender": sender,
            "message": message,
            "status": status,
            "created_at": created_at,
        }
        if path.name in ("tickets.json", "inbox.json") and path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = []
            rows = existing if isinstance(existing, list) else existing.get("tickets") or [existing]
            rows.append(payload)
            path.write_text(json.dumps(rows), encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path
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


def _pick(row: dict, *keys: str) -> str:
    for key in keys:
        val = row.get(key)
        if val not in (None, ""):
            return str(val)
    return ""


def _item_from_row(row: dict, edition: str) -> dict | None:
    ticket_id = _pick(row, "id", "ticket_id")
    message = _pick(row, "message", "subject", "body", "text", "name")
    sender = _pick(row, "sender", "requester", "from_addr", "customer", "from")
    status = (_pick(row, "status") or "new").lower()
    if status in CLOSED:
        return None
    if not ticket_id and not message:
        return None
    return {
        "kind": "family_ticket",
        "id": ticket_id or message[:40],
        "name": (message or ticket_id)[:80],
        "message": message,
        "customer": sender or "Family",
        "sender": sender,
        "status": status or "new",
        "area": "family",
        "edition": _pick(row, "edition") or edition,
        "created_at": _pick(row, "created_at", "updated_at"),
        "isolated": True,
    }


def _read_sqlite(path: Path, edition: str) -> list[dict]:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        conn.row_factory = sqlite3.Row
        try:
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
        except sqlite3.Error:
            return []
        want = [t for t in TICKET_TABLES if t in tables]
        if not want:
            for table in tables:
                if table.startswith("sqlite_"):
                    continue
                try:
                    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
                except sqlite3.Error:
                    continue
                if cols & {"id", "ticket_id"} and cols & {
                    "message", "subject", "body", "text", "sender",
                }:
                    want.append(table)
        items: list[dict] = []
        for table in want:
            try:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            except sqlite3.Error:
                continue
            for raw in rows:
                item = _item_from_row(dict(raw), edition)
                if item:
                    items.append(item)
        return items
    finally:
        conn.close()


def _read_json(path: Path, edition: str) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows: list = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        if isinstance(data.get("tickets"), list):
            rows = data["tickets"]
        elif data.get("id") or data.get("message") or data.get("subject"):
            rows = [data]
    items: list[dict] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        item = _item_from_row(raw, edition)
        if item:
            items.append(item)
    return items


def _read_store(path: Path, edition: str) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix in {".json"}:
        return _read_json(path, edition)
    if suffix in {".db", ".sqlite", ".sqlite3"} or path.name in STORE_FILENAMES:
        return _read_sqlite(path, edition)
    return []


def list_open_tickets(
    editions: Iterable[str] | None = None,
    *,
    base: Path | None = None,
) -> list[dict]:
    allowed = set(process_family_editions())
    want = list(editions or allowed)
    findings: list[dict] = []
    root = base or inbox_base()
    seen_ids: set[str] = set()
    for edition in want:
        if edition not in allowed and allowed:
            continue
        if edition not in HELP_EDITIONS:
            continue
        for store_dir in _edition_store_dirs(edition, base=root):
            for path in _store_files(store_dir):
                try:
                    rows = _read_store(path, edition)
                except Exception:
                    continue
                for item in rows:
                    if is_test_family_ticket(item):
                        continue
                    key = str(item.get("id") or "")
                    if key and key in seen_ids:
                        continue
                    if key:
                        seen_ids.add(key)
                    findings.append(item)
    return findings
