"""Read full pages after a web search, then ground the research answer.

Search snippets are not an answer. For a factual or research question Max
fetches the top results in parallel, skips dead or paywalled pages, and
answers from the page text with dates, citations, and a verified/inference split.
"""
from __future__ import annotations

import html as html_mod
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urlparse

from app.services.max.answer_quality import enforce_reply_structure
from app.services.max.factual_guard import grounding_directive, undated_source_label

logger = logging.getLogger("max.web_research")

TARGET_MIN_PAGES = 3
TARGET_MAX_PAGES = 5
CANDIDATE_LIMIT = 8
FETCH_TIMEOUT_SECONDS = 8.0
MAX_PAGE_CHARS = 2500
MAX_HTML_CHARS = 400_000
MIN_PAGE_CHARS = 120

_PAYWALL_MARKERS = (
    "subscribe to continue",
    "subscription required",
    "subscribers only",
    "this article is for subscribers",
    "sign in to read",
    "sign in to continue",
    "to continue reading",
    "purchase a subscription",
    "already a subscriber",
    "member-only content",
    "members only",
    "paywall",
    "contenido exclusivo para suscriptores",
    "inicia sesión para leer",
    "inicie sesion para leer",
)

_PUBLISHED_KEYS = (
    "article:published_time",
    "og:published_time",
    "publishdate",
    "pubdate",
    "date",
    "datepublished",
    "dc.date",
    "dc.date.issued",
    "dcterms.created",
    "dcterms.date",
    "sailthru.date",
    "parsely-pub-date",
)
_UPDATED_KEYS = (
    "article:modified_time",
    "og:updated_time",
    "datemodified",
    "dcterms.modified",
    "article:modified",
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_BODY_DATE_RE = re.compile(
    r"(?:published|posted|updated|last updated|publicado|actualizado|fecha)\s*[:\-]?\s*"
    r"([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2})",
    re.I,
)

FetchFn = Callable[[str, float], dict]


def normalize_date(value: str | None) -> str | None:
    """Return YYYY-MM-DD when a publication string contains a real calendar date."""
    if not value:
        return None
    text = html_mod.unescape(str(value)).strip()
    # Allow a time suffix (2024-05-02T12:00:00Z). A word boundary fails there
    # because both the day and the "T" are word characters.
    iso = re.search(r"\b((?:19|20)\d{2})-(\d{1,2})-(\d{1,2})(?!\d)", text)
    if iso:
        return _ymd(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    month_first = re.search(
        r"\b([A-Za-z]{3,12})\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d{2})\b",
        text,
    )
    if month_first and month_first.group(1).lower() in _MONTHS:
        return _ymd(int(month_first.group(3)), _MONTHS[month_first.group(1).lower()], int(month_first.group(2)))
    day_first = re.search(
        r"\b(\d{1,2})\s+(?:de\s+)?([A-Za-z]{3,12})\s+(?:de\s+)?((?:19|20)\d{2})\b",
        text,
    )
    if day_first and day_first.group(2).lower() in _MONTHS:
        return _ymd(int(day_first.group(3)), _MONTHS[day_first.group(2).lower()], int(day_first.group(1)))
    return None


def extract_dates(html: str) -> tuple[str | None, str | None]:
    """Pull publication and updated dates from metadata, JSON-LD, or visible text."""
    raw = html or ""
    meta = _meta_values(raw)
    published = _first_normalized(meta, _PUBLISHED_KEYS)
    updated = _first_normalized(meta, _UPDATED_KEYS)
    ld_published, ld_updated = _jsonld_dates(raw)
    published = published or ld_published
    updated = updated or ld_updated
    if not published:
        stamp = re.search(r"<time\b[^>]*\bdatetime\s*=\s*['\"]([^'\"]+)['\"]", raw, re.I)
        if stamp:
            published = normalize_date(stamp.group(1))
    if not published or not updated:
        visible = html_to_text(raw)[:2500]
        for match in _BODY_DATE_RE.finditer(visible):
            found = normalize_date(match.group(1))
            if not found:
                continue
            label = match.group(0).lower()
            if any(word in label for word in ("updated", "actualizado", "modified")):
                updated = updated or found
            else:
                published = published or found
            if published and updated:
                break
    return published, updated


def html_to_text(html: str) -> str:
    """Strip scripts and layout chrome, leaving readable article text."""
    text = re.sub(r"(?is)<(script|style|noscript|svg)\b[^>]*>.*?</\1>", " ", html or "")
    text = re.sub(r"(?is)<(nav|header|footer|aside|form)\b[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "- ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def default_fetch(url: str, timeout: float) -> dict:
    """GET one page. Failures return a dead outcome instead of raising."""
    import httpx

    try:
        response = httpx.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
            },
            timeout=httpx.Timeout(timeout, connect=min(3.0, timeout)),
            follow_redirects=True,
        )
        body = response.text[:MAX_HTML_CHARS] if response.text else ""
        return {
            "status": response.status_code,
            "text": body,
            "content_type": response.headers.get("content-type", ""),
            "error": None,
            "final_url": str(response.url),
        }
    except Exception as exc:
        return {
            "status": 0,
            "text": "",
            "content_type": "",
            "error": type(exc).__name__,
            "final_url": url,
        }


def read_search_results(
    results: list[dict],
    *,
    fetch: FetchFn | None = None,
    question: str | None = None,
    target_min: int = TARGET_MIN_PAGES,
    target_max: int = TARGET_MAX_PAGES,
    candidate_limit: int = CANDIDATE_LIMIT,
    timeout: float = FETCH_TIMEOUT_SECONDS,
    max_chars: int = MAX_PAGE_CHARS,
    skip_urls: set[str] | None = None,
) -> dict[str, list]:
    """Fetch the top relevant hits until 3–5 readable pages are in hand.

    Dead and paywalled URLs are skipped and the next ranked result is tried.
    Each wave runs in parallel. The first wave is the top ``target_max`` hits;
    a shortfall triggers one more parallel wave.
    """
    fetch_fn = fetch or default_fetch
    undated = undated_source_label(question)
    skip = {item.rstrip("/") for item in (skip_urls or set())}
    candidates: list[dict] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not _is_candidate_url(url) or url.rstrip("/") in skip:
            continue
        candidates.append(item)
        if len(candidates) >= candidate_limit:
            break

    pages: list[dict] = []
    skipped: list[dict] = []
    index = 0
    while index < len(candidates) and len(pages) < target_min:
        wave_size = target_max if not pages else max(target_max - len(pages), 1)
        wave = candidates[index:index + wave_size]
        index += len(wave)
        if not wave:
            break
        fetched = _fetch_parallel(wave, fetch_fn, timeout)
        for item in wave:
            url = str(item.get("url") or "").strip()
            outcome = fetched.get(url) or {
                "status": 0, "text": "", "error": "missing", "content_type": "",
            }
            parsed = _interpret_page(item, outcome, max_chars=max_chars, undated_label=undated)
            if parsed.get("ok"):
                pages.append({key: value for key, value in parsed.items() if key != "ok"})
                if len(pages) >= target_max:
                    break
            else:
                skipped.append({
                    "url": url,
                    "title": str(item.get("title") or ""),
                    "reason": parsed.get("reason") or "dead",
                })
        if len(pages) >= target_min:
            break
    report = {"pages": pages[:target_max], "skipped": skipped}
    logger.info(
        "research pages read=%s skipped=%s",
        len(report["pages"]),
        len(report["skipped"]),
    )
    return report


def page_tool_entries(pages: list[dict]) -> list[dict]:
    """Shape page reads as web_read tool results for grounding and transcripts."""
    entries = []
    for page in pages:
        text = page.get("text") or ""
        entries.append({
            "tool": "web_read",
            "success": True,
            "result": {
                "url": page.get("url"),
                "title": page.get("title"),
                "content": text,
                "length": len(text),
                "published": page.get("published"),
                "updated": page.get("updated"),
                "date_label": page.get("date_label"),
            },
        })
    return entries


def build_grounded_search_message(
    question: str,
    search_payload: dict | None,
    pages: list[dict],
    skipped: list[dict] | None = None,
) -> str:
    """System message: page text, dates, and the answer contract. Not snippets."""
    payload = search_payload or {}
    lines = [
        grounding_directive(question),
        "",
        "Do not call web_read or web_search again for these URLs. "
        "The pages below are already loaded. Answer now.",
        "",
    ]
    if pages:
        lines.append("Fetched pages:")
        for index, page in enumerate(pages, start=1):
            lines.append(f"\n[{index}] {page.get('title') or page.get('url')}")
            lines.append(f"URL: {page.get('url')}")
            lines.append(f"Source date: {page.get('date_label')}")
            if page.get("published"):
                lines.append(f"Published: {page['published']}")
            if page.get("updated") and page.get("updated") != page.get("published"):
                lines.append(f"Updated: {page['updated']}")
            lines.append(page.get("text") or "")
    else:
        lines.append(
            "None of the result pages could be read (dead or paywalled). "
            "Say that plainly. Do not invent specifications, and do not offer to open the articles."
        )
        undated = undated_source_label(question)
        for index, item in enumerate((payload.get("results") or [])[:5], start=1):
            if not isinstance(item, dict):
                continue
            lines.append(
                f"\n[{index}] {item.get('title') or 'Result'}\n"
                f"URL: {item.get('url')}\n"
                f"Source date: {undated}\n"
                f"Snippet only — page not read: {item.get('snippet') or ''}"
            )
    if skipped:
        lines.append("\nPages skipped (do not cite these as read):")
        for item in skipped:
            lines.append(f"- {item.get('url')} ({item.get('reason')})")
    lines.append(f"\nQuestion: {question}")
    return "\n".join(lines)


def ground_web_search(
    question: str,
    search_payload: dict,
    *,
    fetch: FetchFn | None = None,
    skip_urls: set[str] | None = None,
) -> dict[str, Any]:
    """Read pages for one web_search payload and build the grounded prompt."""
    payload = search_payload or {}
    report = read_search_results(
        payload.get("results") or [],
        fetch=fetch,
        question=question,
        skip_urls=skip_urls,
    )
    return {
        "pages": report["pages"],
        "skipped": report["skipped"],
        "tool_entries": page_tool_entries(report["pages"]),
        "message": build_grounded_search_message(
            question, payload, report["pages"], report["skipped"],
        ),
    }


def run_research_answer(
    question: str,
    search_results: list[dict],
    *,
    fetch: FetchFn,
    generate: Callable[[str, int], str],
) -> dict[str, Any]:
    """End-to-end research answer: read pages, draft, regenerate or fill structure."""
    grounded = ground_web_search(
        question,
        {"query": question, "results": search_results, "count": len(search_results)},
        fetch=fetch,
    )
    prompt = grounded["message"]

    def _regenerate(issues: list[str]) -> str:
        fix = (
            "The draft failed structural checks: " + ", ".join(issues) + ". "
            "Rewrite the full answer from the fetched pages. Remove empty sections "
            "and do not offer to open articles."
        )
        return generate(prompt + "\n\n" + fix, 2)

    draft = generate(prompt, 1)
    answer = enforce_reply_structure(draft, regenerate=_regenerate)
    return {"answer": answer, "prompt": prompt, "pages": grounded["pages"]}


def _ymd(year: int, month: int, day: int) -> str | None:
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def _meta_values(html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in re.findall(r"<meta\b[^>]*>", html, flags=re.I):
        key = None
        for attr in ("property", "name", "itemprop"):
            match = re.search(rf"{attr}\s*=\s*['\"]([^'\"]+)['\"]", tag, re.I)
            if match:
                key = match.group(1).strip().lower()
                break
        content = re.search(r"content\s*=\s*['\"]([^'\"]+)['\"]", tag, re.I)
        if key and content and key not in found:
            found[key] = content.group(1).strip()
    return found


def _first_normalized(meta: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in meta:
            found = normalize_date(meta[key])
            if found:
                return found
    return None


def _jsonld_dates(html: str) -> tuple[str | None, str | None]:
    published = updated = None
    for match in re.finditer(r'"datePublished"\s*:\s*"([^"]+)"', html, re.I):
        published = published or normalize_date(match.group(1))
    for match in re.finditer(r'"dateModified"\s*:\s*"([^"]+)"', html, re.I):
        updated = updated or normalize_date(match.group(1))
    return published, updated


def _is_candidate_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host.endswith("duckduckgo.com"):
        return False
    if host.endswith("google.com") and parsed.path.startswith("/search"):
        return False
    return True


def _fetch_parallel(wave: list[dict], fetch_fn: FetchFn, timeout: float) -> dict[str, dict]:
    urls = [str(item.get("url") or "").strip() for item in wave]
    if len(urls) == 1:
        return {urls[0]: _safe_fetch(fetch_fn, urls[0], timeout)}
    fetched: dict[str, dict] = {}
    workers = min(5, len(urls))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(_safe_fetch, fetch_fn, url, timeout): url for url in urls
        }
        for future in as_completed(future_map):
            fetched[future_map[future]] = future.result()
    return fetched


def _safe_fetch(fetch_fn: FetchFn, url: str, timeout: float) -> dict:
    try:
        result = fetch_fn(url, timeout)
    except Exception as exc:
        return {"status": 0, "text": "", "error": type(exc).__name__, "content_type": ""}
    if not isinstance(result, dict):
        return {"status": 0, "text": "", "error": "bad_fetch", "content_type": ""}
    return result


def _interpret_page(item: dict, outcome: dict, *, max_chars: int, undated_label: str) -> dict:
    url = str(item.get("url") or "").strip()
    title = str(item.get("title") or "").strip()
    status = int(outcome.get("status") or 0)
    error = outcome.get("error")
    raw = outcome.get("text") or ""
    content_type = (outcome.get("content_type") or "").lower()
    if error or status == 0:
        return {"ok": False, "reason": "dead"}
    if _is_unreadable(content_type, raw):
        return {"ok": False, "reason": "dead"}
    if _is_html(content_type, raw):
        published, updated = extract_dates(raw)
        text = html_to_text(raw)
        if not title:
            title = _html_title(raw)
    else:
        published, updated = extract_dates(raw)
        text = raw.strip()
    text = _truncate(text, max_chars)
    if status in {401, 402, 451} or _looks_paywalled(status, text, raw):
        return {"ok": False, "reason": "paywalled"}
    if status >= 400 or len(text) < MIN_PAGE_CHARS:
        return {"ok": False, "reason": "dead"}
    if published:
        date_label = published
    elif updated:
        date_label = updated
    else:
        date_label = undated_label
    return {
        "ok": True,
        "url": url,
        "title": title or url,
        "text": text,
        "published": published,
        "updated": updated,
        "date_label": date_label,
    }


def _is_html(content_type: str, raw: str) -> bool:
    if "html" in content_type or "xml" in content_type:
        return True
    head = raw.lstrip()[:300].lower()
    return head.startswith("<!doctype html") or "<html" in head or "<meta" in head


def _is_unreadable(content_type: str, raw: str) -> bool:
    if any(token in content_type for token in ("pdf", "image/", "audio/", "video/", "zip", "octet-stream")):
        return True
    return raw.lstrip()[:5].startswith("%PDF")


def _looks_paywalled(status: int, text: str, raw: str) -> bool:
    if status in {401, 402, 451}:
        return True
    blob = (text or "")[:2000].lower()
    raw_head = (raw or "")[:2500].lower()
    in_text = any(marker in blob for marker in _PAYWALL_MARKERS)
    in_raw = any(marker in raw_head for marker in _PAYWALL_MARKERS)
    if not in_text and not in_raw:
        return False
    if len(text) >= 1500 and not any(marker in text[:600].lower() for marker in _PAYWALL_MARKERS):
        return False
    return True


def _html_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", html_to_text(match.group(1))).strip()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[truncated]"
