"""Bulk CSV importer. No hand entry — this is the only catalog write path.

Supports three layouts, detected from headers / filename / notes:

- canonical Empire columns
- Greenhouse mill file (sku + name_color + net_price_per_yd)
- Charlotte book/collection file (pattern = book, color often blank,
  notes hold unit: yard / sq ft / roll / box)
"""

from __future__ import annotations

import csv
import io
import os
import re
from pathlib import Path
from typing import Iterable

from app.db.database import dict_row, get_db
from app.services.fine_fabrics.codes import allocate_empire_code
from app.services.fine_fabrics.schema import (
    CATEGORIES,
    UNSORTED_CATEGORY,
    UNITS,
    ensure_fine_fabrics_schema,
    resolve_vendor_slug,
)

CANONICAL_COLUMNS = (
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
GREENHOUSE_COLUMNS = (
    "sku",
    "name_color",
    "category",
    "width",
    "content",
    "repeat",
    "color_family",
    "net_price_per_yd",
    "list_price",
)

_UNIT_RE = re.compile(
    r"unit\s+per\s+(yd|yard|yards|sq\s*ft|sqft|square\s*foot|roll|box)",
    re.I,
)


def data_dir() -> Path:
    raw = os.getenv("FINE_FABRICS_DATA_DIR")
    if raw:
        return Path(raw)
    return Path(os.getenv("EMPIRE_TASK_DB", ".")).resolve().parent / "fine_fabrics_vendor"


def _norm_header(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def _parse_money(value) -> float | None:
    if value in (None, ""):
        return None
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    return float(cleaned)


def _normalize_category(value: str) -> tuple[str, int]:
    raw = (value or "").strip()
    if not raw:
        return UNSORTED_CATEGORY, 1
    key = raw.lower()
    aliases = {
        "upholstery": "Upholstery",
        "drapery": "Drapery",
        "drape": "Drapery",
        "curtain": "Drapery",
        "outdoor": "Outdoor",
        "sunbrella": "Outdoor",
        "other": "Other",
        "multipurpose": "Other",
        "unsorted": UNSORTED_CATEGORY,
    }
    if raw in CATEGORIES or raw == UNSORTED_CATEGORY:
        return raw, 0 if raw != UNSORTED_CATEGORY else 1
    mapped = aliases.get(key)
    if mapped == UNSORTED_CATEGORY:
        return UNSORTED_CATEGORY, 1
    if mapped:
        return mapped, 0
    return UNSORTED_CATEGORY, 1


def parse_unit(notes: str, explicit: str = "") -> str:
    if explicit and explicit in UNITS:
        return explicit
    match = _UNIT_RE.search(notes or "")
    if not match:
        return "yard"
    token = re.sub(r"\s+", "", match.group(1).lower())
    if token in ("yd", "yard", "yards"):
        return "yard"
    if token in ("sqft", "squarefoot"):
        return "sq_ft"
    if token == "roll":
        return "roll"
    if token == "box":
        return "box"
    return "yard"


def split_greenhouse_name(sku: str, name_color: str) -> tuple[str, str]:
    """'S8090 BRINDLE' + sku S8090 → pattern=S8090, color=BRINDLE."""
    sku = (sku or "").strip()
    text = (name_color or "").strip()
    if sku and text.upper().startswith(sku.upper()):
        return sku, text[len(sku):].strip()
    parts = text.split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return sku or text, ""


def detect_format(headers: list[str], rows: list[dict] | None = None, filename: str | None = None) -> str:
    name = (filename or "").lower()
    if "greenhouse" in name:
        return "greenhouse"
    if "charlotte" in name:
        return "charlotte"
    header_set = set(headers)
    if "name_color" in header_set and "net_price_per_yd" in header_set:
        return "greenhouse"
    if set(CANONICAL_COLUMNS).issubset(header_set):
        if rows and any(_looks_charlotte(r) for r in rows):
            return "charlotte"
        return "canonical"
    missing_g = [c for c in GREENHOUSE_COLUMNS if c not in header_set]
    missing_c = [c for c in CANONICAL_COLUMNS if c not in header_set]
    raise ValueError(
        "CSV is not a known Fine Fabrics layout. "
        f"Greenhouse missing {missing_g or 'none'}; canonical/Charlotte missing {missing_c or 'none'}"
    )


def _looks_charlotte(row: dict) -> bool:
    vendor = (row.get("vendor") or "").lower()
    notes = (row.get("notes") or "").lower()
    if "charlotte" in vendor:
        return True
    if "collection-level" in notes or "book/collection" in notes:
        return True
    if "unit per" in notes and not (row.get("color") or "").strip():
        return True
    return False


def _read_raw_rows(text: str) -> tuple[list[str], list[dict]]:
    sample = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(sample))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")
    headers = [_norm_header(h) for h in reader.fieldnames]
    rows = []
    for raw in reader:
        row = {_norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
        if not any(row.values()):
            continue
        rows.append(row)
    return headers, rows


def map_greenhouse_row(raw: dict, vendor_hint: str | None = None) -> dict:
    sku = (raw.get("sku") or "").strip()
    pattern, color = split_greenhouse_name(sku, raw.get("name_color") or "")
    return {
        "vendor": vendor_hint or "Greenhouse",
        "pattern": pattern,
        "color": color,
        "sku": sku,
        "category": raw.get("category") or "",
        "width": raw.get("width") or "",
        "content": raw.get("content") or "",
        "repeat": raw.get("repeat") or "",
        "net_price": raw.get("net_price_per_yd") or raw.get("net_price"),
        "list_price": raw.get("list_price"),
        "product_url": raw.get("product_url") or "",
        "notes": raw.get("notes") or "",
        "durability": raw.get("durability") or "",
        "care": raw.get("care") or "",
        "color_family": raw.get("color_family") or "",
        "product_type": "sku",
        "unit": "yard",
    }


def map_charlotte_row(raw: dict, vendor_hint: str | None = None) -> dict:
    notes = raw.get("notes") or ""
    sku = (raw.get("sku") or "").strip()
    return {
        "vendor": vendor_hint or raw.get("vendor") or "Charlotte",
        "pattern": (raw.get("pattern") or "").strip(),
        "color": (raw.get("color") or "").strip(),
        "sku": sku,
        "category": raw.get("category") or "",
        "width": raw.get("width") or "",
        "content": raw.get("content") or "",
        "repeat": raw.get("repeat") or "",
        "net_price": raw.get("net_price"),
        "list_price": raw.get("list_price"),
        "product_url": raw.get("product_url") or "",
        "notes": notes,
        "durability": raw.get("durability") or "",
        "care": raw.get("care") or "",
        "color_family": raw.get("color_family") or "",
        "product_type": "collection",
        "unit": parse_unit(notes, raw.get("unit") or ""),
        "sku_range": sku,
    }


def map_canonical_row(raw: dict, vendor_hint: str | None = None) -> dict:
    notes = raw.get("notes") or ""
    mapped = {
        "vendor": vendor_hint or raw.get("vendor") or "",
        "pattern": (raw.get("pattern") or "").strip(),
        "color": (raw.get("color") or "").strip(),
        "sku": (raw.get("sku") or "").strip(),
        "category": raw.get("category") or "",
        "width": raw.get("width") or "",
        "content": raw.get("content") or "",
        "repeat": raw.get("repeat") or "",
        "net_price": raw.get("net_price"),
        "list_price": raw.get("list_price"),
        "product_url": raw.get("product_url") or "",
        "notes": notes,
        "durability": raw.get("durability") or "",
        "care": raw.get("care") or "",
        "color_family": raw.get("color_family") or "",
        "product_type": (raw.get("product_type") or "sku").strip() or "sku",
        "unit": parse_unit(notes, raw.get("unit") or ""),
        "sku_range": raw.get("sku_range") or "",
    }
    if _looks_charlotte(mapped):
        mapped["product_type"] = "collection"
        mapped["sku_range"] = mapped["sku"]
    return mapped


def parse_csv(text: str, *, filename: str | None = None, vendor_hint: str | None = None) -> tuple[str, list[dict]]:
    headers, raw_rows = _read_raw_rows(text)
    fmt = detect_format(headers, raw_rows, filename)
    mapper = {
        "greenhouse": map_greenhouse_row,
        "charlotte": map_charlotte_row,
        "canonical": map_canonical_row,
    }[fmt]
    return fmt, [mapper(row, vendor_hint) for row in raw_rows]


def import_rows(rows: Iterable[dict], *, conn=None) -> dict:
    ensure_fine_fabrics_schema(conn)
    own = conn is None
    if own:
        ctx = get_db()
        conn = ctx.__enter__()
    created = 0
    updated = 0
    unsorted = 0
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
                product_type = (raw.get("product_type") or "sku").strip() or "sku"
                if not pattern:
                    skipped.append({"row": index, "reason": "pattern is required"})
                    continue
                if product_type != "collection" and not color:
                    skipped.append({"row": index, "reason": "pattern and color are required"})
                    continue
                net_price = _parse_money(raw.get("net_price"))
                if net_price is None:
                    skipped.append({"row": index, "reason": "net_price is required"})
                    continue
                category, is_unsorted = _normalize_category(raw.get("category") or "")
                sku = (raw.get("sku") or "").strip() or None
                unit = raw.get("unit") if raw.get("unit") in UNITS else parse_unit(raw.get("notes") or "")
                color_family = (raw.get("color_family") or "").strip()
                sku_range = (raw.get("sku_range") or sku or "").strip()
                found = conn.execute(
                    """SELECT id, empire_code FROM ff_products
                       WHERE vendor_id = ? AND IFNULL(sku, '') = ? AND pattern = ? AND color = ?""",
                    (vendor["id"], sku or "", pattern, color),
                ).fetchone()
                code_color = color or (sku or "Book")
                if found:
                    empire_code = found["empire_code"]
                else:
                    empire_code = allocate_empire_code(
                        category if category != UNSORTED_CATEGORY else "Other",
                        code_color,
                        sku=sku,
                        existing_codes=existing_codes,
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
                    product_type,
                    unit,
                    color_family,
                    is_unsorted,
                    sku_range,
                )
                if found:
                    conn.execute(
                        """UPDATE ff_products SET
                           vendor_id=?, vendor_slug=?, pattern=?, color=?, sku=?, category=?,
                           width=?, content=?, repeat=?, durability=?, care=?,
                           net_price=?, list_price=?, product_url=?, notes=?, empire_code=?,
                           product_type=?, unit=?, color_family=?, is_unsorted=?, sku_range=?,
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
                            net_price, list_price, product_url, notes, empire_code,
                            product_type, unit, color_family, is_unsorted, sku_range, business)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'workroom')""",
                        values,
                    )
                    created += 1
                if is_unsorted:
                    unsorted += 1
            except Exception as exc:
                skipped.append({"row": index, "reason": str(exc)})
        return {
            "created": created,
            "updated": updated,
            "unsorted": unsorted,
            "skipped": skipped,
            "rows_read": created + updated + len(skipped),
        }
    finally:
        if own:
            ctx.__exit__(None, None, None)


def import_csv_text(text: str, *, filename: str | None = None, vendor_hint: str | None = None) -> dict:
    fmt, rows = parse_csv(text, filename=filename, vendor_hint=vendor_hint)
    result = import_rows(rows)
    result["format"] = fmt
    return result


def list_import_files(directory: Path | None = None) -> list[dict]:
    root = directory or data_dir()
    root.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(root.glob("*.csv")):
        files.append({"name": path.name, "bytes": path.stat().st_size, "path": str(path)})
    return files


def import_from_dir(directory: Path | None = None, filename: str | None = None) -> dict:
    root = directory or data_dir()
    if filename:
        path = (root / Path(filename).name).resolve()
        if path.parent != root.resolve():
            raise ValueError("Import path escapes the data directory")
        if not path.is_file():
            raise FileNotFoundError(filename)
        targets = [path]
    else:
        targets = sorted(root.glob("*.csv"))
    reports = []
    for path in targets:
        text = path.read_text(encoding="utf-8-sig")
        report = import_csv_text(text, filename=path.name)
        report["file"] = path.name
        reports.append(report)
    return {"directory": str(root), "files": reports}
