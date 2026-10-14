"""Founder/main studio vs family edition values.

The Dell main backend may stamp journal rows with EMPIRE_EDITION=workroom
(or studio) while still being Rafael's founder studio. Family editions
(Max-e / Maxine) stay excluded from founder session export.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

# One shared set for the founder/main studio, regardless of how the
# process labels itself. Empty string is the historical default.
FOUNDER_EDITIONS = frozenset({"", "main", "workroom", "studio"})
FAMILY_EDITIONS = frozenset({"amp", "maxine", "max-e", "maxe", "max_e"})
FAMILY_PATH_MARKERS = ("/data/amp", "/data/maxine", "empire-amp", "empire-maxine")

# SQL fragment — literals only, never user input.
FOUNDER_EDITION_SQL = (
    "LOWER(TRIM(COALESCE({column}, ''))) IN ('', 'main', 'workroom', 'studio')"
)


def normalize_edition(value: Any) -> str:
    return str(value or "").strip().lower()


def is_founder_edition(value: Any) -> bool:
    return normalize_edition(value) in FOUNDER_EDITIONS


def is_family_edition(value: Any) -> bool:
    ed = normalize_edition(value)
    if not ed or ed in FOUNDER_EDITIONS:
        return False
    if ed in FAMILY_EDITIONS:
        return True
    if ed.startswith("amp") or ed.startswith("max-e") or ed.startswith("maxe"):
        return True
    if "maxine" in ed:
        return True
    return False


def current_edition() -> str:
    return normalize_edition(os.getenv("EMPIRE_EDITION")) or "main"


def founder_edition_sql(column: str = "edition") -> str:
    if not column.replace("_", "").isalnum():
        raise ValueError("invalid edition column")
    return FOUNDER_EDITION_SQL.format(column=column)


def path_looks_family(data_dir: Path | str) -> bool:
    resolved = str(Path(data_dir).expanduser().resolve())
    return any(marker in resolved for marker in FAMILY_PATH_MARKERS)


def founder_editions() -> Iterable[str]:
    return tuple(sorted(FOUNDER_EDITIONS))
