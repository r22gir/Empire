"""
StoreFrontForge — Retail Store Management / POS Module.
Full CRUD for stores, products, inventory, transactions, customers,
employees, shifts, suppliers, purchase orders, and gift cards.
All tables prefixed sf2_ to avoid collision with existing sf_ (SupportForge) tables.
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

router = APIRouter(prefix="/storefront", tags=["storefront"])

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")


# ── Database helpers ────────────────────────────────────────────

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for k in ("variants", "tags", "payment_details"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _rows_to_list(rows):
    return [_row_to_dict(r) for r in rows]


# ── Table creation ──────────────────────────────────────────────

def _init_tables():
    c = _conn()
    try:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS sf2_stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE,
                address TEXT,
                city TEXT,
                state TEXT,
                country TEXT DEFAULT 'US',
                phone TEXT,
                email TEXT,
                timezone TEXT DEFAULT 'America/New_York',
                currency TEXT DEFAULT 'USD',
                tax_rate REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sf2_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER,
                sku TEXT,
                barcode TEXT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                subcategory TEXT,
                cost_price REAL DEFAULT 0.0,
                retail_price REAL DEFAULT 0.0,
                wholesale_price REAL DEFAULT 0.0,
                tax_exempt INTEGER DEFAULT 0,
                track_inventory INTEGER DEFAULT 1,
                image_url TEXT,
                weight REAL,
                weight_unit TEXT DEFAULT 'lb',
                variants TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                supplier_id INTEGER,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sf2_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                store_id INTEGER NOT NULL,
                variant_key TEXT DEFAULT '',
                quantity REAL DEFAULT 0,
                reorder_point REAL DEFAULT 0,
                reorder_quantity REAL DEFAULT 0,
                bin_location TEXT,
                last_counted TEXT,
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(product_id, store_id, variant_key)
            );

            CREATE TABLE IF NOT EXISTS sf2_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER,
                transaction_number TEXT UNIQUE,
                employee_id INTEGER,
                customer_id INTEGER,
                subtotal REAL DEFAULT 0.0,
                discount_amount REAL DEFAULT 0.0,
                discount_type TEXT,
                tax_amount REAL DEFAULT 0.0,
                total REAL DEFAULT 0.0,
                payment_method TEXT DEFAULT 'cash',
                payment_details TEXT DEFAULT '{}',
                status TEXT DEFAULT 'completed',
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sf2_transaction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                product_id INTEGER,
                variant_key TEXT DEFAULT '',
                quantity REAL DEFAULT 1,
                unit_price REAL DEFAULT 0.0,
                discount REAL DEFAULT 0.0,
                tax REAL DEFAULT 0.0,
                total REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS sf2_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                loyalty_points INTEGER DEFAULT 0,
                loyalty_tier TEXT DEFAULT 'bronze',
                total_spent REAL DEFAULT 0.0,
                visit_count INTEGER DEFAULT 0,
                last_visit TEXT,
                birthday TEXT,
                notes TEXT,
                locale TEXT DEFAULT 'en',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sf2_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                role TEXT DEFAULT 'cashier',
                pin TEXT,
                hourly_rate REAL DEFAULT 0.0,
                commission_rate REAL DEFAULT 0.0,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sf2_shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                store_id INTEGER,
                clock_in TEXT DEFAULT (datetime('now')),
                clock_out TEXT,
                cash_drawer_start REAL DEFAULT 0.0,
                cash_drawer_end REAL,
                total_sales REAL DEFAULT 0.0,
                total_transactions INTEGER DEFAULT 0,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS sf2_suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact_name TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                payment_terms TEXT,
                lead_time_days INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sf2_purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER,
                supplier_id INTEGER,
                po_number TEXT UNIQUE,
                status TEXT DEFAULT 'draft',
                order_date TEXT DEFAULT (datetime('now')),
                expected_date TEXT,
                received_date TEXT,
                total REAL DEFAULT 0.0,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sf2_po_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_id INTEGER NOT NULL,
                product_id INTEGER,
                quantity_ordered REAL DEFAULT 0,
                quantity_received REAL DEFAULT 0,
                unit_cost REAL DEFAULT 0.0,
                total REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS sf2_gift_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0.0,
                original_amount REAL DEFAULT 0.0,
                customer_id INTEGER,
                status TEXT DEFAULT 'active',
                expires_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        c.commit()
        logger.info("StoreFrontForge: sf2_ tables initialized")
    finally:
        c.close()


# Run on import
_init_tables()


# ── Pydantic Schemas ────────────────────────────────────────────

class StoreCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "US"
    phone: Optional[str] = None
    email: Optional[str] = None
    timezone: str = "America/New_York"
    currency: str = "USD"
    tax_rate: float = 0.0
    status: str = "active"


class ProductCreate(BaseModel):
    store_id: Optional[int] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    cost_price: float = 0.0
    retail_price: float = 0.0
    wholesale_price: float = 0.0
    tax_exempt: bool = False
    track_inventory: bool = True
    image_url: Optional[str] = None
    weight: Optional[float] = None
    weight_unit: str = "lb"
    variants: Optional[list] = []
    tags: Optional[list] = []
    supplier_id: Optional[int] = None
    active: bool = True


class InventoryAdjust(BaseModel):
    product_id: int
    store_id: int
    variant_key: str = ""
    quantity_change: float
    reason: Optional[str] = None


class SaleItem(BaseModel):
    product_id: int
    variant_key: str = ""
    quantity: float = 1
    unit_price: Optional[float] = None
    discount: float = 0.0


class SaleCreate(BaseModel):
    store_id: int
    employee_id: Optional[int] = None
    customer_id: Optional[int] = None
    items: List[SaleItem]
    discount_amount: float = 0.0
    discount_type: Optional[str] = None
    payment_method: str = "cash"
    payment_details: Optional[dict] = {}
    notes: Optional[str] = None


class CustomerCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    birthday: Optional[str] = None
    notes: Optional[str] = None
    locale: str = "en"


class EmployeeCreate(BaseModel):
    store_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "cashier"
    pin: Optional[str] = None
    hourly_rate: float = 0.0
    commission_rate: float = 0.0


class ShiftClockIn(BaseModel):
    employee_id: int
    store_id: Optional[int] = None
    cash_drawer_start: float = 0.0


class ShiftClockOut(BaseModel):
    shift_id: int
    cash_drawer_end: Optional[float] = None
    notes: Optional[str] = None


class SupplierCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: int = 0
    notes: Optional[str] = None


class POItemCreate(BaseModel):
    product_id: int
    quantity_ordered: float
    unit_cost: float = 0.0


class PurchaseOrderCreate(BaseModel):
    store_id: int
    supplier_id: int
    expected_date: Optional[str] = None
    items: List[POItemCreate]
    notes: Optional[str] = None


class GiftCardCreate(BaseModel):
    amount: float
    customer_id: Optional[int] = None
    expires_at: Optional[str] = None


class GiftCardRedeem(BaseModel):
    amount: float


class LoyaltyRedeem(BaseModel):
    points: int


# ── STORES ──────────────────────────────────────────────────────

@router.get("/stores")
async def list_stores(status: Optional[str] = None):
    c = _conn()
    try:
        q = "SELECT * FROM sf2_stores"
        params = []
        if status:
            q += " WHERE status = ?"
            params.append(status)
        q += " ORDER BY name"
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


@router.post("/stores")
async def create_store(body: StoreCreate):
    c = _conn()
    try:
        slug = body.slug or body.name.lower().replace(" ", "-")
        c.execute(
            """INSERT INTO sf2_stores (name, slug, address, city, state, country,
               phone, email, timezone, currency, tax_rate, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (body.name, slug, body.address, body.city, body.state, body.country,
             body.phone, body.email, body.timezone, body.currency, body.tax_rate, body.status),
        )
        c.commit()
        store_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = c.execute("SELECT * FROM sf2_stores WHERE id = ?", (store_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.get("/stores/{store_id}")
async def get_store(store_id: int):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM sf2_stores WHERE id = ?", (store_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Store not found")
        return _row_to_dict(row)
    finally:
        c.close()


@router.put("/stores/{store_id}")
async def update_store(store_id: int, body: StoreCreate):
    c = _conn()
    try:
        slug = body.slug or body.name.lower().replace(" ", "-")
        c.execute(
            """UPDATE sf2_stores SET name=?, slug=?, address=?, city=?, state=?, country=?,
               phone=?, email=?, timezone=?, currency=?, tax_rate=?, status=?
               WHERE id=?""",
            (body.name, slug, body.address, body.city, body.state, body.country,
             body.phone, body.email, body.timezone, body.currency, body.tax_rate, body.status, store_id),
        )
        c.commit()
        row = c.execute("SELECT * FROM sf2_stores WHERE id = ?", (store_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Store not found")
        return _row_to_dict(row)
    finally:
        c.close()


# ── PRODUCTS ────────────────────────────────────────────────────

@router.get("/products")
async def list_products(
    store_id: Optional[int] = None,
    category: Optional[str] = None,
    active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    c = _conn()
    try:
        q = "SELECT * FROM sf2_products WHERE 1=1"
        params: list = []
        if store_id is not None:
            q += " AND store_id = ?"
            params.append(store_id)
        if category:
            q += " AND category = ?"
            params.append(category)
        if active is not None:
            q += " AND active = ?"
            params.append(1 if active else 0)
        if search:
            q += " AND (name LIKE ? OR sku LIKE ? OR barcode LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        q += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


@router.post("/products")
async def create_product(body: ProductCreate):
    c = _conn()
    try:
        sku = body.sku or f"SKU-{uuid.uuid4().hex[:8].upper()}"
        c.execute(
            """INSERT INTO sf2_products (store_id, sku, barcode, name, description,
               category, subcategory, cost_price, retail_price, wholesale_price,
               tax_exempt, track_inventory, image_url, weight, weight_unit,
               variants, tags, supplier_id, active)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (body.store_id, sku, body.barcode, body.name, body.description,
             body.category, body.subcategory, body.cost_price, body.retail_price,
             body.wholesale_price, int(body.tax_exempt), int(body.track_inventory),
             body.image_url, body.weight, body.weight_unit,
             json.dumps(body.variants or []), json.dumps(body.tags or []),
             body.supplier_id, int(body.active)),
        )
        c.commit()
        pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = c.execute("SELECT * FROM sf2_products WHERE id = ?", (pid,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.get("/products/{product_id}")
async def get_product(product_id: int):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM sf2_products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Product not found")
        return _row_to_dict(row)
    finally:
        c.close()


@router.put("/products/{product_id}")
async def update_product(product_id: int, body: ProductCreate):
    c = _conn()
    try:
        c.execute(
            """UPDATE sf2_products SET store_id=?, sku=?, barcode=?, name=?, description=?,
               category=?, subcategory=?, cost_price=?, retail_price=?, wholesale_price=?,
               tax_exempt=?, track_inventory=?, image_url=?, weight=?, weight_unit=?,
               variants=?, tags=?, supplier_id=?, active=?, updated_at=datetime('now')
               WHERE id=?""",
            (body.store_id, body.sku, body.barcode, body.name, body.description,
             body.category, body.subcategory, body.cost_price, body.retail_price,
             body.wholesale_price, int(body.tax_exempt), int(body.track_inventory),
             body.image_url, body.weight, body.weight_unit,
             json.dumps(body.variants or []), json.dumps(body.tags or []),
             body.supplier_id, int(body.active), product_id),
        )
        c.commit()
        if c.execute("SELECT changes()").fetchone()[0] == 0:
            raise HTTPException(404, "Product not found")
        row = c.execute("SELECT * FROM sf2_products WHERE id = ?", (product_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.delete("/products/{product_id}")
async def delete_product(product_id: int):
    c = _conn()
    try:
        c.execute("DELETE FROM sf2_products WHERE id = ?", (product_id,))
        c.commit()
        if c.execute("SELECT changes()").fetchone()[0] == 0:
            raise HTTPException(404, "Product not found")
        return {"deleted": True, "id": product_id}
    finally:
        c.close()


@router.get("/products/barcode/{code}")
async def get_product_by_barcode(code: str):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM sf2_products WHERE barcode = ?", (code,)).fetchone()
        if not row:
            raise HTTPException(404, "Product not found for barcode")
        return _row_to_dict(row)
    finally:
        c.close()


# ── INVENTORY ───────────────────────────────────────────────────

@router.get("/inventory/{store_id}")
async def get_inventory(store_id: int):
    c = _conn()
    try:
        rows = c.execute(
            """SELECT i.*, p.name as product_name, p.sku, p.barcode
               FROM sf2_inventory i
               JOIN sf2_products p ON p.id = i.product_id
               WHERE i.store_id = ?
               ORDER BY p.name""",
            (store_id,),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        c.close()


@router.patch("/inventory/adjust")
async def adjust_inventory(body: InventoryAdjust):
    c = _conn()
    try:
        existing = c.execute(
            "SELECT * FROM sf2_inventory WHERE product_id=? AND store_id=? AND variant_key=?",
            (body.product_id, body.store_id, body.variant_key),
        ).fetchone()
        if existing:
            c.execute(
                """UPDATE sf2_inventory SET quantity = quantity + ?, updated_at = datetime('now')
                   WHERE product_id=? AND store_id=? AND variant_key=?""",
                (body.quantity_change, body.product_id, body.store_id, body.variant_key),
            )
        else:
            c.execute(
                """INSERT INTO sf2_inventory (product_id, store_id, variant_key, quantity)
                   VALUES (?,?,?,?)""",
                (body.product_id, body.store_id, body.variant_key, body.quantity_change),
            )
        c.commit()
        row = c.execute(
            "SELECT * FROM sf2_inventory WHERE product_id=? AND store_id=? AND variant_key=?",
            (body.product_id, body.store_id, body.variant_key),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.get("/inventory/low-stock")
async def low_stock(store_id: Optional[int] = None):
    c = _conn()
    try:
        q = """SELECT i.*, p.name as product_name, p.sku
               FROM sf2_inventory i
               JOIN sf2_products p ON p.id = i.product_id
               WHERE i.quantity <= i.reorder_point"""
        params: list = []
        if store_id is not None:
            q += " AND i.store_id = ?"
            params.append(store_id)
        q += " ORDER BY (i.quantity - i.reorder_point) ASC"
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


# ── POS / TRANSACTIONS ─────────────────────────────────────────

def _generate_txn_number():
    now = datetime.utcnow()
    return f"TXN-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


@router.post("/pos/sale")
async def create_sale(body: SaleCreate):
    c = _conn()
    try:
        txn_num = _generate_txn_number()

        # Get store tax rate
        store_row = c.execute("SELECT tax_rate FROM sf2_stores WHERE id = ?", (body.store_id,)).fetchone()
        tax_rate = store_row["tax_rate"] if store_row else 0.0

        subtotal = 0.0
        tax_total = 0.0
        item_rows = []

        for item in body.items:
            # Resolve price
            if item.unit_price is not None:
                price = item.unit_price
            else:
                prod = c.execute("SELECT retail_price, tax_exempt FROM sf2_products WHERE id = ?", (item.product_id,)).fetchone()
                if not prod:
                    raise HTTPException(400, f"Product {item.product_id} not found")
                price = prod["retail_price"]

            line_sub = price * item.quantity - item.discount
            prod_row = c.execute("SELECT tax_exempt FROM sf2_products WHERE id = ?", (item.product_id,)).fetchone()
            is_exempt = prod_row and prod_row["tax_exempt"]
            line_tax = 0.0 if is_exempt else round(line_sub * tax_rate / 100, 2)
            line_total = round(line_sub + line_tax, 2)

            subtotal += line_sub
            tax_total += line_tax
            item_rows.append((item.product_id, item.variant_key, item.quantity, price, item.discount, line_tax, line_total))

            # Deduct inventory
            c.execute(
                """UPDATE sf2_inventory SET quantity = quantity - ?, updated_at = datetime('now')
                   WHERE product_id=? AND store_id=? AND variant_key=?""",
                (item.quantity, item.product_id, body.store_id, item.variant_key),
            )

        total = round(subtotal - body.discount_amount + tax_total, 2)

        c.execute(
            """INSERT INTO sf2_transactions (store_id, transaction_number, employee_id,
               customer_id, subtotal, discount_amount, discount_type, tax_amount, total,
               payment_method, payment_details, status, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (body.store_id, txn_num, body.employee_id, body.customer_id,
             round(subtotal, 2), body.discount_amount, body.discount_type,
             round(tax_total, 2), total, body.payment_method,
             json.dumps(body.payment_details or {}), "completed", body.notes),
        )
        txn_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]

        for ir in item_rows:
            c.execute(
                """INSERT INTO sf2_transaction_items (transaction_id, product_id, variant_key,
                   quantity, unit_price, discount, tax, total)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (txn_id, *ir),
            )

        # Update customer stats
        if body.customer_id:
            loyalty_earned = int(total)  # 1 point per dollar
            c.execute(
                """UPDATE sf2_customers SET total_spent = total_spent + ?,
                   visit_count = visit_count + 1, last_visit = datetime('now'),
                   loyalty_points = loyalty_points + ?
                   WHERE id = ?""",
                (total, loyalty_earned, body.customer_id),
            )

        # Update shift stats
        if body.employee_id:
            c.execute(
                """UPDATE sf2_shifts SET total_sales = total_sales + ?,
                   total_transactions = total_transactions + 1
                   WHERE employee_id = ? AND clock_out IS NULL""",
                (total, body.employee_id),
            )

        c.commit()
        txn = c.execute("SELECT * FROM sf2_transactions WHERE id = ?", (txn_id,)).fetchone()
        items = c.execute("SELECT * FROM sf2_transaction_items WHERE transaction_id = ?", (txn_id,)).fetchall()
        result = _row_to_dict(txn)
        result["items"] = _rows_to_list(items)
        return result
    finally:
        c.close()


@router.get("/transactions")
async def list_transactions(
    store_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    c = _conn()
    try:
        q = "SELECT * FROM sf2_transactions WHERE 1=1"
        params: list = []
        if store_id is not None:
            q += " AND store_id = ?"
            params.append(store_id)
        if status:
            q += " AND status = ?"
            params.append(status)
        if date_from:
            q += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            q += " AND created_at <= ?"
            params.append(date_to + " 23:59:59")
        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


@router.get("/transactions/{txn_id}")
async def get_transaction(txn_id: int):
    c = _conn()
    try:
        txn = c.execute("SELECT * FROM sf2_transactions WHERE id = ?", (txn_id,)).fetchone()
        if not txn:
            raise HTTPException(404, "Transaction not found")
        items = c.execute("SELECT * FROM sf2_transaction_items WHERE transaction_id = ?", (txn_id,)).fetchall()
        result = _row_to_dict(txn)
        result["items"] = _rows_to_list(items)
        return result
    finally:
        c.close()


@router.post("/transactions/{txn_id}/refund")
async def refund_transaction(txn_id: int):
    c = _conn()
    try:
        txn = c.execute("SELECT * FROM sf2_transactions WHERE id = ?", (txn_id,)).fetchone()
        if not txn:
            raise HTTPException(404, "Transaction not found")
        if txn["status"] == "refunded":
            raise HTTPException(400, "Transaction already refunded")

        # Restore inventory
        items = c.execute("SELECT * FROM sf2_transaction_items WHERE transaction_id = ?", (txn_id,)).fetchall()
        for item in items:
            c.execute(
                """UPDATE sf2_inventory SET quantity = quantity + ?, updated_at = datetime('now')
                   WHERE product_id=? AND store_id=? AND variant_key=?""",
                (item["quantity"], item["product_id"], txn["store_id"], item["variant_key"]),
            )

        # Reverse customer stats
        if txn["customer_id"]:
            loyalty_back = int(txn["total"])
            c.execute(
                """UPDATE sf2_customers SET total_spent = total_spent - ?,
                   loyalty_points = MAX(0, loyalty_points - ?)
                   WHERE id = ?""",
                (txn["total"], loyalty_back, txn["customer_id"]),
            )

        c.execute("UPDATE sf2_transactions SET status = 'refunded' WHERE id = ?", (txn_id,))
        c.commit()

        result = _row_to_dict(c.execute("SELECT * FROM sf2_transactions WHERE id = ?", (txn_id,)).fetchone())
        result["items"] = _rows_to_list(items)
        return result
    finally:
        c.close()


@router.get("/pos/receipt/{txn_id}")
async def get_receipt(txn_id: int):
    c = _conn()
    try:
        txn = c.execute("SELECT * FROM sf2_transactions WHERE id = ?", (txn_id,)).fetchone()
        if not txn:
            raise HTTPException(404, "Transaction not found")
        items = c.execute(
            """SELECT ti.*, p.name as product_name, p.sku
               FROM sf2_transaction_items ti
               LEFT JOIN sf2_products p ON p.id = ti.product_id
               WHERE ti.transaction_id = ?""",
            (txn_id,),
        ).fetchall()
        store = c.execute("SELECT * FROM sf2_stores WHERE id = ?", (txn["store_id"],)).fetchone()
        customer = None
        if txn["customer_id"]:
            customer = c.execute("SELECT first_name, last_name, email, loyalty_points FROM sf2_customers WHERE id = ?", (txn["customer_id"],)).fetchone()
        employee = None
        if txn["employee_id"]:
            employee = c.execute("SELECT name FROM sf2_employees WHERE id = ?", (txn["employee_id"],)).fetchone()

        return {
            "transaction": _row_to_dict(txn),
            "items": _rows_to_list(items),
            "store": _row_to_dict(store),
            "customer": _row_to_dict(customer),
            "employee": _row_to_dict(employee),
        }
    finally:
        c.close()


# ── CUSTOMERS ───────────────────────────────────────────────────

@router.get("/customers")
async def list_customers(search: Optional[str] = None, limit: int = 100, offset: int = 0):
    c = _conn()
    try:
        q = "SELECT * FROM sf2_customers WHERE 1=1"
        params: list = []
        if search:
            q += " AND (first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])
        q += " ORDER BY last_name, first_name LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


@router.post("/customers")
async def create_customer(body: CustomerCreate):
    c = _conn()
    try:
        c.execute(
            """INSERT INTO sf2_customers (first_name, last_name, email, phone,
               address, city, state, birthday, notes, locale)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (body.first_name, body.last_name, body.email, body.phone,
             body.address, body.city, body.state, body.birthday, body.notes, body.locale),
        )
        c.commit()
        cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = c.execute("SELECT * FROM sf2_customers WHERE id = ?", (cid,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: int):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM sf2_customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Customer not found")
        return _row_to_dict(row)
    finally:
        c.close()


@router.put("/customers/{customer_id}")
async def update_customer(customer_id: int, body: CustomerCreate):
    c = _conn()
    try:
        c.execute(
            """UPDATE sf2_customers SET first_name=?, last_name=?, email=?, phone=?,
               address=?, city=?, state=?, birthday=?, notes=?, locale=?
               WHERE id=?""",
            (body.first_name, body.last_name, body.email, body.phone,
             body.address, body.city, body.state, body.birthday, body.notes, body.locale, customer_id),
        )
        c.commit()
        if c.execute("SELECT changes()").fetchone()[0] == 0:
            raise HTTPException(404, "Customer not found")
        row = c.execute("SELECT * FROM sf2_customers WHERE id = ?", (customer_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.get("/customers/{customer_id}/loyalty")
async def get_loyalty(customer_id: int):
    c = _conn()
    try:
        row = c.execute(
            "SELECT id, first_name, last_name, loyalty_points, loyalty_tier, total_spent, visit_count FROM sf2_customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Customer not found")
        return _row_to_dict(row)
    finally:
        c.close()


@router.post("/customers/{customer_id}/loyalty/redeem")
async def redeem_loyalty(customer_id: int, body: LoyaltyRedeem):
    c = _conn()
    try:
        row = c.execute("SELECT loyalty_points FROM sf2_customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Customer not found")
        if row["loyalty_points"] < body.points:
            raise HTTPException(400, f"Insufficient points: has {row['loyalty_points']}, requested {body.points}")
        c.execute(
            "UPDATE sf2_customers SET loyalty_points = loyalty_points - ? WHERE id = ?",
            (body.points, customer_id),
        )
        c.commit()
        updated = c.execute("SELECT id, first_name, last_name, loyalty_points, loyalty_tier FROM sf2_customers WHERE id = ?", (customer_id,)).fetchone()
        return {"redeemed": body.points, "customer": _row_to_dict(updated)}
    finally:
        c.close()


# ── EMPLOYEES ───────────────────────────────────────────────────

@router.get("/employees")
async def list_employees(store_id: Optional[int] = None, active: Optional[bool] = None):
    c = _conn()
    try:
        q = "SELECT * FROM sf2_employees WHERE 1=1"
        params: list = []
        if store_id is not None:
            q += " AND store_id = ?"
            params.append(store_id)
        if active is not None:
            q += " AND active = ?"
            params.append(1 if active else 0)
        q += " ORDER BY name"
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


@router.post("/employees")
async def create_employee(body: EmployeeCreate):
    c = _conn()
    try:
        c.execute(
            """INSERT INTO sf2_employees (store_id, name, email, phone, role, pin,
               hourly_rate, commission_rate)
               VALUES (?,?,?,?,?,?,?,?)""",
            (body.store_id, body.name, body.email, body.phone, body.role,
             body.pin, body.hourly_rate, body.commission_rate),
        )
        c.commit()
        eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = c.execute("SELECT * FROM sf2_employees WHERE id = ?", (eid,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


# ── SHIFTS ──────────────────────────────────────────────────────

@router.post("/shifts/clock-in")
async def clock_in(body: ShiftClockIn):
    c = _conn()
    try:
        # Check not already clocked in
        existing = c.execute(
            "SELECT id FROM sf2_shifts WHERE employee_id = ? AND clock_out IS NULL",
            (body.employee_id,),
        ).fetchone()
        if existing:
            raise HTTPException(400, "Employee already clocked in")
        c.execute(
            "INSERT INTO sf2_shifts (employee_id, store_id, cash_drawer_start) VALUES (?,?,?)",
            (body.employee_id, body.store_id, body.cash_drawer_start),
        )
        c.commit()
        sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = c.execute("SELECT * FROM sf2_shifts WHERE id = ?", (sid,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.post("/shifts/clock-out")
async def clock_out(body: ShiftClockOut):
    c = _conn()
    try:
        c.execute(
            """UPDATE sf2_shifts SET clock_out = datetime('now'), cash_drawer_end = ?, notes = ?
               WHERE id = ? AND clock_out IS NULL""",
            (body.cash_drawer_end, body.notes, body.shift_id),
        )
        c.commit()
        if c.execute("SELECT changes()").fetchone()[0] == 0:
            raise HTTPException(404, "Active shift not found")
        row = c.execute("SELECT * FROM sf2_shifts WHERE id = ?", (body.shift_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.get("/shifts/active")
async def active_shifts(store_id: Optional[int] = None):
    c = _conn()
    try:
        q = """SELECT s.*, e.name as employee_name
               FROM sf2_shifts s
               JOIN sf2_employees e ON e.id = s.employee_id
               WHERE s.clock_out IS NULL"""
        params: list = []
        if store_id is not None:
            q += " AND s.store_id = ?"
            params.append(store_id)
        q += " ORDER BY s.clock_in DESC"
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


# ── SUPPLIERS ───────────────────────────────────────────────────

@router.get("/suppliers")
async def list_suppliers():
    c = _conn()
    try:
        return _rows_to_list(c.execute("SELECT * FROM sf2_suppliers ORDER BY name").fetchall())
    finally:
        c.close()


@router.post("/suppliers")
async def create_supplier(body: SupplierCreate):
    c = _conn()
    try:
        c.execute(
            """INSERT INTO sf2_suppliers (name, contact_name, email, phone, address,
               payment_terms, lead_time_days, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (body.name, body.contact_name, body.email, body.phone, body.address,
             body.payment_terms, body.lead_time_days, body.notes),
        )
        c.commit()
        sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = c.execute("SELECT * FROM sf2_suppliers WHERE id = ?", (sid,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


# ── PURCHASE ORDERS ─────────────────────────────────────────────

@router.post("/purchase-orders")
async def create_purchase_order(body: PurchaseOrderCreate):
    c = _conn()
    try:
        po_num = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        total = sum(i.quantity_ordered * i.unit_cost for i in body.items)
        c.execute(
            """INSERT INTO sf2_purchase_orders (store_id, supplier_id, po_number, status,
               expected_date, total, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (body.store_id, body.supplier_id, po_num, "draft", body.expected_date, round(total, 2), body.notes),
        )
        po_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in body.items:
            item_total = round(item.quantity_ordered * item.unit_cost, 2)
            c.execute(
                """INSERT INTO sf2_po_items (po_id, product_id, quantity_ordered, unit_cost, total)
                   VALUES (?,?,?,?,?)""",
                (po_id, item.product_id, item.quantity_ordered, item.unit_cost, item_total),
            )
        c.commit()
        po = c.execute("SELECT * FROM sf2_purchase_orders WHERE id = ?", (po_id,)).fetchone()
        items = c.execute("SELECT * FROM sf2_po_items WHERE po_id = ?", (po_id,)).fetchall()
        result = _row_to_dict(po)
        result["items"] = _rows_to_list(items)
        return result
    finally:
        c.close()


@router.get("/purchase-orders/{po_id}")
async def get_purchase_order(po_id: int):
    c = _conn()
    try:
        po = c.execute("SELECT * FROM sf2_purchase_orders WHERE id = ?", (po_id,)).fetchone()
        if not po:
            raise HTTPException(404, "Purchase order not found")
        items = c.execute("SELECT * FROM sf2_po_items WHERE po_id = ?", (po_id,)).fetchall()
        result = _row_to_dict(po)
        result["items"] = _rows_to_list(items)
        return result
    finally:
        c.close()


class POReceiveItem(BaseModel):
    po_item_id: int
    quantity_received: float


class POReceive(BaseModel):
    items: List[POReceiveItem]


@router.patch("/purchase-orders/{po_id}/receive")
async def receive_purchase_order(po_id: int, body: POReceive):
    c = _conn()
    try:
        po = c.execute("SELECT * FROM sf2_purchase_orders WHERE id = ?", (po_id,)).fetchone()
        if not po:
            raise HTTPException(404, "Purchase order not found")

        for ri in body.items:
            poi = c.execute("SELECT * FROM sf2_po_items WHERE id = ? AND po_id = ?", (ri.po_item_id, po_id)).fetchone()
            if not poi:
                continue
            c.execute(
                "UPDATE sf2_po_items SET quantity_received = quantity_received + ? WHERE id = ?",
                (ri.quantity_received, ri.po_item_id),
            )
            # Add to inventory
            existing = c.execute(
                "SELECT id FROM sf2_inventory WHERE product_id = ? AND store_id = ? AND variant_key = ''",
                (poi["product_id"], po["store_id"]),
            ).fetchone()
            if existing:
                c.execute(
                    "UPDATE sf2_inventory SET quantity = quantity + ?, updated_at = datetime('now') WHERE id = ?",
                    (ri.quantity_received, existing["id"]),
                )
            else:
                c.execute(
                    "INSERT INTO sf2_inventory (product_id, store_id, variant_key, quantity) VALUES (?,?,?,?)",
                    (poi["product_id"], po["store_id"], "", ri.quantity_received),
                )

        c.execute(
            "UPDATE sf2_purchase_orders SET status = 'received', received_date = datetime('now') WHERE id = ?",
            (po_id,),
        )
        c.commit()

        po = c.execute("SELECT * FROM sf2_purchase_orders WHERE id = ?", (po_id,)).fetchone()
        items = c.execute("SELECT * FROM sf2_po_items WHERE po_id = ?", (po_id,)).fetchall()
        result = _row_to_dict(po)
        result["items"] = _rows_to_list(items)
        return result
    finally:
        c.close()


# ── GIFT CARDS ──────────────────────────────────────────────────

@router.post("/gift-cards")
async def create_gift_card(body: GiftCardCreate):
    c = _conn()
    try:
        card_num = f"GC-{uuid.uuid4().hex[:12].upper()}"
        c.execute(
            """INSERT INTO sf2_gift_cards (card_number, balance, original_amount, customer_id, expires_at)
               VALUES (?,?,?,?,?)""",
            (card_num, body.amount, body.amount, body.customer_id, body.expires_at),
        )
        c.commit()
        gcid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = c.execute("SELECT * FROM sf2_gift_cards WHERE id = ?", (gcid,)).fetchone()
        return _row_to_dict(row)
    finally:
        c.close()


@router.get("/gift-cards/{number}/balance")
async def gift_card_balance(number: str):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM sf2_gift_cards WHERE card_number = ?", (number,)).fetchone()
        if not row:
            raise HTTPException(404, "Gift card not found")
        return _row_to_dict(row)
    finally:
        c.close()


@router.post("/gift-cards/{number}/redeem")
async def redeem_gift_card(number: str, body: GiftCardRedeem):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM sf2_gift_cards WHERE card_number = ?", (number,)).fetchone()
        if not row:
            raise HTTPException(404, "Gift card not found")
        if row["status"] != "active":
            raise HTTPException(400, "Gift card is not active")
        if row["expires_at"] and row["expires_at"] < datetime.utcnow().isoformat():
            raise HTTPException(400, "Gift card has expired")
        if row["balance"] < body.amount:
            raise HTTPException(400, f"Insufficient balance: {row['balance']}")
        new_balance = round(row["balance"] - body.amount, 2)
        new_status = "active" if new_balance > 0 else "redeemed"
        c.execute(
            "UPDATE sf2_gift_cards SET balance = ?, status = ? WHERE card_number = ?",
            (new_balance, new_status, number),
        )
        c.commit()
        updated = c.execute("SELECT * FROM sf2_gift_cards WHERE card_number = ?", (number,)).fetchone()
        return {"redeemed": body.amount, "card": _row_to_dict(updated)}
    finally:
        c.close()


# ── REPORTS ─────────────────────────────────────────────────────

@router.get("/reports/daily/{report_date}")
async def daily_report(report_date: str, store_id: Optional[int] = None):
    """Daily sales summary for a given date (YYYY-MM-DD)."""
    c = _conn()
    try:
        q_base = "FROM sf2_transactions WHERE date(created_at) = ? AND status = 'completed'"
        params: list = [report_date]
        if store_id is not None:
            q_base += " AND store_id = ?"
            params.append(store_id)

        summary = c.execute(
            f"SELECT COUNT(*) as total_transactions, COALESCE(SUM(total),0) as total_revenue, "
            f"COALESCE(SUM(tax_amount),0) as total_tax, COALESCE(SUM(discount_amount),0) as total_discounts "
            f"{q_base}",
            params,
        ).fetchone()

        by_method = c.execute(
            f"SELECT payment_method, COUNT(*) as count, SUM(total) as total {q_base} GROUP BY payment_method",
            params,
        ).fetchall()

        # Refunds
        refund_params = list(params)
        refund_q = q_base.replace("status = 'completed'", "status = 'refunded'")
        refunds = c.execute(
            f"SELECT COUNT(*) as count, COALESCE(SUM(total),0) as total {refund_q}",
            refund_params,
        ).fetchone()

        return {
            "date": report_date,
            "store_id": store_id,
            "total_transactions": summary["total_transactions"],
            "total_revenue": round(summary["total_revenue"], 2),
            "total_tax": round(summary["total_tax"], 2),
            "total_discounts": round(summary["total_discounts"], 2),
            "by_payment_method": _rows_to_list(by_method),
            "refunds": {"count": refunds["count"], "total": round(refunds["total"], 2)},
        }
    finally:
        c.close()


@router.get("/reports/top-products")
async def top_products(
    store_id: Optional[int] = None,
    days: int = 30,
    limit: int = 20,
):
    c = _conn()
    try:
        q = """SELECT ti.product_id, p.name, p.sku,
                      SUM(ti.quantity) as units_sold, SUM(ti.total) as revenue
               FROM sf2_transaction_items ti
               JOIN sf2_transactions t ON t.id = ti.transaction_id
               JOIN sf2_products p ON p.id = ti.product_id
               WHERE t.status = 'completed'
                 AND t.created_at >= datetime('now', ?)"""
        params: list = [f"-{days} days"]
        if store_id is not None:
            q += " AND t.store_id = ?"
            params.append(store_id)
        q += " GROUP BY ti.product_id ORDER BY revenue DESC LIMIT ?"
        params.append(limit)
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


@router.get("/reports/revenue")
async def revenue_report(
    store_id: Optional[int] = None,
    period: str = "daily",
    days: int = 30,
):
    c = _conn()
    try:
        if period == "monthly":
            date_fmt = "%Y-%m"
        elif period == "weekly":
            date_fmt = "%Y-W%W"
        else:
            date_fmt = "%Y-%m-%d"

        q = f"""SELECT strftime('{date_fmt}', created_at) as period,
                       COUNT(*) as transactions, SUM(total) as revenue,
                       SUM(tax_amount) as tax, SUM(discount_amount) as discounts
                FROM sf2_transactions
                WHERE status = 'completed' AND created_at >= datetime('now', ?)"""
        params: list = [f"-{days} days"]
        if store_id is not None:
            q += " AND store_id = ?"
            params.append(store_id)
        q += f" GROUP BY strftime('{date_fmt}', created_at) ORDER BY period"
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()


@router.get("/reports/inventory-value")
async def inventory_value_report(store_id: Optional[int] = None):
    c = _conn()
    try:
        q = """SELECT i.store_id, s.name as store_name,
                      COUNT(DISTINCT i.product_id) as product_count,
                      SUM(i.quantity) as total_units,
                      SUM(i.quantity * p.cost_price) as total_cost_value,
                      SUM(i.quantity * p.retail_price) as total_retail_value
               FROM sf2_inventory i
               JOIN sf2_products p ON p.id = i.product_id
               JOIN sf2_stores s ON s.id = i.store_id
               WHERE i.quantity > 0"""
        params: list = []
        if store_id is not None:
            q += " AND i.store_id = ?"
            params.append(store_id)
        q += " GROUP BY i.store_id"
        return _rows_to_list(c.execute(q, params).fetchall())
    finally:
        c.close()
