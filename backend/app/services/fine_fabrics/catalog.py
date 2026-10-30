"""Customer-safe catalog views and retail pricing."""

from __future__ import annotations

from typing import Any, Optional

from app.db.database import dict_row, dict_rows, get_db
from app.services.fine_fabrics.schema import CATEGORIES, ensure_fine_fabrics_schema

OWNER_ONLY_FIELDS = (
    "net_price",
    "list_price",
    "product_url",
    "vendor_id",
    "vendor_slug",
    "vendor_name",
    "notes",
)

CUSTOMER_FIELDS = (
    "id",
    "pattern",
    "color",
    "empire_code",
    "category",
    "width",
    "content",
    "repeat",
    "durability",
    "care",
    "price_per_yard",
    "image_url",
    "has_owner_photo",
)


def markup_for(vendor: dict, category: str, conn=None) -> float:
    def _lookup(c) -> float:
        row = c.execute(
            "SELECT markup FROM ff_markups WHERE vendor_id = ? AND category = ?",
            (vendor["id"], category),
        ).fetchone()
        if row:
            return float(row["markup"] if isinstance(row, dict) else row[0])
        return float(vendor.get("default_markup") or 2.0)

    if conn is not None:
        return _lookup(conn)
    with get_db() as c:
        return _lookup(c)


def retail_price(net_price: float, markup: float) -> float:
    return round(float(net_price) * float(markup), 2)


def customer_product(row: dict, vendor: dict | None = None, conn=None) -> dict:
    """Public card. Cost and supplier never leave unless brand_display_allowed."""
    vendor = vendor or _vendor_for(row, conn)
    price = retail_price(row.get("net_price") or 0, markup_for(vendor, row.get("category") or "Other", conn))
    image_path = (row.get("image_path") or "").strip()
    payload = {
        "id": row["id"],
        "pattern": row.get("pattern") or "",
        "color": row.get("color") or "",
        "empire_code": row.get("empire_code") or "",
        "category": row.get("category") or "Other",
        "width": row.get("width") or "",
        "content": row.get("content") or "",
        "repeat": row.get("repeat") or "",
        "durability": row.get("durability") or "",
        "care": row.get("care") or "",
        "price_per_yard": price,
        "image_url": f"/api/v1/fine-fabrics/photos/{row['id']}" if image_path else None,
        "has_owner_photo": bool(image_path),
        "placeholder": not bool(image_path),
    }
    if vendor and int(vendor.get("brand_display_allowed") or 0):
        payload["brand"] = vendor.get("name")
    return payload


def owner_product(row: dict, vendor: dict | None = None, conn=None) -> dict:
    vendor = vendor or _vendor_for(row, conn)
    public = customer_product(row, vendor, conn)
    public.update(
        {
            "sku": row.get("sku"),
            "net_price": row.get("net_price"),
            "list_price": row.get("list_price"),
            "product_url": row.get("product_url"),
            "notes": row.get("notes"),
            "vendor_slug": vendor.get("slug") if vendor else row.get("vendor_slug"),
            "vendor_name": vendor.get("name") if vendor else None,
            "online_sale_allowed": bool(vendor.get("online_sale_allowed")) if vendor else False,
            "brand_display_allowed": bool(vendor.get("brand_display_allowed")) if vendor else False,
            "markup": markup_for(vendor, row.get("category") or "Other", conn) if vendor else None,
            "image_path": row.get("image_path"),
        }
    )
    return public


def _vendor_for(row: dict, conn=None) -> dict:
    vid = row.get("vendor_id")
    if conn is not None:
        found = conn.execute("SELECT * FROM ff_vendors WHERE id = ?", (vid,)).fetchone()
        return dict_row(found) if found else {}
    with get_db() as c:
        found = c.execute("SELECT * FROM ff_vendors WHERE id = ?", (vid,)).fetchone()
        return dict_row(found) if found else {}


def list_catalog(
    category: Optional[str] = None,
    search: Optional[str] = None,
    *,
    include_hidden: bool = False,
    owner: bool = False,
) -> list[dict]:
    ensure_fine_fabrics_schema()
    with get_db() as conn:
        sql = """
            SELECT p.*, v.slug AS vendor_slug, v.name AS vendor_name,
                   v.online_sale_allowed, v.brand_display_allowed, v.default_markup
            FROM ff_products p
            JOIN ff_vendors v ON v.id = p.vendor_id
            WHERE p.is_active = 1
        """
        params: list[Any] = []
        if not include_hidden:
            sql += " AND v.online_sale_allowed = 1"
        if category:
            sql += " AND p.category = ?"
            params.append(category)
        if search:
            sql += " AND (p.pattern LIKE ? OR p.color LIKE ? OR p.empire_code LIKE ? OR p.sku LIKE ?)"
            needle = f"%{search}%"
            params.extend([needle, needle, needle, needle])
        sql += " ORDER BY p.category, p.pattern, p.color"
        rows = dict_rows(conn.execute(sql, params).fetchall())
        out = []
        for row in rows:
            vendor = {
                "id": row["vendor_id"],
                "slug": row["vendor_slug"],
                "name": row["vendor_name"],
                "online_sale_allowed": row["online_sale_allowed"],
                "brand_display_allowed": row["brand_display_allowed"],
                "default_markup": row["default_markup"],
            }
            out.append(owner_product(row, vendor, conn) if owner else customer_product(row, vendor, conn))
        return out


def get_product(product_id: int, *, owner: bool = False, allow_hidden: bool = False) -> dict | None:
    ensure_fine_fabrics_schema()
    with get_db() as conn:
        row = conn.execute(
            """SELECT p.*, v.slug AS vendor_slug, v.name AS vendor_name,
                      v.online_sale_allowed, v.brand_display_allowed, v.default_markup
               FROM ff_products p
               JOIN ff_vendors v ON v.id = p.vendor_id
               WHERE p.id = ? AND p.is_active = 1""",
            (product_id,),
        ).fetchone()
        if not row:
            return None
        row = dict_row(row)
        if not allow_hidden and not int(row.get("online_sale_allowed") or 0):
            return None
        vendor = {
            "id": row["vendor_id"],
            "slug": row["vendor_slug"],
            "name": row["vendor_name"],
            "online_sale_allowed": row["online_sale_allowed"],
            "brand_display_allowed": row["brand_display_allowed"],
            "default_markup": row["default_markup"],
        }
        return owner_product(row, vendor, conn) if owner else customer_product(row, vendor, conn)


def list_vendors() -> list[dict]:
    ensure_fine_fabrics_schema()
    with get_db() as conn:
        vendors = dict_rows(conn.execute("SELECT * FROM ff_vendors ORDER BY name").fetchall())
        for vendor in vendors:
            marks = dict_rows(
                conn.execute(
                    "SELECT category, markup FROM ff_markups WHERE vendor_id = ?",
                    (vendor["id"],),
                ).fetchall()
            )
            vendor["markups"] = {m["category"]: m["markup"] for m in marks}
            vendor["online_sale_allowed"] = bool(vendor["online_sale_allowed"])
            vendor["brand_display_allowed"] = bool(vendor["brand_display_allowed"])
        return vendors


def leaks_cost_or_vendor(payload: Any) -> list[str]:
    """Return field names that must never appear on a customer page."""
    banned = []
    if isinstance(payload, dict):
        items = [payload]
    elif isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict)]
    else:
        return banned
    for item in items:
        for key in OWNER_ONLY_FIELDS:
            if key in item:
                banned.append(key)
        for key, value in item.items():
            if key in ("brand",):
                continue
            text = str(value).lower() if value is not None else ""
            if any(word in text for word in ("net_price", "cost_per", "supplier")):
                banned.append(key)
    return sorted(set(banned))
