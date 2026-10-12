"""Orchestrate official-sources search, verification, footer, and spoken strip."""
from __future__ import annotations

import logging
from typing import Optional

from app.services.max.official_search.citations import verify_citations
from app.services.max.official_search.config import (
    DEFAULT_NUM_RESULTS,
    MAX_NUM_RESULTS,
    default_page_chars,
    official_page_chars,
    today_iso,
)
from app.services.max.official_search.family import (
    family_search_guard,
    maxine_blocks_query,
    redact_maxine_results,
)
from app.services.max.official_search.footer import attach_sources_footer
from app.services.max.official_search.intent import detect_language, is_official_intent
from app.services.max.official_search.providers import (
    minimax_research_enabled,
    run_providers,
)
from app.services.max.official_search.trust_tiers import (
    TIER_OFFICIAL,
    classify_domain,
    filter_by_tiers,
    topic_allowlist,
)

logger = logging.getLogger("max.official_search")


def official_page_char_cap(url: str = "", *, official_mode: bool = False) -> int:
    """6–8k chars for official / long primary docs; 2,500 otherwise."""
    if official_mode or classify_domain(url) == TIER_OFFICIAL:
        return official_page_chars()
    return default_page_chars()


def run_web_search(params: dict, desk: Optional[str] = None, **kwargs) -> dict:
    """Execute official-sources web search. Fail-closed on provider errors.

    Returns ``{tool, success, error, result}`` so tool_executor can wrap it
    without a circular import.
    """
    query = str((params or {}).get("query") or "").strip()
    logger.info("[official_search] query=%r", query[:120])
    if not query:
        return {"tool": "web_search", "success": False, "error": "Query is required", "result": None}

    if maxine_blocks_query(query):
        return {
            "tool": "web_search",
            "success": False,
            "error": "maxine_argos_blocked",
            "result": {
                "query": query,
                "results": [],
                "count": 0,
                "blocked": True,
                "reason": "Maxine does not search or store Argos Campestre legal or company details.",
            },
        }

    guard = family_search_guard("web_search")
    if not guard["ok"]:
        return {
            "tool": "web_search",
            "success": False,
            "error": guard["error"],
            "result": {
                "query": query, "results": [], "count": 0,
                "blocked": True, "reason": guard["message"],
            },
        }

    official = bool(params.get("official")) or is_official_intent(query)
    language = params.get("language") or detect_language(query)
    try:
        num_results = min(int(params.get("num_results", DEFAULT_NUM_RESULTS)), MAX_NUM_RESULTS)
    except (TypeError, ValueError):
        num_results = DEFAULT_NUM_RESULTS

    include_domains = None
    if official:
        include_domains = topic_allowlist(query, entity_domain=params.get("entity_domain"))

    raw = run_providers(
        query,
        num_results,
        include_domains=include_domains,
        start_date=params.get("start_date") or params.get("from_date"),
        end_date=params.get("end_date") or params.get("to_date"),
        providers=kwargs.get("providers"),
        http_get=kwargs.get("http_get"),
        http_post=kwargs.get("http_post"),
    )

    if not raw.get("ok"):
        return {
            "tool": "web_search",
            "success": False,
            "error": raw.get("error") or "all_providers_failed",
            "result": {
                "query": query,
                "results": [],
                "count": 0,
                "source": raw.get("source"),
                "attempts": raw.get("attempts") or [],
                "official": official,
                "minimax_research": minimax_research_enabled(),
            },
        }

    hits = redact_maxine_results(raw.get("results") or [])
    filtered = filter_by_tiers(
        hits,
        official=official,
        query=query,
        entity_domain=params.get("entity_domain"),
        widen=not bool(params.get("strict_tier1")),
        max_results=num_results,
    )
    results = redact_maxine_results(filtered["results"])
    no_tier1 = bool(filtered.get("no_tier1"))
    notice = ""
    if official and no_tier1:
        notice = (
            "No se encontró fuente oficial. No official source found."
            if language == "es"
            else "No official source found."
        )

    return {
        "tool": "web_search",
        "success": True,
        "error": None,
        "result": {
            "query": query,
            "results": results,
            "count": len(results),
            "source": raw.get("source"),
            "attempts": raw.get("attempts") or [],
            "official": official,
            "language": language,
            "no_tier1": no_tier1,
            "widened": filtered.get("widened"),
            "independent": filtered.get("independent"),
            "notice": notice,
            "today": today_iso(),
            "minimax_research": False,
        },
    }


def finalize_research_reply(
    text: str,
    *,
    pages: list[dict] | None = None,
    snippets: list[dict] | None = None,
    question: str | None = None,
    channel: str | None = None,
    official: bool | None = None,
    no_tier1: bool = False,
) -> str:
    """Verify citations, attach the code-built footer, strip URLs for spoken channels."""
    fetched = [p for p in (pages or []) if isinstance(p, dict) and (p.get("text") or p.get("content") or p.get("read"))]
    verified = verify_citations(text or "", fetched)
    cleaned = attach_sources_footer(
        verified["text"],
        fetched,
        question=question,
        snippets=None if official else snippets,
        no_tier1=no_tier1,
    )
    # Official mode: footer is fetched Tier-1 pages only (plus labeled unverified if widened).
    if official:
        cleaned = attach_sources_footer(
            verified["text"],
            fetched or (pages or []),
            question=question,
            snippets=[s for s in (snippets or []) if int(s.get("tier") or 99) != TIER_OFFICIAL] if no_tier1 else None,
            no_tier1=no_tier1,
        )
    try:
        from app.services.max.doc_links import is_spoken_channel, strip_spoken_urls
        if is_spoken_channel(channel):
            return strip_spoken_urls(cleaned)
    except Exception:
        pass
    return cleaned


def finalize_from_tool_results(
    text: str,
    tool_results: list[dict] | None,
    *,
    question: str | None = None,
    channel: str | None = None,
) -> str:
    """Build fetched pages from tool results, then verify + attach footer."""
    pages: list[dict] = []
    snippets: list[dict] = []
    official = False
    no_tier1 = False
    for tr in tool_results or []:
        if not isinstance(tr, dict):
            continue
        result = tr.get("result") or {}
        if not isinstance(result, dict):
            continue
        if tr.get("tool") == "web_read" and tr.get("success"):
            pages.append({
                "url": result.get("url"),
                "title": result.get("title"),
                "text": result.get("content") or result.get("text"),
                "published": result.get("published"),
                "date_label": result.get("date_label"),
                "read": True,
            })
        if tr.get("tool") == "web_search" and tr.get("success"):
            official = official or bool(result.get("official"))
            no_tier1 = no_tier1 or bool(result.get("no_tier1"))
            for item in result.get("results") or []:
                if isinstance(item, dict):
                    snippets.append(item)
    if not pages and not snippets:
        return text or ""
    return finalize_research_reply(
        text,
        pages=pages,
        snippets=snippets,
        question=question,
        channel=channel,
        official=official,
        no_tier1=no_tier1,
    )


def spoken_source_names(pages: list[dict] | None, language: str = "en") -> str:
    names = []
    for page in pages or []:
        title = str(page.get("title") or page.get("domain") or "").strip()
        if title:
            names.append(title)
    if not names:
        return ""
    heading = "Fuentes" if language == "es" else "Sources"
    return heading + "\n" + "\n".join(f"{i}. {n}" for i, n in enumerate(names, 1))
