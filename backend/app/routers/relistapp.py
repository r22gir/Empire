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
import re
from datetime import datetime, date
from urllib.parse import unquote, urlparse

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ra_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_key TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            service_type TEXT NOT NULL DEFAULT 'free_public',
            enabled INTEGER NOT NULL DEFAULT 1,
            mode TEXT NOT NULL DEFAULT 'manual',
            auth_present INTEGER NOT NULL DEFAULT 0,
            auth_required INTEGER NOT NULL DEFAULT 0,
            schedule TEXT DEFAULT '',
            quota_daily INTEGER DEFAULT 0,
            rate_limit INTEGER DEFAULT 0,
            cost_class TEXT NOT NULL DEFAULT 'free',
            last_run TEXT,
            last_success TEXT,
            last_error TEXT,
            health TEXT DEFAULT 'unknown',
            weight INTEGER DEFAULT 100,
            scope TEXT DEFAULT '{}',
            pause_reason TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Compatibility for existing SQLite dev DBs created before the scout
    # orchestrator added source attribution columns.
    existing_source_cols = {
        row[1] for row in cur.execute("PRAGMA table_info(ra_source_products)").fetchall()
    }
    if "scout_source" not in existing_source_cols:
        cur.execute("ALTER TABLE ra_source_products ADD COLUMN scout_source TEXT DEFAULT ''")
    if "scout_confidence" not in existing_source_cols:
        cur.execute("ALTER TABLE ra_source_products ADD COLUMN scout_confidence REAL DEFAULT 0")

    conn.commit()
    conn.close()
    log.info("RelistApp tables initialized")

_init_tables()


# ── Service Registry Defaults ──────────────────────────────────────────────────

DEFAULT_SERVICES = [
    {
        "service_key": "scout_url_import",
        "display_name": "URL Import Scout",
        "description": "Import products via URL from Amazon, Walmart, AliExpress, and other supported sites",
        "service_type": "free_public",
        "enabled": 1,
        "mode": "manual",
        "auth_required": 0,
        "cost_class": "free",
        "health": "healthy",
        "weight": 100,
    },
    {
        "service_key": "scout_amazon_bestsellers",
        "display_name": "Amazon Best Sellers Scout",
        "description": "Automatically pull top sellers from Amazon Best Sellers pages",
        "service_type": "free_public",
        "enabled": 0,
        "mode": "manual",
        "auth_required": 0,
        "cost_class": "free",
        "health": "not_implemented",
        "weight": 50,
    },
    {
        "service_key": "scout_amazon_movers",
        "display_name": "Amazon Movers & Shakers Scout",
        "description": "Track products with rapid rank movement on Amazon",
        "service_type": "free_public",
        "enabled": 0,
        "mode": "manual",
        "auth_required": 0,
        "cost_class": "free",
        "health": "not_implemented",
        "weight": 50,
    },
    {
        "service_key": "scout_google_trends",
        "display_name": "Google Trends Scout",
        "description": "Track trending products via Google Trends signals",
        "service_type": "free_public",
        "enabled": 0,
        "mode": "manual",
        "auth_required": 0,
        "cost_class": "free",
        "health": "not_implemented",
        "weight": 50,
    },
    {
        "service_key": "scout_tiktok",
        "display_name": "TikTok Trend Scout",
        "description": "Track products trending on TikTok Shop and hashtag signals",
        "service_type": "free_public",
        "enabled": 0,
        "mode": "manual",
        "auth_required": 0,
        "cost_class": "free",
        "health": "not_implemented",
        "weight": 50,
    },
    {
        "service_key": "amazon_spapi",
        "display_name": "Amazon SP-API",
        "description": "Official Amazon Selling Partner API for product data, pricing, and inventory",
        "service_type": "official_api",
        "enabled": 0,
        "mode": "off",
        "auth_required": 1,
        "cost_class": "paid",
        "health": "no_auth",
        "weight": 100,
    },
    {
        "service_key": "ebay_api",
        "display_name": "eBay API",
        "description": "Official eBay API for listing, inventory, and order management",
        "service_type": "official_api",
        "enabled": 0,
        "mode": "off",
        "auth_required": 1,
        "cost_class": "paid",
        "health": "no_auth",
        "weight": 100,
    },
    {
        "service_key": "walmart_api",
        "display_name": "Walmart API",
        "description": "Official Walmart API for product data and inventory",
        "service_type": "official_api",
        "enabled": 0,
        "mode": "off",
        "auth_required": 1,
        "cost_class": "paid",
        "health": "no_auth",
        "weight": 100,
    },
    {
        "service_key": "jungle_scout",
        "display_name": "Jungle Scout",
        "description": "Premium product research and analytics via Jungle Scout API",
        "service_type": "premium_optional",
        "enabled": 0,
        "mode": "off",
        "auth_required": 1,
        "cost_class": "premium",
        "health": "not_configured",
        "weight": 100,
    },
    {
        "service_key": "helium_10",
        "display_name": "Helium 10",
        "description": "Premium Amazon product research via Helium 10 API",
        "service_type": "premium_optional",
        "enabled": 0,
        "mode": "off",
        "auth_required": 1,
        "cost_class": "premium",
        "health": "not_configured",
        "weight": 100,
    },
    {
        "service_key": "selleramp",
        "display_name": "SellerAmp",
        "description": "Premium Amazon seller tools via SellerAmp API",
        "service_type": "premium_optional",
        "enabled": 0,
        "mode": "off",
        "auth_required": 1,
        "cost_class": "premium",
        "health": "not_configured",
        "weight": 100,
    },
    {
        "service_key": "ai_deal_finder",
        "display_name": "AI Deal Finder",
        "description": "Score and rank imported products by arbitrage opportunity",
        "service_type": "free_public",
        "enabled": 1,
        "mode": "assist",
        "auth_required": 0,
        "cost_class": "free",
        "health": "healthy",
        "weight": 100,
    },
    {
        "service_key": "price_monitor",
        "display_name": "Price Monitor",
        "description": "Track source product prices and alert on changes",
        "service_type": "free_public",
        "enabled": 1,
        "mode": "assist",
        "auth_required": 0,
        "cost_class": "free",
        "health": "stub",
        "weight": 100,
    },
    {
        "service_key": "inventory_sync",
        "display_name": "Inventory Sync",
        "description": "Sync inventory levels across platforms and handle OOS",
        "service_type": "free_public",
        "enabled": 0,
        "mode": "manual",
        "auth_required": 0,
        "cost_class": "free",
        "health": "not_implemented",
        "weight": 100,
    },
    {
        "service_key": "auto_relist",
        "display_name": "Auto-Relist",
        "description": "Automatically relist sold-out or expired items",
        "service_type": "free_public",
        "enabled": 0,
        "mode": "off",
        "auth_required": 0,
        "cost_class": "free",
        "health": "not_implemented",
        "weight": 100,
    },
    {
        "service_key": "order_router",
        "display_name": "Order Router",
        "description": "Route and fulfill orders from sales channels to source suppliers",
        "service_type": "free_public",
        "enabled": 0,
        "mode": "manual",
        "auth_required": 0,
        "cost_class": "free",
        "health": "not_implemented",
        "weight": 100,
    },
]


def _init_services():
    """Initialize default services if not already present."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    for svc in DEFAULT_SERVICES:
        existing = conn.execute(
            "SELECT id FROM ra_services WHERE service_key = ?",
            (svc["service_key"],)
        ).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO ra_services
                   (service_key, display_name, description, service_type, enabled, mode,
                    auth_required, cost_class, health, weight)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (svc["service_key"], svc["display_name"], svc["description"], svc["service_type"],
                 svc["enabled"], svc["mode"], svc["auth_required"], svc["cost_class"],
                 svc["health"], svc["weight"]),
            )
    conn.commit()
    conn.close()


_init_services()

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
    """Check the live price of a source product by scraping its URL.

    Returns the scraped price or honest error if scraping fails.
    Does NOT update the stored price — caller decides whether to apply.
    """
    with get_db() as db:
        row = db.execute(
            "SELECT id, source_url, source_platform, source_price, availability FROM ra_source_products WHERE id = ?",
            (source_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Source product not found")
        src = dict_row(row)

    url = src.get("source_url", "")
    platform = src.get("source_platform", "unknown")

    if not url:
        return {
            "source_product_id": source_id,
            "price": src["source_price"],
            "availability": src["availability"],
            "success": False,
            "error": "No source URL — cannot check live price",
            "message": "This product was imported without a URL. Update the source URL to enable live price checks.",
        }

    live = await _scrape_live_price(url, platform)
    scraped_price = live["price"]
    scraped_avail = live["availability"]
    change = round(scraped_price - src["source_price"], 2) if scraped_price > 0 else 0

    with get_db() as db:
        last_watch = db.execute(
            "SELECT price FROM ra_price_watch WHERE source_product_id = ? ORDER BY checked_at DESC LIMIT 1",
            (source_id,),
        ).fetchone()
        prev_price = dict_row(last_watch)["price"] if last_watch else src["source_price"]
        db.execute(
            "INSERT INTO ra_price_watch (source_product_id, price, availability, price_change) VALUES (?,?,?,?)",
            (source_id, scraped_price if scraped_price > 0 else prev_price, scraped_avail, change),
        )
        db.execute(
            "UPDATE ra_source_products SET last_checked = datetime('now') WHERE id = ?",
            (source_id,),
        )

    return {
        "source_product_id": source_id,
        "scraped_price": scraped_price if live["success"] else None,
        "prev_price": prev_price,
        "price_change": change,
        "availability": scraped_avail if live["success"] else src["availability"],
        "success": live["success"],
        "error": live["error"],
        "message": "Live price scraped successfully" if live["success"] else f"Scraping failed: {live['error']}",
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
    extraction_status: str = "live"
    extraction_error: str = ""
    needs_manual_review: bool = False


def _parse_price_text(value: str | None) -> float:
    if not value:
        return 0.0
    match = re.search(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{2})?)", value.replace("\xa0", " "))
    if not match:
        return 0.0
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return 0.0


def _title_from_url(url: str, platform: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "") or platform or "source"
    tail = unquote(parsed.path.rstrip("/").split("/")[-1] if parsed.path else "").replace("-", " ").replace("_", " ").strip()
    if tail and not tail.lower().startswith(("dp", "ip", "gp")):
        return tail[:120]
    return f"Unverified product from {host}"


def _extract_product_from_html(url: str, platform: str, html: str) -> ProductExtractedData:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    title = ""
    for selector in [
        "#productTitle",
        "h1[itemprop='name']",
        "h1",
        "meta[property='og:title']",
        "meta[name='twitter:title']",
        "title",
    ]:
        elem = soup.select_one(selector)
        if not elem:
            continue
        title = elem.get("content", "") if elem.name == "meta" else elem.get_text(" ", strip=True)
        if title:
            break
    title = re.sub(r"\s+", " ", title).strip(" -|") or _title_from_url(url, platform)

    description = ""
    desc_elem = soup.select_one("meta[name='description']") or soup.select_one("meta[property='og:description']")
    if desc_elem:
        description = desc_elem.get("content", "").strip()

    price = 0.0
    for selector in [
        "meta[property='product:price:amount']",
        "meta[itemprop='price']",
        "[itemprop='price']",
        ".a-price .a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        ".x-price-primary span",
        "[data-testid='price-wrap']",
        ".price",
    ]:
        elem = soup.select_one(selector)
        if not elem:
            continue
        raw = elem.get("content", "") if elem.name == "meta" else elem.get_text(" ", strip=True)
        price = _parse_price_text(raw)
        if price > 0:
            break

    images = []
    for selector in ["meta[property='og:image']", "img#landingImage", "img[itemprop='image']"]:
        elem = soup.select_one(selector)
        ref = elem.get("content") if elem and elem.name == "meta" else elem.get("src") if elem else ""
        if ref and ref not in images:
            images.append(ref)

    availability = "in_stock"
    availability_text = " ".join([
        elem.get("content", "") if elem.name == "meta" else elem.get_text(" ", strip=True)
        for elem in soup.select("[itemprop='availability'], #availability, .availability")
    ]).lower()
    if "out of stock" in availability_text or "unavailable" in availability_text:
        availability = "out_of_stock"
    elif "limited" in availability_text:
        availability = "limited"

    brand = ""
    brand_elem = soup.select_one("[itemprop='brand']") or soup.select_one("meta[property='product:brand']")
    if brand_elem:
        brand = brand_elem.get("content", "") if brand_elem.name == "meta" else brand_elem.get_text(" ", strip=True)

    category = ""
    category_elem = soup.select_one("meta[property='product:category']") or soup.select_one("nav[aria-label='Breadcrumb']") or soup.select_one("#wayfinding-breadcrumbs_container")
    if category_elem:
        category = category_elem.get("content", "") if category_elem.name == "meta" else category_elem.get_text(" ", strip=True)

    return ProductExtractedData(
        title=title[:220],
        description=description[:1000],
        price=price,
        images=images[:6],
        brand=brand[:120],
        category=category[:180],
        availability=availability,
        source_name=(platform or urlparse(url).netloc or "source").title(),
        extraction_status="live" if price > 0 and not title.startswith("Unverified product") else "partial",
        needs_manual_review=price <= 0 or title.startswith("Unverified product"),
        extraction_error="" if price > 0 else "No source price found; founder review needed before draft listing.",
    )


async def _extract_product_from_url(url: str, platform: str) -> ProductExtractedData:
    import httpx

    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("A valid http(s) product URL is required")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    }
    async with httpx.AsyncClient(timeout=18.0, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return _extract_product_from_html(str(resp.url), platform, resp.text)


async def _scrape_live_price(url: str, platform: str) -> dict:
    """Scrape the live price from a product URL.

    Returns {"price": float, "availability": str, "success": bool, "error": str or None}
    """
    import httpx
    from bs4 import BeautifulSoup

    if not url or not url.startswith("http"):
        return {"price": 0, "availability": "unknown", "success": False, "error": "No valid URL"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        price = 0.0
        availability = "in_stock"

        if platform == "amazon":
            price_elem = soup.select_one(".a-price .a-offscreen") or soup.select_one("#priceblock_ourprice") or soup.select_one("#priceblock_dealprice") or soup.select_one(".a-color-price")
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass
            avail_elem = soup.select_one("#availability span")
            if avail_elem:
                avail_text = avail_elem.get_text(strip=True).lower()
                if "out of stock" in avail_text or "unavailable" in avail_text:
                    availability = "out_of_stock"
                elif "limited" in avail_text:
                    availability = "limited"

        elif platform == "walmart":
            price_elem = soup.select_one("[itemprop='price']")
            if price_elem:
                price_text = price_elem.get("content", price_elem.get_text(strip=True)).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass
            avail_elem = soup.select_one("[itemprop='availability']")
            if avail_elem and "out" in avail_elem.get("content", "").lower():
                availability = "out_of_stock"

        elif platform == "aliexpress":
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

        elif platform == "ebay":
            price_elem = soup.select_one(".x-price-primary span") or soup.select_one("[itemprop='price']")
            if price_elem:
                price_text = price_elem.get("content", price_elem.get_text(strip=True)).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass

        else:
            price_elem = soup.select_one("[itemprop='price'], .price, #priceblock")
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except ValueError:
                    pass

        if price <= 0:
            return {"price": 0, "availability": availability, "success": False, "error": f"No price found on {platform}"}

        return {"price": price, "availability": availability, "success": True, "error": None}

    except Exception as e:
        return {"price": 0, "availability": "unknown", "success": False, "error": str(e)}


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
            title=_title_from_url(url, platform),
            source_name=platform.title(),
            availability="unknown",
            extraction_status="failed",
            extraction_error=str(e),
            needs_manual_review=True,
        )

    market = _estimate_market_value(extracted.title, extracted.category, extracted.price)
    effective_shipping = extracted.shipping_cost if extracted.shipping_cost > 0 else market["shipping_estimate"]
    deal = _score_deal(market["market_price"], extracted.price, effective_shipping, market["fees_estimate"])

    with get_db() as db:
        cur = db.execute(
            """INSERT INTO ra_source_products
               (source_platform, source_url, title, description, source_price, shipping_cost,
                source_images, category, brand, condition, availability, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (platform, url, extracted.title, extracted.description, extracted.price,
             effective_shipping, json.dumps(extracted.images), extracted.category,
             extracted.brand, extracted.condition, extracted.availability,
             json.dumps({
                 "deal_score": deal,
                 "market_estimate": market,
                 "extraction_status": extracted.extraction_status,
                 "extraction_error": extracted.extraction_error,
                 "needs_manual_review": extracted.needs_manual_review,
             })),
        )
        source_id = cur.lastrowid

    return {
        "id": source_id,
        "source_platform": platform,
        "source_url": url,
        "title": extracted.title,
        "price": extracted.price,
        "shipping_cost": effective_shipping,
        "images": extracted.images[:4],
        "brand": extracted.brand,
        "market_estimate": market,
        "deal": {**deal, "market_price": market["market_price"]},
        "extraction_status": extracted.extraction_status,
        "extraction_error": extracted.extraction_error,
        "needs_manual_review": extracted.needs_manual_review,
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
    """Refresh prices for all active source products with live URL scraping.

    Scrapes each product's source URL for the current live price.
    Only processes products with valid URLs.
    Returns honest results including scrape failures.

    Returns:
    - Summary of price changes
    - Per-product results with success/failure
    """
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM ra_source_products
               WHERE source_price > 0
               AND availability = 'in_stock'
               AND source_url IS NOT NULL
               AND source_url != ''
               ORDER BY created_at DESC LIMIT 50""",
        ).fetchall())

    results = []
    successful = 0
    failed = 0

    for row in rows:
        row = _parse_json_fields(row, JSON_FIELDS_SOURCE)
        product_id = row["id"]
        url = row.get("source_url", "")
        platform = row.get("source_platform", "unknown")

        with get_db() as db:
            last_watch = db.execute(
                "SELECT price FROM ra_price_watch WHERE source_product_id = ? ORDER BY checked_at DESC LIMIT 1",
                (product_id,),
            ).fetchone()
        prev_price = dict_row(last_watch)["price"] if last_watch else row["source_price"]

        live = await _scrape_live_price(url, platform)
        scraped_price = live["price"] if live["success"] else row["source_price"]
        scraped_avail = live["availability"] if live["success"] else row.get("availability", "in_stock")

        price_change = round(scraped_price - prev_price, 2) if prev_price else 0

        market = _estimate_market_value(row["title"], row.get("category", ""), scraped_price if scraped_price > 0 else row["source_price"])
        new_profit = market["estimated_profit"]

        old_profit = row.get("_cached_profit", market["estimated_profit"])
        profit_change = new_profit - old_profit

        if scraped_price <= 0 or not live["success"]:
            recommendation = "unavailable"
            failed += 1
        elif abs(price_change) > 0.01:
            recommendation = "reprice"
            successful += 1
        elif profit_change < -5:
            recommendation = "review"
            successful += 1
        elif profit_change < -10:
            recommendation = "delist"
            successful += 1
        else:
            recommendation = "keep"
            successful += 1

        with get_db() as db:
            if scraped_price > 0 and scraped_price != row["source_price"]:
                db.execute(
                    "UPDATE ra_source_products SET source_price = ?, availability = ?, last_checked = datetime('now') WHERE id = ?",
                    (scraped_price, scraped_avail, product_id),
                )
            else:
                db.execute(
                    "UPDATE ra_source_products SET last_checked = datetime('now') WHERE id = ?",
                    (product_id,),
                )

            db.execute(
                "INSERT INTO ra_price_watch (source_product_id, price, availability, price_change) VALUES (?,?,?,?)",
                (product_id, scraped_price if scraped_price > 0 else prev_price, scraped_avail, price_change),
            )

        results.append({
            "id": product_id,
            "title": row["title"][:60],
            "source_url": url[:50] + "..." if len(url) > 50 else url,
            "scraped_price": scraped_price if live["success"] else None,
            "stored_price": row["source_price"],
            "price_change": price_change,
            "prev_price": prev_price,
            "availability": scraped_avail,
            "estimated_profit": new_profit,
            "profit_change": round(profit_change, 2),
            "recommendation": recommendation,
            "scrape_success": live["success"],
            "scrape_error": live["error"] if not live["success"] else None,
        })

    return {
        "checked": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
        "summary": {
            "keep": len([r for r in results if r["recommendation"] == "keep"]),
            "reprice": len([r for r in results if r["recommendation"] == "reprice"]),
            "review": len([r for r in results if r["recommendation"] == "review"]),
            "delist": len([r for r in results if r["recommendation"] == "delist"]),
            "unavailable": len([r for r in results if r["recommendation"] == "unavailable"]),
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


# ── Service Registry ────────────────────────────────────────────────────────────

class ServiceUpdate(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = None
    weight: Optional[int] = None
    schedule: Optional[str] = None
    quota_daily: Optional[int] = None
    rate_limit: Optional[int] = None
    scope: Optional[dict] = None


@router.get("/services")
async def list_services():
    """List all RelistApp services with their current state.

    Returns all registered services including disabled/not-implemented ones.
    Health values: healthy, stub, not_implemented, no_auth, not_configured, error, unknown
    """
    with get_db() as db:
        rows = dict_rows(db.execute(
            "SELECT * FROM ra_services ORDER BY service_type, display_name"
        ).fetchall())
    for row in rows:
        if row.get("scope") and isinstance(row["scope"], str):
            try:
                row["scope"] = json.loads(row["scope"])
            except (json.JSONDecodeError, TypeError):
                row["scope"] = {}
    return {"services": rows, "total": len(rows)}


@router.get("/services/{service_key}")
async def get_service(service_key: str):
    """Get a specific service by key."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM ra_services WHERE service_key = ?", (service_key,)
        ).fetchone()
    if not row:
        raise HTTPException(404, f"Service '{service_key}' not found")
    row = dict_row(row)
    if row.get("scope") and isinstance(row["scope"], str):
        try:
            row["scope"] = json.loads(row["scope"])
        except (json.JSONDecodeError, TypeError):
            row["scope"] = {}
    return row


@router.patch("/services/{service_key}")
async def update_service(service_key: str, req: ServiceUpdate):
    """Update a service's configuration.

    Supports: enabled, mode, weight, schedule, quota_daily, rate_limit, scope
    Mode values: off, manual, assist, auto
    """
    valid_modes = ("off", "manual", "assist", "auto")
    if req.mode is not None and req.mode not in valid_modes:
        raise HTTPException(400, f"Invalid mode. Must be one of: {', '.join(valid_modes)}")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    if "scope" in updates:
        updates["scope"] = json.dumps(updates["scope"])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [service_key]
    with get_db() as db:
        affected = db.execute(
            f"UPDATE ra_services SET {set_clause}, updated_at = datetime('now') WHERE service_key = ?",
            values,
        ).rowcount
        if not affected:
            raise HTTPException(404, f"Service '{service_key}' not found")

        row = db.execute(
            "SELECT * FROM ra_services WHERE service_key = ?", (service_key,)
        ).fetchone()
    row = dict_row(row)
    if row.get("scope") and isinstance(row["scope"], str):
        try:
            row["scope"] = json.loads(row["scope"])
        except (json.JSONDecodeError, TypeError):
            row["scope"] = {}
    return row


@router.post("/services/{service_key}/pause")
async def pause_service(service_key: str, reason: str = ""):
    """Pause a service. Sets mode to 'off' and records pause reason."""
    with get_db() as db:
        affected = db.execute(
            """UPDATE ra_services SET enabled = 0, mode = 'off',
               pause_reason = ?, updated_at = datetime('now')
               WHERE service_key = ?""",
            (reason, service_key),
        ).rowcount
    if not affected:
        raise HTTPException(404, f"Service '{service_key}' not found")
    return {"service_key": service_key, "enabled": False, "mode": "off", "pause_reason": reason}


@router.post("/services/{service_key}/resume")
async def resume_service(service_key: str):
    """Resume a paused service. Restores previous mode if it was 'off'."""
    with get_db() as db:
        row = db.execute(
            "SELECT service_type, pause_reason FROM ra_services WHERE service_key = ?",
            (service_key,)
        ).fetchone()
    if not row:
        raise HTTPException(404, f"Service '{service_key}' not found")
    row = dict_row(row)

    default_mode = "manual"
    if row["service_type"] == "free_public":
        default_mode = "assist"
    elif row["service_type"] == "official_api":
        default_mode = "manual"
    else:
        default_mode = "off"

    with get_db() as db:
        affected = db.execute(
            """UPDATE ra_services SET enabled = 1, mode = ?, pause_reason = '',
               updated_at = datetime('now') WHERE service_key = ?""",
            (default_mode, service_key),
        ).rowcount
    return {"service_key": service_key, "enabled": True, "mode": default_mode}


@router.post("/services/{service_key}/run-now")
async def run_service_now(service_key: str):
    """Trigger an immediate run of a service.

    Returns the result of the run or an error if the service is not runnable.
    For manual services, this initiates the scout/pricing operation immediately.
    """
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM ra_services WHERE service_key = ?", (service_key,)
        ).fetchone()
    if not row:
        raise HTTPException(404, f"Service '{service_key}' not found")
    row = dict_row(row)

    if row["service_key"] == "scout_url_import":
        return {"service_key": service_key, "status": "noop", "message": "Use POST /sources/import-full to import a URL. URL import is manual."}
    elif row["service_key"] == "ai_deal_finder":
        return {"service_key": service_key, "status": "noop", "message": "AI deal finder runs automatically on imported products."}
    elif row["service_key"] == "price_monitor":
        return {"service_key": service_key, "status": "triggered", "message": "Price check triggered. Use POST /sources/bulk-refresh for bulk refresh."}
    elif row["service_key"] == "amazon_spapi":
        return {"service_key": service_key, "status": "not_implemented", "message": "Amazon SP-API integration not yet built."}
    elif row["service_key"] == "ebay_api":
        return {"service_key": service_key, "status": "not_implemented", "message": "eBay API integration not yet built."}
    elif row["service_key"] == "walmart_api":
        return {"service_key": service_key, "status": "not_implemented", "message": "Walmart API integration not yet built."}
    elif row["service_key"].startswith("scout_"):
        return {"service_key": service_key, "status": "not_implemented", "message": f"Scout source '{service_key}' not yet implemented."}
    elif row["service_key"].startswith("premium_"):
        return {"service_key": service_key, "status": "not_configured", "message": f"Premium service '{service_key}' requires API credentials."}
    else:
        return {"service_key": service_key, "status": "noop", "message": f"Service '{service_key}' does not support run-now."}


# ── Scout Orchestrator ────────────────────────────────────────────────────────────

class ScoutResult(BaseModel):
    source_platform: str
    source_url: Optional[str] = None
    source_product_id: Optional[str] = None
    title: str
    source_price: float = 0
    shipping_cost: float = 0
    currency: str = "USD"
    category: str = ""
    brand: str = ""
    condition: str = "new"
    availability: str = "in_stock"
    source_images: List[str] = []
    scout_source: str = "unknown"
    scout_confidence: float = 0.5
    scout_signals: dict = {}


async def _scout_amazon_best_sellers(category: str = "", limit: int = 20) -> List[ScoutResult]:
    """Scrape Amazon Best Sellers pages for product opportunities.

    Returns a list of ScoutResult objects with source attribution.
    This is a free/public signal — no API key required.
    """
    import httpx
    from bs4 import BeautifulSoup

    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    categories = [
        "electronics", "computers", "camera", "headphones", "speaker",
        "home", "kitchen", "appliances", "home-improvement",
        "toys", "games", "sports", "outdoors",
        "beauty", "health", "clothing", "shoes", "jewelry",
    ] if not category else [category]

    for cat in categories[:3]:
        url = f"https://www.amazon.com/gp/bestsellers/{cat}/"
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                html = resp.text

            soup = BeautifulSoup(html, "html.parser")
            items = soup.select("#zg_better-root .zg_itemImmersion") or soup.select(".p13n-sc-truncated")

            for item in items[:limit]:
                try:
                    title_elem = item.select_one("._cDEzb_p13n-sc-css-line-clamp-3") or item.select_one("a.a-size-small") or item.select_one("span.a-size-small")
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    if not title:
                        continue

                    price_elem = item.select_one(".p13n-sc-price")
                    price_text = price_elem.get_text(strip=True).replace("$", "").replace(",", "") if price_elem else "0"
                    try:
                        price = float(price_text)
                    except ValueError:
                        price = 0.0

                    link_elem = item.select_one("a.a-link-normal") or item.select_one("a")
                    href = link_elem.get("href", "") if link_elem else ""
                    product_url = f"https://www.amazon.com{href}" if href.startswith("/") else href

                    results.append(ScoutResult(
                        source_platform="amazon",
                        source_url=product_url,
                        source_product_id=href.split("/dp/")[-1].split("/")[0] if "/dp/" in href else None,
                        title=title,
                        source_price=price,
                        currency="USD",
                        category=cat,
                        availability="in_stock",
                        scout_source="amazon_bestsellers",
                        scout_confidence=0.7,
                        scout_signals={"rank_position": len(results) + 1, "page": cat, "type": "best_seller"},
                    ))
                except Exception:
                    continue

        except Exception as e:
            log.warning(f"Failed to scrape Amazon best sellers for {cat}: {e}")
            continue

    return results


async def _scout_walmart_trends(limit: int = 20) -> List[ScoutResult]:
    """Scrape Walmart's trending items as a free/public signal."""
    import httpx
    from bs4 import BeautifulSoup

    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,*/*",
    }

    url = "https://www.walmart.com/trending"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(".search-result-gridview-item") or soup.select("[data-item-id]")[:limit]

        for item in items[:limit]:
            title_elem = item.select_one("a span") or item.select_one("span")
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                continue

            price_elem = item.select_one("[itemprop='price']")
            price_text = price_elem.get("content", price_elem.get_text(strip=True)).replace("$", "").replace(",", "") if price_elem else "0"
            try:
                price = float(price_text)
            except ValueError:
                price = 0.0

            link_elem = item.select_one("a")
            href = link_elem.get("href", "") if link_elem else ""
            product_url = f"https://www.walmart.com{href}" if href.startswith("/") else href

            results.append(ScoutResult(
                source_platform="walmart",
                source_url=product_url,
                title=title,
                source_price=price,
                currency="USD",
                availability="in_stock",
                scout_source="walmart_trending",
                scout_confidence=0.5,
                scout_signals={"type": "trending"},
            ))
    except Exception as e:
        log.warning(f"Failed to scrape Walmart trending: {e}")

    return results


def _deduplicate_scout_results(existing: List[dict], new_results: List[ScoutResult]) -> List[ScoutResult]:
    """Remove duplicates based on title similarity and URL."""
    existing_titles = {r.get("title", "").lower()[:50]: r for r in existing if r.get("title")}
    existing_urls = {r.get("source_url", ""): r for r in existing if r.get("source_url")}

    deduped = []
    for result in new_results:
        url_key = result.source_url or ""
        title_key = result.title.lower()[:50]

        if url_key and url_key in existing_urls:
            continue
        if title_key in existing_titles:
            continue

        deduped.append(result)

    return deduped


async def _run_scout_sources(sources: List[str], category: str = "", limit_per_source: int = 30) -> List[ScoutResult]:
    """Run multiple scout sources and aggregate results."""
    all_results: List[ScoutResult] = []

    for source in sources:
        try:
            if source == "amazon_bestsellers":
                results = await _scout_amazon_best_sellers(category=category, limit=limit_per_source)
                all_results.extend(results)
            elif source == "walmart_trending":
                results = await _scout_walmart_trends(limit=limit_per_source)
                all_results.extend(results)
        except Exception as e:
            log.warning(f"Scout source {source} failed: {e}")

    return all_results


@router.post("/scout/run")
async def scout_run(
    sources: Optional[List[str]] = None,
    category: str = "",
    limit_per_source: int = Query(30, ge=1, le=100),
):
    """Run the scout orchestrator across enabled sources.

    Runs specified scout sources and imports new products into ra_source_products.
    Deduplicates against existing products by URL and title.
    """
    if sources is None:
        sources = ["amazon_bestsellers"]

    results = await _run_scout_sources(sources, category=category, limit_per_source=limit_per_source)

    if not results:
        return {"scouted": 0, "imported": 0, "skipped_duplicates": 0, "results": []}

    with get_db() as db:
        existing = dict_rows(db.execute(
            "SELECT title, source_url, source_platform FROM ra_source_products LIMIT 500"
        ).fetchall())

    deduped = _deduplicate_scout_results(existing, results)

    imported = 0
    import_results = []
    for r in deduped:
        try:
            with get_db() as db:
                cur = db.execute(
                    """INSERT INTO ra_source_products
                       (source_platform, source_url, source_product_id, title, source_price,
                        shipping_cost, source_images, category, brand, condition, availability,
                        notes, scout_source, scout_confidence)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        r.source_platform, r.source_url, r.source_product_id, r.title,
                        r.source_price, r.shipping_cost,
                        json.dumps(r.source_images[:4]), r.category, r.brand, r.condition,
                        r.availability,
                        json.dumps({"scout_signals": r.scout_signals}),
                        r.scout_source, r.scout_confidence,
                    ),
                )
                new_id = cur.lastrowid

            import_results.append({
                "id": new_id,
                "title": r.title[:60],
                "source_platform": r.source_platform,
                "source_price": r.source_price,
                "scout_source": r.scout_source,
                "scout_confidence": r.scout_confidence,
            })
            imported += 1
        except Exception as e:
            log.warning(f"Failed to import scout result: {e}")

    return {
        "scouted": len(results),
        "imported": imported,
        "skipped_duplicates": len(results) - len(deduped),
        "results": import_results,
    }


@router.get("/scout/sources")
async def list_scout_sources():
    """List available scout sources and their status."""
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT service_key, display_name, description, enabled, mode,
                      health, weight, last_run, last_success, last_error
               FROM ra_services
               WHERE service_key LIKE 'scout_%'"""
        ).fetchall())

    return {"sources": rows}


@router.get("/scout/opportunities")
async def list_scout_opportunities(
    min_confidence: float = Query(0, ge=0, le=1),
    platform: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """List imported products that came from scout sources (not manual URL import).

    Useful for reviewing AI-scored opportunities from automated scout runs.
    """
    with get_db() as db:
        where = ["scout_source IS NOT NULL AND scout_source != ''"]
        params = []
        if platform:
            where.append("source_platform = ?")
            params.append(platform)
        clause = f"WHERE {' AND '.join(where)}"
        params.append(limit)

        rows = dict_rows(db.execute(
            f"""SELECT id, title, source_platform, source_price, scout_source,
                       scout_confidence, category, brand, availability,
                       notes, created_at, last_checked
                FROM ra_source_products
                {clause}
                ORDER BY scout_confidence DESC, created_at DESC
                LIMIT ?""",
            params,
        ).fetchall())

    for row in rows:
        if row.get("notes"):
            try:
                notes = json.loads(row["notes"]) if isinstance(row["notes"], str) else row["notes"]
                row["scout_signals"] = notes.get("scout_signals", {})
            except (json.JSONDecodeError, TypeError):
                row["scout_signals"] = {}

    return {"opportunities": rows, "total": len(rows)}
