"""SQLite schema and vendor seed for Empire Fine Fabrics."""

from __future__ import annotations

from typing import Iterable

from app.db.database import get_db

CATEGORIES = ("Upholstery", "Drapery", "Outdoor", "Other")
PUBLIC_CATEGORIES = CATEGORIES
ADMIN_CATEGORIES = CATEGORIES + ("Unsorted",)
UNSORTED_CATEGORY = "Unsorted"
PRODUCT_TYPES = ("sku", "collection")
UNITS = ("yard", "sq_ft", "roll", "box")

# Pass-through shipping defaults. Customer always pays an estimate of
# vendor freight + handling. Never zero — no free-shipping threshold.
DEFAULT_SHIPPING = {
    "ship_per_yard": 1.50,
    "ship_per_sample": 8.00,
    "ship_minimum": 12.00,
    "handling_fee": 3.50,
}

# Rafael: starter mills are offered online with brand names visible.
# Admin can still toggle either flag per vendor after seed.
SEED_VENDORS: tuple[dict, ...] = (
    {
        "slug": "charlotte",
        "name": "Charlotte",
        "online_sale_allowed": 1,
        "brand_display_allowed": 1,
        "default_markup": 2.2,
    },
    {
        "slug": "greenhouse",
        "name": "Greenhouse",
        "online_sale_allowed": 1,
        "brand_display_allowed": 1,
        "default_markup": 2.0,
    },
    {
        "slug": "kravet",
        "name": "Kravet",
        "online_sale_allowed": 1,
        "brand_display_allowed": 1,
        "default_markup": 2.5,
    },
    {
        "slug": "keyston",
        "name": "Keyston",
        "online_sale_allowed": 1,
        "brand_display_allowed": 1,
        "default_markup": 2.0,
    },
    {
        "slug": "sunbrella",
        "name": "Sunbrella",
        "online_sale_allowed": 1,
        "brand_display_allowed": 1,
        "default_markup": 1.85,
    },
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ff_vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    online_sale_allowed INTEGER NOT NULL DEFAULT 0,
    brand_display_allowed INTEGER NOT NULL DEFAULT 0,
    default_markup REAL NOT NULL DEFAULT 2.0,
    business TEXT NOT NULL DEFAULT 'workroom',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ff_markups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    markup REAL NOT NULL,
    UNIQUE(vendor_id, category),
    FOREIGN KEY (vendor_id) REFERENCES ff_vendors(id)
);

CREATE TABLE IF NOT EXISTS ff_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL,
    vendor_slug TEXT NOT NULL,
    pattern TEXT NOT NULL,
    color TEXT NOT NULL,
    sku TEXT,
    category TEXT NOT NULL,
    width TEXT,
    content TEXT,
    repeat TEXT,
    durability TEXT,
    care TEXT,
    net_price REAL NOT NULL,
    list_price REAL,
    product_url TEXT,
    notes TEXT,
    empire_code TEXT NOT NULL,
    image_path TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    business TEXT NOT NULL DEFAULT 'workroom',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (vendor_id) REFERENCES ff_vendors(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ff_products_identity
    ON ff_products(vendor_id, IFNULL(sku, ''), pattern, color);
CREATE INDEX IF NOT EXISTS idx_ff_products_category ON ff_products(category);
CREATE INDEX IF NOT EXISTS idx_ff_products_empire ON ff_products(empire_code);
CREATE INDEX IF NOT EXISTS idx_ff_products_active ON ff_products(is_active);

CREATE TABLE IF NOT EXISTS ff_sample_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_phone TEXT,
    product_ids TEXT NOT NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    business TEXT NOT NULL DEFAULT 'workroom',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ff_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id TEXT,
    invoice_id TEXT,
    customer_name TEXT,
    customer_email TEXT,
    customer_phone TEXT,
    items_json TEXT NOT NULL,
    subtotal REAL NOT NULL,
    checkout_url TEXT,
    stripe_mode TEXT NOT NULL DEFAULT 'test',
    status TEXT NOT NULL DEFAULT 'link_ready',
    business TEXT NOT NULL DEFAULT 'workroom',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ff_shipping_rules (
    vendor_id INTEGER PRIMARY KEY,
    ship_per_yard REAL NOT NULL DEFAULT 1.50,
    ship_per_sample REAL NOT NULL DEFAULT 8.00,
    ship_minimum REAL NOT NULL DEFAULT 12.00,
    handling_fee REAL NOT NULL DEFAULT 3.50,
    FOREIGN KEY (vendor_id) REFERENCES ff_vendors(id)
);

CREATE TABLE IF NOT EXISTS ff_quote_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    item_type TEXT,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_phone TEXT,
    message TEXT,
    lead_id INTEGER,
    status TEXT NOT NULL DEFAULT 'new',
    engine TEXT NOT NULL DEFAULT 'stub',
    business TEXT NOT NULL DEFAULT 'workroom',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ff_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

PRODUCT_EXTRA_COLUMNS = (
    ("product_type", "TEXT NOT NULL DEFAULT 'sku'"),
    ("unit", "TEXT NOT NULL DEFAULT 'yard'"),
    ("color_family", "TEXT"),
    ("is_unsorted", "INTEGER NOT NULL DEFAULT 0"),
    ("sku_range", "TEXT"),
    ("vendor_image_url", "TEXT"),
    ("collection", "TEXT"),
    ("description", "TEXT"),
    ("brand", "TEXT"),
)

ORDER_EXTRA_COLUMNS = (
    ("shipping_estimate", "REAL NOT NULL DEFAULT 0"),
    ("handling_total", "REAL NOT NULL DEFAULT 0"),
    ("shipping_total", "REAL NOT NULL DEFAULT 0"),
    ("shipping_breakdown", "TEXT"),
    ("actual_vendor_shipping", "REAL"),
    ("shipping_shortfall", "REAL NOT NULL DEFAULT 0"),
    ("shipping_flag", "TEXT NOT NULL DEFAULT ''"),
)

SAMPLE_EXTRA_COLUMNS = (
    ("shipping_estimate", "REAL NOT NULL DEFAULT 0"),
    ("handling_total", "REAL NOT NULL DEFAULT 0"),
    ("shipping_total", "REAL NOT NULL DEFAULT 0"),
    ("shipping_breakdown", "TEXT"),
    ("actual_vendor_shipping", "REAL"),
    ("shipping_shortfall", "REAL NOT NULL DEFAULT 0"),
    ("shipping_flag", "TEXT NOT NULL DEFAULT ''"),
)


def ensure_fine_fabrics_schema(conn=None) -> None:
    own = conn is None
    if own:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        conn.executescript(SCHEMA_SQL)
        _ensure_columns(conn, "ff_products", PRODUCT_EXTRA_COLUMNS)
        _ensure_columns(conn, "ff_orders", ORDER_EXTRA_COLUMNS)
        _ensure_columns(conn, "ff_sample_requests", SAMPLE_EXTRA_COLUMNS)
        _seed_vendors(conn)
        _align_visible_brands(conn)
        _seed_shipping_rules(conn)
    finally:
        if own:
            ctx.__exit__(None, None, None)


def _ensure_columns(conn, table: str, columns: tuple[tuple[str, str], ...]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, decl in columns:
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def _seed_shipping_rules(conn) -> None:
    for row in conn.execute("SELECT id FROM ff_vendors").fetchall():
        vid = row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]
        found = conn.execute("SELECT vendor_id FROM ff_shipping_rules WHERE vendor_id = ?", (vid,)).fetchone()
        if found:
            continue
        conn.execute(
            """INSERT INTO ff_shipping_rules
               (vendor_id, ship_per_yard, ship_per_sample, ship_minimum, handling_fee)
               VALUES (?, ?, ?, ?, ?)""",
            (
                vid,
                DEFAULT_SHIPPING["ship_per_yard"],
                DEFAULT_SHIPPING["ship_per_sample"],
                DEFAULT_SHIPPING["ship_minimum"],
                DEFAULT_SHIPPING["handling_fee"],
            ),
        )


def _seed_vendors(conn) -> None:
    for vendor in SEED_VENDORS:
        existing = conn.execute(
            "SELECT id FROM ff_vendors WHERE slug = ?", (vendor["slug"],)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """INSERT INTO ff_vendors
               (slug, name, online_sale_allowed, brand_display_allowed, default_markup, business)
               VALUES (?, ?, ?, ?, ?, 'workroom')""",
            (
                vendor["slug"],
                vendor["name"],
                vendor["online_sale_allowed"],
                vendor["brand_display_allowed"],
                vendor["default_markup"],
            ),
        )


def _align_visible_brands(conn) -> None:
    """One-time flip of starter mills that were seeded hidden. Admin toggles after this persist."""
    found = conn.execute(
        "SELECT value FROM ff_meta WHERE key = 'rafael_visible_brands_v1'"
    ).fetchone()
    if found:
        return
    for vendor in SEED_VENDORS:
        conn.execute(
            """UPDATE ff_vendors
               SET online_sale_allowed = ?, brand_display_allowed = ?, updated_at=datetime('now')
               WHERE slug = ?""",
            (vendor["online_sale_allowed"], vendor["brand_display_allowed"], vendor["slug"]),
        )
    conn.execute(
        "INSERT INTO ff_meta (key, value) VALUES ('rafael_visible_brands_v1', '1')"
    )


def normalize_vendor_slug(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "").replace("bros", "").replace("fabrics", "")


def vendor_aliases() -> dict[str, str]:
    aliases = {}
    for vendor in SEED_VENDORS:
        aliases[vendor["slug"]] = vendor["slug"]
        aliases[vendor["name"].lower()] = vendor["slug"]
    aliases["charlotte fabrics"] = "charlotte"
    aliases["greenhouse fabrics"] = "greenhouse"
    aliases["keyston bros"] = "keyston"
    aliases["keyston brothers"] = "keyston"
    return aliases


def resolve_vendor_slug(raw: str, extra: Iterable[str] = ()) -> str:
    key = (raw or "").strip().lower()
    aliases = vendor_aliases()
    if key in aliases:
        return aliases[key]
    compact = normalize_vendor_slug(key)
    if compact in aliases:
        return aliases[compact]
    for slug in extra:
        if slug and slug.lower() == compact:
            return slug
    return compact
