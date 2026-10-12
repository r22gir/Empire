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


def test_brief_never_uses_empire_repo_path(seeded_db, monkeypatch):
    """Quotes/inbox/reports resolve through EMPIRE_DATA_DIR, not ~/empire-repo."""
    from app.services import data_paths

    assert "empire-repo" not in str(data_paths.quotes_data_dir())
    assert "empire-repo" not in str(data_paths.inbox_dir())
    payload = build_and_persist_brief(now=seeded_db)
    assert payload["sections"]["quotes"]
