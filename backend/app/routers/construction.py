"""
ConstructionForge — Real estate land development module.
Colombian country home developments: projects, phases, lots, buyers,
sales pipeline, payments, construction progress, contractors,
infrastructure, and materials tracking.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import sqlite3
import json
import uuid
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/construction", tags=["construction"])

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# ── Database helpers ─────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    # Parse JSON fields
    for key in ("features", "payment_plan", "photos"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def rows_to_list(rows):
    return [row_to_dict(r) for r in rows]


# ── Table init ───────────────────────────────────────────────────────

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cf_projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            total_area_m2 REAL,
            total_lots INTEGER DEFAULT 0,
            status TEXT DEFAULT 'planning',
            currency TEXT DEFAULT 'COP',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cf_phases (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            phase_number INTEGER DEFAULT 1,
            total_lots INTEGER DEFAULT 0,
            status TEXT DEFAULT 'planning',
            start_date TEXT,
            target_completion TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES cf_projects(id)
        );

        CREATE TABLE IF NOT EXISTS cf_lots (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            phase_id TEXT,
            lot_number TEXT NOT NULL,
            block TEXT,
            area_m2 REAL,
            frontage_m REAL,
            depth_m REAL,
            orientation TEXT,
            features TEXT DEFAULT '[]',
            base_price REAL DEFAULT 0,
            current_price REAL DEFAULT 0,
            status TEXT DEFAULT 'available',
            reserved_at TEXT,
            reserved_by TEXT,
            sold_at TEXT,
            sold_to TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES cf_projects(id),
            FOREIGN KEY (phase_id) REFERENCES cf_phases(id)
        );

        CREATE TABLE IF NOT EXISTS cf_buyers (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            cedula TEXT,
            email TEXT,
            phone TEXT,
            whatsapp TEXT,
            address TEXT,
            city TEXT,
            country TEXT DEFAULT 'Colombia',
            buyer_type TEXT DEFAULT 'individual',
            referral_source TEXT,
            referred_by TEXT,
            notes TEXT,
            locale TEXT DEFAULT 'es',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cf_sales (
            id TEXT PRIMARY KEY,
            lot_id TEXT NOT NULL,
            buyer_id TEXT NOT NULL,
            agent_id TEXT,
            sale_price REAL NOT NULL,
            currency TEXT DEFAULT 'COP',
            payment_plan TEXT DEFAULT '{}',
            contract_type TEXT,
            contract_date TEXT,
            contract_document TEXT,
            down_payment REAL DEFAULT 0,
            down_payment_received INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (lot_id) REFERENCES cf_lots(id),
            FOREIGN KEY (buyer_id) REFERENCES cf_buyers(id)
        );

        CREATE TABLE IF NOT EXISTS cf_payments (
            id TEXT PRIMARY KEY,
            sale_id TEXT NOT NULL,
            buyer_id TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'COP',
            payment_method TEXT,
            payment_date TEXT,
            due_date TEXT,
            installment_number INTEGER,
            status TEXT DEFAULT 'pending',
            receipt_number TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (sale_id) REFERENCES cf_sales(id),
            FOREIGN KEY (buyer_id) REFERENCES cf_buyers(id)
        );

        CREATE TABLE IF NOT EXISTS cf_construction (
            id TEXT PRIMARY KEY,
            lot_id TEXT NOT NULL,
            phase TEXT DEFAULT 'cimentacion',
            status TEXT DEFAULT 'pending',
            start_date TEXT,
            completion_date TEXT,
            contractor_id TEXT,
            inspector_notes TEXT,
            progress_percent INTEGER DEFAULT 0,
            photos TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (lot_id) REFERENCES cf_lots(id),
            FOREIGN KEY (contractor_id) REFERENCES cf_contractors(id)
        );

        CREATE TABLE IF NOT EXISTS cf_contractors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT,
            cedula_nit TEXT,
            specialty TEXT,
            phone TEXT,
            whatsapp TEXT,
            email TEXT,
            rating REAL DEFAULT 0,
            active_lots INTEGER DEFAULT 0,
            total_completed INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cf_infrastructure (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            phase_id TEXT,
            type TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'planned',
            contractor_id TEXT,
            budget REAL DEFAULT 0,
            actual_cost REAL DEFAULT 0,
            start_date TEXT,
            completion_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES cf_projects(id),
            FOREIGN KEY (phase_id) REFERENCES cf_phases(id),
            FOREIGN KEY (contractor_id) REFERENCES cf_contractors(id)
        );

        CREATE TABLE IF NOT EXISTS cf_materials (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            unit_cost REAL DEFAULT 0,
            supplier TEXT,
            stock_on_site REAL DEFAULT 0,
            reorder_point REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES cf_projects(id)
        );

        CREATE INDEX IF NOT EXISTS idx_cf_lots_project ON cf_lots(project_id);
        CREATE INDEX IF NOT EXISTS idx_cf_lots_status ON cf_lots(status);
        CREATE INDEX IF NOT EXISTS idx_cf_sales_lot ON cf_sales(lot_id);
        CREATE INDEX IF NOT EXISTS idx_cf_sales_buyer ON cf_sales(buyer_id);
        CREATE INDEX IF NOT EXISTS idx_cf_payments_sale ON cf_payments(sale_id);
        CREATE INDEX IF NOT EXISTS idx_cf_payments_status ON cf_payments(status);
        CREATE INDEX IF NOT EXISTS idx_cf_construction_lot ON cf_construction(lot_id);
        CREATE INDEX IF NOT EXISTS idx_cf_phases_project ON cf_phases(project_id);
        CREATE INDEX IF NOT EXISTS idx_cf_infrastructure_project ON cf_infrastructure(project_id);
        CREATE INDEX IF NOT EXISTS idx_cf_materials_project ON cf_materials(project_id);
    """)
    conn.close()
    logger.info("ConstructionForge tables initialized")


# Run on import
init_db()


# ── Pydantic schemas ─────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area_m2: Optional[float] = None
    total_lots: int = 0
    status: str = "planning"
    currency: str = "COP"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area_m2: Optional[float] = None
    total_lots: Optional[int] = None
    status: Optional[str] = None
    currency: Optional[str] = None

class PhaseCreate(BaseModel):
    name: str
    phase_number: int = 1
    total_lots: int = 0
    status: str = "planning"
    start_date: Optional[str] = None
    target_completion: Optional[str] = None

class PhaseUpdate(BaseModel):
    name: Optional[str] = None
    phase_number: Optional[int] = None
    total_lots: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    target_completion: Optional[str] = None

class LotCreate(BaseModel):
    phase_id: Optional[str] = None
    lot_number: str
    block: Optional[str] = None
    area_m2: Optional[float] = None
    frontage_m: Optional[float] = None
    depth_m: Optional[float] = None
    orientation: Optional[str] = None
    features: Optional[list] = Field(default_factory=list)
    base_price: float = 0
    current_price: float = 0
    status: str = "available"

class LotUpdate(BaseModel):
    phase_id: Optional[str] = None
    lot_number: Optional[str] = None
    block: Optional[str] = None
    area_m2: Optional[float] = None
    frontage_m: Optional[float] = None
    depth_m: Optional[float] = None
    orientation: Optional[str] = None
    features: Optional[list] = None
    base_price: Optional[float] = None
    current_price: Optional[float] = None

class LotStatusUpdate(BaseModel):
    status: str
    reserved_by: Optional[str] = None

class BulkLotCreate(BaseModel):
    phase_id: Optional[str] = None
    block: Optional[str] = None
    start_number: int = 1
    count: int
    area_m2: Optional[float] = None
    frontage_m: Optional[float] = None
    depth_m: Optional[float] = None
    base_price: float = 0
    current_price: float = 0

class BuyerCreate(BaseModel):
    first_name: str
    last_name: str
    cedula: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Colombia"
    buyer_type: str = "individual"
    referral_source: Optional[str] = None
    referred_by: Optional[str] = None
    notes: Optional[str] = None
    locale: str = "es"

class BuyerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    cedula: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    buyer_type: Optional[str] = None
    referral_source: Optional[str] = None
    referred_by: Optional[str] = None
    notes: Optional[str] = None
    locale: Optional[str] = None

class SaleCreate(BaseModel):
    lot_id: str
    buyer_id: str
    agent_id: Optional[str] = None
    sale_price: float
    currency: str = "COP"
    payment_plan: Optional[dict] = Field(default_factory=dict)
    contract_type: Optional[str] = None
    contract_date: Optional[str] = None
    contract_document: Optional[str] = None
    down_payment: float = 0
    down_payment_received: bool = False
    status: str = "pending"
    notes: Optional[str] = None

class SaleUpdate(BaseModel):
    agent_id: Optional[str] = None
    sale_price: Optional[float] = None
    currency: Optional[str] = None
    payment_plan: Optional[dict] = None
    contract_type: Optional[str] = None
    contract_date: Optional[str] = None
    contract_document: Optional[str] = None
    down_payment: Optional[float] = None
    down_payment_received: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(BaseModel):
    sale_id: str
    buyer_id: str
    amount: float
    currency: str = "COP"
    payment_method: Optional[str] = None
    payment_date: Optional[str] = None
    due_date: Optional[str] = None
    installment_number: Optional[int] = None
    status: str = "pending"
    receipt_number: Optional[str] = None
    notes: Optional[str] = None

class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None

class ConstructionCreate(BaseModel):
    phase: str = "cimentacion"
    status: str = "pending"
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    contractor_id: Optional[str] = None
    inspector_notes: Optional[str] = None
    progress_percent: int = 0
    photos: Optional[list] = Field(default_factory=list)

class ConstructionUpdate(BaseModel):
    phase: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    contractor_id: Optional[str] = None
    inspector_notes: Optional[str] = None
    progress_percent: Optional[int] = None
    photos: Optional[list] = None

class ContractorCreate(BaseModel):
    name: str
    company: Optional[str] = None
    cedula_nit: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    rating: float = 0
    notes: Optional[str] = None

class ContractorUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    cedula_nit: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    rating: Optional[float] = None
    active_lots: Optional[int] = None
    total_completed: Optional[int] = None
    notes: Optional[str] = None

class InfrastructureCreate(BaseModel):
    phase_id: Optional[str] = None
    type: str
    description: Optional[str] = None
    status: str = "planned"
    contractor_id: Optional[str] = None
    budget: float = 0
    actual_cost: float = 0
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    notes: Optional[str] = None

class InfrastructureUpdate(BaseModel):
    phase_id: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    contractor_id: Optional[str] = None
    budget: Optional[float] = None
    actual_cost: Optional[float] = None
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    notes: Optional[str] = None

class MaterialCreate(BaseModel):
    name: str
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_cost: float = 0
    supplier: Optional[str] = None
    stock_on_site: float = 0
    reorder_point: float = 0
    notes: Optional[str] = None

class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_cost: Optional[float] = None
    supplier: Optional[str] = None
    stock_on_site: Optional[float] = None
    reorder_point: Optional[float] = None
    notes: Optional[str] = None


# ── Helper: build UPDATE SET clause from optional fields ─────────────

def _build_update(data: BaseModel, extra: dict = None):
    """Return (set_clause, values_list) for non-None fields."""
    fields = {k: v for k, v in data.dict().items() if v is not None}
    if extra:
        fields.update(extra)
    if not fields:
        return None, None
    # Serialize JSON fields
    for key in ("features", "payment_plan", "photos"):
        if key in fields and not isinstance(fields[key], str):
            fields[key] = json.dumps(fields[key])
    # Bool -> int for sqlite
    for key in ("down_payment_received",):
        if key in fields and isinstance(fields[key], bool):
            fields[key] = 1 if fields[key] else 0
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    return set_clause, list(fields.values())


# ═════════════════════════════════════════════════════════════════════
# PROJECTS
# ═════════════════════════════════════════════════════════════════════

@router.get("/projects")
def list_projects(status: Optional[str] = None):
    conn = get_db()
    try:
        if status:
            rows = conn.execute("SELECT * FROM cf_projects WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM cf_projects ORDER BY created_at DESC").fetchall()
        return {"projects": rows_to_list(rows)}
    finally:
        conn.close()


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate):
    pid = str(uuid.uuid4())
    slug = body.slug or body.name.lower().replace(" ", "-").replace(".", "")
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO cf_projects (id, name, slug, description, location, latitude, longitude,
                                     total_area_m2, total_lots, status, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, body.name, slug, body.description, body.location, body.latitude,
              body.longitude, body.total_area_m2, body.total_lots, body.status, body.currency))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_projects WHERE id = ?", (pid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM cf_projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
        return row_to_dict(row)
    finally:
        conn.close()


@router.put("/projects/{project_id}")
def update_project(project_id: str, body: ProjectUpdate):
    set_clause, vals = _build_update(body, {"updated_at": datetime.utcnow().isoformat()})
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_projects SET {set_clause} WHERE id = ?", vals + [project_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/projects/{project_id}/dashboard")
def project_dashboard(project_id: str):
    conn = get_db()
    try:
        proj = conn.execute("SELECT * FROM cf_projects WHERE id = ?", (project_id,)).fetchone()
        if not proj:
            raise HTTPException(404, "Project not found")

        lots = conn.execute("SELECT status, COUNT(*) as cnt FROM cf_lots WHERE project_id = ? GROUP BY status", (project_id,)).fetchall()
        lot_summary = {r["status"]: r["cnt"] for r in lots}
        total_lots = sum(lot_summary.values())

        sales_rows = conn.execute("""
            SELECT s.status, COUNT(*) as cnt, SUM(s.sale_price) as total
            FROM cf_sales s JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? GROUP BY s.status
        """, (project_id,)).fetchall()
        sales_summary = {r["status"]: {"count": r["cnt"], "total": r["total"] or 0} for r in sales_rows}

        total_revenue = sum(v["total"] for v in sales_summary.values())

        payments_received = conn.execute("""
            SELECT COALESCE(SUM(p.amount), 0) as total
            FROM cf_payments p JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? AND p.status = 'received'
        """, (project_id,)).fetchone()["total"]

        payments_pending = conn.execute("""
            SELECT COALESCE(SUM(p.amount), 0) as total
            FROM cf_payments p JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? AND p.status = 'pending'
        """, (project_id,)).fetchone()["total"]

        overdue_count = conn.execute("""
            SELECT COUNT(*) as cnt
            FROM cf_payments p JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? AND p.status = 'overdue'
        """, (project_id,)).fetchone()["cnt"]

        construction_rows = conn.execute("""
            SELECT c.phase, c.status, COUNT(*) as cnt
            FROM cf_construction c JOIN cf_lots l ON c.lot_id = l.id
            WHERE l.project_id = ? GROUP BY c.phase, c.status
        """, (project_id,)).fetchall()
        construction_summary = {}
        for r in construction_rows:
            construction_summary.setdefault(r["phase"], {})[r["status"]] = r["cnt"]

        avg_progress = conn.execute("""
            SELECT COALESCE(AVG(c.progress_percent), 0) as avg_pct
            FROM cf_construction c JOIN cf_lots l ON c.lot_id = l.id
            WHERE l.project_id = ?
        """, (project_id,)).fetchone()["avg_pct"]

        phases = conn.execute("SELECT * FROM cf_phases WHERE project_id = ? ORDER BY phase_number", (project_id,)).fetchall()

        return {
            "project": row_to_dict(proj),
            "lots": {"total": total_lots, "by_status": lot_summary},
            "sales": {"summary": sales_summary, "total_revenue": total_revenue},
            "payments": {
                "received": payments_received,
                "pending": payments_pending,
                "overdue_count": overdue_count,
            },
            "construction": {
                "by_phase": construction_summary,
                "avg_progress_percent": round(avg_progress, 1),
            },
            "phases": rows_to_list(phases),
        }
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# PHASES
# ═════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/phases")
def list_phases(project_id: str):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM cf_phases WHERE project_id = ? ORDER BY phase_number", (project_id,)).fetchall()
        return {"phases": rows_to_list(rows)}
    finally:
        conn.close()


@router.post("/projects/{project_id}/phases", status_code=201)
def create_phase(project_id: str, body: PhaseCreate):
    pid = str(uuid.uuid4())
    conn = get_db()
    try:
        # Verify project exists
        if not conn.execute("SELECT 1 FROM cf_projects WHERE id = ?", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        conn.execute("""
            INSERT INTO cf_phases (id, project_id, name, phase_number, total_lots, status, start_date, target_completion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, project_id, body.name, body.phase_number, body.total_lots,
              body.status, body.start_date, body.target_completion))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_phases WHERE id = ?", (pid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.put("/phases/{phase_id}")
def update_phase(phase_id: str, body: PhaseUpdate):
    set_clause, vals = _build_update(body)
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_phases SET {set_clause} WHERE id = ?", vals + [phase_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_phases WHERE id = ?", (phase_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Phase not found")
        return row_to_dict(row)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# LOTS
# ═════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/lots")
def list_lots(project_id: str, status: Optional[str] = None, phase_id: Optional[str] = None):
    conn = get_db()
    try:
        query = "SELECT * FROM cf_lots WHERE project_id = ?"
        params: list = [project_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        if phase_id:
            query += " AND phase_id = ?"
            params.append(phase_id)
        query += " ORDER BY block, lot_number"
        rows = conn.execute(query, params).fetchall()
        return {"lots": rows_to_list(rows), "count": len(rows)}
    finally:
        conn.close()


@router.post("/projects/{project_id}/lots", status_code=201)
def create_lot(project_id: str, body: LotCreate):
    lid = str(uuid.uuid4())
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM cf_projects WHERE id = ?", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        features_json = json.dumps(body.features or [])
        conn.execute("""
            INSERT INTO cf_lots (id, project_id, phase_id, lot_number, block, area_m2,
                                 frontage_m, depth_m, orientation, features, base_price,
                                 current_price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (lid, project_id, body.phase_id, body.lot_number, body.block,
              body.area_m2, body.frontage_m, body.depth_m, body.orientation,
              features_json, body.base_price, body.current_price, body.status))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_lots WHERE id = ?", (lid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.put("/lots/{lot_id}")
def update_lot(lot_id: str, body: LotUpdate):
    set_clause, vals = _build_update(body, {"updated_at": datetime.utcnow().isoformat()})
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_lots SET {set_clause} WHERE id = ?", vals + [lot_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_lots WHERE id = ?", (lot_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Lot not found")
        return row_to_dict(row)
    finally:
        conn.close()


@router.patch("/lots/{lot_id}/status")
def update_lot_status(lot_id: str, body: LotStatusUpdate):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM cf_lots WHERE id = ?", (lot_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Lot not found")

        updates = {"status": body.status, "updated_at": datetime.utcnow().isoformat()}
        if body.status == "reserved":
            updates["reserved_at"] = datetime.utcnow().isoformat()
            if body.reserved_by:
                updates["reserved_by"] = body.reserved_by
        elif body.status == "sold":
            updates["sold_at"] = datetime.utcnow().isoformat()
            if body.reserved_by:
                updates["sold_to"] = body.reserved_by

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE cf_lots SET {set_clause} WHERE id = ?", list(updates.values()) + [lot_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_lots WHERE id = ?", (lot_id,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.post("/lots/bulk", status_code=201)
def bulk_create_lots(project_id: str, body: BulkLotCreate):
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM cf_projects WHERE id = ?", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        created = []
        for i in range(body.count):
            lid = str(uuid.uuid4())
            lot_num = str(body.start_number + i)
            conn.execute("""
                INSERT INTO cf_lots (id, project_id, phase_id, lot_number, block, area_m2,
                                     frontage_m, depth_m, base_price, current_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')
            """, (lid, project_id, body.phase_id, lot_num, body.block,
                  body.area_m2, body.frontage_m, body.depth_m,
                  body.base_price, body.current_price))
            created.append(lid)
        conn.commit()
        return {"created": len(created), "lot_ids": created}
    finally:
        conn.close()


@router.get("/projects/{project_id}/sitemap")
def project_sitemap(project_id: str):
    """Return all lots with coordinates/block layout for site map rendering."""
    conn = get_db()
    try:
        proj = conn.execute("SELECT * FROM cf_projects WHERE id = ?", (project_id,)).fetchone()
        if not proj:
            raise HTTPException(404, "Project not found")
        lots = conn.execute("""
            SELECT l.*, b.first_name || ' ' || b.last_name as buyer_name
            FROM cf_lots l
            LEFT JOIN cf_buyers b ON l.sold_to = b.id OR l.reserved_by = b.id
            WHERE l.project_id = ?
            ORDER BY l.block, l.lot_number
        """, (project_id,)).fetchall()
        phases = conn.execute("SELECT * FROM cf_phases WHERE project_id = ? ORDER BY phase_number", (project_id,)).fetchall()
        return {
            "project": row_to_dict(proj),
            "lots": rows_to_list(lots),
            "phases": rows_to_list(phases),
        }
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# BUYERS
# ═════════════════════════════════════════════════════════════════════

@router.get("/buyers")
def list_buyers(search: Optional[str] = None):
    conn = get_db()
    try:
        if search:
            rows = conn.execute("""
                SELECT * FROM cf_buyers
                WHERE first_name LIKE ? OR last_name LIKE ? OR cedula LIKE ? OR email LIKE ?
                ORDER BY last_name, first_name
            """, (f"%{search}%",) * 4).fetchall()
        else:
            rows = conn.execute("SELECT * FROM cf_buyers ORDER BY last_name, first_name").fetchall()
        return {"buyers": rows_to_list(rows)}
    finally:
        conn.close()


@router.post("/buyers", status_code=201)
def create_buyer(body: BuyerCreate):
    bid = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO cf_buyers (id, first_name, last_name, cedula, email, phone, whatsapp,
                                   address, city, country, buyer_type, referral_source,
                                   referred_by, notes, locale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (bid, body.first_name, body.last_name, body.cedula, body.email,
              body.phone, body.whatsapp, body.address, body.city, body.country,
              body.buyer_type, body.referral_source, body.referred_by,
              body.notes, body.locale))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_buyers WHERE id = ?", (bid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/buyers/{buyer_id}")
def get_buyer(buyer_id: str):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM cf_buyers WHERE id = ?", (buyer_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Buyer not found")
        # Include their purchases
        sales = conn.execute("""
            SELECT s.*, l.lot_number, l.block, l.project_id
            FROM cf_sales s JOIN cf_lots l ON s.lot_id = l.id
            WHERE s.buyer_id = ?
        """, (buyer_id,)).fetchall()
        result = row_to_dict(row)
        result["sales"] = rows_to_list(sales)
        return result
    finally:
        conn.close()


@router.put("/buyers/{buyer_id}")
def update_buyer(buyer_id: str, body: BuyerUpdate):
    set_clause, vals = _build_update(body)
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_buyers SET {set_clause} WHERE id = ?", vals + [buyer_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_buyers WHERE id = ?", (buyer_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Buyer not found")
        return row_to_dict(row)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# SALES
# ═════════════════════════════════════════════════════════════════════

@router.post("/sales", status_code=201)
def create_sale(body: SaleCreate):
    sid = str(uuid.uuid4())
    conn = get_db()
    try:
        # Verify lot and buyer exist
        lot = conn.execute("SELECT * FROM cf_lots WHERE id = ?", (body.lot_id,)).fetchone()
        if not lot:
            raise HTTPException(404, "Lot not found")
        if not conn.execute("SELECT 1 FROM cf_buyers WHERE id = ?", (body.buyer_id,)).fetchone():
            raise HTTPException(404, "Buyer not found")
        if lot["status"] not in ("available", "reserved"):
            raise HTTPException(400, f"Lot status is '{lot['status']}', cannot sell")

        payment_plan_json = json.dumps(body.payment_plan or {})
        dp_received = 1 if body.down_payment_received else 0

        conn.execute("""
            INSERT INTO cf_sales (id, lot_id, buyer_id, agent_id, sale_price, currency,
                                  payment_plan, contract_type, contract_date, contract_document,
                                  down_payment, down_payment_received, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sid, body.lot_id, body.buyer_id, body.agent_id, body.sale_price,
              body.currency, payment_plan_json, body.contract_type, body.contract_date,
              body.contract_document, body.down_payment, dp_received,
              body.status, body.notes))

        # Update lot status
        conn.execute("""
            UPDATE cf_lots SET status = 'sold', sold_at = ?, sold_to = ?, updated_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), body.buyer_id,
              datetime.utcnow().isoformat(), body.lot_id))

        conn.commit()
        row = conn.execute("SELECT * FROM cf_sales WHERE id = ?", (sid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/sales/{sale_id}")
def get_sale(sale_id: str):
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT s.*, l.lot_number, l.block, l.project_id,
                   b.first_name, b.last_name, b.cedula, b.phone
            FROM cf_sales s
            JOIN cf_lots l ON s.lot_id = l.id
            JOIN cf_buyers b ON s.buyer_id = b.id
            WHERE s.id = ?
        """, (sale_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Sale not found")
        return row_to_dict(row)
    finally:
        conn.close()


@router.put("/sales/{sale_id}")
def update_sale(sale_id: str, body: SaleUpdate):
    set_clause, vals = _build_update(body, {"updated_at": datetime.utcnow().isoformat()})
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_sales SET {set_clause} WHERE id = ?", vals + [sale_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_sales WHERE id = ?", (sale_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Sale not found")
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/projects/{project_id}/sales/pipeline")
def sales_pipeline(project_id: str):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT s.*, l.lot_number, l.block, l.area_m2,
                   b.first_name, b.last_name, b.phone, b.whatsapp
            FROM cf_sales s
            JOIN cf_lots l ON s.lot_id = l.id
            JOIN cf_buyers b ON s.buyer_id = b.id
            WHERE l.project_id = ?
            ORDER BY s.created_at DESC
        """, (project_id,)).fetchall()

        pipeline = {"pending": [], "signed": [], "in_progress": [], "completed": [], "cancelled": []}
        for r in rows_to_list(rows):
            status = r.get("status", "pending")
            pipeline.setdefault(status, []).append(r)

        totals = conn.execute("""
            SELECT s.status, COUNT(*) as cnt, SUM(s.sale_price) as total
            FROM cf_sales s JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ?
            GROUP BY s.status
        """, (project_id,)).fetchall()

        return {
            "pipeline": pipeline,
            "totals": {r["status"]: {"count": r["cnt"], "total": r["total"] or 0} for r in totals},
        }
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# PAYMENTS
# ═════════════════════════════════════════════════════════════════════

@router.get("/sales/{sale_id}/payments")
def list_payments(sale_id: str):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT * FROM cf_payments WHERE sale_id = ? ORDER BY installment_number, due_date
        """, (sale_id,)).fetchall()
        total_paid = sum(r["amount"] for r in rows if r["status"] == "received")
        total_pending = sum(r["amount"] for r in rows if r["status"] in ("pending", "overdue"))
        return {
            "payments": rows_to_list(rows),
            "total_paid": total_paid,
            "total_pending": total_pending,
        }
    finally:
        conn.close()


@router.post("/payments", status_code=201)
def create_payment(body: PaymentCreate):
    pid = str(uuid.uuid4())
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM cf_sales WHERE id = ?", (body.sale_id,)).fetchone():
            raise HTTPException(404, "Sale not found")
        conn.execute("""
            INSERT INTO cf_payments (id, sale_id, buyer_id, amount, currency, payment_method,
                                     payment_date, due_date, installment_number, status,
                                     receipt_number, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, body.sale_id, body.buyer_id, body.amount, body.currency,
              body.payment_method, body.payment_date, body.due_date,
              body.installment_number, body.status, body.receipt_number, body.notes))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_payments WHERE id = ?", (pid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.patch("/payments/{payment_id}")
def update_payment(payment_id: str, body: PaymentUpdate):
    set_clause, vals = _build_update(body)
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_payments SET {set_clause} WHERE id = ?", vals + [payment_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_payments WHERE id = ?", (payment_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Payment not found")
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/projects/{project_id}/payments/overdue")
def overdue_payments(project_id: str):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT p.*, s.lot_id, s.sale_price, l.lot_number, l.block,
                   b.first_name, b.last_name, b.phone, b.whatsapp
            FROM cf_payments p
            JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            JOIN cf_buyers b ON p.buyer_id = b.id
            WHERE l.project_id = ?
              AND (p.status = 'overdue' OR (p.status = 'pending' AND p.due_date < datetime('now')))
            ORDER BY p.due_date
        """, (project_id,)).fetchall()

        # Auto-mark as overdue
        if rows:
            conn.execute("""
                UPDATE cf_payments SET status = 'overdue'
                WHERE status = 'pending' AND due_date < datetime('now')
                AND sale_id IN (
                    SELECT s.id FROM cf_sales s JOIN cf_lots l ON s.lot_id = l.id
                    WHERE l.project_id = ?
                )
            """, (project_id,))
            conn.commit()

        return {"overdue": rows_to_list(rows), "count": len(rows)}
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# CONSTRUCTION PROGRESS
# ═════════════════════════════════════════════════════════════════════

@router.get("/lots/{lot_id}/progress")
def get_construction_progress(lot_id: str):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT c.*, ct.name as contractor_name, ct.company as contractor_company
            FROM cf_construction c
            LEFT JOIN cf_contractors ct ON c.contractor_id = ct.id
            WHERE c.lot_id = ?
            ORDER BY c.created_at DESC
        """, (lot_id,)).fetchall()
        return {"progress": rows_to_list(rows)}
    finally:
        conn.close()


@router.post("/lots/{lot_id}/progress", status_code=201)
def create_construction_progress(lot_id: str, body: ConstructionCreate):
    cid = str(uuid.uuid4())
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM cf_lots WHERE id = ?", (lot_id,)).fetchone():
            raise HTTPException(404, "Lot not found")
        photos_json = json.dumps(body.photos or [])
        conn.execute("""
            INSERT INTO cf_construction (id, lot_id, phase, status, start_date, completion_date,
                                         contractor_id, inspector_notes, progress_percent, photos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cid, lot_id, body.phase, body.status, body.start_date,
              body.completion_date, body.contractor_id, body.inspector_notes,
              body.progress_percent, photos_json))

        # Update lot status if construction is active
        if body.status in ("in_progress", "active"):
            conn.execute("UPDATE cf_lots SET status = 'under_construction', updated_at = ? WHERE id = ?",
                         (datetime.utcnow().isoformat(), lot_id))

        conn.commit()
        row = conn.execute("SELECT * FROM cf_construction WHERE id = ?", (cid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.patch("/progress/{progress_id}")
def update_construction_progress(progress_id: str, body: ConstructionUpdate):
    set_clause, vals = _build_update(body, {"updated_at": datetime.utcnow().isoformat()})
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_construction SET {set_clause} WHERE id = ?", vals + [progress_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_construction WHERE id = ?", (progress_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Progress record not found")

        # If phase completed and delivered, update lot
        if row["status"] == "completed" and row["phase"] == "entrega":
            conn.execute("UPDATE cf_lots SET status = 'delivered', updated_at = ? WHERE id = ?",
                         (datetime.utcnow().isoformat(), row["lot_id"]))
            conn.commit()

        return row_to_dict(row)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# CONTRACTORS
# ═════════════════════════════════════════════════════════════════════

@router.get("/contractors")
def list_contractors(specialty: Optional[str] = None):
    conn = get_db()
    try:
        if specialty:
            rows = conn.execute("SELECT * FROM cf_contractors WHERE specialty LIKE ? ORDER BY name",
                                (f"%{specialty}%",)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM cf_contractors ORDER BY name").fetchall()
        return {"contractors": rows_to_list(rows)}
    finally:
        conn.close()


@router.post("/contractors", status_code=201)
def create_contractor(body: ContractorCreate):
    cid = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO cf_contractors (id, name, company, cedula_nit, specialty, phone,
                                        whatsapp, email, rating, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cid, body.name, body.company, body.cedula_nit, body.specialty,
              body.phone, body.whatsapp, body.email, body.rating, body.notes))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_contractors WHERE id = ?", (cid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.put("/contractors/{contractor_id}")
def update_contractor(contractor_id: str, body: ContractorUpdate):
    set_clause, vals = _build_update(body)
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_contractors SET {set_clause} WHERE id = ?", vals + [contractor_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_contractors WHERE id = ?", (contractor_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Contractor not found")
        return row_to_dict(row)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# INFRASTRUCTURE
# ═════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/infrastructure")
def list_infrastructure(project_id: str):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT i.*, ct.name as contractor_name
            FROM cf_infrastructure i
            LEFT JOIN cf_contractors ct ON i.contractor_id = ct.id
            WHERE i.project_id = ?
            ORDER BY i.created_at DESC
        """, (project_id,)).fetchall()
        total_budget = sum(r["budget"] or 0 for r in rows)
        total_actual = sum(r["actual_cost"] or 0 for r in rows)
        return {
            "infrastructure": rows_to_list(rows),
            "total_budget": total_budget,
            "total_actual_cost": total_actual,
        }
    finally:
        conn.close()


@router.post("/infrastructure", status_code=201)
def create_infrastructure(body: InfrastructureCreate, project_id: str = Query(...)):
    iid = str(uuid.uuid4())
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM cf_projects WHERE id = ?", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        conn.execute("""
            INSERT INTO cf_infrastructure (id, project_id, phase_id, type, description, status,
                                           contractor_id, budget, actual_cost, start_date,
                                           completion_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (iid, project_id, body.phase_id, body.type, body.description,
              body.status, body.contractor_id, body.budget, body.actual_cost,
              body.start_date, body.completion_date, body.notes))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_infrastructure WHERE id = ?", (iid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.put("/infrastructure/{infra_id}")
def update_infrastructure(infra_id: str, body: InfrastructureUpdate):
    set_clause, vals = _build_update(body)
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_infrastructure SET {set_clause} WHERE id = ?", vals + [infra_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_infrastructure WHERE id = ?", (infra_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Infrastructure item not found")
        return row_to_dict(row)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# MATERIALS
# ═════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/materials")
def list_materials(project_id: str, category: Optional[str] = None):
    conn = get_db()
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM cf_materials WHERE project_id = ? AND category = ? ORDER BY name",
                (project_id, category)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cf_materials WHERE project_id = ? ORDER BY category, name",
                (project_id,)).fetchall()
        return {"materials": rows_to_list(rows)}
    finally:
        conn.close()


@router.post("/materials", status_code=201)
def create_material(body: MaterialCreate, project_id: str = Query(...)):
    mid = str(uuid.uuid4())
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM cf_projects WHERE id = ?", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        conn.execute("""
            INSERT INTO cf_materials (id, project_id, name, category, unit, unit_cost,
                                      supplier, stock_on_site, reorder_point, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (mid, project_id, body.name, body.category, body.unit, body.unit_cost,
              body.supplier, body.stock_on_site, body.reorder_point, body.notes))
        conn.commit()
        row = conn.execute("SELECT * FROM cf_materials WHERE id = ?", (mid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@router.put("/materials/{material_id}")
def update_material(material_id: str, body: MaterialUpdate):
    set_clause, vals = _build_update(body)
    if not set_clause:
        raise HTTPException(400, "No fields to update")
    conn = get_db()
    try:
        conn.execute(f"UPDATE cf_materials SET {set_clause} WHERE id = ?", vals + [material_id])
        conn.commit()
        row = conn.execute("SELECT * FROM cf_materials WHERE id = ?", (material_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Material not found")
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/projects/{project_id}/materials/low-stock")
def low_stock_materials(project_id: str):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT * FROM cf_materials
            WHERE project_id = ? AND stock_on_site <= reorder_point AND reorder_point > 0
            ORDER BY (stock_on_site / NULLIF(reorder_point, 0))
        """, (project_id,)).fetchall()
        return {"low_stock": rows_to_list(rows), "count": len(rows)}
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════
# REPORTS
# ═════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/report/executive")
def executive_report(project_id: str):
    """High-level executive summary for stakeholders."""
    conn = get_db()
    try:
        proj = conn.execute("SELECT * FROM cf_projects WHERE id = ?", (project_id,)).fetchone()
        if not proj:
            raise HTTPException(404, "Project not found")

        # Lot stats
        lot_stats = conn.execute("""
            SELECT status, COUNT(*) as cnt, COALESCE(SUM(current_price), 0) as value
            FROM cf_lots WHERE project_id = ? GROUP BY status
        """, (project_id,)).fetchall()
        lot_summary = {r["status"]: {"count": r["cnt"], "value": r["value"]} for r in lot_stats}
        total_lots = sum(r["cnt"] for r in lot_stats)
        sold_count = lot_summary.get("sold", {}).get("count", 0) + lot_summary.get("delivered", {}).get("count", 0)
        sell_through = round((sold_count / total_lots * 100), 1) if total_lots > 0 else 0

        # Revenue
        revenue = conn.execute("""
            SELECT COALESCE(SUM(s.sale_price), 0) as total_contracted,
                   COUNT(*) as total_sales
            FROM cf_sales s JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? AND s.status != 'cancelled'
        """, (project_id,)).fetchone()

        collected = conn.execute("""
            SELECT COALESCE(SUM(p.amount), 0) as total
            FROM cf_payments p JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? AND p.status = 'received'
        """, (project_id,)).fetchone()["total"]

        # Construction progress
        avg_progress = conn.execute("""
            SELECT COALESCE(AVG(c.progress_percent), 0) as avg_pct
            FROM cf_construction c JOIN cf_lots l ON c.lot_id = l.id
            WHERE l.project_id = ?
        """, (project_id,)).fetchone()["avg_pct"]

        # Infrastructure budget vs actual
        infra = conn.execute("""
            SELECT COALESCE(SUM(budget), 0) as total_budget,
                   COALESCE(SUM(actual_cost), 0) as total_actual
            FROM cf_infrastructure WHERE project_id = ?
        """, (project_id,)).fetchone()

        # Phases
        phases = conn.execute("""
            SELECT name, phase_number, status, total_lots, start_date, target_completion
            FROM cf_phases WHERE project_id = ? ORDER BY phase_number
        """, (project_id,)).fetchall()

        return {
            "project": row_to_dict(proj),
            "summary": {
                "total_lots": total_lots,
                "lots_by_status": lot_summary,
                "sell_through_percent": sell_through,
                "total_contracted": revenue["total_contracted"],
                "total_sales_count": revenue["total_sales"],
                "total_collected": collected,
                "collection_rate": round((collected / revenue["total_contracted"] * 100), 1) if revenue["total_contracted"] > 0 else 0,
                "avg_construction_progress": round(avg_progress, 1),
                "infrastructure_budget": infra["total_budget"],
                "infrastructure_actual": infra["total_actual"],
                "infrastructure_variance": round(infra["total_actual"] - infra["total_budget"], 2),
            },
            "phases": rows_to_list(phases),
        }
    finally:
        conn.close()


@router.get("/projects/{project_id}/report/financial")
def financial_report(project_id: str):
    """Detailed financial breakdown: revenue, payments, receivables, cost tracking."""
    conn = get_db()
    try:
        proj = conn.execute("SELECT * FROM cf_projects WHERE id = ?", (project_id,)).fetchone()
        if not proj:
            raise HTTPException(404, "Project not found")

        # Sales by status
        sales_by_status = conn.execute("""
            SELECT s.status, COUNT(*) as cnt, SUM(s.sale_price) as total, SUM(s.down_payment) as dp_total
            FROM cf_sales s JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ?
            GROUP BY s.status
        """, (project_id,)).fetchall()

        # Payment summary by status
        payment_summary = conn.execute("""
            SELECT p.status, COUNT(*) as cnt, SUM(p.amount) as total
            FROM cf_payments p JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ?
            GROUP BY p.status
        """, (project_id,)).fetchall()

        # Payment summary by method
        payment_by_method = conn.execute("""
            SELECT p.payment_method, COUNT(*) as cnt, SUM(p.amount) as total
            FROM cf_payments p JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? AND p.status = 'received'
            GROUP BY p.payment_method
        """, (project_id,)).fetchall()

        # Monthly collections (last 12 months)
        monthly = conn.execute("""
            SELECT strftime('%Y-%m', p.payment_date) as month, SUM(p.amount) as total
            FROM cf_payments p JOIN cf_sales s ON p.sale_id = s.id
            JOIN cf_lots l ON s.lot_id = l.id
            WHERE l.project_id = ? AND p.status = 'received' AND p.payment_date IS NOT NULL
            GROUP BY month ORDER BY month DESC LIMIT 12
        """, (project_id,)).fetchall()

        # Infrastructure costs
        infra_costs = conn.execute("""
            SELECT type, SUM(budget) as budget, SUM(actual_cost) as actual
            FROM cf_infrastructure WHERE project_id = ?
            GROUP BY type
        """, (project_id,)).fetchall()

        # Material costs
        material_costs = conn.execute("""
            SELECT category, SUM(unit_cost * stock_on_site) as total_value, COUNT(*) as items
            FROM cf_materials WHERE project_id = ?
            GROUP BY category
        """, (project_id,)).fetchall()

        # Unsold inventory value
        unsold_value = conn.execute("""
            SELECT COALESCE(SUM(current_price), 0) as total
            FROM cf_lots WHERE project_id = ? AND status IN ('available', 'reserved')
        """, (project_id,)).fetchone()["total"]

        return {
            "project": {"id": proj["id"], "name": proj["name"], "currency": proj["currency"]},
            "sales_by_status": rows_to_list(sales_by_status),
            "payments": {
                "by_status": rows_to_list(payment_summary),
                "by_method": rows_to_list(payment_by_method),
                "monthly_collections": rows_to_list(monthly),
            },
            "costs": {
                "infrastructure_by_type": rows_to_list(infra_costs),
                "materials_by_category": rows_to_list(material_costs),
            },
            "unsold_inventory_value": unsold_value,
        }
    finally:
        conn.close()
