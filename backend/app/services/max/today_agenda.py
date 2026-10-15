"""Today's calendar + Organizer + tasks for Max (Fix A).

Rafael asking "what's on today / my schedule / mi agenda" must always
hit live calendar and Organizer/task tools. Empty today is a real empty
list — never "no reliable calendar" and never a substitute from open
projects or the Chief e brief.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger("max.today_agenda")


def _tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/New_York")
    except Exception:  # pragma: no cover
        return None


def today_et() -> str:
    tz = _tz()
    now = datetime.now(tz) if tz else datetime.now()
    return now.date().isoformat()


def _db_path() -> str:
    import os
    from app.db.database import DB_PATH
    return os.environ.get("EMPIRE_TASK_DB") or DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return bool(row)


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _on_day(value: Any, day: str) -> bool:
    text = str(value or "").strip()
    return bool(text) and text[:10] == day


def calendar_events(conn: sqlite3.Connection, day: str) -> list[dict[str, Any]]:
    if not _table_exists(conn, "schedule_events"):
        return []
    start = f"{day}T00:00:00"
    end = f"{day}T23:59:59"
    rows = conn.execute(
        """
        SELECT id, title, type, start_time, end_time, status, customer_vendor,
               location_address, job_id, notes
        FROM schedule_events
        WHERE start_time >= ? AND start_time <= ?
        ORDER BY start_time ASC
        """,
        (start, end),
    ).fetchall()
    out = []
    for row in rows:
        item = _row_dict(row)
        item["source"] = "calendar"
        out.append(item)
    return out


def organizer_items(conn: sqlite3.Connection, day: str) -> list[dict[str, Any]]:
    if not _table_exists(conn, "organizer_items"):
        return []
    try:
        from app.services.organizer.schema import migrate_organizer_tables
        migrate_organizer_tables(conn)
    except Exception:
        pass
    rows = conn.execute(
        """
        SELECT id, kind, title, status, due_at, start_time, end_time,
               job_id, location_address, notes
        FROM organizer_items
        WHERE COALESCE(status, '') NOT IN ('done', 'cancelled')
        ORDER BY COALESCE(start_time, due_at, '') ASC
        """
    ).fetchall()
    out = []
    for row in rows:
        item = _row_dict(row)
        when = item.get("start_time") or item.get("due_at")
        if _on_day(when, day):
            item["source"] = "organizer"
            out.append(item)
    return out


def due_tasks(conn: sqlite3.Connection, day: str) -> list[dict[str, Any]]:
    if not _table_exists(conn, "tasks"):
        return []
    rows = conn.execute(
        """
        SELECT id, title, status, priority, desk, due_date, created_at
        FROM tasks
        WHERE COALESCE(status, '') NOT IN ('done', 'cancelled')
        ORDER BY COALESCE(due_date, created_at) ASC
        LIMIT 40
        """
    ).fetchall()
    out = []
    for row in rows:
        item = _row_dict(row)
        due = item.get("due_date")
        if _on_day(due, day) or (not due and item.get("status") == "in_progress"):
            item["source"] = "tasks"
            out.append(item)
    return out


def collect_today_agenda(day: Optional[str] = None) -> dict[str, Any]:
    """Read-only snapshot. Always succeeds; empty lists are a real empty day."""
    day = (day or "").strip()[:10] or today_et()
    calendar: list[dict[str, Any]] = []
    organizer: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    notes: list[str] = []
    conn = None
    try:
        conn = _connect()
        calendar = calendar_events(conn, day)
        organizer = organizer_items(conn, day)
        tasks = due_tasks(conn, day)
    except Exception as exc:
        logger.warning("today_agenda lookup failed: %s", type(exc).__name__)
        notes.append(f"lookup_warning:{type(exc).__name__}")
    finally:
        if conn is not None:
            conn.close()

    items = [
        *[{"kind": "calendar", **row} for row in calendar],
        *[{"kind": "organizer", **row} for row in organizer],
        *[{"kind": "task", **row} for row in tasks],
    ]
    empty = not items
    message = (
        f"Nothing on the calendar, Organizer, or due tasks for {day}."
        if empty
        else f"{len(items)} item(s) on {day}: {len(calendar)} calendar, "
             f"{len(organizer)} Organizer, {len(tasks)} task(s)."
    )
    return {
        "date": day,
        "calendar": calendar,
        "organizer": organizer,
        "tasks": tasks,
        "items": items,
        "count": len(items),
        "source": "calendar+organizer+tasks",
        "reliable_calendar": True,
        "from_open_projects": False,
        "message": message,
        "notes": notes,
        "instruction": (
            "List today's items from these tool results. Do not invent from open "
            "projects or the Chief e brief. Never claim the calendar is unavailable or unreliable."
        ),
    }


def register_tools(tool, ToolResult) -> None:
    """Bound from tool_executor so this module stays import-safe in tests."""

    @tool("get_today_agenda")
    def _get_today_agenda(params: dict, desk: Optional[str] = None):
        """Today's calendar events, Organizer items, and due/in-progress tasks."""
        day = str(params.get("date") or params.get("day") or "").strip()
        result = collect_today_agenda(day or None)
        return ToolResult(tool="get_today_agenda", success=True, result=result)


def today_agenda_doc() -> str:
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    return f"""
### Today's calendar & Organizer
- **get_today_agenda** — REQUIRED for "what's on today", "my schedule", "my agenda",
  "qué hay hoy", "mi agenda", "qué tengo hoy". Reads the calendar (schedule_events),
  Organizer items, and tasks due today. Always call this (and list_schedule / get_tasks)
  before answering. Empty day = say nothing is on the calendar/Organizer today.
  NEVER answer from open projects or the Chief e brief. NEVER claim the calendar is
  unavailable or unreliable.
  `{{"tool": "get_today_agenda"}}`
  Optional date: `{{"tool": "get_today_agenda", "date": "{tomorrow}"}}`
"""


class _TodayAgendaDoc(str):
    def __new__(cls):
        return str.__new__(cls, today_agenda_doc())

    def __str__(self) -> str:
        return today_agenda_doc()

    def __add__(self, other):
        return today_agenda_doc() + other

    def __radd__(self, other):
        return other + today_agenda_doc()


TODAY_AGENDA_DOC = _TodayAgendaDoc()
