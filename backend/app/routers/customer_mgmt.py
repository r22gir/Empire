"""
Empire CRM — Customer management, import from quotes, sales pipeline.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from pathlib import Path

from app.db.database import get_db, dict_row, dict_rows
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix="/crm", tags=["crm"])

QUOTES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "quotes"


# ── Schemas ──────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    company: Optional[str] = None
    type: str = "residential"
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    source: str = "direct"


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    company: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    source: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _enrich_customer(cust: dict) -> dict:
    """Parse JSON fields in a customer row."""
    if cust:
        cust["tags"] = json.loads(cust["tags"]) if cust.get("tags") else []
    return cust


# ── Routes ───────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/customers")
def list_customers(
    request: Request,
    search: Optional[str] = None,
    type: Optional[str] = None,
    source: Optional[str] = None,
    business: Optional[str] = None,
    sort_by: str = Query("name", description="name, total_revenue, created_at, lifetime_quotes"),
    sort_dir: str = Query("asc", description="asc or desc"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List customers with search and sort options."""
    clauses = []
    params = []

    if search:
        clauses.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR company LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s, s])
    if type:
        clauses.append("type = ?")
        params.append(type)
    if source:
        clauses.append("source = ?")
        params.append(source)
    if business:
        clauses.append("business = ?")
        params.append(business)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    # Validate sort column
    valid_sorts = {"name", "total_revenue", "created_at", "lifetime_quotes", "updated_at"}
    if sort_by not in valid_sorts:
        sort_by = "name"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM customers{where} ORDER BY {sort_by} {direction} LIMIT ? OFFSET ?",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM customers{where}", params_count
        ).fetchone()[0]

        customers = [_enrich_customer(dict_row(r)) for r in rows]
        return {"customers": customers, "total": total, "limit": limit, "offset": offset}


@limiter.limit("30/minute")
@router.post("/customers")
def create_customer(request: Request, customer: CustomerCreate):
    """Create a new customer."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO customers
               (id, name, email, phone, address, company, type, tags, notes, source)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                customer.name,
                customer.email,
                customer.phone,
                customer.address,
                customer.company,
                customer.type,
                json.dumps(customer.tags) if customer.tags else None,
                customer.notes,
                customer.source,
            )
        )

        row = conn.execute(
            "SELECT * FROM customers ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return {"customer": _enrich_customer(dict_row(row))}


@limiter.limit("30/minute")
@router.get("/customers/{customer_id}")
def get_customer(request: Request, customer_id: str):
    """Full customer detail with quote/invoice/payment history."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer = _enrich_customer(dict_row(row))

        # Get invoices
        invoices = dict_rows(conn.execute(
            "SELECT * FROM invoices WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,)
        ).fetchall())
        for inv in invoices:
            inv["line_items"] = json.loads(inv["line_items"]) if inv.get("line_items") else []

        # Get payments
        payments = dict_rows(conn.execute(
            "SELECT * FROM payments WHERE customer_id = ? ORDER BY payment_date DESC",
            (customer_id,)
        ).fetchall())

        # Find matching quotes from JSON files
        quotes = _find_quotes_for_customer(customer["name"], customer.get("email"))

        customer["invoices"] = invoices
        customer["payments"] = payments
        customer["quotes"] = quotes
        return {"customer": customer}


@limiter.limit("30/minute")
@router.patch("/customers/{customer_id}")
def update_customer(request: Request, customer_id: str, update: CustomerUpdate):
    """Update a customer."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Customer not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        fields = []
        values = []
        for key, val in data.items():
            if key == "tags":
                val = json.dumps(val)
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(customer_id)

        conn.execute(
            f"UPDATE customers SET {', '.join(fields)} WHERE id = ?", values
        )

        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return {"customer": _enrich_customer(dict_row(row))}


@limiter.limit("30/minute")
@router.delete("/customers/{customer_id}")
def delete_customer(request: Request, customer_id: str):
    """Delete a customer."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Customer not found")

        conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        return {"status": "deleted", "customer_id": customer_id}


@limiter.limit("30/minute")
@router.get("/customers/{customer_id}/quotes")
def get_customer_quotes(request: Request, customer_id: str):
    """All quotes for a customer (from JSON files)."""
    with get_db() as conn:
        row = conn.execute("SELECT name, email FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")

        cust = dict_row(row)
        quotes = _find_quotes_for_customer(cust["name"], cust.get("email"))
        return {"customer_id": customer_id, "quotes": quotes, "total": len(quotes)}


@limiter.limit("30/minute")
@router.get("/customers/{customer_id}/invoices")
def get_customer_invoices(request: Request, customer_id: str):
    """All invoices for a customer."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")

        invoices = dict_rows(conn.execute(
            "SELECT * FROM invoices WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,)
        ).fetchall())
        for inv in invoices:
            inv["line_items"] = json.loads(inv["line_items"]) if inv.get("line_items") else []

        return {"customer_id": customer_id, "invoices": invoices, "total": len(invoices)}


@limiter.limit("30/minute")
@router.post("/customers/import-from-quotes")
def import_customers_from_quotes(request: Request):
    """Scan all quote JSON files, extract unique customers, insert into DB."""
    if not QUOTES_DIR.exists():
        raise HTTPException(status_code=404, detail="Quotes directory not found")

    # Collect customer data from all quotes
    customer_map = {}  # key = (name, email) -> { data }

    for quote_file in QUOTES_DIR.glob("*.json"):
        if quote_file.name.startswith("_"):
            continue
        try:
            with open(quote_file) as f:
                quote = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        name = quote.get("customer_name", "").strip()
        if not name or name.lower() in ("", "customer", "unknown", "unnamed customer",
                                         "new customer", "new client", "default customer",
                                         "sample customer", "test client"):
            continue

        email = (quote.get("customer_email") or "").strip()
        phone = (quote.get("customer_phone") or "").strip()
        address = (quote.get("customer_address") or "").strip()

        key = (name.lower(), email.lower() if email else "")
        if key not in customer_map:
            customer_map[key] = {
                "name": name,
                "email": email or None,
                "phone": phone or None,
                "address": address or None,
                "quotes": [],
                "total_revenue": 0,
            }

        # Track quote info
        quote_total = quote.get("total", 0) or quote.get("subtotal", 0) or 0
        # Check proposal_totals
        if quote_total == 0:
            proposal_totals = quote.get("proposal_totals", {})
            if proposal_totals:
                quote_total = proposal_totals.get("A", 0) or proposal_totals.get("B", 0) or 0

        customer_map[key]["quotes"].append({
            "id": quote.get("id"),
            "quote_number": quote.get("quote_number"),
            "total": quote_total,
            "status": quote.get("status"),
        })
        customer_map[key]["total_revenue"] += quote_total

        # Update contact info if we have better data
        if phone and not customer_map[key]["phone"]:
            customer_map[key]["phone"] = phone
        if address and not customer_map[key]["address"]:
            customer_map[key]["address"] = address

    # Insert into database
    created = 0
    skipped = 0

    with get_db() as conn:
        for key, cust_data in customer_map.items():
            # Check if already exists
            existing = None
            if cust_data["email"]:
                existing = conn.execute(
                    "SELECT id FROM customers WHERE email = ?", (cust_data["email"],)
                ).fetchone()
            if not existing:
                existing = conn.execute(
                    "SELECT id FROM customers WHERE lower(name) = ?", (cust_data["name"].lower(),)
                ).fetchone()

            if existing:
                # Update stats
                conn.execute(
                    """UPDATE customers SET
                         total_revenue = ?, lifetime_quotes = ?,
                         phone = COALESCE(phone, ?),
                         address = COALESCE(address, ?),
                         updated_at = datetime('now')
                       WHERE id = ?""",
                    (
                        cust_data["total_revenue"],
                        len(cust_data["quotes"]),
                        cust_data["phone"],
                        cust_data["address"],
                        existing["id"],
                    )
                )
                skipped += 1
            else:
                conn.execute(
                    """INSERT INTO customers
                       (id, name, email, phone, address, type, total_revenue, lifetime_quotes, source)
                       VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, 'residential', ?, ?, 'direct')""",
                    (
                        cust_data["name"],
                        cust_data["email"],
                        cust_data["phone"],
                        cust_data["address"],
                        cust_data["total_revenue"],
                        len(cust_data["quotes"]),
                    )
                )
                created += 1

    return {
        "status": "ok",
        "created": created,
        "updated": skipped,
        "total_unique_customers": len(customer_map),
        "customers": [
            {"name": d["name"], "email": d["email"], "quotes": len(d["quotes"]), "revenue": d["total_revenue"]}
            for d in customer_map.values()
        ],
    }


@limiter.limit("30/minute")
@router.get("/pipeline")
def sales_pipeline(request: Request):
    """Sales pipeline: group quotes by status with totals."""
    if not QUOTES_DIR.exists():
        return {"pipeline": {}, "total_quotes": 0}

    pipeline = {}
    total_quotes = 0

    for quote_file in QUOTES_DIR.glob("*.json"):
        if quote_file.name.startswith("_"):
            continue
        try:
            with open(quote_file) as f:
                quote = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        total_quotes += 1
        status = quote.get("status", "unknown")

        if status not in pipeline:
            pipeline[status] = {"count": 0, "total_value": 0, "quotes": []}

        quote_total = quote.get("total", 0) or quote.get("subtotal", 0) or 0
        if quote_total == 0:
            proposal_totals = quote.get("proposal_totals", {})
            if proposal_totals:
                quote_total = proposal_totals.get("A", 0) or proposal_totals.get("B", 0) or 0

        pipeline[status]["count"] += 1
        pipeline[status]["total_value"] += quote_total
        pipeline[status]["quotes"].append({
            "id": quote.get("id"),
            "quote_number": quote.get("quote_number"),
            "customer_name": quote.get("customer_name"),
            "total": quote_total,
            "created_at": quote.get("created_at"),
        })

    # Round totals
    for status in pipeline:
        pipeline[status]["total_value"] = round(pipeline[status]["total_value"], 2)

    return {"pipeline": pipeline, "total_quotes": total_quotes}


# ── Internal helpers ─────────────────────────────────────────────────

def _find_quotes_for_customer(name: str, email: Optional[str] = None) -> list:
    """Find all quote JSON files matching a customer name or email."""
    quotes = []
    if not QUOTES_DIR.exists():
        return quotes

    for quote_file in QUOTES_DIR.glob("*.json"):
        if quote_file.name.startswith("_"):
            continue
        try:
            with open(quote_file) as f:
                quote = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        q_name = (quote.get("customer_name") or "").strip().lower()
        q_email = (quote.get("customer_email") or "").strip().lower()

        if (name and q_name == name.lower()) or (email and q_email == email.lower()):
            quote_total = quote.get("total", 0) or quote.get("subtotal", 0) or 0
            if quote_total == 0:
                proposal_totals = quote.get("proposal_totals", {})
                if proposal_totals:
                    quote_total = proposal_totals.get("A", 0) or 0

            quotes.append({
                "id": quote.get("id"),
                "quote_number": quote.get("quote_number"),
                "customer_name": quote.get("customer_name"),
                "total": quote_total,
                "status": quote.get("status"),
                "created_at": quote.get("created_at"),
                "rooms": len(quote.get("rooms") or []),
            })

    return quotes
