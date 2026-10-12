"""Inbox unreviewed count, HTML stripping, overdue query (desk not desk_id)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.services.data_paths import inbox_dir
from app.services.max.channel_text import for_channel, strip_telegram_html
from app.services.max.desks.live_data import count_unreviewed_inbox, list_unreviewed_inbox, query_overdue_tasks
from app.services.max.monitor import MaxMonitor


def _write_inbox(items: list[dict]) -> Path:
    root = inbox_dir()
    root.mkdir(parents=True, exist_ok=True)
    for item in items:
        (root / f"{item['id']}.json").write_text(json.dumps(item), encoding="utf-8")
    return root


def test_inbox_counts_only_unreviewed(isolated_empire_db, tmp_path, monkeypatch):
    root = inbox_dir()
    # Wipe any leftover files from other tests in this session tmp tree
    if root.exists():
        for f in root.glob("*.json"):
            f.unlink()
    _write_inbox([
        {"id": "old-1", "status": "reviewed", "text": "Mar telegram", "source": "telegram"},
        {"id": "old-2", "status": "reviewed", "text": "Jun telegram", "source": "telegram"},
        {"id": "new-1", "status": "received", "text": "Need fabric", "source": "telegram"},
        {"id": "new-2", "status": "done", "text": "already handled", "source": "email"},
    ])
    assert count_unreviewed_inbox() == 1
    items = list_unreviewed_inbox()
    assert items[0]["id"] == "new-1"

    monitor = MaxMonitor()
    # 1 unreviewed < 15 → no alert
    assert monitor._check_inbox() is None
    for i in range(16):
        _write_inbox([{"id": f"p-{i}", "status": "received", "text": f"item {i}"}])
    alert = monitor._check_inbox()
    assert alert is not None
    assert "unreviewed" in alert
    assert "<b>" in alert  # telegram-shaped; app strips separately


def test_html_stripped_for_app_kept_for_telegram():
    raw = "\n📥 <b>194 inbox items</b> piling up — review when you can"
    assert "<b>" not in strip_telegram_html(raw)
    assert "194 inbox items" in strip_telegram_html(raw)
    assert "<b>" in for_channel(raw, "telegram")
    assert "<b>" not in for_channel(raw, "app")
    assert "**194 inbox items**" in for_channel(raw, "markdown")


def test_notify_founder_stores_plain_and_history(isolated_empire_db):
    from app.routers.notifications import notify_founder, notifications_db
    from app.db.database import get_db

    notifications_db.clear()
    entry = notify_founder(
        "System", "system_alert", "Monitor Check",
        "\n📥 <b>16 unreviewed inbox items</b>",
        "low",
    )
    assert "<b>" not in entry["message"]
    assert "16 unreviewed" in entry["message"]
    with get_db() as conn:
        row = conn.execute(
            "SELECT message, message_plain FROM founder_notifications WHERE id = ?",
            (entry["id"],),
        ).fetchone()
        assert row is not None
        assert "16 unreviewed" in (row[1] or row[0] or "")


def test_overdue_query_uses_desk_column(isolated_empire_db):
    import asyncio
    from app.db.database import get_db

    now = datetime(2026, 10, 12)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, due_date, created_at)
               VALUES ('t-over', 'Cut lining', '', 'todo', 'normal', 'forge', ?, ?)""",
            ((now - timedelta(days=3)).strftime("%Y-%m-%d"), now.isoformat()),
        )
        rows = query_overdue_tasks(conn, now)
    assert rows
    assert rows[0]["name"] == "Cut lining"
    assert rows[0]["desk"] == "forge"

    monitor = MaxMonitor()
    alert = asyncio.run(monitor._check_overdue_tasks())
    assert alert is not None
    assert "Cut lining" in alert
    assert "[forge]" in alert
