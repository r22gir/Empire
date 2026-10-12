"""ONE daily brief from the DB, with sections, diff, and history."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.db.max_ops_schema import ensure_max_ops_schema
from app.services.max.daily_brief import (
    SECTION_KEYS,
    build_and_persist_brief,
    build_brief_sections,
    latest_brief,
    persist_brief,
    render_brief_plain,
)
from app.services.max.desks.live_data import snapshot
from tests.test_desk_live_jobs import _seed


@pytest.fixture
def seeded_db(isolated_empire_db):
    now = datetime(2026, 10, 12, 8, 0, 0)
    from app.db.database import get_db

    with get_db() as conn:
        _seed(conn, now)
    return now


def test_brief_has_required_sections(seeded_db):
    snap = snapshot(seeded_db)
    sections = build_brief_sections(snap, now=seeded_db, service_rows=[
        {"id": "empire-backend", "name": "empire-backend", "up": True, "detail": "port 8000 UP"},
        {"id": "disk", "name": "disk", "up": True, "pct": 40, "detail": "40% used"},
    ])
    for key in SECTION_KEYS:
        assert key in sections
        assert sections[key]["title"]
        assert sections[key]["text"]
    text = render_brief_plain(sections, seeded_db)
    assert "INV-2044" in text
    assert "EST-2026-088" in text
    assert "Nelma Rivera" in text
    assert "Fabric question" in text
    assert "School pickup tomorrow" in text or "Family" in text
    assert "Today and this week" in text
    assert "Money" in text
    assert "Watch list" in text


def test_brief_diff_marks_new_items(seeded_db):
    snap = snapshot(seeded_db)
    first = build_brief_sections(snap, now=seeded_db, service_rows=[])
    persist_brief(first, now=seeded_db - timedelta(days=1))
    # Add a new payment-like invoice name by rebuilding with previous
    previous = first
    second = build_brief_sections(snap, previous=previous, now=seeded_db, service_rows=[])
    # Same snapshot → no NEW flags
    assert " NEW" not in second["quotes"]["text"]
    # Pretend yesterday had no quotes
    previous["quote_items"] = []
    previous["quotes"] = {"items": []}
    changed = build_brief_sections(snap, previous=previous, now=seeded_db, service_rows=[])
    assert "NEW" in changed["quotes"]["text"]
    assert changed["quotes"]["new_count"] >= 1


def test_brief_persists_history(seeded_db):
    first = build_and_persist_brief(now=seeded_db - timedelta(days=1))
    second = build_and_persist_brief(now=seeded_db)
    assert first["id"] != second["id"]
    assert second["previous_brief_id"] == first["id"]
    latest = latest_brief()
    assert latest["id"] == second["id"]
    assert latest["sections"]
    from app.db.database import get_db
    with get_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM daily_briefs").fetchone()[0]
        assert n == 2


def test_sample_brief_render_from_fixtures(seeded_db, tmp_path):
    """Keep a rendered sample so reviewers can see the brief shape."""
    from app.services.max.daily_brief import build_brief_sections, render_brief_plain
    from app.services.max.desks.live_data import snapshot

    sections = build_brief_sections(
        snapshot(seeded_db),
        now=seeded_db,
        service_rows=[
            {"id": "empire-backend", "name": "empire-backend", "up": True, "detail": "port 8000 UP"},
            {"id": "disk", "name": "disk", "up": True, "pct": 41, "detail": "41% used, 200 GB free"},
        ],
    )
    text = render_brief_plain(sections, seeded_db)
    sample = tmp_path / "sample_brief.txt"
    sample.write_text(text, encoding="utf-8")
    assert "INV-2044" in text
    assert "EST-2026-088" in text
    print("\n===== SAMPLE BRIEF =====\n" + text + "\n===== END SAMPLE =====\n")


def test_brief_never_uses_empire_repo_path(seeded_db, monkeypatch):
    """Quotes/inbox/reports resolve through EMPIRE_DATA_DIR, not ~/empire-repo."""
    from app.services import data_paths

    assert "empire-repo" not in str(data_paths.quotes_data_dir())
    assert "empire-repo" not in str(data_paths.inbox_dir())
    payload = build_and_persist_brief(now=seeded_db)
    assert payload["sections"]["quotes"]


def test_brief_mail_from_organizer_gmail_and_outlook(seeded_db):
    """Unanswered mail section reads Organizer Gmail+Outlook (read-only)."""
    import app.services.organizer.mail as mailmod

    mailmod.TEST_INBOX = [
        {
            "source": "gmail",
            "message_id": "gm-88",
            "from": "Marley <marley@example.com>",
            "subject": "Install date?",
            "date": "2026-10-11T12:00:00",
            "preview": "Can we move the drapery install?",
            "unread": True,
            "account": "gmail",
        },
        {
            "source": "outlook",
            "message_id": "ol-22",
            "from": "School Office <office@school.edu>",
            "subject": "Permission slip",
            "date": "2026-10-10T09:00:00",
            "preview": "Please sign for the field trip.",
            "unread": False,
            "account": "outlook",
        },
    ]
    try:
        text = render_brief_plain(build_brief_sections(snapshot(seeded_db), now=seeded_db, service_rows=[]), seeded_db)
        assert "Install date?" in text
        assert "Permission slip" in text
        assert "Marley" in text
        snap = snapshot(seeded_db)
        assert all(m.get("sent") is False or m.get("sent") is None for m in snap["pending_mail"])
    finally:
        mailmod.TEST_INBOX = None


def test_brief_family_from_help_store(seeded_db):
    """Family section reads /data/family-help/<ed>/help.db (temp store in tests)."""
    from app.services.max.desks.family_help_store import inbox_base, write_ticket_for_tests

    base = inbox_base()
    assert "family-help" in str(base)
    resolved = str(base.resolve())
    assert not resolved.startswith("/data/family-help")
    assert not resolved.startswith("/data/amp")
    assert not resolved.startswith("/data/maxine")
    write_ticket_for_tests(
        edition="amp",
        ticket_id="fh-amp-1",
        sender="Amp",
        message="Need a ride to practice",
        created_at=seeded_db.isoformat(),
        base=base,
    )
    write_ticket_for_tests(
        edition="maxine",
        ticket_id="fh-max-1",
        sender="Maxine",
        message="Help with homework",
        created_at=seeded_db.isoformat(),
        base=base,
    )
    sections = build_brief_sections(snapshot(seeded_db), now=seeded_db, service_rows=[])
    text = sections["other_areas"]["text"]
    assert "Need a ride to practice" in text
    assert "Help with homework" in text
    assert "Max-e" in text
    assert "Maxine" in text
    assert "Family:" in text


def test_brief_other_areas_from_organizer_items(seeded_db):
    from app.db.database import get_db
    from app.services.organizer.store import insert_item

    with get_db() as conn:
        insert_item(conn, {"kind": "todo", "title": "LLC filing follow-up", "space_id": "ventures"})
        insert_item(conn, {"kind": "appointment", "title": "Dentist Thursday", "space_id": "personal",
                           "start_time": (seeded_db + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")})
        insert_item(conn, {"kind": "todo", "title": "Empire hosting invoice", "space_id": "empire"})
        insert_item(conn, {"kind": "todo", "title": "Cut lining", "space_id": "workroom"})
    sections = build_brief_sections(snapshot(seeded_db), now=seeded_db, service_rows=[])
    text = sections["other_areas"]["text"]
    assert "LLC filing follow-up" in text
    assert "Dentist Thursday" in text
    assert "Empire hosting invoice" in text
    assert "Cut lining" not in text  # Workroom is not Other


def test_brief_today_includes_schedule_events_and_organizer(seeded_db):
    """Today already reads schedule_events; also include Organizer items due today."""
    from app.db.database import get_db
    from app.services.organizer.store import insert_item

    with get_db() as conn:
        insert_item(conn, {
            "kind": "appointment",
            "title": "Personal errand noon",
            "space_id": "personal",
            "start_time": seeded_db.replace(hour=12, minute=0).strftime("%Y-%m-%d %H:%M:%S"),
        })
    snap = snapshot(seeded_db)
    names = [i.get("name") for i in snap["schedule_today"]]
    assert "Nelma install" in names
    assert any(i.get("source") == "schedule_events" for i in snap["schedule_today"])
    assert "Personal errand noon" in names
    text = render_brief_plain(build_brief_sections(snap, now=seeded_db, service_rows=[]), seeded_db)
    assert "Nelma install" in text
    assert "Personal errand noon" in text


def test_family_store_isolates_editions(seeded_db, monkeypatch):
    from app.services.max.desks.family_help_store import (
        inbox_base, list_open_tickets, write_ticket_for_tests,
    )

    base = inbox_base()
    write_ticket_for_tests(
        edition="amp", ticket_id="fh-amp-only", sender="Amp",
        message="Amp only ticket", created_at=seeded_db.isoformat(), base=base,
    )
    write_ticket_for_tests(
        edition="maxine", ticket_id="fh-max-only", sender="Maxine",
        message="Maxine only ticket", created_at=seeded_db.isoformat(), base=base,
    )
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    mine = list_open_tickets(base=base)
    assert any(t["id"] == "fh-max-only" for t in mine)
    assert not any(t["id"] == "fh-amp-only" for t in mine)
