"""
SupportForge SQLite schema — the live tickets table.

The original Alembic migration (supportforge_001) is PostgreSQL-only
(UUID / ARRAY / JSONB) and never created sf_tickets on empire.db.
Runtime logs reported the missing table. This module is the SQLite
source of truth: idempotent CREATE IF NOT EXISTS, safe to re-run,
never writes live ticket rows.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from app.db.database import get_connection

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sf_tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    subdomain TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL DEFAULT 'starter',
    settings TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS sf_customers (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT,
    name TEXT,
    phone TEXT,
    company TEXT,
    empire_product_type TEXT,
    empire_product_id TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (tenant_id) REFERENCES sf_tenants(id) ON DELETE CASCADE,
    UNIQUE (tenant_id, email)
);
CREATE INDEX IF NOT EXISTS idx_sf_customers_tenant ON sf_customers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sf_customers_email ON sf_customers(email);

CREATE TABLE IF NOT EXISTS sf_tickets (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    ticket_number INTEGER NOT NULL,
    customer_id TEXT,
    assigned_agent_id TEXT,
    subject TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    priority TEXT NOT NULL DEFAULT 'normal',
    channel TEXT NOT NULL DEFAULT 'portal',
    tags TEXT NOT NULL DEFAULT '[]',
    category TEXT,
    source TEXT NOT NULL DEFAULT 'portal',
    edition_id TEXT,
    family_help_request_id TEXT,
    proposed_action TEXT,
    proposed_action_summary TEXT,
    proposed_action_status TEXT,
    auto_build INTEGER NOT NULL DEFAULT 0,
    sla_policy_id TEXT,
    first_response_at TEXT,
    resolved_at TEXT,
    closed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (tenant_id) REFERENCES sf_tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES sf_customers(id),
    UNIQUE (tenant_id, ticket_number)
);
CREATE INDEX IF NOT EXISTS idx_sf_tickets_tenant ON sf_tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sf_tickets_status ON sf_tickets(status);
CREATE INDEX IF NOT EXISTS idx_sf_tickets_source ON sf_tickets(source);
CREATE INDEX IF NOT EXISTS idx_sf_tickets_edition ON sf_tickets(edition_id);
CREATE INDEX IF NOT EXISTS idx_sf_tickets_created ON sf_tickets(created_at);

CREATE TABLE IF NOT EXISTS sf_messages (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    sender_type TEXT NOT NULL,
    sender_id TEXT,
    content TEXT NOT NULL,
    content_html TEXT,
    is_internal_note INTEGER NOT NULL DEFAULT 0,
    attachments TEXT NOT NULL DEFAULT '[]',
    ai_suggested INTEGER NOT NULL DEFAULT 0,
    ai_confidence REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (ticket_id) REFERENCES sf_tickets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sf_messages_ticket ON sf_messages(ticket_id);
"""

SEED_TENANTS = (
    ("edition:founder", "Founder", "founder"),
    ("edition:amp", "AMP family edition", "amp"),
    ("edition:maxine", "Maxine family edition", "maxine"),
    ("edition:minimax-meter", "MiniMax meter family edition", "minimax-meter"),
)


def ensure_supportforge_tables(conn: Optional[sqlite3.Connection] = None) -> None:
    """Create SupportForge tables. Idempotent. Does not insert ticket rows."""
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        for tenant_id, name, subdomain in SEED_TENANTS:
            conn.execute(
                """
                INSERT OR IGNORE INTO sf_tenants (id, name, subdomain)
                VALUES (?, ?, ?)
                """,
                (tenant_id, name, subdomain),
            )
        conn.commit()
    finally:
        if owns_conn:
            conn.close()


def tickets_table_exists(conn: Optional[sqlite3.Connection] = None) -> bool:
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sf_tickets'"
        ).fetchone()
        return row is not None
    finally:
        if owns_conn:
            conn.close()


def apply_to_path(db_path: Path) -> None:
    """Create tables on an explicit SQLite file (tests)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        ensure_supportforge_tables(conn)
    finally:
        conn.close()
