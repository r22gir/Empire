"""Isolated job-mail intake tables. Safe to re-run. Never touches live mail."""

from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jmi_processed (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    message_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL UNIQUE,
    subject TEXT,
    from_addr TEXT,
    matched_job_id TEXT,
    matched_customer_id TEXT,
    match_reason TEXT,
    kind TEXT NOT NULL DEFAULT 'note',
    status TEXT NOT NULL DEFAULT 'processed',
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jmi_review_queue (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    message_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL UNIQUE,
    subject TEXT,
    from_name TEXT,
    from_addr TEXT,
    preview TEXT,
    received_at TEXT,
    status TEXT NOT NULL DEFAULT 'unmatched',
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jmi_calendar_proposals (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    customer_id TEXT,
    source TEXT,
    message_id TEXT,
    fingerprint TEXT,
    title TEXT NOT NULL,
    proposed_date TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'deadline',
    excerpt TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    approved_at TEXT,
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jmi_supplier_order_events (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    source TEXT,
    message_id TEXT,
    fingerprint TEXT,
    event_type TEXT NOT NULL,
    tracking_number TEXT,
    order_number TEXT,
    supplier_name TEXT,
    excerpt TEXT,
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jmi_timeline_notes (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    source TEXT,
    message_id TEXT,
    fingerprint TEXT,
    summary TEXT NOT NULL,
    excerpt TEXT,
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jmi_processed_fp ON jmi_processed(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jmi_review_fp ON jmi_review_queue(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jmi_cal_job ON jmi_calendar_proposals(job_id);
CREATE INDEX IF NOT EXISTS idx_jmi_sup_job ON jmi_supplier_order_events(job_id);
CREATE INDEX IF NOT EXISTS idx_jmi_notes_job ON jmi_timeline_notes(job_id);
"""


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS job_events (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
                job_id TEXT NOT NULL,
                event_type TEXT,
                actor TEXT,
                summary TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )"""
        )
    except Exception:
        pass
