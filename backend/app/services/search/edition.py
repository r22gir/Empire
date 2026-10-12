"""Edition isolation for universal search. Fail-closed on EMPIRE_EDITION.

Reuses the Organizer edition module from PR #111 when that package is
present. Otherwise a local copy of the same rules so search still ships
on deploy/pr82-84-85 without merging Organizer.

Editions (who owns the data):
  main   — Max (Rafael) — all businesses / areas, including Workroom
  max_e  — Max-e (Juan)
  maxine — Maxine (Camilo) — never Workroom / Argos Campestre

Unknown EMPIRE_EDITION never maps onto main / Workroom data.
"""
from __future__ import annotations

import os
import re
from typing import Optional

# Prefer the Organizer edition module when PR #111 is on this tree.
try:
    from app.services.organizer.edition import (  # type: ignore
        ARGOS_BLOCKLIST as _ORG_ARGOS,
        can_read_business_directory as _org_can_dir,
        can_read_workroom_jobs as _org_can_jobs,
        contains_blocked_term as _org_blocked,
        edition_meta as _org_meta,
        is_family_edition as _org_family,
        process_edition as _org_process,
        redact_blocked as _org_redact,
    )
    _HAS_ORGANIZER = True
except Exception:
    _HAS_ORGANIZER = False
    _ORG_ARGOS = None
    _org_can_dir = _org_can_jobs = _org_blocked = _org_meta = None
    _org_family = _org_process = _org_redact = None


EDITIONS = ("main", "max_e", "maxine")

ARGOS_BLOCKLIST = _ORG_ARGOS or (
    "argos campestre",
    "argos-campestre",
    "argos_campestre",
    "campestre",
    "argos",
)

_ARGOS_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in ARGOS_BLOCKLIST) + r")\b",
    re.I,
)

# Workroom operator businesses — family editions never search these rows.
WORKROOM_BUSINESS_UNITS = frozenset({
    "workroom", "woodcraft", "craft", "craftforge", "luxe", "luxeforge",
    "construction", "storefront",
})

_META = {
    "main": {
        "id": "main",
        "assistant": "Max",
        "owner": "Rafael",
        "allows_business_directory": True,
        "allows_workroom_jobs": True,
        "family": False,
    },
    "max_e": {
        "id": "max_e",
        "assistant": "Max-e",
        "owner": "Juan",
        "allows_business_directory": False,
        "allows_workroom_jobs": False,
        "family": True,
    },
    "maxine": {
        "id": "maxine",
        "assistant": "Maxine",
        "owner": "Camilo",
        "allows_business_directory": False,
        "allows_workroom_jobs": False,
        "family": True,
    },
    "unknown": {
        "id": "unknown",
        "assistant": "Search",
        "owner": "",
        "allows_business_directory": False,
        "allows_workroom_jobs": False,
        "family": True,
    },
}


def raw_edition_env() -> str:
    return (os.getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")


def normalize_edition(value: Optional[str] = None) -> str:
    """Map an env / request value onto a known edition. Unknown → unknown (never main)."""
    key = (value if value is not None else raw_edition_env()).strip().lower().replace("-", "_")
    if key in ("", "main", "workroom", "empire"):
        return "main"
    if key in ("amp", "max_e", "maxe"):
        return "max_e"
    if key == "maxine":
        return "maxine"
    return "unknown"


def process_edition() -> str:
    """Edition of this backend process. Fail-closed: unknown env ≠ main."""
    if _HAS_ORGANIZER and _org_process is not None:
        try:
            return _org_process()
        except Exception:
            pass
    raw = raw_edition_env()
    if raw in ("", "main"):
        return "main"
    if raw in ("workroom", "empire"):
        return "main"
    if raw in ("amp", "max_e", "maxe"):
        return "max_e"
    if raw == "maxine":
        return "maxine"
    return "unknown"


def edition_meta(edition: Optional[str] = None) -> dict:
    if _HAS_ORGANIZER and _org_meta is not None:
        try:
            meta = dict(_org_meta(edition))
            meta["family"] = meta.get("id") in ("max_e", "maxine", "unknown")
            return meta
        except Exception:
            pass
    ed = edition or process_edition()
    return dict(_META.get(ed) or _META["unknown"])


def is_family_edition(edition: Optional[str] = None) -> bool:
    if _HAS_ORGANIZER and _org_family is not None and edition is None:
        try:
            return bool(_org_family())
        except Exception:
            pass
    ed = edition or process_edition()
    return ed in ("max_e", "maxine", "unknown")


def can_read_workroom_jobs(edition: Optional[str] = None) -> bool:
    if _HAS_ORGANIZER and _org_can_jobs is not None and edition is None:
        try:
            return bool(_org_can_jobs())
        except Exception:
            pass
    return bool(edition_meta(edition).get("allows_workroom_jobs"))


def can_read_business_directory(edition: Optional[str] = None) -> bool:
    if _HAS_ORGANIZER and _org_can_dir is not None and edition is None:
        try:
            return bool(_org_can_dir())
        except Exception:
            pass
    return bool(edition_meta(edition).get("allows_business_directory"))


def contains_blocked_term(text: str, edition: Optional[str] = None) -> bool:
    """Maxine never surfaces Argos Campestre legal / company details."""
    ed = edition or process_edition()
    if ed != "maxine":
        return False
    if _HAS_ORGANIZER and _org_blocked is not None:
        try:
            return bool(_org_blocked(text))
        except Exception:
            pass
    return bool(_ARGOS_RE.search(text or ""))


def redact_blocked(text: str, edition: Optional[str] = None) -> str:
    ed = edition or process_edition()
    if ed != "maxine":
        return text or ""
    if _HAS_ORGANIZER and _org_redact is not None:
        try:
            return _org_redact(text)
        except Exception:
            pass
    return _ARGOS_RE.sub("[blocked]", text or "")


def is_workroom_business(value: Optional[str]) -> bool:
    key = (value or "").strip().lower().replace("-", "_")
    return key in WORKROOM_BUSINESS_UNITS


def result_blocked(text: str, edition: Optional[str] = None) -> bool:
    return contains_blocked_term(text, edition)
