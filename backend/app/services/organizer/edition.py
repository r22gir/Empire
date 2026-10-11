"""Organizer edition isolation. Family editions never share Workroom rows or files."""

from __future__ import annotations

import os
from typing import Optional

ORGANIZER_EDITIONS = ("workroom", "max_e", "maxine")


def normalize_edition(value: Optional[str]) -> str:
    key = (value or "").strip().lower().replace("-", "_")
    if key in ("", "main", "empire", "workroom"):
        return "workroom"
    if key in ("amp", "max_e", "maxe"):
        return "max_e"
    if key == "maxine":
        return "maxine"
    return "workroom"


def process_edition() -> str:
    """Edition of this backend process (EMPIRE_EDITION)."""
    return normalize_edition(os.getenv("EMPIRE_EDITION") or "main")


def resolve_edition(requested: Optional[str] = None) -> str:
    """Callers cannot cross editions. A spoofed request is ignored."""
    current = process_edition()
    want = normalize_edition(requested) if requested else current
    if want != current:
        return current
    return current


def edition_clause(alias: str = "") -> tuple[str, list]:
    col = f"{alias}.edition" if alias else "edition"
    return f"COALESCE({col}, 'workroom') = ?", [process_edition()]
