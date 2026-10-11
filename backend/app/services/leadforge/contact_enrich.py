"""
LeadForge free contact lookup.

For a prospect with its own website, fetch the home page plus up to a few
contact / about / team pages and pull out:
  owner or principal name (+ title), email, phone, Instagram, Facebook, LinkedIn.

Rules:
  * Free only: plain HTTP GETs to the business's own site. No paid APIs.
  * robots.txt is checked for every URL (urllib.robotparser); disallowed = skipped.
  * Rate limited: one request at a time per domain, MIN_DELAY_S between requests,
    small global concurrency, hard page cap per site, size + time caps per page.
  * Directory / social sites (Yelp, Houzz, Facebook, ...) are never scraped.
  * Results are stored on the prospect row (contact_* / instagram / facebook /
    linkedin / enrichment_*). Existing values are never overwritten with blanks.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import urllib.robotparser
from datetime import datetime
from html import unescape
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

from app.services.leadforge import prospect_engine as pe

USER_AGENT = "EmpireLeadForgeBot/1.0 (free contact lookup; respects robots.txt)"
MIN_DELAY_S = 2.0          # between requests to the same domain
MAX_PAGES_PER_SITE = 5     # home + up to 4 contact/about/team pages
MAX_BYTES = 1_500_000
PAGE_TIMEOUT_S = 10.0
GLOBAL_CONCURRENCY = 2     # sites processed in parallel
MAX_BATCH = 25             # per call

_CONTACT_HINTS = ("contact", "about", "team", "our-story", "meet", "staff", "people", "leadership", "who-we-are", "founder", "studio")
_FALLBACK_PATHS = ("/contact", "/contact-us", "/about", "/about-us", "/team", "/our-team")

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?([2-9]\d{2})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})(?!\d)")
_BAD_EMAIL_PARTS = ("example.", "sentry", "wixpress", "domain.com", "email.com", "yourname", "@2x", ".png", ".jpg",
                    ".jpeg", ".gif", ".webp", ".svg", "godaddy", "squarespace", "wordpress", "noreply", "no-reply")
_TITLES = ("Owner", "Co-Owner", "Founder", "Co-Founder", "Principal", "Principal Designer", "President", "CEO",
           "Lead Designer", "Creative Director", "Design Director", "Managing Partner", "Managing Director", "Partner")
_TITLE_RE = "|".join(sorted((re.escape(t) for t in _TITLES), key=len, reverse=True))
_NAME = r"([A-Z][a-z]+(?:[ '-][A-Z][a-zA-Z'.-]+){1,2})"
_NAME_THEN_TITLE = re.compile(_NAME + r"\s*(?:,|–|—|-|\||:|\bis\b(?: the)?|\bour\b)?\s*(?:and\s+)?(" + _TITLE_RE + r")\b")
_TITLE_THEN_NAME = re.compile(r"\b(" + _TITLE_RE + r")\s*(?:,|:|–|—|-|\|)?\s*" + _NAME)
_MEET_RE = re.compile(r"\bMeet\s+" + _NAME)
_NOT_NAMES = {"Interior Design", "Design Studio", "Contact Us", "About Us", "Our Team", "Read More", "Learn More",
              "Home Page", "Privacy Policy", "Washington Dc", "United States", "Our Story", "Get Started",
              "Design Group", "Kitchen Bath", "Book Now", "Free Consultation", "General Contractor"}

_SOCIAL_PATTERNS = {
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]{2,30})/?(?=[\"'?#\s<]|$)", re.I),
    "facebook": re.compile(r"https?://(?:www\.|m\.)?facebook\.com/([A-Za-z0-9_.-]{2,80})/?(?=[\"'?#\s<]|$)", re.I),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(company|in)/([A-Za-z0-9_-]{2,100})/?", re.I),
}
_SOCIAL_SKIP = {"p", "explore", "reel", "reels", "stories", "sharer", "sharer.php", "share", "tr", "plugins", "dialog",
                "accounts", "about", "legal", "privacy", "help", "login", "intent", "home.php", "pages", "groups",
                "instagram", "facebook", "events", "watch", "hashtag"}


class _DomainLimiter:
    """Serialises requests per domain with MIN_DELAY_S spacing."""

    def __init__(self) -> None:
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last: Dict[str, float] = {}

    async def wait(self, host: str) -> asyncio.Lock:
        lock = self._locks.setdefault(host, asyncio.Lock())
        await lock.acquire()
        gap = time.monotonic() - self._last.get(host, 0.0)
        if gap < MIN_DELAY_S:
            await asyncio.sleep(MIN_DELAY_S - gap)
        return lock

    def done(self, host: str, lock: asyncio.Lock) -> None:
        self._last[host] = time.monotonic()
        lock.release()


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|section|span|a)>", "\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    return re.sub(r"[ \t\r\f\v]+", " ", text)


def _clean_email(e: str) -> Optional[str]:
    e = e.strip().strip(".").lower()
    if any(b in e for b in _BAD_EMAIL_PARTS) or len(e) > 80:
        return None
    return e


def _fmt_phone(m: re.Match) -> str:
    return f"({m.group(1)}) {m.group(2)}-{m.group(3)}"


def _site_root(url: str) -> Optional[str]:
    u = urlparse(url if "://" in url else f"https://{url}")
    if not u.netloc:
        return None
    return f"{u.scheme or 'https'}://{u.netloc}"


def _registrable(host: str) -> str:
    host = host.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def _extract(html: str, page_url: str, site_host: str) -> dict:
    """Pull contact signals out of one page."""
    out: dict = {"emails": [], "phones": [], "social": {}, "people": [], "links": []}
    # mailto / tel first (most reliable)
    for m in re.finditer(r'(?i)href=["\']mailto:([^"\'?]+)', html):
        e = _clean_email(unescape(m.group(1)))
        if e:
            out["emails"].append(e)
    for m in re.finditer(r'(?i)href=["\']tel:([^"\']+)', html):
        pm = _PHONE_RE.search(unescape(m.group(1)))
        if pm:
            out["phones"].append(_fmt_phone(pm))
    text = _html_to_text(html)
    for m in _EMAIL_RE.finditer(text):
        e = _clean_email(m.group(0))
        if e:
            out["emails"].append(e)
    for m in _PHONE_RE.finditer(text):
        out["phones"].append(_fmt_phone(m))
    # social links
    for kind, rx in _SOCIAL_PATTERNS.items():
        for m in rx.finditer(html):
            if kind == "linkedin":
                handle = f"{m.group(1)}/{m.group(2)}"
                url = f"https://www.linkedin.com/{handle}"
            else:
                handle = m.group(1)
                if handle.lower() in _SOCIAL_SKIP:
                    continue
                url = f"https://www.{kind}.com/{handle}"
            out["social"].setdefault(kind, url)
    # JSON-LD founder / employee names
    for block in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if not isinstance(it, dict):
                continue
            for key, title in (("founder", "Founder"), ("employee", None), ("author", None)):
                v = it.get(key)
                for person in (v if isinstance(v, list) else [v]):
                    if isinstance(person, dict) and person.get("name"):
                        out["people"].append((str(person["name"])[:60], person.get("jobTitle") or title, 3))
            if it.get("email"):
                e = _clean_email(str(it["email"]).replace("mailto:", ""))
                if e:
                    out["emails"].append(e)
            if it.get("telephone"):
                pm = _PHONE_RE.search(str(it["telephone"]))
                if pm:
                    out["phones"].append(_fmt_phone(pm))
    # Name + title patterns in visible text
    for m in _NAME_THEN_TITLE.finditer(text):
        out["people"].append((m.group(1), m.group(2), 2))
    for m in _TITLE_THEN_NAME.finditer(text):
        out["people"].append((m.group(2), m.group(1), 2))
    for m in _MEET_RE.finditer(text):
        out["people"].append((m.group(1), None, 1))
    # same-site links that look like contact/about/team pages
    for m in re.finditer(r'(?i)<a[^>]+href=["\']([^"\'#]+)["\']', html):
        href = urljoin(page_url, unescape(m.group(1)))
        u = urlparse(href)
        if u.scheme not in ("http", "https") or _registrable(u.netloc) != site_host:
            continue
        path = u.path.lower()
        if any(h in path for h in _CONTACT_HINTS) and not re.search(r"\.(pdf|jpe?g|png|gif|zip)$", path):
            out["links"].append(f"{u.scheme}://{u.netloc}{u.path}")
    return out


def _pick_person(people: List[Tuple[str, Optional[str], int]], business_name: str) -> Tuple[Optional[str], Optional[str]]:
    biz_words = {w.lower() for w in re.findall(r"[A-Za-z]+", business_name or "")}
    best = None
    for name, title, weight in people:
        name = re.sub(r"\s+", " ", name or "").strip()
        words = name.split()
        if not (2 <= len(words) <= 3) or name.title() in _NOT_NAMES:
            continue
        if all(w.lower() in biz_words for w in words) and not title:
            continue  # bare company name, not a person (owner-named firms still match with a title)
        if any(w.lower() in {"design", "designs", "interiors", "interior", "studio", "group", "llc", "inc",
                             "the", "our", "and", "home", "homes", "kitchen", "bath", "remodeling",
                             "principal", "designer", "founder", "owner", "president", "director", "creative",
                             "lead", "partner", "managing", "ceo", "co-founder", "senior", "associate"} for w in words):
            continue
        score = weight + (2 if title else 0) + (1 if title and title.lower() in ("owner", "founder", "principal") else 0)
        if best is None or score > best[0]:
            best = (score, name, title)
    return (best[1], best[2]) if best else (None, None)


def _pick_email(emails: List[str], site_host: str) -> Optional[str]:
    if not emails:
        return None
    seen = list(dict.fromkeys(emails))
    same = [e for e in seen if e.split("@")[-1].endswith(site_host)]
    pool = same or seen
    # Prefer a personal-looking address over info@ / hello@
    generic = ("info@", "hello@", "contact@", "office@", "admin@", "sales@", "support@", "team@", "studio@", "design@")
    weak = ("press@", "media@", "orders@", "careers@", "jobs@", "billing@", "accounts@", "accounting@", "marketing@",
            "webmaster@", "privacy@", "returns@", "shop@", "store@")
    personal = [e for e in pool if not e.startswith(generic + weak)]
    general = [e for e in pool if e.startswith(generic)]
    return (personal or general or pool)[0]


class _Robots:
    def __init__(self) -> None:
        self._cache: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}

    async def allowed(self, client: httpx.AsyncClient, url: str, limiter: _DomainLimiter) -> bool:
        u = urlparse(url)
        root = f"{u.scheme}://{u.netloc}"
        if root not in self._cache:
            rp = urllib.robotparser.RobotFileParser()
            lock = await limiter.wait(u.netloc)
            try:
                r = await client.get(f"{root}/robots.txt", timeout=PAGE_TIMEOUT_S)
                if r.status_code in (401, 403):
                    rp.parse(["User-agent: *", "Disallow: /"])
                elif r.status_code >= 400:
                    rp.parse([])  # no robots.txt = allowed
                else:
                    rp.parse(r.text[:200_000].splitlines())
            except Exception:
                rp.parse([])
            finally:
                limiter.done(u.netloc, lock)
            self._cache[root] = rp
        rp = self._cache[root]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)


async def _fetch(client: httpx.AsyncClient, url: str, limiter: _DomainLimiter) -> Optional[str]:
    host = urlparse(url).netloc
    lock = await limiter.wait(host)
    try:
        async with client.stream("GET", url, timeout=PAGE_TIMEOUT_S) as r:
            if r.status_code >= 400:
                return None
            ctype = r.headers.get("content-type", "")
            if "html" not in ctype and "text" not in ctype:
                return None
            buf = b""
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > MAX_BYTES:
                    break
            return buf.decode(r.encoding or "utf-8", errors="replace")
    except Exception:
        return None
    finally:
        limiter.done(host, lock)


async def lookup_site(website: str, business_name: str = "", *, client: Optional[httpx.AsyncClient] = None,
                      limiter: Optional[_DomainLimiter] = None, robots: Optional[_Robots] = None) -> dict:
    """Scan one business website. Returns found fields + which pages were read/skipped."""
    root = _site_root(website)
    result = {"status": "no_website", "pages": [], "skipped_robots": [], "contact_name": None, "contact_title": None,
              "contact_email": None, "contact_phone": None, "instagram": None, "facebook": None, "linkedin": None}
    if not root:
        return result
    if pe.is_directory_url(root):
        result["status"] = "skipped_directory"
        return result
    own_client = client is None
    client = client or httpx.AsyncClient(headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"},
                                         follow_redirects=True)
    limiter = limiter or _DomainLimiter()
    robots = robots or _Robots()
    site_host = _registrable(urlparse(root).netloc)
    emails: List[str] = []
    phones: List[str] = []
    people: List[Tuple[str, Optional[str], int]] = []
    social: Dict[str, str] = {}
    queue: List[str] = [root + "/"]
    start_url = website if website.startswith("http") else f"https://{website}"
    if urlparse(start_url).path not in ("", "/"):
        queue.append(start_url)  # the exact page search found (often an about page)
    seen = set()
    try:
        while queue and len(result["pages"]) < MAX_PAGES_PER_SITE:
            url = queue.pop(0).rstrip("/")
            if url in seen:
                continue
            seen.add(url)
            if not await robots.allowed(client, url, limiter):
                result["skipped_robots"].append(url)
                continue
            html = await _fetch(client, url, limiter)
            if html is None:
                continue
            result["pages"].append(url)
            info = _extract(html, url, site_host)
            emails += info["emails"]
            phones += info["phones"]
            people += info["people"]
            for k, v in info["social"].items():
                social.setdefault(k, v)
            for link in info["links"]:
                if link.rstrip("/") not in seen and link not in queue:
                    queue.append(link)
            if len(result["pages"]) == 1 and not info["links"]:
                queue += [root + p for p in _FALLBACK_PATHS]
    finally:
        if own_client:
            await client.aclose()
    name, title = _pick_person(people, business_name)
    result.update({
        "contact_name": name, "contact_title": title,
        "contact_email": _pick_email(emails, site_host),
        "contact_phone": (list(dict.fromkeys(phones)) or [None])[0],
        "instagram": social.get("instagram"), "facebook": social.get("facebook"), "linkedin": social.get("linkedin"),
    })
    if not result["pages"]:
        result["status"] = "blocked_by_robots" if result["skipped_robots"] else "unreachable"
    elif any(result[k] for k in ("contact_name", "contact_email", "instagram")):
        result["status"] = "found"
    else:
        result["status"] = "nothing_found"
    return result


def _save(prospect_id: int, found: dict) -> None:
    note_bits = []
    if found.get("skipped_robots"):
        note_bits.append(f"robots.txt skipped {len(found['skipped_robots'])} page(s)")
    with pe._db() as conn:
        sets = ["enrichment_status = ?", "enrichment_pages = ?", "enrichment_note = ?", "enriched_at = ?"]
        vals = [found["status"], json.dumps(found.get("pages", [])), "; ".join(note_bits) or None,
                datetime.utcnow().isoformat(timespec="seconds")]
        for col in ("contact_name", "contact_title", "contact_email", "contact_phone", "instagram", "facebook", "linkedin"):
            if found.get(col):
                sets.append(f"{col} = ?")
                vals.append(found[col])
        # fill the main phone too when the listing had none
        if found.get("contact_phone"):
            sets.append("phone = COALESCE(NULLIF(phone, ''), ?)")
            vals.append(found["contact_phone"])
            sets.append("has_phone = 1")
        vals.append(prospect_id)
        conn.execute(f"UPDATE prospects SET {', '.join(sets)} WHERE id = ?", vals)


def _website_for(p: dict) -> Optional[str]:
    """Own website for a prospect. Google rows carry none; borrow one from a
    web-search row of the same business already in the DB (free, no API call)."""
    if p.get("website") and not pe.is_directory_url(p["website"]):
        return p["website"]
    target = pe._norm_name(pe.clean_display_name(p.get("name"), p.get("source")))
    if not target or len(target) < 5:
        return None
    with pe._db() as conn:
        rows = conn.execute(
            "SELECT name, website FROM prospects WHERE website IS NOT NULL AND website != '' AND id != ?",
            (p["id"],),
        ).fetchall()
    for r in rows:
        if pe.is_directory_url(r["website"]):
            continue
        cand = pe._norm_name(pe.clean_display_name(r["name"], "brave"))
        if cand and (cand == target or (len(target) >= 8 and (cand.startswith(target) or target.startswith(cand)))):
            return r["website"]
    return None


MAX_DISCOVER_PER_CALL = 10


async def discover_website(p: dict, client: httpx.AsyncClient, limiter: Optional["_DomainLimiter"] = None) -> Optional[str]:
    """Opt-in: find the business's own site with ONE query on the already-configured
    Brave Search key (the same provider Prospect Finder uses). Skips directories."""
    key = pe._get_brave_key()
    name = p.get("display_name") or pe.clean_display_name(p.get("name"), p.get("source"))
    if not key or not name or name == "—":
        return None
    city = (p.get("display_city") or "").split(",")[0]
    limiter = limiter or _DomainLimiter()
    lock = await limiter.wait("api.search.brave.com")  # free tier is ~1 query/second: serialise
    try:
        r = await client.get("https://api.search.brave.com/res/v1/web/search",
                             params={"q": f"\"{name}\" {city}".strip(), "count": 8, "result_filter": "web"},
                             headers={"Accept": "application/json", "X-Subscription-Token": key}, timeout=PAGE_TIMEOUT_S)
        r.raise_for_status()
        results = (r.json().get("web") or {}).get("results") or []
    except Exception:
        return None
    finally:
        limiter.done("api.search.brave.com", lock)
    tokens = [t for t in re.findall(r"[a-z0-9]+", name.lower()) if len(t) >= 4 and t not in
              ("design", "designs", "interior", "interiors", "home", "remodeling", "kitchen", "bath", "group", "studio", "center", "llc")]
    for item in results:
        url = item.get("url") or ""
        if not url or pe.is_directory_url(url):
            continue
        host = _registrable(urlparse(url).netloc)
        title = (item.get("title") or "").lower()
        if tokens and (any(t in host for t in tokens) or sum(t in title for t in tokens) >= max(1, len(tokens) // 2)):
            return _site_root(url)
    return None


async def enrich_prospects(prospect_ids: List[int], *, force: bool = False, discover_websites: bool = False) -> dict:
    """Free contact lookup for a batch of prospects (capped at MAX_BATCH).
    discover_websites=True also looks up missing websites via the existing Brave key (max 10/call)."""
    ids = list(dict.fromkeys(int(i) for i in prospect_ids))[:MAX_BATCH]
    discover_budget = [MAX_DISCOVER_PER_CALL if discover_websites else 0]
    limiter, robots = _DomainLimiter(), _Robots()
    sem = asyncio.Semaphore(GLOBAL_CONCURRENCY)
    results: List[dict] = []
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"},
                                 follow_redirects=True) as client:
        async def one(pid: int):
            p = pe.get_prospect(pid)
            if not p:
                results.append({"prospect_id": pid, "status": "not_found"})
                return
            if p.get("enriched_at") and not force and p.get("enrichment_status") in ("found", "nothing_found"):
                results.append({"prospect_id": pid, "name": p["display_name"], "status": "cached",
                                "contact_name": p.get("contact_name"), "contact_email": p.get("contact_email"),
                                "instagram": p.get("instagram")})
                return
            site = _website_for(p)
            discovered = False
            if not site and discover_budget[0] > 0 and not p.get("website"):
                discover_budget[0] -= 1
                site = await discover_website(p, client, limiter)
                if site:
                    discovered = True
                    with pe._db() as conn:
                        conn.execute("UPDATE prospects SET website = COALESCE(NULLIF(website, ''), ?), has_website = 1 WHERE id = ?",
                                     (site, pid))
            if not site:
                found = {"status": "skipped_directory" if p.get("website") else "no_website", "pages": []}
            else:
                async with sem:
                    found = await lookup_site(site, p.get("display_name") or "", client=client,
                                              limiter=limiter, robots=robots)
                found["website_used"] = site
                found["website_discovered"] = discovered
            _save(pid, found)
            results.append({"prospect_id": pid, "name": p["display_name"], **{k: found.get(k) for k in (
                "status", "website_used", "contact_name", "contact_title", "contact_email", "contact_phone",
                "instagram", "facebook", "linkedin", "website_discovered")}, "pages_read": len(found.get("pages", [])),
                "robots_skipped": len(found.get("skipped_robots", []))})
        await asyncio.gather(*(one(i) for i in ids))
    summary: Dict[str, int] = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {"requested": len(prospect_ids), "processed": len(ids), "summary": summary, "results": results,
            "rules": {"robots_txt": True, "min_delay_s_per_domain": MIN_DELAY_S, "max_pages_per_site": MAX_PAGES_PER_SITE,
                      "paid_apis": False, "brave_website_lookups": (MAX_DISCOVER_PER_CALL - discover_budget[0])}}


def enrich_prospects_sync(prospect_ids: List[int], *, force: bool = False, discover_websites: bool = False) -> dict:
    """Sync wrapper for Max tools (works inside or outside a running loop)."""
    coro = enrich_prospects(prospect_ids, force=force, discover_websites=discover_websites)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=600)
