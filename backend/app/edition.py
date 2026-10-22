"""Edition identity for founder Max and family help/meter ports.

Workroom / studio is the default. This module only answers "which process
is this?" so personal Max can read family-help stores and aggregate the
shared MiniMax meter. It does not change Workroom paths, login, module
visibility, or business.json.

Family editions (amp / maxine) are detected from EMPIRE_EDITION or a
family EMPIRE_DATA_DIR basename. They never become the live Workroom.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

WORKROOM_EDITION = "workroom"
AMP_EDITION = "amp"
MAXINE_EDITION = "maxine"
FAMILY_EDITIONS = frozenset({AMP_EDITION, MAXINE_EDITION})
FAMILY_DATA_DIR_ALIASES = {
    "amp": AMP_EDITION,
    "max_e": AMP_EDITION,
    "max-e": AMP_EDITION,
    "maxe": AMP_EDITION,
    "maxine": MAXINE_EDITION,
}
# Live Dell studio: EMPIRE_EDITION is often unset or "studio".
# All of these are Rafael's personal Max, not a family edition.
FOUNDER_EDITION_VALUES = frozenset({"", "main", "workroom", "studio"})

WORKROOM_ASSISTANT_NAME = "Max"
AMP_ASSISTANT_NAME = "Max-e"
MAXINE_ASSISTANT_NAME = "Maxine"
AMP_COACH_NAME = "Juan Diego Giraldo"
MAXINE_OWNER_NAME = "Camilo Giraldo"

EDITION_PROFILES = {
    "workroom": {
        "assistant_default": WORKROOM_ASSISTANT_NAME,
        "locale": "en",
        "primary": "workroom",
        "host": "studio.empirebox.store",
        "backend_port": 8000,
        "frontend_port": 3005,
    },
    "amp": {
        "assistant_default": AMP_ASSISTANT_NAME,
        "locale": "es",
        "primary": "amp",
        "host": "amp.empirebox.store",
        "backend_port": 8011,
        "frontend_port": 3011,
        "data_dir": "/data/amp",
    },
    "maxine": {
        "assistant_default": MAXINE_ASSISTANT_NAME,
        "locale": "es",
        "primary": "construction",
        "host": "maxine.empirebox.store",
        "backend_port": 8012,
        "frontend_port": 3012,
        "data_dir": "/data/maxine",
    },
}

_ALLOWLIST_EXEMPT = (
    ("GET", "/health"),
    ("GET", "/"),
    ("GET", "/api/v1/edition"),
    ("GET", "/api/v1/support/health"),
    ("GET", "/api/v1/support/dry-run"),
    ("POST", "/api/v1/support/dry-run"),
)


class EditionPathError(RuntimeError):
    """A data path escaped the instance data root."""


def _family_from_data_dir() -> Optional[str]:
    raw = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    if not raw:
        return None
    return FAMILY_DATA_DIR_ALIASES.get(Path(raw).name.lower())


def edition_name() -> str:
    raw = os.getenv("EMPIRE_EDITION", "").strip().lower()
    if raw in FAMILY_EDITIONS:
        return raw
    inferred = _family_from_data_dir()
    if inferred:
        return inferred
    if raw in FOUNDER_EDITION_VALUES:
        return WORKROOM_EDITION
    return raw or WORKROOM_EDITION


def is_amp() -> bool:
    return edition_name() == AMP_EDITION


def is_maxine() -> bool:
    return edition_name() == MAXINE_EDITION


def is_family_edition() -> bool:
    return edition_name() in FAMILY_EDITIONS


def is_founder_edition() -> bool:
    """True for Rafael's personal Max (unset, main, workroom, studio).

    Live Dell: EMPIRE_EDITION is unset and EMPIRE_DATA_DIR=/home/rg/empire-data.
    That basename is not a family alias, so this stays founder.
    """
    if is_family_edition():
        return False
    raw = (os.getenv("EMPIRE_EDITION") or "").strip().lower()
    if raw in FOUNDER_EDITION_VALUES:
        return True
    return edition_name() == WORKROOM_EDITION


def edition_profile() -> dict:
    return dict(EDITION_PROFILES.get(edition_name()) or EDITION_PROFILES["workroom"])


def assistant_name() -> str:
    raw = os.getenv("ASSISTANT_NAME", "").strip()
    if raw:
        return raw
    if is_family_edition():
        return str(edition_profile().get("assistant_default") or AMP_ASSISTANT_NAME)
    return WORKROOM_ASSISTANT_NAME


def data_root_or_none() -> Optional[Path]:
    raw = os.getenv("EMPIRE_DATA_DIR", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def require_data_root() -> Path:
    root = data_root_or_none()
    if root is None:
        raise EditionPathError(
            "Esta edición requiere EMPIRE_DATA_DIR "
            "(la instancia no usa los datos del Workroom)"
        )
    root.mkdir(parents=True, exist_ok=True)
    return root


def apply_amp_process_paths() -> None:
    """No-op on studio / Workroom. Tests use this to isolate a family tmp dir.

    Never called from main.py on this branch. Does not read or rewrite
    business.json, client_aliases.json, or max/memory.md.
    """
    if not is_family_edition():
        return
    root = data_root_or_none()
    if root is None:
        return
    root.mkdir(parents=True, exist_ok=True)
    os.environ["EMPIRE_DATA_DIR"] = str(root)
    os.environ.setdefault(
        "ASSISTANT_NAME",
        str(edition_profile().get("assistant_default") or AMP_ASSISTANT_NAME),
    )
    os.environ.setdefault("EMPIRE_DEFAULT_LOCALE", "es")
    os.environ.setdefault("INSTANCE_USAGE_CAP_PCT", "20")


def access_exempt(method: str, path: str) -> bool:
    """Inbox and meter routes are never exempt. Studio auth stays Cloudflare Access."""
    clean = path.split("?", 1)[0]
    for allowed_method, allowed_path in _ALLOWLIST_EXEMPT:
        if method.upper() == allowed_method and clean == allowed_path:
            return True
    return False
