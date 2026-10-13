"""Persistent SQLite queue for Max improvement jobs (Atlas / CodeForge).

Approve never talks to MiniMax or GitHub. It only writes a row here.
The CodeForge (Atlas) worker claims jobs and runs the plan loop.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from app.services.leadforge import growth
from app.services.max import improvements as imp

JOB_KINDS = ("plan", "retry")
JOB_STATUSES = ("queued", "running", "done", "failed")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_jobs(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS max_improvement_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            improvement_id INTEGER NOT NULL,
            kind TEXT NOT NULL DEFAULT 'plan',
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER NOT NULL DEFAULT 0,
            payload TEXT,
            result TEXT,
            error TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            started_at TEXT,
            finished_at TEXT
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_max_imp_jobs_status ON max_improvement_jobs(status, id)"
    )


def enqueue(improvement_id: int, kind: str = "plan", payload: Optional[dict] = None) -> dict:
    """Idempotent: one queued/running job per improvement. Retry allowed after failed/done."""
    kind = kind if kind in JOB_KINDS else "plan"
    with growth._db() as conn:
        ensure_jobs(conn)
        imp._ensure(conn)
        existing = conn.execute(
            """SELECT * FROM max_improvement_jobs
               WHERE improvement_id=? AND status IN ('queued','running')
               ORDER BY id DESC LIMIT 1""",
            (improvement_id,),
        ).fetchone()
        if existing:
            return dict(existing)
        cur = conn.execute(
            """INSERT INTO max_improvement_jobs (improvement_id, kind, status, payload)
               VALUES (?,?, 'queued', ?)""",
            (improvement_id, kind, json.dumps(payload or {})),
        )
        row = conn.execute(
            "SELECT * FROM max_improvement_jobs WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)


def claim_next() -> Optional[dict]:
    """Atomically claim the oldest queued job."""
    with growth._db() as conn:
        ensure_jobs(conn)
        row = conn.execute(
            """SELECT * FROM max_improvement_jobs
               WHERE status='queued' ORDER BY id ASC LIMIT 1"""
        ).fetchone()
        if not row:
            return None
        job_id = row["id"]
        cur = conn.execute(
            """UPDATE max_improvement_jobs
               SET status='running', started_at=?, attempts=attempts+1
               WHERE id=? AND status='queued'""",
            (_now(), job_id),
        )
        if cur.rowcount != 1:
            return None
        claimed = conn.execute(
            "SELECT * FROM max_improvement_jobs WHERE id=?", (job_id,)
        ).fetchone()
        return dict(claimed) if claimed else None


def mark_done(job_id: int, result: Optional[dict] = None) -> dict:
    with growth._db() as conn:
        ensure_jobs(conn)
        conn.execute(
            """UPDATE max_improvement_jobs
               SET status='done', finished_at=?, result=?, error=NULL
               WHERE id=?""",
            (_now(), json.dumps(result or {}), job_id),
        )
        return dict(conn.execute("SELECT * FROM max_improvement_jobs WHERE id=?", (job_id,)).fetchone())


def mark_failed(job_id: int, error: str) -> dict:
    with growth._db() as conn:
        ensure_jobs(conn)
        conn.execute(
            """UPDATE max_improvement_jobs
               SET status='failed', finished_at=?, error=?
               WHERE id=?""",
            (_now(), (error or "")[:800], job_id),
        )
        return dict(conn.execute("SELECT * FROM max_improvement_jobs WHERE id=?", (job_id,)).fetchone())


def get_job(job_id: int) -> Optional[dict]:
    with growth._db() as conn:
        ensure_jobs(conn)
        r = conn.execute("SELECT * FROM max_improvement_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(r) if r else None


def latest_for(improvement_id: int) -> Optional[dict]:
    with growth._db() as conn:
        ensure_jobs(conn)
        r = conn.execute(
            "SELECT * FROM max_improvement_jobs WHERE improvement_id=? ORDER BY id DESC LIMIT 1",
            (improvement_id,),
        ).fetchone()
        return dict(r) if r else None


def queue_counts() -> dict:
    with growth._db() as conn:
        ensure_jobs(conn)
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM max_improvement_jobs GROUP BY status"
        ).fetchall()
    counts = {s: 0 for s in JOB_STATUSES}
    for r in rows:
        counts[r["status"]] = r["n"]
    counts["queued_or_running"] = counts["queued"] + counts["running"]
    return counts
