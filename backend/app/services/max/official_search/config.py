"""Env-driven config for official-sources search. Free tiers only."""
from __future__ import annotations

import os
from typing import Optional

# Free-tier page budgets. Official / long primary docs get 6–8k chars.
DEFAULT_PAGE_CHARS = 2500
OFFICIAL_PAGE_CHARS = 8000
DEFAULT_NUM_RESULTS = 5
MAX_NUM_RESULTS = 10

# Family editions may spend at most this share of EmpireBox monthly AI use.
DEFAULT_FAMILY_CAP_PCT = 20.0

# Paid / card-gated search products are never used.
FORBIDDEN_PROVIDER_ENV = (
    "SERPAPI_API_KEY",
    "GOOGLE_CSE_API_KEY",
    "BING_API_KEY",
)


def env_flag(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    raw = env_flag(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def process_edition() -> str:
    try:
        from app.services.search.edition import process_edition as _pe
        return _pe()
    except Exception:
        raw = (os.getenv("EMPIRE_EDITION") or "").strip().lower().replace("-", "_")
        if raw in ("", "main", "workroom", "empire", "founder", "studio"):
            return "main"
        if raw in ("amp", "max_e", "maxe"):
            return "max_e"
        if raw == "maxine":
            return "maxine"
        return "unknown"


def is_family_edition(edition: Optional[str] = None) -> bool:
    ed = edition or process_edition()
    return ed in ("max_e", "maxine", "unknown")


def edition_key(base_name: str, edition: Optional[str] = None) -> str:
    """Edition-scoped API key. Family editions do not inherit the workroom key.

    Lookups, in order:
      EXA_API_KEY_MAXINE / EXA_API_KEY_MAX_E / EXA_API_KEY_AMP
      then (main / workroom only) EXA_API_KEY
    """
    ed = edition or process_edition()
    if ed == "maxine":
        return env_flag(f"{base_name}_MAXINE")
    if ed == "max_e":
        return env_flag(f"{base_name}_MAX_E") or env_flag(f"{base_name}_AMP")
    return env_flag(base_name)


def shared_free_key(base_name: str, edition: Optional[str] = None) -> str:
    """Free public-API keys (Congress, Regulations) may be shared platform-wide."""
    scoped = edition_key(base_name, edition)
    if scoped:
        return scoped
    return env_flag(base_name)


def family_cap_pct() -> float:
    raw = env_flag("INSTANCE_USAGE_CAP_PCT")
    if not raw:
        return DEFAULT_FAMILY_CAP_PCT if is_family_edition() else 100.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_FAMILY_CAP_PCT


def official_page_chars() -> int:
    raw = env_flag("OFFICIAL_SEARCH_PAGE_CHARS", str(OFFICIAL_PAGE_CHARS))
    try:
        return max(6000, min(8000, int(raw)))
    except ValueError:
        return OFFICIAL_PAGE_CHARS


def default_page_chars() -> int:
    raw = env_flag("WEB_RESEARCH_PAGE_CHARS", str(DEFAULT_PAGE_CHARS))
    try:
        return max(500, int(raw))
    except ValueError:
        return DEFAULT_PAGE_CHARS


def sec_user_agent() -> str:
    return env_flag(
        "SEC_EDGAR_USER_AGENT",
        "EmpireBox-Max/1.0 (official-sources; contact=max@empirebox.store)",
    )


def brave_goggles() -> str:
    return env_flag("BRAVE_GOGGLES_ID") or env_flag("BRAVE_GOGGLES_URL")
