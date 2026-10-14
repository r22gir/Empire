"""Isolated job-mail intake tables. Safe to re-run. Never touches live mail."""

from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jmi_processed (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    account TEXT,
    message_id TEXT NOT NULL,
    rfc_message_id TEXT,
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
    account TEXT,
    message_id TEXT NOT NULL,
    rfc_message_id TEXT,
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
    account TEXT,
    message_id TEXT,
    rfc_message_id TEXT,
    fingerprint TEXT,
    title TEXT NOT NULL,
    proposed_date TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'deadline',
    excerpt TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    approved_at TEXT,
    approved_by TEXT,
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jmi_supplier_order_events (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    source TEXT,
    account TEXT,
    message_id TEXT,
    rfc_message_id TEXT,
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
    account TEXT,
    message_id TEXT,
    rfc_message_id TEXT,
    fingerprint TEXT,
    summary TEXT NOT NULL,
    excerpt TEXT,
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jmi_scan_state (
    id TEXT PRIMARY KEY,
    last_success_at TEXT,
    backoff_until TEXT,
    fail_count INTEGER NOT NULL DEFAULT 0,
    last_error_type TEXT,
    last_scanned INTEGER NOT NULL DEFAULT 0,
    last_matched INTEGER NOT NULL DEFAULT 0,
    last_unmatched INTEGER NOT NULL DEFAULT 0,
    last_duplicates INTEGER NOT NULL DEFAULT 0,
    last_ignored INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jmi_processed_fp ON jmi_processed(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jmi_processed_rfc ON jmi_processed(rfc_message_id);
CREATE INDEX IF NOT EXISTS idx_jmi_review_fp ON jmi_review_queue(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jmi_review_rfc ON jmi_review_queue(rfc_message_id);
CREATE INDEX IF NOT EXISTS idx_jmi_cal_job ON jmi_calendar_proposals(job_id);
CREATE INDEX IF NOT EXISTS idx_jmi_sup_job ON jmi_supplier_order_events(job_id);
CREATE INDEX IF NOT EXISTS idx_jmi_notes_job ON jmi_timeline_notes(job_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jmi_cal_dedupe
    ON jmi_calendar_proposals(fingerprint, proposed_date, kind);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jmi_sup_dedupe
    ON jmi_supplier_order_events(fingerprint);
"""

_ALTERS = (
    ("jmi_processed", "account", "TEXT"),
    ("jmi_processed", "rfc_message_id", "TEXT"),
    ("jmi_review_queue", "account", "TEXT"),
    ("jmi_review_queue", "rfc_message_id", "TEXT"),
    ("jmi_calendar_proposals", "account", "TEXT"),
    ("jmi_calendar_proposals", "rfc_message_id", "TEXT"),
    ("jmi_calendar_proposals", "approved_by", "TEXT"),
    ("jmi_supplier_order_events", "account", "TEXT"),
    ("jmi_supplier_order_events", "rfc_message_id", "TEXT"),
    ("jmi_timeline_notes", "account", "TEXT"),
    ("jmi_timeline_notes", "rfc_message_id", "TEXT"),
    ("jmi_scan_state", "last_scanned", "INTEGER NOT NULL DEFAULT 0"),
    ("jmi_scan_state", "last_matched", "INTEGER NOT NULL DEFAULT 0"),
    ("jmi_scan_state", "last_unmatched", "INTEGER NOT NULL DEFAULT 0"),
    ("jmi_scan_state", "last_duplicates", "INTEGER NOT NULL DEFAULT 0"),
    ("jmi_scan_state", "last_ignored", "INTEGER NOT NULL DEFAULT 0"),
    ("jobs", "contacts", "TEXT"),
)


def _ensure_columns(conn) -> None:
    for table, col, decl in _ALTERS:
        try:
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        except Exception:
            continue
        if col not in cols:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            except Exception:
                pass


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)
    _ensure_columns(conn)
    try:
        job_cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        if job_cols and "contacts" not in job_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN contacts TEXT")
    except Exception:
        pass
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
