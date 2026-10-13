"""
Runtime feature flags and edition gates.

Flags are env-only. Do not read client_aliases.json, business.json, or .env files
from disk — callers inject os.environ (or a process .env loader elsewhere).

Editions:
  studio | empire  — Studio/Empire line (QuickBooks Online)
  maxine           — Maxine edition (Alegra/Siigo DIAN e-invoicing stub)
"""
from __future__ import annotations

import os
from typing import Literal

Edition = Literal["studio", "empire", "maxine"]

VALID_EDITIONS = frozenset({"studio", "empire", "maxine"})
QBO_EDITIONS = frozenset({"studio", "empire"})
DIAN_EDITIONS = frozenset({"maxine"})


def _truthy(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


def get_edition() -> Edition:
    raw = (os.getenv("EMPIRE_EDITION") or "studio").strip().lower()
    if raw in VALID_EDITIONS:
        return raw  # type: ignore[return-value]
    return "studio"


def forgecrm_messaging_enabled() -> bool:
    """Unified WhatsApp/SMS thread. Default on — it never auto-replies."""
    return _truthy("FEATURE_FORGECRM_MESSAGING", "true")


def qbo_sync_enabled() -> bool:
    """QuickBooks Online sandbox pull. Studio/Empire line only."""
    return _truthy("FEATURE_QBO_SYNC") and get_edition() in QBO_EDITIONS


def alegra_siigo_enabled() -> bool:
    """Alegra/Siigo DIAN stub. Maxine edition only."""
    return _truthy("FEATURE_ALEGRA_SIIGO") and get_edition() in DIAN_EDITIONS


def flag_status() -> dict:
    edition = get_edition()
    return {
        "edition": edition,
        "forgecrm_messaging": forgecrm_messaging_enabled(),
        "qbo_sync": {
            "flag": _truthy("FEATURE_QBO_SYNC"),
            "edition_allowed": edition in QBO_EDITIONS,
            "enabled": qbo_sync_enabled(),
            "line": "studio_empire",
            "mode": "sandbox_pull_only",
            "live_writes": False,
        },
        "alegra_siigo": {
            "flag": _truthy("FEATURE_ALEGRA_SIIGO"),
            "edition_allowed": edition in DIAN_EDITIONS,
            "enabled": alegra_siigo_enabled(),
            "line": "maxine",
            "mode": "sandbox_stub",
            "live_writes": False,
        },
        "auto_replies": False,
        "live_data_writes": False,
    }
