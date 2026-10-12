"""Schema for Max ops persistence: desk jobs, briefs, notifications, orchestrator.

Idempotent CREATE IF NOT EXISTS. Safe to call on every startup and from tests.
"""
from __future__ import annotations

import sqlite3

MAX_OPS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS desk_job_results (
    id TEXT PRIMARY KEY,
    desk_id TEXT NOT NULL,
    job_key TEXT NOT NULL,
    job_title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('done', 'failed', 'retried')),
    findings_json TEXT,
    result_text TEXT,
    fail_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    executed_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_desk_job_results_desk ON desk_job_results(desk_id);
CREATE INDEX IF NOT EXISTS idx_desk_job_results_executed ON desk_job_results(executed_at);
CREATE INDEX IF NOT EXISTS idx_desk_job_results_status ON desk_job_results(status);

CREATE TABLE IF NOT EXISTS daily_briefs (
    id TEXT PRIMARY KEY,
    brief_date TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    sections_json TEXT NOT NULL,
    text_plain TEXT,
    text_html TEXT,
    text_markdown TEXT,
    previous_brief_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_daily_briefs_date ON daily_briefs(brief_date);

CREATE TABLE IF NOT EXISTS founder_notifications (
    id TEXT PRIMARY KEY,
    source TEXT,
    type TEXT,
    title TEXT,
    message TEXT,
    message_plain TEXT,
    priority TEXT,
    context TEXT,
    read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_founder_notifications_created ON founder_notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_founder_notifications_read ON founder_notifications(read);

CREATE TABLE IF NOT EXISTS orchestrator_runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    desks_assigned_json TEXT,
    tasks_created INTEGER DEFAULT 0,
    result_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_orchestrator_runs_started ON orchestrator_runs(started_at);

CREATE TABLE IF NOT EXISTS pending_mail (
    id TEXT PRIMARY KEY,
    from_addr TEXT,
    from_name TEXT,
    subject TEXT,
    channel TEXT DEFAULT 'email',
    status TEXT DEFAULT 'pending',
    body TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS family_help_tickets (
    id TEXT PRIMARY KEY,
    requester TEXT,
    subject TEXT,
    status TEXT DEFAULT 'open',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def ensure_max_ops_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(MAX_OPS_SCHEMA_SQL)


def ensure_max_ops_schema_on_default_db() -> None:
    """Open the live task DB (honors EMPIRE_TASK_DB) and ensure tables exist."""
    from app.db.database import get_db

    with get_db() as conn:
        ensure_max_ops_schema(conn)
