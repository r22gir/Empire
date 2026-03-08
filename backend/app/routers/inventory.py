"""
Empire Inventory & Vendor Management — Track materials, hardware, and suppliers.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import json

from app.db.database import get_db, dict_row, dict_rows

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ── Schemas ──────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    category: str
    quantity: float = 0
    unit: str = "yards"
    min_stock: float = 0
    cost_per_unit: float = 0
    sell_price: float = 0
    vendor: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    business: str = "workroom"


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    min_stock: Optional[float] = None
    cost_per_unit: Optional[float] = None
    sell_price: Optional[float] = None
    vendor: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    business: Optional[str] = None


class VendorCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    account_number: Optional[str] = None
    lead_time_days: int = 7
    notes: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    account_number: Optional[str] = None
    lead_time_days: Optional[int] = None
    notes: Optional[str] = None


# ── Inventory Items ──────────────────────────────────────────────────

@router.get("/items")
def list_items(
    category: Optional[str] = None,
    business: Optional[str] = None,
    low_stock: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List inventory items with optional filters."""
    clauses = []
    params = []

    if category:
        clauses.append("category = ?")
        params.append(category)
    if business:
        clauses.append("business = ?")
        params.append(business)
    if low_stock:
        clauses.append("quantity < min_stock AND min_stock > 0")
    if search:
        clauses.append("(name LIKE ? OR sku LIKE ? OR vendor LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM inventory_items{where} ORDER BY category, name LIMIT ? OFFSET ?",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM inventory_items{where}", params_count
        ).fetchone()[0]

        return {"items": dict_rows(rows), "total": total, "limit": limit, "offset": offset}


@router.post("/items")
def create_item(item: ItemCreate):
    """Create a new inventory item."""
    with get_db() as conn:
        # Check for duplicate SKU
        if item.sku:
            existing = conn.execute(
                "SELECT id FROM inventory_items WHERE sku = ?", (item.sku,)
            ).fetchone()
            if existing:
                raise HTTPException(status_code=409, detail=f"SKU '{item.sku}' already exists")

        conn.execute(
            """INSERT INTO inventory_items
               (id, name, sku, category, quantity, unit, min_stock,
                cost_per_unit, sell_price, vendor, location, notes, business)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.name,
                item.sku,
                item.category,
                item.quantity,
                item.unit,
                item.min_stock,
                item.cost_per_unit,
                item.sell_price,
                item.vendor,
                item.location,
                item.notes,
                item.business,
            )
        )

        row = conn.execute(
            "SELECT * FROM inventory_items ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return {"item": dict_row(row)}


@router.get("/items/{item_id}")
def get_item(item_id: str):
    """Get inventory item detail."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"item": dict_row(row)}


@router.patch("/items/{item_id}")
def update_item(item_id: str, update: ItemUpdate):
    """Update an inventory item."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Item not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Check SKU uniqueness if changing
        if "sku" in data and data["sku"]:
            sku_check = conn.execute(
                "SELECT id FROM inventory_items WHERE sku = ? AND id != ?",
                (data["sku"], item_id)
            ).fetchone()
            if sku_check:
                raise HTTPException(status_code=409, detail=f"SKU '{data['sku']}' already exists")

        fields = []
        values = []
        for key, val in data.items():
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(item_id)

        conn.execute(
            f"UPDATE inventory_items SET {', '.join(fields)} WHERE id = ?", values
        )

        row = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        return {"item": dict_row(row)}


@router.delete("/items/{item_id}")
def delete_item(item_id: str):
    """Delete an inventory item."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Item not found")

        conn.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
        return {"status": "deleted", "item_id": item_id}


@router.get("/low-stock")
def low_stock_items():
    """Items where quantity is below min_stock threshold."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT *, (min_stock - quantity) as deficit
               FROM inventory_items
               WHERE quantity < min_stock AND min_stock > 0
               ORDER BY (min_stock - quantity) / min_stock DESC"""
        ).fetchall()

        items = dict_rows(rows)
        return {"items": items, "total": len(items)}


# ── Vendors ──────────────────────────────────────────────────────────

@router.get("/vendors")
def list_vendors(
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all vendors."""
    clauses = []
    params = []

    if search:
        clauses.append("(name LIKE ? OR contact_name LIKE ? OR email LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM vendors{where} ORDER BY name LIMIT ? OFFSET ?",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM vendors{where}", params_count
        ).fetchone()[0]

        return {"vendors": dict_rows(rows), "total": total, "limit": limit, "offset": offset}


@router.post("/vendors")
def create_vendor(vendor: VendorCreate):
    """Create a new vendor."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO vendors
               (id, name, contact_name, email, phone, address, account_number, lead_time_days, notes)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                vendor.name,
                vendor.contact_name,
                vendor.email,
                vendor.phone,
                vendor.address,
                vendor.account_number,
                vendor.lead_time_days,
                vendor.notes,
            )
        )

        row = conn.execute(
            "SELECT * FROM vendors ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return {"vendor": dict_row(row)}


@router.patch("/vendors/{vendor_id}")
def update_vendor(vendor_id: str, update: VendorUpdate):
    """Update a vendor."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Vendor not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        fields = []
        values = []
        for key, val in data.items():
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(vendor_id)

        conn.execute(
            f"UPDATE vendors SET {', '.join(fields)} WHERE id = ?", values
        )

        row = conn.execute(
            "SELECT * FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        return {"vendor": dict_row(row)}


# ── Dashboard ────────────────────────────────────────────────────────

@router.get("/dashboard")
def inventory_dashboard():
    """Summary stats: total value, low stock count, breakdown by category."""
    with get_db() as conn:
        # Total inventory value (quantity * cost_per_unit)
        value_row = conn.execute(
            "SELECT COALESCE(SUM(quantity * cost_per_unit), 0) as total_value, COUNT(*) as total_items FROM inventory_items"
        ).fetchone()

        # Low stock count
        low_stock_count = conn.execute(
            "SELECT COUNT(*) FROM inventory_items WHERE quantity < min_stock AND min_stock > 0"
        ).fetchone()[0]

        # By category
        by_category = dict_rows(conn.execute(
            """SELECT category, COUNT(*) as item_count,
                      SUM(quantity * cost_per_unit) as total_value,
                      SUM(CASE WHEN quantity < min_stock AND min_stock > 0 THEN 1 ELSE 0 END) as low_stock
               FROM inventory_items
               GROUP BY category ORDER BY total_value DESC"""
        ).fetchall())

        # By business
        by_business = dict_rows(conn.execute(
            """SELECT business, COUNT(*) as item_count,
                      SUM(quantity * cost_per_unit) as total_value
               FROM inventory_items
               GROUP BY business"""
        ).fetchall())

        # Vendor summary
        vendor_count = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]

        return {
            "total_items": value_row["total_items"],
            "total_value": round(value_row["total_value"], 2),
            "low_stock_count": low_stock_count,
            "by_category": by_category,
            "by_business": by_business,
            "vendor_count": vendor_count,
        }
