"""
Empire Task Engine — API routes for task CRUD, activity log, and dashboard.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import json

from app.db.database import get_db, dict_row, dict_rows

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── Schemas ──────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "normal"
    desk: str
    business: Optional[str] = None  # 'workroom', 'woodcraft', 'empire'
    assigned_to: Optional[str] = None
    created_by: str = "rg"
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None
    parent_task_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    desk: Optional[str] = None
    business: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None
    parent_task_id: Optional[str] = None


class CommentCreate(BaseModel):
    actor: str = "rg"
    action: str = "comment"
    detail: str
    metadata: Optional[dict] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _enrich_task(task: dict) -> dict:
    """Parse JSON fields in a task row."""
    if task:
        task["tags"] = json.loads(task["tags"]) if task.get("tags") else []
        task["metadata"] = json.loads(task["metadata"]) if task.get("metadata") else {}
    return task


def _log_activity(conn, task_id: str, actor: str, action: str, detail: str = None, metadata: dict = None):
    """Insert a row into task_activity."""
    conn.execute(
        """INSERT INTO task_activity (task_id, actor, action, detail, metadata)
           VALUES (?, ?, ?, ?, ?)""",
        (task_id, actor, action, detail, json.dumps(metadata) if metadata else None),
    )


# ── Routes ───────────────────────────────────────────────────────────

@router.get("/dashboard")
def task_dashboard(business: Optional[str] = None):
    """Cross-desk summary: counts by status per desk. Optionally filter by business."""
    biz_clause = ""
    biz_params: list = []
    if business:
        biz_clause = " AND business = ?"
        biz_params = [business]

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT desk, status, COUNT(*) as count
               FROM tasks WHERE status != 'cancelled'{biz_clause}
               GROUP BY desk, status""",
            biz_params,
        ).fetchall()

        summary = {}
        for r in dict_rows(rows):
            desk = r["desk"]
            if desk not in summary:
                summary[desk] = {"todo": 0, "in_progress": 0, "waiting": 0, "done": 0}
            summary[desk][r["status"]] = r["count"]

        totals = conn.execute(
            f"""SELECT status, COUNT(*) as count
               FROM tasks WHERE status != 'cancelled'{biz_clause}
               GROUP BY status""",
            biz_params,
        ).fetchall()

        return {
            "desks": summary,
            "totals": {r["status"]: r["count"] for r in dict_rows(totals)},
        }


@router.get("/")
def list_tasks(
    desk: Optional[str] = None,
    business: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[str] = None,
    due_before: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List tasks with optional filters."""
    clauses = []
    params = []

    if desk:
        clauses.append("desk = ?")
        params.append(desk)
    if business:
        clauses.append("business = ?")
        params.append(business)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if assigned_to:
        clauses.append("assigned_to = ?")
        params.append(assigned_to)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if due_before:
        clauses.append("due_date <= ?")
        params.append(due_before)
    if parent_task_id:
        clauses.append("parent_task_id = ?")
        params.append(parent_task_id)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT * FROM tasks{where}
                ORDER BY
                    CASE priority
                        WHEN 'urgent' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'normal' THEN 2
                        WHEN 'low' THEN 3
                    END,
                    created_at DESC
                LIMIT ? OFFSET ?""",
            params,
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM tasks{where}", params[:-2]
        ).fetchone()[0]

        return {
            "tasks": [_enrich_task(dict_row(r)) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.post("/")
def create_task(task: TaskCreate):
    """Create a new task."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO tasks
               (id, title, description, status, priority, desk, business, assigned_to,
                created_by, due_date, tags, metadata, parent_task_id)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.title,
                task.description,
                task.status,
                task.priority,
                task.desk,
                task.business,
                task.assigned_to,
                task.created_by,
                task.due_date,
                json.dumps(task.tags) if task.tags else None,
                json.dumps(task.metadata) if task.metadata else None,
                task.parent_task_id,
            ),
        )

        # Get the created task by querying the last insert
        row = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        created = _enrich_task(dict_row(row))

        _log_activity(conn, created["id"], task.created_by, "created", f"Created task: {task.title}")

        return {"task": created}


@router.get("/{task_id}")
def get_task(task_id: str):
    """Get task detail with its activity log."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")

        task = _enrich_task(dict_row(row))

        activity = conn.execute(
            "SELECT * FROM task_activity WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,),
        ).fetchall()
        activity_list = dict_rows(activity)
        for a in activity_list:
            a["metadata"] = json.loads(a["metadata"]) if a.get("metadata") else {}

        # Get subtasks
        subtasks = conn.execute(
            "SELECT * FROM tasks WHERE parent_task_id = ? ORDER BY created_at",
            (task_id,),
        ).fetchall()

        task["activity"] = activity_list
        task["subtasks"] = [_enrich_task(dict_row(s)) for s in subtasks]
        return {"task": task}


@router.patch("/{task_id}")
def update_task(task_id: str, update: TaskUpdate):
    """Update a task. Logs status changes."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")

        old = dict_row(existing)
        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        fields = []
        values = []
        for key, val in data.items():
            if key in ("tags",):
                val = json.dumps(val)
            elif key == "metadata":
                val = json.dumps(val)
            fields.append(f"{key} = ?")
            values.append(val)

        # Auto-set completed_at
        if data.get("status") == "done" and old["status"] != "done":
            fields.append("completed_at = datetime('now')")
        elif data.get("status") and data["status"] != "done":
            fields.append("completed_at = NULL")

        fields.append("updated_at = datetime('now')")
        values.append(task_id)

        conn.execute(
            f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values
        )

        # Log status changes
        if "status" in data and data["status"] != old["status"]:
            _log_activity(
                conn, task_id, "rg", "status_changed",
                f"Status: {old['status']} → {data['status']}"
            )

        # Log assignment changes
        if "assigned_to" in data and data["assigned_to"] != old.get("assigned_to"):
            _log_activity(
                conn, task_id, "rg", "assigned",
                f"Assigned to {data['assigned_to']}"
            )

        return get_task(task_id)


@router.delete("/{task_id}")
def delete_task(task_id: str):
    """Soft delete — sets status to cancelled."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")

        conn.execute(
            "UPDATE tasks SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?",
            (task_id,),
        )
        _log_activity(conn, task_id, "rg", "cancelled", "Task cancelled")
        return {"status": "cancelled", "task_id": task_id}


@router.post("/{task_id}/comment")
def add_comment(task_id: str, comment: CommentCreate):
    """Add a comment or activity entry to a task."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")

        _log_activity(
            conn, task_id, comment.actor, comment.action,
            comment.detail, comment.metadata
        )

        # Update task's updated_at
        conn.execute(
            "UPDATE tasks SET updated_at = datetime('now') WHERE id = ?", (task_id,)
        )
        return {"status": "ok", "task_id": task_id}
