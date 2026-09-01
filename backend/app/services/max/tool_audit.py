"""Tool Audit — logs all tool executions to SQLite for accountability.

Every tool execution (success or failure) is recorded with timestamp,
parameters, result, access level, and desk. Never crashes on failure.
"""
import os
import sqlite3
import time
import json
import logging
from datetime import datetime

logger = logging.getLogger("max.tool_audit")

AUDIT_DB = os.path.expanduser("~/empire-repo/backend/data/tool_audit.db")


def init_audit_db():
    """Create the audit table if it doesn't exist. chmod 600 the DB.
    Apply column-level migrations idempotently — safe to call on
    existing DBs (H81 Phase 2, 2026-09-01)."""
    try:
        os.makedirs(os.path.dirname(AUDIT_DB), exist_ok=True)
        conn = sqlite3.connect(AUDIT_DB)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool TEXT NOT NULL,
                params TEXT,
                result TEXT,
                access_level INTEGER DEFAULT 1,
                approved_via TEXT,
                desk TEXT,
                success INTEGER DEFAULT 1,
                duration_ms INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tool_exec_ts
            ON tool_executions(timestamp DESC)
        """)
        # H81 Phase 2 — channel + founder columns. SQLite ALTER TABLE
        # ADD COLUMN has no IF NOT EXISTS in 3.x; we read PRAGMA
        # table_info to make this idempotent. Existing rows get NULL
        # for the new columns — do NOT backfill a guess. NULL means
        # "we did not record it," which is the truth for the 7928
        # historical rows.
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(tool_executions)").fetchall()
        }
        if "channel" not in existing_cols:
            conn.execute("ALTER TABLE tool_executions ADD COLUMN channel TEXT")
            logger.info("H81 Phase 2: added 'channel' column to tool_executions")
        if "founder" not in existing_cols:
            conn.execute("ALTER TABLE tool_executions ADD COLUMN founder INTEGER")
            logger.info("H81 Phase 2: added 'founder' column to tool_executions")
        conn.commit()
        conn.close()
        os.chmod(AUDIT_DB, 0o600)
        logger.info(f"Audit DB initialized: {AUDIT_DB}")
    except Exception as e:
        logger.warning(f"Could not initialize audit DB: {e}")


def log_execution(
    tool: str,
    params: dict | None = None,
    result: dict | str | None = None,
    access_level: int = 1,
    approved_via: str | None = None,
    desk: str | None = None,
    success: bool = True,
    duration_ms: int = 0,
    channel: str | None = None,
    founder: bool | None = None,
):
    """Log a tool execution. Never raises — failures are silently logged.

    H81 Phase 2: channel and founder are nullable. The executor can
    always supply founder (the bool is already on execute_tool's
    signature); channel is plumbed via tool_call['_channel'] and may
    be None until the router passes it through (see Phase 3 backlog).
    NULL means 'we did not record it' — that is the truth for the
    pre-Phase-2 history and is preserved.
    """
    try:
        conn = sqlite3.connect(AUDIT_DB, timeout=5)
        conn.execute(
            """INSERT INTO tool_executions
               (timestamp, tool, params, result, access_level, approved_via, desk, success, duration_ms, channel, founder)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                tool,
                json.dumps(params) if params else None,
                json.dumps(result) if isinstance(result, dict) else str(result) if result else None,
                access_level,
                approved_via,
                desk,
                1 if success else 0,
                duration_ms,
                channel,
                1 if founder else (0 if founder is not None else None),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"Audit log write failed (non-fatal): {e}")


def get_recent_executions(limit: int = 50) -> list[dict]:
    """Get recent tool executions for the dev panel."""
    try:
        conn = sqlite3.connect(AUDIT_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM tool_executions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"Audit read failed: {e}")
        return []


# Initialize on import
init_audit_db()
