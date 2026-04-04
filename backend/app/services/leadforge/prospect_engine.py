"""
LeadForge Prospect Engine — complete prospect finder with multi-provider
search, transparent scoring, deduplication, and pipeline management.

Tables auto-created on import. Uses Brave Search as primary provider;
Google Places and Yelp used only when their API keys are present.
"""

import asyncio
import json
import math
import os
import re
import sqlite3
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

# ── Configuration ────────────────────────────────────────────────────────

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "empire.db"),
)

# Read at call time, not import time (dotenv may not be loaded yet at import)
def _get_brave_key(): return os.getenv("BRAVE_API_KEY", "")
def _get_google_key(): return os.getenv("GOOGLE_PLACES_API_KEY", "")
def _get_yelp_key(): return os.getenv("YELP_FUSION_API_KEY", "")

HTTP_TIMEOUT = 15.0  # seconds per provider call

# ── Database helpers ─────────────────────────────────────────────────────


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _dict(row) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row)
    for k in (
        "expanded_locations", "providers_attempted", "providers_succeeded",
        "providers_failed", "categories", "matched_keywords", "recommended_units",
    ):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _dicts(rows) -> list:
    return [_dict(r) for r in rows]


# ── Table creation (runs on import) ─────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prospect_search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_unit TEXT NOT NULL,
    location_query TEXT NOT NULL,
    target_type TEXT NOT NULL,
    expanded_locations TEXT DEFAULT '[]',
    providers_attempted TEXT DEFAULT '[]',
    providers_succeeded TEXT DEFAULT '[]',
    providers_failed TEXT DEFAULT '[]',
    raw_result_count INTEGER DEFAULT 0,
    unique_result_count INTEGER DEFAULT 0,
    inserted_count INTEGER DEFAULT 0,
    deduped_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    business_name TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    phone TEXT,
    website TEXT,
    email TEXT,
    location TEXT,
    platform TEXT,
    source TEXT,
    external_id TEXT,
    rating REAL DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    categories TEXT DEFAULT '[]',
    description TEXT,
    score INTEGER DEFAULT 0,
    rating_points REAL DEFAULT 0,
    review_points REAL DEFAULT 0,
    relevance_points REAL DEFAULT 0,
    proximity_points REAL DEFAULT 0,
    keyword_bonus REAL DEFAULT 0,
    source_bonus REAL DEFAULT 0,
    confidence_score INTEGER DEFAULT 0,
    has_phone INTEGER DEFAULT 0,
    has_website INTEGER DEFAULT 0,
    has_address INTEGER DEFAULT 0,
    has_reviews INTEGER DEFAULT 0,
    matched_keywords TEXT DEFAULT '[]',
    window_treatments_fit INTEGER DEFAULT 0,
    upholstery_fit INTEGER DEFAULT 0,
    millwork_fit INTEGER DEFAULT 0,
    cabinetry_fit INTEGER DEFAULT 0,
    hospitality_fit INTEGER DEFAULT 0,
    restaurant_fit INTEGER DEFAULT 0,
    gc_fit INTEGER DEFAULT 0,
    designer_fit INTEGER DEFAULT 0,
    recommended_units TEXT DEFAULT '[]',
    client_type TEXT,
    outreach_ready INTEGER DEFAULT 0,
    best_contact_method TEXT,
    recommended_angle TEXT,
    outreach_priority TEXT DEFAULT 'medium',
    card_summary TEXT,
    status TEXT DEFAULT 'new',
    search_run_id INTEGER REFERENCES prospect_search_runs(id) ON DELETE SET NULL,
    first_seen_at TEXT DEFAULT (datetime('now')),
    last_seen_at TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prospect_pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL UNIQUE REFERENCES prospects(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'new',
    notes TEXT,
    next_action TEXT,
    assigned_unit TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


def _init_tables():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _db() as conn:
        conn.executescript(_SCHEMA)


try:
    _init_tables()
except Exception as e:
    print(f"[LeadForge Prospect Engine] Table init warning: {e}")


# ── Location Expander ────────────────────────────────────────────────────

DMV_LOCATIONS = [
    "Washington DC", "Arlington VA", "Alexandria VA", "Bethesda MD",
    "Silver Spring MD", "Fairfax VA", "Tysons VA", "Reston VA",
    "Rockville MD", "McLean VA", "Falls Church VA", "Herndon VA",
    "Chevy Chase MD", "Georgetown DC", "Potomac MD",
]

NATIONWIDE_METROS = [
    "New York NY", "Los Angeles CA", "Chicago IL", "Houston TX",
    "Phoenix AZ", "Philadelphia PA", "San Antonio TX", "San Diego CA",
    "Dallas TX", "Austin TX", "Miami FL", "Atlanta GA",
    "Denver CO", "Seattle WA", "Boston MA",
]


def expand_location(location_query: str) -> List[str]:
    """Expand a location alias into a list of search locations."""
    q = location_query.strip().lower()
    if q in ("dmv", "dc area", "dc metro", "dmv area"):
        return DMV_LOCATIONS
    if q in ("nationwide", "national", "usa", "us", "all"):
        return NATIONWIDE_METROS
    return [location_query.strip()]


# ── Keyword & Fit Definitions ───────────────────────────────────────────

RELEVANCE_KEYWORDS = {
    "interior design": 4, "interior designer": 4,
    "decorator": 3, "design firm": 3,
    "contractor": 2, "general contractor": 3,
    "architect": 2, "home builder": 2,
    "renovator": 2, "remodeler": 2, "remodeling": 2,
    "workroom": 5, "drapery": 5, "upholstery": 5,
    "window treatment": 5, "blinds": 3, "shutters": 3,
    "curtain": 4, "fabric": 3, "custom window": 5,
    "cabinetry": 4, "cabinet maker": 4, "millwork": 4,
    "woodwork": 4, "custom furniture": 4,
    "hotel": 3, "hospitality": 4, "resort": 3, "boutique hotel": 4,
    "restaurant": 3, "bar & restaurant": 3,
    "staging": 3, "home staging": 3,
}

FIT_RULES: Dict[str, Dict[str, Any]] = {
    "designer_fit": {
        "keywords": [
            "interior design", "interior designer", "decorator", "design firm",
            "staging", "home staging", "decor",
        ]
    },
    "window_treatments_fit": {
        "keywords": [
            "drapery", "curtain", "window treatment", "blinds", "shutters",
            "custom window", "shade", "valance",
        ]
    },
    "upholstery_fit": {
        "keywords": [
            "upholstery", "reupholster", "fabric", "furniture repair",
            "custom furniture", "cushion",
        ]
    },
    "millwork_fit": {
        "keywords": [
            "millwork", "woodwork", "trim", "molding", "moulding",
            "custom wood", "architectural wood",
        ]
    },
    "cabinetry_fit": {
        "keywords": [
            "cabinet", "cabinetry", "cabinet maker", "kitchen cabinet",
            "custom cabinet", "vanity",
        ]
    },
    "hospitality_fit": {
        "keywords": [
            "hotel", "hospitality", "resort", "boutique hotel", "inn",
            "bed and breakfast", "lodge",
        ]
    },
    "restaurant_fit": {
        "keywords": [
            "restaurant", "bar", "cafe", "bistro", "dining",
            "eatery", "food service",
        ]
    },
    "gc_fit": {
        "keywords": [
            "general contractor", "contractor", "builder", "home builder",
            "remodeler", "remodeling", "renovator", "renovation", "construction",
        ]
    },
}

DMV_INDICATORS = [
    "dc", "washington", "virginia", "maryland", "arlington", "alexandria",
    "bethesda", "silver spring", "fairfax", "tysons", "reston", "rockville",
    "mclean", "falls church", "herndon", "chevy chase", "georgetown", "potomac",
]


# ── Scoring ──────────────────────────────────────────────────────────────


def _score_prospect(raw: dict, search_location: str) -> dict:
    """
    Score a raw prospect dict and return it with all score breakdown fields.
    Score range: 0-100.
    """
    name_lower = (raw.get("name") or raw.get("business_name") or "").lower()
    cats_str = " ".join(raw.get("categories") or []).lower()
    desc_lower = (raw.get("description") or "").lower()
    combined = f"{name_lower} {cats_str} {desc_lower}"

    # -- Rating points (0-40) --
    rating = float(raw.get("rating") or 0)
    rating_points = round((rating / 5.0) * 40, 2) if rating > 0 else 0

    # -- Review points (0-30, log scale, cap 500+) --
    reviews = int(raw.get("review_count") or 0)
    if reviews > 0:
        review_points = round(min(30, (math.log10(min(reviews, 500) + 1) / math.log10(501)) * 30), 2)
    else:
        review_points = 0

    # -- Relevance points (0-20) --
    relevance_points = 0.0
    matched_keywords = []
    for kw, pts in RELEVANCE_KEYWORDS.items():
        if kw in combined:
            relevance_points += pts
            matched_keywords.append(kw)
    relevance_points = round(min(20, relevance_points), 2)

    # -- Proximity points (0-10) --
    loc_combined = f"{combined} {(raw.get('location') or '').lower()} {(raw.get('address') or '').lower()} {(raw.get('city') or '').lower()} {(raw.get('state') or '').lower()}"
    proximity_points = 0.0
    for ind in DMV_INDICATORS:
        if ind in loc_combined or ind in search_location.lower():
            proximity_points = 10.0
            break

    # -- Keyword bonus (0-10) --
    workroom_terms = ["workroom", "drapery", "upholstery", "custom window", "window treatment"]
    keyword_bonus = 0.0
    for t in workroom_terms:
        if t in combined:
            keyword_bonus += 2.5
    keyword_bonus = round(min(10, keyword_bonus), 2)

    # -- Source bonus (0-5) --
    source = (raw.get("source") or "").lower()
    source_bonus_map = {"google": 5, "google_places": 5, "yelp": 4, "brave": 2}
    source_bonus = source_bonus_map.get(source, 1)

    # -- Total score --
    total = round(min(100, rating_points + review_points + relevance_points +
                       proximity_points + keyword_bonus + source_bonus))

    # -- Confidence score (0-100) --
    has_phone = 1 if raw.get("phone") else 0
    has_website = 1 if raw.get("website") else 0
    has_address = 1 if (raw.get("address") or raw.get("city")) else 0
    has_reviews = 1 if reviews > 0 else 0
    confidence = (has_phone + has_website + has_address + has_reviews) * 25

    # -- Fit tags --
    fits = {}
    recommended_units = []
    for fit_key, rule in FIT_RULES.items():
        hit = any(kw in combined for kw in rule["keywords"])
        fits[fit_key] = 1 if hit else 0
        if hit:
            unit_map = {
                "designer_fit": "workroom",
                "window_treatments_fit": "workroom",
                "upholstery_fit": "workroom",
                "millwork_fit": "woodcraft",
                "cabinetry_fit": "woodcraft",
                "hospitality_fit": "workroom",
                "restaurant_fit": "workroom",
                "gc_fit": "workroom",
            }
            u = unit_map.get(fit_key)
            if u and u not in recommended_units:
                recommended_units.append(u)

    # -- Client type --
    if fits.get("hospitality_fit") or fits.get("restaurant_fit"):
        client_type = "commercial"
    elif fits.get("gc_fit"):
        client_type = "contractor"
    elif fits.get("designer_fit"):
        client_type = "designer"
    else:
        client_type = "residential"

    # -- Outreach readiness --
    outreach_ready = 1 if confidence >= 50 and total >= 30 else 0

    # -- Best contact method --
    if raw.get("email"):
        best_contact = "email"
    elif raw.get("phone"):
        best_contact = "phone"
    elif raw.get("website"):
        best_contact = "website_form"
    else:
        best_contact = "social"

    # -- Recommended angle --
    if fits.get("designer_fit"):
        angle = "workroom services for your design projects"
    elif fits.get("hospitality_fit"):
        angle = "commercial drapery and upholstery for hospitality"
    elif fits.get("gc_fit"):
        angle = "subcontractor for window treatments and soft furnishings"
    elif fits.get("millwork_fit") or fits.get("cabinetry_fit"):
        angle = "custom woodwork and cabinetry partnership"
    else:
        angle = "custom window treatments and upholstery"

    # -- Priority --
    if total >= 70:
        priority = "high"
    elif total >= 40:
        priority = "medium"
    else:
        priority = "low"

    # -- Card summary --
    card_parts = [raw.get("business_name") or raw.get("name") or "Unknown"]
    if raw.get("city"):
        card_parts.append(raw["city"])
    if rating > 0:
        card_parts.append(f"{rating}★")
    if reviews > 0:
        card_parts.append(f"{reviews} reviews")
    card_summary = " | ".join(card_parts)

    return {
        **raw,
        "score": total,
        "rating_points": rating_points,
        "review_points": review_points,
        "relevance_points": relevance_points,
        "proximity_points": proximity_points,
        "keyword_bonus": keyword_bonus,
        "source_bonus": source_bonus,
        "confidence_score": confidence,
        "has_phone": has_phone,
        "has_website": has_website,
        "has_address": has_address,
        "has_reviews": has_reviews,
        "matched_keywords": matched_keywords,
        **fits,
        "recommended_units": recommended_units,
        "client_type": client_type,
        "outreach_ready": outreach_ready,
        "best_contact_method": best_contact,
        "recommended_angle": angle,
        "outreach_priority": priority,
        "card_summary": card_summary,
    }


# ── Normalization & Deduplication ────────────────────────────────────────

_PUNCT_RE = re.compile(r"[^a-z0-9\s]")


def _norm_name(name: str) -> str:
    if not name:
        return ""
    return _PUNCT_RE.sub("", name.lower()).strip()


def _norm_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    return digits[-10:] if len(digits) >= 10 else digits


def _norm_domain(website: str) -> str:
    if not website:
        return ""
    try:
        parsed = urlparse(website if "://" in website else f"https://{website}")
        domain = (parsed.netloc or parsed.path).lower()
        domain = re.sub(r"^www\.", "", domain)
        return domain.split("/")[0]
    except Exception:
        return ""


def _dedupe_batch(prospects: List[dict]) -> List[dict]:
    """Deduplicate within a batch, keeping the higher-scored entry."""
    seen: Dict[str, dict] = {}  # key -> prospect
    # Track which keys belong to each prospect (by id)
    prospect_keys: Dict[int, set] = {}  # id(prospect) -> set of keys

    for p in prospects:
        keys = set()
        nn = _norm_name(p.get("name") or p.get("business_name") or "")
        if nn:
            keys.add(f"name:{nn}")
        np_ = _norm_phone(p.get("phone") or "")
        if np_:
            keys.add(f"phone:{np_}")
        nd = _norm_domain(p.get("website") or "")
        if nd:
            keys.add(f"domain:{nd}")

        matched_key = None
        for k in keys:
            if k in seen:
                matched_key = k
                break

        if matched_key:
            existing = seen[matched_key]
            existing_id = id(existing)
            if p.get("score", 0) > existing.get("score", 0):
                # Replace: update ALL keys that pointed to the old entry
                old_keys = prospect_keys.pop(existing_id, set())
                new_keys = old_keys | keys
                for k in new_keys:
                    seen[k] = p
                prospect_keys[id(p)] = new_keys
            else:
                # Keep existing but add new keys to point to it
                existing_keys = prospect_keys.get(existing_id, set())
                existing_keys |= keys
                prospect_keys[existing_id] = existing_keys
                for k in keys:
                    seen[k] = existing
        else:
            for k in keys:
                seen[k] = p
            prospect_keys[id(p)] = keys

    # Unique by id(dict)
    unique = []
    seen_ids = set()
    for p in seen.values():
        pid = id(p)
        if pid not in seen_ids:
            seen_ids.add(pid)
            unique.append(p)

    return unique


def _find_existing_prospect(conn: sqlite3.Connection, prospect: dict) -> Optional[int]:
    """Check if a prospect already exists in the DB. Return its id or None."""
    nn = _norm_name(prospect.get("name") or prospect.get("business_name") or "")
    np = _norm_phone(prospect.get("phone") or "")
    nd = _norm_domain(prospect.get("website") or "")

    if nn:
        rows = conn.execute(
            "SELECT id, name, business_name FROM prospects"
        ).fetchall()
        for row in rows:
            existing_name = _norm_name(row["name"] or row["business_name"] or "")
            if existing_name and existing_name == nn:
                return row["id"]

    if np:
        rows = conn.execute("SELECT id, phone FROM prospects WHERE phone IS NOT NULL AND phone != ''").fetchall()
        for row in rows:
            if _norm_phone(row["phone"]) == np:
                return row["id"]

    if nd:
        rows = conn.execute("SELECT id, website FROM prospects WHERE website IS NOT NULL AND website != ''").fetchall()
        for row in rows:
            if _norm_domain(row["website"]) == nd:
                return row["id"]

    return None


# ── Search Providers ─────────────────────────────────────────────────────


async def _search_brave(query: str, location: str, count: int = 20) -> List[dict]:
    """Search Brave Web Search for business prospects."""
    if not _get_brave_key():
        raise ValueError("BRAVE_API_KEY not configured")

    search_query = f"{query} {location}"
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": _get_brave_key(),
    }
    params = {
        "q": search_query,
        "count": count,
        "result_filter": "web",
    }

    results = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    for item in (data.get("web", {}).get("results") or []):
        title = item.get("title", "")
        desc = item.get("description", "")
        page_url = item.get("url", "")

        # Extract phone from description if present
        phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", desc)
        phone = phone_match.group(0) if phone_match else None

        results.append({
            "name": title,
            "business_name": title,
            "address": None,
            "city": location.split(",")[0].split()[-1] if "," in location else location.split()[-2] if len(location.split()) > 1 else location,
            "state": location.split()[-1] if len(location.split()) > 1 else None,
            "zip": None,
            "phone": phone,
            "website": page_url,
            "email": None,
            "rating": None,
            "review_count": 0,
            "source": "brave",
            "platform": "brave_search",
            "categories": [],
            "description": desc,
            "location": location,
            "external_id": None,
        })

    return results


async def _search_google_places(query: str, location: str) -> List[dict]:
    """Search Google Places API (Text Search)."""
    if not _get_google_key():
        raise ValueError("GOOGLE_PLACES_API_KEY not configured")

    search_query = f"{query} in {location}"
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": search_query,
        "key": _get_google_key(),
    }

    results = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    for place in (data.get("results") or []):
        addr_parts = (place.get("formatted_address") or "").split(",")
        city = addr_parts[0].strip() if len(addr_parts) > 1 else None
        state_zip = addr_parts[-2].strip() if len(addr_parts) > 2 else None
        state = state_zip.split()[0] if state_zip else None
        zipcode = state_zip.split()[1] if state_zip and len(state_zip.split()) > 1 else None

        results.append({
            "name": place.get("name", ""),
            "business_name": place.get("name", ""),
            "address": place.get("formatted_address"),
            "city": city,
            "state": state,
            "zip": zipcode,
            "phone": None,  # Requires Places Details call
            "website": None,  # Requires Places Details call
            "email": None,
            "rating": place.get("rating"),
            "review_count": place.get("user_ratings_total", 0),
            "source": "google_places",
            "platform": "google",
            "categories": place.get("types", []),
            "description": "",
            "location": location,
            "external_id": place.get("place_id"),
        })

    return results


async def _search_yelp(query: str, location: str) -> List[dict]:
    """Search Yelp Fusion API."""
    if not _get_yelp_key():
        raise ValueError("YELP_FUSION_API_KEY not configured")

    url = "https://api.yelp.com/v3/businesses/search"
    headers = {"Authorization": f"Bearer {_get_yelp_key()}"}
    params = {
        "term": query,
        "location": location,
        "limit": 20,
    }

    results = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    for biz in (data.get("businesses") or []):
        loc = biz.get("location", {})
        cats = [c.get("title", "") for c in (biz.get("categories") or [])]

        results.append({
            "name": biz.get("name", ""),
            "business_name": biz.get("name", ""),
            "address": loc.get("address1"),
            "city": loc.get("city"),
            "state": loc.get("state"),
            "zip": loc.get("zip_code"),
            "phone": biz.get("phone"),
            "website": biz.get("url"),
            "email": None,
            "rating": biz.get("rating"),
            "review_count": biz.get("review_count", 0),
            "source": "yelp",
            "platform": "yelp",
            "categories": cats,
            "description": ", ".join(cats),
            "location": location,
            "external_id": biz.get("id"),
        })

    return results


# ── Query Builder ────────────────────────────────────────────────────────

TARGET_QUERIES = {
    "interior_designers": "interior designer design firm decorator",
    "contractors": "general contractor home builder remodeling contractor",
    "hospitality": "hotel boutique hotel resort inn bed and breakfast",
    "restaurants": "restaurant bar bistro cafe upscale dining",
    "window_treatments": "drapery workroom window treatments custom curtains blinds",
    "upholstery": "upholstery shop custom upholstery furniture repair",
    "woodwork": "custom cabinetry millwork woodwork cabinet maker",
    "staging": "home staging company property staging",
    "all": "interior designer contractor hotel restaurant drapery upholstery",
}


def _build_query(target_type: str) -> str:
    return TARGET_QUERIES.get(target_type.lower(), target_type)


# ── Insert / Update Prospects ────────────────────────────────────────────

_INSERT_COLS = [
    "name", "business_name", "address", "city", "state", "zip",
    "phone", "website", "email", "location", "platform", "source",
    "external_id", "rating", "review_count", "categories", "description",
    "score", "rating_points", "review_points", "relevance_points",
    "proximity_points", "keyword_bonus", "source_bonus",
    "confidence_score", "has_phone", "has_website", "has_address",
    "has_reviews", "matched_keywords",
    "window_treatments_fit", "upholstery_fit", "millwork_fit",
    "cabinetry_fit", "hospitality_fit", "restaurant_fit", "gc_fit",
    "designer_fit", "recommended_units", "client_type",
    "outreach_ready", "best_contact_method", "recommended_angle",
    "outreach_priority", "card_summary", "status", "search_run_id",
]


def _prep_value(val):
    """Prepare a value for SQLite insertion."""
    if isinstance(val, (list, dict)):
        return json.dumps(val)
    return val


def _insert_prospect(conn: sqlite3.Connection, prospect: dict, search_run_id: int) -> int:
    prospect["search_run_id"] = search_run_id
    prospect.setdefault("status", "new")

    cols = [c for c in _INSERT_COLS if c in prospect]
    placeholders = ", ".join(["?"] * len(cols))
    vals = [_prep_value(prospect.get(c)) for c in cols]

    cur = conn.execute(
        f"INSERT INTO prospects ({', '.join(cols)}) VALUES ({placeholders})",
        vals,
    )
    return cur.lastrowid


def _update_prospect(conn: sqlite3.Connection, prospect_id: int, prospect: dict):
    update_cols = [
        "rating", "review_count", "score", "rating_points", "review_points",
        "relevance_points", "proximity_points", "keyword_bonus", "source_bonus",
        "confidence_score", "has_phone", "has_website", "has_address", "has_reviews",
        "matched_keywords", "recommended_units", "client_type", "outreach_ready",
        "best_contact_method", "recommended_angle", "outreach_priority", "card_summary",
        "last_seen_at",
    ]
    prospect["last_seen_at"] = datetime.utcnow().isoformat()

    sets = []
    vals = []
    for c in update_cols:
        if c in prospect:
            sets.append(f"{c} = ?")
            vals.append(_prep_value(prospect[c]))

    # Also update any field that was previously null but now has data
    for c in ("phone", "website", "email", "address", "city", "state", "zip"):
        if prospect.get(c):
            sets.append(f"{c} = COALESCE({c}, ?)")
            vals.append(_prep_value(prospect[c]))

    if sets:
        vals.append(prospect_id)
        conn.execute(f"UPDATE prospects SET {', '.join(sets)} WHERE id = ?", vals)


# ── Pipeline Management ─────────────────────────────────────────────────


def add_to_pipeline(
    prospect_id: int,
    status: str = "new",
    notes: str = None,
    next_action: str = None,
    assigned_unit: str = None,
) -> dict:
    """
    Add a prospect to the pipeline. Duplicate-safe via UNIQUE constraint.
    Returns dict with 'status' key: 'added' or 'already_in_pipeline'.
    """
    with _db() as conn:
        # Verify prospect exists
        row = conn.execute("SELECT id FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
        if not row:
            return {"status": "error", "message": f"Prospect {prospect_id} not found"}

        try:
            conn.execute(
                """INSERT INTO prospect_pipeline
                   (prospect_id, status, notes, next_action, assigned_unit)
                   VALUES (?, ?, ?, ?, ?)""",
                (prospect_id, status, notes, next_action, assigned_unit),
            )
            return {"status": "added", "prospect_id": prospect_id}
        except sqlite3.IntegrityError:
            return {"status": "already_in_pipeline", "prospect_id": prospect_id}


# ── Main Search Function ────────────────────────────────────────────────


async def run_prospect_search(
    business_unit: str,
    location: str,
    target_type: str,
) -> dict:
    """
    Run a full prospect search pipeline:
    1. Expand location
    2. Check available providers
    3. Run available providers in parallel
    4. Score all results
    5. Dedupe and insert
    6. Log search run
    7. Return results summary
    """
    started_at = datetime.utcnow().isoformat()

    # 1. Expand location
    locations = expand_location(location)
    query = _build_query(target_type)

    # 2. Check available providers
    providers = []
    if _get_brave_key():
        providers.append(("brave", _search_brave))
    if _get_google_key():
        providers.append(("google_places", _search_google_places))
    if _get_yelp_key():
        providers.append(("yelp", _search_yelp))

    if not providers:
        return {
            "success": False,
            "error": "No search providers configured. Set BRAVE_API_KEY, GOOGLE_PLACES_API_KEY, or YELP_FUSION_API_KEY.",
            "providers_available": [],
        }

    providers_attempted = [p[0] for p in providers]
    providers_succeeded = []
    providers_failed = []

    # 3. Run providers across all locations in parallel
    all_raw: List[dict] = []

    async def _run_provider_location(provider_name: str, search_fn, loc: str):
        try:
            results = await search_fn(query, loc)
            return provider_name, loc, results, None
        except Exception as e:
            return provider_name, loc, [], str(e)

    tasks = []
    for pname, pfn in providers:
        for loc in locations:
            tasks.append(_run_provider_location(pname, pfn, loc))

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    provider_errors: Dict[str, List[str]] = {}
    provider_successes: set = set()

    for result in results_list:
        if isinstance(result, Exception):
            # Unexpected exception from gather
            continue
        pname, loc, results, error = result
        if error:
            provider_errors.setdefault(pname, []).append(f"{loc}: {error}")
        else:
            if results:
                provider_successes.add(pname)
            all_raw.extend(results)

    providers_succeeded = list(provider_successes)
    providers_failed = [
        {"provider": k, "errors": v}
        for k, v in provider_errors.items()
        if k not in provider_successes
    ]

    raw_count = len(all_raw)

    # 4. Score all results
    scored = []
    for raw in all_raw:
        try:
            scored_prospect = _score_prospect(raw, location)
            scored.append(scored_prospect)
        except Exception:
            # Skip prospects that fail scoring
            continue

    # 5. Dedupe within batch
    unique = _dedupe_batch(scored)
    unique_count = len(unique)

    # 6. Insert into DB, handling existing duplicates
    inserted_count = 0
    deduped_count = 0

    # Create search run record first
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO prospect_search_runs
               (business_unit, location_query, target_type, expanded_locations,
                providers_attempted, providers_succeeded, providers_failed,
                raw_result_count, unique_result_count, inserted_count, deduped_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
            (
                business_unit, location, target_type,
                json.dumps(locations),
                json.dumps(providers_attempted),
                json.dumps(providers_succeeded),
                json.dumps(providers_failed),
                raw_count, unique_count,
            ),
        )
        search_run_id = cur.lastrowid

    # Insert prospects
    with _db() as conn:
        for prospect in unique:
            try:
                existing_id = _find_existing_prospect(conn, prospect)
                if existing_id:
                    _update_prospect(conn, existing_id, prospect)
                    deduped_count += 1
                else:
                    _insert_prospect(conn, prospect, search_run_id)
                    inserted_count += 1
            except Exception:
                traceback.print_exc()
                continue

        # Update search run with final counts
        conn.execute(
            """UPDATE prospect_search_runs
               SET inserted_count = ?, deduped_count = ?
               WHERE id = ?""",
            (inserted_count, deduped_count, search_run_id),
        )

    # 7. Build summary
    # Fetch top prospects for the response
    top_prospects = []
    with _db() as conn:
        rows = conn.execute(
            """SELECT * FROM prospects
               WHERE search_run_id = ?
               ORDER BY score DESC LIMIT 20""",
            (search_run_id,),
        ).fetchall()
        top_prospects = _dicts(rows)

    return {
        "success": True,
        "search_run_id": search_run_id,
        "business_unit": business_unit,
        "location_query": location,
        "target_type": target_type,
        "expanded_locations": locations,
        "providers_attempted": providers_attempted,
        "providers_succeeded": providers_succeeded,
        "providers_failed": providers_failed,
        "raw_result_count": raw_count,
        "unique_result_count": unique_count,
        "inserted_count": inserted_count,
        "deduped_count": deduped_count,
        "top_prospects": top_prospects,
        "started_at": started_at,
        "completed_at": datetime.utcnow().isoformat(),
    }


# ── Utility functions for router integration ─────────────────────────────


def get_search_runs(limit: int = 20, offset: int = 0) -> List[dict]:
    """Fetch recent search runs."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM prospect_search_runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return _dicts(rows)


def get_prospects(
    search_run_id: int = None,
    min_score: int = 0,
    outreach_ready: bool = None,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    """Fetch prospects with optional filters."""
    where_parts = []
    params: list = []

    if search_run_id is not None:
        where_parts.append("search_run_id = ?")
        params.append(search_run_id)
    if min_score > 0:
        where_parts.append("score >= ?")
        params.append(min_score)
    if outreach_ready is not None:
        where_parts.append("outreach_ready = ?")
        params.append(1 if outreach_ready else 0)

    where = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    params.extend([limit, offset])

    with _db() as conn:
        rows = conn.execute(
            f"SELECT * FROM prospects{where} ORDER BY score DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return _dicts(rows)


def get_prospect(prospect_id: int) -> Optional[dict]:
    """Fetch a single prospect by ID."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM prospects WHERE id = ?", (prospect_id,)
        ).fetchone()
        return _dict(row)


def get_pipeline(status: str = None, limit: int = 50) -> List[dict]:
    """Fetch pipeline entries with prospect details."""
    if status:
        query = """
            SELECT pp.*, p.name, p.business_name, p.score, p.card_summary,
                   p.outreach_priority, p.best_contact_method
            FROM prospect_pipeline pp
            JOIN prospects p ON pp.prospect_id = p.id
            WHERE pp.status = ?
            ORDER BY p.score DESC LIMIT ?
        """
        params = (status, limit)
    else:
        query = """
            SELECT pp.*, p.name, p.business_name, p.score, p.card_summary,
                   p.outreach_priority, p.best_contact_method
            FROM prospect_pipeline pp
            JOIN prospects p ON pp.prospect_id = p.id
            ORDER BY p.score DESC LIMIT ?
        """
        params = (limit,)

    with _db() as conn:
        rows = conn.execute(query, params).fetchall()
        return _dicts(rows)


def update_pipeline_entry(
    prospect_id: int,
    status: str = None,
    notes: str = None,
    next_action: str = None,
    assigned_unit: str = None,
) -> Optional[dict]:
    """Update an existing pipeline entry."""
    sets = ["updated_at = datetime('now')"]
    vals: list = []

    if status is not None:
        sets.append("status = ?")
        vals.append(status)
    if notes is not None:
        sets.append("notes = ?")
        vals.append(notes)
    if next_action is not None:
        sets.append("next_action = ?")
        vals.append(next_action)
    if assigned_unit is not None:
        sets.append("assigned_unit = ?")
        vals.append(assigned_unit)

    vals.append(prospect_id)

    with _db() as conn:
        conn.execute(
            f"UPDATE prospect_pipeline SET {', '.join(sets)} WHERE prospect_id = ?",
            vals,
        )
        row = conn.execute(
            "SELECT * FROM prospect_pipeline WHERE prospect_id = ?",
            (prospect_id,),
        ).fetchone()
        return _dict(row)


def get_prospect_stats() -> dict:
    """Return aggregate stats for the dashboard."""
    with _db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
        outreach = conn.execute(
            "SELECT COUNT(*) FROM prospects WHERE outreach_ready = 1"
        ).fetchone()[0]
        pipeline_count = conn.execute(
            "SELECT COUNT(*) FROM prospect_pipeline"
        ).fetchone()[0]
        runs = conn.execute(
            "SELECT COUNT(*) FROM prospect_search_runs"
        ).fetchone()[0]
        avg_score = conn.execute(
            "SELECT COALESCE(AVG(score), 0) FROM prospects"
        ).fetchone()[0]

        by_type = {}
        for row in conn.execute(
            "SELECT client_type, COUNT(*) as cnt FROM prospects GROUP BY client_type"
        ).fetchall():
            by_type[row["client_type"] or "unknown"] = row["cnt"]

        by_source = {}
        for row in conn.execute(
            "SELECT source, COUNT(*) as cnt FROM prospects GROUP BY source"
        ).fetchall():
            by_source[row["source"] or "unknown"] = row["cnt"]

    return {
        "total_prospects": total,
        "outreach_ready": outreach,
        "in_pipeline": pipeline_count,
        "total_search_runs": runs,
        "average_score": round(avg_score, 1),
        "by_client_type": by_type,
        "by_source": by_source,
    }
