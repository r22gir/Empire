"""
Empire Unified Job Pipeline — comprehensive job lifecycle management.

Replaces the basic jobs.py with a full pipeline: intake -> measuring -> designing ->
quoting -> quoted -> approved -> in_production -> installing -> completed -> invoiced -> paid -> closed.

Child tables: job_items, job_documents, job_selections, job_revisions, job_events.
Enhanced invoicing with PDF generation, payment rollup, and revenue tracking.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List
import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime, date, timedelta

from app.db.database import get_db, dict_row, dict_rows

router = APIRouter(tags=["jobs-unified"])

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path(__file__).resolve().parent.parent.parent / "data" / "empire.db"),
)
QUOTES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "quotes"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# ── Status Machine ─────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    "intake": ["measuring"],
    "measuring": ["designing"],
    "designing": ["quoting"],
    "quoting": ["quoted"],
    "quoted": ["approved", "designing"],
    "approved": ["in_production"],
    "in_production": ["installing"],
    "installing": ["completed"],
    "completed": ["invoiced"],
    "invoiced": ["paid"],
    "paid": ["closed"],
}

ALL_STAGES = list(VALID_TRANSITIONS.keys()) + ["closed"]

# ── Business helpers ───────────────────────────────────────────────────

_BUSINESS_ALIASES = {
    "empire workroom": "workroom",
    "workroom": "workroom",
    "woodcraft": "woodcraft",
    "wood craft": "woodcraft",
    "empire": "empire",
}

_BUSINESS_DISPLAY = {
    "workroom": "Empire Workroom",
    "woodcraft": "WoodCraft",
    "empire": "Empire",
}


def _normalise_business(raw: str | None) -> str:
    if not raw:
        return "all"
    return _BUSINESS_ALIASES.get(raw.strip().lower(), raw.strip().lower())


def _quote_business_key(quote: dict) -> str:
    business = _normalise_business(
        quote.get("business_unit") or quote.get("business_name") or "workroom"
    )
    return "workroom" if business == "all" else business


def _find_or_create_customer_for_quote(conn, quote: dict, business_unit: str) -> Optional[str]:
    customer_name = (quote.get("customer_name") or "").strip()
    customer_email = (quote.get("customer_email") or "").strip()
    customer_phone = (quote.get("customer_phone") or "").strip()
    customer_address = (quote.get("customer_address") or "").strip()

    customer_id = None
    if customer_email:
        cust = conn.execute(
            "SELECT id FROM customers WHERE lower(email) = lower(?)",
            (customer_email,),
        ).fetchone()
        if cust:
            customer_id = cust["id"]

    if not customer_id and customer_name:
        cust = conn.execute(
            "SELECT id FROM customers WHERE lower(name) = lower(?)",
            (customer_name,),
        ).fetchone()
        if cust:
            customer_id = cust["id"]

    if customer_id:
        conn.execute(
            """UPDATE customers
               SET email = COALESCE(NULLIF(email, ''), ?),
                   phone = COALESCE(NULLIF(phone, ''), ?),
                   address = COALESCE(NULLIF(address, ''), ?),
                   business = CASE WHEN business IS NULL OR business = '' OR business = 'empire'
                                   THEN ? ELSE business END,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                customer_email or None,
                customer_phone or None,
                customer_address or None,
                business_unit,
                customer_id,
            ),
        )
        return customer_id

    if not customer_name:
        return None

    conn.execute(
        """INSERT INTO customers
           (name, email, phone, address, type, tags, notes, total_revenue,
            lifetime_quotes, source, business)
           VALUES (?, ?, ?, ?, 'residential', '[]', ?, 0, 1, 'quote', ?)""",
        (
            customer_name,
            customer_email or None,
            customer_phone or None,
            customer_address or None,
            quote.get("project_description") or quote.get("notes"),
            business_unit,
        ),
    )
    cust = conn.execute(
        """SELECT id FROM customers
           WHERE name = ? AND COALESCE(email, '') = COALESCE(?, '')
           ORDER BY created_at DESC LIMIT 1""",
        (customer_name, customer_email or None),
    ).fetchone()
    return cust["id"] if cust else None


# ── Schema init ────────────────────────────────────────────────────────

def _safe_alter(conn, table: str, column: str, col_type: str, default=None):
    """Add column if it doesn't already exist."""
    try:
        dflt = f" DEFAULT {default}" if default is not None else ""
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{dflt}")
    except sqlite3.OperationalError:
        pass  # column already exists


def init_schema():
    """Create/alter all tables needed by the unified pipeline."""
    with get_db() as conn:
        # ── ALTER jobs ─────────────────────────────────────────────
        job_cols = {
            "job_number": "TEXT",
            "client_name": "TEXT",
            "client_email": "TEXT",
            "client_phone": "TEXT",
            "client_address": "TEXT",
            "business_unit": "TEXT DEFAULT 'workroom'",
            "room": "TEXT",
            "description": "TEXT",
            "design_session_id": "TEXT",
            "photos": "TEXT",          # JSON
            "measurements": "TEXT",    # JSON
            "items": "TEXT",           # JSON
            "treatment_selections": "TEXT",
            "hardware_selections": "TEXT",
            "fabric_selections": "TEXT",
            "drawings": "TEXT",
            "mockups": "TEXT",
            "pipeline_stage": "TEXT DEFAULT 'intake'",
            "current_revision": "INTEGER DEFAULT 1",
            "estimated_value": "REAL DEFAULT 0",
            "quoted_amount": "REAL DEFAULT 0",
            "invoiced_amount": "REAL DEFAULT 0",
            "paid_amount": "REAL DEFAULT 0",
            "intake_date": "TEXT",
            "site_visit_date": "TEXT",
            "quote_date": "TEXT",
            "approved_date": "TEXT",
            "production_start": "TEXT",
            "install_date": "TEXT",
            "invoiced_date": "TEXT",
            "paid_date": "TEXT",
            "presentation_url": "TEXT",
            "share_link": "TEXT",
        }
        for col, ctype in job_cols.items():
            # split type and default
            parts = ctype.split(" DEFAULT ")
            base_type = parts[0]
            default = parts[1] if len(parts) > 1 else None
            _safe_alter(conn, "jobs", col, base_type, default)

        # ── ALTER invoices ─────────────────────────────────────────
        inv_cols = {
            "job_id": "TEXT",
            "revision": "INTEGER DEFAULT 1",
            "client_name": "TEXT",
            "client_email": "TEXT",
            "client_phone": "TEXT",
            "client_address": "TEXT",
            "billing_address": "TEXT",
            "business_unit": "TEXT DEFAULT 'workroom'",
            "discount_amount": "REAL DEFAULT 0",
            "discount_type": "TEXT DEFAULT 'flat'",
            "deposit_required": "REAL DEFAULT 0",
            "deposit_received": "REAL DEFAULT 0",
            "deposit_date": "TEXT",
            "payment_method": "TEXT",
            "payment_status": "TEXT DEFAULT 'unpaid'",
            "pdf_url": "TEXT",
            "invoice_date": "TEXT",
            "sent_date": "TEXT",
        }
        for col, ctype in inv_cols.items():
            parts = ctype.split(" DEFAULT ")
            base_type = parts[0]
            default = parts[1] if len(parts) > 1 else None
            _safe_alter(conn, "invoices", col, base_type, default)

        # ── ALTER design_sessions ──────────────────────────────────
        _safe_alter(conn, "design_sessions", "job_id", "TEXT")

        # ── ALTER drawing_versions ─────────────────────────────────
        try:
            _safe_alter(conn, "drawing_versions", "job_id", "TEXT")
        except sqlite3.OperationalError:
            pass  # table may not exist

        # ── NEW child tables ───────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_items (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
                job_id TEXT NOT NULL REFERENCES jobs(id),
                item_key TEXT,
                item_type TEXT,
                room TEXT,
                name TEXT,
                measurements TEXT,
                approval_status TEXT DEFAULT 'pending',
                selected_revision INTEGER DEFAULT 1,
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_documents (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
                job_id TEXT NOT NULL REFERENCES jobs(id),
                document_type TEXT,
                item_key TEXT,
                url TEXT,
                filename TEXT,
                revision INTEGER DEFAULT 1,
                visible_to_client INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_selections (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
                job_id TEXT NOT NULL REFERENCES jobs(id),
                item_key TEXT,
                selection_type TEXT,
                selection_code TEXT,
                selection_name TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_revisions (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
                job_id TEXT NOT NULL REFERENCES jobs(id),
                artifact_type TEXT,
                artifact_id TEXT,
                revision INTEGER DEFAULT 1,
                summary TEXT,
                created_by TEXT,
                approved_by TEXT,
                is_client_sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_events (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
                job_id TEXT NOT NULL REFERENCES jobs(id),
                event_type TEXT,
                actor TEXT,
                summary TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoice_payments (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
                invoice_id TEXT NOT NULL REFERENCES invoices(id),
                amount REAL NOT NULL,
                method TEXT,
                reference TEXT,
                notes TEXT,
                recorded_by TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Indexes
        for idx in [
            "CREATE INDEX IF NOT EXISTS idx_job_items_job ON job_items(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_job_docs_job ON job_documents(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_job_sel_job ON job_selections(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_job_rev_job ON job_revisions(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_inv_payments_inv ON invoice_payments(invoice_id)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_pipeline ON jobs(pipeline_stage)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_number ON jobs(job_number)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_business ON jobs(business_unit)",
        ]:
            try:
                conn.execute(idx)
            except sqlite3.OperationalError:
                pass


# Run schema on import
try:
    init_schema()
    print("  ✓ Jobs unified schema ready")
except Exception as e:
    print(f"  ✗ Jobs unified schema: {e}")


# ── Helpers ────────────────────────────────────────────────────────────

def _parse_json_fields(row: dict, fields: list[str]) -> dict:
    """Parse JSON string fields into dicts/lists."""
    if not row:
        return row
    for f in fields:
        if row.get(f) and isinstance(row[f], str):
            try:
                row[f] = json.loads(row[f])
            except (json.JSONDecodeError, TypeError):
                pass
    return row

_JOB_JSON_FIELDS = [
    "metadata", "photos", "measurements", "items",
    "treatment_selections", "hardware_selections",
    "fabric_selections", "drawings", "mockups",
]

_INV_JSON_FIELDS = ["line_items", "metadata"]


def _enrich_job(row):
    if not row:
        return row
    d = dict_row(row) if not isinstance(row, dict) else row
    return _parse_json_fields(d, _JOB_JSON_FIELDS)


def _enrich_invoice(row):
    if not row:
        return row
    d = dict_row(row) if not isinstance(row, dict) else row
    return _parse_json_fields(d, _INV_JSON_FIELDS)


def _next_job_number(conn) -> str:
    """Generate JOB-YYYY-XXXX."""
    year = date.today().year
    prefix = f"JOB-{year}-"
    row = conn.execute(
        "SELECT job_number FROM jobs WHERE job_number LIKE ? ORDER BY job_number DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    if row and row["job_number"]:
        try:
            last = int(row["job_number"].split("-")[-1])
        except ValueError:
            last = 0
        return f"{prefix}{last + 1:04d}"
    return f"{prefix}0001"


def _next_invoice_number(conn) -> str:
    """Generate INV-YYYY-XXXX."""
    year = date.today().year
    prefix = f"INV-{year}-"
    row = conn.execute(
        "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? ORDER BY invoice_number DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    if row and row["invoice_number"]:
        try:
            last = int(row["invoice_number"].split("-")[-1])
        except ValueError:
            last = 0
        return f"{prefix}{last + 1:04d}"
    return f"{prefix}0001"


def _add_event(conn, job_id: str, event_type: str, summary: str,
               actor: str = "system", metadata: dict | None = None):
    """Insert a job_event row."""
    conn.execute(
        """INSERT INTO job_events (id, job_id, event_type, actor, summary, metadata)
           VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?)""",
        (job_id, event_type, actor, summary, json.dumps(metadata) if metadata else None),
    )


# ── Pydantic Schemas ──────────────────────────────────────────────────

class JobCreateSchema(BaseModel):
    title: str
    customer_id: Optional[str] = None
    quote_id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    client_address: Optional[str] = None
    business_unit: str = "workroom"
    room: Optional[str] = None
    description: Optional[str] = None
    job_type: str = "fabrication"
    priority: str = "normal"
    assigned_to: Optional[str] = None
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    estimated_value: Optional[float] = 0
    materials_cost: float = 0
    labor_cost: float = 0
    notes: Optional[str] = None
    address: Optional[str] = None
    metadata: Optional[dict] = None
    pipeline_stage: str = "intake"


class JobUpdateSchema(BaseModel):
    title: Optional[str] = None
    customer_id: Optional[str] = None
    quote_id: Optional[str] = None
    invoice_id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    client_address: Optional[str] = None
    business_unit: Optional[str] = None
    room: Optional[str] = None
    description: Optional[str] = None
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
    estimated_value: Optional[float] = None
    quoted_amount: Optional[float] = None
    notes: Optional[str] = None
    address: Optional[str] = None
    metadata: Optional[dict] = None
    photos: Optional[list] = None
    measurements: Optional[dict] = None
    items: Optional[list] = None
    treatment_selections: Optional[list] = None
    hardware_selections: Optional[list] = None
    fabric_selections: Optional[list] = None
    drawings: Optional[list] = None
    mockups: Optional[list] = None
    design_session_id: Optional[str] = None
    presentation_url: Optional[str] = None
    share_link: Optional[str] = None
    site_visit_date: Optional[str] = None
    install_date: Optional[str] = None


class StatusChange(BaseModel):
    status: str
    actor: str = "founder"
    notes: Optional[str] = None


class ItemCreate(BaseModel):
    item_key: Optional[str] = None
    item_type: Optional[str] = None
    room: Optional[str] = None
    name: str
    measurements: Optional[dict] = None
    status: str = "draft"


class ItemApproval(BaseModel):
    approval_status: str = "approved"
    actor: str = "founder"


class DocumentCreate(BaseModel):
    document_type: str
    item_key: Optional[str] = None
    url: str
    filename: Optional[str] = None
    revision: int = 1
    visible_to_client: bool = False


class SelectionCreate(BaseModel):
    item_key: Optional[str] = None
    selection_type: str
    selection_code: str
    selection_name: Optional[str] = None
    metadata: Optional[dict] = None


class EventCreate(BaseModel):
    event_type: str
    actor: str = "system"
    summary: str
    metadata: Optional[dict] = None


class InvoiceCreateSchema(BaseModel):
    customer_id: Optional[str] = None
    job_id: Optional[str] = None
    quote_id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    client_address: Optional[str] = None
    billing_address: Optional[str] = None
    business_unit: str = "workroom"
    subtotal: float = 0
    tax_rate: float = 0.06
    discount_amount: float = 0
    discount_type: str = "flat"
    deposit_required: float = 0
    line_items: Optional[List[dict]] = None
    notes: Optional[str] = None
    terms: str = "Net 30"
    due_date: Optional[str] = None
    invoice_date: Optional[str] = None


class InvoiceUpdateSchema(BaseModel):
    customer_id: Optional[str] = None
    job_id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    client_address: Optional[str] = None
    billing_address: Optional[str] = None
    business_unit: Optional[str] = None
    status: Optional[str] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    discount_amount: Optional[float] = None
    discount_type: Optional[str] = None
    deposit_required: Optional[float] = None
    deposit_received: Optional[float] = None
    line_items: Optional[List[dict]] = None
    notes: Optional[str] = None
    terms: Optional[str] = None
    due_date: Optional[str] = None
    payment_method: Optional[str] = None


class PaymentRecord(BaseModel):
    amount: float
    method: str = "zelle"
    reference: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: str = "founder"


class InvoiceStatusChange(BaseModel):
    status: str
    actor: str = "founder"


# ══════════════════════════════════════════════════════════════════════
#  JOBS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/jobs/pipeline")
def jobs_pipeline():
    """Jobs grouped by pipeline_stage for kanban/pipeline view."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.pipeline_stage IS NOT NULL
                 AND COALESCE(j.status, '') NOT IN ('cancelled')
               ORDER BY j.created_at DESC"""
        ).fetchall()
        jobs = [_enrich_job(dict_row(r)) for r in rows]

        stages = {}
        for s in ALL_STAGES:
            stages[s] = []
        for job in jobs:
            stage = job.get("pipeline_stage", "intake")
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(job)

        return {
            "stages": [
                {"stage": s, "label": s.replace("_", " ").title(), "jobs": stages[s], "count": len(stages[s])}
                for s in ALL_STAGES if s in stages
            ],
            "total": len(jobs),
        }


@router.get("/jobs/active")
def jobs_active():
    """All non-closed, non-cancelled jobs."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE COALESCE(j.pipeline_stage, 'intake') NOT IN ('closed')
                 AND COALESCE(j.status, '') NOT IN ('cancelled')
               ORDER BY j.created_at DESC"""
        ).fetchall()
        return {"jobs": [_enrich_job(dict_row(r)) for r in rows], "total": len(rows)}


@router.get("/jobs/search")
def jobs_search(q: str = Query(..., min_length=1)):
    """Global search across client name, job number, item names, fabric codes."""
    pattern = f"%{q}%"
    with get_db() as conn:
        rows = conn.execute(
            """SELECT DISTINCT j.*, c.name as customer_name
               FROM jobs j
               LEFT JOIN customers c ON j.customer_id = c.id
               LEFT JOIN job_items ji ON ji.job_id = j.id
               LEFT JOIN job_selections js ON js.job_id = j.id
               WHERE j.client_name LIKE ?
                  OR j.job_number LIKE ?
                  OR j.title LIKE ?
                  OR j.description LIKE ?
                  OR c.name LIKE ?
                  OR ji.name LIKE ?
                  OR js.selection_code LIKE ?
                  OR js.selection_name LIKE ?
               ORDER BY j.created_at DESC
               LIMIT 50""",
            (pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern),
        ).fetchall()
        return {"jobs": [_enrich_job(dict_row(r)) for r in rows], "total": len(rows)}


@router.get("/jobs/dashboard")
def jobs_dashboard():
    """Summary stats for the jobs dashboard."""
    today = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        by_status = dict_rows(conn.execute(
            "SELECT status, COUNT(*) as count FROM jobs GROUP BY status ORDER BY count DESC"
        ).fetchall())

        by_stage = dict_rows(conn.execute(
            "SELECT pipeline_stage, COUNT(*) as count FROM jobs WHERE pipeline_stage IS NOT NULL GROUP BY pipeline_stage"
        ).fetchall())

        by_business = dict_rows(conn.execute(
            "SELECT business_unit, COUNT(*) as count FROM jobs WHERE business_unit IS NOT NULL GROUP BY business_unit"
        ).fetchall())

        total_value = conn.execute(
            "SELECT COALESCE(SUM(estimated_value), 0) FROM jobs WHERE COALESCE(status,'') NOT IN ('cancelled','closed')"
        ).fetchone()[0]

        total_quoted = conn.execute(
            "SELECT COALESCE(SUM(quoted_amount), 0) FROM jobs"
        ).fetchone()[0]

        total_paid = conn.execute(
            "SELECT COALESCE(SUM(paid_amount), 0) FROM jobs"
        ).fetchone()[0]

        upcoming_rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.scheduled_date >= ? AND j.scheduled_date <= ?
                 AND COALESCE(j.status,'') NOT IN ('completed', 'cancelled', 'closed')
               ORDER BY j.scheduled_date ASC LIMIT 10""",
            (today, week_end),
        ).fetchall()

        return {
            "total": total,
            "by_status": by_status,
            "by_stage": by_stage,
            "by_business": by_business,
            "pipeline_value": total_value,
            "total_quoted": total_quoted,
            "total_paid": total_paid,
            "upcoming_this_week": [_enrich_job(dict_row(r)) for r in upcoming_rows],
        }


@router.get("/jobs/calendar")
def jobs_calendar(date_from: Optional[str] = None, date_to: Optional[str] = None):
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
            (start, end),
        ).fetchall()
        jobs = [_enrich_job(dict_row(r)) for r in rows]
        grouped = {}
        for job in jobs:
            d = job.get("scheduled_date", "unscheduled")
            grouped.setdefault(d, []).append(job)
        return [{"date": d, "jobs": j} for d, j in sorted(grouped.items())]


@router.get("/jobs/kanban")
def jobs_kanban():
    """Jobs grouped by status for kanban board view."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               ORDER BY j.priority DESC, j.created_at DESC"""
        ).fetchall()
        jobs = [_enrich_job(dict_row(r)) for r in rows]
        columns = {}
        for job in jobs:
            status = job.get("status", "pending")
            columns.setdefault(status, []).append(job)
        return {
            "columns": [{"status": s, "jobs": j, "count": len(j)} for s, j in columns.items()],
            "total": len(jobs),
        }


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    business_unit: Optional[str] = None,
    client: Optional[str] = None,
    search: Optional[str] = None,
    pipeline_stage: Optional[str] = None,
    job_type: Optional[str] = None,
    customer_id: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all jobs with optional filters."""
    clauses = []
    params: list = []

    if status:
        clauses.append("j.status = ?")
        params.append(status)
    if business_unit:
        clauses.append("j.business_unit = ?")
        params.append(_normalise_business(business_unit))
    if client:
        clauses.append("(j.client_name LIKE ? OR c.name LIKE ?)")
        params.extend([f"%{client}%", f"%{client}%"])
    if search:
        clauses.append("(j.title LIKE ? OR j.job_number LIKE ? OR j.client_name LIKE ? OR j.description LIKE ?)")
        params.extend([f"%{search}%"] * 4)
    if pipeline_stage:
        clauses.append("j.pipeline_stage = ?")
        params.append(pipeline_stage)
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
    count_params = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT j.*, c.name as customer_name
                FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
                {where} ORDER BY j.created_at DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id {where}",
            count_params,
        ).fetchone()[0]

        return {"jobs": [_enrich_job(dict_row(r)) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.post("/jobs")
def create_job(job: JobCreateSchema):
    """Create a new job with auto-generated job_number."""
    with get_db() as conn:
        job_number = _next_job_number(conn)
        job_id = None

        conn.execute(
            """INSERT INTO jobs
               (id, job_number, title, customer_id, quote_id, status, job_type, priority,
                assigned_to, scheduled_date, due_date, estimated_hours,
                materials_cost, labor_cost, notes, address, metadata,
                client_name, client_email, client_phone, client_address,
                business_unit, room, description, pipeline_stage,
                estimated_value, intake_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_number,
                job.title,
                job.customer_id,
                job.quote_id,
                job.pipeline_stage if job.pipeline_stage != "intake" else "pending",
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
                job.client_name,
                job.client_email,
                job.client_phone,
                job.client_address,
                _normalise_business(job.business_unit),
                job.room,
                job.description,
                job.pipeline_stage,
                job.estimated_value or 0,
                datetime.now().isoformat() if job.pipeline_stage == "intake" else None,
            ),
        )

        row = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        result = _enrich_job(dict_row(row))
        job_id = result["id"]

        _add_event(conn, job_id, "created", f"Job {job_number} created", "system",
                   {"pipeline_stage": job.pipeline_stage})

        return {"job": result}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Full job detail with all child data."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT j.*, c.name as customer_name, c.email as customer_email_joined,
                      c.phone as customer_phone_joined, c.address as customer_address_joined
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.id = ?""",
            (job_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        job = _enrich_job(dict_row(row))

        # Child data
        items = [_parse_json_fields(dict_row(r), ["measurements"]) for r in
                 conn.execute("SELECT * FROM job_items WHERE job_id = ? ORDER BY created_at", (job_id,)).fetchall()]

        documents = [dict_row(r) for r in
                     conn.execute("SELECT * FROM job_documents WHERE job_id = ? ORDER BY created_at DESC", (job_id,)).fetchall()]

        selections = [_parse_json_fields(dict_row(r), ["metadata"]) for r in
                      conn.execute("SELECT * FROM job_selections WHERE job_id = ? ORDER BY created_at", (job_id,)).fetchall()]

        events = [_parse_json_fields(dict_row(r), ["metadata"]) for r in
                  conn.execute("SELECT * FROM job_events WHERE job_id = ? ORDER BY created_at DESC LIMIT 50", (job_id,)).fetchall()]

        revisions = [dict_row(r) for r in
                     conn.execute("SELECT * FROM job_revisions WHERE job_id = ? ORDER BY created_at DESC", (job_id,)).fetchall()]

        # Linked invoices
        invoices = [_enrich_invoice(dict_row(r)) for r in
                    conn.execute("SELECT * FROM invoices WHERE job_id = ? ORDER BY created_at DESC", (job_id,)).fetchall()]

        job["items"] = items
        job["documents"] = documents
        job["selections"] = selections
        job["events"] = events
        job["revisions"] = revisions
        job["invoices"] = invoices

        return {"job": job}


@router.put("/jobs/{job_id}")
def update_job(job_id: str, update: JobUpdateSchema):
    """Update job fields."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Job not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        if data.get("status") == "completed" and "completed_date" not in data:
            data["completed_date"] = datetime.now().isoformat()

        json_fields = ["metadata", "photos", "measurements", "items",
                       "treatment_selections", "hardware_selections",
                       "fabric_selections", "drawings", "mockups"]

        fields = []
        values = []
        for key, val in data.items():
            if key in json_fields and val is not None:
                val = json.dumps(val)
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(job_id)

        conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)

        row = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.id = ?""",
            (job_id,),
        ).fetchone()

        _add_event(conn, job_id, "updated", f"Job updated: {', '.join(data.keys())}", "system")

        return {"job": _enrich_job(dict_row(row))}


@router.patch("/jobs/{job_id}/status")
def change_job_status(job_id: str, body: StatusChange):
    """Change job status with pipeline validation."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        job = dict_row(row)
        current_stage = job.get("pipeline_stage", "intake")
        new_stage = body.status

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_stage, [])
        if new_stage not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{current_stage}' to '{new_stage}'. Allowed: {allowed}",
            )

        # Set date milestones
        now = datetime.now().isoformat()
        date_fields = {
            "measuring": "site_visit_date",
            "quoting": "quote_date",
            "approved": "approved_date",
            "in_production": "production_start",
            "installing": "install_date",
            "invoiced": "invoiced_date",
            "paid": "paid_date",
            "completed": "completed_date",
        }

        updates = ["pipeline_stage = ?", "status = ?", "updated_at = datetime('now')"]
        params = [new_stage, new_stage]

        if new_stage in date_fields:
            col = date_fields[new_stage]
            updates.append(f"{col} = ?")
            params.append(now)

        params.append(job_id)
        conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params)

        _add_event(conn, job_id, "status_change",
                   f"Status: {current_stage} -> {new_stage}" + (f" — {body.notes}" if body.notes else ""),
                   body.actor, {"from": current_stage, "to": new_stage})

        updated = conn.execute(
            """SELECT j.*, c.name as customer_name
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id
               WHERE j.id = ?""",
            (job_id,),
        ).fetchone()
        return {"job": _enrich_job(dict_row(updated))}


@router.get("/jobs/{job_id}/timeline")
def job_timeline(job_id: str):
    """All events chronologically."""
    with get_db() as conn:
        exists = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found")

        rows = conn.execute(
            "SELECT * FROM job_events WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ).fetchall()
        return {"events": [_parse_json_fields(dict_row(r), ["metadata"]) for r in rows]}


@router.get("/jobs/{job_id}/documents")
def job_documents(job_id: str):
    """All documents for a job."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM job_documents WHERE job_id = ? ORDER BY created_at DESC",
            (job_id,),
        ).fetchall()
        return {"documents": [dict_row(r) for r in rows]}


@router.get("/jobs/{job_id}/items")
def job_items(job_id: str):
    """All items for a job."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM job_items WHERE job_id = ? ORDER BY created_at",
            (job_id,),
        ).fetchall()
        return {"items": [_parse_json_fields(dict_row(r), ["measurements"]) for r in rows]}


@router.post("/jobs/{job_id}/items")
def add_job_item(job_id: str, item: ItemCreate):
    """Add an item to a job."""
    with get_db() as conn:
        exists = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found")

        conn.execute(
            """INSERT INTO job_items (id, job_id, item_key, item_type, room, name, measurements, status)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, item.item_key, item.item_type, item.room, item.name,
             json.dumps(item.measurements) if item.measurements else None, item.status),
        )

        row = conn.execute(
            "SELECT * FROM job_items WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()

        _add_event(conn, job_id, "item_added", f"Item added: {item.name}")

        return {"item": _parse_json_fields(dict_row(row), ["measurements"])}


@router.patch("/jobs/{job_id}/items/{item_id}/approve")
def approve_job_item(job_id: str, item_id: str, body: ItemApproval):
    """Approve or reject a job item."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM job_items WHERE id = ? AND job_id = ?",
            (item_id, job_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

        conn.execute(
            "UPDATE job_items SET approval_status = ? WHERE id = ?",
            (body.approval_status, item_id),
        )

        _add_event(conn, job_id, "item_approved",
                   f"Item '{dict_row(row)['name']}' {body.approval_status}", body.actor)

        updated = conn.execute("SELECT * FROM job_items WHERE id = ?", (item_id,)).fetchone()
        return {"item": _parse_json_fields(dict_row(updated), ["measurements"])}


@router.post("/jobs/{job_id}/events")
def add_job_event(job_id: str, event: EventCreate):
    """Add an event to a job's timeline."""
    with get_db() as conn:
        exists = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found")

        _add_event(conn, job_id, event.event_type, event.summary, event.actor,
                   event.metadata)

        row = conn.execute(
            "SELECT * FROM job_events WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        return {"event": _parse_json_fields(dict_row(row), ["metadata"])}


@router.post("/jobs/{job_id}/documents")
def add_job_document(job_id: str, doc: DocumentCreate):
    """Add a document to a job."""
    with get_db() as conn:
        exists = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found")

        conn.execute(
            """INSERT INTO job_documents (id, job_id, document_type, item_key, url, filename, revision, visible_to_client)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, doc.document_type, doc.item_key, doc.url, doc.filename,
             doc.revision, 1 if doc.visible_to_client else 0),
        )

        _add_event(conn, job_id, "document_added",
                   f"Document added: {doc.filename or doc.document_type}")

        row = conn.execute(
            "SELECT * FROM job_documents WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        return {"document": dict_row(row)}


@router.post("/jobs/{job_id}/selections")
def add_job_selection(job_id: str, sel: SelectionCreate):
    """Add a selection (fabric, hardware, treatment) to a job."""
    with get_db() as conn:
        exists = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found")

        conn.execute(
            """INSERT INTO job_selections (id, job_id, item_key, selection_type, selection_code, selection_name, metadata)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?)""",
            (job_id, sel.item_key, sel.selection_type, sel.selection_code, sel.selection_name,
             json.dumps(sel.metadata) if sel.metadata else None),
        )

        _add_event(conn, job_id, "selection_added",
                   f"Selection: {sel.selection_type} — {sel.selection_code}")

        row = conn.execute(
            "SELECT * FROM job_selections WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        return {"selection": _parse_json_fields(dict_row(row), ["metadata"])}


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    """Delete a job and all child data."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Job not found")

        for table in ["job_items", "job_documents", "job_selections", "job_revisions", "job_events"]:
            conn.execute(f"DELETE FROM {table} WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return {"status": "deleted", "job_id": job_id}


@router.post("/jobs/from-quote/{quote_id}")
def create_job_from_quote(quote_id: str):
    """Create a job from an existing quote JSON file."""
    quote_file = QUOTES_DIR / f"{quote_id}.json"
    if not quote_file.exists():
        raise HTTPException(status_code=404, detail=f"Quote file not found: {quote_id}")

    with open(quote_file) as f:
        quote = json.load(f)

    rooms_desc = []
    for room in (quote.get("rooms") or []):
        room_name = room.get("name", "Room")
        windows = [w.get("name", "Window") for w in room.get("windows", [])]
        rooms_desc.append(f"{room_name}: {', '.join(windows)}")
    description = "; ".join(rooms_desc) if rooms_desc else "Job from quote"

    customer_name = quote.get("customer_name", "")
    customer_email = quote.get("customer_email", "")
    customer_phone = quote.get("customer_phone", "")
    customer_address = quote.get("customer_address", "")
    business_unit = _quote_business_key(quote)

    with get_db() as conn:
        customer_id = _find_or_create_customer_for_quote(conn, quote, business_unit)

        job_number = _next_job_number(conn)
        title = f"Job for {customer_name or 'Unknown'} — {quote.get('quote_number', quote_id)}"
        total = quote.get("grand_total", quote.get("total", 0))

        conn.execute(
            """INSERT INTO jobs
               (id, job_number, title, customer_id, quote_id, status, job_type, notes, metadata,
                client_name, client_email, client_phone, client_address, business_unit,
                pipeline_stage, quoted_amount, description, quote_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, 'pending', 'fabrication', ?, ?,
                       ?, ?, ?, ?, ?,
                       'quoted', ?, ?, ?)""",
            (
                job_number, title, customer_id, quote_id, description,
                json.dumps({
                    "source": "quote",
                    "quote_number": quote.get("quote_number"),
                    "intake_project_id": quote.get("intake_project_id"),
                    "intake_code": quote.get("intake_code"),
                }),
                customer_name, customer_email, customer_phone, customer_address,
                business_unit, total, description, datetime.now().isoformat(),
            ),
        )

        row = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1").fetchone()
        result = _enrich_job(dict_row(row))
        _add_event(conn, result["id"], "created", f"Job {job_number} created from quote {quote_id}")
        return {"job": result, "quote_id": quote_id}


# ══════════════════════════════════════════════════════════════════════
#  INVOICES ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@router.get("/invoices/overdue")
def invoices_overdue():
    """List overdue invoices."""
    today = date.today().isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT i.*, c.name as customer_name
               FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id
               WHERE i.due_date < ? AND i.status NOT IN ('paid', 'cancelled')
               ORDER BY i.due_date ASC""",
            (today,),
        ).fetchall()
        return {"invoices": [_enrich_invoice(dict_row(r)) for r in rows], "total": len(rows)}


@router.get("/invoices/summary")
def invoices_summary():
    """Revenue summary across all invoices."""
    with get_db() as conn:
        total_invoiced = conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status != 'cancelled'"
        ).fetchone()[0]
        total_paid = conn.execute(
            "SELECT COALESCE(SUM(amount_paid), 0) FROM invoices"
        ).fetchone()[0]
        total_outstanding = conn.execute(
            "SELECT COALESCE(SUM(balance_due), 0) FROM invoices WHERE status NOT IN ('paid', 'cancelled')"
        ).fetchone()[0]
        by_status = dict_rows(conn.execute(
            "SELECT status, COUNT(*) as count, COALESCE(SUM(total), 0) as total_amount FROM invoices GROUP BY status"
        ).fetchall())
        by_business = dict_rows(conn.execute(
            "SELECT business_unit, COUNT(*) as count, COALESCE(SUM(total), 0) as total_amount FROM invoices WHERE business_unit IS NOT NULL GROUP BY business_unit"
        ).fetchall())

        return {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "by_status": by_status,
            "by_business": by_business,
        }


@router.get("/invoices")
def list_invoices(
    status: Optional[str] = None,
    business_unit: Optional[str] = None,
    customer_id: Optional[str] = None,
    job_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List invoices with optional filters."""
    clauses = []
    params: list = []

    if status:
        clauses.append("i.status = ?")
        params.append(status)
    if business_unit:
        clauses.append("i.business_unit = ?")
        params.append(_normalise_business(business_unit))
    if customer_id:
        clauses.append("i.customer_id = ?")
        params.append(customer_id)
    if job_id:
        clauses.append("i.job_id = ?")
        params.append(job_id)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    count_params = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT i.*, c.name as customer_name
                FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id
                {where} ORDER BY i.created_at DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM invoices i {where}", count_params,
        ).fetchone()[0]

        return {"invoices": [_enrich_invoice(dict_row(r)) for r in rows], "total": total}


@router.post("/invoices")
def create_invoice(inv: InvoiceCreateSchema):
    """Create a new invoice."""
    with get_db() as conn:
        inv_number = _next_invoice_number(conn)

        subtotal = inv.subtotal
        discount = inv.discount_amount if inv.discount_type == "flat" else subtotal * (inv.discount_amount / 100)
        taxable = subtotal - discount
        tax_amount = round(taxable * inv.tax_rate, 2)
        total = round(taxable + tax_amount, 2)
        due = inv.due_date or (date.today() + timedelta(days=30)).isoformat()

        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, quote_id, job_id, status,
                subtotal, tax_rate, tax_amount, total, amount_paid, balance_due,
                line_items, notes, terms, due_date,
                client_name, client_email, client_phone, client_address, billing_address,
                business_unit, discount_amount, discount_type, deposit_required,
                invoice_date, payment_status)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, 'draft',
                       ?, ?, ?, ?, 0, ?,
                       ?, ?, ?, ?,
                       ?, ?, ?, ?, ?,
                       ?, ?, ?, ?,
                       ?, 'unpaid')""",
            (
                inv_number, inv.customer_id, inv.quote_id, inv.job_id,
                subtotal, inv.tax_rate, tax_amount, total, total,
                json.dumps(inv.line_items) if inv.line_items else None,
                inv.notes, inv.terms, due,
                inv.client_name, inv.client_email, inv.client_phone,
                inv.client_address, inv.billing_address,
                _normalise_business(inv.business_unit), inv.discount_amount,
                inv.discount_type, inv.deposit_required,
                inv.invoice_date or date.today().isoformat(),
            ),
        )

        row = conn.execute(
            "SELECT * FROM invoices ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        result = _enrich_invoice(dict_row(row))

        # If linked to a job, update job and add event
        if inv.job_id:
            conn.execute(
                "UPDATE jobs SET invoiced_amount = COALESCE(invoiced_amount, 0) + ?, invoice_id = ?, updated_at = datetime('now') WHERE id = ?",
                (total, result["id"], inv.job_id),
            )
            _add_event(conn, inv.job_id, "invoice_created",
                       f"Invoice {inv_number} created — ${total:,.2f}")

        return {"invoice": result}


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """Get invoice detail with payments."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT i.*, c.name as customer_name
               FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id
               WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")

        inv = _enrich_invoice(dict_row(row))

        payments = [dict_row(r) for r in conn.execute(
            "SELECT * FROM invoice_payments WHERE invoice_id = ? ORDER BY created_at DESC",
            (invoice_id,),
        ).fetchall()]

        inv["payments"] = payments
        return {"invoice": inv}


@router.put("/invoices/{invoice_id}")
def update_invoice(invoice_id: str, update: InvoiceUpdateSchema):
    """Update invoice fields."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Invoice not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        if "line_items" in data and data["line_items"] is not None:
            data["line_items"] = json.dumps(data["line_items"])

        # Recalculate totals if subtotal or tax changed
        if "subtotal" in data or "tax_rate" in data or "discount_amount" in data:
            cur = dict_row(conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
            subtotal = data.get("subtotal", cur["subtotal"])
            tax_rate = data.get("tax_rate", cur["tax_rate"])
            disc_amount = data.get("discount_amount", cur.get("discount_amount", 0) or 0)
            disc_type = data.get("discount_type", cur.get("discount_type", "flat") or "flat")
            discount = disc_amount if disc_type == "flat" else subtotal * (disc_amount / 100)
            taxable = subtotal - discount
            data["tax_amount"] = round(taxable * tax_rate, 2)
            data["total"] = round(taxable + data["tax_amount"], 2)
            data["balance_due"] = round(data["total"] - (cur.get("amount_paid", 0) or 0), 2)

        fields = []
        values = []
        for key, val in data.items():
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(invoice_id)

        conn.execute(f"UPDATE invoices SET {', '.join(fields)} WHERE id = ?", values)

        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        return {"invoice": _enrich_invoice(dict_row(row))}


@router.patch("/invoices/{invoice_id}/status")
def change_invoice_status(invoice_id: str, body: InvoiceStatusChange):
    """Change invoice status."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")

        inv = dict_row(row)
        now = datetime.now().isoformat()

        updates = ["status = ?", "updated_at = datetime('now')"]
        params = [body.status]

        if body.status == "sent":
            updates.append("sent_at = ?")
            params.append(now)
            updates.append("sent_date = ?")
            params.append(now)
        elif body.status == "paid":
            updates.append("paid_at = ?")
            params.append(now)
            updates.append("payment_status = 'paid'")

        params.append(invoice_id)
        conn.execute(f"UPDATE invoices SET {', '.join(updates)} WHERE id = ?", params)

        updated = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        return {"invoice": _enrich_invoice(dict_row(updated))}


@router.post("/invoices/{invoice_id}/payments")
def record_payment(invoice_id: str, payment: PaymentRecord):
    """Record a payment. Rolls up to invoice, job, and customer."""
    with get_db() as conn:
        inv_row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not inv_row:
            raise HTTPException(status_code=404, detail="Invoice not found")

        inv = dict_row(inv_row)

        # Insert payment record
        conn.execute(
            """INSERT INTO invoice_payments (id, invoice_id, amount, method, reference, notes, recorded_by)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?)""",
            (invoice_id, payment.amount, payment.method, payment.reference,
             payment.notes, payment.recorded_by),
        )

        # Update invoice
        new_paid = (inv.get("amount_paid") or 0) + payment.amount
        new_balance = round((inv.get("total") or 0) - new_paid, 2)
        new_status = "paid" if new_balance <= 0 else "partial"
        payment_status = "paid" if new_balance <= 0 else "partial"

        update_parts = [
            "amount_paid = ?", "balance_due = ?", "status = ?",
            "payment_status = ?", "payment_method = ?", "updated_at = datetime('now')",
        ]
        update_params = [new_paid, max(new_balance, 0), new_status, payment_status, payment.method]

        if new_balance <= 0:
            update_parts.append("paid_at = ?")
            update_params.append(datetime.now().isoformat())

        update_params.append(invoice_id)
        conn.execute(f"UPDATE invoices SET {', '.join(update_parts)} WHERE id = ?", update_params)

        # Rollup to job
        job_id = inv.get("job_id")
        if job_id:
            conn.execute(
                "UPDATE jobs SET paid_amount = COALESCE(paid_amount, 0) + ?, updated_at = datetime('now') WHERE id = ?",
                (payment.amount, job_id),
            )
            _add_event(conn, job_id, "payment_received",
                       f"Payment ${payment.amount:,.2f} via {payment.method} on invoice {inv.get('invoice_number', '')}",
                       payment.recorded_by,
                       {"amount": payment.amount, "method": payment.method, "invoice_id": invoice_id})

        # Rollup to customer
        customer_id = inv.get("customer_id")
        if customer_id:
            conn.execute(
                "UPDATE customers SET total_revenue = COALESCE(total_revenue, 0) + ?, updated_at = datetime('now') WHERE id = ?",
                (payment.amount, customer_id),
            )

        # Return updated invoice
        updated = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        pay_row = conn.execute(
            "SELECT * FROM invoice_payments WHERE invoice_id = ? ORDER BY created_at DESC LIMIT 1",
            (invoice_id,),
        ).fetchone()
        pay = dict_row(pay_row)
        finance_method = payment.method if payment.method in {
            "cash", "check", "card", "zelle", "venmo", "wire", "crypto", "other",
        } else "other"
        conn.execute(
            """INSERT OR IGNORE INTO payments
               (id, invoice_id, customer_id, amount, method, reference, notes, payment_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pay["id"],
                invoice_id,
                customer_id,
                payment.amount,
                finance_method,
                payment.reference,
                payment.notes,
                date.today().isoformat(),
            ),
        )

        return {
            "invoice": _enrich_invoice(dict_row(updated)),
            "payment": pay,
            "message": f"Payment of ${payment.amount:,.2f} recorded. Balance: ${max(new_balance, 0):,.2f}",
        }


@router.get("/invoices/{invoice_id}/payments")
def list_payments(invoice_id: str):
    """List all payments for an invoice."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM invoice_payments WHERE invoice_id = ? ORDER BY created_at DESC",
            (invoice_id,),
        ).fetchall()
        return {"payments": [dict_row(r) for r in rows]}


@router.post("/invoices/from-quote/{quote_id}")
def invoice_from_quote(quote_id: str):
    """Auto-create invoice from a quote JSON file."""
    quote_file = QUOTES_DIR / f"{quote_id}.json"
    if not quote_file.exists():
        raise HTTPException(status_code=404, detail=f"Quote not found: {quote_id}")

    with open(quote_file) as f:
        quote = json.load(f)

    customer_name = quote.get("customer_name", "")
    customer_email = quote.get("customer_email", "")
    line_items = []

    for room in (quote.get("rooms") or []):
        for window in room.get("windows", []):
            line_items.append({
                "description": f"{room.get('name', 'Room')} — {window.get('name', 'Window')} — {window.get('treatment', 'Treatment')}",
                "quantity": 1,
                "unit_price": window.get("total", 0),
                "total": window.get("total", 0),
            })

    subtotal = quote.get("subtotal", sum(i["total"] for i in line_items))
    tax_rate = quote.get("tax_rate", 0.06)
    business = quote.get("business_name", "Empire Workroom")

    with get_db() as conn:
        customer_id = None
        if customer_email:
            cust = conn.execute("SELECT id FROM customers WHERE email = ?", (customer_email,)).fetchone()
            if cust:
                customer_id = cust["id"]
        if not customer_id and customer_name:
            cust = conn.execute("SELECT id FROM customers WHERE name = ?", (customer_name,)).fetchone()
            if cust:
                customer_id = cust["id"]

        # Check for linked job
        job_id = None
        job_row = conn.execute("SELECT id FROM jobs WHERE quote_id = ? LIMIT 1", (quote_id,)).fetchone()
        if job_row:
            job_id = job_row["id"]

        inv_number = _next_invoice_number(conn)
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)
        due = (date.today() + timedelta(days=30)).isoformat()

        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, quote_id, job_id, status,
                subtotal, tax_rate, tax_amount, total, amount_paid, balance_due,
                line_items, notes, terms, due_date,
                client_name, client_email, business_unit,
                invoice_date, payment_status)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, 'draft',
                       ?, ?, ?, ?, 0, ?,
                       ?, ?, 'Net 30', ?,
                       ?, ?, ?,
                       ?, 'unpaid')""",
            (
                inv_number, customer_id, quote_id, job_id,
                subtotal, tax_rate, tax_amount, total, total,
                json.dumps(line_items),
                f"Invoice from quote {quote.get('quote_number', quote_id)}",
                due,
                customer_name, customer_email, _normalise_business(business),
                date.today().isoformat(),
            ),
        )

        row = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 1").fetchone()
        result = _enrich_invoice(dict_row(row))

        if job_id:
            conn.execute(
                "UPDATE jobs SET invoiced_amount = COALESCE(invoiced_amount, 0) + ?, invoice_id = ?, updated_at = datetime('now') WHERE id = ?",
                (total, result["id"], job_id),
            )
            _add_event(conn, job_id, "invoice_created",
                       f"Invoice {inv_number} created from quote — ${total:,.2f}")

        return {"invoice": result, "quote_id": quote_id}


@router.post("/invoices/from-job/{job_id}")
def invoice_from_job(job_id: str):
    """Auto-create invoice from a job's data."""
    with get_db() as conn:
        job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job_row:
            raise HTTPException(status_code=404, detail="Job not found")

        job = _enrich_job(dict_row(job_row))

        # Build line items from job items
        line_items = []
        item_rows = conn.execute("SELECT * FROM job_items WHERE job_id = ?", (job_id,)).fetchall()
        if item_rows:
            for item in item_rows:
                item_d = dict_row(item)
                line_items.append({
                    "description": item_d.get("name", "Item"),
                    "quantity": 1,
                    "unit_price": 0,
                    "total": 0,
                })

        subtotal = job.get("quoted_amount") or job.get("estimated_value") or (job.get("materials_cost", 0) + job.get("labor_cost", 0))

        if not line_items:
            line_items = [{"description": job.get("title", "Services"), "quantity": 1,
                           "unit_price": subtotal, "total": subtotal}]
        else:
            # Distribute subtotal evenly if items have no prices
            per_item = round(subtotal / len(line_items), 2) if line_items else subtotal
            for item in line_items:
                if item["total"] == 0:
                    item["unit_price"] = per_item
                    item["total"] = per_item

        inv_number = _next_invoice_number(conn)
        tax_rate = 0.06
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)
        due = (date.today() + timedelta(days=30)).isoformat()

        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, quote_id, job_id, status,
                subtotal, tax_rate, tax_amount, total, amount_paid, balance_due,
                line_items, notes, terms, due_date,
                client_name, client_email, client_phone, client_address,
                business_unit, invoice_date, payment_status)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, 'draft',
                       ?, ?, ?, ?, 0, ?,
                       ?, ?, 'Net 30', ?,
                       ?, ?, ?, ?,
                       ?, ?, 'unpaid')""",
            (
                inv_number, job.get("customer_id"), job.get("quote_id"), job_id,
                subtotal, tax_rate, tax_amount, total, total,
                json.dumps(line_items),
                f"Invoice for job {job.get('job_number', job_id)}",
                due,
                job.get("client_name"), job.get("client_email"),
                job.get("client_phone"), job.get("client_address"),
                job.get("business_unit", "workroom"),
                date.today().isoformat(),
            ),
        )

        row = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 1").fetchone()
        result = _enrich_invoice(dict_row(row))

        # Update job
        conn.execute(
            "UPDATE jobs SET invoiced_amount = COALESCE(invoiced_amount, 0) + ?, invoice_id = ?, updated_at = datetime('now') WHERE id = ?",
            (total, result["id"], job_id),
        )
        _add_event(conn, job_id, "invoice_created",
                   f"Invoice {inv_number} created — ${total:,.2f}")

        return {"invoice": result, "job_id": job_id}


# ══════════════════════════════════════════════════════════════════════
#  INVOICE PDF
# ══════════════════════════════════════════════════════════════════════

@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: str):
    """Generate a professional branded PDF for an invoice using WeasyPrint."""
    try:
        import weasyprint
    except ImportError:
        raise HTTPException(status_code=503, detail="WeasyPrint not installed")

    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")

        inv = _enrich_invoice(dict_row(row))

        customer = None
        if inv.get("customer_id"):
            cust_row = conn.execute("SELECT * FROM customers WHERE id = ?", (inv["customer_id"],)).fetchone()
            if cust_row:
                customer = dict_row(cust_row)

        payments = [dict_row(r) for r in conn.execute(
            "SELECT * FROM invoice_payments WHERE invoice_id = ? ORDER BY created_at",
            (invoice_id,),
        ).fetchall()]

        # Linked job info
        job = None
        if inv.get("job_id"):
            job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (inv["job_id"],)).fetchone()
            if job_row:
                job = dict_row(job_row)

    # ── Business branding ──────────────────────────────────────────
    biz_unit = inv.get("business_unit", "workroom") or "workroom"
    is_woodcraft = biz_unit in ("woodcraft", "wood craft", "craftforge")

    if not is_woodcraft and customer and customer.get("business") == "woodcraft":
        is_woodcraft = True

    biz_cfg = {}
    cfg_file = CONFIG_DIR / ("woodcraft_business.json" if is_woodcraft else "business.json")
    try:
        biz_cfg = json.loads(cfg_file.read_text())
    except Exception:
        pass

    biz_name = biz_cfg.get("business_name", "WoodCraft" if is_woodcraft else "Empire Workroom")
    biz_tagline = biz_cfg.get("business_tagline", "Custom Woodwork & CNC" if is_woodcraft else "Custom Window Treatments & Upholstery")
    biz_phone = biz_cfg.get("business_phone", "")
    biz_email = biz_cfg.get("business_email", "")
    biz_address = biz_cfg.get("business_address", "")
    biz_website = biz_cfg.get("business_website", "")

    accent = "#d4a636" if is_woodcraft else "#b8960c"
    header_bg = "#3d2e1a" if is_woodcraft else "#2c2416"

    # ── Client info ────────────────────────────────────────────────
    client_name = inv.get("client_name") or (customer["name"] if customer else "Customer")
    client_email = inv.get("client_email") or (customer.get("email", "") if customer else "")
    client_phone = inv.get("client_phone") or (customer.get("phone", "") if customer else "")
    client_addr = inv.get("client_address") or inv.get("billing_address") or (customer.get("address", "") if customer else "")

    client_block = f"<strong>{client_name}</strong>"
    if client_email:
        client_block += f"<br>{client_email}"
    if client_phone:
        client_block += f"<br>{client_phone}"
    if client_addr:
        client_block += f"<br>{client_addr}"

    # ── Line items ─────────────────────────────────────────────────
    items_html = ""
    for item in inv.get("line_items") or []:
        desc = item.get("description", "")
        # Include fabric/hardware details if present
        details = []
        if item.get("fabric"):
            details.append(f"Fabric: {item['fabric']}")
        if item.get("hardware"):
            details.append(f"Hardware: {item['hardware']}")
        if details:
            desc += f"<br><span style='font-size:9pt;color:#888'>{' | '.join(details)}</span>"

        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", item.get("rate", 0))
        total = item.get("total", item.get("amount", 0))
        items_html += f"""<tr>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd">{desc}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:center">{qty}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:right">${unit_price:,.2f}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:right">${total:,.2f}</td>
        </tr>"""

    if not items_html:
        items_html = f"""<tr>
            <td style="padding:10px 12px" colspan="3">Services as quoted</td>
            <td style="padding:10px 12px;text-align:right">${inv.get('subtotal', 0):,.2f}</td>
        </tr>"""

    # ── Discount row ───────────────────────────────────────────────
    discount_html = ""
    disc_amt = inv.get("discount_amount", 0) or 0
    if disc_amt > 0:
        disc_type = inv.get("discount_type", "flat")
        if disc_type == "percent":
            disc_display = f"Discount ({disc_amt}%)"
            disc_value = round(inv.get("subtotal", 0) * disc_amt / 100, 2)
        else:
            disc_display = "Discount"
            disc_value = disc_amt
        discount_html = f"""<tr>
            <td style="padding:6px 12px;color:#dc2626">{disc_display}</td>
            <td style="padding:6px 12px;text-align:right;color:#dc2626">-${disc_value:,.2f}</td>
        </tr>"""

    # ── Deposit info ───────────────────────────────────────────────
    deposit_html = ""
    dep_req = inv.get("deposit_required", 0) or 0
    dep_recv = inv.get("deposit_received", 0) or 0
    if dep_req > 0:
        deposit_html = f"""
        <tr><td style="padding:6px 12px">Deposit Required</td>
            <td style="padding:6px 12px;text-align:right">${dep_req:,.2f}</td></tr>
        <tr><td style="padding:6px 12px">Deposit Received</td>
            <td style="padding:6px 12px;text-align:right">${dep_recv:,.2f}</td></tr>"""

    # ── Payments table ─────────────────────────────────────────────
    payments_html = ""
    if payments:
        payments_html = """<div style="margin-top:20px">
        <h3 style="font-size:11pt;color:""" + accent + """;margin-bottom:8px">Payments Received</h3>
        <table style="width:100%;border-collapse:collapse">
        <tr style="background:#f5f3ef">
            <th style="padding:6px 10px;text-align:left;font-size:9pt">Date</th>
            <th style="padding:6px 10px;text-align:left;font-size:9pt">Method</th>
            <th style="padding:6px 10px;text-align:left;font-size:9pt">Reference</th>
            <th style="padding:6px 10px;text-align:right;font-size:9pt">Amount</th>
        </tr>"""
        for p in payments:
            payments_html += f"""<tr>
                <td style="padding:6px 10px;border-bottom:1px solid #eee">{p.get('created_at', '')[:10]}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee">{p.get('method', '')}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee">{p.get('reference', '') or ''}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right">${p.get('amount', 0):,.2f}</td>
            </tr>"""
        payments_html += "</table></div>"

    # ── Job info block ─────────────────────────────────────────────
    job_html = ""
    if job:
        job_html = f"""<div class="info-box">
            <h3>Job Details</h3>
            <div>{job.get('job_number', '')}</div>
            <div>{job.get('title', '')}</div>
            <div>{job.get('description', '') or ''}</div>
        </div>"""

    status_color = {
        "draft": "#888", "sent": "#2563eb", "partial": "#d97706",
        "paid": "#16a34a", "overdue": "#dc2626", "cancelled": "#6b7280",
    }.get(inv.get("status", "draft"), "#888")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: letter; margin: 0.75in; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; font-size: 11pt; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 3px solid {accent}; }}
  .logo {{ font-size: 24pt; font-weight: 800; color: #1a1a2e; }}
  .logo span {{ color: {accent}; }}
  .tagline {{ font-size: 9pt; color: #888; margin-top: 2px; }}
  .invoice-title {{ text-align: right; }}
  .invoice-title h1 {{ margin: 0; font-size: 28pt; color: {accent}; letter-spacing: 2px; }}
  .invoice-number {{ font-size: 11pt; color: #666; margin-top: 4px; }}
  .status {{ display: inline-block; padding: 3px 12px; border-radius: 12px; font-size: 9pt; font-weight: 600; text-transform: uppercase; color: white; background: {status_color}; }}
  .info-grid {{ display: flex; justify-content: space-between; margin: 24px 0; gap: 20px; }}
  .info-box {{ flex: 1; }}
  .info-box h3 {{ margin: 0 0 6px; font-size: 9pt; text-transform: uppercase; color: {accent}; letter-spacing: 1px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  thead {{ background: #f5f3ef; }}
  th {{ padding: 10px 12px; text-align: left; font-size: 9pt; text-transform: uppercase; color: #666; letter-spacing: 0.5px; border-bottom: 2px solid {accent}; }}
  .totals {{ margin-left: auto; width: 280px; }}
  .totals tr td {{ padding: 6px 12px; }}
  .totals .total-row {{ font-size: 14pt; font-weight: 700; color: #1a1a2e; border-top: 2px solid {accent}; }}
  .totals .balance-row {{ font-size: 13pt; font-weight: 700; color: #dc2626; }}
  .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e8e4dd; font-size: 9pt; color: #888; text-align: center; }}
  .payment-methods {{ margin-top: 20px; padding: 15px; background: #f9f8f5; border-radius: 8px; font-size: 10pt; }}
  .payment-methods h3 {{ margin: 0 0 8px; font-size: 10pt; color: {accent}; }}
</style>
</head><body>

<div class="header">
  <div>
    <div class="logo">{'<span>Wood</span>Craft' if is_woodcraft else '<span>Empire</span> Workroom'}</div>
    <div class="tagline">{biz_tagline}</div>
    <div style="font-size:9pt;color:#666;margin-top:4px">
      {biz_phone}{'<br>' if biz_phone else ''}{biz_email}{'<br>' if biz_email else ''}{biz_address}
    </div>
  </div>
  <div class="invoice-title">
    <h1>INVOICE</h1>
    <div class="invoice-number">{inv.get('invoice_number', '')}</div>
    <div style="margin-top:6px"><span class="status">{inv.get('status', 'draft')}</span></div>
  </div>
</div>

<div class="info-grid">
  <div class="info-box">
    <h3>Bill To</h3>
    {client_block}
  </div>
  {job_html}
  <div class="info-box" style="text-align:right">
    <h3>Invoice Details</h3>
    <div><strong>Date:</strong> {inv.get('invoice_date', inv.get('created_at', '')[:10])}</div>
    <div><strong>Due:</strong> {inv.get('due_date', '')}</div>
    <div><strong>Terms:</strong> {inv.get('terms', 'Net 30')}</div>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width:50%">Description</th>
      <th style="text-align:center">Qty</th>
      <th style="text-align:right">Unit Price</th>
      <th style="text-align:right">Amount</th>
    </tr>
  </thead>
  <tbody>
    {items_html}
  </tbody>
</table>

<table class="totals">
  <tr>
    <td>Subtotal</td>
    <td style="text-align:right">${inv.get('subtotal', 0):,.2f}</td>
  </tr>
  {discount_html}
  <tr>
    <td>Tax ({(inv.get('tax_rate', 0) or 0) * 100:.1f}%)</td>
    <td style="text-align:right">${inv.get('tax_amount', 0):,.2f}</td>
  </tr>
  <tr class="total-row">
    <td style="padding-top:10px"><strong>Total</strong></td>
    <td style="text-align:right;padding-top:10px"><strong>${inv.get('total', 0):,.2f}</strong></td>
  </tr>
  {deposit_html}
  <tr>
    <td>Amount Paid</td>
    <td style="text-align:right">${inv.get('amount_paid', 0):,.2f}</td>
  </tr>
  <tr class="balance-row">
    <td><strong>Balance Due</strong></td>
    <td style="text-align:right"><strong>${inv.get('balance_due', 0):,.2f}</strong></td>
  </tr>
</table>

{payments_html}

<div class="payment-methods">
  <h3>Payment Methods Accepted</h3>
  <div><strong>Zelle:</strong> {biz_email or 'Contact for details'}</div>
  <div><strong>Check:</strong> Made payable to {biz_name}</div>
  <div><strong>Credit/Debit Card:</strong> Contact us for card payment link</div>
</div>

<div class="footer">
  <div>{biz_name} &mdash; {biz_tagline}</div>
  <div>{biz_website}</div>
  <div style="margin-top:6px">Thank you for your business!</div>
</div>

</body></html>"""

    pdf = weasyprint.HTML(string=html).write_pdf()

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=invoice-{inv.get('invoice_number', invoice_id)}.pdf",
        },
    )
