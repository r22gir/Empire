"""Sprint M fabric intake.

Depends on PR #128 (`docs/FABRIC_CODES.csv` + `app.services.fabric_codes`)
when that branch is present. This module does not copy that registry.

Contract (same either way):
- Codes are sequential and never reused. V001–V007 are already taken.
- Next vinyl assignment is V008.
- 'Kravet V639 Navy Velvet' must NOT become V639 (that is the supplier SKU).
- Client-facing fields: code + color only. Never brand, supplier, or SKU.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

CODE_RE = re.compile(r"^([VFL])(\d{3,})-(.+)$")

# V001–V007 reserved by the shared registry (PR #128). Never reallocate.
RESERVED_VINYL = 7

PREFIX_BY_TYPE = {"vinyl": "V", "fabric": "F", "leather": "L", "v": "V", "f": "F", "l": "L"}
TYPE_BY_PREFIX = {"V": "vinyl", "F": "fabric", "L": "leather"}

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

SKU_TOKEN_RE = re.compile(r"\b([VFL])(\d{3,})\b", re.IGNORECASE)

LOCAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS sm_fabric_codes (
    code TEXT NOT NULL PRIMARY KEY,
    prefix TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    color TEXT NOT NULL,
    material_type TEXT NOT NULL,
    brand TEXT,
    supplier_sku TEXT,
    retired INTEGER NOT NULL DEFAULT 0,
    UNIQUE(prefix, sequence)
);
"""


class FabricCodeError(ValueError):
    """Raised when a fabric value cannot be reduced to a registry code."""


def _shared():
    """PR #128 registry, if that PR is on the tree. Never required here."""
    try:
        from app.services import fabric_codes as fc

        return fc
    except ImportError:
        return None


def normalize_color(color: str) -> str:
    raw = (color or "").strip()
    if not raw:
        raise FabricCodeError("color is required")
    parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", raw)
    if not parts:
        parts = re.split(r"[^A-Za-z0-9]+", raw)
    cleaned = "".join(p[:1].upper() + p[1:].lower() for p in parts if p)
    if not cleaned:
        raise FabricCodeError(f"color {color!r} is empty after normalize")
    return cleaned


def infer_material_type(raw: str | None, explicit: str | None = None) -> str:
    if explicit:
        key = str(explicit).strip().lower()
        if key in MATERIAL_HINTS:
            return MATERIAL_HINTS[key]
        if key in PREFIX_BY_TYPE:
            return TYPE_BY_PREFIX[PREFIX_BY_TYPE[key]]
    text = (raw or "").lower()
    for hint, material in MATERIAL_HINTS.items():
        if re.search(rf"\b{re.escape(hint)}\b", text):
            return material
    return "vinyl"


def parse_intake(raw: str) -> dict[str, str]:
    text = re.sub(r"[|/]+", " ", str(raw or "")).strip()
    brand = ""
    supplier_sku = ""
    lowered = text.lower()
    for token in FORBIDDEN_BRAND_TOKENS:
        if len(token) > 2 and re.search(rf"\b{re.escape(token)}\b", lowered):
            if not brand:
                brand = token.title()
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
    return {
        "color": " ".join(parts) or "Unspecified",
        "brand": brand,
        "supplier_sku": supplier_sku,
    }


def strip_client_facing(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    for token in FORBIDDEN_BRAND_TOKENS:
        if len(token) > 2:
            text = re.sub(rf"\b{re.escape(token)}\b", " ", text, flags=re.IGNORECASE)
    text = SKU_TOKEN_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def seed_reserved_codes(conn: sqlite3.Connection) -> None:
    """Mark V001–V007 consumed so the next vinyl code is V008. Never reuse."""
    conn.executescript(LOCAL_SCHEMA)
    for seq in range(1, RESERVED_VINYL + 1):
        conn.execute(
            """INSERT OR IGNORE INTO sm_fabric_codes
               (code, prefix, sequence, color, material_type, retired)
               VALUES (?, 'V', ?, 'Assigned', 'vinyl', 0)""",
            (f"V{seq:03d}-Assigned", seq),
        )


def ensure_shared_registry(conn: sqlite3.Connection) -> None:
    fc = _shared()
    if fc is not None:
        fc.ensure_registry(conn)
        csv_path = getattr(fc, "DEFAULT_CSV", None)
        if csv_path is not None and getattr(csv_path, "exists", lambda: False)():
            fc.import_csv(conn, path=csv_path)
            return
    seed_reserved_codes(conn)


def _registry_table(conn: sqlite3.Connection) -> str:
    names = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    if "fabric_code_registry" in names:
        return "fabric_code_registry"
    seed_reserved_codes(conn)
    return "sm_fabric_codes"


def highest_sequence(conn: sqlite3.Connection, prefix: str) -> int:
    table = _registry_table(conn)
    row = conn.execute(f"SELECT MAX(sequence) FROM {table} WHERE prefix = ?", (prefix,)).fetchone()
    return int(row[0] or 0)


def next_sequence(conn: sqlite3.Connection, prefix: str) -> int:
    return highest_sequence(conn, prefix) + 1


def _existing_by_sku(conn: sqlite3.Connection, sku: str) -> dict | None:
    if not sku:
        return None
    table = _registry_table(conn)
    row = conn.execute(
        f"SELECT * FROM {table} WHERE upper(supplier_sku) = upper(?) AND retired = 0",
        (sku,),
    ).fetchone()
    return dict(row) if row else None


def _existing_by_color(conn: sqlite3.Connection, color: str, material_type: str) -> dict | None:
    if not color or color.lower() in {"assigned", "unspecified"}:
        return None
    table = _registry_table(conn)
    row = conn.execute(
        f"""SELECT * FROM {table}
           WHERE color = ? AND material_type = ? AND retired = 0
           ORDER BY sequence ASC LIMIT 1""",
        (color, material_type),
    ).fetchone()
    return dict(row) if row else None


def _client_view(row: dict) -> dict:
    return {
        "code": row.get("code"),
        "color": row.get("color"),
        "material_type": row.get("material_type"),
    }


def _assign_local(
    conn: sqlite3.Connection,
    *,
    color: str,
    material_type: str,
    brand: str | None,
    supplier_sku: str | None,
) -> dict:
    seed_reserved_codes(conn)
    prefix = PREFIX_BY_TYPE[material_type]
    color_n = normalize_color(color)
    seq = next_sequence(conn, prefix)
    code = f"{prefix}{seq:03d}-{color_n}"
    conn.execute(
        """INSERT INTO sm_fabric_codes
           (code, prefix, sequence, color, material_type, brand, supplier_sku, retired)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
        (code, prefix, seq, color_n, TYPE_BY_PREFIX[prefix], brand, supplier_sku),
    )
    return {"code": code, "color": color_n, "material_type": TYPE_BY_PREFIX[prefix]}


def lookup_or_assign(
    raw: str | None,
    *,
    conn: sqlite3.Connection,
    material_type: str | None = None,
    required: bool = False,
) -> dict | None:
    if raw is None or not str(raw).strip():
        if required:
            raise FabricCodeError("fabric code is required")
        return None

    text = str(raw).strip()
    ensure_shared_registry(conn)
    fc = _shared()

    if CODE_RE.match(text) and fc is not None:
        try:
            return fc.get_code(conn, text, internal=False)
        except Exception:
            pass

    parsed = parse_intake(text)
    kind = infer_material_type(text, material_type)
    found = _existing_by_sku(conn, parsed["supplier_sku"]) or _existing_by_color(
        conn, normalize_color(parsed["color"]), kind
    )
    if found:
        return _client_view(found)

    if fc is not None and _registry_table(conn) == "fabric_code_registry":
        assigned = fc.assign_code(
            conn,
            color=parsed["color"],
            material_type=kind,
            brand=parsed.get("brand") or None,
            supplier_sku=parsed.get("supplier_sku") or None,
            notes="Assigned on Sprint M intake; supplier SKU stored internally only",
        )
        # Keep brand/SKU on the local internal table. Client views never read it.
        seed_reserved_codes(conn)
        prefix, seq, color_n = fc.parse_code(assigned["code"])
        conn.execute(
            """INSERT OR IGNORE INTO sm_fabric_codes
               (code, prefix, sequence, color, material_type, brand, supplier_sku, retired)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                assigned["code"],
                prefix,
                seq,
                assigned.get("color") or color_n,
                assigned.get("material_type") or kind,
                parsed.get("brand") or None,
                parsed.get("supplier_sku") or None,
            ),
        )
        return _client_view(assigned)

    return _assign_local(
        conn,
        color=parsed["color"],
        material_type=kind,
        brand=parsed.get("brand") or None,
        supplier_sku=parsed.get("supplier_sku") or None,
    )


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
        if not row or not row.get("code"):
            if required:
                raise FabricCodeError("fabric code is required")
            return None
        code = str(row["code"])
        if any(token in code.lower() for token in FORBIDDEN_BRAND_TOKENS if len(token) > 3):
            raise FabricCodeError("sanitized fabric code still contained a brand or supplier token")
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
        table = _registry_table(opened)
        row = opened.execute(f"SELECT 1 FROM {table} WHERE code = ?", (value.strip(),)).fetchone()
        return bool(row)
    finally:
        if owns:
            opened.close()
