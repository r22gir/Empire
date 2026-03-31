"""
MAX → OpenClaw Bridge
Dispatches desk tasks to OpenClaw for autonomous execution.
Add to: backend/app/routers/openclaw_bridge.py
Register in: backend/app/main.py
"""

import asyncio
import httpx
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("empire.openclaw_bridge")

router = APIRouter(prefix="/api/v1/openclaw", tags=["openclaw"])

# OpenClaw gateway config
OPENCLAW_URL = "http://localhost:7878"
OPENCLAW_TIMEOUT = 300  # 5 min for complex tasks


class TaskRequest(BaseModel):
    """Task to dispatch to OpenClaw."""
    task_id: Optional[str] = None
    title: str
    description: str
    priority: str = "normal"  # low, normal, high, critical
    desk: Optional[str] = None
    skills_needed: list[str] = []  # which skills to hint


class TaskResult(BaseModel):
    """Result from OpenClaw execution."""
    task_id: str
    status: str  # completed, failed, needs_review
    summary: str
    changes_made: list[str] = []
    errors: list[str] = []
    started_at: str
    completed_at: str


# In-memory task queue (upgrade to DB later)
task_queue: list[dict] = []
task_results: list[dict] = []


def _build_prompt(task: TaskRequest) -> str:
    """Convert a desk task into an OpenClaw execution prompt."""
    skill_hints = ""
    if task.skills_needed:
        skill_hints = f"\nRelevant skills: {', '.join(task.skills_needed)}"

    return f"""Execute the following Empire task:

## Task: {task.title}
Priority: {task.priority}
{f"Desk: {task.desk}" if task.desk else ""}
{skill_hints}

## Instructions
{task.description}

## Requirements
1. Read relevant files before making changes
2. Back up any data before deleting
3. Test your changes (build check, curl endpoints)
4. Commit with a clear message if code was changed
5. Report back with:
   - What you changed (file paths, line counts)
   - What you tested
   - Any issues or things needing founder review
"""


@router.get("/health")
async def openclaw_health():
    """Check if OpenClaw is reachable."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OPENCLAW_URL}/health")
            if resp.status_code == 200:
                return {"status": "online", "openclaw_url": OPENCLAW_URL}
            return {"status": "unhealthy", "code": resp.status_code}
    except httpx.ConnectError:
        return {"status": "offline", "openclaw_url": OPENCLAW_URL}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/dispatch", response_model=dict)
async def dispatch_task(task: TaskRequest):
    """
    Dispatch a task to OpenClaw for execution.
    Called by MAX desk system when a task needs autonomous execution.
    """
    task_id = task.task_id or f"oc-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    prompt = _build_prompt(task)

    # Log the dispatch
    task_record = {
        "task_id": task_id,
        "title": task.title,
        "priority": task.priority,
        "status": "dispatched",
        "dispatched_at": datetime.now().isoformat(),
    }
    task_queue.append(task_record)

    logger.info(f"Dispatching to OpenClaw: {task.title} [{task_id}]")

    try:
        async with httpx.AsyncClient(timeout=OPENCLAW_TIMEOUT) as client:
            # Send to OpenClaw /chat endpoint (native format)
            resp = await client.post(
                f"{OPENCLAW_URL}/chat",
                json={
                    "message": prompt,
                    "history": [],
                    "system_prompt": "You are MAX's execution agent. Execute the task precisely. Report what you did, what changed, and what needs review.",
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                result_text = data.get("response", "")

                result = {
                    "task_id": task_id,
                    "status": "completed",
                    "summary": result_text[:500],
                    "full_response": result_text,
                    "skill_used": data.get("skill_used"),
                    "source": data.get("source", "openclaw"),
                    "completed_at": datetime.now().isoformat(),
                }
                task_record["status"] = "completed"
                task_results.append(result)

                logger.info(f"OpenClaw completed: {task.title} [{task_id}]")
                return result
            else:
                error_detail = resp.text[:200]
                task_record["status"] = "failed"
                logger.error(f"OpenClaw error {resp.status_code}: {error_detail}")
                raise HTTPException(status_code=502, detail=f"OpenClaw returned {resp.status_code}: {error_detail}")

    except httpx.ConnectError:
        task_record["status"] = "failed"
        raise HTTPException(status_code=503, detail="OpenClaw is not running on port 7878. Start it with: openclaw start")
    except httpx.ReadTimeout:
        task_record["status"] = "timeout"
        raise HTTPException(status_code=504, detail=f"OpenClaw task timed out after {OPENCLAW_TIMEOUT}s")


@router.post("/dispatch-async", response_model=dict)
async def dispatch_task_async(task: TaskRequest):
    """
    Dispatch a task to OpenClaw without waiting for completion.
    Returns immediately with task_id for polling.
    """
    task_id = task.task_id or f"oc-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    task_record = {
        "task_id": task_id,
        "title": task.title,
        "priority": task.priority,
        "status": "queued",
        "dispatched_at": datetime.now().isoformat(),
    }
    task_queue.append(task_record)

    # Fire and forget
    asyncio.create_task(_execute_in_background(task, task_id, task_record))

    return {"task_id": task_id, "status": "queued", "message": f"Task '{task.title}' queued for OpenClaw execution"}


async def _execute_in_background(task: TaskRequest, task_id: str, task_record: dict):
    """Background execution — updates task_record in place."""
    try:
        task_record["status"] = "running"
        prompt = _build_prompt(task)

        async with httpx.AsyncClient(timeout=OPENCLAW_TIMEOUT) as client:
            resp = await client.post(
                f"{OPENCLAW_URL}/chat",
                json={
                    "message": prompt,
                    "history": [],
                    "system_prompt": "You are MAX's execution agent. Execute the task precisely. Report what you did, what changed, and what needs review.",
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                result_text = data.get("response", "")

                task_record["status"] = "completed"
                task_record["result"] = result_text[:500]
                task_record["completed_at"] = datetime.now().isoformat()
                task_results.append({
                    "task_id": task_id,
                    "status": "completed",
                    "summary": result_text[:500],
                    "full_response": result_text,
                    "completed_at": datetime.now().isoformat(),
                })
                logger.info(f"Background task completed: {task.title} [{task_id}]")

                # Log to notification system (no auto-Telegram)
                await _log_notification(task_id, task.title, "completed", result_text[:300])
            else:
                task_record["status"] = "failed"
                task_record["error"] = resp.text[:200]
                logger.error(f"Background task failed: {task.title} [{task_id}]")

    except Exception as e:
        task_record["status"] = "failed"
        task_record["error"] = str(e)
        logger.error(f"Background task error: {task.title} [{task_id}]: {e}")


@router.get("/legacy-tasks")
async def list_legacy_tasks():
    """List in-memory dispatched tasks (legacy — use /api/v1/openclaw/tasks for DB-backed queue)."""
    return {"tasks": task_queue, "count": len(task_queue)}


@router.get("/legacy-tasks/{task_id}")
async def get_legacy_task(task_id: str):
    """Get in-memory task status (legacy — use /api/v1/openclaw/tasks/{id} for DB-backed)."""
    for task in task_queue:
        if task["task_id"] == task_id:
            for result in task_results:
                if result["task_id"] == task_id:
                    return {**task, "result": result}
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.get("/results")
async def list_results():
    """List all completed task results."""
    return {"results": task_results, "count": len(task_results)}


async def _log_notification(task_id: str, title: str, status: str, summary: str):
    """Log task completion to notification system (no auto-Telegram)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                "http://localhost:8000/api/v1/notifications/internal",
                json={
                    "source": "System",
                    "type": "task_complete",
                    "title": f"OpenClaw: {title}",
                    "message": f"Task {task_id} {status}: {summary[:300]}",
                    "priority": "low",
                    "context": {"task_id": task_id, "status": status},
                },
            )
    except Exception as e:
        logger.warning(f"Failed to log notification: {e}")


def _get_gateway_token() -> str:
    """Get OpenClaw gateway token from env."""
    import os
    return os.getenv("OPENCLAW_GATEWAY_TOKEN", "empire-max-gateway")


# ── Desk-Aware Dispatch (called by desks / scheduler) ────────────────────

async def dispatch_desk_task_to_openclaw(
    desk_id: str,
    task_title: str,
    task_description: str,
    timeout: int = 120,
) -> dict:
    """Called by desks to execute tasks via OpenClaw. Returns result dict.

    This is the primary integration point between the desk system and OpenClaw.
    Desks call this function directly (not via HTTP) to avoid a roundtrip.

    Returns:
        {"status": "completed", "summary": "...", "task_id": "...", "source": "openclaw"}
        or
        {"status": "failed", "error": "..."}
    """
    task_id = f"oc-desk-{desk_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Build prompt with desk context
    prompt = f"""Execute the following task for the {desk_id} desk:

## Task: {task_title}
Desk: {desk_id}

## Instructions
{task_description}

## Requirements
1. Read relevant files before making changes
2. Back up any data before deleting
3. Test your changes if applicable
4. Report back with what you did, what changed, and any issues
"""

    # Record in task queue
    task_record = {
        "task_id": task_id,
        "title": task_title,
        "desk": desk_id,
        "priority": "normal",
        "status": "dispatched",
        "dispatched_at": datetime.now().isoformat(),
    }
    task_queue.append(task_record)

    logger.info(f"Desk dispatch to OpenClaw: [{desk_id}] {task_title} [{task_id}]")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{OPENCLAW_URL}/chat",
                json={
                    "message": prompt,
                    "history": [],
                    "system_prompt": (
                        f"You are MAX's execution agent for the {desk_id} desk. "
                        "Execute the task precisely. Report what you did and any issues."
                    ),
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                result_text = data.get("response", "")

                result = {
                    "task_id": task_id,
                    "status": "completed",
                    "summary": result_text[:500],
                    "full_response": result_text,
                    "source": "openclaw",
                    "desk": desk_id,
                    "completed_at": datetime.now().isoformat(),
                }
                task_record["status"] = "completed"
                task_results.append(result)

                logger.info(f"OpenClaw desk dispatch completed: [{desk_id}] {task_title}")

                # Process result back into desk system
                await handle_openclaw_result(task_id, result)

                return result
            else:
                error_detail = resp.text[:200]
                task_record["status"] = "failed"
                logger.error(f"OpenClaw desk dispatch error {resp.status_code}: {error_detail}")
                return {"status": "failed", "error": f"OpenClaw returned {resp.status_code}: {error_detail}", "task_id": task_id}

    except httpx.ConnectError:
        task_record["status"] = "failed"
        logger.warning(f"OpenClaw not running — desk dispatch failed for [{desk_id}] {task_title}")
        return {"status": "failed", "error": "OpenClaw is not running on port 7878", "task_id": task_id}
    except httpx.ReadTimeout:
        task_record["status"] = "timeout"
        logger.warning(f"OpenClaw timeout — desk dispatch for [{desk_id}] {task_title}")
        return {"status": "failed", "error": f"OpenClaw timed out after {timeout}s", "task_id": task_id}
    except Exception as e:
        task_record["status"] = "failed"
        logger.error(f"OpenClaw desk dispatch exception: {e}")
        return {"status": "failed", "error": str(e), "task_id": task_id}


async def handle_openclaw_result(task_id: str, result: dict) -> None:
    """Process OpenClaw result back into desk task system.

    Updates the in-memory task record and sends a Telegram notification
    if the result is significant (completed or failed with errors).
    """
    try:
        # Update task record in queue
        for task in task_queue:
            if task["task_id"] == task_id:
                task["status"] = result.get("status", "unknown")
                task["completed_at"] = result.get("completed_at", datetime.now().isoformat())
                break

        # Persist to DB if available
        try:
            from app.db.database import get_db
            import json as _json
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO task_activity (task_id, actor, action, detail)
                       VALUES (?, 'openclaw', ?, ?)""",
                    (
                        task_id,
                        f"openclaw_{result.get('status', 'unknown')}",
                        result.get("summary", "")[:500],
                    ),
                )
        except Exception as e:
            logger.warning(f"Failed to persist OpenClaw result to DB: {e}")

        # Notify via Telegram if significant
        status = result.get("status", "unknown")
        desk = result.get("desk", "unknown")
        if status in ("completed", "failed"):
            await _log_notification(
                task_id,
                f"[{desk}] OpenClaw task",
                status,
                result.get("summary", "No summary")[:300],
            )

    except Exception as e:
        logger.warning(f"handle_openclaw_result error: {e}")
