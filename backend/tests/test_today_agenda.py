"""Fix A: what's on today uses calendar + Organizer + tasks. Isolated DB only."""
from __future__ import annotations

import sqlite3

from app.services.max import answer_policy as ap
from app.services.max.today_agenda import collect_today_agenda, today_et


def _tools(msg, history=None):
    return [c["tool"] for c in ap.prelookup_calls(msg, history)]


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
        "Resúmeme el día",
        "resumeme el dia",
        "summarize the day",
    ):
        tools = _tools(msg)
        assert tools[:3] == ["get_today_agenda", "list_schedule", "get_tasks"], msg


def test_brief_me_on_todays_jobs_is_not_the_calendar():
    tools = _tools("Morning Max, brief me on today's jobs")
    assert "get_tasks" in tools
    assert "get_today_agenda" not in tools


def test_whats_on_todays_jobs_goes_to_the_job_brief():
    tools = _tools("What's on today's jobs")
    assert "get_today_agenda" not in tools
    assert "get_tasks" in tools


def test_prelookup_message_does_not_use_open_projects_or_no_calendar():
    note = ap.prelookup_message(
        "what's on today",
        [("get_today_agenda", "Result: 1 calendar item — Marley install 26 3/4\" seat")],
    )
    assert "unavailable or unreliable" in note.lower()
    assert "open projects" in note.lower()


def test_missed_the_point_retries_prior_tools_before_chief_e():
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
    note = ap.prelookup_message(
        "you missed the point",
        [("get_today_agenda", "calendar: Marley install")],
        hist,
    )
    assert "Chief e" in note
    assert "retry" in note.lower() or "Retry" in note


def test_missed_the_point_skips_prior_missed_the_point_turns():
    hist = [
        {"role": "user", "content": "what's on today"},
        {"role": "assistant", "content": "You have a few open projects."},
        {"role": "user", "content": "you missed the point"},
        {"role": "assistant", "content": "Sorry — here is the calendar."},
    ]
    assert ap.last_user_question(hist, skip="you missed the point") == "what's on today"
    tools = _tools("you missed the point", hist)
    assert "get_today_agenda" in tools


def test_get_today_agenda_lists_seeded_items_not_open_projects(isolated_empire_db):
    day = today_et()
    conn = sqlite3.connect(isolated_empire_db)
    conn.execute(
        """INSERT INTO schedule_events
           (id, type, title, start_time, status, created_by, notes)
           VALUES ('ev-today', 'install', 'Marley seat 26 3/4 in', ?, 'confirmed', 'manual',
                   'back 26 3/4\" · 12\" channels')""",
        (f"{day}T09:00:00",),
    )
    conn.execute(
        """INSERT INTO tasks (id, title, status, priority, desk, due_date)
           VALUES ('t-today', 'Call Whittington about 12\" foam', 'todo', 'normal', 'forge', ?)""",
        (day,),
    )
    conn.commit()
    from app.services.organizer.schema import migrate_organizer_tables
    migrate_organizer_tables(conn)
    conn.execute(
        """INSERT INTO organizer_items (id, kind, title, due_at, status, created_by)
           VALUES ('org-today', 'todo', 'Pick up 2 1/2\" welt cord', ?, 'open', 'manual')""",
        (f"{day}T11:00:00",),
    )
    conn.commit()
    conn.close()

    data = collect_today_agenda(day)
    assert data["reliable_calendar"] is True
    assert data["from_open_projects"] is False
    assert "no reliable calendar" not in data["message"].lower()
    titles = " ".join(
        str(row.get("title") or "")
        for row in data["calendar"] + data["organizer"] + data["tasks"]
    )
    assert "Marley seat 26 3/4" in titles
    assert "welt cord" in titles
    assert "12\" foam" in titles
    assert data["count"] >= 3


def test_organizer_lookup_does_not_migrate(isolated_empire_db, monkeypatch):
    called = []

    def boom(*a, **k):
        called.append(True)
        raise AssertionError("migrate_organizer_tables must not run")

    monkeypatch.setattr("app.services.organizer.schema.migrate_organizer_tables", boom)
    collect_today_agenda(today_et())
    assert called == []


def test_empty_today_is_empty_not_open_projects(isolated_empire_db):
    data = collect_today_agenda("2099-01-01")
    assert data["count"] == 0
    assert data["reliable_calendar"] is True
    assert "Nothing on the calendar" in data["message"]
    assert "open project" not in data["message"].lower()
