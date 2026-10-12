"""Optional free authoritative API tools. No paid providers."""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional
from urllib.parse import quote_plus

from app.services.max.official_search.config import (
    env_flag,
    sec_user_agent,
    shared_free_key,
)

logger = logging.getLogger("max.official_search.authoritative")

HttpGet = Callable[..., object]


def _json(resp: Any) -> dict:
    if resp is None:
        return {}
    if hasattr(resp, "json"):
        try:
            return resp.json() or {}
        except Exception:
            return {}
    return {}


def _get(http_get: Optional[HttpGet], url: str, **kwargs):
    if http_get is None:
        import httpx
        kwargs.setdefault("timeout", 12.0)
        kwargs.setdefault("follow_redirects", True)
        return httpx.get(url, **kwargs)
    return http_get(url, **kwargs)


def congress_search(params: dict, *, http_get: Optional[HttpGet] = None) -> dict:
    """Congress.gov v3 (api.data.gov key). Free."""
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required", "results": []}
    key = shared_free_key("CONGRESS_GOV_API_KEY") or shared_free_key("DATA_GOV_API_KEY")
    url = "https://api.congress.gov/v3/bill"
    try:
        resp = _get(
            http_get, url,
            params={"query": query, "limit": min(int(params.get("limit", 5)), 20), "format": "json", "api_key": key},
            headers={"Accept": "application/json"},
        )
        status = getattr(resp, "status_code", 200)
        if key == "" and status >= 400:
            return {"ok": False, "error": "DATA_GOV_API_KEY or CONGRESS_GOV_API_KEY is required", "results": []}
        if status >= 400:
            return {"ok": False, "error": f"HTTP {status}", "results": []}
        data = _json(resp)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "results": []}
    results = []
    for bill in data.get("bills") or []:
        number = bill.get("number") or bill.get("type") or ""
        title = bill.get("title") or str(number)
        congress = bill.get("congress")
        href = ((bill.get("url") or "") if isinstance(bill.get("url"), str)
                else (bill.get("url") or {}).get("href") if isinstance(bill.get("url"), dict) else "")
        results.append({
            "title": title,
            "url": href or f"https://www.congress.gov/search?q={quote_plus(title)}",
            "snippet": f"Congress {congress} {bill.get('type', '')} {number}".strip(),
            "tier": 1,
            "provider": "congress.gov",
        })
    return {"ok": True, "results": results, "source": "congress.gov", "query": query}


def regulations_search(params: dict, *, http_get: Optional[HttpGet] = None) -> dict:
    """Regulations.gov v4 (api.data.gov key). Free."""
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required", "results": []}
    key = shared_free_key("REGULATIONS_GOV_API_KEY") or shared_free_key("DATA_GOV_API_KEY")
    if not key:
        return {"ok": False, "error": "DATA_GOV_API_KEY or REGULATIONS_GOV_API_KEY is required", "results": []}
    try:
        resp = _get(
            http_get,
            "https://api.regulations.gov/v4/documents",
            params={"filter[searchTerm]": query, "page[size]": min(int(params.get("limit", 5)), 20), "api_key": key},
            headers={"Accept": "application/json"},
        )
        status = getattr(resp, "status_code", 200)
        if status >= 400:
            return {"ok": False, "error": f"HTTP {status}", "results": []}
        data = _json(resp)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "results": []}
    results = []
    for row in data.get("data") or []:
        attrs = row.get("attributes") or {}
        title = attrs.get("title") or row.get("id") or "Document"
        doc_id = row.get("id") or ""
        results.append({
            "title": title,
            "url": f"https://www.regulations.gov/document/{doc_id}" if doc_id else "https://www.regulations.gov",
            "snippet": attrs.get("docketId") or attrs.get("documentType") or "",
            "tier": 1,
            "provider": "regulations.gov",
        })
    return {"ok": True, "results": results, "source": "regulations.gov", "query": query}


def pubmed_search(params: dict, *, http_get: Optional[HttpGet] = None) -> dict:
    """PubMed E-utilities. Free, no key required."""
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required", "results": []}
    try:
        resp = _get(
            http_get,
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": min(int(params.get("limit", 5)), 20),
                "email": env_flag("PUBMED_EMAIL", "max@empirebox.store"),
                "tool": "empirebox-max",
            },
        )
        data = _json(resp)
        ids = ((data.get("esearchresult") or {}).get("idlist")) or []
        if not ids:
            return {"ok": True, "results": [], "source": "pubmed", "query": query}
        summary = _get(
            http_get,
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        )
        payload = _json(summary).get("result") or {}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "results": []}
    results = []
    for pmid in ids:
        row = payload.get(pmid) or {}
        title = row.get("title") or pmid
        results.append({
            "title": title,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "snippet": row.get("source") or row.get("fulljournalname") or "",
            "published": (row.get("pubdate") or "")[:10],
            "tier": 1,
            "provider": "pubmed",
        })
    return {"ok": True, "results": results, "source": "pubmed", "query": query}


def sec_edgar_search(params: dict, *, http_get: Optional[HttpGet] = None) -> dict:
    """SEC EDGAR full-text search. Free; User-Agent required."""
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required", "results": []}
    try:
        resp = _get(
            http_get,
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": query, "dateRange": "custom", "startdt": params.get("start_date") or "2000-01-01"},
            headers={"User-Agent": sec_user_agent(), "Accept": "application/json"},
        )
        status = getattr(resp, "status_code", 200)
        if status >= 400:
            return {"ok": False, "error": f"HTTP {status}", "results": []}
        data = _json(resp)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "results": []}
    hits = ((data.get("hits") or {}).get("hits")) or []
    results = []
    for row in hits[: min(int(params.get("limit", 5)), 20)]:
        src = row.get("_source") or {}
        cik = str(src.get("ciks", [""])[0] if isinstance(src.get("ciks"), list) else src.get("cik") or "")
        adsh = src.get("adsh") or ""
        title = src.get("display_names", [query])[0] if src.get("display_names") else (src.get("entity") or query)
        file_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{adsh.replace('-', '')}/{adsh}-index.html" if cik and adsh else "https://www.sec.gov/edgar/search/"
        results.append({
            "title": str(title),
            "url": file_url,
            "snippet": src.get("file_description") or src.get("form") or "",
            "tier": 1,
            "provider": "sec_edgar",
        })
    return {"ok": True, "results": results, "source": "sec_edgar", "query": query}


def wikipedia_search(params: dict, *, http_get: Optional[HttpGet] = None) -> dict:
    """Wikipedia + Wikidata search. Free, no key."""
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required", "results": []}
    lang = str(params.get("language") or "en")[:8]
    results = []
    try:
        wiki = _get(
            http_get,
            f"https://{lang}.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query, "format": "json", "utf8": 1},
            headers={"User-Agent": sec_user_agent()},
        )
        for row in ((_json(wiki).get("query") or {}).get("search") or [])[:5]:
            title = row.get("title") or query
            slug = quote_plus(title.replace(" ", "_"))
            results.append({
                "title": title,
                "url": f"https://{lang}.wikipedia.org/wiki/{slug}",
                "snippet": re_sub_tags(row.get("snippet") or ""),
                "tier": 1,
                "provider": "wikipedia",
            })
        wikidata = _get(
            http_get,
            "https://www.wikidata.org/w/api.php",
            params={"action": "wbsearchentities", "search": query, "language": lang, "format": "json"},
            headers={"User-Agent": sec_user_agent()},
        )
        for row in (_json(wikidata).get("search") or [])[:3]:
            results.append({
                "title": row.get("label") or query,
                "url": row.get("concepturi") or f"https://www.wikidata.org/wiki/{row.get('id', '')}",
                "snippet": row.get("description") or "",
                "tier": 1,
                "provider": "wikidata",
            })
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "results": results}
    return {"ok": True, "results": results, "source": "wikipedia", "query": query}


def re_sub_tags(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html or "")


def fact_check_search(params: dict, *, http_get: Optional[HttpGet] = None) -> dict:
    """Google Fact Check Tools API. Optional key; stays off without it."""
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        return {"ok": False, "error": "Query is required", "results": []}
    key = shared_free_key("GOOGLE_FACTCHECK_API_KEY")
    if not key:
        return {"ok": False, "error": "GOOGLE_FACTCHECK_API_KEY is not set", "results": [], "disabled": True}
    try:
        resp = _get(
            http_get,
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={"query": query, "key": key, "pageSize": min(int(params.get("limit", 5)), 20)},
        )
        status = getattr(resp, "status_code", 200)
        if status >= 400:
            return {"ok": False, "error": f"HTTP {status}", "results": []}
        data = _json(resp)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "results": []}
    results = []
    for claim in data.get("claims") or []:
        review = (claim.get("claimReview") or [{}])[0]
        results.append({
            "title": claim.get("text") or review.get("title") or query,
            "url": review.get("url") or "",
            "snippet": review.get("textualRating") or "",
            "tier": 2,
            "provider": "google_factcheck",
        })
    return {"ok": True, "results": results, "source": "google_factcheck", "query": query}


AUTHORITATIVE_TOOLS = {
    "congress_search": congress_search,
    "regulations_search": regulations_search,
    "pubmed_search": pubmed_search,
    "sec_edgar_search": sec_edgar_search,
    "wikipedia_search": wikipedia_search,
    "fact_check_search": fact_check_search,
}
