"""Today's calendar + Organizer + tasks for Maxine (family Maxine).

Camilo asking "what's on today / my schedule / mi agenda" must always
hit live calendar and Organizer/task tools. Empty today is a real empty
list — never "no reliable calendar" and never a substitute from open
projects. A missed-the-point reply retries those tools instead of
handing off.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger("max.today_agenda")

_TODAY_AGENDA = re.compile(
    r"(?:"
    r"(?:what'?s|what\s+is|whats)\s+(?:on\s+)?(?:for\s+)?(?:today|my\s+(?:schedule|agenda|calendar|day)|the\s+calendar)|"
    r"(?:my|today'?s|the)\s+(?:schedule|agenda|calendar)(?:\s+today|\s+for\s+today)?|"
    r"(?:show|list|check|see)\s+(?:me\s+)?(?:my\s+)?(?:today'?s\s+)?(?:schedule|agenda|calendar)|"
    r"what do i have (?:on\s+)?today|"
    r"my\s+day\b|"
    r"qu[eé]\s+(?:hay|tengo)\s+(?:hoy|para\s+hoy)|"
    r"qu[eé]\s+hay\s+en\s+(?:la\s+|el\s+)?(?:agenda|calendario|horario)|"
    r"(?:mi|la)\s+(?:agenda|horario|calendario)(?:\s+de\s+hoy)?|"
    r"agenda\s+de\s+hoy|horario\s+de\s+hoy|calendario\s+de\s+hoy"
    r")",
    re.I,
)
_BRIEF = re.compile(
    r"(?i)(?:brief\s+me|rundown|what'?s\s+on\s+(?:my\s+plate|today'?s\s+jobs)|today'?s\s+jobs|"
    r"res[uú]men\s+de\s+(?:hoy|trabajos)|qu[eé]\s+hay\s+en\s+los\s+trabajos)",
)
_MISSED_POINT = re.compile(
    r"(?:"
    r"missed the point|missed (?:it|that)|not what i (?:asked|said|meant)|"
    r"that(?:'s| is) not (?:it|what|the point)|you missed|"
    r"eso no (?:es|era)(?:\s+lo que)?|no (?:es|era) (?:eso|lo que)|"
    r"no (?:entendiste|captaste)|te (?:fuiste|desviaste)|"
    r"no toca(?:s)?(?:\s+el\s+(?:tema|punto))?|no es el punto|no era eso|"
    r"perdiste el punto"
    r")",
    re.I,
)


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
    """Read-only. Never migrate or write the Organizer / task schema."""
    import os
    path = os.path.abspath(_db_path())
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
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
            "projects. Never claim the calendar is unavailable or unreliable."
        ),
    }


def is_today_agenda_ask(message: Optional[str]) -> bool:
    """True for schedule/agenda/what's-on-today (EN + ES). Not 'what's on today's jobs'."""
    t = message or ""
    if _BRIEF.search(t):
        return False
    return bool(_TODAY_AGENDA.search(t))


def missed_the_point(message: Optional[str]) -> bool:
    """Owner saying the previous answer missed. Retry tools; do not hand off."""
    raw = (message or "").strip()
    if not raw or len(raw) > 280:
        return False
    return bool(_MISSED_POINT.search(raw))


def last_user_question(history: Any, *, skip: Optional[str] = None) -> str:
    """Most recent prior user turn that is not itself a 'missed the point' line."""
    skip_norm = (skip or "").strip()
    for h in reversed(list(history or [])):
        role = h.get("role") if isinstance(h, dict) else getattr(h, "role", "")
        if role != "user":
            continue
        c = h.get("content") if isinstance(h, dict) else getattr(h, "content", "")
        text = str(c or "").strip()
        if not text:
            continue
        if skip_norm and text == skip_norm:
            continue
        if missed_the_point(text):
            continue
        return text
    return ""


def _today_agenda_calls() -> list[dict]:
    try:
        day = today_et()
    except Exception:
        from datetime import date
        day = date.today().isoformat()
    return [
        {"tool": "get_today_agenda", "date": day},
        {"tool": "list_schedule", "start_date": f"{day}T00:00:00", "end_date": f"{day}T23:59:59"},
        {"tool": "get_tasks", "limit": 15},
    ]


def prelookup_calls(message: Optional[str], history: Any = None, _retry_depth: int = 0) -> list[dict]:
    """Tool calls to run before the model sees a today/agenda or missed-the-point turn."""
    t = (message or "").strip()
    if not t:
        return []
    if _retry_depth == 0 and missed_the_point(t):
        prior = last_user_question(history, skip=t)
        retried = prelookup_calls(prior, history, _retry_depth=1) if prior else []
        if not retried:
            retried = _today_agenda_calls()
        return retried
    if is_today_agenda_ask(t):
        return _today_agenda_calls()
    return []


def prelookup_message(message: Optional[str], results: list[tuple[str, str]], history: Any = None) -> str:
    """System note with the pre-lookup results. results: [(tool, rendered result)]."""
    if not results:
        return ""
    parts = [
        "Looked up before you answer (real results from this instance; use them, "
        "do not say you still need to look):"
    ]
    for tool, body in results:
        parts.append(f"[{tool}] {body}")
    rules = [
        "Answer short, but keep the key facts from these results.",
    ]
    if is_today_agenda_ask(message or "") or any(tool == "get_today_agenda" for tool, _body in results):
        rules.append(
            "This is today's schedule/agenda. List the calendar, Organizer and task items from "
            "the tool results. Do not answer from open projects. "
            "Never claim the calendar is unavailable or unreliable."
        )
    if missed_the_point(message):
        rules.append(
            "The owner said the previous answer missed the point. Retry from these tool results. "
            "Do not hand off. Use the tools again."
        )
    parts.append(" ".join(rules))
    return "\n\n".join(parts)


def list_schedule_range(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Read-only calendar slice. Empty if the schedule table is missing."""
    conn = None
    try:
        conn = _connect()
        if not _table_exists(conn, "schedule_events"):
            return []
        rows = conn.execute(
            """
            SELECT id, title, type, start_time, end_time, status, customer_vendor,
                   location_address, job_id, notes
            FROM schedule_events
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time ASC
            """,
            (start_date, end_date),
        ).fetchall()
        return [_row_dict(row) for row in rows]
    except Exception as exc:
        logger.warning("list_schedule lookup failed: %s", type(exc).__name__)
        return []
    finally:
        if conn is not None:
            conn.close()


def register_tools(tool, ToolResult) -> None:
    """Bound from tool_executor so this module stays import-safe in tests."""

    @tool("get_today_agenda")
    def _get_today_agenda(params: dict, desk: Optional[str] = None):
        """Today's calendar events, Organizer items, and due/in-progress tasks."""
        day = str(params.get("date") or params.get("day") or "").strip()
        result = collect_today_agenda(day or None)
        return ToolResult(tool="get_today_agenda", success=True, result=result)

    @tool("list_schedule")
    def _list_schedule(params: dict, desk: Optional[str] = None):
        """Calendar events in a date range. For today, prefer get_today_agenda."""
        day = today_et()
        start = str(params.get("start_date") or f"{day}T00:00:00").strip()
        end = str(params.get("end_date") or f"{day}T23:59:59").strip()
        rows = list_schedule_range(start, end)
        return ToolResult(
            tool="list_schedule",
            success=True,
            result={"events": rows, "count": len(rows), "start_date": start, "end_date": end},
        )


def today_agenda_doc() -> str:
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    return f"""
### Agenda de hoy
- **get_today_agenda** — OBLIGATORIO para "what's on today", "my schedule", "my agenda",
  "qué hay hoy", "mi agenda", "qué tengo hoy". Lee el calendario (schedule_events),
  Organizer y tareas de hoy. Siempre llama esto (y list_schedule / get_tasks)
  antes de responder. Día vacío = di que no hay nada en el calendario/Organizer hoy.
  NUNCA respondas desde proyectos abiertos. NUNCA digas que el calendario no está
  disponible o no es confiable.
  `{{"tool": "get_today_agenda"}}`
  Fecha opcional: `{{"tool": "get_today_agenda", "date": "{tomorrow}"}}`
- Si el dueño dice que no era eso / missed the point, vuelve a llamar las
  herramientas de la pregunta anterior. No pases a nadie más.
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
