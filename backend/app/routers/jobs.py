"""
Empire Jobs / Production — Job tracking, scheduling, calendar, dashboard.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from pathlib import Path
from datetime import datetime, date, timedelta

from app.db.database import get_db, dict_row, dict_rows

router = APIRouter(prefix="/jobs", tags=["jobs"])

QUOTES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "quotes"


# -- Schemas ----------------------------------------------------------------

class JobCreate(BaseModel):
    title: str
    customer_id: Optional[str] = None
    quote_id: Optional[str] = None
    invoice_id: Optional[str] = None
    status: str = "pending"
    job_type: str = "fabrication"
    priority: str = "normal"
    assigned_to: Optional[str] = None
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    materials_cost: float = 0
    labor_cost: float = 0
    notes: Optional[str] = None
    address: Optional[str] = None
    metadata: Optional[dict] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    customer_id: Optional[str] = None
    quote_id: Optional[str] = None
    invoice_id: Optional[str] = None
    status: Optional[str] = None
    job_type: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    completed_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    materials_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    notes: Optional[str] = None
    address: Optional[str] = None
    metadata: Optional[dict] = None


# -- Helpers ----------------------------------------------------------------

def _enrich_job(job: dict) -> dict:
    """Parse JSON fields in a job row."""
    if job and job.get("metadata"):
        try:
            job["metadata"] = json.loads(job["metadata"])
        except (json.JSONDecodeError, TypeError):
            pass
    return job


# -- Dashboard & Calendar (must be before /{job_id} routes) -----------------

@router.get("/dashboard")
def jobs_dashboard():
    """Summary stats: total jobs, by status, by type, upcoming this week, overdue."""
    today = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        by_status = dict_rows(conn.execute(
            "SELECT status, COUNT(*) as count FROM jobs GROUP BY status ORDER BY count DESC"
        ).fetchall())

        by_type = dict_rows(conn.execute(
            "SELECT job_type, COUNT(*) as count FROM jobs GROUP BY job_type ORDER BY count DESC"
        ).fetchall())

        upcoming_rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.scheduled_date >= ? AND j.scheduled_date <= ?
                 AND j.status NOT IN ('completed', 'cancelled')
               ORDER BY j.scheduled_date ASC""",
            (today, week_end)
        ).fetchall()
        upcoming = [_enrich_job(dict_row(r)) for r in upcoming_rows]

        overdue_rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.due_date < ? AND j.status NOT IN ('completed', 'cancelled')
               ORDER BY j.due_date ASC""",
            (today,)
        ).fetchall()
        overdue = [_enrich_job(dict_row(r)) for r in overdue_rows]

        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "upcoming_this_week": upcoming,
            "overdue": overdue,
        }


@router.get("/calendar")
def jobs_calendar(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Jobs grouped by scheduled_date for calendar view."""
    today = date.today()
    start = date_from or (today - timedelta(days=today.weekday())).isoformat()
    end = date_to or (today + timedelta(days=30)).isoformat()

    with get_db() as conn:
        rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.scheduled_date >= ? AND j.scheduled_date <= ?
               ORDER BY j.scheduled_date ASC""",
            (start, end)
        ).fetchall()

        jobs = [_enrich_job(dict_row(r)) for r in rows]

        # Group by date
        grouped = {}
        for job in jobs:
            d = job.get("scheduled_date", "unscheduled")
            if d not in grouped:
                grouped[d] = []
            grouped[d].append(job)

        return [{"date": d, "jobs": j} for d, j in sorted(grouped.items())]


# -- From Quote -------------------------------------------------------------

@router.post("/from-quote/{quote_id}")
def create_job_from_quote(quote_id: str):
    """Create a job from an existing quote JSON file."""
    quote_file = QUOTES_DIR / f"{quote_id}.json"
    if not quote_file.exists():
        raise HTTPException(status_code=404, detail=f"Quote file not found: {quote_id}")

    with open(quote_file) as f:
        quote = json.load(f)

    # Build description from rooms
    rooms_desc = []
    for room in (quote.get("rooms") or []):
        room_name = room.get("name", "Room")
        windows = [w.get("name", "Window") for w in room.get("windows", [])]
        rooms_desc.append(f"{room_name}: {', '.join(windows)}")
    description = "; ".join(rooms_desc) if rooms_desc else "Job from quote"

    customer_name = quote.get("customer_name", "")
    customer_email = quote.get("customer_email", "")
    customer_id = None

    with get_db() as conn:
        # Look up customer
        if customer_email:
            cust = conn.execute(
                "SELECT id FROM customers WHERE email = ?", (customer_email,)
            ).fetchone()
            if cust:
                customer_id = cust["id"]
        if not customer_id and customer_name:
            cust = conn.execute(
                "SELECT id FROM customers WHERE name = ?", (customer_name,)
            ).fetchone()
            if cust:
                customer_id = cust["id"]

        title = f"Job for {customer_name or 'Unknown'} — {quote.get('quote_number', quote_id)}"

        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, quote_id, status, job_type, notes, metadata)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, 'pending', 'fabrication', ?, ?)""",
            (
                title,
                customer_id,
                quote_id,
                description,
                json.dumps({"source": "quote", "quote_number": quote.get("quote_number")}),
            )
        )

        row = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        job_data = dict_row(row)
        if not job_data:
            raise HTTPException(status_code=500, detail="Job insert succeeded but retrieval failed")
        return {"job": _enrich_job(job_data), "quote_id": quote_id}


# -- Kanban View ------------------------------------------------------------

@router.get("/kanban")
def jobs_kanban():
    """Jobs grouped by status for kanban board view."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               ORDER BY j.priority DESC, j.created_at DESC"""
        ).fetchall()

        jobs = [_enrich_job(dict_row(r)) for r in rows]

        # Group by status
        columns = {}
        for job in jobs:
            status = job.get("status", "pending")
            if status not in columns:
                columns[status] = []
            columns[status].append(job)

        return {
            "columns": [
                {"status": s, "jobs": j, "count": len(j)}
                for s, j in columns.items()
            ],
            "total": len(jobs),
        }


# -- CRUD -------------------------------------------------------------------

@router.get("/")
def list_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    customer_id: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List jobs with optional filters."""
    clauses = []
    params = []

    if status:
        clauses.append("j.status = ?")
        params.append(status)
    if job_type:
        clauses.append("j.job_type = ?")
        params.append(job_type)
    if customer_id:
        clauses.append("j.customer_id = ?")
        params.append(customer_id)
    if priority:
        clauses.append("j.priority = ?")
        params.append(priority)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT j.*, c.name as customer_name
                FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
                {where} ORDER BY j.created_at DESC LIMIT ? OFFSET ?""",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM jobs j{where}", params_count
        ).fetchone()[0]

        jobs = [_enrich_job(dict_row(r)) for r in rows]
        return {"jobs": jobs, "total": total, "limit": limit, "offset": offset}


@router.post("/")
def create_job(job: JobCreate):
    """Create a new job."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, quote_id, invoice_id, status, job_type, priority,
                assigned_to, scheduled_date, due_date, estimated_hours,
                materials_cost, labor_cost, notes, address, metadata)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.title,
                job.customer_id,
                job.quote_id,
                job.invoice_id,
                job.status,
                job.job_type,
                job.priority,
                job.assigned_to,
                job.scheduled_date,
                job.due_date,
                job.estimated_hours,
                job.materials_cost,
                job.labor_cost,
                job.notes,
                job.address,
                json.dumps(job.metadata) if job.metadata else None,
            )
        )

        row = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return {"job": _enrich_job(dict_row(row))}


@router.get("/{job_id}")
def get_job(job_id: str):
    """Get a single job with customer name joined."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT j.*, c.name as customer_name, c.email as customer_email,
                      c.phone as customer_phone, c.address as customer_address
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.id = ?""",
            (job_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        return {"job": _enrich_job(dict_row(row))}


@router.patch("/{job_id}")
def update_job(job_id: str, update: JobUpdate):
    """Update job fields."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Job not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Auto-set completed_date when status changes to completed
        if data.get("status") == "completed" and "completed_date" not in data:
            data["completed_date"] = datetime.now().isoformat()

        fields = []
        values = []
        for key, val in data.items():
            if key == "metadata":
                val = json.dumps(val)
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(job_id)

        conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values
        )

        row = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.id = ?""",
            (job_id,)
        ).fetchone()
        return {"job": _enrich_job(dict_row(row))}


@router.delete("/{job_id}")
def delete_job(job_id: str):
    """Delete a job."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Job not found")

        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return {"status": "deleted", "job_id": job_id}
