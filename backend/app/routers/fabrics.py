"""
Fabric Library CRUD router.
Dual-mode: owner endpoints (full data) + client-safe endpoints (no pricing/supplier).
Yardage calculator included.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List
import sqlite3
import os
import logging
from datetime import datetime

from app.db.database import get_db, dict_row, dict_rows

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fabrics"])

INTAKE_DB = os.path.expanduser("~/empire-repo/backend/data/intake.db")

# ── Pydantic schemas ──────────────────────────────────────────

class FabricCreate(BaseModel):
    code: str
    name: str
    color_pattern: Optional[str] = None
    material_type: Optional[str] = None
    supplier: Optional[str] = None
    supplier_link: Optional[str] = None
    cost_per_yard: float = 0
    margin_percent: float = 0
    durability: Optional[str] = None
    pattern_repeat_h: float = 0
    pattern_repeat_v: float = 0
    width_inches: float = 54
    backing_fabric_id: Optional[int] = None
    swatch_photo_path: Optional[str] = None
    notes: Optional[str] = None

class FabricUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    color_pattern: Optional[str] = None
    material_type: Optional[str] = None
    supplier: Optional[str] = None
    supplier_link: Optional[str] = None
    cost_per_yard: Optional[float] = None
    margin_percent: Optional[float] = None
    durability: Optional[str] = None
    pattern_repeat_h: Optional[float] = None
    pattern_repeat_v: Optional[float] = None
    width_inches: Optional[float] = None
    backing_fabric_id: Optional[int] = None
    swatch_photo_path: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[int] = None

class ClientFabricSubmit(BaseModel):
    intake_id: str
    client_fabric_name: Optional[str] = None
    client_fabric_code: Optional[str] = None
    client_notes: Optional[str] = None
    has_own_fabric: bool = False
    yards_available: Optional[float] = None

class YardageRequest(BaseModel):
    width_inches: float = 0
    length_inches: float = 0
    quantity: int = 1
    fabric_width: float = 54
    pattern_repeat_v: float = 0
    seam_allowance: float = 1
    waste_percent: float = 10


# ── Helper: ensure fabrics table exists ───────────────────────

def _ensure_tables():
    """Create fabrics and intake_fabrics tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fabrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                color_pattern TEXT,
                material_type TEXT,
                supplier TEXT,
                supplier_link TEXT,
                cost_per_yard REAL DEFAULT 0,
                margin_percent REAL DEFAULT 0,
                durability TEXT,
                pattern_repeat_h REAL DEFAULT 0,
                pattern_repeat_v REAL DEFAULT 0,
                width_inches REAL DEFAULT 54,
                backing_fabric_id INTEGER,
                swatch_photo_path TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                source TEXT DEFAULT 'owner',
                submitted_by_customer_id TEXT,
                client_description TEXT,
                client_swatch_photo_path TEXT,
                needs_review INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (backing_fabric_id) REFERENCES fabrics(id)
            );
            CREATE INDEX IF NOT EXISTS idx_fabrics_code ON fabrics(code);
            CREATE INDEX IF NOT EXISTS idx_fabrics_active ON fabrics(is_active);
            CREATE INDEX IF NOT EXISTS idx_fabrics_type ON fabrics(material_type);
            CREATE INDEX IF NOT EXISTS idx_fabrics_supplier ON fabrics(supplier);
        """)

    # intake_fabrics goes in intake.db
    if os.path.exists(INTAKE_DB):
        intake_conn = sqlite3.connect(INTAKE_DB)
        intake_conn.executescript("""
            CREATE TABLE IF NOT EXISTS intake_fabrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intake_id TEXT NOT NULL,
                fabric_id INTEGER,
                client_fabric_name TEXT,
                client_fabric_code TEXT,
                client_swatch_photo TEXT,
                client_notes TEXT,
                has_own_fabric INTEGER DEFAULT 0,
                yards_available REAL,
                owner_matched INTEGER DEFAULT 0,
                owner_notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_intake_fabrics_intake ON intake_fabrics(intake_id);
        """)
        intake_conn.commit()
        intake_conn.close()


# Run on import
_ensure_tables()


# ── OWNER ENDPOINTS (full data) ──────────────────────────────

@router.get("")
async def list_fabrics(
    search: Optional[str] = None,
    type: Optional[str] = None,
    supplier: Optional[str] = None,
    active_only: bool = True,
):
    """List all fabrics with optional filters. Full owner data."""
    with get_db() as conn:
        query = "SELECT * FROM fabrics WHERE 1=1"
        params = []

        if active_only:
            query += " AND is_active = 1"

        if search:
            query += " AND (code LIKE ? OR name LIKE ? OR color_pattern LIKE ? OR supplier LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])

        if type:
            query += " AND material_type = ?"
            params.append(type)

        if supplier:
            query += " AND supplier LIKE ?"
            params.append(f"%{supplier}%")

        query += " ORDER BY material_type, name"
        rows = conn.execute(query, params).fetchall()
        fabrics = dict_rows(rows)

        # Attach backing info
        for f in fabrics:
            if f.get("backing_fabric_id"):
                backing = conn.execute(
                    "SELECT id, code, name, color_pattern, material_type, cost_per_yard, margin_percent FROM fabrics WHERE id = ?",
                    (f["backing_fabric_id"],)
                ).fetchone()
                f["backing"] = dict_row(backing)

        return fabrics


@router.get("/calculate-yards")
async def calculate_yards(
    width_inches: float = 0,
    length_inches: float = 0,
    quantity: int = 1,
    fabric_width: float = 54,
    pattern_repeat_v: float = 0,
    seam_allowance: float = 1,
    waste_percent: float = 10,
):
    """Calculate yardage for upholstery/general pieces."""
    if width_inches <= 0 or length_inches <= 0:
        raise HTTPException(400, "width_inches and length_inches must be > 0")

    # Add seam allowance to each dimension
    cut_width = width_inches + (seam_allowance * 2)
    cut_length = length_inches + (seam_allowance * 2)

    # Adjust for pattern repeat
    pattern_adjusted_cut = cut_length
    if pattern_repeat_v > 0:
        import math
        pattern_adjusted_cut = math.ceil(cut_length / pattern_repeat_v) * pattern_repeat_v

    # How many pieces fit across the fabric width?
    cuts_across = max(1, int(fabric_width / cut_width))

    # How many rows of cuts do we need?
    import math
    rows_needed = math.ceil(quantity / cuts_across)

    # Total linear inches needed
    total_inches = rows_needed * pattern_adjusted_cut

    # Convert to yards
    yards_calculated = round(total_inches / 36, 2)
    yards_with_waste = round(yards_calculated * (1 + waste_percent / 100), 2)

    breakdown = (
        f"{quantity} pieces × {pattern_adjusted_cut}\" cut length ÷ "
        f"{cuts_across} across = {rows_needed} rows × {pattern_adjusted_cut}\" = "
        f"{total_inches}\" = {yards_calculated} yards + {waste_percent}% waste"
    )

    return {
        "yards_calculated": yards_calculated,
        "yards_with_waste": yards_with_waste,
        "cuts_across_width": cuts_across,
        "cut_length_inches": cut_length,
        "pattern_adjusted_cut": pattern_adjusted_cut,
        "breakdown": breakdown,
    }


@router.get("/catalog")
async def fabric_catalog(search: Optional[str] = None):
    """Client-safe fabric list. NO cost, margin, supplier, supplier_link."""
    with get_db() as conn:
        query = "SELECT id, name, color_pattern, material_type, swatch_photo_path, backing_fabric_id FROM fabrics WHERE is_active = 1"
        params = []

        if search:
            query += " AND (name LIKE ? OR color_pattern LIKE ? OR material_type LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])

        query += " ORDER BY name"
        rows = conn.execute(query, params).fetchall()
        fabrics = dict_rows(rows)

        # Only expose whether backing exists, not the backing details
        for f in fabrics:
            f["has_backing"] = bool(f.pop("backing_fabric_id", None))

        return fabrics


@router.post("/client-submit")
async def client_submit_fabric(data: ClientFabricSubmit):
    """Client submits their own fabric info during intake. Goes to intake_fabrics."""
    if not os.path.exists(INTAKE_DB):
        raise HTTPException(500, "Intake database not available")

    intake_conn = sqlite3.connect(INTAKE_DB)
    intake_conn.row_factory = sqlite3.Row
    try:
        intake_conn.execute(
            """INSERT INTO intake_fabrics
               (intake_id, client_fabric_name, client_fabric_code, client_notes,
                has_own_fabric, yards_available)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data.intake_id,
                data.client_fabric_name,
                data.client_fabric_code,
                data.client_notes,
                1 if data.has_own_fabric else 0,
                data.yards_available,
            ),
        )
        intake_conn.commit()
        row_id = intake_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"id": row_id, "status": "submitted"}
    finally:
        intake_conn.close()


@router.post("/client-submit/photo")
async def client_submit_photo(
    intake_fabric_id: int = Form(...),
    file: UploadFile = File(...),
):
    """Client uploads a swatch photo for their fabric submission."""
    if not os.path.exists(INTAKE_DB):
        raise HTTPException(500, "Intake database not available")

    # Proxy to the existing photos upload system
    from pathlib import Path
    photos_dir = Path(os.path.expanduser("~/empire-repo/backend/data/photos/fabric/client"))
    photos_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    ext = Path(file.filename or "photo.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    file_path = photos_dir / filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    photo_path = f"/photos/fabric/client/{filename}"

    # Update intake_fabrics record
    intake_conn = sqlite3.connect(INTAKE_DB)
    try:
        intake_conn.execute(
            "UPDATE intake_fabrics SET client_swatch_photo = ? WHERE id = ?",
            (photo_path, intake_fabric_id),
        )
        intake_conn.commit()
    finally:
        intake_conn.close()

    return {"photo_path": photo_path, "filename": filename}


@router.get("/{fabric_id}")
async def get_fabric(fabric_id: int):
    """Get single fabric with full details + backing info."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Fabric not found")
        fabric = dict_row(row)

        if fabric.get("backing_fabric_id"):
            backing = conn.execute(
                "SELECT * FROM fabrics WHERE id = ?",
                (fabric["backing_fabric_id"],)
            ).fetchone()
            fabric["backing"] = dict_row(backing)

        return fabric


@router.post("")
async def create_fabric(data: FabricCreate):
    """Create a new fabric record."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO fabrics
               (code, name, color_pattern, material_type, supplier, supplier_link,
                cost_per_yard, margin_percent, durability, pattern_repeat_h, pattern_repeat_v,
                width_inches, backing_fabric_id, swatch_photo_path, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.code, data.name, data.color_pattern, data.material_type,
                data.supplier, data.supplier_link, data.cost_per_yard, data.margin_percent,
                data.durability, data.pattern_repeat_h, data.pattern_repeat_v,
                data.width_inches, data.backing_fabric_id, data.swatch_photo_path, data.notes,
            ),
        )
        fabric_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        return dict_row(row)


@router.put("/{fabric_id}")
async def update_fabric(fabric_id: int, data: FabricUpdate):
    """Update fabric fields. Only non-None fields are updated."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Fabric not found")

        updates = {}
        for field, value in data.model_dump(exclude_none=True).items():
            updates[field] = value

        if not updates:
            return dict_row(existing)

        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [fabric_id]

        conn.execute(f"UPDATE fabrics SET {set_clause} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        return dict_row(row)


@router.delete("/{fabric_id}")
async def delete_fabric(fabric_id: int):
    """Soft delete — set is_active=0."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Fabric not found")
        conn.execute(
            "UPDATE fabrics SET is_active = 0, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), fabric_id),
        )
        return {"status": "deleted", "id": fabric_id}


@router.post("/{fabric_id}/swatch")
async def upload_swatch(fabric_id: int, file: UploadFile = File(...)):
    """Upload swatch photo for a fabric."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Fabric not found")

    from pathlib import Path
    import uuid
    photos_dir = Path(os.path.expanduser("~/empire-repo/backend/data/photos/fabric/swatches"))
    photos_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "swatch.jpg").suffix or ".jpg"
    filename = f"{fabric_id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = photos_dir / filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    photo_path = f"/photos/fabric/swatches/{filename}"

    with get_db() as conn:
        conn.execute(
            "UPDATE fabrics SET swatch_photo_path = ?, updated_at = ? WHERE id = ?",
            (photo_path, datetime.utcnow().isoformat(), fabric_id),
        )
        row = conn.execute("SELECT * FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        return dict_row(row)


# ── INTAKE FABRIC REVIEW (owner endpoints) ───────────────────

@router.get("/intake/pending")
async def list_pending_intake_fabrics():
    """List all client-submitted fabrics pending owner review."""
    if not os.path.exists(INTAKE_DB):
        return []

    intake_conn = sqlite3.connect(INTAKE_DB)
    intake_conn.row_factory = sqlite3.Row
    try:
        rows = intake_conn.execute(
            "SELECT * FROM intake_fabrics WHERE owner_matched = 0 ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        intake_conn.close()


@router.get("/intake/{intake_id}")
async def get_intake_fabrics(intake_id: str):
    """Get all fabric submissions for a specific intake project."""
    if not os.path.exists(INTAKE_DB):
        return []

    intake_conn = sqlite3.connect(INTAKE_DB)
    intake_conn.row_factory = sqlite3.Row
    try:
        rows = intake_conn.execute(
            "SELECT * FROM intake_fabrics WHERE intake_id = ? ORDER BY created_at",
            (intake_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        intake_conn.close()


@router.put("/intake/match/{intake_fabric_id}")
async def match_intake_fabric(intake_fabric_id: int, fabric_id: int, owner_notes: Optional[str] = None):
    """Owner matches a client-submitted fabric to a library fabric."""
    if not os.path.exists(INTAKE_DB):
        raise HTTPException(500, "Intake database not available")

    # Verify the fabric exists
    with get_db() as conn:
        fabric = conn.execute("SELECT id FROM fabrics WHERE id = ?", (fabric_id,)).fetchone()
        if not fabric:
            raise HTTPException(404, f"Fabric {fabric_id} not found in library")

    intake_conn = sqlite3.connect(INTAKE_DB)
    try:
        intake_conn.execute(
            "UPDATE intake_fabrics SET fabric_id = ?, owner_matched = 1, owner_notes = ? WHERE id = ?",
            (fabric_id, owner_notes, intake_fabric_id),
        )
        intake_conn.commit()
        return {"status": "matched", "intake_fabric_id": intake_fabric_id, "fabric_id": fabric_id}
    finally:
        intake_conn.close()


# ── SEED DATA ─────────────────────────────────────────────────

def seed_ramiro_fabrics():
    """Pre-load Ramiro Quote fabrics. Safe to re-run (checks for existing)."""
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM fabrics").fetchone()[0]
        if existing > 0:
            return  # Already seeded

        # Seat fabrics
        conn.execute(
            """INSERT INTO fabrics (code, name, color_pattern, material_type, supplier, cost_per_yard, margin_percent, durability, notes)
               VALUES ('V639', 'Charlotte Fabrics Cuaderno', 'Spruce', 'Upholstery', 'Charlotte Fabrics', 0, 0, '2,000,000 rubs', 'Seat fabric — Upstairs Dining (Comedor Arriba)')"""
        )
        conn.execute(
            """INSERT INTO fabrics (code, name, color_pattern, material_type, supplier, cost_per_yard, margin_percent, notes)
               VALUES ('V638', 'Charlotte Fabrics V638', 'Teak', 'Upholstery', 'Charlotte Fabrics', 0, 0, 'Seat fabric — First Floor Dining (Primer Piso Comedor)')"""
        )
        conn.execute(
            """INSERT INTO fabrics (code, name, color_pattern, material_type, supplier, cost_per_yard, margin_percent, notes)
               VALUES ('V1012', 'Marine Vinyl II', 'Hazelnut', 'Marine Vinyl', 'Kovi Fabrics', 0, 0, 'Seat fabric — Rear Upstairs Dining (Comedor Arriba Atras)')"""
        )

        # Backings
        conn.execute(
            """INSERT INTO fabrics (code, name, color_pattern, material_type, supplier, cost_per_yard, notes)
               VALUES ('NCOP-64', 'Douglass NCOP-64', 'Neutral', 'Backing', 'Douglass Industries', 0, 'Backing for V639 Spruce')"""
        )
        conn.execute(
            """INSERT INTO fabrics (code, name, color_pattern, material_type, cost_per_yard, notes)
               VALUES ('D3191', 'D3191', 'Fawn', 'Backing', 0, 'Backing for V638 Teak')"""
        )
        conn.execute(
            """INSERT INTO fabrics (code, name, color_pattern, material_type, cost_per_yard, notes)
               VALUES ('D3222', 'D3222', 'Umber', 'Backing', 0, 'Backing for V1012 Hazelnut')"""
        )

        # Link backings to parent fabrics
        conn.execute("UPDATE fabrics SET backing_fabric_id = (SELECT id FROM fabrics WHERE code = 'NCOP-64') WHERE code = 'V639'")
        conn.execute("UPDATE fabrics SET backing_fabric_id = (SELECT id FROM fabrics WHERE code = 'D3191') WHERE code = 'V638'")
        conn.execute("UPDATE fabrics SET backing_fabric_id = (SELECT id FROM fabrics WHERE code = 'D3222') WHERE code = 'V1012'")

        logger.info("✓ Seeded 6 Ramiro Quote fabrics (3 seat + 3 backing)")


# Auto-seed on import
try:
    seed_ramiro_fabrics()
except Exception as e:
    logger.warning(f"Fabric seed skipped: {e}")
