"""Rank web-search hits and format clickable Fuentes for Max-e / Maxine.

Official sites (government TLDs and the edition's own websites) and
registries first, major news next, everything else after, Facebook /
Instagram / TikTok last. Each source is one short markdown link; the
raw URL is not repeated after the title.
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterable
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

# Host / registrable-domain tokens only. Do not match these in titles or paths
# ("Cámara de Comercio" in a news headline is not a registry hit).
REGISTRY_HOST_TOKENS = (
    "rues",
    "camara",
    "directorio",
    "chamber",
    "opencorporates",
    "companieshouse",
    "superintendencia",
    "sunat",
    "yellowpages",
    "paginasamarillas",
    "infobel",
    "registro",
)

REGISTRY_HOST_SUFFIXES = (
    "sec.gov",
    "dnb.com",
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


def _normalize_host(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if "://" in raw:
        return _host(raw)
    if raw.startswith("www."):
        raw = raw[4:]
    return raw.split("/")[0].split(":")[0]


def _host_matches(host: str, official: str) -> bool:
    if not host or not official:
        return False
    return host == official or host.endswith("." + official)


def _is_social(host: str) -> bool:
    return any(host == name or host.endswith("." + name) for name in SOCIAL_HOSTS)


def _is_news(host: str) -> bool:
    return any(host == name or host.endswith("." + name) for name in NEWS_HOSTS)


def _is_gov_official(host: str) -> bool:
    if not host:
        return False
    if _OFFICIAL_HOST_RE.search(host):
        return True
    return host.endswith(".gov") or host.endswith(".gob") or host.endswith(".edu") or host.endswith(".mil")


def _is_registry_host(host: str) -> bool:
    if not host:
        return False
    if any(_host_matches(host, suffix) for suffix in REGISTRY_HOST_SUFFIXES):
        return True
    labels = [part for part in host.split(".") if part]
    for token in REGISTRY_HOST_TOKENS:
        if any(
            label == token or label.startswith(token) or label.endswith(token)
            for label in labels
        ):
            return True
    return False


def edition_official_hosts(extra: Iterable[str] | None = None) -> frozenset[str]:
    """Hosts that belong to this edition's businesses (own websites)."""
    found: set[str] = set()
    for raw in extra or ():
        host = _normalize_host(str(raw))
        if host:
            found.add(host)
    for raw in (os.getenv("EDITION_OFFICIAL_SITES") or "").split(","):
        host = _normalize_host(raw)
        if host:
            found.add(host)
    try:
        from app.edition import edition_manifest

        product = edition_manifest().get("product") or {}
        host = _normalize_host(str(product.get("site") or ""))
        if host:
            found.add(host)
    except Exception:
        pass
    try:
        from app.services.leadforge.trade_profile import social_default_profile, trade_profile

        profile = trade_profile() or {}
        social = profile.get("social") or {}
        for blob in (
            social.get("profile"),
            *((social.get("profiles_by_business") or {}).values()),
        ):
            if isinstance(blob, dict):
                host = _normalize_host(str(blob.get("website") or ""))
                if host:
                    found.add(host)
        extra_profile = social_default_profile() or {}
        host = _normalize_host(str(extra_profile.get("website") or ""))
        if host:
            found.add(host)
    except Exception:
        pass
    return frozenset(found)


def source_bucket(
    url: str,
    title: str = "",
    *,
    official_hosts: Iterable[str] | None = None,
) -> str:
    host = _host(url)
    if _is_social(host):
        return "social"
    own = {
        _normalize_host(str(item))
        for item in (official_hosts if official_hosts is not None else edition_official_hosts())
        if _normalize_host(str(item))
    }
    if _is_gov_official(host) or any(_host_matches(host, item) for item in own):
        return "official"
    if _is_registry_host(host):
        return "registry"
    if _is_news(host):
        return "news"
    return "other"


def source_rank(
    url: str,
    title: str = "",
    *,
    official_hosts: Iterable[str] | None = None,
) -> int:
    return {
        "official": 0,
        "registry": 1,
        "news": 2,
        "other": 3,
        "social": 4,
    }.get(source_bucket(url, title, official_hosts=official_hosts), 3)


def rank_search_results(
    results: list[Any] | None,
    *,
    official_hosts: Iterable[str] | None = None,
) -> list[dict]:
    """Stable sort: official / registry / news / other / social. Drops empty URLs."""
    hosts = None if official_hosts is None else list(official_hosts)
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
        row["source_bucket"] = source_bucket(url, title, official_hosts=hosts)
        cleaned.append(row)
    cleaned.sort(
        key=lambda row: (
            source_rank(row["url"], row["title"], official_hosts=hosts),
            row["title"].lower(),
        )
    )
    return cleaned


def _display_title(title: str, url: str) -> str:
    host = _host(url)
    cleaned = (title or "").replace("]", "").replace("[", "").strip()
    if not cleaned or cleaned.rstrip("/") == url.rstrip("/") or cleaned.lower() == url.lower():
        return host or cleaned or url
    return cleaned


def format_fuentes_markdown(
    results: list[dict] | None,
    *,
    heading: str = "Fuentes",
    official_hosts: Iterable[str] | None = None,
) -> str:
    rows = rank_search_results(results, official_hosts=official_hosts)
    if not rows:
        return ""
    lines = [f"**{heading}**"]
    for index, row in enumerate(rows, start=1):
        title = _display_title(row["title"], row["url"])
        lines.append(f"{index}. [{title}]({row['url']})")
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


def attach_ranked_sources(
    answer: str,
    tool_results: list[Any] | None,
    *,
    official_hosts: Iterable[str] | None = None,
) -> str:
    """Replace or append a Fuentes list of short clickable title links."""
    rows = rank_search_results(
        extract_web_search_results(tool_results),
        official_hosts=official_hosts,
    )
    if not rows:
        return answer or ""
    block = format_fuentes_markdown(rows, official_hosts=official_hosts)
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
