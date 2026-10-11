"""Edition isolation for the Organizer. Fail-closed on EMPIRE_EDITION.

Editions (who owns the data):
  main   — Max (Rafael)
  max_e  — Max-e (Juan)
  maxine — Maxine (Camilo)

Spaces (areas of one owner's life) live *inside* an edition. They are not
editions. Workroom is one space on Rafael's Organizer, not the product.

Unknown EMPIRE_EDITION never maps onto main/workroom data.
Maxine never reads Workroom jobs or Argos Campestre legal/company details.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

ORGANIZER_MODEL = "grok-4.6"

EDITIONS = ("main", "max_e", "maxine")

# Legal / company strings Maxine must never surface.
ARGOS_BLOCKLIST = (
    "argos campestre",
    "argos-campestre",
    "argos_campestre",
    "campestre",
    "argos",
)

# Per-edition daily caps. Family editions stay small on purpose.
USAGE_CAPS = {
    "main": {"items": 500, "captures": 200, "actions": 400},
    "max_e": {"items": 80, "captures": 40, "actions": 80},
    "maxine": {"items": 80, "captures": 40, "actions": 80},
    "unknown": {"items": 10, "captures": 5, "actions": 10},
}

_EDITION_META = {
    "main": {
        "id": "main",
        "assistant": "Max",
        "owner": "Rafael",
        "label": "Max · Rafael",
        "allows_business_directory": True,
        "allows_workroom_jobs": True,
        "spaces": (
            {"slug": "workroom", "label": "Workroom", "kind": "business"},
            {"slug": "empire", "label": "Empire", "kind": "business"},
            {"slug": "family", "label": "Family", "kind": "life"},
            {"slug": "personal", "label": "Personal", "kind": "life"},
            {"slug": "ventures", "label": "Ventures", "kind": "business"},
        ),
    },
    "max_e": {
        "id": "max_e",
        "assistant": "Max-e",
        "owner": "Juan",
        "label": "Max-e · Juan",
        "allows_business_directory": False,
        "allows_workroom_jobs": False,
        "spaces": (
            {"slug": "amp", "label": "AMP", "kind": "business"},
            {"slug": "family", "label": "Family", "kind": "life"},
            {"slug": "personal", "label": "Personal", "kind": "life"},
            {"slug": "ventures", "label": "Ventures", "kind": "business"},
        ),
    },
    "maxine": {
        "id": "maxine",
        "assistant": "Maxine",
        "owner": "Camilo",
        "label": "Maxine · Camilo",
        "allows_business_directory": False,
        "allows_workroom_jobs": False,
        "spaces": (
            {"slug": "family", "label": "Family", "kind": "life"},
            {"slug": "personal", "label": "Personal", "kind": "life"},
            {"slug": "ventures", "label": "Ventures", "kind": "business"},
        ),
    },
    "unknown": {
        "id": "unknown",
        "assistant": "Organizer",
        "owner": "",
        "label": "Unknown edition (fail-closed)",
        "allows_business_directory": False,
        "allows_workroom_jobs": False,
        "spaces": ({"slug": "personal", "label": "Personal", "kind": "life"},),
    },
}


def raw_edition_env() -> str:
    return (os.getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")


def normalize_edition(value: Optional[str]) -> str:
    """Map an env / request value onto a known edition. Unknown → unknown (never main)."""
    key = (value or "").strip().lower().replace("-", "_")
    if key in ("", "main", "workroom", "empire"):
        return "main"
    if key in ("amp", "max_e", "maxe"):
        return "max_e"
    if key == "maxine":
        return "maxine"
    return "unknown"


def process_edition() -> str:
    """Edition of this backend process. Fail-closed: unknown env ≠ main."""
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
    ed = edition or process_edition()
    return dict(_EDITION_META.get(ed) or _EDITION_META["unknown"])


def read_edition_keys(edition: Optional[str] = None) -> tuple[str, ...]:
    """SQLite edition values this process may read.

    Rafael's process also sees legacy rows stored as 'workroom'.
    Family and unknown processes never do.
    """
    ed = edition or process_edition()
    if ed == "main":
        return ("main", "workroom")
    if ed == "max_e":
        return ("max_e",)
    if ed == "maxine":
        return ("maxine",)
    return ("unknown",)


def edition_sql(alias: str = "") -> tuple[str, list]:
    col = f"{alias}.edition" if alias else "edition"
    keys = read_edition_keys()
    placeholders = ",".join("?" * len(keys))
    return f"COALESCE({col}, 'workroom') IN ({placeholders})", list(keys)


def resolve_edition(requested: Optional[str] = None) -> str:
    """Callers cannot cross editions. A spoofed request is ignored."""
    current = process_edition()
    if not requested:
        return current
    want = normalize_edition(requested)
    if want != current:
        return current
    return current


def can_read_business_directory(edition: Optional[str] = None) -> bool:
    return bool(edition_meta(edition).get("allows_business_directory"))


def can_read_workroom_jobs(edition: Optional[str] = None) -> bool:
    return bool(edition_meta(edition).get("allows_workroom_jobs"))


def default_spaces(edition: Optional[str] = None) -> list[dict]:
    return [dict(s) for s in edition_meta(edition).get("spaces") or ()]


def default_space_slug(edition: Optional[str] = None) -> str:
    spaces = default_spaces(edition)
    return spaces[0]["slug"] if spaces else "personal"


def allowed_space_slugs(edition: Optional[str] = None) -> set[str]:
    return {s["slug"] for s in default_spaces(edition)}


def normalize_space(slug: Optional[str], edition: Optional[str] = None) -> str:
    allowed = allowed_space_slugs(edition)
    key = (slug or "").strip().lower().replace(" ", "_")
    if key in allowed:
        return key
    aliases = {
        "work": "workroom",
        "nelma": "workroom",
        "home": "personal",
        "life": "personal",
        "kids": "family",
        "other": "ventures",
        "venture": "ventures",
        "coaching": "amp",
    }
    mapped = aliases.get(key)
    if mapped in allowed:
        return mapped
    return default_space_slug(edition)


def usage_caps(edition: Optional[str] = None) -> dict:
    ed = edition or process_edition()
    return dict(USAGE_CAPS.get(ed) or USAGE_CAPS["unknown"])


def blocked_terms(edition: Optional[str] = None) -> tuple[str, ...]:
    ed = edition or process_edition()
    if ed == "maxine":
        return ARGOS_BLOCKLIST
    return ()


def contains_blocked_term(text: Optional[str], edition: Optional[str] = None) -> bool:
    blob = (text or "").lower()
    if not blob:
        return False
    return any(term in blob for term in blocked_terms(edition))


def redact_blocked(text: Optional[str], edition: Optional[str] = None) -> str:
    out = text or ""
    for term in blocked_terms(edition):
        out = re.sub(re.escape(term), "[redacted]", out, flags=re.I)
    return out


def reject_if_blocked(*parts: Optional[str], edition: Optional[str] = None) -> Optional[str]:
    """Return an error string if any part is blocked for this edition."""
    if any(contains_blocked_term(p, edition) for p in parts):
        return "This edition cannot store or show that content."
    return None


def _configured_main_token_paths() -> dict:
    """Rafael's configured token locations — used to refuse leaks, even if missing."""
    gmail = outlook = None
    try:
        from app.services.max.gmail_reader import get_oauth_paths
        p = get_oauth_paths().get("token_path")
        if p:
            gmail = Path(p).expanduser().resolve()
    except Exception:
        pass
    try:
        from app.services.max.outlook_reader import token_path
        p = token_path()
        if p:
            outlook = Path(p).expanduser().resolve()
    except Exception:
        pass
    return {"gmail": gmail, "outlook": outlook}


def _existing(path) -> Optional[Path]:
    if not path:
        return None
    p = Path(path)
    return p if p.exists() else None


def mailbox_token_paths(edition: Optional[str] = None) -> dict:
    """Token files this edition may read. Never falls back to another edition's mail."""
    ed = edition or process_edition()
    empty = {"edition": ed, "gmail": None, "outlook": None, "sources": []}
    if ed not in EDITIONS:
        return {**empty, "edition": "unknown"}
    main = _configured_main_token_paths()
    if ed == "main":
        gmail = _existing(main.get("gmail"))
        outlook = _existing(main.get("outlook"))
        sources = [name for name, val in (("gmail", gmail), ("outlook", outlook)) if val]
        return {"edition": ed, "gmail": gmail, "outlook": outlook, "sources": sources}

    env_g = os.getenv(f"GMAIL_TOKEN_PATH_{ed.upper()}")
    env_o = os.getenv(f"OUTLOOK_TOKEN_PATH_{ed.upper()}")
    base = Path.home() / ".config" / "empirebox" / ed
    gmail_path = Path(env_g).expanduser() if env_g else (base / "gmail" / "token.json")
    outlook_path = Path(env_o).expanduser() if env_o else (base / "outlook" / "token.json")

    def _own(path: Path, other):
        if not path.exists():
            return None
        resolved = path.resolve()
        if other is not None and resolved == Path(other).resolve():
            return None
        return resolved

    gmail = _own(gmail_path, main.get("gmail"))
    outlook = _own(outlook_path, main.get("outlook"))
    sources = [name for name, val in (("gmail", gmail), ("outlook", outlook)) if val]
    return {"edition": ed, "gmail": gmail, "outlook": outlook, "sources": sources}


def edition_public() -> dict:
    meta = edition_meta()
    return {
        "edition": meta["id"],
        "assistant": meta["assistant"],
        "owner": meta["owner"],
        "label": meta["label"],
        "isolated": True,
        "fail_closed": True,
        "allows_workroom_jobs": meta["allows_workroom_jobs"],
        "allows_business_directory": meta["allows_business_directory"],
        "spaces": default_spaces(),
        "usage_caps": usage_caps(),
        "model": ORGANIZER_MODEL,
        "editions": [
            {"id": "main", "assistant": "Max", "owner": "Rafael"},
            {"id": "max_e", "assistant": "Max-e", "owner": "Juan"},
            {"id": "maxine", "assistant": "Maxine", "owner": "Camilo"},
        ],
        "note": "Each edition has its own Organizer. Nothing crosses editions. Outbound needs the owner's tap.",
    }


# Back-compat alias used by older imports.
def edition_clause(alias: str = "") -> tuple[str, list]:
    return edition_sql(alias)
