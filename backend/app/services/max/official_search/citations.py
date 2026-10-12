"""Citation verification: only fetched URLs, quotes must appear, strip invented links."""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urlparse, urlunparse

_URL_RE = re.compile(r"https?://[^\s)\]>\"']+", re.I)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", re.I)
_QUOTE_RE = re.compile(r"[\"“”«»]([^\"“”«»]{8,400})[\"“”«»]")


def _norm_url(url: str) -> str:
    raw = (url or "").strip()
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").rstrip("/")
    return urlunparse((parsed.scheme.lower(), host, path, "", "", ""))


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def fetched_url_set(pages: Iterable[dict] | None) -> set[str]:
    allowed: set[str] = set()
    for page in pages or []:
        if not isinstance(page, dict):
            continue
        url = str(page.get("url") or "").strip()
        if url:
            allowed.add(_norm_url(url))
            allowed.add(url.rstrip("/"))
    return allowed


def _url_allowed(url: str, allowed: set[str]) -> bool:
    if not allowed:
        return False
    if url in allowed or _norm_url(url) in allowed:
        return True
    # Trailing-slash / www variants
    n = _norm_url(url)
    for item in allowed:
        if _norm_url(item) == n:
            return True
    return False


def strip_invented_citations(text: str, fetched_pages: Iterable[dict] | None) -> tuple[str, int]:
    """Remove markdown and bare URLs that were never fetched."""
    allowed = fetched_url_set(fetched_pages)
    stripped = 0

    def md(match: re.Match) -> str:
        nonlocal stripped
        title, url = match.group(1), match.group(2)
        if _url_allowed(url, allowed):
            return match.group(0)
        stripped += 1
        return title

    out = _MD_LINK_RE.sub(md, text or "")

    def bare(match: re.Match) -> str:
        nonlocal stripped
        url = match.group(0)
        if _url_allowed(url, allowed):
            return url
        stripped += 1
        return ""

    out = _URL_RE.sub(bare, out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" +\n", "\n", out)
    return out, stripped


def verify_quoted_text(text: str, fetched_pages: Iterable[dict] | None) -> tuple[str, int]:
    """Drop quoted spans that do not appear in fetched page text."""
    corpus = _norm_text("\n".join(
        str(p.get("text") or p.get("content") or "")
        for p in (fetched_pages or [])
        if isinstance(p, dict)
    ))
    if not corpus:
        # Nothing fetched — strip every quote so we do not invent citations.
        def drop_all(match: re.Match) -> str:
            return ""
        cleaned = _QUOTE_RE.sub(drop_all, text or "")
        removed = len(_QUOTE_RE.findall(text or ""))
        return cleaned, removed

    removed = 0

    def keep(match: re.Match) -> str:
        nonlocal removed
        quote = match.group(1)
        if _norm_text(quote) in corpus:
            return match.group(0)
        removed += 1
        return ""

    return _QUOTE_RE.sub(keep, text or ""), removed


def verify_citations(text: str, fetched_pages: Iterable[dict] | None) -> dict:
    """Strip invented links and unsupported quotes. Return the cleaned text."""
    cleaned, quotes_removed = verify_quoted_text(text or "", fetched_pages)
    cleaned, links_removed = strip_invented_citations(cleaned, fetched_pages)
    return {
        "text": cleaned,
        "links_removed": links_removed,
        "quotes_removed": quotes_removed,
    }
