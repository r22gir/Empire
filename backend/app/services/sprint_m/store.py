"""Isolated Sprint M SQLite store. Never the live empire.db unless explicitly set."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sm_organizer_jobs (
    id TEXT PRIMARY KEY,
    job_number TEXT UNIQUE NOT NULL,
    quote_id TEXT,
    quote_number TEXT,
    customer_id TEXT,
    customer_name TEXT,
    business_unit TEXT DEFAULT 'workroom',
    status TEXT DEFAULT 'sold',
    title TEXT,
    style TEXT,
    photos_json TEXT DEFAULT '[]',
    fabric_codes_json TEXT DEFAULT '[]',
    seamstress_hours REAL DEFAULT 0,
    seamstress_rate REAL DEFAULT 0,
    seamstress_pay REAL DEFAULT 0,
    due_date TEXT,
    scheduled_at TEXT,
    quoted_amount REAL DEFAULT 0,
    notes TEXT,
    measurements_json TEXT DEFAULT '{}',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_job_items (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    line_number INTEGER DEFAULT 0,
    item_type TEXT,
    style TEXT,
    description TEXT,
    room TEXT,
    fabric_code TEXT,
    measurements_json TEXT DEFAULT '{}',
    photo_urls_json TEXT DEFAULT '[]',
    seamstress_hours REAL DEFAULT 0,
    seamstress_rate REAL DEFAULT 0,
    seamstress_pay REAL DEFAULT 0,
    quantity REAL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    trigger_event TEXT NOT NULL,
    action TEXT NOT NULL,
    params_json TEXT DEFAULT '{}',
    created_by TEXT DEFAULT 'owner',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_drafts (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    customer_id TEXT,
    channel TEXT NOT NULL,
    to_address TEXT,
    subject TEXT,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    approval_required INTEGER DEFAULT 1,
    approved_by TEXT,
    approved_at TEXT,
    source TEXT,
    rule_id TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_job_costs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    planned_amount REAL DEFAULT 0,
    actual_amount REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_credit_memos (
    id TEXT PRIMARY KEY,
    memo_number TEXT UNIQUE NOT NULL,
    customer_id TEXT NOT NULL,
    customer_name TEXT,
    amount REAL NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'open',
    source TEXT DEFAULT 'credit_memo',
    invoice_id TEXT,
    job_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_account_credits (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT,
    credit_balance REAL DEFAULT 0,
    overpayment_balance REAL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_credit_applications (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    amount REAL NOT NULL,
    source TEXT,
    memo_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_family_alerts (
    id TEXT PRIMARY KEY,
    request_id TEXT,
    requester TEXT,
    requester_agent TEXT,
    summary TEXT,
    classification TEXT,
    needs TEXT,
    delivery_status TEXT DEFAULT 'queued',
    delivery_channel TEXT,
    recipient_role TEXT DEFAULT 'owner',
    recipient TEXT,
    noop_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sm_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    action TEXT NOT NULL,
    actor TEXT DEFAULT 'system',
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sm_jobs_quote ON sm_organizer_jobs(quote_id);
CREATE INDEX IF NOT EXISTS idx_sm_jobs_status ON sm_organizer_jobs(status);
CREATE INDEX IF NOT EXISTS idx_sm_items_job ON sm_job_items(job_id);
CREATE INDEX IF NOT EXISTS idx_sm_drafts_status ON sm_drafts(status);
CREATE INDEX IF NOT EXISTS idx_sm_costs_job ON sm_job_costs(job_id);
CREATE INDEX IF NOT EXISTS idx_sm_credits_customer ON sm_credit_memos(customer_id);
"""

DEFAULT_RULES = [
    {
        "id": "rule-proposal-signed-sold",
        "name": "Proposal signed → job Sold",
        "trigger_event": "proposal_signed",
        "action": "set_job_status",
        "params_json": '{"status":"sold"}',
    },
    {
        "id": "rule-quote-approved-sold",
        "name": "Quote approved → job Sold",
        "trigger_event": "quote_approved",
        "action": "set_job_status",
        "params_json": '{"status":"sold"}',
    },
    {
        "id": "rule-job-scheduled-draft-email",
        "name": "Job scheduled → draft client email",
        "trigger_event": "job_scheduled",
        "action": "draft_client_email",
        "params_json": '{"template":"job_scheduled"}',
    },
]


def sprint_m_db_path() -> Path:
    override = os.getenv("SPRINT_M_DB")
    if override:
        return Path(override)
    empire = os.getenv("EMPIRE_TASK_DB")
    if empire:
        return Path(empire).with_name("sprint_m.db")
    return Path.home() / "empire-data" / "sprint_m.db"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else sprint_m_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_store(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    for rule in DEFAULT_RULES:
        conn.execute(
            """INSERT OR IGNORE INTO sm_rules
               (id, name, enabled, trigger_event, action, params_json, created_by)
               VALUES (?, ?, 1, ?, ?, ?, 'owner')""",
            (rule["id"], rule["name"], rule["trigger_event"], rule["action"], rule["params_json"]),
        )
    from app.services.sprint_m.fabric import seed_reserved_codes

    seed_reserved_codes(conn)
    conn.commit()


@contextmanager
def get_store(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        init_store(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def audit(conn: sqlite3.Connection, entity_type: str, entity_id: str | None, action: str,
          actor: str = "system", detail: str | None = None) -> None:
    conn.execute(
        "INSERT INTO sm_audit (entity_type, entity_id, action, actor, detail) VALUES (?, ?, ?, ?, ?)",
        (entity_type, entity_id, action, actor, detail),
    )
