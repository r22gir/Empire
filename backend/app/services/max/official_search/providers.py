"""Free-tier search providers with a documented fallback order.

Dell live tests (2026-10): DuckDuckGo resets most connections. Brave is
already keyed on studio and is the default raw provider when
``BRAVE_API_KEY`` exists (Goggles + allowlist boosts) and the monthly
free-credit cap is open (``BRAVE_MONTHLY_FREE_REQUESTS``, default 900).
At the cap Brave is skipped automatically. MiniMax Token Plan MCP
``POST /v1/coding_plan/search`` is a second raw source (no domain
filter) merged/deduped with Brave, then run through the trust layer.

Exa and Tavily are free fallbacks. DuckDuckGo is last. The MiniMax
Responses API server-tool ``web_search`` is never used as an answer engine.
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
    env_flag,
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
    """MiniMax Responses API / server-tool web_search stays OFF as an answer engine."""
    return env_bool("MINIMAX_WEB_SEARCH_FOR_RESEARCH", False)


def minimax_api_key() -> str:
    """Edition-scoped MiniMax key, then the process MINIMAX_API_KEY (plan quota)."""
    return edition_key("MINIMAX_API_KEY") or env_flag("MINIMAX_API_KEY")


def minimax_coding_plan_enabled() -> bool:
    """Token Plan MCP search is on when a MiniMax key exists (included in plan quota)."""
    if env_bool("MINIMAX_CODING_PLAN_SEARCH", True) is False:
        return False
    if env_flag("MINIMAX_CODING_PLAN_SEARCH").lower() in {"off", "0", "false", "no"}:
        return False
    return bool(minimax_api_key())


def _brave_key_and_budget() -> bool:
    """Brave is on only with a key AND remaining monthly free credit."""
    if not edition_key("BRAVE_API_KEY"):
        return False
    from app.services.max.official_search.brave_budget import brave_budget_available
    return brave_budget_available()


def provider_fallback_order() -> list[str]:
    """Enabled providers. Brave + MiniMax coding-plan merge first; DDG last.

    Brave drops out automatically at the monthly free-credit cap so
    MiniMax Token Plan + Exa/Tavily + DuckDuckGo take over.
    """
    names: list[str] = []
    if _brave_key_and_budget():
        names.append("brave")
    if minimax_coding_plan_enabled():
        names.append("minimax_coding_plan")
    if edition_key("EXA_API_KEY"):
        names.append("exa")
    if edition_key("TAVILY_API_KEY"):
        names.append("tavily")
    names.append("duckduckgo")
    return names


PROVIDER_ORDER = ("brave", "minimax_coding_plan", "exa", "tavily", "duckduckgo")
MERGE_PROVIDERS = frozenset({"brave", "minimax_coding_plan"})


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
    """Pluggable Brave Search + Goggles adapter.

    Stays OFF without ``BRAVE_API_KEY`` and when the monthly free-credit
    cap is reached. The reserve happens before any HTTP call so we never
    exceed ``BRAVE_MONTHLY_FREE_REQUESTS``.
    """

    name = "brave"

    def enabled(self) -> bool:
        return _brave_key_and_budget()

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
        from app.services.max.official_search.brave_budget import reserve_brave_request
        if not reserve_brave_request():
            logger.info("[official_search] Brave monthly cap reached — skipping HTTP")
            return []
        params: dict = {"q": query, "count": max(num_results, 10), "extra_snippets": True}
        goggles = brave_goggles()
        if goggles:
            params["goggles_id"] = goggles
        if include_domains:
            # Allowlist boost: site: operators plus a hard post-filter below.
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
        if include_domains:
            allowed = {d.lower().lstrip(".") for d in include_domains}
            hits = [
                h for h in hits
                if any(
                    (urlparse_host(h.url) == d or urlparse_host(h.url).endswith("." + d))
                    for d in allowed
                )
            ]
        return hits[:num_results]


def urlparse_host(url: str) -> str:
    from urllib.parse import urlparse
    host = (urlparse(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


class MiniMaxCodingPlanProvider(SearchProvider):
    """Token Plan MCP search: POST /v1/coding_plan/search {\"q\": query}.

    Raw source only — no domain filter. Results go through the trust layer.
    This is not the Responses API server-tool web_search.
    """

    name = "minimax_coding_plan"

    def enabled(self) -> bool:
        return minimax_coding_plan_enabled()

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
        key = minimax_api_key()
        if not key:
            return []
        base = env_flag("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
        post = http_post or _httpx().post
        try:
            resp = post(
                f"{base}/coding_plan/search",
                json={"q": query},
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=8.0,
            )
            status = getattr(resp, "status_code", 200)
            if status >= 400:
                raise ProviderError(self.name, f"HTTP {status}")
            data = resp.json() if hasattr(resp, "json") else {}
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name, f"{type(exc).__name__}: {exc}") from exc
        rows = (
            data.get("results")
            or data.get("data")
            or data.get("items")
            or (data.get("web") or {}).get("results")
            or []
        )
        hits: list[SearchHit] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = str(row.get("url") or row.get("link") or row.get("href") or "")
            title = str(row.get("title") or row.get("name") or url)
            snippet = str(row.get("snippet") or row.get("content") or row.get("description") or "")
            published = row.get("date") or row.get("published") or row.get("published_date")
            if url and title:
                hits.append(SearchHit(
                    title=title, url=url, snippet=snippet[:400],
                    published=str(published) if published else None,
                    provider=self.name,
                ))
        return hits[: max(num_results, 10)]


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
                timeout=6,
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
    return [
        BraveProvider(),
        MiniMaxCodingPlanProvider(),
        ExaProvider(),
        TavilyProvider(),
        DuckDuckGoProvider(),
    ]


def _norm_url(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def merge_hits(groups: list[list[SearchHit]], limit: int = 10) -> list[SearchHit]:
    """Dedupe by URL (Brave + MiniMax coding-plan raw merge)."""
    seen: set[str] = set()
    out: list[SearchHit] = []
    for group in groups:
        for hit in group:
            key = _norm_url(hit.url)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(hit)
            if len(out) >= limit:
                return out
    return out


def _search_one(
    provider: SearchProvider,
    query: str,
    num_results: int,
    include_domains,
    start_date,
    end_date,
    http_get,
    http_post,
) -> list[SearchHit]:
    return provider.search(
        query,
        num_results,
        include_domains=include_domains,
        start_date=start_date,
        end_date=end_date,
        http_get=http_get,
        http_post=http_post,
    )


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
    """Brave + MiniMax coding-plan merge first; Exa/Tavily/DDG fallback.

    Fail closed when every enabled provider errors.
    """
    chain = providers or default_providers()
    attempts: list[ProviderAttempt] = []
    errors: list[str] = []
    last_empty_ok: Optional[str] = None
    merge_groups: list[list[SearchHit]] = []
    merge_sources: list[str] = []

    def _record_error(name: str, message: str) -> None:
        attempts.append(ProviderAttempt(name=name, enabled=True, ok=False, error=message))
        errors.append(f"{name}: {message}")

    for provider in chain:
        is_merge = provider.name in MERGE_PROVIDERS
        if merge_groups and not is_merge:
            # Already have raw merged hits — skip free/DDG fallbacks.
            break
        enabled = bool(provider.enabled())
        if not enabled:
            attempts.append(ProviderAttempt(name=provider.name, enabled=False))
            continue
        try:
            hits = _search_one(
                provider, query, num_results, include_domains,
                start_date, end_date, http_get, http_post,
            )
        except ProviderError as exc:
            logger.warning("[official_search] %s failed: %s", provider.name, exc.message)
            _record_error(provider.name, exc.message)
            continue
        except Exception as exc:
            logger.warning("[official_search] %s failed: %s", provider.name, exc)
            _record_error(provider.name, f"{type(exc).__name__}: {exc}")
            continue
        attempts.append(ProviderAttempt(name=provider.name, enabled=True, ok=True, count=len(hits)))
        if is_merge:
            if hits:
                merge_groups.append(hits)
                merge_sources.append(provider.name)
            else:
                last_empty_ok = provider.name
            continue
        if hits:
            return {
                "ok": True,
                "results": [h.as_dict() for h in hits],
                "source": provider.name,
                "attempts": [a.__dict__ for a in attempts],
                "error": None,
            }
        last_empty_ok = provider.name

    merged = merge_hits(merge_groups, limit=max(num_results, 10))
    if merged:
        return {
            "ok": True,
            "results": [h.as_dict() for h in merged],
            "source": "+".join(merge_sources) if merge_sources else "merged",
            "attempts": [a.__dict__ for a in attempts],
            "error": None,
        }
    if last_empty_ok:
        return {
            "ok": True,
            "results": [],
            "source": last_empty_ok,
            "attempts": [a.__dict__ for a in attempts],
            "error": None,
        }
    return {
        "ok": False,
        "results": [],
        "source": None,
        "attempts": [a.__dict__ for a in attempts],
        "error": errors[0] if errors else "all_providers_failed",
    }
