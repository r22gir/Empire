"""OpenClaw Task Queue — persistent task queue with status tracking.

Endpoints for creating, listing, updating, and managing OpenClaw tasks.
Tasks flow: queued → running → done/failed/paused/cancelled.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import logging

from app.db.database import get_db, dict_row, dict_rows
from app.services.max.openclaw_gate import check_openclaw_gate, openclaw_gate_metadata

router = APIRouter(prefix="/api/v1/openclaw/tasks", tags=["openclaw-tasks"])
log = logging.getLogger("openclaw_tasks")


# ── Schemas ──────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: str
    desk: str = "general"
    priority: int = 5  # 1=critical, 5=normal, 10=low
    source: str = "manual"
    assigned_to: str = "openclaw"
    max_retries: int = 2
    parent_task_id: Optional[str] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    files_modified: Optional[str] = None  # JSON array
    commit_hash: Optional[str] = None
    retry_count: Optional[int] = None
    priority: Optional[int] = None
    desk: Optional[str] = None
    description: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("")
async def create_task(req: TaskCreate):
    """Create a new task in the queue."""
    gate = check_openclaw_gate()
    if gate.state in {"degraded", "unknown"}:
        raise HTTPException(
            status_code=503,
            detail={
                "message": gate.founder_message,
                "openclaw_gate": gate.to_dict(),
            },
        )

    gate_meta = openclaw_gate_metadata(gate)
    with get_db() as db:
        cursor = db.execute(
            """INSERT INTO openclaw_tasks (title, description, desk, priority, source, assigned_to, max_retries, parent_task_id, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (req.title, req.description, req.desk, req.priority, req.source,
             req.assigned_to, req.max_retries, req.parent_task_id,
             None if gate.allowed else gate.founder_message),
        )
        db.commit()
        task_id = cursor.lastrowid
    log.info(f"Task #{task_id} created: {req.title} [desk={req.desk}, priority={req.priority}]")
    status_message = gate.founder_message if not gate.allowed else "OpenClaw healthy - delegating task now."
    return {
        "id": task_id,
        "title": req.title,
        "status": "queued",
        "desk": req.desk,
        "message": status_message,
        "openclaw_gate": {**gate.to_dict(), **gate_meta},
    }


@router.get("")
async def list_tasks(
    status: Optional[str] = None,
    desk: Optional[str] = None,
    priority: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List tasks with optional filters."""
    with get_db() as db:
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if desk:
            conditions.append("desk = ?")
            params.append(desk)
        if priority:
            conditions.append("priority <= ?")
            params.append(priority)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        count_params = list(params)
        params.extend([limit, offset])

        rows = dict_rows(db.execute(
            f"SELECT * FROM openclaw_tasks {where} ORDER BY priority ASC, created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall())
        total = db.execute(f"SELECT COUNT(*) FROM openclaw_tasks {where}", count_params).fetchone()[0]

    return {"tasks": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/stats")
async def task_stats():
    """Get task counts by status."""
    with get_db() as db:
        rows = db.execute("SELECT status, COUNT(*) as count FROM openclaw_tasks GROUP BY status").fetchall()
    stats = {row[0]: row[1] for row in rows}
    total = sum(stats.values())
    return {"total": total, **stats}


@router.get("/queue")
async def get_next_queued():
    """Get the next queued task (highest priority, oldest first). For worker polling."""
    with get_db() as db:
        row = dict_row(db.execute(
            "SELECT * FROM openclaw_tasks WHERE status = 'queued' ORDER BY priority ASC, created_at ASC LIMIT 1"
        ).fetchone())
    if not row:
        return {"task": None}
    return {"task": row}


@router.get("/{task_id}")
async def get_task(task_id: int):
    """Get full task details."""
    with get_db() as db:
        row = dict_row(db.execute("SELECT * FROM openclaw_tasks WHERE id = ?", (task_id,)).fetchone())
    if not row:
        raise HTTPException(404, f"Task #{task_id} not found")
    return row


@router.put("/{task_id}")
async def update_task(task_id: int, req: TaskUpdate):
    """Update task status, result, error, etc."""
    with get_db() as db:
        existing = db.execute("SELECT id, status FROM openclaw_tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            raise HTTPException(404, f"Task #{task_id} not found")

        updates = []
        params = []
        for field, value in req.model_dump(exclude_none=True).items():
            updates.append(f"{field} = ?")
            params.append(value)

        if req.status == "running":
            updates.append("started_at = datetime('now')")
        elif req.status in ("done", "failed", "cancelled"):
            updates.append("completed_at = datetime('now')")

        if not updates:
            raise HTTPException(400, "No fields to update")

        params.append(task_id)
        db.execute(f"UPDATE openclaw_tasks SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()

    log.info(f"Task #{task_id} updated: {req.model_dump(exclude_none=True)}")
    return {"id": task_id, "updated": True}


@router.delete("/{task_id}")
async def cancel_task(task_id: int):
    """Cancel a queued or running task."""
    with get_db() as db:
        existing = db.execute("SELECT status FROM openclaw_tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            raise HTTPException(404, f"Task #{task_id} not found")
        if existing[0] in ("done", "cancelled"):
            raise HTTPException(400, f"Task #{task_id} is already {existing[0]}")

        db.execute(
            "UPDATE openclaw_tasks SET status = 'cancelled', completed_at = datetime('now') WHERE id = ?",
            (task_id,),
        )
        db.commit()
    log.info(f"Task #{task_id} cancelled")
    return {"id": task_id, "status": "cancelled"}


@router.post("/{task_id}/retry")
async def retry_task(task_id: int):
    """Retry a failed task — resets to queued with incremented retry_count."""
    with get_db() as db:
        row = db.execute("SELECT status, retry_count, max_retries FROM openclaw_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"Task #{task_id} not found")
        if row[0] != "failed":
            raise HTTPException(400, f"Can only retry failed tasks (current: {row[0]})")

        db.execute(
            """UPDATE openclaw_tasks SET status = 'queued', error = NULL, result = NULL,
               started_at = NULL, completed_at = NULL, retry_count = retry_count + 1
               WHERE id = ?""",
            (task_id,),
        )
        db.commit()
    log.info(f"Task #{task_id} retried (attempt {row[1] + 1})")
    return {"id": task_id, "status": "queued", "retry_count": row[1] + 1}


@router.post("/{task_id}/approve")
async def approve_task(task_id: int):
    """Approve a paused task — sets it back to queued for execution."""
    with get_db() as db:
        row = db.execute("SELECT status FROM openclaw_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"Task #{task_id} not found")
        if row[0] != "paused":
            raise HTTPException(400, f"Can only approve paused tasks (current: {row[0]})")

        db.execute("UPDATE openclaw_tasks SET status = 'queued', error = NULL WHERE id = ?", (task_id,))
        db.commit()
    log.info(f"Task #{task_id} approved — back to queue")
    return {"id": task_id, "status": "queued"}


@router.post("/{task_id}/reject")
async def reject_task(task_id: int, reason: str = "Rejected by founder"):
    """Reject a paused task — marks as cancelled."""
    with get_db() as db:
        row = db.execute("SELECT status FROM openclaw_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"Task #{task_id} not found")
        if row[0] != "paused":
            raise HTTPException(400, f"Can only reject paused tasks (current: {row[0]})")

        db.execute(
            "UPDATE openclaw_tasks SET status = 'cancelled', error = ?, completed_at = datetime('now') WHERE id = ?",
            (reason, task_id),
        )
        db.commit()
    log.info(f"Task #{task_id} rejected: {reason}")
    return {"id": task_id, "status": "cancelled", "reason": reason}
