"""Bulk CSV importer. No hand entry — this is the only catalog write path."""

from __future__ import annotations

import csv
import io
from typing import Iterable

from app.db.database import dict_row, get_db
from app.services.fine_fabrics.codes import allocate_empire_code
from app.services.fine_fabrics.schema import CATEGORIES, ensure_fine_fabrics_schema, resolve_vendor_slug

REQUIRED_COLUMNS = (
    "vendor",
    "pattern",
    "color",
    "sku",
    "category",
    "width",
    "content",
    "repeat",
    "net_price",
    "list_price",
    "product_url",
    "notes",
)
OPTIONAL_COLUMNS = ("durability", "care")


def _norm_header(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def parse_csv(text: str) -> list[dict]:
    sample = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(sample))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")
    headers = [_norm_header(h) for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(missing)}")
    rows = []
    for raw in reader:
        row = {_norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
        if not any(row.values()):
            continue
        rows.append(row)
    return rows


def _parse_money(value) -> float | None:
    if value in (None, ""):
        return None
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    return float(cleaned)


def _normalize_category(value: str) -> str:
    key = (value or "").strip().lower()
    aliases = {
        "upholstery": "Upholstery",
        "drapery": "Drapery",
        "drape": "Drapery",
        "curtain": "Drapery",
        "outdoor": "Outdoor",
        "sunbrella": "Outdoor",
        "other": "Other",
        "multipurpose": "Other",
    }
    if value in CATEGORIES:
        return value
    return aliases.get(key, "Other")


def import_rows(rows: Iterable[dict], *, conn=None) -> dict:
    ensure_fine_fabrics_schema(conn)
    own = conn is None
    if own:
        ctx = get_db()
        conn = ctx.__enter__()
    created = 0
    updated = 0
    skipped = []
    try:
        vendors = {
            r["slug"]: dict_row(r)
            for r in conn.execute("SELECT * FROM ff_vendors").fetchall()
        }
        existing_codes = {
            r[0] for r in conn.execute("SELECT empire_code FROM ff_products").fetchall() if r[0]
        }
        for index, raw in enumerate(rows, start=2):
            try:
                vendor_slug = resolve_vendor_slug(raw.get("vendor") or "", vendors.keys())
                vendor = vendors.get(vendor_slug)
                if not vendor:
                    skipped.append({"row": index, "reason": f"unknown vendor '{raw.get('vendor')}'"})
                    continue
                pattern = (raw.get("pattern") or "").strip()
                color = (raw.get("color") or "").strip()
                if not pattern or not color:
                    skipped.append({"row": index, "reason": "pattern and color are required"})
                    continue
                net_price = _parse_money(raw.get("net_price"))
                if net_price is None:
                    skipped.append({"row": index, "reason": "net_price is required"})
                    continue
                category = _normalize_category(raw.get("category") or "")
                sku = (raw.get("sku") or "").strip() or None
                found = conn.execute(
                    """SELECT id, empire_code FROM ff_products
                       WHERE vendor_id = ? AND IFNULL(sku, '') = ? AND pattern = ? AND color = ?""",
                    (vendor["id"], sku or "", pattern, color),
                ).fetchone()
                if found:
                    empire_code = found["empire_code"]
                else:
                    empire_code = allocate_empire_code(
                        category, color, sku=sku, existing_codes=existing_codes
                    )
                    existing_codes.add(empire_code)
                values = (
                    vendor["id"],
                    vendor["slug"],
                    pattern,
                    color,
                    sku,
                    category,
                    (raw.get("width") or "").strip(),
                    (raw.get("content") or "").strip(),
                    (raw.get("repeat") or "").strip(),
                    (raw.get("durability") or "").strip(),
                    (raw.get("care") or "").strip(),
                    net_price,
                    _parse_money(raw.get("list_price")),
                    (raw.get("product_url") or "").strip(),
                    (raw.get("notes") or "").strip(),
                    empire_code,
                )
                if found:
                    conn.execute(
                        """UPDATE ff_products SET
                           vendor_id=?, vendor_slug=?, pattern=?, color=?, sku=?, category=?,
                           width=?, content=?, repeat=?, durability=?, care=?,
                           net_price=?, list_price=?, product_url=?, notes=?, empire_code=?,
                           updated_at=datetime('now')
                           WHERE id=?""",
                        values + (found["id"],),
                    )
                    updated += 1
                else:
                    conn.execute(
                        """INSERT INTO ff_products
                           (vendor_id, vendor_slug, pattern, color, sku, category,
                            width, content, repeat, durability, care,
                            net_price, list_price, product_url, notes, empire_code, business)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'workroom')""",
                        values,
                    )
                    created += 1
            except Exception as exc:
                skipped.append({"row": index, "reason": str(exc)})
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "rows_read": created + updated + len(skipped),
        }
    finally:
        if own:
            ctx.__exit__(None, None, None)


def import_csv_text(text: str) -> dict:
    return import_rows(parse_csv(text))
