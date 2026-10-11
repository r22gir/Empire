"""Rank web-search hits and format clickable Fuentes for Max-e / Maxine.

Official sites and registries first, major news next, everything else after,
Facebook / Instagram / TikTok last. Family answers keep Spanish short and
always show title + URL as markdown links.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SOCIAL_HOSTS = frozenset({
    "facebook.com",
    "fb.com",
    "instagram.com",
    "tiktok.com",
})

NEWS_HOSTS = frozenset({
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "wsj.com",
    "bloomberg.com",
    "cnn.com",
    "npr.org",
    "eltiempo.com",
    "elespectador.com",
    "semana.com",
    "elpais.com",
    "elmundo.es",
    "lavanguardia.com",
    "clarin.com",
    "lanacion.com.ar",
    "reforma.com",
    "jornada.com.mx",
    "milenio.com",
    "portafolio.co",
    "larepublica.co",
    "caracol.com.co",
    "rcnradio.com",
    "noticiasrcn.com",
    "bluradio.com",
    "wradio.com.co",
    "france24.com",
    "dw.com",
    "aljazeera.com",
})

REGISTRY_MARKERS = (
    "rues",
    "registro",
    "camara",
    "superintendencia",
    "opencorporates",
    "companieshouse",
    "sec.gov",
    "sunat",
    "sat.gob",
    "directorio",
    "yellowpages",
    "paginasamarillas",
    "infobel",
    "dnb.com",
    "bloomberg.com/profile",
    "chamber",
)

_OFFICIAL_HOST_RE = re.compile(
    r"(?:^|\.)(?:gov|gob|edu|mil)(?:\.[a-z]{2})?$",
    re.I,
)
_FUENTES_HEADING_RE = re.compile(
    r"(?is)\n(?:#{1,6}\s*)?(?:\*\*)?(?:fuentes|sources|references)(?:\*\*)?\s*:?[ \t]*\n.*\Z",
)


def _host(url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_social(host: str) -> bool:
    return any(host == name or host.endswith("." + name) for name in SOCIAL_HOSTS)


def _is_news(host: str) -> bool:
    return any(host == name or host.endswith("." + name) for name in NEWS_HOSTS)


def _is_official(host: str) -> bool:
    if not host:
        return False
    if _OFFICIAL_HOST_RE.search(host):
        return True
    return host.endswith(".gov") or host.endswith(".gob") or host.endswith(".edu") or host.endswith(".mil")


def _is_registry(url: str, title: str, host: str) -> bool:
    blob = f"{host} {url} {title}".lower()
    return any(marker in blob for marker in REGISTRY_MARKERS)


def source_bucket(url: str, title: str = "") -> str:
    host = _host(url)
    if _is_social(host):
        return "social"
    if _is_official(host):
        return "official"
    if _is_registry(url, title, host):
        return "registry"
    if _is_news(host):
        return "news"
    return "other"


def source_rank(url: str, title: str = "") -> int:
    return {
        "official": 0,
        "registry": 1,
        "news": 2,
        "other": 3,
        "social": 4,
    }.get(source_bucket(url, title), 3)


def rank_search_results(results: list[Any] | None) -> list[dict]:
    """Stable sort: official / registry / news / other / social. Drops empty URLs."""
    cleaned: list[dict] = []
    seen: set[str] = set()
    for item in results or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        title = str(item.get("title") or "").strip() or _host(url) or url
        row = dict(item)
        row["url"] = url
        row["title"] = title
        row["source_bucket"] = source_bucket(url, title)
        cleaned.append(row)
    cleaned.sort(key=lambda row: (source_rank(row["url"], row["title"]), row["title"].lower()))
    return cleaned


def format_fuentes_markdown(results: list[dict] | None, *, heading: str = "Fuentes") -> str:
    rows = rank_search_results(results)
    if not rows:
        return ""
    lines = [f"**{heading}**"]
    for index, row in enumerate(rows, start=1):
        title = row["title"].replace("]", "").replace("[", "")
        url = row["url"]
        lines.append(f"{index}. [{title}]({url}) — {url}")
    return "\n".join(lines)


def extract_web_search_results(tool_results: list[Any] | None) -> list[dict]:
    found: list[dict] = []
    for entry in tool_results or []:
        if not isinstance(entry, dict):
            continue
        tool = str(entry.get("tool") or "")
        payload = entry.get("result") if entry.get("success", True) else None
        if tool == "web_search" and isinstance(payload, dict):
            rows = payload.get("results") or payload.get("items") or []
            if isinstance(rows, list):
                found.extend(item for item in rows if isinstance(item, dict))
        elif tool == "web_read" and isinstance(payload, dict):
            url = str(payload.get("url") or "").strip()
            if url:
                found.append({
                    "url": url,
                    "title": str(payload.get("title") or "").strip(),
                    "snippet": "",
                })
    return found


def attach_ranked_sources(answer: str, tool_results: list[Any] | None) -> str:
    """Replace or append a Fuentes list of clickable title + URL links."""
    rows = rank_search_results(extract_web_search_results(tool_results))
    if not rows:
        return answer or ""
    block = format_fuentes_markdown(rows)
    text = answer or ""
    if _FUENTES_HEADING_RE.search(text):
        text = _FUENTES_HEADING_RE.sub("\n\n" + block, text).rstrip()
        return text
    return text.rstrip() + "\n\n" + block


def attach_family_search_sources(answer: str, tool_results: list[Any] | None) -> str:
    try:
        from app.edition import is_family_edition
        if not is_family_edition():
            return answer
    except Exception:
        return answer
    return attach_ranked_sources(answer, tool_results)
