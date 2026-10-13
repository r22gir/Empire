"""Internal fabric / vinyl / leather code registry.

Every incoming material gets a sequential internal code that is never reused:

    V003-Cognac   vinyl
    F012-Navy     fabric
    L002-Cognac   leather

Client-facing views expose code, color, and specs only — never brand or supplier.
Internal views may include supplier / brand.

This module does not write to the live EMPIRE_TASK_DB on import. Callers pass
an explicit sqlite connection (tests use a temp file). Import from a CSV whose
header matches docs/FABRIC_CODES.csv.
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

PREFIX_BY_TYPE = {
    "vinyl": "V",
    "v": "V",
    "fabric": "F",
    "f": "F",
    "textile": "F",
    "cloth": "F",
    "leather": "L",
    "l": "L",
}

TYPE_BY_PREFIX = {"V": "vinyl", "F": "fabric", "L": "leather"}

CODE_RE = re.compile(r"^([VFL])(\d{3,})-(.+)$")

# Canonical CSV header — must match docs/FABRIC_CODES.csv
CSV_HEADER = [
    "code",
    "color",
    "material_type",
    "width_inches",
    "pattern_repeat_v",
    "pattern_repeat_h",
    "backing",
    "specs",
    "brand",
    "supplier",
    "supplier_sku",
    "notes",
]

CLIENT_FIELDS = (
    "code",
    "color",
    "material_type",
    "width_inches",
    "pattern_repeat_v",
    "pattern_repeat_h",
    "backing",
    "specs",
)

INTERNAL_ONLY_FIELDS = ("brand", "supplier", "supplier_sku", "notes")

DEFAULT_CSV = Path(__file__).resolve().parents[3] / "docs" / "FABRIC_CODES.csv"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS fabric_code_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    prefix TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    color TEXT NOT NULL,
    material_type TEXT NOT NULL,
    width_inches REAL,
    pattern_repeat_v REAL,
    pattern_repeat_h REAL,
    backing TEXT,
    specs TEXT,
    brand TEXT,
    supplier TEXT,
    supplier_sku TEXT,
    notes TEXT,
    retired INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(prefix, sequence)
);
CREATE INDEX IF NOT EXISTS idx_fabric_code_prefix_seq
    ON fabric_code_registry(prefix, sequence);
"""


class FabricCodeError(ValueError):
    pass


def ensure_registry(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)


def normalize_color(color: str) -> str:
    raw = (color or "").strip()
    if not raw:
        raise FabricCodeError("color is required")
    parts = re.split(r"[^A-Za-z0-9]+", raw)
    cleaned = "".join(p[:1].upper() + p[1:].lower() for p in parts if p)
    if not cleaned:
        raise FabricCodeError(f"color {color!r} is empty after normalize")
    return cleaned


def prefix_for_type(material_type: str) -> str:
    key = (material_type or "").strip().lower()
    if key in PREFIX_BY_TYPE:
        return PREFIX_BY_TYPE[key]
    if key.upper() in TYPE_BY_PREFIX:
        return key.upper()
    raise FabricCodeError(
        f"material_type must be vinyl (V), fabric (F), or leather (L); got {material_type!r}"
    )


def parse_code(code: str) -> tuple[str, int, str]:
    m = CODE_RE.match((code or "").strip())
    if not m:
        raise FabricCodeError(f"invalid internal code {code!r}; expected V003-Cognac")
    return m.group(1), int(m.group(2)), m.group(3)


def format_code(prefix: str, sequence: int, color: str) -> str:
    return f"{prefix}{sequence:03d}-{normalize_color(color)}"


def highest_sequence(conn: sqlite3.Connection, prefix: str) -> int:
    ensure_registry(conn)
    row = conn.execute(
        "SELECT MAX(sequence) FROM fabric_code_registry WHERE prefix = ?",
        (prefix,),
    ).fetchone()
    return int(row[0] or 0)


def next_sequence(conn: sqlite3.Connection, prefix: str) -> int:
    """Next unused sequence. Never reuses a retired or deleted number."""
    return highest_sequence(conn, prefix) + 1


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: sqlite3.Row | tuple, columns: Iterable[str]) -> dict:
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    return dict(zip(columns, row))


def assign_code(
    conn: sqlite3.Connection,
    *,
    color: str,
    material_type: str,
    width_inches: float | None = None,
    pattern_repeat_v: float | None = None,
    pattern_repeat_h: float | None = None,
    backing: str | None = None,
    specs: str | None = None,
    brand: str | None = None,
    supplier: str | None = None,
    supplier_sku: str | None = None,
    notes: str | None = None,
) -> dict:
    """Allocate the next sequential code. Never reuses a prior sequence."""
    ensure_registry(conn)
    prefix = prefix_for_type(material_type)
    color_n = normalize_color(color)
    seq = next_sequence(conn, prefix)
    code = format_code(prefix, seq, color_n)
    conn.execute(
        """INSERT INTO fabric_code_registry
           (code, prefix, sequence, color, material_type, width_inches,
            pattern_repeat_v, pattern_repeat_h, backing, specs, brand,
            supplier, supplier_sku, notes, retired, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (
            code, prefix, seq, color_n, TYPE_BY_PREFIX[prefix],
            width_inches, pattern_repeat_v, pattern_repeat_h, backing, specs,
            brand, supplier, supplier_sku, notes, _now(),
        ),
    )
    return get_code(conn, code, internal=True)


def retire_code(conn: sqlite3.Connection, code: str) -> dict:
    """Retire a code. The sequence stays consumed and is never reused."""
    ensure_registry(conn)
    cur = conn.execute(
        "UPDATE fabric_code_registry SET retired = 1 WHERE code = ?",
        (code,),
    )
    if cur.rowcount == 0:
        raise FabricCodeError(f"unknown code {code}")
    return get_code(conn, code, internal=True)


def get_code(conn: sqlite3.Connection, code: str, *, internal: bool = False) -> dict:
    ensure_registry(conn)
    row = conn.execute(
        "SELECT * FROM fabric_code_registry WHERE code = ?",
        (code,),
    ).fetchone()
    if not row:
        raise FabricCodeError(f"unknown code {code}")
    data = dict(row) if isinstance(row, sqlite3.Row) else dict(row)
    return internal_view(data) if internal else client_view(data)


def client_view(row: dict) -> dict:
    """Client-facing docs: code, color, specs — never brand or supplier."""
    return {k: row.get(k) for k in CLIENT_FIELDS if k in row or k in CLIENT_FIELDS}


def internal_view(row: dict) -> dict:
    """Internal docs may include supplier / brand."""
    keys = (*CLIENT_FIELDS, *INTERNAL_ONLY_FIELDS, "prefix", "sequence", "retired", "created_at")
    return {k: row.get(k) for k in keys}


def client_fabric_line(item: dict) -> str:
    """Client-facing fabric line for quotes / PDFs: code, color, specs only."""
    line = format_client_material({
        "code": item.get("fabric_code") or item.get("code"),
        "color": item.get("fabric_color") or item.get("color_pattern") or item.get("color"),
        "specs": item.get("fabric_specs") or item.get("specs"),
        "width_inches": item.get("fabric_width") or item.get("width_inches"),
        "material_type": item.get("material_type"),
        "pattern_repeat_v": item.get("pattern_repeat_v"),
        "pattern_repeat_h": item.get("pattern_repeat_h"),
        "backing": item.get("backing"),
        "brand": item.get("brand") or item.get("fabric_brand"),
        "supplier": item.get("supplier"),
    })
    if line:
        return line
    code = item.get("fabric_code") or item.get("code") or ""
    color = item.get("fabric_color") or item.get("color_pattern") or ""
    if code or color:
        return " ".join(p for p in (code, color) if p)
    name = (item.get("fabric_name") or "").strip()
    lowered = name.lower()
    if name and not any(k in lowered for k in ("supplier", "brand", "kravet", "schumacher", "fabricut")):
        return name
    return ""


def format_client_material(row: dict) -> str:
    """One-line client-safe material description for quotes / PDFs."""
    view = client_view(row)
    parts = [view.get("code") or "", view.get("color") or ""]
    specs = view.get("specs") or ""
    width = view.get("width_inches")
    bits = [p for p in parts if p]
    extras = []
    if specs:
        extras.append(specs)
    if width:
        extras.append(f'{width}" wide')
    if extras:
        bits.append("— " + ", ".join(str(x) for x in extras))
    return " ".join(bits).strip()


def _float_or_none(value) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


def validate_csv_header(header: list[str]) -> None:
    got = [h.strip() for h in header]
    if got != CSV_HEADER:
        raise FabricCodeError(
            "CSV header must match FABRIC_CODES.csv exactly: "
            + ",".join(CSV_HEADER)
            + f" (got {','.join(got)})"
        )


def import_csv(
    conn: sqlite3.Connection,
    csv_text: str | None = None,
    *,
    path: Path | str | None = None,
) -> dict:
    """Import codes from a CSV whose header matches docs/FABRIC_CODES.csv.

    Existing codes are left untouched (never reused / never overwritten).
    New rows keep their stated code when valid; sequences after the highest
    existing number (V001–V007 already assigned) stay reserved.
    """
    ensure_registry(conn)
    if csv_text is None:
        csv_path = Path(path) if path else DEFAULT_CSV
        csv_text = csv_path.read_text(encoding="utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    try:
        header = next(reader)
    except StopIteration:
        raise FabricCodeError("CSV is empty")
    validate_csv_header(header)

    inserted = 0
    skipped = 0
    errors: list[str] = []
    for i, raw in enumerate(reader, start=2):
        if not raw or all(not (c or "").strip() for c in raw):
            continue
        row = dict(zip(CSV_HEADER, (raw + [""] * len(CSV_HEADER))[: len(CSV_HEADER)]))
        code = (row.get("code") or "").strip()
        try:
            if not code:
                assigned = assign_code(
                    conn,
                    color=row["color"],
                    material_type=row["material_type"],
                    width_inches=_float_or_none(row.get("width_inches")),
                    pattern_repeat_v=_float_or_none(row.get("pattern_repeat_v")),
                    pattern_repeat_h=_float_or_none(row.get("pattern_repeat_h")),
                    backing=row.get("backing") or None,
                    specs=row.get("specs") or None,
                    brand=row.get("brand") or None,
                    supplier=row.get("supplier") or None,
                    supplier_sku=row.get("supplier_sku") or None,
                    notes=row.get("notes") or None,
                )
                inserted += 1
                continue
            prefix, seq, color_from_code = parse_code(code)
            existing = conn.execute(
                "SELECT code FROM fabric_code_registry WHERE code = ? OR (prefix = ? AND sequence = ?)",
                (code, prefix, seq),
            ).fetchone()
            if existing:
                skipped += 1
                continue
            color = normalize_color(row.get("color") or color_from_code)
            expected = format_code(prefix, seq, color)
            if expected != code and normalize_color(color_from_code) != color:
                # Allow V003-Cognac when color column is Cognac
                code = expected
            conn.execute(
                """INSERT INTO fabric_code_registry
                   (code, prefix, sequence, color, material_type, width_inches,
                    pattern_repeat_v, pattern_repeat_h, backing, specs, brand,
                    supplier, supplier_sku, notes, retired, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                (
                    code, prefix, seq, color,
                    TYPE_BY_PREFIX[prefix],
                    _float_or_none(row.get("width_inches")),
                    _float_or_none(row.get("pattern_repeat_v")),
                    _float_or_none(row.get("pattern_repeat_h")),
                    row.get("backing") or None,
                    row.get("specs") or None,
                    row.get("brand") or None,
                    row.get("supplier") or None,
                    row.get("supplier_sku") or None,
                    row.get("notes") or None,
                    _now(),
                ),
            )
            inserted += 1
        except Exception as exc:
            errors.append(f"line {i}: {exc}")
    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "highest": {
            "V": highest_sequence(conn, "V"),
            "F": highest_sequence(conn, "F"),
            "L": highest_sequence(conn, "L"),
        },
    }
