"""Family-edition isolation for official-sources search.

Max-e and Maxine use this same module with their own keys and the 20%
usage cap. Maxine never searches or stores Argos Campestre legal or
company details.
"""
from __future__ import annotations

from typing import Optional

from app.services.max.official_search.config import (
    family_cap_pct,
    is_family_edition,
    process_edition,
)


def _argos_blocked(text: str, edition: Optional[str] = None) -> bool:
    try:
        from app.services.search.edition import contains_blocked_term
        return bool(contains_blocked_term(text or "", edition))
    except Exception:
        ed = edition or process_edition()
        if ed != "maxine":
            return False
        blob = (text or "").lower()
        return any(term in blob for term in ("argos campestre", "argos-campestre", "argos_campestre", "argos", "campestre"))


def maxine_blocks_query(query: str, edition: Optional[str] = None) -> bool:
    return _argos_blocked(query, edition)


def redact_maxine_results(results: list[dict], edition: Optional[str] = None) -> list[dict]:
    """Drop any hit that would store or surface Argos Campestre details."""
    kept: list[dict] = []
    for item in results or []:
        blob = " ".join(
            str(item.get(k) or "")
            for k in ("title", "url", "snippet", "text", "content")
        )
        if _argos_blocked(blob, edition):
            continue
        kept.append(item)
    return kept


def _instance_usage_blocked(kind: str) -> Optional[bool]:
    """Honor the family 20% cap when instance_usage is on this tree."""
    try:
        from app.services.instance_usage import allow_heavy  # type: ignore
        return not bool(allow_heavy(kind=kind))
    except Exception:
        pass
    try:
        from app.services.instance_usage import assess_request  # type: ignore
        verdict = assess_request(kind=kind, heavy=True)
        if isinstance(verdict, dict):
            return verdict.get("level") == "blocked"
    except Exception:
        pass
    return None


def family_search_guard(kind: str = "web_search", edition: Optional[str] = None) -> dict:
    """Fail closed when Maxine hits Argos terms or the family 20% cap is spent."""
    import os

    ed = edition or process_edition()

    if os.getenv("INSTANCE_USAGE_BLOCKED", "").strip() in {"1", "true", "yes"}:
        return {
            "ok": False,
            "error": "family_usage_cap",
            "message": "This family edition has used its 20% monthly allowance.",
        }

    used_pct = os.getenv("OFFICIAL_SEARCH_USED_PCT", "").strip()
    if used_pct and is_family_edition(ed):
        try:
            if float(used_pct) >= family_cap_pct():
                return {
                    "ok": False,
                    "error": "family_usage_cap",
                    "message": "This family edition has used its 20% monthly allowance.",
                }
        except ValueError:
            pass

    imported = _instance_usage_blocked(kind)
    if imported is True and is_family_edition(ed):
        return {
            "ok": False,
            "error": "family_usage_cap",
            "message": "This family edition has used its 20% monthly allowance.",
        }

    return {"ok": True, "error": None, "message": ""}
