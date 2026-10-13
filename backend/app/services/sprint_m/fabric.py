"""Intake fabric codes from the shared sequential registry.

Source of truth: docs/FABRIC_CODES.csv (PR #128).
V001–V007 are reserved. The next vinyl code is V008. Sequences are never reused.

'Kravet V639 Navy Velvet' must NOT become V639 — that is the supplier SKU.
On intake we look up the material or assign the next registry code.
Client-facing fields expose code + color only. Brand, supplier, and SKU stay internal.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from app.services.fabric_codes import (
    CODE_RE,
    DEFAULT_CSV,
    FabricCodeError,
    assign_code,
    client_view,
    ensure_registry,
    get_code,
    import_csv,
    normalize_color,
)

# Words that must never appear in a client-facing fabric field.
FORBIDDEN_BRAND_TOKENS = {
    "kravet",
    "fabricut",
    "schumacher",
    "brunschwig",
    "lee",
    "jofa",
    "pindler",
    "osborne",
    "little",
    "supplier",
    "wholesaler",
    "vendor",
    "robert",
    "allen",
    "designers",
    "guild",
    "www",
    "http",
    "https",
    ".com",
    "inc",
    "llc",
    "wholesale",
    "retailer",
    "mill",
    "house",
    "collection",
}

COLOR_STOPWORDS = {
    "vinyl",
    "leather",
    "fabric",
    "velvet",
    "textile",
    "cloth",
    "marine",
    "grade",
    "wide",
    "yards",
    "yard",
    "drapery",
    "upholstery",
}

MATERIAL_HINTS = {
    "vinyl": "vinyl",
    "marine": "vinyl",
    "leather": "leather",
    "hide": "leather",
    "fabric": "fabric",
    "textile": "fabric",
    "cloth": "fabric",
    "linen": "fabric",
    "cotton": "fabric",
    "silk": "fabric",
    "wool": "fabric",
    "velvet": "vinyl",
}

# Supplier-looking tokens in incoming text. Never treat these as our codes.
SKU_TOKEN_RE = re.compile(r"\b([VFL])(\d{3,})\b", re.IGNORECASE)


def ensure_shared_registry(conn: sqlite3.Connection) -> None:
    """Load reserved V001–V007 (and any other CSV rows) without overwriting."""
    ensure_registry(conn)
    import_csv(conn, path=DEFAULT_CSV)


def infer_material_type(raw: str | None, explicit: str | None = None) -> str:
    if explicit:
        key = str(explicit).strip().lower()
        if key in MATERIAL_HINTS:
            return MATERIAL_HINTS[key]
        if key in ("vinyl", "fabric", "leather", "v", "f", "l"):
            return {"v": "vinyl", "f": "fabric", "l": "leather"}.get(key, key)
    text = (raw or "").lower()
    for hint, material in MATERIAL_HINTS.items():
        if re.search(rf"\b{re.escape(hint)}\b", text):
            return material
    # Workroom reserved series is V001–V007; untyped intake continues that series.
    return "vinyl"


def parse_intake(raw: str) -> dict[str, str]:
    """Split incoming material into internal-only brand/SKU and a client color."""
    text = re.sub(r"[|/]+", " ", str(raw or "")).strip()
    brand = ""
    supplier_sku = ""
    lowered = text.lower()
    for token in FORBIDDEN_BRAND_TOKENS:
        if len(token) > 2 and re.search(rf"\b{re.escape(token)}\b", lowered):
            brand = token.title() if not brand else brand
            text = re.sub(rf"\b{re.escape(token)}\b", " ", text, flags=re.IGNORECASE)

    sku_match = SKU_TOKEN_RE.search(text)
    if sku_match:
        supplier_sku = f"{sku_match.group(1).upper()}{sku_match.group(2)}"
        text = text[: sku_match.start()] + " " + text[sku_match.end() :]

    text = re.sub(r"[-–]+", " ", text)
    parts = [
        p
        for p in re.split(r"[^A-Za-z0-9]+", text)
        if p and p.lower() not in FORBIDDEN_BRAND_TOKENS and p.lower() not in COLOR_STOPWORDS
    ]
    color_src = " ".join(parts) or "Unspecified"
    return {
        "color": color_src,
        "brand": brand,
        "supplier_sku": supplier_sku,
    }


def strip_client_facing(value: Any) -> str:
    """Remove brand / supplier / SKU tokens from a client-visible string."""
    if value is None:
        return ""
    text = str(value)
    for token in FORBIDDEN_BRAND_TOKENS:
        if len(token) > 2:
            text = re.sub(rf"\b{re.escape(token)}\b", " ", text, flags=re.IGNORECASE)
    text = SKU_TOKEN_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _existing_by_sku(conn: sqlite3.Connection, sku: str) -> dict | None:
    if not sku:
        return None
    row = conn.execute(
        "SELECT * FROM fabric_code_registry WHERE upper(supplier_sku) = upper(?) AND retired = 0",
        (sku,),
    ).fetchone()
    return dict(row) if row else None


def _existing_by_color(conn: sqlite3.Connection, color: str, material_type: str) -> dict | None:
    if not color or color.lower() in {"assigned", "unspecified"}:
        return None
    row = conn.execute(
        """SELECT * FROM fabric_code_registry
           WHERE color = ? AND material_type = ? AND retired = 0
           ORDER BY sequence ASC LIMIT 1""",
        (color, material_type),
    ).fetchone()
    return dict(row) if row else None


def lookup_or_assign(
    raw: str | None,
    *,
    conn: sqlite3.Connection,
    material_type: str | None = None,
    required: bool = False,
) -> dict | None:
    """Look up a registry row or assign the next sequential code.

    Never returns a supplier SKU as the public code.
    """
    if raw is None or not str(raw).strip():
        if required:
            raise FabricCodeError("fabric code is required")
        return None

    text = str(raw).strip()
    ensure_shared_registry(conn)

    if CODE_RE.match(text):
        try:
            return get_code(conn, text, internal=False)
        except FabricCodeError:
            pass

    parsed = parse_intake(text)
    kind = infer_material_type(text, material_type)

    found = _existing_by_sku(conn, parsed["supplier_sku"]) or _existing_by_color(
        conn, normalize_color(parsed["color"]), kind
    )
    if found:
        return client_view(found)

    assigned = assign_code(
        conn,
        color=parsed["color"],
        material_type=kind,
        brand=parsed.get("brand") or None,
        supplier_sku=parsed.get("supplier_sku") or None,
        notes="Assigned on Sprint M intake; supplier SKU stored internally only",
    )
    return client_view(assigned)


def _open_registry_conn(conn: sqlite3.Connection | None) -> tuple[sqlite3.Connection, bool]:
    if conn is not None:
        ensure_shared_registry(conn)
        return conn, False
    from app.services.sprint_m.store import connect, init_store

    opened = connect()
    init_store(opened)
    return opened, True


def sanitize_fabric_code(
    raw: str | None,
    *,
    required: bool = False,
    conn: sqlite3.Connection | None = None,
    material_type: str | None = None,
) -> str | None:
    """Return a registry code such as V008-Navy. Never a brand or supplier SKU."""
    opened, owns = _open_registry_conn(conn)
    try:
        row = lookup_or_assign(raw, conn=opened, material_type=material_type, required=required)
        if not row:
            return None
        code = row.get("code")
        if not code:
            if required:
                raise FabricCodeError("fabric code is required")
            return None
        lowered = str(code).lower()
        if any(token in lowered for token in FORBIDDEN_BRAND_TOKENS if len(token) > 3):
            raise FabricCodeError("sanitized fabric code still contained a brand or supplier token")
        if SKU_TOKEN_RE.fullmatch(str(raw or "").strip()) and not CODE_RE.match(str(raw or "").strip()):
            pass
        return code
    finally:
        if owns:
            opened.commit()
            opened.close()


def is_internal_fabric_code(value: str | None, conn: sqlite3.Connection | None = None) -> bool:
    if not value or not CODE_RE.match(value.strip()):
        return False
    opened, owns = _open_registry_conn(conn)
    try:
        get_code(opened, value.strip(), internal=False)
        return True
    except FabricCodeError:
        return False
    finally:
        if owns:
            opened.close()
