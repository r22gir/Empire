"""
MAX Autonomous Maintenance — API Router
────────────────────────────────────────
Endpoints for the maintenance task lifecycle:
sync roadmap, approve, execute, revert, toggle, and status queries.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.max.maintenance_manager import (
    ingest_roadmap,
    get_next_task,
    execute_maintenance_task,
    approve_task,
    revert_last_maintenance,
    get_pending_tasks,
    get_completed_today,
    get_maintenance_history,
    get_maintenance_status,
    toggle_maintenance,
)

router = APIRouter()


# ── Models ───────────────────────────────────────────────────────────

class ToggleRequest(BaseModel):
    enabled: bool


# ── GET Endpoints ────────────────────────────────────────────────────

@router.get("/maintenance/status")
async def status():
    """Get maintenance system summary: enabled, counts, last run."""
    try:
        return get_maintenance_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance/pending")
async def pending(bucket: Optional[str] = Query(None)):
    """List pending/approved maintenance tasks, optionally filtered by bucket."""
    try:
        return get_pending_tasks(bucket=bucket)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance/history")
async def history(limit: int = Query(20, ge=1, le=100)):
    """Recent maintenance task history."""
    try:
        return get_maintenance_history(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance/today")
async def today():
    """Tasks completed, failed, or reverted today."""
    try:
        return get_completed_today()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance/next")
async def next_task():
    """Preview the next task that would be executed."""
    try:
        result = get_next_task()
        if result is None:
            return {"task": None, "message": "No tasks available"}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST Endpoints ───────────────────────────────────────────────────

@router.post("/maintenance/execute")
async def execute_next():
    """Execute the next auto-executable maintenance task."""
    try:
        result = execute_maintenance_task()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/execute/{key}")
async def execute_specific(key: str):
    """Execute a specific maintenance task by task_key."""
    try:
        result = execute_maintenance_task(task_key=key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/approve/{key}")
async def approve(key: str):
    """Approve a pending task for execution."""
    try:
        result = approve_task(key)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/revert")
async def revert():
    """Revert the last completed maintenance task."""
    try:
        result = revert_last_maintenance()
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/sync")
async def sync():
    """Sync/ingest the productivity roadmap into maintenance_log."""
    try:
        return ingest_roadmap()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/toggle")
async def toggle(body: ToggleRequest):
    """Enable or disable autonomous maintenance."""
    try:
        return toggle_maintenance(body.enabled)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
