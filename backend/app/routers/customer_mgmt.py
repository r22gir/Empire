"""
Empire CRM — Customer management, import from quotes, sales pipeline.

Workroom leads from LeadForge, LuxeForge, and manual capture share this
customer table. Email identity is case-insensitive: a second submit updates
the same row instead of inserting another contact.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import sqlite3
from pathlib import Path

from app.db.database import get_db, dict_row, dict_rows
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix="/crm", tags=["crm"])

QUOTES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "quotes"

_CUSTOMER_TYPES = {"residential", "commercial", "designer", "contractor"}
_WORKROOM_CAPTURES = {"leadforge", "luxeforge", "manual"}
_UTM_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
_ATTRIBUTION_COLUMNS = (
    ("source_url", "TEXT"),
    ("utm_source", "TEXT"),
    ("utm_medium", "TEXT"),
    ("utm_campaign", "TEXT"),
    ("utm_content", "TEXT"),
    ("utm_term", "TEXT"),
)
_BUSINESS_ALIASES = {
    "empire workroom": "workroom",
    "workroom": "workroom",
    "woodcraft": "woodcraft",
    "wood craft": "woodcraft",
    "craftforge": "woodcraft",
    "empire": "empire",
}
_FILL_IF_BLANK = ("name", "email", "phone", "address", "company", "notes", "source", "source_url", *_UTM_FIELDS)


# ── Schemas ──────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    """ForgeCRM create. Accepts LeadForge intake names (first_name, business_unit, source_url, utm_*)."""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    company: Optional[str] = None
    type: str = "residential"
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    business: Optional[str] = None
    business_unit: Optional[str] = None
    capture: Optional[str] = None  # leadforge | luxeforge | manual
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None


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
        cust["tags"] = _tag_list(cust.get("tags"))
    return cust


def _clean(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _tag_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in raw.split(",")]
        value = parsed
    if not isinstance(value, list):
        return []
    tags = []
    seen = set()
    for tag in value:
        text = _clean(tag)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(text)
    return tags


def _normalise_business(raw: Optional[str]) -> Optional[str]:
    text = _clean(raw)
    if not text:
        return None
    return _BUSINESS_ALIASES.get(text.lower(), text.lower())


def _resolve_business(data: dict) -> str:
    explicit = _normalise_business(data.get("business") or data.get("business_unit"))
    if explicit:
        return explicit
    capture = (_clean(data.get("capture")) or "").lower()
    if capture in _WORKROOM_CAPTURES:
        return "workroom"
    return "empire"


def _resolve_name(data: dict, email: Optional[str]) -> Optional[str]:
    name = _clean(data.get("name"))
    if name:
        return name
    joined = " ".join(
        part for part in (_clean(data.get("first_name")), _clean(data.get("last_name"))) if part
    ).strip()
    if joined:
        return joined
    if email and "@" in email:
        return email.split("@", 1)[0]
    return None


def _resolve_source(data: dict) -> Optional[str]:
    source = _clean(data.get("source"))
    if source:
        return source
    capture = (_clean(data.get("capture")) or "").lower()
    if capture in _WORKROOM_CAPTURES:
        return capture
    return None


def _merge_tags(existing, incoming, business: str, capture: Optional[str]) -> list:
    tags = _tag_list(existing) + _tag_list(incoming)
    merged = []
    seen = set()
    for tag in tags:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(tag)
    if business == "workroom" and "workroom" not in seen:
        merged.append("workroom")
        seen.add("workroom")
    if capture in _WORKROOM_CAPTURES and business == "workroom" and capture not in seen:
        merged.append(capture)
    return merged


def _merge_business(existing: Optional[str], incoming: str) -> str:
    current = _normalise_business(existing) or ""
    if incoming == "workroom" and current in ("", "empire", "workroom"):
        return "workroom"
    if current in ("", "empire") and incoming:
        return incoming
    return current or incoming or "empire"


def ensure_customer_attribution_columns(conn) -> None:
    """Add source_url / utm columns and the case-insensitive email index."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(customers)")}
    for name, coltype in _ATTRIBUTION_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE customers ADD COLUMN {name} {coltype}")
    try:
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_email_ci
               ON customers(lower(email))
               WHERE email IS NOT NULL AND email != ''"""
        )
    except sqlite3.OperationalError:
        # Legacy databases can already contain duplicate emails. Keep
        # application-level upsert working even if the index cannot be built.
        pass


def _find_customer_by_email(conn, email: str):
    return conn.execute(
        """SELECT * FROM customers
           WHERE email IS NOT NULL AND trim(email) != ''
             AND lower(email) = lower(?)
           ORDER BY updated_at DESC
           LIMIT 1""",
        (email,),
    ).fetchone()


def upsert_forgecrm_customer(data: dict, conn=None) -> dict:
    """Insert or update one ForgeCRM customer.

    Email is the identity key (case-insensitive). A second submit with the
    same email returns the existing row. Source and UTM already stored on
    that row are left in place. Phone may be omitted.
    """
    if conn is not None:
        return _upsert_forgecrm_customer(conn, data)
    with get_db() as owned:
        return _upsert_forgecrm_customer(owned, data)


def _upsert_forgecrm_customer(conn, data: dict) -> dict:
    ensure_customer_attribution_columns(conn)

    email = _clean(data.get("email"))
    phone = _clean(data.get("phone"))
    business = _resolve_business(data)
    capture = (_clean(data.get("capture")) or "").lower() or None
    if capture not in _WORKROOM_CAPTURES:
        capture = None
    name = _resolve_name(data, email)
    incoming_source = _resolve_source(data)
    customer_type = (_clean(data.get("type")) or "residential").lower()
    if customer_type not in _CUSTOMER_TYPES:
        customer_type = "residential"

    existing = None
    hinted_id = _clean(data.get("customer_id"))
    if hinted_id:
        existing = conn.execute(
            "SELECT * FROM customers WHERE id = ?",
            (hinted_id,),
        ).fetchone()
    if email:
        by_email = _find_customer_by_email(conn, email)
        if by_email is not None:
            existing = by_email

    if existing:
        current = dict(existing)
        stored_business = _merge_business(current.get("business"), business)
        tag_business = business if business == "workroom" else stored_business
        updates = {
            "tags": json.dumps(_merge_tags(current.get("tags"), data.get("tags"), tag_business, capture)),
            "business": stored_business,
            "type": current.get("type") or customer_type,
        }
        incoming = {
            "name": name,
            "email": email,
            "phone": phone,
            "address": _clean(data.get("address")),
            "company": _clean(data.get("company")),
            "notes": _clean(data.get("notes")),
            "source": incoming_source,
            "source_url": _clean(data.get("source_url")),
        }
        for field in _UTM_FIELDS:
            incoming[field] = _clean(data.get(field))
        for field in _FILL_IF_BLANK:
            if _clean(current.get(field)):
                continue
            if incoming.get(field):
                updates[field] = incoming[field]
        assignments = ", ".join(f"{key} = ?" for key in updates)
        conn.execute(
            f"UPDATE customers SET {assignments}, updated_at = datetime('now') WHERE id = ?",
            [*updates.values(), current["id"]],
        )
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (current["id"],)).fetchone()
        customer = _enrich_customer(dict_row(row))
        return {
            "customer": customer,
            "upsert_outcome": "matched",
            "customer_id": customer["id"],
            "business": customer.get("business"),
            "source": customer.get("source"),
        }

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    stored_source = incoming_source or "direct"
    tags = _merge_tags([], data.get("tags"), business, capture)
    values = {
        "name": name,
        "email": email,
        "phone": phone,
        "address": _clean(data.get("address")),
        "company": _clean(data.get("company")),
        "type": customer_type,
        "tags": json.dumps(tags),
        "notes": _clean(data.get("notes")),
        "source": stored_source,
        "source_url": _clean(data.get("source_url")),
        "business": business,
        "utm_source": _clean(data.get("utm_source")),
        "utm_medium": _clean(data.get("utm_medium")),
        "utm_campaign": _clean(data.get("utm_campaign")),
        "utm_content": _clean(data.get("utm_content")),
        "utm_term": _clean(data.get("utm_term")),
    }
    columns = ", ".join(values.keys())
    placeholders = ", ".join("?" for _ in values)
    try:
        conn.execute(
            f"""INSERT INTO customers (id, {columns})
                VALUES (lower(hex(randomblob(8))), {placeholders})""",
            tuple(values.values()),
        )
    except sqlite3.IntegrityError:
        if not email:
            raise
        raced = _find_customer_by_email(conn, email)
        if raced is None:
            raise
        return _upsert_forgecrm_customer(conn, {**data, "customer_id": dict(raced)["id"]})

    row = _find_customer_by_email(conn, email) if email else conn.execute(
        "SELECT * FROM customers WHERE name = ? ORDER BY created_at DESC LIMIT 1",
        (name,),
    ).fetchone()
    customer = _enrich_customer(dict_row(row))
    return {
        "customer": customer,
        "upsert_outcome": "created",
        "customer_id": customer["id"],
        "business": customer.get("business"),
        "source": customer.get("source"),
    }


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
    """Create or update a customer. Same email (any case) is one contact."""
    result = upsert_forgecrm_customer(customer.model_dump())
    return {
        "customer": result["customer"],
        "upsert_outcome": result["upsert_outcome"],
        "customer_id": result["customer_id"],
    }


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
