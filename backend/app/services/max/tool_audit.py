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
    """Create the audit table if it doesn't exist. chmod 600 the DB."""
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
):
    """Log a tool execution. Never raises — failures are silently logged."""
    try:
        conn = sqlite3.connect(AUDIT_DB, timeout=5)
        conn.execute(
            """INSERT INTO tool_executions
               (timestamp, tool, params, result, access_level, approved_via, desk, success, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
