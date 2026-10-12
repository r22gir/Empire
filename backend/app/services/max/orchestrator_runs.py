"""Persist #110 orchestrator runs and route leftover work to idle desks."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from app.db.max_ops_schema import ensure_max_ops_schema
from app.services.max.desks import live_data as ld
from app.services.max.desks.job_runner import JOB_REGISTRY, run_scheduled_job

logger = logging.getLogger("max.orchestrator_runs")

# Desks that already have a daily cron job.
SCHEDULED_DESKS = {
    "finance", "it", "sales", "support", "marketing", "forge", "analytics", "quality",
}

# Idle desks get a real job via the orchestrator.
IDLE_DESK_JOBS = (
    ("clients", "Client Care Scan", "Unanswered client mail, unpaid invoices, today's visits."),
    ("contractors", "Vendor Pickup Scan", "Pickups and deliveries on this week's calendar."),
    ("intake", "New Intake Review", "New inbound items waiting to become jobs."),
    ("market", "Listing and Lead Scan", "Draft quotes and inbound leads."),
    ("legal", "Approvals Waiting Review", "Decisions waiting on Rafael."),
    ("website", "Storefront Watch", "Read-only watch of live services. No outbound."),
    ("lab", "Family Help Ticket Scan", "Family-help tickets only. Isolated from Workroom."),
    ("innovation", "Ventures and Personal Scan", "Organizer items for personal and ventures."),
    ("codeforge", "Failed Job Retry Scan", "Failed desk jobs from yesterday."),
)


def record_run(
    *,
    status: str,
    desks_assigned: list[str],
    tasks_created: int,
    result: dict[str, Any],
    started_at: datetime,
    finished_at: datetime | None = None,
    run_id: str | None = None,
) -> str:
    from app.db.database import get_db

    rid = run_id or uuid.uuid4().hex[:12]
    with get_db() as conn:
        ensure_max_ops_schema(conn)
        conn.execute(
            """INSERT INTO orchestrator_runs
               (id, started_at, finished_at, status, desks_assigned_json, tasks_created, result_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                rid,
                started_at.isoformat(),
                (finished_at or datetime.now()).isoformat(),
                status,
                json.dumps(desks_assigned),
                tasks_created,
                json.dumps(result, default=str)[:8000],
            ),
        )
    return rid


def list_runs(limit: int = 20) -> list[dict]:
    from app.db.database import get_db

    with get_db() as conn:
        ensure_max_ops_schema(conn)
        rows = conn.execute(
            "SELECT id, started_at, finished_at, status, desks_assigned_json, tasks_created, result_json "
            "FROM orchestrator_runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r) if hasattr(r, "keys") else {
            "id": r[0], "started_at": r[1], "finished_at": r[2], "status": r[3],
            "desks_assigned_json": r[4], "tasks_created": r[5], "result_json": r[6],
        }
        try:
            d["desks_assigned"] = json.loads(d.pop("desks_assigned_json") or "[]")
        except json.JSONDecodeError:
            d["desks_assigned"] = []
        try:
            d["result"] = json.loads(d.pop("result_json") or "{}")
        except json.JSONDecodeError:
            d["result"] = {}
        out.append(d)
    return out


def route_idle_desks(now: datetime | None = None, snap: dict | None = None) -> dict[str, Any]:
    """Give idle desks a real job and persist an orchestrator run."""
    now = now or datetime.now()
    started = now
    assigned: list[str] = []
    created = 0
    results = []
    snap = snap or ld.snapshot(now)
    for desk_id, title, description in IDLE_DESK_JOBS:
        if title not in JOB_REGISTRY:
            continue
        try:
            out = run_scheduled_job(desk_id, title, description, snap=snap, now=now)
            assigned.append(desk_id)
            created += 1
            results.append({"desk": desk_id, "title": title, "status": out.get("status")})
        except Exception as e:
            logger.warning("idle desk %s failed: %s", desk_id, e)
            results.append({"desk": desk_id, "title": title, "status": "failed", "error": str(e)})
    payload = {
        "desks_assigned": assigned,
        "tasks_created": created,
        "results": results,
    }
    rid = record_run(
        status="ok" if created else "empty",
        desks_assigned=assigned,
        tasks_created=created,
        result=payload,
        started_at=started,
        finished_at=datetime.now(),
    )
    payload["run_id"] = rid
    return payload
