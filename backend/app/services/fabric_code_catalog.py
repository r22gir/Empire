"""Read-only view of the shared fabric code registry.

Source of truth: docs/FABRIC_CODES.csv (PR #128).
V001–V008 are the assigned Workroom vinyls (V001-Raven = Black seat,
V003-Cognac = channel backs). The next vinyl code is V009 and is
assigned only by the sequential registry — never invented here.

Client-facing rows expose code, color, and specs. Brand and supplier
never leave this module on a share / client path.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Optional

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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def csv_path() -> Path:
    override = os.getenv("EMPIRE_FABRIC_CODES_CSV")
    if override:
        return Path(override)
    return _repo_root() / "docs" / "FABRIC_CODES.csv"


def client_view(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row.get(k) if k in row else None for k in CLIENT_FIELDS}


def _parse_row(raw: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {k: (raw.get(k) or "").strip() or None for k in CSV_HEADER}
    for num_key in ("width_inches", "pattern_repeat_v", "pattern_repeat_h"):
        val = out.get(num_key)
        if val in (None, ""):
            out[num_key] = None
        else:
            try:
                out[num_key] = float(val)
            except (TypeError, ValueError):
                out[num_key] = None
    return out


def load_registry_rows() -> list[dict[str, Any]]:
    """Load every assigned code from the shared CSV. Read-only."""
    path = csv_path()
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames and [h.strip() for h in reader.fieldnames] != CSV_HEADER:
            raise ValueError("FABRIC_CODES.csv header does not match the shared registry")
        rows = [_parse_row(row) for row in reader if (row.get("code") or "").strip()]
    if os.getenv("EMPIRE_FABRIC_LIVE_REGISTRY", "").strip().lower() in {"1", "true", "yes"}:
        extra = _live_registry_rows()
        seen = {r["code"] for r in rows}
        for row in extra:
            if row.get("code") and row["code"] not in seen:
                rows.append(row)
                seen.add(row["code"])
    return rows


def _live_registry_rows() -> list[dict[str, Any]]:
    """Read already-assigned codes from PR #128's SQLite table if it exists.

    Never creates tables or writes. CSV remains the baseline (V001–V007).
    """
    try:
        from app.db.database import get_db
    except Exception:
        return []
    try:
        with get_db() as conn:
            exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fabric_code_registry'"
            ).fetchone()
            if not exists:
                return []
            fetched = conn.execute(
                "SELECT * FROM fabric_code_registry ORDER BY prefix, sequence"
            ).fetchall()
        rows = []
        for item in fetched:
            rows.append(dict(item) if not isinstance(item, dict) else item)
        return rows
    except Exception:
        return []


def client_catalog() -> list[dict[str, Any]]:
    return [client_view(row) for row in load_registry_rows() if row.get("code")]


def lookup_code(code: Optional[str]) -> Optional[dict[str, Any]]:
    """Resolve a registry code to a client-safe row.

    Empty / None → uncoded (None).
    Unknown / invented codes raise ValueError.
    """
    cleaned = (code or "").strip()
    if not cleaned:
        return None
    for row in load_registry_rows():
        if row.get("code") == cleaned:
            return client_view(row)
    raise ValueError(
        f"Fabric code '{cleaned}' is not in the shared registry "
        "(docs/FABRIC_CODES.csv). Pick a registered code or leave the swatch uncoded."
    )


def next_vinyl_hint() -> str:
    """Informational only — mood boards never assign codes."""
    highest = 0
    for row in load_registry_rows():
        code = row.get("code") or ""
        if code.startswith("V") and len(code) >= 4 and code[1:4].isdigit():
            highest = max(highest, int(code[1:4]))
    nxt = max(highest + 1, 9)
    return f"V{nxt:03d}"
