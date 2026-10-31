"""job_stages table and job_documents columns used by the document-set gate."""
from __future__ import annotations

import sqlite3


JOB_STAGES_DDL = """
CREATE TABLE IF NOT EXISTS job_stages (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    job_id TEXT NOT NULL,
    stage_key TEXT NOT NULL,
    stage_order INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_started',
    approved_by TEXT,
    approved_at TEXT,
    linked_documents TEXT,
    required INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(job_id, stage_key)
)
"""

JOB_STAGE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_job_stages_job ON job_stages(job_id)",
    "CREATE INDEX IF NOT EXISTS idx_job_stages_status ON job_stages(job_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_job_docs_stage ON job_documents(stage_key)",
    "CREATE INDEX IF NOT EXISTS idx_job_docs_superseded ON job_documents(job_id, superseded)",
)

JOB_DOCUMENT_COLUMNS = (
    ("superseded", "INTEGER DEFAULT 0"),
    ("superseded_by", "TEXT"),
    ("standard_name", "TEXT"),
    ("audience", "TEXT"),
    ("stage_key", "TEXT"),
)

GATE_CUTOVER_KEY = "gate_cutover_at"


def _safe_alter(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass


def init_job_stages_schema(conn: sqlite3.Connection) -> None:
    """Idempotent migration: job_stages table + document-set columns."""
    conn.execute(JOB_STAGES_DDL)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS job_stage_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )"""
    )
    # Cutover is stamped once at first migrate: jobs created before this
    # moment are grandfathered. Existing rows get gate_enforced=0.
    conn.execute(
        "INSERT OR IGNORE INTO job_stage_config (key, value) VALUES (?, datetime('now'))",
        (GATE_CUTOVER_KEY,),
    )
    _safe_alter(conn, "jobs", "gate_enforced", "INTEGER DEFAULT 0")
    _safe_alter(conn, "job_stages", "gate_enforced", "INTEGER DEFAULT 0")
    for column, col_type in JOB_DOCUMENT_COLUMNS:
        _safe_alter(conn, "job_documents", column, col_type)
    for statement in JOB_STAGE_INDEXES:
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass


def get_gate_cutover_at(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT value FROM job_stage_config WHERE key = ?",
        (GATE_CUTOVER_KEY,),
    ).fetchone()
    if not row:
        return None
    return row[0] if not hasattr(row, "keys") else row["value"]
