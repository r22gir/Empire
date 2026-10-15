"""Today's agenda uses calendar + Organizer + tasks. Isolated DB only."""
from __future__ import annotations

import sqlite3

from app.services.max.today_agenda import (
    collect_today_agenda,
    is_today_agenda_ask,
    last_user_question,
    missed_the_point,
    prelookup_calls,
    prelookup_message,
    today_et,
)


def _tools(msg, history=None):
    return [c["tool"] for c in prelookup_calls(msg, history)]


def test_today_phrases_english_and_spanish_hit_calendar_and_organizer():
    for msg in (
        "what's on today",
        "What's on my schedule",
        "my agenda",
        "today's calendar",
        "qué hay hoy",
        "qué tengo hoy",
        "mi agenda",
        "qué hay en la agenda",
        "horario de hoy",
    ):
        tools = _tools(msg)
        assert tools[:3] == ["get_today_agenda", "list_schedule", "get_tasks"], msg


def test_brief_me_on_todays_jobs_is_not_the_calendar():
    tools = _tools("Morning Max, brief me on today's jobs")
    assert "get_today_agenda" not in tools


def test_whats_on_todays_jobs_goes_to_the_job_brief():
    tools = _tools("What's on today's jobs")
    assert "get_today_agenda" not in tools


def test_prelookup_message_does_not_use_open_projects_or_no_calendar():
    note = prelookup_message(
        "what's on today",
        [("get_today_agenda", "Result: 1 calendar item — session 10am")],
    )
    assert "unavailable or unreliable" in note.lower()
    assert "open projects" in note.lower()


def test_missed_the_point_retries_prior_tools_before_handoff():
    hist = [
        {"role": "user", "content": "what's on today"},
        {"role": "assistant", "content": "You have a few open projects."},
    ]
    for msg in (
        "you missed the point",
        "that's not what I asked",
        "eso no es lo que pregunté",
        "no es eso",
    ):
        tools = _tools(msg, hist)
        assert "get_today_agenda" in tools, msg
        assert "list_schedule" in tools, msg
    note = prelookup_message(
        "you missed the point",
        [("get_today_agenda", "calendar: session")],
        hist,
    )
    assert "hand off" in note.lower() or "Retry" in note or "retry" in note.lower()
    assert "Chief e" not in note


def test_missed_the_point_skips_prior_missed_the_point_turns():
    hist = [
        {"role": "user", "content": "what's on today"},
        {"role": "assistant", "content": "You have a few open projects."},
        {"role": "user", "content": "you missed the point"},
        {"role": "assistant", "content": "Sorry — here is the calendar."},
    ]
    assert last_user_question(hist, skip="you missed the point") == "what's on today"
    tools = _tools("you missed the point", hist)
    assert "get_today_agenda" in tools
    assert missed_the_point("eso no es lo que pregunté")
    assert is_today_agenda_ask("qué hay hoy")


def _seed_agenda_tables(path: str, day: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schedule_events (
            id TEXT PRIMARY KEY, type TEXT, title TEXT, start_time TEXT, end_time TEXT,
            status TEXT, customer_vendor TEXT, location_address TEXT, job_id TEXT,
            notes TEXT, created_by TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS organizer_items (
            id TEXT PRIMARY KEY, kind TEXT, title TEXT, status TEXT, due_at TEXT,
            start_time TEXT, end_time TEXT, job_id TEXT, location_address TEXT,
            notes TEXT, created_by TEXT
        )"""
    )
    conn.execute(
        """INSERT INTO schedule_events
           (id, type, title, start_time, status, created_by, notes)
           VALUES ('ev-today', 'session', 'Sesión Maxine 10am', ?, 'confirmed', 'manual',
                   'coaching')""",
        (f"{day}T10:00:00",),
    )
    conn.execute(
        """INSERT INTO tasks (id, title, status, priority, desk, due_date)
           VALUES ('t-today', 'Llamar al comprador', 'todo', 'normal', 'maxine', ?)""",
        (day,),
    )
    conn.execute(
        """INSERT INTO organizer_items (id, kind, title, due_at, status, created_by)
           VALUES ('org-today', 'todo', 'Preparar guía de hoy', ?, 'open', 'manual')""",
        (f"{day}T11:00:00",),
    )
    conn.commit()
    conn.close()


def test_get_today_agenda_lists_seeded_items_not_open_projects(isolated_empire_db):
    day = today_et()
    _seed_agenda_tables(isolated_empire_db, day)
    data = collect_today_agenda(day)
    assert data["reliable_calendar"] is True
    assert data["from_open_projects"] is False
    assert "no reliable calendar" not in data["message"].lower()
    titles = " ".join(
        str(row.get("title") or "")
        for row in data["calendar"] + data["organizer"] + data["tasks"]
    )
    assert "Sesión Maxine 10am" in titles
    assert "Preparar guía" in titles
    assert "comprador" in titles
    assert data["count"] >= 3


def test_organizer_lookup_does_not_migrate(isolated_empire_db, monkeypatch):
    """Family agenda is read-only sqlite. It never migrates Organizer schema."""
    import inspect

    from app.services.max import today_agenda as ta

    src = inspect.getsource(ta)
    assert "migrate_organizer" not in src
    assert "mode=ro" in inspect.getsource(ta._connect)

    connects = []
    orig = ta.sqlite3.connect

    def wrap(*a, **k):
        connects.append((a, k))
        return orig(*a, **k)

    monkeypatch.setattr(ta.sqlite3, "connect", wrap)
    collect_today_agenda(today_et())
    assert connects
    assert any("mode=ro" in str(a) + str(k) for a, k in connects)


def test_empty_today_is_empty_not_open_projects(isolated_empire_db):
    data = collect_today_agenda("2099-01-01")
    assert data["count"] == 0
    assert data["reliable_calendar"] is True
    assert "Nothing on the calendar" in data["message"]
    assert "open project" not in data["message"].lower()
