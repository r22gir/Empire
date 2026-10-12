"""Free-tier search providers with a documented fallback order.

Order when keys exist: Exa → Tavily → Brave (only if BRAVE_API_KEY) → DuckDuckGo.
Brave stays OFF until a key is set. MiniMax built-in web_search is never used
for research (no domain filter).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import unquote

from app.services.max.official_search.config import (
    brave_goggles,
    edition_key,
    env_bool,
)

logger = logging.getLogger("max.official_search.providers")

HttpGet = Callable[..., object]
HttpPost = Callable[..., object]


class ProviderError(Exception):
    """A configured provider failed. Fail-closed if every provider errors."""

    def __init__(self, provider: str, message: str):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.message = message


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    published: Optional[str] = None
    provider: str = ""

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published": self.published,
            "provider": self.provider,
        }


@dataclass
class ProviderAttempt:
    name: str
    enabled: bool
    ok: bool = False
    error: Optional[str] = None
    count: int = 0


def minimax_research_enabled() -> bool:
    """MiniMax built-in web_search stays OFF for research (no domain filter)."""
    return env_bool("MINIMAX_WEB_SEARCH_FOR_RESEARCH", False)


def provider_fallback_order() -> list[str]:
    """Enabled providers in fail-over order. DDG is always last."""
    names: list[str] = []
    if edition_key("EXA_API_KEY"):
        names.append("exa")
    if edition_key("TAVILY_API_KEY"):
        names.append("tavily")
    if edition_key("BRAVE_API_KEY"):
        names.append("brave")
    names.append("duckduckgo")
    return names


PROVIDER_ORDER = ("exa", "tavily", "brave", "duckduckgo")


def _httpx():
    import httpx
    return httpx


class SearchProvider:
    name = "base"

    def enabled(self) -> bool:
        return False

    def search(
        self,
        query: str,
        num_results: int = 5,
        *,
        include_domains: Optional[list[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        http_get: Optional[HttpGet] = None,
        http_post: Optional[HttpPost] = None,
    ) -> list[SearchHit]:
        raise NotImplementedError


class ExaProvider(SearchProvider):
    name = "exa"

    def enabled(self) -> bool:
        return bool(edition_key("EXA_API_KEY"))

    def search(
        self,
        query: str,
        num_results: int = 5,
        *,
        include_domains: Optional[list[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        http_get: Optional[HttpGet] = None,
        http_post: Optional[HttpPost] = None,
    ) -> list[SearchHit]:
        key = edition_key("EXA_API_KEY")
        if not key:
            return []
        payload: dict = {
            "query": query,
            "type": "instant",
            "numResults": num_results,
            "contents": {"highlights": True},
        }
        if include_domains:
            payload["includeDomains"] = include_domains[:200]
        if start_date:
            payload["startPublishedDate"] = start_date
        if end_date:
            payload["endPublishedDate"] = end_date
        post = http_post or _httpx().post
        try:
            resp = post(
                "https://api.exa.ai/search",
                json=payload,
                headers={
                    "Authorization": f"Bearer {key}",
                    "x-api-key": key,
                    "Content-Type": "application/json",
                },
                timeout=12.0,
            )
            status = getattr(resp, "status_code", 200)
            if status >= 400:
                raise ProviderError(self.name, f"HTTP {status}")
            data = resp.json() if hasattr(resp, "json") else {}
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name, f"{type(exc).__name__}: {exc}") from exc
        hits: list[SearchHit] = []
        for row in data.get("results") or []:
            url = str(row.get("url") or "")
            title = str(row.get("title") or url)
            snippet = ""
            highlights = row.get("highlights") or []
            if highlights:
                snippet = " ".join(str(h) for h in highlights[:2])
            snippet = snippet or str(row.get("text") or row.get("summary") or "")
            if url and title:
                hits.append(SearchHit(
                    title=title, url=url, snippet=snippet[:400],
                    published=row.get("publishedDate") or row.get("published"),
                    provider=self.name,
                ))
        return hits[:num_results]


class TavilyProvider(SearchProvider):
    name = "tavily"

    def enabled(self) -> bool:
        return bool(edition_key("TAVILY_API_KEY"))

    def search(
        self,
        query: str,
        num_results: int = 5,
        *,
        include_domains: Optional[list[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        http_get: Optional[HttpGet] = None,
        http_post: Optional[HttpPost] = None,
    ) -> list[SearchHit]:
        key = edition_key("TAVILY_API_KEY")
        if not key:
            return []
        payload: dict = {
            "api_key": key,
            "query": query,
            "max_results": num_results,
            "search_depth": "basic",
        }
        if include_domains:
            # Hard filter — Tavily will not return other hosts.
            payload["include_domains"] = include_domains[:200]
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
        post = http_post or _httpx().post
        try:
            resp = post(
                "https://api.tavily.com/search",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=12.0,
            )
            status = getattr(resp, "status_code", 200)
            if status >= 400:
                raise ProviderError(self.name, f"HTTP {status}")
            data = resp.json() if hasattr(resp, "json") else {}
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name, f"{type(exc).__name__}: {exc}") from exc
        hits: list[SearchHit] = []
        for row in data.get("results") or []:
            url = str(row.get("url") or "")
            title = str(row.get("title") or url)
            snippet = str(row.get("content") or row.get("snippet") or "")
            if url and title:
                hits.append(SearchHit(
                    title=title, url=url, snippet=snippet[:400],
                    published=row.get("published_date") or row.get("published"),
                    provider=self.name,
                ))
        return hits[:num_results]


class BraveProvider(SearchProvider):
    """Pluggable Brave Search + Goggles adapter. Stays OFF until BRAVE_API_KEY."""

    name = "brave"

    def enabled(self) -> bool:
        return bool(edition_key("BRAVE_API_KEY"))

    def search(
        self,
        query: str,
        num_results: int = 5,
        *,
        include_domains: Optional[list[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        http_get: Optional[HttpGet] = None,
        http_post: Optional[HttpPost] = None,
    ) -> list[SearchHit]:
        key = edition_key("BRAVE_API_KEY")
        if not key:
            return []
        params: dict = {"q": query, "count": num_results}
        goggles = brave_goggles()
        if goggles:
            params["goggles_id"] = goggles
        if include_domains:
            # Brave has no hard include_domains; site: operators + post-filter.
            params["q"] = query + " " + " OR ".join(f"site:{d}" for d in include_domains[:8])
        get = http_get or _httpx().get
        try:
            resp = get(
                "https://api.search.brave.com/res/v1/web/search",
                params=params,
                headers={"X-Subscription-Token": key, "Accept": "application/json"},
                timeout=10.0,
            )
            status = getattr(resp, "status_code", 200)
            if status >= 400:
                raise ProviderError(self.name, f"HTTP {status}")
            data = resp.json() if hasattr(resp, "json") else {}
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name, f"{type(exc).__name__}: {exc}") from exc
        hits: list[SearchHit] = []
        for row in (data.get("web") or {}).get("results") or []:
            url = str(row.get("url") or "")
            title = str(row.get("title") or url)
            snippet = str(row.get("description") or "")
            if url and title:
                hits.append(SearchHit(
                    title=title, url=url, snippet=snippet[:400],
                    published=row.get("page_age") or row.get("age"),
                    provider=self.name,
                ))
        return hits[:num_results]


def parse_ddg_html(html: str, max_results: int) -> list[SearchHit]:
    results: list[SearchHit] = []
    blocks = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    for i, (url, title_html) in enumerate(blocks[:max_results]):
        actual_match = re.search(r"uddg=([^&]+)", url)
        actual_url = unquote(actual_match.group(1)) if actual_match else url
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
        if title and actual_url:
            results.append(SearchHit(title=title, url=actual_url, snippet=snippet, provider="duckduckgo"))
    return results


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    def enabled(self) -> bool:
        return True

    def search(
        self,
        query: str,
        num_results: int = 5,
        *,
        include_domains: Optional[list[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        http_get: Optional[HttpGet] = None,
        http_post: Optional[HttpPost] = None,
    ) -> list[SearchHit]:
        q = query
        if include_domains:
            q = query + " " + " OR ".join(f"site:{d}" for d in include_domains[:8])
        get = http_get or _httpx().get
        try:
            resp = get(
                "https://html.duckduckgo.com/html/",
                params={"q": q},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                },
                timeout=10,
                follow_redirects=True,
            )
            status = getattr(resp, "status_code", 200)
            if status >= 400:
                raise ProviderError(self.name, f"HTTP {status}")
            html = getattr(resp, "text", "") or ""
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name, f"{type(exc).__name__}: {exc}") from exc
        return parse_ddg_html(html, num_results)


def default_providers() -> list[SearchProvider]:
    return [ExaProvider(), TavilyProvider(), BraveProvider(), DuckDuckGoProvider()]


def run_providers(
    query: str,
    num_results: int = 5,
    *,
    include_domains: Optional[list[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    providers: Optional[list[SearchProvider]] = None,
    http_get: Optional[HttpGet] = None,
    http_post: Optional[HttpPost] = None,
) -> dict:
    """Try enabled providers in order. Fail closed when every attempt errors."""
    chain = providers or default_providers()
    attempts: list[ProviderAttempt] = []
    errors: list[str] = []
    last_empty_ok: Optional[str] = None

    for provider in chain:
        enabled = bool(provider.enabled())
        if not enabled:
            attempts.append(ProviderAttempt(name=provider.name, enabled=False))
            continue
        try:
            hits = provider.search(
                query,
                num_results,
                include_domains=include_domains,
                start_date=start_date,
                end_date=end_date,
                http_get=http_get,
                http_post=http_post,
            )
        except ProviderError as exc:
            logger.warning("[official_search] %s failed: %s", provider.name, exc.message)
            attempts.append(ProviderAttempt(name=provider.name, enabled=True, ok=False, error=exc.message))
            errors.append(str(exc))
            continue
        except Exception as exc:
            logger.warning("[official_search] %s failed: %s", provider.name, exc)
            attempts.append(ProviderAttempt(
                name=provider.name, enabled=True, ok=False, error=f"{type(exc).__name__}: {exc}",
            ))
            errors.append(f"{provider.name}: {type(exc).__name__}: {exc}")
            continue
        if hits:
            attempts.append(ProviderAttempt(name=provider.name, enabled=True, ok=True, count=len(hits)))
            return {
                "ok": True,
                "results": [h.as_dict() for h in hits],
                "source": provider.name,
                "attempts": [a.__dict__ for a in attempts],
                "error": None,
            }
        last_empty_ok = provider.name
        attempts.append(ProviderAttempt(name=provider.name, enabled=True, ok=True, count=0))

    if last_empty_ok:
        return {
            "ok": True,
            "results": [],
            "source": last_empty_ok,
            "attempts": [a.__dict__ for a in attempts],
            "error": None,
        }
    # Every enabled provider errored (or none were enabled — should not happen).
    return {
        "ok": False,
        "results": [],
        "source": None,
        "attempts": [a.__dict__ for a in attempts],
        "error": errors[0] if errors else "all_providers_failed",
    }
