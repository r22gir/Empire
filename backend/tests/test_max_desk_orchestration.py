"""Behavior tests for Max-as-chief-of-staff desk orchestration."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.services.max.desks.desk_registry import DESK_ROSTER, live_desk_count, roster_prompt_block
from app.services.max.desks.delegate_first import classify_request, create_tracked_task
from app.services.max.desks.desk_review import looks_like_template, mark_draft_only, review_desk_output
from app.services.max.desks.desk_sweeper import format_digest, sweep_once
from app.services.max.desks.task_lifecycle import (
    ALLOWED_STATUSES,
    migrate_task_status_constraint,
    record_timeout_retry,
)
from app.services.max.desks import founder_inbox
from app.services.max.improvements import approval_deep_link, INCLUDED_MODEL
from app.services.max.answer_policy import wants_document_search, prelookup_calls


OLD_TASKS_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo', 'in_progress', 'waiting', 'done', 'cancelled')),
    priority TEXT NOT NULL DEFAULT 'normal',
    desk TEXT NOT NULL,
    created_by TEXT DEFAULT 'founder',
    metadata TEXT,
    result_summary TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);
"""


def _prep_tasks(conn):
    conn.execute("DROP TABLE IF EXISTS tasks")
    conn.executescript(OLD_TASKS_SQL)
    migrate_task_status_constraint(conn)
    founder_inbox.ensure_schema(conn)
    conn.commit()


@pytest.fixture
def tasks_db(isolated_empire_db):
    conn = sqlite3.connect(isolated_empire_db)
    conn.row_factory = sqlite3.Row
    _prep_tasks(conn)
    yield conn
    conn.close()


# ── roster / prompt ──────────────────────────────────────────────────

def test_live_desk_count_is_seventeen():
    assert live_desk_count() == 17
    assert len(DESK_ROSTER) == 17
    ids = [d["id"] for d in DESK_ROSTER]
    assert "analytics" in ids and "quality" in ids and "intake" in ids
    assert "costtracker" not in ids
    text = roster_prompt_block()
    assert "18" not in text.split("DESK SYSTEM")[1][:80]
    assert "17 DESKS" in text
    assert "OpenClaw" in text and "Never delegate to OpenClaw" in text
    assert "pick desk" in text.lower() or "Pick the owning desk" in text


# ── routing cases ────────────────────────────────────────────────────

@pytest.mark.parametrize("msg,desk", [
    ("Pull today's analytics metrics and forecast", "analytics"),
    ("Run the AI quality audit and accuracy report", "quality"),
    ("New LuxeForge intake submission just arrived", "intake"),
    ("Draft an Instagram post for the workroom", "marketing"),
    ("Check overdue invoices and P&L", "finance"),
])
def test_classify_routes_desk_work(msg, desk):
    d = classify_request(msg)
    assert d.action == "delegate"
    assert d.desk_id == desk
    assert d.method == "rule"


def test_classify_answers_orchestration_and_lookups():
    assert classify_request("How many desks do you have?").answers_directly
    assert classify_request("What's the status of the desks?").answers_directly
    assert classify_request("What's the latest quote for Dahlia?").answers_directly
    assert classify_request("hi").answers_directly
    assert classify_request("give me a link here please").answers_directly


def test_classify_approval_gate_does_not_send():
    d = classify_request("Email the client this invoice and charge the card")
    assert d.action == "approval"
    assert d.approval_required is True


def test_classify_honors_specified_desk():
    d = classify_request("whatever", specified_desk="quality")
    assert d.desk_id == "quality" and d.method == "specified"


# ── status persistence ───────────────────────────────────────────────

def test_failed_and_escalated_persist(tasks_db):
    conn = tasks_db
    conn.execute(
        "INSERT INTO tasks (id, title, status, desk) VALUES ('a','t','failed','analytics')"
    )
    conn.execute(
        "INSERT INTO tasks (id, title, status, desk) VALUES ('b','t','escalated','unassigned')"
    )
    conn.commit()
    rows = {r["id"]: r["status"] for r in conn.execute("SELECT id, status FROM tasks")}
    assert rows["a"] == "failed"
    assert rows["b"] == "escalated"
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='tasks'").fetchone()[0]
    assert "'failed'" in sql and "'escalated'" in sql
    assert set(ALLOWED_STATUSES) >= {"failed", "escalated", "todo", "done"}


def test_founder_inbox_persists(tasks_db):
    founder_inbox.add(task_id="inbox1", title="Unrouted", reason="no desk matched")
    rows = founder_inbox.list_open()
    assert any(r["id"] == "inbox1" for r in rows)
    assert founder_inbox.count_open() >= 1
    founder_inbox.resolve("inbox1")
    assert not any(r["id"] == "inbox1" for r in founder_inbox.list_open())


def test_create_tracked_task_writes_status(tasks_db):
    task = create_tracked_task(
        title="Daily metrics",
        description="Pull today's analytics metrics and forecast",
        desk_id="analytics",
    )
    row = tasks_db.execute("SELECT * FROM tasks WHERE id=?", (task["id"],)).fetchone()
    assert row["desk"] == "analytics"
    assert row["status"] == "todo"
    assert row["created_by"] == "max"


# ── retry cap ────────────────────────────────────────────────────────

def test_retry_cap_with_backoff(tasks_db):
    conn = tasks_db
    conn.execute(
        "INSERT INTO tasks (id, title, status, desk, retry_count, max_retries) "
        "VALUES ('r1','stale','todo','it', 0, 3)"
    )
    conn.commit()
    first = record_timeout_retry(conn, "r1")
    assert first["status"] == "todo" and first["retry_count"] == 1 and not first["capped"]
    assert first["next_retry_at"]
    second = record_timeout_retry(conn, "r1")
    third = record_timeout_retry(conn, "r1")
    assert second["retry_count"] == 2 and third["retry_count"] == 3
    capped = record_timeout_retry(conn, "r1")
    assert capped["capped"] is True
    assert capped["status"] == "failed"
    status = conn.execute("SELECT status, retry_count FROM tasks WHERE id='r1'").fetchone()
    assert status["status"] == "failed"


# ── sweeper ──────────────────────────────────────────────────────────

def test_sweeper_lists_open_tasks_and_digest(tasks_db):
    conn = tasks_db
    old = (datetime.utcnow() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO tasks (id, title, status, desk, updated_at, created_at) "
        "VALUES ('s1','Waiting on tap','waiting','finance', ?, ?)",
        (old, old),
    )
    conn.execute(
        "INSERT INTO tasks (id, title, status, desk, updated_at, created_at) "
        "VALUES ('s2','Stuck work','in_progress','marketing', ?, ?)",
        (old, old),
    )
    conn.commit()
    founder_inbox.add(task_id="s3", title="Inbox item", reason="assign a desk")
    summary = sweep_once()
    assert summary["open"] >= 2
    assert summary["stale_waiting"] >= 1
    assert summary["stale_in_progress"] >= 1
    text = format_digest(summary)
    assert "Daily desk digest" in text
    assert "s1" in text or "Waiting on tap" in text
    assert "next:" in text


# ── review / draft only ──────────────────────────────────────────────

def test_template_output_is_draft_only():
    assert looks_like_template("Post drafted for Instagram. Suggested hashtags: #a")
    assert looks_like_template("")
    marked = mark_draft_only("Post drafted for Instagram. Suggested hashtags: #a")
    assert marked.lower().startswith("draft only")


def test_review_marks_template_without_calling_ollama():
    import asyncio
    with patch("app.services.max.desks.desk_review._second_pass", new_callable=AsyncMock) as spy:
        out = asyncio.run(review_desk_output(
            original_request="Draft a specific Instagram caption about the Willard install",
            desk_id="marketing",
            result_text="Post drafted for Instagram. Suggested hashtags: #drapes",
        ))
        spy.assert_not_called()
    assert out["verdict"] == "draft_only"
    assert out["report"].lower().startswith("draft only")


# ── deep link ────────────────────────────────────────────────────────

def test_improvement_deep_link_stable():
    url = approval_deep_link(9)
    assert url.endswith("?screen=improvements&id=9")
    assert "screen=improvements" in url
    assert INCLUDED_MODEL == "grok-4.6"
    from app.services.max.improvements import _row
    # _row is for sqlite rows; check create_request shape via helper
    assert approval_deep_link("12") == approval_deep_link(12)


# ── document search gate (PR #105 coordination) ──────────────────────

def test_give_me_a_link_does_not_document_search():
    assert wants_document_search("give me a link here") is False
    assert wants_document_search("there are no links") is False
    assert "find_files" not in [c["tool"] for c in prelookup_calls("give me a link here")]


def test_show_me_docs_still_searches():
    assert wants_document_search("show me wall unit led docs") is True
    assert "find_files" in [c["tool"] for c in prelookup_calls("Find the Willard addendum PDF")]
