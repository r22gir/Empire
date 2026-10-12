"""Code-built Sources / Fuentes footer. One format, EN and ES."""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urlparse

from app.services.max.official_search.intent import detect_language
from app.services.max.official_search.trust_tiers import TIER_LABELS, classify_domain

_FOOTER_HEAD = re.compile(r"(?is)\n*(?:#{1,3}\s*)?(?:sources|fuentes)\s*\n.*\Z")


def detect_reply_language(question: str | None, text: str | None = None) -> str:
    if detect_language(question) == "es":
        return "es"
    if detect_language(text) == "es":
        return "es"
    return "en"


def _host(url: str) -> str:
    host = (urlparse(url or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _read_label(page: dict, language: str) -> str:
    if page.get("read") or page.get("text") or page.get("content"):
        return "leído" if language == "es" else "read"
    return "solo fragmento" if language == "es" else "snippet-only"


def _tier_badge(page: dict, language: str) -> str:
    tier = int(page.get("tier") or classify_domain(str(page.get("url") or "")))
    labels = TIER_LABELS.get(language) or TIER_LABELS["en"]
    return labels.get(tier, labels[3])


def build_sources_footer(
    pages: Iterable[dict] | None,
    *,
    language: str = "en",
    snippets: Iterable[dict] | None = None,
) -> str:
    """One format: title (link), domain, date, Official/Not official, read|snippet-only."""
    heading = "Fuentes" if language == "es" else "Sources"
    rows: list[dict] = []
    seen: set[str] = set()
    for page in list(pages or []) + list(snippets or []):
        if not isinstance(page, dict):
            continue
        url = str(page.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(page)
    if not rows:
        return ""
    lines = [heading]
    for index, page in enumerate(rows, start=1):
        url = str(page.get("url") or "").strip()
        title = str(page.get("title") or _host(url) or url).strip()
        domain = page.get("domain") or _host(url)
        date = page.get("published") or page.get("date_label") or page.get("updated") or (
            "fecha no indicada" if language == "es" else "date not shown"
        )
        badge = _tier_badge(page, language)
        read = _read_label(page, language)
        lines.append(f"{index}. [{title}]({url}) — {domain} — {date} — {badge} — {read}")
    return "\n".join(lines)


def attach_sources_footer(
    text: str,
    pages: Iterable[dict] | None,
    *,
    question: str | None = None,
    snippets: Iterable[dict] | None = None,
    language: str | None = None,
    no_tier1: bool = False,
) -> str:
    """Replace any model-built Sources block with the code-built footer."""
    lang = language or detect_reply_language(question, text)
    footer = build_sources_footer(pages, language=lang, snippets=snippets)
    body = _FOOTER_HEAD.sub("", text or "").rstrip()
    notice = ""
    if no_tier1:
        notice = (
            "No se encontraron fuentes oficiales (Nivel 1) para esta consulta."
            if lang == "es"
            else "No official (Tier 1) sources were found for this query."
        )
    parts = [p for p in (body, notice, footer) if p]
    return "\n\n".join(parts).strip()
