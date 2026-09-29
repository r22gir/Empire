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

# iX-day R1X-INT-FIX: INTAKE_DB constant REMOVED. The stale-fork
# `~/empire-repo/backend/data/intake.db` path is dead. The live
# `intake_fabrics` table lives in canonical empire.db (see
# `_init_intake_fabrics_table` below). Old `/client-submit`,
# `/intake/pending`, `/intake/{intake_id}`, `/intake/match/{id}` endpoints
# that referenced this constant were dead code (no front-end callers) and
# have been deleted.

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

# iX-day R1X-INT-FIX: ClientFabricSubmit REMOVED. Schema referenced the
# old (stale-fork) intake_fabrics columns. No callers — front-end uses
# the canonical-scoped IntakeFabricCreate defined near the bottom of this
# file via /intake-project/{intake_id}/fabrics.

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
    """Create fabrics table if it doesn't exist (canonical empire.db)."""
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

    # iX-day R1X-INT-FIX: intake_fabrics creation in stale-fork REMOVED.
    # The canonical intake_fabrics lives in empire.db and is created by
    # `_init_intake_fabrics_table` below (rich schema: scope, room_name,
    # item_name, fabric_preference, fabric_name, …). The old schema
    # (client_fabric_name, client_fabric_code, has_own_fabric, …) is dead.


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


# iX-day R1X-INT-FIX: `/client-submit` and `/client-submit/photo` REMOVED.
# Both wrote to the stale-fork `~/empire-repo/backend/data/intake.db` (and
# the deprecated `~/empire-repo/backend/data/photos/fabric/client/`).
# The front-end uses the canonical `/intake-project/{intake_id}/fabrics`
# endpoint (defined further down), which writes to empire.db. No callers
# of the dead endpoints were found via repo-wide grep.


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


# iX-day R1X-INT-FIX: `/intake/pending`, `/intake/{intake_id}`, and
# `/intake/match/{intake_fabric_id}` REMOVED. All three read or wrote
# to the stale-fork `~/empire-repo/backend/data/intake.db`. The owner
# review surface for intake fabrics now lives in the canonical
# `/intake-project/{intake_id}/fabrics` GET endpoint (see below) and
# the rest of the fabrics library tooling. No front-end callers existed
# for the removed endpoints.


# ── INTAKE FABRIC INFO (empire.db) ────────────────────────────

class IntakeFabricCreate(BaseModel):
    scope: str = "item"  # 'room' or 'item'
    room_name: Optional[str] = None
    item_name: Optional[str] = None
    fabric_preference: str = "not_sure"  # picked_out, com, recommend, not_sure
    fabric_name: Optional[str] = None
    color_pattern: Optional[str] = None
    fabric_code: Optional[str] = None
    supplier_url: Optional[str] = None
    swatch_photo_path: Optional[str] = None
    vertical_repeat: Optional[float] = None
    horizontal_repeat: Optional[float] = None
    fabric_width: Optional[float] = None
    material_type: Optional[str] = None
    yards_available: Optional[float] = None
    client_notes: Optional[str] = None


def _init_intake_fabrics_table():
    """Create intake_fabrics table in empire.db if not exists."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS intake_fabrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intake_id TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'item',
                room_name TEXT,
                item_name TEXT,
                fabric_preference TEXT NOT NULL DEFAULT 'not_sure',
                fabric_name TEXT,
                color_pattern TEXT,
                fabric_code TEXT,
                supplier_url TEXT,
                swatch_photo_path TEXT,
                vertical_repeat REAL,
                horizontal_repeat REAL,
                fabric_width REAL,
                material_type TEXT,
                yards_available REAL,
                client_notes TEXT,
                owner_matched_fabric_id INTEGER,
                owner_notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)


try:
    _init_intake_fabrics_table()
except Exception as e:
    logger.warning(f"intake_fabrics table init: {e}")


@router.post("/intake-project/{intake_id}/fabrics")
async def save_intake_fabric(intake_id: str, payload: IntakeFabricCreate):
    """Save fabric info for an intake project (room or item level)."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO intake_fabrics
               (intake_id, scope, room_name, item_name, fabric_preference,
                fabric_name, color_pattern, fabric_code, supplier_url,
                swatch_photo_path, vertical_repeat, horizontal_repeat,
                fabric_width, material_type, yards_available, client_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (intake_id, payload.scope, payload.room_name, payload.item_name,
             payload.fabric_preference, payload.fabric_name, payload.color_pattern,
             payload.fabric_code, payload.supplier_url, payload.swatch_photo_path,
             payload.vertical_repeat, payload.horizontal_repeat, payload.fabric_width,
             payload.material_type, payload.yards_available, payload.client_notes),
        )
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = conn.execute("SELECT * FROM intake_fabrics WHERE id = ?", (row_id,)).fetchone()
        return dict_row(row)


@router.get("/intake-project/{intake_id}/fabrics")
async def get_intake_fabrics(intake_id: str):
    """Get all fabric info for an intake project."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM intake_fabrics WHERE intake_id = ? ORDER BY id", (intake_id,)
        ).fetchall()
        return dict_rows(rows)


@router.put("/intake-project/{intake_id}/fabrics/{fabric_id}")
async def update_intake_fabric(intake_id: str, fabric_id: int, payload: IntakeFabricCreate):
    """Update a fabric entry."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM intake_fabrics WHERE id = ? AND intake_id = ?", (fabric_id, intake_id)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Fabric entry not found")
        conn.execute(
            """UPDATE intake_fabrics SET
               scope=?, room_name=?, item_name=?, fabric_preference=?,
               fabric_name=?, color_pattern=?, fabric_code=?, supplier_url=?,
               swatch_photo_path=?, vertical_repeat=?, horizontal_repeat=?,
               fabric_width=?, material_type=?, yards_available=?, client_notes=?
               WHERE id=? AND intake_id=?""",
            (payload.scope, payload.room_name, payload.item_name,
             payload.fabric_preference, payload.fabric_name, payload.color_pattern,
             payload.fabric_code, payload.supplier_url, payload.swatch_photo_path,
             payload.vertical_repeat, payload.horizontal_repeat, payload.fabric_width,
             payload.material_type, payload.yards_available, payload.client_notes,
             fabric_id, intake_id),
        )
        row = conn.execute("SELECT * FROM intake_fabrics WHERE id = ?", (fabric_id,)).fetchone()
        return dict_row(row)


@router.delete("/intake-project/{intake_id}/fabrics/{fabric_id}")
async def delete_intake_fabric(intake_id: str, fabric_id: int):
    """Remove a fabric entry."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM intake_fabrics WHERE id = ? AND intake_id = ?", (fabric_id, intake_id)
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Fabric entry not found")
        return {"deleted": fabric_id}


@router.put("/intake-project/{intake_id}/fabrics/{fabric_id}/match")
async def match_intake_fabric_to_library(intake_id: str, fabric_id: int, library_fabric_id: int, owner_notes: Optional[str] = None):
    """Owner matches a client fabric submission to a library fabric."""
    with get_db() as conn:
        lib = conn.execute("SELECT id FROM fabrics WHERE id = ?", (library_fabric_id,)).fetchone()
        if not lib:
            raise HTTPException(404, f"Library fabric {library_fabric_id} not found")
        conn.execute(
            "UPDATE intake_fabrics SET owner_matched_fabric_id=?, owner_notes=? WHERE id=? AND intake_id=?",
            (library_fabric_id, owner_notes, fabric_id, intake_id),
        )
        return {"matched": True, "fabric_id": fabric_id, "library_fabric_id": library_fabric_id}


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
