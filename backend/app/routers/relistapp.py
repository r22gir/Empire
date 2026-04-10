"""
RelistApp API — Drop-ship arbitrage: source products, cross-list, track orders & profit.

Tables are prefixed ra_ and created on import. All endpoints live under /api/v1/relist/.
"""
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from app.middleware.auth_middleware import get_optional_user
from pydantic import BaseModel
from typing import Optional, List
import json
import logging
import sqlite3
from datetime import datetime, date

from app.db.database import get_db, dict_rows, dict_row, DB_PATH
from app.config.pricing_tiers import PRICING_TIERS, check_relist_within_limit, get_relist_limit

router = APIRouter(prefix="/relist", tags=["relistapp"])
log = logging.getLogger("relistapp")


def _get_tier_from_user(user: Optional[dict]) -> str:
    """Extract a valid tier from an authenticated user dict.

    Returns the user's stored tier if valid, otherwise defaults to 'lite'.
    """
    if user and user.get("id"):
        tier = user.get("tier", "lite")
        if tier in PRICING_TIERS:
            return tier
    return "lite"

# ── Table Creation ────────────────────────────────────────────────────────────

def _init_tables():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ra_source_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_platform TEXT NOT NULL,
            source_url TEXT,
            source_product_id TEXT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            source_price REAL DEFAULT 0,
            source_currency TEXT DEFAULT 'USD',
            shipping_cost REAL DEFAULT 0,
            source_images TEXT DEFAULT '[]',
            category TEXT DEFAULT '',
            brand TEXT DEFAULT '',
            condition TEXT DEFAULT 'new',
            weight_oz REAL,
            dimensions TEXT DEFAULT '',
            availability TEXT DEFAULT 'in_stock',
            last_checked TEXT,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ra_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_product_id INTEGER REFERENCES ra_source_products(id),
            platform TEXT NOT NULL,
            platform_listing_id TEXT,
            platform_url TEXT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            your_price REAL DEFAULT 0,
            markup_amount REAL DEFAULT 0,
            markup_percent REAL DEFAULT 0,
            platform_fee_percent REAL DEFAULT 0,
            estimated_profit REAL DEFAULT 0,
            images TEXT DEFAULT '[]',
            status TEXT DEFAULT 'draft',
            listed_at TEXT,
            sold_at TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            offers_received INTEGER DEFAULT 0,
            auto_relist INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ra_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER REFERENCES ra_listings(id),
            source_product_id INTEGER REFERENCES ra_source_products(id),
            platform TEXT NOT NULL,
            buyer_name TEXT DEFAULT '',
            buyer_address TEXT DEFAULT '{}',
            sale_price REAL DEFAULT 0,
            platform_fee REAL DEFAULT 0,
            source_order_id TEXT,
            source_order_cost REAL DEFAULT 0,
            source_order_status TEXT DEFAULT '',
            tracking_number TEXT,
            tracking_carrier TEXT,
            profit REAL DEFAULT 0,
            status TEXT DEFAULT 'new',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ra_price_watch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_product_id INTEGER REFERENCES ra_source_products(id),
            checked_at TEXT DEFAULT (datetime('now')),
            price REAL DEFAULT 0,
            availability TEXT DEFAULT 'in_stock',
            price_change REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ra_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            platform TEXT NOT NULL,
            total_sales REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            total_fees REAL DEFAULT 0,
            total_profit REAL DEFAULT 0,
            items_sold INTEGER DEFAULT 0,
            items_listed INTEGER DEFAULT 0,
            avg_markup_percent REAL DEFAULT 0,
            UNIQUE(date, platform)
        )
    """)

    conn.commit()
    conn.close()
    log.info("RelistApp tables initialized")

_init_tables()

# ── Helpers ───────────────────────────────────────────────────────────────────

JSON_FIELDS_SOURCE = ("source_images",)
JSON_FIELDS_LISTING = ("images",)
JSON_FIELDS_ORDER = ("buyer_address",)


def _parse_json_fields(row: dict, fields: tuple) -> dict:
    for f in fields:
        if f in row and isinstance(row[f], str):
            try:
                row[f] = json.loads(row[f])
            except (json.JSONDecodeError, TypeError):
                row[f] = [] if f != "buyer_address" else {}
    return row


def _calc_profit(your_price: float, source_price: float, shipping: float, fee_pct: float) -> dict:
    markup_amount = your_price - source_price - shipping
    markup_percent = ((your_price - source_price - shipping) / (source_price + shipping) * 100) if (source_price + shipping) > 0 else 0
    platform_fee = your_price * (fee_pct / 100)
    estimated_profit = your_price - source_price - shipping - platform_fee
    return {
        "markup_amount": round(markup_amount, 2),
        "markup_percent": round(markup_percent, 2),
        "estimated_profit": round(estimated_profit, 2),
    }


# ── Pydantic Models ──────────────────────────────────────────────────────────

class SourceProductCreate(BaseModel):
    source_platform: str
    source_url: Optional[str] = None
    source_product_id: Optional[str] = None
    title: str
    description: str = ""
    source_price: float = 0
    source_currency: str = "USD"
    shipping_cost: float = 0
    source_images: List[str] = []
    category: str = ""
    brand: str = ""
    condition: str = "new"
    weight_oz: Optional[float] = None
    dimensions: str = ""
    availability: str = "in_stock"
    notes: str = ""


class SourceProductUpdate(BaseModel):
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    source_product_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source_price: Optional[float] = None
    source_currency: Optional[str] = None
    shipping_cost: Optional[float] = None
    source_images: Optional[List[str]] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    condition: Optional[str] = None
    weight_oz: Optional[float] = None
    dimensions: Optional[str] = None
    availability: Optional[str] = None
    notes: Optional[str] = None


class ImportUrlRequest(BaseModel):
    url: str
    source_platform: Optional[str] = None


class ListingCreate(BaseModel):
    source_product_id: int
    platform: str
    platform_listing_id: Optional[str] = None
    platform_url: Optional[str] = None
    title: str
    description: str = ""
    your_price: float = 0
    platform_fee_percent: float = 0
    images: List[str] = []
    auto_relist: bool = False


class ListingUpdate(BaseModel):
    platform_listing_id: Optional[str] = None
    platform_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    your_price: Optional[float] = None
    platform_fee_percent: Optional[float] = None
    images: Optional[List[str]] = None
    auto_relist: Optional[bool] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    offers_received: Optional[int] = None


class StatusUpdate(BaseModel):
    status: str


class CrossListRequest(BaseModel):
    target_platform: str
    your_price: Optional[float] = None
    platform_fee_percent: float = 0


class SourceOrderedUpdate(BaseModel):
    source_order_id: str
    source_order_cost: float


class TrackingUpdate(BaseModel):
    tracking_number: str
    tracking_carrier: str = ""


# ── Source Products ───────────────────────────────────────────────────────────

@router.get("/sources")
async def list_sources(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    with get_db() as db:
        where, params = [], []
        if platform:
            where.append("source_platform = ?")
            params.append(platform)
        if category:
            where.append("category = ?")
            params.append(category)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params += [limit, offset]
        rows = dict_rows(db.execute(
            f"SELECT * FROM ra_source_products {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall())
        total = db.execute(f"SELECT COUNT(*) FROM ra_source_products {clause}", params[:-2]).fetchone()[0]
    return {"items": [_parse_json_fields(r, JSON_FIELDS_SOURCE) for r in rows], "total": total}


@router.post("/sources", status_code=201)
async def create_source(req: SourceProductCreate):
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO ra_source_products
               (source_platform, source_url, source_product_id, title, description,
                source_price, source_currency, shipping_cost, source_images,
                category, brand, condition, weight_oz, dimensions, availability, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (req.source_platform, req.source_url, req.source_product_id, req.title,
             req.description, req.source_price, req.source_currency, req.shipping_cost,
             json.dumps(req.source_images), req.category, req.brand, req.condition,
             req.weight_oz, req.dimensions, req.availability, req.notes),
        )
    log.info(f"Source product #{cur.lastrowid} created: {req.title}")
    return {"id": cur.lastrowid, "title": req.title, "source_platform": req.source_platform}


@router.post("/sources/import-url")
async def import_source_url(req: ImportUrlRequest):
    """Stub: accept a product URL and create a source product (scraping not yet implemented)."""
    platform = req.source_platform or "unknown"
    url = req.url
    # Detect platform from URL
    if not req.source_platform:
        if "amazon" in url.lower():
            platform = "amazon"
        elif "walmart" in url.lower():
            platform = "walmart"
        elif "aliexpress" in url.lower():
            platform = "aliexpress"
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO ra_source_products
               (source_platform, source_url, title, description, availability)
               VALUES (?,?,?,?,?)""",
            (platform, url, f"Imported from {platform}", "Pending scrape — update details manually", "unknown"),
        )
    return {
        "id": cur.lastrowid,
        "source_platform": platform,
        "source_url": url,
        "message": "Product stub created. Scraping not yet connected — update details manually.",
    }


@router.get("/sources/{source_id}")
async def get_source(source_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM ra_source_products WHERE id = ?", (source_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Source product not found")
    return _parse_json_fields(dict_row(row), JSON_FIELDS_SOURCE)


@router.put("/sources/{source_id}")
async def update_source(source_id: int, req: SourceProductUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    if "source_images" in updates:
        updates["source_images"] = json.dumps(updates["source_images"])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [source_id]
    with get_db() as db:
        affected = db.execute(
            f"UPDATE ra_source_products SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        ).rowcount
    if not affected:
        raise HTTPException(404, "Source product not found")
    return {"id": source_id, "updated": True}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int):
    with get_db() as db:
        affected = db.execute("DELETE FROM ra_source_products WHERE id = ?", (source_id,)).rowcount
    if not affected:
        raise HTTPException(404, "Source product not found")
    return {"id": source_id, "deleted": True}


@router.post("/sources/{source_id}/check-price")
async def check_price(source_id: int):
    """Stub: re-check the source price. Logs a price-watch entry with current stored price."""
    with get_db() as db:
        row = db.execute(
            "SELECT id, source_price, availability FROM ra_source_products WHERE id = ?",
            (source_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Source product not found")
        src = dict_row(row)
        # In a real implementation we'd scrape the source URL here.
        # For now, record the current known price.
        last_watch = db.execute(
            "SELECT price FROM ra_price_watch WHERE source_product_id = ? ORDER BY checked_at DESC LIMIT 1",
            (source_id,),
        ).fetchone()
        prev_price = dict_row(last_watch)["price"] if last_watch else src["source_price"]
        change = round(src["source_price"] - prev_price, 2)
        db.execute(
            "INSERT INTO ra_price_watch (source_product_id, price, availability, price_change) VALUES (?,?,?,?)",
            (source_id, src["source_price"], src["availability"], change),
        )
        db.execute(
            "UPDATE ra_source_products SET last_checked = datetime('now') WHERE id = ?",
            (source_id,),
        )
    return {
        "source_product_id": source_id,
        "price": src["source_price"],
        "price_change": change,
        "availability": src["availability"],
        "message": "Price check recorded. Live scraping not yet connected.",
    }



# ── Usage & Plans ────────────────────────────────────────────────────────────

@router.get("/usage")
async def get_usage(tier: str = "lite", user: dict = Depends(get_optional_user)):
    """Get current usage vs limits for RelistApp features.

    Tier is read from the authenticated user's stored subscription.
    The tier query param is used ONLY when no auth is present (dev/unauthenticated fallback).
    """
    stored_tier = _get_tier_from_user(user)
    if stored_tier != "lite" or not user:
        tier = stored_tier
    else:
        tier = tier.lower() if tier else "lite"
        if tier not in PRICING_TIERS:
            tier = "lite"

    with get_db() as db:
        source_products = db.execute("SELECT COUNT(*) FROM ra_source_products").fetchone()[0]
        listings = db.execute("SELECT COUNT(*) FROM ra_listings").fetchone()[0]
        listings_active = db.execute("SELECT COUNT(*) FROM ra_listings WHERE status = 'active'").fetchone()[0]
        orders_total = db.execute("SELECT COUNT(*) FROM ra_orders").fetchone()[0]
        orders_completed = db.execute("SELECT COUNT(*) FROM ra_orders WHERE status = 'completed'").fetchone()[0]

    tier_config = PRICING_TIERS[tier].get("relist", {})

    return {
        "tier": tier,
        "tier_name": PRICING_TIERS[tier]["name"],
        "price_monthly": PRICING_TIERS[tier]["price_monthly"],
        "usage": {
            "source_products": {
                "used": source_products,
                **check_relist_within_limit(tier, "source_products_limit", source_products),
            },
            "listings": {
                "used": listings,
                **check_relist_within_limit(tier, "listings_limit", listings),
            },
            "active_listings": {
                "used": listings_active,
                "limit": get_relist_limit(tier, "listings_limit"),
            },
            "orders": {
                "used": orders_total,
                **check_relist_within_limit(tier, "orders_limit", orders_total),
            },
            "completed_orders": {
                "used": orders_completed,
            },
        },
        "limits": {
            "ai_analysis_limit": get_relist_limit(tier, "ai_analysis_limit"),
            "crosslist_limit": get_relist_limit(tier, "crosslist_limit"),
            "ai_deal_finder": tier_config.get("ai_deal_finder", False),
            "auto_relist": tier_config.get("auto_relist", False),
            "price_alerts": get_relist_limit(tier, "price_alerts"),
        },
        "upgrade_available": tier in ("lite", "pro"),
        "upgrade_to": {
            "lite": "pro",
            "pro": "empire",
            "empire": None,
            "founder": None,
        }.get(tier),
    }


@router.get("/subscription/me")
async def get_my_subscription(user: dict = Depends(get_optional_user)):
    """Return the stored subscription state for the authenticated user.

    Uses JWT Bearer token from Authorization header. Falls back to 'lite'/unauthenticated
    only when no valid token is present.
    """
    if not user or not user.get("id"):
        return {
            "tier": "lite",
            "authenticated": False,
            "stripe_subscription_id": None,
            "stripe_current_period_end": None,
        }

    return {
        "tier": user.get("tier", "lite"),
        "authenticated": True,
        "user_id": user["id"],
        "stripe_subscription_id": user.get("stripe_subscription_id"),
        "stripe_current_period_end": user.get("stripe_current_period_end"),
    }


@router.get("/whoami")
async def relist_whoami(user: dict = Depends(get_optional_user)):
    """Return the authenticated RelistApp user.

    If a valid JWT Bearer token is present, returns that user's info.
    Otherwise returns the founder user (dev fallback). The 'authenticated' flag
    indicates whether a real JWT was validated.
    """
    if user and user.get("id"):
        return {
            "user_id": user["id"],
            "tier": user.get("tier", "lite"),
            "authenticated": True,
        }

    with get_db() as db:
        row = db.execute(
            "SELECT id, tier FROM access_users WHERE role = 'founder' AND is_active = 1 LIMIT 1"
        ).fetchone()
        if row:
            d = dict_row(row)
            return {"user_id": d["id"], "tier": d["tier"], "authenticated": False}
        row2 = db.execute(
            "SELECT id, tier FROM access_users WHERE is_active = 1 ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if row2:
            d = dict_row(row2)
            return {"user_id": d["id"], "tier": d["tier"], "authenticated": False}
        return {"user_id": None, "tier": "lite", "authenticated": False}

# ── Listings ──────────────────────────────────────────────────────────────────

@router.get("/listings")
async def list_listings(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    source_product_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
):
    with get_db() as db:
        where, params = [], []
        if platform:
            where.append("l.platform = ?")
            params.append(platform)
        if status:
            where.append("l.status = ?")
            params.append(status)
        if source_product_id:
            where.append("l.source_product_id = ?")
            params.append(source_product_id)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params += [limit, offset]
        rows = dict_rows(db.execute(
            f"""SELECT l.*, sp.title AS source_title, sp.source_price, sp.source_platform
                FROM ra_listings l
                LEFT JOIN ra_source_products sp ON l.source_product_id = sp.id
                {clause} ORDER BY l.created_at DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall())
        total = db.execute(
            f"SELECT COUNT(*) FROM ra_listings l {clause}", params[:-2],
        ).fetchone()[0]
    return {"items": [_parse_json_fields(r, JSON_FIELDS_LISTING) for r in rows], "total": total}


@router.post("/listings", status_code=201)
async def create_listing(req: ListingCreate):
    with get_db() as db:
        # Fetch source to calc profit
        src = db.execute(
            "SELECT source_price, shipping_cost FROM ra_source_products WHERE id = ?",
            (req.source_product_id,),
        ).fetchone()
        if not src:
            raise HTTPException(404, "Source product not found")
        src = dict_row(src)
        profit = _calc_profit(req.your_price, src["source_price"], src["shipping_cost"], req.platform_fee_percent)

        cur = db.execute(
            """INSERT INTO ra_listings
               (source_product_id, platform, platform_listing_id, platform_url,
                title, description, your_price, markup_amount, markup_percent,
                platform_fee_percent, estimated_profit, images, auto_relist)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (req.source_product_id, req.platform, req.platform_listing_id, req.platform_url,
             req.title, req.description, req.your_price,
             profit["markup_amount"], profit["markup_percent"],
             req.platform_fee_percent, profit["estimated_profit"],
             json.dumps(req.images), int(req.auto_relist)),
        )
    return {"id": cur.lastrowid, "title": req.title, "platform": req.platform, **profit}


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: int):
    with get_db() as db:
        row = db.execute(
            """SELECT l.*, sp.title AS source_title, sp.source_price, sp.source_platform, sp.source_url
               FROM ra_listings l
               LEFT JOIN ra_source_products sp ON l.source_product_id = sp.id
               WHERE l.id = ?""",
            (listing_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Listing not found")
    return _parse_json_fields(dict_row(row), JSON_FIELDS_LISTING)


@router.put("/listings/{listing_id}")
async def update_listing(listing_id: int, req: ListingUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    if "images" in updates:
        updates["images"] = json.dumps(updates["images"])
    if "auto_relist" in updates:
        updates["auto_relist"] = int(updates["auto_relist"])

    # Recalc profit if price or fee changed
    if "your_price" in updates or "platform_fee_percent" in updates:
        with get_db() as db:
            row = db.execute(
                """SELECT l.your_price, l.platform_fee_percent, sp.source_price, sp.shipping_cost
                   FROM ra_listings l
                   LEFT JOIN ra_source_products sp ON l.source_product_id = sp.id
                   WHERE l.id = ?""",
                (listing_id,),
            ).fetchone()
            if row:
                cur = dict_row(row)
                price = updates.get("your_price", cur["your_price"])
                fee = updates.get("platform_fee_percent", cur["platform_fee_percent"])
                profit = _calc_profit(price, cur["source_price"] or 0, cur["shipping_cost"] or 0, fee)
                updates["markup_amount"] = profit["markup_amount"]
                updates["markup_percent"] = profit["markup_percent"]
                updates["estimated_profit"] = profit["estimated_profit"]

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [listing_id]
    with get_db() as db:
        affected = db.execute(
            f"UPDATE ra_listings SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        ).rowcount
    if not affected:
        raise HTTPException(404, "Listing not found")
    return {"id": listing_id, "updated": True}


@router.patch("/listings/{listing_id}/status")
async def update_listing_status(listing_id: int, req: StatusUpdate):
    valid = ("draft", "listed", "active", "sold", "expired", "removed", "out_of_stock")
    if req.status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid)}")
    extras = ""
    params: list = [req.status]
    if req.status == "active":
        extras = ", listed_at = datetime('now')"
    elif req.status == "sold":
        extras = ", sold_at = datetime('now')"
    params.append(listing_id)
    with get_db() as db:
        affected = db.execute(
            f"UPDATE ra_listings SET status = ?{extras}, updated_at = datetime('now') WHERE id = ?",
            params,
        ).rowcount
    if not affected:
        raise HTTPException(404, "Listing not found")
    return {"id": listing_id, "status": req.status}


@router.post("/listings/{listing_id}/cross-list")
async def cross_list(listing_id: int, req: CrossListRequest):
    """Clone a listing to a different platform."""
    with get_db() as db:
        row = db.execute("SELECT * FROM ra_listings WHERE id = ?", (listing_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Listing not found")
        orig = dict_row(row)
        price = req.your_price if req.your_price is not None else orig["your_price"]

        src = db.execute(
            "SELECT source_price, shipping_cost FROM ra_source_products WHERE id = ?",
            (orig["source_product_id"],),
        ).fetchone()
        src_d = dict_row(src) if src else {"source_price": 0, "shipping_cost": 0}
        profit = _calc_profit(price, src_d["source_price"], src_d["shipping_cost"], req.platform_fee_percent)

        cur = db.execute(
            """INSERT INTO ra_listings
               (source_product_id, platform, title, description, your_price,
                markup_amount, markup_percent, platform_fee_percent, estimated_profit,
                images, auto_relist)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (orig["source_product_id"], req.target_platform, orig["title"],
             orig["description"], price,
             profit["markup_amount"], profit["markup_percent"],
             req.platform_fee_percent, profit["estimated_profit"],
             orig["images"], orig["auto_relist"]),
        )
    return {"id": cur.lastrowid, "platform": req.target_platform, "cloned_from": listing_id, **profit}


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders")
async def list_orders(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    with get_db() as db:
        where, params = [], []
        if status:
            where.append("o.status = ?")
            params.append(status)
        if platform:
            where.append("o.platform = ?")
            params.append(platform)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params += [limit, offset]
        rows = dict_rows(db.execute(
            f"""SELECT o.*, l.title AS listing_title, l.platform AS listing_platform
                FROM ra_orders o
                LEFT JOIN ra_listings l ON o.listing_id = l.id
                {clause} ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall())
        total = db.execute(
            f"SELECT COUNT(*) FROM ra_orders o {clause}", params[:-2],
        ).fetchone()[0]
    return {"items": [_parse_json_fields(r, JSON_FIELDS_ORDER) for r in rows], "total": total}


@router.get("/orders/{order_id}")
async def get_order(order_id: int):
    with get_db() as db:
        row = db.execute(
            """SELECT o.*, l.title AS listing_title, l.your_price,
                      sp.title AS source_title, sp.source_price, sp.source_platform
               FROM ra_orders o
               LEFT JOIN ra_listings l ON o.listing_id = l.id
               LEFT JOIN ra_source_products sp ON o.source_product_id = sp.id
               WHERE o.id = ?""",
            (order_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Order not found")
    return _parse_json_fields(dict_row(row), JSON_FIELDS_ORDER)


@router.patch("/orders/{order_id}/source-ordered")
async def mark_source_ordered(order_id: int, req: SourceOrderedUpdate):
    with get_db() as db:
        affected = db.execute(
            """UPDATE ra_orders SET
               source_order_id = ?, source_order_cost = ?, source_order_status = 'ordered',
               status = 'source_ordered', updated_at = datetime('now')
               WHERE id = ?""",
            (req.source_order_id, req.source_order_cost, order_id),
        ).rowcount
    if not affected:
        raise HTTPException(404, "Order not found")
    return {"id": order_id, "status": "source_ordered", "source_order_id": req.source_order_id}


@router.patch("/orders/{order_id}/tracking")
async def update_tracking(order_id: int, req: TrackingUpdate):
    with get_db() as db:
        affected = db.execute(
            """UPDATE ra_orders SET
               tracking_number = ?, tracking_carrier = ?, status = 'shipped',
               updated_at = datetime('now')
               WHERE id = ?""",
            (req.tracking_number, req.tracking_carrier, order_id),
        ).rowcount
    if not affected:
        raise HTTPException(404, "Order not found")
    return {"id": order_id, "status": "shipped", "tracking_number": req.tracking_number}


@router.patch("/orders/{order_id}/complete")
async def complete_order(order_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT sale_price, platform_fee, source_order_cost FROM ra_orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Order not found")
        o = dict_row(row)
        profit = round((o["sale_price"] or 0) - (o["platform_fee"] or 0) - (o["source_order_cost"] or 0), 2)
        db.execute(
            """UPDATE ra_orders SET status = 'completed', profit = ?,
               updated_at = datetime('now') WHERE id = ?""",
            (profit, order_id),
        )
    return {"id": order_id, "status": "completed", "profit": profit}


# ── Price Watch ───────────────────────────────────────────────────────────────

@router.get("/price-watch")
async def list_price_watch(
    source_product_id: Optional[int] = None,
    limit: int = 100,
):
    with get_db() as db:
        if source_product_id:
            rows = dict_rows(db.execute(
                """SELECT pw.*, sp.title FROM ra_price_watch pw
                   LEFT JOIN ra_source_products sp ON pw.source_product_id = sp.id
                   WHERE pw.source_product_id = ? ORDER BY pw.checked_at DESC LIMIT ?""",
                (source_product_id, limit),
            ).fetchall())
        else:
            rows = dict_rows(db.execute(
                """SELECT pw.*, sp.title FROM ra_price_watch pw
                   LEFT JOIN ra_source_products sp ON pw.source_product_id = sp.id
                   ORDER BY pw.checked_at DESC LIMIT ?""",
                (limit,),
            ).fetchall())
    return {"items": rows}


@router.get("/price-watch/alerts")
async def price_watch_alerts(threshold: float = 0.0):
    """Get price-watch entries where the price changed (optionally above a threshold)."""
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT pw.*, sp.title, sp.source_url
               FROM ra_price_watch pw
               LEFT JOIN ra_source_products sp ON pw.source_product_id = sp.id
               WHERE ABS(pw.price_change) > ?
               ORDER BY pw.checked_at DESC LIMIT 100""",
            (threshold,),
        ).fetchall())
    return {"items": rows, "threshold": threshold}


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics/dashboard")
async def analytics_dashboard():
    with get_db() as db:
        sources = db.execute("SELECT COUNT(*) FROM ra_source_products").fetchone()[0]
        listings_total = db.execute("SELECT COUNT(*) FROM ra_listings").fetchone()[0]
        listings_active = db.execute("SELECT COUNT(*) FROM ra_listings WHERE status = 'active'").fetchone()[0]
        listings_sold = db.execute("SELECT COUNT(*) FROM ra_listings WHERE status = 'sold'").fetchone()[0]
        orders_total = db.execute("SELECT COUNT(*) FROM ra_orders").fetchone()[0]
        orders_pending = db.execute("SELECT COUNT(*) FROM ra_orders WHERE status NOT IN ('completed','refunded')").fetchone()[0]
        total_revenue = db.execute("SELECT COALESCE(SUM(sale_price), 0) FROM ra_orders WHERE status = 'completed'").fetchone()[0]
        total_profit = db.execute("SELECT COALESCE(SUM(profit), 0) FROM ra_orders WHERE status = 'completed'").fetchone()[0]
        total_cost = db.execute("SELECT COALESCE(SUM(source_order_cost), 0) FROM ra_orders WHERE status = 'completed'").fetchone()[0]
        total_fees = db.execute("SELECT COALESCE(SUM(platform_fee), 0) FROM ra_orders WHERE status = 'completed'").fetchone()[0]
        avg_markup = db.execute("SELECT COALESCE(AVG(markup_percent), 0) FROM ra_listings WHERE status = 'sold'").fetchone()[0]
    return {
        "source_products": sources,
        "listings": {"total": listings_total, "active": listings_active, "sold": listings_sold},
        "orders": {"total": orders_total, "pending": orders_pending},
        "financials": {
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "total_fees": round(total_fees, 2),
            "total_profit": round(total_profit, 2),
            "avg_markup_percent": round(avg_markup, 2),
        },
    }


@router.get("/analytics/by-platform")
async def analytics_by_platform():
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT platform,
                      COUNT(*) AS total_listings,
                      SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) AS sold,
                      SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
                      COALESCE(AVG(CASE WHEN status = 'sold' THEN markup_percent END), 0) AS avg_markup
               FROM ra_listings GROUP BY platform""",
        ).fetchall())
        # Add order financials per platform
        for r in rows:
            fin = db.execute(
                """SELECT COALESCE(SUM(sale_price), 0) AS revenue,
                          COALESCE(SUM(profit), 0) AS profit,
                          COUNT(*) AS orders
                   FROM ra_orders WHERE platform = ? AND status = 'completed'""",
                (r["platform"],),
            ).fetchone()
            if fin:
                f = dict_row(fin)
                r["revenue"] = round(f["revenue"], 2)
                r["profit"] = round(f["profit"], 2)
                r["completed_orders"] = f["orders"]
    return {"platforms": rows}


@router.get("/analytics/by-product")
async def analytics_by_product(limit: int = 20):
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT sp.id, sp.title, sp.source_platform, sp.source_price,
                      COUNT(DISTINCT l.id) AS listing_count,
                      SUM(CASE WHEN l.status = 'sold' THEN 1 ELSE 0 END) AS times_sold,
                      COALESCE(SUM(o.profit), 0) AS total_profit
               FROM ra_source_products sp
               LEFT JOIN ra_listings l ON sp.id = l.source_product_id
               LEFT JOIN ra_orders o ON sp.id = o.source_product_id AND o.status = 'completed'
               GROUP BY sp.id
               ORDER BY total_profit DESC
               LIMIT ?""",
            (limit,),
        ).fetchall())
    return {"products": rows}


@router.get("/analytics/trends")
async def analytics_trends(days: int = 30):
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT date(created_at) AS day,
                      COUNT(*) AS orders,
                      COALESCE(SUM(sale_price), 0) AS revenue,
                      COALESCE(SUM(profit), 0) AS profit
               FROM ra_orders
               WHERE created_at >= date('now', ?)
               GROUP BY date(created_at)
               ORDER BY day""",
            (f"-{days} days",),
        ).fetchall())
    return {"days": days, "trends": rows}


@router.get("/analytics/best-sellers")
async def analytics_best_sellers(limit: int = 10):
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT sp.id, sp.title, sp.source_platform, sp.source_price,
                      COUNT(o.id) AS times_sold,
                      COALESCE(SUM(o.profit), 0) AS total_profit,
                      COALESCE(AVG(o.profit), 0) AS avg_profit
               FROM ra_source_products sp
               JOIN ra_orders o ON sp.id = o.source_product_id AND o.status = 'completed'
               GROUP BY sp.id
               ORDER BY times_sold DESC
               LIMIT ?""",
            (limit,),
        ).fetchall())
    return {"best_sellers": rows}


# ── URL Import with AI Extraction ─────────────────────────────────────────────

class UrlImportRequest(BaseModel):
    url: str
    source_platform: Optional[str] = None


class ProductExtractedData(BaseModel):
    title: str
    description: str = ""
    price: float = 0
    shipping_cost: float = 0
    images: List[str] = []
    brand: str = ""
    category: str = ""
    condition: str = "new"
    upc: str = ""
    model: str = ""
    availability: str = "in_stock"
    source_name: str = "Unknown"


async def _extract_product_from_url(url: str, platform: str) -> ProductExtractedData:
    """Extract product data from a URL using AI analysis of the page content."""
    import httpx
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")

        title = ""
        price = 0.0
        shipping = 0.0
        images = []
        brand = ""
        description = ""
        availability = "in_stock"

        if platform == "amazon":
            title = soup.select_one("#productTitle")
            if title:
                title = title.get_text(strip=True)
            price_elem = soup.select_one(".a-price .a-offscreen")
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass
            ship_elem = soup.select_one("#deliveryBlockInner .a-color-secondary")
            if ship_elem and "free" in ship_elem.get_text().lower():
                shipping = 0.0
            img_elems = soup.select("#altImages img, #imgTagWrapperId img")
            images = [img.get("src", "") for img in img_elems[:6] if img.get("src")]
            brand_elem = soup.select_one("#bylineInfoBrand, #brand")
            if brand_elem:
                brand = brand_elem.get_text(strip=True)
            avail_elem = soup.select_one("#availability span")
            if avail_elem:
                avail_text = avail_elem.get_text(strip=True).lower()
                if "out of stock" in avail_text or "unavailable" in avail_text:
                    availability = "out_of_stock"
                elif "limited" in avail_text:
                    availability = "limited"

        elif platform == "walmart":
            title = soup.select_one("h1[itemprop='name']")
            if not title:
                title = soup.select_one("h1")
            if title:
                title = title.get_text(strip=True)
            price_elem = soup.select_one("[itemprop='price']")
            if price_elem:
                price_text = price_elem.get("content", price_elem.get_text(strip=True)).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass
            img_elem = soup.select_one("[itemprop='image']")
            if img_elem:
                images = [img_elem.get("src", "")]
            avail_elem = soup.select_one("[itemprop='availability']")
            if avail_elem and "out" in avail_elem.get("content", "").lower():
                availability = "out_of_stock"

        elif platform == "aliexpress":
            title = soup.select_one("h1.product-title-text")
            if title:
                title = title.get_text(strip=True)
            price_elem = soup.select_one(".product-price-value")
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass
            avail_elem = soup.select_one(".product-status")
            if avail_elem and "out of stock" in avail_elem.get_text().lower():
                availability = "out_of_stock"

        else:
            title = soup.select_one("h1")
            if title:
                title = title.get_text(strip=True)
            price_elem = soup.select_one("[itemprop='price'], .price, #priceblock")
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass
            for img in soup.select("img[src]")[:6]:
                src = img.get("src", "")
                if src and not src.startswith("data:"):
                    images.append(src)

        return ProductExtractedData(
            title=title or f"Product from {platform}",
            description=description,
            price=price,
            shipping_cost=shipping,
            images=images,
            brand=brand,
            availability=availability,
            source_name=platform.title(),
        )

    except Exception as e:
        log.warning(f"Failed to extract from {url}: {e}")
        return ProductExtractedData(title=f"Product from {platform}", source_name=platform.title())


def _estimate_market_value(title: str, category: str, source_price: float) -> dict:
    """Estimate market resale value using AI analysis of title and category."""
    title_lower = title.lower()

    default_multipliers = {
        "electronics": 2.2, "headphones": 1.8, "speaker": 1.9, "camera": 2.1,
        "phone": 1.6, "tablet": 1.7, "laptop": 1.5, "computer": 1.5,
        "clothing": 2.5, "shoes": 2.3, "jewelry": 3.0, "watch": 2.8,
        "furniture": 2.0, "home": 2.2, "kitchen": 2.1, "appliance": 1.8,
        "toys": 2.4, "games": 2.2, "sports": 2.3, "outdoor": 2.1,
        "beauty": 2.6, "health": 2.4, "books": 3.5, "media": 2.8,
    }

    multiplier = 2.0
    for cat, mult in default_multipliers.items():
        if cat in title_lower or cat in category.lower():
            multiplier = mult
            break

    market_price = round(source_price * multiplier, 2)
    fees = round(market_price * 0.13, 2)
    shipping_estimate = 8.50
    profit = round(market_price - source_price - shipping_estimate - fees, 2)
    roi = round((profit / (source_price + shipping_estimate)) * 100, 1) if (source_price + shipping_estimate) > 0 else 0

    return {
        "market_price": market_price,
        "fees_estimate": fees,
        "shipping_estimate": shipping_estimate,
        "estimated_profit": profit,
        "roi_percent": roi,
    }


def _score_deal(market_price: float, source_price: float, shipping: float, fees: float) -> dict:
    """Score a deal opportunity. Returns score 0-100 and label."""
    profit = market_price - source_price - shipping - fees
    if profit <= 0:
        return {"score": 0, "label": "weak", "reason": f"Negative profit ${profit:.2f}"}

    cost = source_price + shipping
    roi = (profit / cost) * 100 if cost > 0 else 0

    score = min(100, int(roi / 2 + profit / 5))
    label = "strong" if score >= 70 else "medium" if score >= 40 else "weak"

    reasons = []
    if roi >= 100:
        reasons.append(f"Excellent ROI {roi:.0f}%")
    elif roi >= 50:
        reasons.append(f"Good ROI {roi:.0f}%")
    elif roi >= 20:
        reasons.append(f"Modest ROI {roi:.0f}%")
    else:
        reasons.append(f"Low ROI {roi:.0f}%")

    if profit >= 50:
        reasons.append(f"High margin ${profit:.2f}")
    elif profit >= 20:
        reasons.append(f"Decent margin ${profit:.2f}")
    else:
        reasons.append(f"Thin margin ${profit:.2f}")

    if score >= 70:
        reasons.append("Recommended deal")
    elif score >= 40:
        reasons.append("Consider carefully")
    else:
        reasons.append("Marginal opportunity")

    return {
        "score": score,
        "label": label,
        "reason": "; ".join(reasons),
        "profit": round(profit, 2),
        "roi": round(roi, 1),
    }


@router.post("/sources/import-full", status_code=201)
async def import_url_full(req: UrlImportRequest):
    """Import a product URL with full AI-powered data extraction.

    1. Detects platform from URL
    2. Fetches and parses the page
    3. Extracts title, price, images, brand, etc.
    4. Estimates market value and deal score
    5. Saves to database as source product
    """
    platform = req.source_platform or "unknown"
    url = req.url

    if not req.source_platform:
        if "amazon" in url.lower():
            platform = "amazon"
        elif "walmart" in url.lower():
            platform = "walmart"
        elif "aliexpress" in url.lower():
            platform = "aliexpress"
        elif "ebay" in url.lower():
            platform = "ebay"
        elif "costco" in url.lower():
            platform = "costco"
        elif "target" in url.lower():
            platform = "target"
        elif "bestbuy" in url.lower():
            platform = "bestbuy"

    try:
        extracted = await _extract_product_from_url(url, platform)
    except Exception as e:
        log.warning(f"Extraction failed, using minimal data: {e}")
        extracted = ProductExtractedData(
            title=f"Product from {platform}",
            source_name=platform.title(),
        )

    market = _estimate_market_value(extracted.title, extracted.category, extracted.price)
    deal = _score_deal(market["market_price"], extracted.price, extracted.shipping_cost, market["fees_estimate"])

    with get_db() as db:
        cur = db.execute(
            """INSERT INTO ra_source_products
               (source_platform, source_url, title, description, source_price, shipping_cost,
                source_images, category, brand, condition, availability, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (platform, url, extracted.title, extracted.description, extracted.price,
             extracted.shipping_cost, json.dumps(extracted.images), extracted.category,
             extracted.brand, extracted.condition, extracted.availability,
             json.dumps({"deal_score": deal, "market_estimate": market})),
        )
        source_id = cur.lastrowid

    return {
        "id": source_id,
        "source_platform": platform,
        "source_url": url,
        "title": extracted.title,
        "price": extracted.price,
        "shipping_cost": extracted.shipping_cost,
        "images": extracted.images[:4],
        "brand": extracted.brand,
        "market_estimate": market,
        "deal": {**deal, "market_price": market["market_price"]},
        "saved": True,
    }


# ── AI Deal Finder ──────────────────────────────────────────────────────────────

@router.get("/deals")
async def get_deals(
    min_score: int = 0,
    platform: Optional[str] = None,
    sort_by: str = "score",
    limit: int = 50,
):
    """Get all source products scored and ranked by deal opportunity.

    Returns products with:
    - Deal score (0-100)
    - Label (strong/medium/weak)
    - Reason explanation
    - Market estimates
    - ROI and profit estimates
    """
    with get_db() as db:
        where = ["source_price > 0"]
        params = []
        if platform:
            where.append("source_platform = ?")
            params.append(platform)
        if min_score > 0:
            where.append("source_price IS NOT NULL")
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params.append(limit)

        rows = dict_rows(db.execute(
            f"""SELECT * FROM ra_source_products
                {clause} ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall())

    deals = []
    for row in rows:
        row = _parse_json_fields(row, JSON_FIELDS_SOURCE)
        notes = {}
        try:
            if row.get("notes"):
                notes = json.loads(row["notes"]) if isinstance(row["notes"], str) else row["notes"]
        except (json.JSONDecodeError, TypeError):
            pass

        market = _estimate_market_value(row["title"], row.get("category", ""), row["source_price"])
        deal = _score_deal(market["market_price"], row["source_price"], row.get("shipping_cost", 0), market["fees_estimate"])

        deals.append({
            "id": row["id"],
            "title": row["title"],
            "source_platform": row["source_platform"],
            "source_url": row.get("source_url"),
            "source_price": row["source_price"],
            "shipping_cost": row.get("shipping_cost", 0),
            "images": row.get("source_images", [])[:3],
            "brand": row.get("brand", ""),
            "availability": row.get("availability", "in_stock"),
            "market_estimate": market,
            "deal_score": deal["score"],
            "deal_label": deal["label"],
            "deal_reason": deal["reason"],
            "estimated_profit": market["estimated_profit"],
            "roi_percent": market["roi_percent"],
            "created_at": row["created_at"],
        })

    if sort_by == "score":
        deals.sort(key=lambda x: x["deal_score"], reverse=True)
    elif sort_by == "profit":
        deals.sort(key=lambda x: x["estimated_profit"], reverse=True)
    elif sort_by == "roi":
        deals.sort(key=lambda x: x["roi_percent"], reverse=True)
    elif sort_by == "price":
        deals.sort(key=lambda x: x["source_price"])

    deals = [d for d in deals if d["deal_score"] >= min_score]

    return {
        "deals": deals,
        "total": len(deals),
        "strong": len([d for d in deals if d["deal_label"] == "strong"]),
        "medium": len([d for d in deals if d["deal_label"] == "medium"]),
        "weak": len([d for d in deals if d["deal_label"] == "weak"]),
    }


@router.post("/sources/{source_id}/analyze")
async def analyze_source(source_id: int):
    """Re-analyze a source product and update its deal score."""
    with get_db() as db:
        row = db.execute("SELECT * FROM ra_source_products WHERE id = ?", (source_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Source product not found")

    row = _parse_json_fields(dict_row(row), JSON_FIELDS_SOURCE)
    market = _estimate_market_value(row["title"], row.get("category", ""), row["source_price"])
    deal = _score_deal(market["market_price"], row["source_price"], row.get("shipping_cost", 0), market["fees_estimate"])

    notes = {}
    try:
        if row.get("notes"):
            notes = json.loads(row["notes"]) if isinstance(row["notes"], str) else row["notes"]
    except (json.JSONDecodeError, TypeError):
        pass
    notes["deal_score"] = deal
    notes["market_estimate"] = market

    with get_db() as db:
        db.execute(
            "UPDATE ra_source_products SET notes = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(notes), source_id),
        )

    return {
        "id": source_id,
        "market_estimate": market,
        "deal": {**deal, "market_price": market["market_price"]},
    }


# ── Bulk Price Check ────────────────────────────────────────────────────────────

@router.post("/sources/bulk-refresh")
async def bulk_refresh_prices():
    """Refresh prices for all active source products.

    Returns:
    - Summary of price changes
    - Recommendations per product
    """
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM ra_source_products
               WHERE source_price > 0 AND availability = 'in_stock'
               ORDER BY created_at DESC LIMIT 100""",
        ).fetchall())

    results = []
    for row in rows:
        row = _parse_json_fields(row, JSON_FIELDS_SOURCE)

        last_watch = db.execute(
            "SELECT price, checked_at FROM ra_price_watch WHERE source_product_id = ? ORDER BY checked_at DESC LIMIT 1",
            (row["id"],),
        ).fetchone()

        prev_price = dict_row(last_watch)["price"] if last_watch else row["source_price"]
        price_change = round(row["source_price"] - prev_price, 2) if prev_price else 0

        market = _estimate_market_value(row["title"], row.get("category", ""), row["source_price"])
        old_profit = market["estimated_profit"]
        new_market = _estimate_market_value(row["title"], row.get("category", ""), row["source_price"])
        new_profit = new_market["estimated_profit"]

        profit_change = new_profit - old_profit

        if abs(price_change) > 0.01:
            recommendation = "reprice"
        elif profit_change < -5:
            recommendation = "review"
        elif profit_change < -10:
            recommendation = "delist"
        else:
            recommendation = "keep"

        db.execute(
            "INSERT INTO ra_price_watch (source_product_id, price, availability, price_change) VALUES (?,?,?,?)",
            (row["id"], row["source_price"], row.get("availability", "in_stock"), price_change),
        )
        db.execute(
            "UPDATE ra_source_products SET last_checked = datetime('now') WHERE id = ?",
            (row["id"],),
        )

        results.append({
            "id": row["id"],
            "title": row["title"][:60],
            "source_price": row["source_price"],
            "price_change": price_change,
            "prev_price": prev_price,
            "availability": row.get("availability", "in_stock"),
            "estimated_profit": new_profit,
            "profit_change": round(profit_change, 2),
            "recommendation": recommendation,
        })

    return {
        "checked": len(results),
        "results": results,
        "summary": {
            "keep": len([r for r in results if r["recommendation"] == "keep"]),
            "reprice": len([r for r in results if r["recommendation"] == "reprice"]),
            "review": len([r for r in results if r["recommendation"] == "review"]),
            "delist": len([r for r in results if r["recommendation"] == "delist"]),
        },
    }


# ── Create Listing from Source ─────────────────────────────────────────────────

class CreateListingFromSourceRequest(BaseModel):
    source_id: int
    platform: str
    your_price: float
    platform_fee_percent: float = 13.0
    title: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None


@router.post("/listings/from-source")
async def create_listing_from_source(req: CreateListingFromSourceRequest):
    """Create a listing draft from a source product with all computed fields."""
    with get_db() as db:
        src = db.execute("SELECT * FROM ra_source_products WHERE id = ?", (req.source_id,)).fetchone()
        if not src:
            raise HTTPException(404, "Source product not found")

        src = _parse_json_fields(dict_row(src), JSON_FIELDS_SOURCE)

        title = req.title or src["title"]
        description = req.description or src.get("description", "")
        images = req.images or src.get("source_images", [])[:6]

        profit = _calc_profit(
            req.your_price,
            src["source_price"],
            src.get("shipping_cost", 0),
            req.platform_fee_percent,
        )

        cur = db.execute(
            """INSERT INTO ra_listings
               (source_product_id, platform, title, description, your_price,
                markup_amount, markup_percent, platform_fee_percent, estimated_profit,
                images, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (req.source_id, req.platform, title, description, req.your_price,
             profit["markup_amount"], profit["markup_percent"], req.platform_fee_percent,
             profit["estimated_profit"], json.dumps(images), "draft"),
        )

    return {
        "id": cur.lastrowid,
        "title": title,
        "platform": req.platform,
        "your_price": req.your_price,
        **profit,
    }

