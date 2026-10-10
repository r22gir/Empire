"""Edition-scoped document / alias lookup.

Family editions never read repo client_aliases.json (9c34d3eb) and never
call the Workroom docs hub (default :3005).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.edition import is_family_edition, is_founder_edition
from app.services.whatsapp_store import (
    edition_aliases_path,
    jobs_root,
    load_client_aliases,
    repo_aliases_path,
)

__all__ = [
    "docs_hub_enabled",
    "edition_aliases_path",
    "final_docs_all",
    "find_docs",
    "is_founder_edition",
    "jobs_root",
    "load_client_aliases",
    "repo_aliases_path",
    "_hub_base",
    "default_hub_get",
]


def docs_hub_enabled() -> bool:
    return is_founder_edition() and not is_family_edition()


def _hub_base() -> str | None:
    """Workroom Final Docs origin. Disabled for family editions."""
    if not docs_hub_enabled():
        return None
    return (os.getenv("EMPIRE_PORTAL_INTERNAL_URL") or "").strip() or "http://localhost:3005"


def default_hub_get(path: str) -> dict[str, Any]:
    if not docs_hub_enabled():
        return {"ok": False, "docs": [], "reason": "docs hub disabled for this edition"}
    return {"ok": False, "docs": [], "reason": "docs hub not called from tests"}


def find_docs(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    if not docs_hub_enabled():
        return {"ok": False, "docs": [], "reason": "docs hub disabled for this edition"}
    return {"ok": False, "docs": [], "reason": "docs hub not called from tests"}


def final_docs_all(*_args: Any, **_kwargs: Any) -> list[Any]:
    if not docs_hub_enabled():
        return []
    return []


def resolve_job_folder(query: str) -> dict[str, Any] | None:
    """Family editions never resolve Rafael's repo aliases (dahlia / nehal)."""
    aliases = load_client_aliases()
    needle = (query or "").strip().lower()
    if not needle:
        return None
    for row in aliases.get("clients") or []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip().lower()
        names = [slug, str(row.get("name") or "").strip().lower()]
        names.extend(str(a).strip().lower() for a in (row.get("aliases") or []) if a)
        if needle in names or any(needle in name for name in names if name):
            return {"slug": slug, "name": row.get("name") or slug}
    return None
