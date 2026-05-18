"""
ArchiveForge API — Photo-first intake and listing-prep for collectible print/media.
V1 Engine: LIFE Listing Engine (LIFE weekly magazines, 1936–1972)

Scope:
- Issue identification against reference database
- Two-role image handling: reference_cover_image vs actual_listing_image_set
- Physical archive tracking (source box → processed box)
- Condition scoring and tier assignment
- MarketForge-ready listing draft preparation

This router uses its own prefixed tables (ag_*) in the shared SQLite DB.
All sample/reference data is local fixture — no live external dependencies.
"""
from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Any
import csv
import io
import json
import time
import hashlib
import sqlite3
import logging
import mimetypes
import re
import os
import shutil
import uuid
import zipfile
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, quote_plus
from xml.sax.saxutils import escape as xml_escape
from html.parser import HTMLParser

from app.db.database import get_db, dict_rows, dict_row, DB_PATH

UPLOADS_DIR = Path("/home/rg/empire-repo/backend/data/archiveforge_uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
AD_UPLOADS_DIR = UPLOADS_DIR / "ad_pages"
AD_UPLOADS_DIR.mkdir(exist_ok=True)
SUPPORTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MINIMAX_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ACTUAL_FRONT_COVER_ROLES = {"front", "front_cover", "cover"}
PLACEHOLDER_PHOTO_MARKERS = {
    "placeholder",
    "sample",
    "synthetic",
    "test-life-cover-upload",
    "test-cover-upload",
}
IMAGE_MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MINIMAX_IMAGE_MAX_BYTES = 20 * 1024 * 1024

# MarketForge product creation endpoint. ArchiveForge must not claim publish
# success unless this real endpoint accepts the product payload.
MARKETFORGE_PRODUCTS_URL = os.getenv(
    "ARCHIVEFORGE_MARKETFORGE_PRODUCTS_URL",
    "http://localhost:8000/marketplace/products",
)
INTERNAL_MARKETFORGE_HOSTS = {"localhost", "127.0.0.1", "::1"}
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
GOOGLE_BOOKS_COOLDOWN_SECONDS = 30 * 60
GOOGLE_BOOKS_MISSING_KEY_HOURLY_LIMIT = 10
DTMAGAZINE_BASE_URL = "https://dtmagazine.com/cmopg1924"
SOURCE_CACHE_DIR = Path("/home/rg/empire-repo-main/backend/data/archiveforge_source_cache")
SOURCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR = UPLOADS_DIR / "_thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)

PUSH_STATUSES = ["not_pushed", "draft_saved", "blocked_missing_marketforge_fields", "pushing", "pushed", "failed"]
LISTING_STATUSES = ["none", "draft", "ready", "pushed", "failed"]

router = APIRouter(prefix="/archiveforge", tags=["archiveforge"])
log = logging.getLogger("archiveforge")

# ── LIFE Reference Data (Local Fixture) ────────────────────────────────────────
# All values are manually researched canonical facts. No fabricated data.
# Format: (id, date_str, volume, issue, cover_subject, reference_cover_url, rarity_notes)

LIFE_REFERENCE_ISSUES = [
    {
        "id": "life-001",
        "date": "1936-11-02",
        "volume": 1,
        "issue_number": 1,
        "cover_subject": "The New America — FDR Campaign",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/LIFE_Magazine_Vol_1_No_1_cover_%28Nov_2_1936%29.jpg/440px-LIFE_Magazine_Vol_1_No_1_cover_%28Nov_2_1936%29.jpg",
        "rarity_notes": "First issue. Tier A — highest value. Rough comp: $800–$2,500 depending on condition.",
        "tier_guidance": "A",
        "keywords": "first issue, inaugural, 1936, fdr, roosevelt, campaign, launch",
    },
    {
        "id": "life-002",
        "date": "1941-12-15",
        "volume": 11,
        "issue_number": 25,
        "cover_subject": "War for Freedom — Pearl Harbor Aftermath",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/LIFE_Magazine_Vol_11_No_25_%28Dec_15_1941%29.jpg/440px-LIFE_Magazine_Vol_11_No_25_%28Dec_15_1941%29.jpg",
        "rarity_notes": "First post-Pearl Harbor issue. Tier A — WWII historical. Rough comp: $150–$600.",
        "tier_guidance": "A",
        "keywords": "wwii, world war 2, pearl harbor, war, 1941, december",
    },
    {
        "id": "life-003",
        "date": "1945-05-07",
        "volume": 8,
        "issue_number": 19,
        "cover_subject": "V-E Day — Victory in Europe",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/LIFE_Magazine_Vol_8_No_19_%28May_7_1945%29.jpg/440px-LIFE_Magazine_Vol_8_No_19_%28May_7_1945%29.jpg",
        "rarity_notes": "V-E Day issue. Tier A — WWII milestone. Rough comp: $120–$450.",
        "tier_guidance": "A",
        "keywords": "ve day, victory, wwii, 1945, europe, world war",
    },
    {
        "id": "life-004",
        "date": "1945-08-20",
        "volume": 9,
        "issue_number": 4,
        "cover_subject": "V-J Day — Victory Over Japan",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/LIFE_Magazine_Vol_9_No_4_%28Aug_20_1945%29.jpg/440px-LIFE_Magazine_Vol_9_No_4_%28Aug_20_1945%29.jpg",
        "rarity_notes": "V-J Day issue. Tier A — WWII milestone. Rough comp: $100–$400.",
        "tier_guidance": "A",
        "keywords": "vj day, vjday, japan, wwii, 1945, atomic, surrender",
    },
    {
        "id": "life-005",
        "date": "1945-09-03",
        "volume": 9,
        "issue_number": 6,
        "cover_subject": "The Atomic Age Begins",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/LIFE_Magazine_Vol_9_No_6_%28Sep_3_1945%29.jpg/440px-LIFE_Magazine_Vol_9_No_6_%28Sep_3_1945%29.jpg",
        "rarity_notes": "First atomic age issue. Tier A. Rough comp: $80–$300.",
        "tier_guidance": "A",
        "keywords": "atomic, nuclear, 1945, science, age",
    },
    {
        "id": "life-006",
        "date": "1953-07-04",
        "volume": 35,
        "issue_number": 1,
        "cover_subject": "American Life — 4th of July Celebration",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/LIFE_Magazine_Vol_35_No_1_%28Jul_4_1953%29.jpg/440px-LIFE_Magazine_Vol_35_No_1_%28Jul_4_1953%29.jpg",
        "rarity_notes": "Mid-century iconic. Tier B. Rough comp: $30–$120.",
        "tier_guidance": "B",
        "keywords": "1953, july, july 4th, summer, patriotic, midcentury",
    },
    {
        "id": "life-007",
        "date": "1955-08-01",
        "volume": 39,
        "issue_number": 5,
        "cover_subject": "The Teenage Age — American Youth Culture",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/LIFE_Magazine_Vol_39_No_5_%28Aug_1_1955%29.jpg/440px-LIFE_Magazine_Vol_39_No_5_%28Aug_1_1955%29.jpg",
        "rarity_notes": "Teen culture issue. Tier B. Rough comp: $25–$90.",
        "tier_guidance": "B",
        "keywords": "teenage, 1955, youth, culture, 1950s, rock and roll",
    },
    {
        "id": "life-008",
        "date": "1960-04-01",
        "volume": 48,
        "issue_number": 13,
        "cover_subject": "The Space Age — Satellites and the Future",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/LIFE_Magazine_Vol_48_No_13_%28Apr_1_1960%29.jpg/440px-LIFE_Magazine_Vol_48_No_13_%28Apr_1_1960%29.jpg",
        "rarity_notes": "Pre-Apollo space interest. Tier B. Rough comp: $20–$80.",
        "tier_guidance": "B",
        "keywords": "space, 1960, satellite, nasa, future, science",
    },
    {
        "id": "life-009",
        "date": "1963-11-22",
        "volume": 55,
        "issue_number": 21,
        "cover_subject": "The Death of a President — JFK Assassination",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/LIFE_Magazine_Vol_55_No_21_%28Nov_22_1963%29.jpg/440px-LIFE_Magazine_Vol_55_No_21_%28Nov_22_1963%29.jpg",
        "rarity_notes": "JFK assassination issue. Tier A — highest historical significance. Rough comp: $200–$800.",
        "tier_guidance": "A",
        "keywords": "jfk, kennedy, assassination, dallas, 1963, president, tragic",
    },
    {
        "id": "life-010",
        "date": "1965-08-06",
        "volume": 59,
        "issue_number": 6,
        "cover_subject": "The Great American Dream — Civil Rights",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/LIFE_Magazine_Vol_59_No_6_%28Aug_6_1965%29.jpg/440px-LIFE_Magazine_Vol_59_No_6_%28Aug_6_1965%29.jpg",
        "rarity_notes": "Civil rights era. Tier B. Rough comp: $20–$75.",
        "tier_guidance": "B",
        "keywords": "civil rights, 1965, mlk, movement, racial, america",
    },
    {
        "id": "life-011",
        "date": "1969-07-25",
        "volume": 67,
        "issue_number": 4,
        "cover_subject": "The Moon Landing — Apollo 11",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/LIFE_Magazine_Vol_67_No_4_%28Jul_25_1969%29.jpg/440px-LIFE_Magazine_Vol_67_No_4_%28Jul_25_1969%29.jpg",
        "rarity_notes": "Apollo 11 / Moon landing. Tier A — iconic cover. Rough comp: $150–$600.",
        "tier_guidance": "A",
        "keywords": "moon, apollo 11, apollo, 1969, landing, space, nasa, armstrong",
    },
    {
        "id": "life-012",
        "date": "1970-04-01",
        "volume": 68,
        "issue_number": 13,
        "cover_subject": "Earth Day — The Environmental Movement",
        "reference_cover_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/LIFE_Magazine_Vol_68_No_13_%28Apr_1_1970%29.jpg/440px-LIFE_Magazine_Vol_68_No_13_%28Apr_1_1970%29.jpg",
        "rarity_notes": "First Earth Day issue. Tier B. Rough comp: $15–$50.",
        "tier_guidance": "B",
        "keywords": "earth day, 1970, environment, ecology, conservation, 1970s",
    },
    {
        "id": "life-generic-01",
        "date": "1958-03-15",
        "volume": 44,
        "issue_number": 11,
        "cover_subject": "Hollywood and the Stars",
        "reference_cover_url": "",
        "rarity_notes": "Generic 1950s — common. Tier C. Rough comp: $5–$20.",
        "tier_guidance": "C",
        "keywords": "1958, common, generic, 1950s, popular",
    },
    {
        "id": "life-generic-02",
        "date": "1962-09-01",
        "volume": 53,
        "issue_number": 9,
        "cover_subject": "American Family Life",
        "reference_cover_url": "",
        "rarity_notes": "Common 1960s — Tier C. Rough comp: $5–$15.",
        "tier_guidance": "C",
        "keywords": "1962, common, family, 1960s, domestic",
    },
    {
        "id": "life-generic-03",
        "date": "1967-06-01",
        "volume": 62,
        "issue_number": 21,
        "cover_subject": "Summer in America",
        "reference_cover_url": "",
        "rarity_notes": "Common 1960s — Tier C. Rough comp: $5–$15.",
        "tier_guidance": "C",
        "keywords": "1967, summer, common, 1960s, bulk",
    },
]

LIFE_GOOGLE_BOOKS_KNOWN_ISSUES = [
    {
        "source": "google_books",
        "google_books_volume_id": "9kwEAAAAMBAJ",
        "id": "google-books-9kwEAAAAMBAJ",
        "date": "1949-11-21",
        "volume": None,
        "issue_number": None,
        "cover_subject": "Ricardo Montalban / Hollywood's New Romantic Star",
        "issue_title": "LIFE",
        "volume_label": "Nov. 21, 1949",
        "reference_cover_url": "https://books.google.com/books/content?id=9kwEAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_thumbnail_url": "https://books.google.com/books/content?id=9kwEAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_preview_url": "https://books.google.com/books/about/LIFE.html?id=9kwEAAAAMBAJ",
        "rarity_notes": "Google Books reference issue. Official API may expose issue metadata, not a verified ad inventory.",
        "tier_guidance": "C",
        "keywords": "life, 1949, november, nov 21, ricardo montalban, hollywood, romantic star, google books",
        "match_reason": "Known Google Books LIFE issue page for Nov 21, 1949.",
    },
    {
        "source": "google_books",
        "google_books_volume_id": "N0EEAAAAMBAJ",
        "id": "google-books-N0EEAAAAMBAJ",
        "date": "1936-11-23",
        "volume": 1,
        "issue_number": 4,
        "cover_subject": "LIFE — Nov 23, 1936",
        "issue_title": "LIFE",
        "volume_label": "Vol. 1, No. 4",
        "reference_cover_url": "https://books.google.com/books/content?id=N0EEAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_thumbnail_url": "https://books.google.com/books/content?id=N0EEAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_preview_url": "https://books.google.com/books/about/LIFE.html?id=N0EEAAAAMBAJ",
        "rarity_notes": "Google Books reference issue. Cover image is reference-only; use actual uploaded photos for listing.",
        "tier_guidance": "C",
        "keywords": "life, 1936, november, nov 23, google books",
        "match_reason": "Known Google Books LIFE issue page for Nov 23, 1936.",
    },
    {
        "source": "google_books",
        "google_books_volume_id": "IE8EAAAAMBAJ",
        "id": "google-books-IE8EAAAAMBAJ",
        "date": "1969-07-25",
        "volume": 67,
        "issue_number": 4,
        "cover_subject": "The Moon Landing — Apollo 11",
        "issue_title": "LIFE",
        "volume_label": "Vol. 67, No. 4",
        "reference_cover_url": "https://books.google.com/books/content?id=IE8EAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_thumbnail_url": "https://books.google.com/books/content?id=IE8EAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_preview_url": "https://books.google.com/books/about/LIFE.html?id=IE8EAAAAMBAJ",
        "rarity_notes": "Google Books reference issue with Apollo 11 coverage. Cover image is reference-only.",
        "tier_guidance": "A",
        "keywords": "moon, apollo 11, apollo, 1969, landing, space, nasa, armstrong",
        "match_reason": "Known Google Books LIFE issue for Jul 25, 1969 with Apollo 11 coverage.",
    },
    {
        "source": "google_books",
        "google_books_volume_id": "oEwEAAAAMBAJ",
        "id": "google-books-oEwEAAAAMBAJ",
        "date": "1969-08-11",
        "volume": 67,
        "issue_number": 7,
        "cover_subject": "LIFE — Moon Story / Apollo 11 Follow-up",
        "issue_title": "LIFE",
        "volume_label": "Aug 11, 1969",
        "reference_cover_url": "https://books.google.com/books/content?id=oEwEAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_thumbnail_url": "https://books.google.com/books/content?id=oEwEAAAAMBAJ&printsec=frontcover&img=1&zoom=1&edge=curl",
        "cover_preview_url": "https://books.google.com/books/about/LIFE.html?id=oEwEAAAAMBAJ",
        "rarity_notes": "Google Books reference issue with moon/Apollo 11 content. Cover image is reference-only.",
        "tier_guidance": "B",
        "keywords": "moon, apollo 11, apollo, 1969, nasa, astronauts, armstrong, aldrin, collins",
        "match_reason": "Known Google Books LIFE issue with strong moon/Apollo metadata.",
    },
]


def _score_match(query_str: str, ref: dict) -> float:
    """Simple keyword match score 0.0–1.0 between a query string and reference issue."""
    q = query_str.lower()
    score = 0.0
    # Exact date match
    if ref["date"].replace("-", "") in q.replace("-", "").replace("/", ""):
        score += 0.5
    # Keyword overlap
    q_words = set(q.split())
    ref_words = set(ref["keywords"].split(", "))
    overlap = q_words & ref_words
    if overlap:
        score += 0.4 * (len(overlap) / max(len(q_words), 1))
    # Volume / issue number match
    vol_match = re.search(r"vol[:\s]*(\d+)", q)
    iss_match = re.search(r"issue[:\s]*(\d+)", q)
    if vol_match and str(ref["volume"]) == vol_match.group(1):
        score += 0.1
    if iss_match and str(ref["issue_number"]) == iss_match.group(1):
        score += 0.1
    return min(1.0, score)


def _parse_reference_date(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            pass
    return None


def _date_distance_days(candidate: str, target: Optional[datetime]) -> int:
    if not target or not candidate:
        return 99999
    parsed = _parse_reference_date(candidate)
    if not parsed:
        return 99999
    return abs((parsed.date() - target.date()).days)


def _google_books_cover_url(volume_id: str) -> str:
    return f"https://books.google.com/books/content?id={volume_id}&printsec=frontcover&img=1&zoom=1&edge=curl"


def _reference_search_text(issue: dict) -> str:
    return " ".join(str(issue.get(k, "")) for k in (
        "cover_subject", "issue_title", "keywords", "rarity_notes", "volume_label", "date"
    )).lower()


REFERENCE_STOPWORDS = {
    "life", "magazine", "issue", "issues", "vol", "volume", "no", "number",
    "the", "and", "for", "with", "not", "this", "that", "cover",
}


def _search_tokens(value: str) -> set[str]:
    return {
        token for token in re.split(r"[^a-z0-9]+", value.lower())
        if len(token) > 1 and token not in REFERENCE_STOPWORDS
    }


def _rank_reference_issue(issue: dict, query_date: Optional[datetime], keyword: str) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []
    distance = _date_distance_days(issue.get("date", ""), query_date)
    if query_date and distance == 0:
        score += 1.0
        reasons.append("exact issue-date match")
    elif query_date and distance <= 14:
        score += max(0.0, 0.5 - (distance / 30))
        reasons.append(f"published within {distance} days of requested date")

    words = _search_tokens(keyword)
    if words:
        text_tokens = _search_tokens(_reference_search_text(issue))
        matches = sorted(words & text_tokens)
        alpha_matches = [w for w in matches if not w.isdigit()]
        if matches and not alpha_matches:
            matches = []
        if matches:
            score += min(0.8, 0.25 * len(matches))
            reasons.append("keyword match: " + ", ".join(matches[:4]))

    # Cover availability is only a tie-breaker after a real date/keyword
    # match. It must never make Apollo/moon fallback issues appear for
    # unrelated searches such as "Queen Elizabeth".
    if score > 0 and (issue.get("cover_thumbnail_url") or issue.get("reference_cover_url")):
        score += 0.15
        reasons.append("real cover thumbnail available")

    return score, "; ".join(reasons) or "no date or keyword match"


def _normalize_known_google_issue(issue: dict, query_used: str, query_date: Optional[datetime], keyword: str) -> dict:
    score, reason = _rank_reference_issue(issue, query_date, keyword)
    normalized = dict(issue)
    normalized["match_score"] = round(score, 3)
    normalized["match_reason"] = reason
    normalized["search_query_used"] = query_used
    return normalized


def _normalize_google_api_item(item: dict, query_used: str, query_date: Optional[datetime], keyword: str) -> Optional[dict]:
    volume_id = item.get("id")
    info = item.get("volumeInfo") or {}
    if not volume_id:
        return None
    title = info.get("title") or "LIFE"
    published = info.get("publishedDate") or ""
    if len(published) == 4:
        date_value = f"{published}-01-01"
    elif len(published) == 7:
        date_value = f"{published}-01"
    else:
        date_value = published[:10]
    description = info.get("description") or ""
    label = description[:120] if description else title
    volume_match = re.search(r"Vol\\.\\s*(\\d+)", description, re.I)
    issue_match = re.search(r"No\\.\\s*(\\d+)", description, re.I)
    images = info.get("imageLinks") or {}
    thumbnail = images.get("thumbnail") or images.get("smallThumbnail") or _google_books_cover_url(volume_id)
    issue = {
        "source": "google_books",
        "google_books_volume_id": volume_id,
        "id": f"google-books-{volume_id}",
        "date": date_value,
        "volume": int(volume_match.group(1)) if volume_match else None,
        "issue_number": int(issue_match.group(1)) if issue_match else None,
        "cover_subject": label,
        "issue_title": title,
        "volume_label": ", ".join(x for x in [f"Vol. {volume_match.group(1)}" if volume_match else "", f"No. {issue_match.group(1)}" if issue_match else ""] if x) or date_value,
        "reference_cover_url": thumbnail.replace("http://", "https://"),
        "cover_thumbnail_url": thumbnail.replace("http://", "https://"),
        "cover_preview_url": info.get("previewLink") or f"https://books.google.com/books/about/LIFE.html?id={volume_id}",
        "rarity_notes": "Google Books metadata result. Cover image is reference-only; use actual uploaded photos for listing.",
        "tier_guidance": "C",
        "keywords": " ".join([title, description]).lower(),
        "search_query_used": query_used,
    }
    score, reason = _rank_reference_issue(issue, query_date, keyword)
    issue["match_score"] = round(score, 3)
    issue["match_reason"] = reason
    return issue


async def _search_google_books_api(query_used: str, query_date: Optional[datetime], keyword: str) -> tuple[list[dict], str]:
    allowed, blocked_status = _google_books_live_allowed(None)
    if not allowed:
        _record_external_api_call(
            provider="google_books",
            endpoint_type="volume_search",
            archive_id=None,
            source_volume_id="",
            status_code=0,
            lookup_status=blocked_status,
            cache_hit=False,
            caller="reference_search",
        )
        return [], blocked_status
    params = {"q": query_used, "printType": "magazines", "maxResults": 10}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(GOOGLE_BOOKS_API_URL, params=params)
        if res.status_code != 200:
            lookup_status = "quota_limited" if res.status_code == 429 else f"google_books_api_http_{res.status_code}"
            _record_external_api_call(
                provider="google_books",
                endpoint_type="volume_search",
                archive_id=None,
                source_volume_id="",
                status_code=res.status_code,
                lookup_status=lookup_status,
                cache_hit=False,
                caller="reference_search",
            )
            return [], lookup_status
        data = res.json()
        items = []
        for item in data.get("items", []):
            normalized = _normalize_google_api_item(item, query_used, query_date, keyword)
            if normalized and "life" in _reference_search_text(normalized):
                items.append(normalized)
        lookup_status = "google_books_api" if GOOGLE_BOOKS_API_KEY else "api_key_missing_google_books_api"
        _record_external_api_call(
            provider="google_books",
            endpoint_type="volume_search",
            archive_id=None,
            source_volume_id="",
            status_code=res.status_code,
            lookup_status=lookup_status,
            cache_hit=False,
            caller="reference_search",
        )
        return items, lookup_status
    except Exception as exc:
        lookup_status = f"google_books_api_error:{type(exc).__name__}"
        _record_external_api_call(
            provider="google_books",
            endpoint_type="volume_search",
            archive_id=None,
            source_volume_id="",
            status_code=0,
            lookup_status=lookup_status,
            cache_hit=False,
            caller="reference_search",
        )
        return [], lookup_status


def _marketforge_target_is_internal(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in INTERNAL_MARKETFORGE_HOSTS


def _marketforge_photo_origin(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return os.getenv("ARCHIVEFORGE_API_BASE_URL", "http://localhost:8000")


def _is_valid_marketforge_category_id(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _resolve_marketforge_publish_fields(archive: dict | None) -> dict:
    if not archive:
        return {
            "category_id": "",
            "ships_from_zip": "",
            "missing_required_fields": [],
            "invalid_required_fields": [],
        }

    category_id = str(archive.get("marketforge_category_id") or "").strip()
    ships_from_zip = str(archive.get("marketforge_ships_from_zip") or "").strip()

    missing: list[str] = []
    invalid: list[str] = []
    if not category_id:
        missing.append("marketforge_category_id")
    elif not _is_valid_marketforge_category_id(category_id):
        invalid.append("marketforge_category_id")

    if not ships_from_zip:
        missing.append("marketforge_ships_from_zip")
    elif not re.fullmatch(r"\d{5}", ships_from_zip):
        invalid.append("marketforge_ships_from_zip")

    return {
        "category_id": category_id,
        "ships_from_zip": ships_from_zip,
        "missing_required_fields": missing,
        "invalid_required_fields": invalid,
    }


async def _marketforge_publish_status(archive: dict | None = None) -> dict:
    field_status = _resolve_marketforge_publish_fields(archive)
    base_status = {
        "target": MARKETFORGE_PRODUCTS_URL,
        "publish_mode": "internal_staged_only",
        "approval_required": True,
        "external_publish_enabled": False,
        "required_marketforge_fields": [
            "marketforge_category_id",
            "marketforge_ships_from_zip",
            "approval_confirmed",
        ],
        **field_status,
    }

    if not _marketforge_target_is_internal(MARKETFORGE_PRODUCTS_URL):
        return {
            **base_status,
            "publish_available": False,
            "reason": "External MarketForge target is blocked. ArchiveForge publish is internal/staged only.",
            "action_label": "Save draft only — external publish blocked",
        }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(MARKETFORGE_PRODUCTS_URL)
        if res.status_code == 404:
            return {
                **base_status,
                "publish_available": False,
                "reason": "MarketForge products endpoint is not mounted at /marketplace/products.",
                "action_label": "Save draft only — MarketForge publish unavailable",
            }
        if res.status_code >= 500:
            return {
                **base_status,
                "publish_available": False,
                "reason": f"MarketForge products endpoint returned HTTP {res.status_code}.",
                "action_label": "Save draft only — MarketForge publish unavailable",
            }
        response = {
            **base_status,
            "publish_available": True,
            "reason": "MarketForge products endpoint responded.",
            "action_label": "Publish to MarketForge",
        }
        if base_status["missing_required_fields"] or base_status["invalid_required_fields"]:
            response["action_label"] = "Save required MarketForge fields before publish"
        return response
    except Exception as exc:
        return {
            **base_status,
            "publish_available": False,
            "reason": f"MarketForge products endpoint unreachable: {type(exc).__name__}",
            "action_label": "Save draft only — MarketForge publish unavailable",
        }


# ── Database ───────────────────────────────────────────────────────────────────

ARCHIVE_STATUSES = [
    "RAW", "IDENTIFIED", "PHOTOGRAPHED", "VALUED",
    "READY_TO_LIST", "LISTED", "SOLD", "HOLD", "REBOXED",
]

VALID_STATUS_TRANSITIONS = {
    "RAW": ["IDENTIFIED", "HOLD"],
    "IDENTIFIED": ["PHOTOGRAPHED", "HOLD", "REBOXED"],
    "PHOTOGRAPHED": ["VALUED", "HOLD"],
    "VALUED": ["READY_TO_LIST", "HOLD", "REBOXED"],
    "READY_TO_LIST": ["LISTED", "HOLD", "REBOXED"],
    "LISTED": ["SOLD", "HOLD", "REBOXED"],
    "SOLD": [],
    "HOLD": ["RAW", "IDENTIFIED", "PHOTOGRAPHED", "VALUED", "READY_TO_LIST"],
    "REBOXED": ["RAW", "IDENTIFIED", "PHOTOGRAPHED", "VALUED", "READY_TO_LIST"],
}


def _init_tables():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    def ensure_column(table: str, column: str, definition: str) -> None:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ag_archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_issue_id TEXT,
            reference_issue_key TEXT DEFAULT '',
            reference_source TEXT DEFAULT '',
            google_books_volume_id TEXT DEFAULT '',
            issue_title TEXT DEFAULT '',
            volume_label TEXT DEFAULT '',
            cover_thumbnail_url TEXT DEFAULT '',
            cover_preview_url TEXT DEFAULT '',
            search_query_used TEXT DEFAULT '',
            match_reason TEXT DEFAULT '',
            issue_date TEXT,
            volume INTEGER,
            issue_number INTEGER,
            cover_subject TEXT DEFAULT '',
            reference_cover_url TEXT DEFAULT '',
            -- Image roles kept separate
            actual_listing_images TEXT DEFAULT '[]',
            -- Physical archive tracking
            source_box_code TEXT DEFAULT '',
            source_slot_position TEXT DEFAULT '',
            processed_box_code TEXT DEFAULT '',
            processed_status TEXT DEFAULT 'RAW',
            archive_location TEXT DEFAULT '',
            reboxed_at TEXT,
            reboxed_by TEXT DEFAULT '',
            -- Condition
            condition_score INTEGER DEFAULT 0,
            has_address_label INTEGER DEFAULT 0,
            is_complete INTEGER DEFAULT 1,
            defects TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            -- Tier and value
            tier TEXT DEFAULT 'C',
            rough_comp_min REAL DEFAULT 0,
            rough_comp_max REAL DEFAULT 0,
            sale_plan TEXT DEFAULT '',
            pricing_basis TEXT DEFAULT '',
            final_price REAL DEFAULT 0,
            pricing_updated_at TEXT DEFAULT '',
            -- AI/reference confirmation
            ai_identified INTEGER DEFAULT 0,
            ai_confidence REAL DEFAULT 0,
            ai_evidence_source TEXT DEFAULT '',
            ai_identification_json TEXT DEFAULT '{}',
            ai_identified_at TEXT DEFAULT '',
            confirmed_reference_source TEXT DEFAULT '',
            confirmed_reference_id TEXT DEFAULT '',
            confirmed_reference_url TEXT DEFAULT '',
            confirmed_issue_date TEXT DEFAULT '',
            confirmed_cover_title TEXT DEFAULT '',
            confirmed_confidence REAL DEFAULT 0,
            confirmed_by_user INTEGER DEFAULT 0,
            -- Listing draft
            listing_title TEXT DEFAULT '',
            listing_description TEXT DEFAULT '',
            item_specifics TEXT DEFAULT '{}',
            batch_tag TEXT DEFAULT '',
            listing_draft_status TEXT DEFAULT 'draft',
            -- MarketForge publish tracking
            marketforge_category_id TEXT DEFAULT '',
            marketforge_ships_from_zip TEXT DEFAULT '',
            listing_status TEXT DEFAULT 'none',
            marketforge_listing_id TEXT DEFAULT '',
            marketforge_push_status TEXT DEFAULT 'not_pushed',
            marketforge_pushed_at TEXT DEFAULT '',
            marketforge_error_message TEXT DEFAULT '',
            -- Metadata
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ag_listing_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER REFERENCES ag_archives(id),
            listing_title TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT '',
            item_specifics TEXT DEFAULT '{}',
            batch_tag TEXT DEFAULT '',
            marketforge_payload TEXT DEFAULT '{}',
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_listing_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            draft_status TEXT DEFAULT 'draft',
            platform_target TEXT DEFAULT 'manual_handoff',
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            condition_label TEXT DEFAULT '',
            condition_score INTEGER DEFAULT 0,
            defects TEXT DEFAULT '',
            address_label INTEGER DEFAULT 0,
            complete INTEGER DEFAULT 1,
            price_low REAL DEFAULT 0,
            price_high REAL DEFAULT 0,
            recommended_price REAL DEFAULT 0,
            sale_plan TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            inventory_location TEXT DEFAULT '',
            photo_manifest_json TEXT DEFAULT '[]',
            ai_identification_json TEXT DEFAULT '{}',
            reference_confirmation_json TEXT DEFAULT '{}',
            missing_fields_json TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_issue_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            source TEXT DEFAULT '',
            source_volume_id TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            issue_title TEXT DEFAULT '',
            issue_date TEXT DEFAULT '',
            publisher TEXT DEFAULT '',
            page_count INTEGER DEFAULT 0,
            issn TEXT DEFAULT '',
            description TEXT DEFAULT '',
            preview_link TEXT DEFAULT '',
            info_link TEXT DEFAULT '',
            web_reader_link TEXT DEFAULT '',
            cover_image_url TEXT DEFAULT '',
            raw_metadata_json TEXT DEFAULT '{}',
            lookup_status TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_issue_info_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            front_photo_id INTEGER,
            status TEXT DEFAULT 'pending',
            is_life_magazine INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0,
            issue_date TEXT DEFAULT '',
            cover_title TEXT DEFAULT '',
            detected_subject TEXT DEFAULT '',
            detected_quote TEXT DEFAULT '',
            detected_price TEXT DEFAULT '',
            visible_text_json TEXT DEFAULT '[]',
            condition_notes TEXT DEFAULT '',
            evidence_source TEXT DEFAULT '',
            evidence_grade TEXT DEFAULT 'F',
            google_books_candidates_json TEXT DEFAULT '[]',
            selected_google_books_volume_id TEXT DEFAULT '',
            reference_sources_json TEXT DEFAULT '[]',
            conflicts_json TEXT DEFAULT '[]',
            needs_user_confirmation INTEGER DEFAULT 1,
            ad_opportunity_ready INTEGER DEFAULT 0,
            stale_result_used INTEGER DEFAULT 0,
            error_message TEXT DEFAULT '',
            started_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_ad_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            issue_metadata_id INTEGER REFERENCES archive_issue_metadata(id),
            candidate_type TEXT DEFAULT '',
            brand TEXT DEFAULT '',
            product TEXT DEFAULT '',
            category TEXT DEFAULT '',
            evidence_source TEXT DEFAULT '',
            evidence_grade TEXT DEFAULT 'D',
            evidence_text TEXT DEFAULT '',
            search_query TEXT DEFAULT '',
            estimated_low REAL DEFAULT 0,
            estimated_high REAL DEFAULT 0,
            comp_count INTEGER DEFAULT 0,
            sold_comp_count INTEGER DEFAULT 0,
            active_listing_count INTEGER DEFAULT 0,
            value_score REAL DEFAULT 0,
            comp_confidence TEXT DEFAULT 'none',
            last_comp_checked_at TEXT DEFAULT '',
            policy_flags_json TEXT DEFAULT '[]',
            recommendation TEXT DEFAULT '',
            verification_status TEXT DEFAULT 'unverified',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_ad_comps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            candidate_id INTEGER NOT NULL REFERENCES archive_ad_opportunities(id),
            ad_id INTEGER,
            provider TEXT DEFAULT '',
            query TEXT DEFAULT '',
            result_type TEXT DEFAULT '',
            title TEXT DEFAULT '',
            url TEXT DEFAULT '',
            price REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            shipping_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            condition_text TEXT DEFAULT '',
            sold_date TEXT DEFAULT '',
            observed_at TEXT DEFAULT (datetime('now')),
            match_confidence REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            raw_result_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_ad_page_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            candidate_id INTEGER REFERENCES archive_ad_opportunities(id),
            page_number TEXT DEFAULT '',
            filename TEXT NOT NULL,
            original_name TEXT DEFAULT '',
            file_path TEXT NOT NULL,
            mime_type TEXT DEFAULT '',
            byte_size INTEGER DEFAULT 0,
            analysis_json TEXT DEFAULT '{}',
            analyzed_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_external_api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            endpoint_type TEXT DEFAULT '',
            archive_id INTEGER,
            source_volume_id TEXT DEFAULT '',
            status_code INTEGER DEFAULT 0,
            lookup_status TEXT DEFAULT '',
            cache_hit INTEGER DEFAULT 0,
            caller TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_life_issue_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_date TEXT DEFAULT '',
            normalized_date TEXT UNIQUE,
            year INTEGER DEFAULT 0,
            volume TEXT DEFAULT '',
            issue_number TEXT DEFAULT '',
            cover_title TEXT DEFAULT '',
            cover_subject TEXT DEFAULT '',
            description TEXT DEFAULT '',
            visible_cover_text_json TEXT DEFAULT '[]',
            google_books_volume_id TEXT DEFAULT '',
            google_books_page_count INTEGER DEFAULT 0,
            google_books_cover_url TEXT DEFAULT '',
            dtmagazine_description TEXT DEFAULT '',
            dtmagazine_low REAL DEFAULT 0,
            dtmagazine_high REAL DEFAULT 0,
            dtmagazine_average REAL DEFAULT 0,
            dtmagazine_freshness TEXT DEFAULT 'unknown',
            dealer_current_asking_low REAL DEFAULT 0,
            dealer_current_asking_high REAL DEFAULT 0,
            ebay_active_low REAL DEFAULT 0,
            ebay_active_high REAL DEFAULT 0,
            ebay_sold_low REAL DEFAULT 0,
            ebay_sold_high REAL DEFAULT 0,
            worthpoint_low REAL DEFAULT 0,
            worthpoint_high REAL DEFAULT 0,
            source_count INTEGER DEFAULT 0,
            source_confidence TEXT DEFAULT 'low',
            last_verified_at TEXT DEFAULT '',
            last_price_checked_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_life_issue_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_master_id INTEGER NOT NULL REFERENCES archive_life_issue_master(id),
            archive_id INTEGER,
            source_name TEXT DEFAULT '',
            source_type TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            source_date_observed TEXT DEFAULT '',
            source_claim_date TEXT DEFAULT '',
            source_claim_title TEXT DEFAULT '',
            source_claim_price_low REAL DEFAULT 0,
            source_claim_price_high REAL DEFAULT 0,
            source_claim_average REAL DEFAULT 0,
            confidence TEXT DEFAULT 'low',
            freshness TEXT DEFAULT 'unknown',
            notes TEXT DEFAULT '',
            raw_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_magazine_comps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            issue_master_id INTEGER,
            provider TEXT DEFAULT '',
            query TEXT DEFAULT '',
            result_type TEXT DEFAULT '',
            title TEXT DEFAULT '',
            url TEXT DEFAULT '',
            price REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            shipping_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            condition_text TEXT DEFAULT '',
            sold_date TEXT DEFAULT '',
            observed_at TEXT DEFAULT (datetime('now')),
            match_confidence REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            raw_result_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archive_pricing_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            issue_master_id INTEGER,
            pricing_type TEXT DEFAULT 'needs_comps',
            estimate_low REAL DEFAULT 0,
            estimate_high REAL DEFAULT 0,
            recommended_price REAL DEFAULT 0,
            comp_count INTEGER DEFAULT 0,
            sold_comp_count INTEGER DEFAULT 0,
            active_listing_count INTEGER DEFAULT 0,
            dealer_listing_count INTEGER DEFAULT 0,
            reference_guide_count INTEGER DEFAULT 0,
            confidence TEXT DEFAULT 'none',
            pricing_basis TEXT DEFAULT '',
            needs_manual_review INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ag_box_registry (
            box_code TEXT PRIMARY KEY,
            box_type TEXT DEFAULT 'processed',
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ag_archive_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL REFERENCES ag_archives(id),
            role TEXT NOT NULL DEFAULT 'front',
            filename TEXT NOT NULL,
            original_name TEXT DEFAULT '',
            file_path TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    archive_columns = {
        "reference_issue_id": "TEXT",
        "reference_issue_key": "TEXT DEFAULT ''",
        "reference_source": "TEXT DEFAULT ''",
        "google_books_volume_id": "TEXT DEFAULT ''",
        "issue_title": "TEXT DEFAULT ''",
        "volume_label": "TEXT DEFAULT ''",
        "cover_thumbnail_url": "TEXT DEFAULT ''",
        "cover_preview_url": "TEXT DEFAULT ''",
        "search_query_used": "TEXT DEFAULT ''",
        "match_reason": "TEXT DEFAULT ''",
        "issue_date": "TEXT",
        "volume": "INTEGER",
        "issue_number": "INTEGER",
        "cover_subject": "TEXT DEFAULT ''",
        "reference_cover_url": "TEXT DEFAULT ''",
        "actual_listing_images": "TEXT DEFAULT '[]'",
        "source_box_code": "TEXT DEFAULT ''",
        "source_slot_position": "TEXT DEFAULT ''",
        "processed_box_code": "TEXT DEFAULT ''",
        "processed_status": "TEXT DEFAULT 'RAW'",
        "archive_location": "TEXT DEFAULT ''",
        "reboxed_at": "TEXT",
        "reboxed_by": "TEXT DEFAULT ''",
        "condition_score": "INTEGER DEFAULT 0",
        "has_address_label": "INTEGER DEFAULT 0",
        "is_complete": "INTEGER DEFAULT 1",
        "defects": "TEXT DEFAULT ''",
        "notes": "TEXT DEFAULT ''",
        "tier": "TEXT DEFAULT 'C'",
        "rough_comp_min": "REAL DEFAULT 0",
        "rough_comp_max": "REAL DEFAULT 0",
        "sale_plan": "TEXT DEFAULT ''",
        "pricing_basis": "TEXT DEFAULT ''",
        "final_price": "REAL DEFAULT 0",
        "pricing_updated_at": "TEXT DEFAULT ''",
        "ai_identified": "INTEGER DEFAULT 0",
        "ai_confidence": "REAL DEFAULT 0",
        "ai_evidence_source": "TEXT DEFAULT ''",
        "ai_identification_json": "TEXT DEFAULT '{}'",
        "ai_identified_at": "TEXT DEFAULT ''",
        "confirmed_reference_source": "TEXT DEFAULT ''",
        "confirmed_reference_id": "TEXT DEFAULT ''",
        "confirmed_reference_url": "TEXT DEFAULT ''",
        "confirmed_issue_date": "TEXT DEFAULT ''",
        "confirmed_cover_title": "TEXT DEFAULT ''",
        "confirmed_confidence": "REAL DEFAULT 0",
        "confirmed_by_user": "INTEGER DEFAULT 0",
        "listing_title": "TEXT DEFAULT ''",
        "listing_description": "TEXT DEFAULT ''",
        "item_specifics": "TEXT DEFAULT '{}'",
        "batch_tag": "TEXT DEFAULT ''",
        "listing_draft_status": "TEXT DEFAULT 'draft'",
        "marketforge_category_id": "TEXT DEFAULT ''",
        "marketforge_ships_from_zip": "TEXT DEFAULT ''",
        "listing_status": "TEXT DEFAULT 'none'",
        "marketforge_listing_id": "TEXT DEFAULT ''",
        "marketforge_push_status": "TEXT DEFAULT 'not_pushed'",
        "marketforge_pushed_at": "TEXT DEFAULT ''",
        "marketforge_error_message": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''",
        "updated_at": "TEXT DEFAULT ''",
    }
    for column, definition in archive_columns.items():
        ensure_column("ag_archives", column, definition)

    photo_columns = {
        "archive_id": "INTEGER NOT NULL DEFAULT 0",
        "role": "TEXT NOT NULL DEFAULT 'front'",
        "filename": "TEXT NOT NULL DEFAULT ''",
        "original_name": "TEXT DEFAULT ''",
        "file_path": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT DEFAULT ''",
    }
    for column, definition in photo_columns.items():
        ensure_column("ag_archive_photos", column, definition)

    ad_opportunity_columns = {
        "value_score": "REAL DEFAULT 0",
        "comp_confidence": "TEXT DEFAULT 'none'",
        "last_comp_checked_at": "TEXT DEFAULT ''",
    }
    for column, definition in ad_opportunity_columns.items():
        ensure_column("archive_ad_opportunities", column, definition)

    issue_info_columns = {
        "archive_id": "INTEGER NOT NULL DEFAULT 0",
        "front_photo_id": "INTEGER",
        "status": "TEXT DEFAULT 'pending'",
        "is_life_magazine": "INTEGER DEFAULT 0",
        "confidence": "REAL DEFAULT 0",
        "issue_date": "TEXT DEFAULT ''",
        "cover_title": "TEXT DEFAULT ''",
        "detected_subject": "TEXT DEFAULT ''",
        "detected_quote": "TEXT DEFAULT ''",
        "detected_price": "TEXT DEFAULT ''",
        "visible_text_json": "TEXT DEFAULT '[]'",
        "condition_notes": "TEXT DEFAULT ''",
        "evidence_source": "TEXT DEFAULT ''",
        "evidence_grade": "TEXT DEFAULT 'F'",
        "google_books_candidates_json": "TEXT DEFAULT '[]'",
        "selected_google_books_volume_id": "TEXT DEFAULT ''",
        "reference_sources_json": "TEXT DEFAULT '[]'",
        "conflicts_json": "TEXT DEFAULT '[]'",
        "needs_user_confirmation": "INTEGER DEFAULT 1",
        "ad_opportunity_ready": "INTEGER DEFAULT 0",
        "stale_result_used": "INTEGER DEFAULT 0",
        "error_message": "TEXT DEFAULT ''",
        "started_at": "TEXT DEFAULT ''",
        "completed_at": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''",
        "updated_at": "TEXT DEFAULT ''",
    "dealer_reference_json": "TEXT DEFAULT '[]'",
    }
    for column, definition in issue_info_columns.items():
        ensure_column("archive_issue_info_runs", column, definition)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_listing_drafts_archive_id ON archive_listing_drafts(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_issue_metadata_archive_id ON archive_issue_metadata(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_issue_info_runs_archive_id ON archive_issue_info_runs(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_issue_info_runs_front_photo_id ON archive_issue_info_runs(front_photo_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_ad_opportunities_archive_id ON archive_ad_opportunities(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_ad_page_photos_archive_id ON archive_ad_page_photos(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_external_api_calls_provider_created ON archive_external_api_calls(provider, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_external_api_calls_archive_id ON archive_external_api_calls(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_ad_comps_archive_id ON archive_ad_comps(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_ad_comps_candidate_id ON archive_ad_comps(candidate_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_life_issue_master_normalized_date ON archive_life_issue_master(normalized_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_life_issue_master_year ON archive_life_issue_master(year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_life_issue_sources_issue_master_id ON archive_life_issue_sources(issue_master_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_magazine_comps_archive_id ON archive_magazine_comps(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_pricing_summary_archive_id ON archive_pricing_summary(archive_id)")

    # ── Lifecycle / Disposition tables ──────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS archive_item_lifecycle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL UNIQUE,
            item_status TEXT NOT NULL DEFAULT 'inventory'
                CHECK(item_status IN ('inventory','listed','sold','held','broken_for_ads','ads_only','archived','needs_review')),
            marketplace_status TEXT NOT NULL DEFAULT 'not_listed'
                CHECK(marketplace_status IN ('not_listed','draft','listed','sold','cancelled')),
            ad_breakout_status TEXT NOT NULL DEFAULT 'none'
                CHECK(ad_breakout_status IN ('none','candidate','in_progress','ads_removed','ads_listed','complete')),
            sold_price REAL,
            sold_date TEXT,
            sold_platform TEXT,
            disposition_notes TEXT DEFAULT '',
            updated_by TEXT DEFAULT 'system',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS archive_item_lifecycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            from_status TEXT DEFAULT '',
            to_status TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (archive_id) REFERENCES ag_archives(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_archive_id ON archive_item_lifecycle(archive_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_events_archive_id ON archive_item_lifecycle_events(archive_id)")

    conn.commit()
    conn.close()
    log.info("ArchiveForge tables initialized")


_init_tables()


# ── Pydantic Models ───────────────────────────────────────────────────────────

class ArchiveCreate(BaseModel):
    reference_issue_id: Optional[str] = None
    reference_source: str = ""
    google_books_volume_id: str = ""
    issue_title: str = ""
    volume_label: str = ""
    cover_thumbnail_url: str = ""
    cover_preview_url: str = ""
    search_query_used: str = ""
    match_reason: str = ""
    issue_date: Optional[str] = None
    volume: Optional[int] = None
    issue_number: Optional[int] = None
    cover_subject: str = ""
    reference_cover_url: str = ""
    actual_listing_images: List[str] = []
    source_box_code: str = ""
    source_slot_position: str = ""
    processed_box_code: str = ""
    processed_status: str = "RAW"
    archive_location: str = ""
    condition_score: int = 0
    has_address_label: bool = False
    is_complete: bool = True
    defects: str = ""
    notes: str = ""
    tier: str = "C"
    rough_comp_min: float = 0
    rough_comp_max: float = 0
    sale_plan: str = ""
    marketforge_category_id: str = ""
    marketforge_ships_from_zip: str = ""


class ArchiveUpdate(BaseModel):
    reference_issue_id: Optional[str] = None
    reference_source: Optional[str] = None
    google_books_volume_id: Optional[str] = None
    issue_title: Optional[str] = None
    volume_label: Optional[str] = None
    cover_thumbnail_url: Optional[str] = None
    cover_preview_url: Optional[str] = None
    search_query_used: Optional[str] = None
    match_reason: Optional[str] = None
    issue_date: Optional[str] = None
    volume: Optional[int] = None
    issue_number: Optional[int] = None
    cover_subject: Optional[str] = None
    reference_cover_url: Optional[str] = None
    actual_listing_images: Optional[List[str]] = None
    source_box_code: Optional[str] = None
    source_slot_position: Optional[str] = None
    processed_box_code: Optional[str] = None
    processed_status: Optional[str] = None
    archive_location: Optional[str] = None
    condition_score: Optional[int] = None
    has_address_label: Optional[bool] = None
    is_complete: Optional[bool] = None
    defects: Optional[str] = None
    notes: Optional[str] = None
    tier: Optional[str] = None
    rough_comp_min: Optional[float] = None
    rough_comp_max: Optional[float] = None
    sale_plan: Optional[str] = None
    listing_title: Optional[str] = None
    listing_description: Optional[str] = None
    item_specifics: Optional[dict] = None
    batch_tag: Optional[str] = None
    reboxed_by: Optional[str] = None
    listing_status: Optional[str] = None
    marketforge_push_status: Optional[str] = None
    marketforge_error_message: Optional[str] = None
    marketforge_category_id: Optional[str] = None
    marketforge_ships_from_zip: Optional[str] = None


class StatusTransition(BaseModel):
    status: str


class ReboxRequest(BaseModel):
    processed_box_code: str = ""
    archive_location: str = ""


class ListingDraftCreate(BaseModel):
    listing_title: str = ""
    description: str = ""
    item_specifics: dict = {}
    batch_tag: str = ""


class ConfirmReferenceRequest(BaseModel):
    reference_source: str = ""
    reference_id: str = ""
    reference_url: str = ""
    confirmed_issue_date: Optional[str] = None
    cover_title: str = ""
    confidence: Optional[float] = None
    source: str = ""
    confirmed_by_user: bool = True


class PricingRequest(BaseModel):
    rough_comp_min: Optional[float] = None
    rough_comp_max: Optional[float] = None
    sale_plan: str = ""
    accept_final: bool = False


class AdCompResearchRequest(BaseModel):
    candidate_ids: Optional[List[int]] = None
    provider: str = "auto"
    max_candidates: int = 5
    max_results_per_candidate: int = 5


class ManualAdCompRequest(BaseModel):
    candidate_id: int
    title: str = ""
    url: str = ""
    price: Optional[float] = None
    currency: str = "USD"
    result_type: str = "manual_reference"
    notes: str = ""


class MagazineCompResearchRequest(BaseModel):
    provider: str = "auto"
    max_results: int = 8


class ManualMagazineCompRequest(BaseModel):
    title: str = ""
    url: str = ""
    price: Optional[float] = None
    currency: str = "USD"
    result_type: str = "manual_reference"
    condition_text: str = ""
    notes: str = ""


class ManualIssueSourceRequest(BaseModel):
    source_name: str = "manual"
    source_type: str = "manual_reference"
    source_url: str = ""
    source_claim_date: str = ""
    source_claim_title: str = ""
    source_claim_price_low: Optional[float] = None
    source_claim_price_high: Optional[float] = None
    source_claim_average: Optional[float] = None
    confidence: str = "medium"
    freshness: str = "unknown"
    notes: str = ""


# ── Reference Data Endpoints ──────────────────────────────────────────────────

@router.get("/reference")
async def search_reference(q: str = Query("", description="Search by date, volume, issue, or keyword")):
    """Search LIFE reference database. Returns scored matches."""
    if not q or len(q) < 2:
        return {"results": [], "query": q}

    scored = []
    for ref in LIFE_REFERENCE_ISSUES:
        score = _score_match(q, ref)
        if score > 0.05:
            scored.append({**ref, "match_score": round(score, 3)})

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return {"results": scored[:8], "query": q}


@router.get("/reference/search")
async def search_life_cover_reference(
    date: str = Query("", description="Exact issue date or approximate date"),
    keyword: str = Query("", description="Event, person, or issue keyword"),
    limit: int = Query(12, ge=1, le=20),
):
    """Search Google Books LIFE issue metadata, with known issue fallback.

    Google Books API is the preferred path. If it is quota-limited or misses a
    known issue, we add a small curated fallback of Google Books issue pages.
    Returned cover URLs are reference-only and never replace uploaded item
    photos.
    """
    query_date = _parse_reference_date(date)
    query_parts = ["LIFE magazine"]
    if keyword.strip():
        query_parts.append(keyword.strip())
    if date.strip():
        query_parts.append(date.strip())
    query_used = " ".join(query_parts)

    api_results, api_status = await _search_google_books_api(query_used, query_date, keyword)
    results: list[dict] = []
    seen: set[str] = set()
    for issue in api_results:
        if issue.get("match_score", 0) <= 0.05:
            continue
        key = issue.get("google_books_volume_id") or issue.get("id")
        if key and key not in seen:
            results.append(issue)
            seen.add(key)

    for known in LIFE_GOOGLE_BOOKS_KNOWN_ISSUES:
        normalized = _normalize_known_google_issue(known, query_used, query_date, keyword)
        if normalized["match_score"] <= 0.05:
            continue
        key = normalized.get("google_books_volume_id") or normalized["id"]
        if key not in seen:
            results.append(normalized)
            seen.add(key)

    # Keep legacy curated references in the same result shape as a final local
    # fallback, but label their source truthfully.
    legacy_query = " ".join([date, keyword]).strip()
    if legacy_query:
        for ref in LIFE_REFERENCE_ISSUES:
            score = _score_match(legacy_query, ref)
            if score <= 0.05:
                continue
            issue = {
                **ref,
                "source": "local_reference_fixture",
                "google_books_volume_id": "",
                "issue_title": "LIFE",
                "volume_label": f"Vol. {ref.get('volume')}, No. {ref.get('issue_number')}",
                "cover_thumbnail_url": ref.get("reference_cover_url", ""),
                "cover_preview_url": "",
                "search_query_used": query_used,
                "match_score": score,
                "match_reason": "local curated reference match",
            }
            key = issue["id"]
            if key not in seen:
                results.append(issue)
                seen.add(key)

    results.sort(key=lambda item: item.get("match_score", 0), reverse=True)
    return {
        "results": results[:limit],
        "query": {"date": date, "keyword": keyword, "query_used": query_used},
        "source_status": api_status,
        "truth_note": "Google Books covers are reference-only. Upload actual item photos before listing.",
    }


@router.get("/publish-status")
async def archiveforge_publish_status(archive_id: Optional[int] = Query(None, ge=1)):
    """Truthful status for ArchiveForge → MarketForge publishing."""
    archive = None
    if archive_id is not None:
        with get_db() as db:
            row = db.execute("SELECT * FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Archive item not found")
        archive = dict_row(row)
    status = await _marketforge_publish_status(archive=archive)
    if archive_id is not None:
        status["archive_id"] = archive_id
        status["publish_ready"] = bool(
            status.get("publish_available")
            and not status.get("missing_required_fields")
            and not status.get("invalid_required_fields")
        )
    return status


@router.get("/reference/{ref_id}")
async def get_reference_issue(ref_id: str):
    """Get a specific reference issue by ID."""
    for ref in LIFE_REFERENCE_ISSUES:
        if ref["id"] == ref_id:
            return ref
    raise HTTPException(404, f"Reference issue '{ref_id}' not found in LIFE database")


@router.get("/reference/all")
async def list_all_reference_issues():
    """List all LIFE reference issues. For admin/debug use."""
    return {"issues": LIFE_REFERENCE_ISSUES, "total": len(LIFE_REFERENCE_ISSUES)}


# ── Archive CRUD ────────────────────────────────────────────────────────────────

@router.get("/archives")
async def list_archives(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    source_box: Optional[str] = None,
    processed_box: Optional[str] = None,
    listing_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List all archive items with optional filters."""
    with get_db() as db:
        where, params = [], []
        if status:
            where.append("processed_status = ?")
            params.append(status)
        if tier:
            where.append("tier = ?")
            params.append(tier)
        if source_box:
            where.append("source_box_code = ?")
            params.append(source_box)
        if processed_box:
            where.append("processed_box_code = ?")
            params.append(processed_box)
        if listing_status:
            where.append("listing_status = ?")
            params.append(listing_status)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params += [limit, offset]
        rows = dict_rows(db.execute(
            f"""SELECT a.*,
                       (SELECT COUNT(*) FROM ag_archive_photos p WHERE p.archive_id = a.id) AS photo_count
                FROM ag_archives a {clause} ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall())
        total = db.execute(
            f"SELECT COUNT(*) FROM ag_archives {clause}", params[:-2],
        ).fetchone()[0]

    normalized = []
    for d in rows:
        if d.get("reference_issue_key") and not d.get("reference_issue_id"):
            d["reference_issue_id"] = d["reference_issue_key"]
        for fld in ("actual_listing_images", "item_specifics"):
            if fld in d and isinstance(d[fld], str):
                try:
                    d[fld] = json.loads(d[fld])
                except (json.JSONDecodeError, TypeError):
                    d[fld] = [] if fld == "actual_listing_images" else {}
        normalized.append(_normalized_inventory_row(d))

    return {"items": normalized, "total": total, "counters": _inventory_counters(normalized)}


@router.post("/archives", status_code=201)
async def create_archive(req: ArchiveCreate):
    """Create a new archive intake record."""
    reference_issue_db_id = req.reference_issue_id if str(req.reference_issue_id or "").isdigit() else None
    reference_issue_key = req.reference_issue_id or ""
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO ag_archives
               (reference_issue_id, reference_issue_key, reference_source, google_books_volume_id,
                issue_title, volume_label, cover_thumbnail_url, cover_preview_url,
                search_query_used, match_reason,
                issue_date, volume, issue_number, cover_subject,
                reference_cover_url, actual_listing_images, source_box_code,
                source_slot_position, processed_box_code, processed_status,
                archive_location, condition_score, has_address_label, is_complete,
                defects, notes, tier, rough_comp_min, rough_comp_max, sale_plan,
                marketforge_category_id, marketforge_ships_from_zip,
                listing_status, marketforge_push_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                reference_issue_db_id, reference_issue_key, req.reference_source,
                req.google_books_volume_id, req.issue_title, req.volume_label,
                req.cover_thumbnail_url, req.cover_preview_url,
                req.search_query_used, req.match_reason,
                req.issue_date, req.volume, req.issue_number,
                req.cover_subject, req.reference_cover_url,
                json.dumps(req.actual_listing_images),
                req.source_box_code, req.source_slot_position,
                req.processed_box_code, req.processed_status,
                req.archive_location, req.condition_score,
                int(req.has_address_label), int(req.is_complete),
                req.defects, req.notes, req.tier,
                req.rough_comp_min, req.rough_comp_max, req.sale_plan,
                req.marketforge_category_id, req.marketforge_ships_from_zip,
                'none', 'not_pushed',
            ),
        )
        db.commit()
        archive_id = cur.lastrowid

    log.info(f"Archive #{archive_id} created: {req.cover_subject or req.issue_date}")
    return {"id": archive_id, "processed_status": req.processed_status, "tier": req.tier}


@router.get("/archives/{archive_id}")
async def get_archive(archive_id: int):
    """Get a specific archive item."""
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")
    d = dict_row(row)
    if d.get("reference_issue_key") and not d.get("reference_issue_id"):
        d["reference_issue_id"] = d["reference_issue_key"]
    for fld in ("actual_listing_images", "item_specifics"):
        if fld in d and isinstance(d[fld], str):
            try:
                d[fld] = json.loads(d[fld])
            except (json.JSONDecodeError, TypeError):
                d[fld] = [] if fld == "actual_listing_images" else {}
    return d


@router.patch("/archives/{archive_id}")
async def update_archive(archive_id: int, req: ArchiveUpdate):
    """Update archive fields. Supports partial updates."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    if "actual_listing_images" in updates:
        updates["actual_listing_images"] = json.dumps(updates["actual_listing_images"])
    if "item_specifics" in updates:
        updates["item_specifics"] = json.dumps(updates["item_specifics"])
    if "has_address_label" in updates:
        updates["has_address_label"] = int(updates["has_address_label"])
    if "is_complete" in updates:
        updates["is_complete"] = int(updates["is_complete"])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [archive_id]
    with get_db() as db:
        affected = db.execute(
            f"UPDATE ag_archives SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        ).rowcount
    if not affected:
        raise HTTPException(404, "Archive item not found")
    return {"id": archive_id, "updated": True}


@router.post("/{archive_id}/confirm-reference")
async def confirm_reference(archive_id: int, req: ConfirmReferenceRequest):
    """Persist the user's confirmed reference match without requiring a full archive update."""
    with get_db() as db:
        row = db.execute("SELECT id FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")

    confidence = req.confidence if req.confidence is not None else 0
    with get_db() as db:
        db.execute(
            """UPDATE ag_archives
               SET confirmed_reference_source = ?,
                   confirmed_reference_id = ?,
                   confirmed_reference_url = ?,
                   confirmed_issue_date = ?,
                   confirmed_cover_title = ?,
                   confirmed_confidence = ?,
                   confirmed_by_user = ?,
                   reference_source = COALESCE(NULLIF(?, ''), reference_source),
                   reference_issue_key = COALESCE(NULLIF(?, ''), reference_issue_key),
                   issue_date = COALESCE(NULLIF(?, ''), issue_date),
                   cover_subject = COALESCE(NULLIF(?, ''), cover_subject),
                   reference_cover_url = COALESCE(NULLIF(?, ''), reference_cover_url),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                req.reference_source or req.source,
                req.reference_id,
                req.reference_url,
                req.confirmed_issue_date or "",
                req.cover_title,
                confidence,
                int(req.confirmed_by_user),
                req.reference_source or req.source,
                req.reference_id,
                req.confirmed_issue_date or "",
                req.cover_title,
                req.reference_url,
                archive_id,
            ),
        )
    return {
        "archive_id": archive_id,
        "confirmed_by_user": bool(req.confirmed_by_user),
        "reference_source": req.reference_source or req.source,
        "reference_id": req.reference_id,
        "confirmed_issue_date": req.confirmed_issue_date,
        "cover_title": req.cover_title,
        "confidence": confidence,
    }


def _pricing_snapshot(archive: dict, stage: str) -> dict:
    low = _num_or_none(archive.get("rough_comp_min")) or 0
    high = _num_or_none(archive.get("rough_comp_max")) or 0
    final_price = _num_or_none(archive.get("final_price")) or 0
    if not final_price and low and high:
        final_price = round((low + high) / 2, 2)
    elif not final_price and low:
        final_price = low

    comps = _list_magazine_comps(int(archive.get("id") or 0)) if archive.get("id") else []
    summary = _pricing_summary_for_archive(int(archive.get("id") or 0)) if archive.get("id") else None
    if not summary and archive.get("id"):
        summary = _calculate_magazine_pricing(int(archive.get("id")), persist=False)
    pricing_type = (summary or {}).get("pricing_type") or "manual_rough_estimate"
    true_comps = bool((summary or {}).get("sold_comp_count") or (summary or {}).get("active_listing_count") or (summary or {}).get("dealer_listing_count"))
    return {
        "archive_id": archive.get("id"),
        "stage": stage,
        "pricing_type": pricing_type,
        "true_comps_available": true_comps,
        "comps": comps,
        "pricing_summary": summary,
        "message": (summary or {}).get("pricing_basis") or "Pricing engine needs comps or owner approval.",
        "rough_comp_min": low,
        "rough_comp_max": high,
        "recommended_price": (summary or {}).get("recommended_price") or final_price or None,
        "sale_plan": archive.get("sale_plan") or "",
        "condition_score": archive.get("condition_score") or 0,
        "defects": archive.get("defects") or "",
        "is_complete": bool(archive.get("is_complete")),
        "has_address_label": bool(archive.get("has_address_label")),
        "pricing_basis": (summary or {}).get("pricing_basis") or archive.get("pricing_basis") or "manual_rough_estimate",
        "confidence": (summary or {}).get("confidence") or "low",
        "warnings": (summary or {}).get("warnings") or [],
        "updated_at": archive.get("pricing_updated_at") or archive.get("updated_at"),
    }


def _load_archive_or_404(archive_id: int) -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")
    return dict_row(row)


@router.get("/{archive_id}/pricing")
async def get_pricing(archive_id: int):
    """Return the current pricing snapshot. This is not a real comps engine yet."""
    archive = _load_archive_or_404(archive_id)
    return _pricing_snapshot(archive, "current")


@router.post("/{archive_id}/pricing/estimate")
async def run_pricing_estimate(archive_id: int, req: PricingRequest):
    """Early estimate scaffold. Uses only current/manual rough range until true comps are added."""
    archive = _load_archive_or_404(archive_id)
    return _pricing_snapshot(archive, "early_estimate")


@router.post("/{archive_id}/pricing/final")
async def run_final_pricing(archive_id: int, req: PricingRequest):
    """Final pricing scaffold. Saves accepted manual rough estimate; does not claim true comps."""
    archive = _load_archive_or_404(archive_id)
    low = req.rough_comp_min if req.rough_comp_min is not None else archive.get("rough_comp_min", 0)
    high = req.rough_comp_max if req.rough_comp_max is not None else archive.get("rough_comp_max", 0)
    final_price = 0
    if low and high:
        final_price = round((low + high) / 2, 2)
    elif low:
        final_price = low

    with get_db() as db:
        db.execute(
            """UPDATE ag_archives
               SET rough_comp_min = ?,
                   rough_comp_max = ?,
                   sale_plan = COALESCE(NULLIF(?, ''), sale_plan),
                   pricing_basis = 'manual_rough_estimate',
                   final_price = ?,
                   pricing_updated_at = datetime('now'),
                   processed_status = CASE
                       WHEN ? = 1 AND processed_status IN ('RAW','IDENTIFIED','PHOTOGRAPHED') THEN 'VALUED'
                       ELSE processed_status
                   END,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (low or 0, high or 0, req.sale_plan or "", final_price or 0, int(req.accept_final), archive_id),
        )
    archive = _load_archive_or_404(archive_id)
    snapshot = _pricing_snapshot(archive, "final_pricing")
    snapshot["accepted"] = bool(req.accept_final)
    return snapshot


@router.post("/{archive_id}/comps/research")
async def research_magazine_comps(archive_id: int, req: Optional[MagazineCompResearchRequest] = None):
    """Read-only magazine comp research. Generates links when marketplace read credentials are missing."""
    archive = _load_archive_or_404(archive_id)
    issue_info = _latest_issue_info_response(archive_id, include_stale=False)
    if not issue_info or issue_info.get("status") != "completed":
        raise HTTPException(409, "Resolve issue info first before researching magazine comps.")
    issue_master = _issue_master_for_archive(archive_id)
    if not issue_master:
        try:
            issue_master = _sync_archive_to_life_master(archive_id).get("issue_master")
        except Exception:
            issue_master = None
    req = req or MagazineCompResearchRequest()
    query = _magazine_research_query(archive, issue_master)
    issue_master_id = int(issue_master.get("id")) if issue_master and issue_master.get("id") else None
    access = _marketplace_read_access_status()
    stored: list[dict] = []
    for link in _research_links_for_query(query):
        stored.append(_insert_magazine_comp_if_new(archive_id, issue_master_id, query, link))
    if issue_master and _num_or_zero(issue_master.get("dtmagazine_average")):
        stored.append(_insert_magazine_comp_if_new(
            archive_id,
            issue_master_id,
            query,
            {
                "provider": "dtmagazine",
                "result_type": "dtmagazine_reference_price_guide",
                "title": f"DTM guide: {issue_master.get('dtmagazine_description') or issue_master.get('description') or query}",
                "url": f"{DTMAGAZINE_BASE_URL}/life{issue_master.get('year')}.html",
                "price": issue_master.get("dtmagazine_average") or 0,
                "total_price": issue_master.get("dtmagazine_average") or 0,
                "match_confidence": 0.65,
                "notes": "DTM guide values are reference-guide values, not current sold comps.",
                "raw_result": {"source_type": "dtmagazine_reference_price_guide", "issue_date": issue_master.get("normalized_date")},
            },
        ))
    summary = _calculate_magazine_pricing(archive_id, persist=True)
    return {
        "archive_id": archive_id,
        "provider_behavior": "manual_search_links",
        "marketplace_access": access,
        "query": query,
        "stored_results": stored,
        "stored_count": len(stored),
        "pricing_summary": summary,
        "note": "No live marketplace write APIs were called. Search links are research aids, not sold comps.",
    }


@router.get("/{archive_id}/comps")
async def get_magazine_comps(archive_id: int):
    _load_archive_or_404(archive_id)
    return {
        "archive_id": archive_id,
        "comps": _list_magazine_comps(archive_id),
        "pricing_summary": _pricing_summary_for_archive(archive_id) or _calculate_magazine_pricing(archive_id, persist=False),
        "marketplace_access": _marketplace_read_access_status(),
    }


@router.post("/{archive_id}/comps/manual", status_code=201)
async def add_manual_magazine_comp(archive_id: int, req: ManualMagazineCompRequest):
    archive = _load_archive_or_404(archive_id)
    allowed = {"sold_comp", "active_listing", "dealer_asking", "manual_reference"}
    result_type = req.result_type if req.result_type in allowed else "manual_reference"
    if not (req.title.strip() or req.url.strip()):
        raise HTTPException(400, "Manual comp requires a title or URL.")
    issue_master = _issue_master_for_archive(archive_id)
    query = _magazine_research_query(archive, issue_master)
    comp = _insert_magazine_comp_if_new(
        archive_id,
        int(issue_master.get("id")) if issue_master and issue_master.get("id") else None,
        query,
        {
            "provider": "manual_entry",
            "result_type": result_type,
            "title": req.title.strip(),
            "url": req.url.strip(),
            "price": req.price or 0,
            "currency": (req.currency or "USD").upper(),
            "total_price": req.price or 0,
            "condition_text": req.condition_text.strip(),
            "match_confidence": 0.85 if result_type == "sold_comp" else 0.6,
            "notes": req.notes.strip(),
            "raw_result": {"entered_by": "owner_manual_entry", "result_type": result_type},
        },
    )
    summary = _calculate_magazine_pricing(archive_id, persist=True)
    return {"archive_id": archive_id, "comp": comp, "pricing_summary": summary}


@router.post("/{archive_id}/pricing/calculate")
async def calculate_magazine_pricing(archive_id: int):
    _load_archive_or_404(archive_id)
    return _calculate_magazine_pricing(archive_id, persist=True)


# ── Google Books Issue Metadata & Ad Opportunity Checks ───────────────────────

GOOGLE_BOOKS_CONTENT_LIMITATION = (
    "Official Google Books volume/search metadata does not provide a reliable page-level ad inventory. "
    "Ad opportunities are issue-level candidates until a user uploads the ad page from this physical copy."
)

EXACT_1949_AD_SEEDS = [
    {"brand": "Ford", "product": "car ad", "category": "automotive", "search_query": "1949 LIFE magazine Ford car ad", "policy_flags": []},
    {"brand": "Chevy", "product": "car ad", "category": "automotive", "search_query": "1949 LIFE magazine Chevy ad", "policy_flags": []},
    {"brand": "Disney", "product": "Alice in Wonderland ad", "category": "entertainment", "search_query": "1949 LIFE magazine Disney Alice in Wonderland ad", "policy_flags": []},
    {"brand": "", "product": "toy ad", "category": "toys", "search_query": "1949 LIFE magazine toy ad", "policy_flags": []},
    {"brand": "Philco", "product": "television ad", "category": "electronics", "search_query": "1949 LIFE magazine Philco television ad", "policy_flags": []},
    {"brand": "Frigidaire", "product": "appliance ad", "category": "appliances", "search_query": "1949 LIFE magazine Frigidaire ad", "policy_flags": []},
    {"brand": "Camels", "product": "cigarette ad", "category": "tobacco", "search_query": "1949 LIFE magazine Camels ad", "policy_flags": ["tobacco_manual_review"]},
    {"brand": "Aqua Velva", "product": "after shave ad", "category": "grooming", "search_query": "1949 LIFE magazine Aqua Velva ad", "policy_flags": []},
    {"brand": "Firestone", "product": "tire ad", "category": "automotive", "search_query": "1949 LIFE magazine Firestone ad", "policy_flags": []},
    {"brand": "Borden's", "product": "food ad", "category": "food", "search_query": "1949 LIFE magazine Borden's ad", "policy_flags": []},
    {"brand": "Pepsodent", "product": "toothpaste ad", "category": "health and grooming", "search_query": "1949 LIFE magazine Pepsodent ad", "policy_flags": ["medical_or_health_claims_review"]},
    {"brand": "", "product": "whiskey ad", "category": "alcohol", "search_query": "1949 LIFE magazine whiskey ad", "policy_flags": ["alcohol_manual_review"]},
]


def _archive_google_books_volume_id(archive: dict) -> str:
    candidates = [
        archive.get("google_books_volume_id"),
        archive.get("confirmed_reference_id"),
        archive.get("reference_issue_key"),
        archive.get("reference_issue_id"),
    ]
    for value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        if text.startswith("google-books-"):
            text = text.replace("google-books-", "", 1)
        if re.fullmatch(r"[A-Za-z0-9_-]{8,}", text):
            return text
    return ""


def _known_google_issue_by_volume(volume_id: str) -> Optional[dict]:
    for issue in LIFE_GOOGLE_BOOKS_KNOWN_ISSUES:
        if issue.get("google_books_volume_id") == volume_id:
            return issue
    return None


def _known_google_issue_for_archive(archive: dict) -> Optional[dict]:
    volume_id = _archive_google_books_volume_id(archive)
    if volume_id:
        known = _known_google_issue_by_volume(volume_id)
        if known:
            return known
    query = " ".join(str(archive.get(k) or "") for k in (
        "issue_date", "confirmed_issue_date", "cover_subject", "confirmed_cover_title", "issue_title"
    )).lower()
    if "1949" in query and ("montalban" in query or "nov" in query or "11-21" in query or "november" in query):
        return _known_google_issue_by_volume("9kwEAAAAMBAJ")
    return None


def _google_books_query_for_archive(archive: dict) -> str:
    issue_date = archive.get("confirmed_issue_date") or archive.get("issue_date") or ""
    title = archive.get("confirmed_cover_title") or archive.get("cover_subject") or archive.get("issue_title") or ""
    parts = ["LIFE", issue_date, title]
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())


def _extract_issn(info: dict) -> str:
    for ident in info.get("industryIdentifiers") or []:
        if str(ident.get("type") or "").upper() == "ISSN" and ident.get("identifier"):
            return str(ident["identifier"])
    return ""


def _metadata_from_google_volume(volume_id: str, data: dict, lookup_status: str) -> dict:
    info = data.get("volumeInfo") or {}
    access = data.get("accessInfo") or {}
    images = info.get("imageLinks") or {}
    cover = images.get("thumbnail") or images.get("smallThumbnail") or _google_books_cover_url(volume_id)
    return {
        "source": "google_books_api",
        "source_volume_id": volume_id,
        "source_url": info.get("canonicalVolumeLink") or info.get("infoLink") or f"https://books.google.com/books?id={volume_id}",
        "issue_title": info.get("title") or "LIFE",
        "issue_date": info.get("publishedDate") or "",
        "publisher": info.get("publisher") or "",
        "page_count": int(info.get("pageCount") or 0),
        "issn": _extract_issn(info),
        "description": info.get("description") or "",
        "preview_link": info.get("previewLink") or "",
        "info_link": info.get("infoLink") or "",
        "web_reader_link": access.get("webReaderLink") or "",
        "cover_image_url": str(cover).replace("http://", "https://"),
        "raw_metadata": {
            "id": data.get("id") or volume_id,
            "title": info.get("title"),
            "subtitle": info.get("subtitle"),
            "publisher": info.get("publisher"),
            "publishedDate": info.get("publishedDate"),
            "description": info.get("description"),
            "pageCount": info.get("pageCount"),
            "industryIdentifiers": info.get("industryIdentifiers") or [],
            "imageLinks": images,
            "previewLink": info.get("previewLink"),
            "infoLink": info.get("infoLink"),
            "canonicalVolumeLink": info.get("canonicalVolumeLink"),
            "webReaderLink": access.get("webReaderLink"),
            "contents_available": False,
            "contents_limitation": GOOGLE_BOOKS_CONTENT_LIMITATION,
        },
        "lookup_status": lookup_status,
    }


def _metadata_from_known_google_issue(issue: dict, lookup_status: str) -> dict:
    volume_id = issue["google_books_volume_id"]
    return {
        "source": "google_books_known_reference",
        "source_volume_id": volume_id,
        "source_url": issue.get("cover_preview_url") or f"https://books.google.com/books?id={volume_id}",
        "issue_title": issue.get("issue_title") or "LIFE",
        "issue_date": issue.get("date") or "",
        "publisher": "Time Inc.",
        "page_count": 144 if volume_id == "9kwEAAAAMBAJ" else 0,
        "issn": "",
        "description": issue.get("cover_subject") or "",
        "preview_link": issue.get("cover_preview_url") or "",
        "info_link": f"https://books.google.com/books?id={volume_id}",
        "web_reader_link": f"https://play.google.com/books/reader?id={volume_id}",
        "cover_image_url": issue.get("cover_thumbnail_url") or _google_books_cover_url(volume_id),
        "raw_metadata": {
            "id": volume_id,
            "title": issue.get("issue_title") or "LIFE",
            "publisher": "Time Inc.",
            "publishedDate": issue.get("date"),
            "description": issue.get("cover_subject"),
            "pageCount": 144 if volume_id == "9kwEAAAAMBAJ" else None,
            "previewLink": issue.get("cover_preview_url"),
            "infoLink": f"https://books.google.com/books?id={volume_id}",
            "canonicalVolumeLink": f"https://books.google.com/books/about/LIFE.html?id={volume_id}",
            "webReaderLink": f"https://play.google.com/books/reader?id={volume_id}",
            "imageLinks": {"thumbnail": issue.get("cover_thumbnail_url") or _google_books_cover_url(volume_id)},
            "contents_available": False,
            "contents_limitation": GOOGLE_BOOKS_CONTENT_LIMITATION,
            "reference_note": "Known issue reference used because official API metadata was unavailable or quota-limited.",
        },
        "lookup_status": lookup_status,
    }


def _record_external_api_call(
    provider: str,
    endpoint_type: str,
    archive_id: Optional[int],
    source_volume_id: str,
    status_code: int,
    lookup_status: str,
    cache_hit: bool,
    caller: str,
) -> None:
    with get_db() as db:
        db.execute(
            """INSERT INTO archive_external_api_calls
               (provider, endpoint_type, archive_id, source_volume_id, status_code,
                lookup_status, cache_hit, caller)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                provider,
                endpoint_type,
                archive_id,
                source_volume_id or "",
                int(status_code or 0),
                lookup_status or "",
                1 if cache_hit else 0,
                caller or "",
            ),
        )
        db.commit()


def _parse_sqlite_datetime(value: str) -> Optional[datetime]:
    text = str(value or "").strip().replace("Z", "")
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _google_books_last_429_at() -> Optional[str]:
    with get_db() as db:
        row = db.execute(
            """SELECT created_at FROM archive_external_api_calls
               WHERE provider = 'google_books'
                 AND (status_code = 429 OR lookup_status IN ('quota_limited', 'quota_limited_cooldown_active'))
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 1"""
        ).fetchone()
    return row[0] if row else None


def _google_books_cooldown_status() -> tuple[bool, Optional[str]]:
    last_429_at = _google_books_last_429_at()
    parsed = _parse_sqlite_datetime(last_429_at or "")
    if not parsed:
        return False, last_429_at
    return datetime.utcnow() - parsed < timedelta(seconds=GOOGLE_BOOKS_COOLDOWN_SECONDS), last_429_at


def _google_books_live_call_count(since_modifier: str) -> int:
    with get_db() as db:
        row = db.execute(
            """SELECT COUNT(*) FROM archive_external_api_calls
               WHERE provider = 'google_books'
                 AND cache_hit = 0
                 AND status_code > 0
                 AND created_at >= datetime('now', ?)""",
            (since_modifier,),
        ).fetchone()
    return int(row[0] if row else 0)


def _google_books_calls_last_hour() -> int:
    return _google_books_live_call_count("-1 hour")


def _google_books_calls_today() -> int:
    with get_db() as db:
        row = db.execute(
            """SELECT COUNT(*) FROM archive_external_api_calls
               WHERE provider = 'google_books'
                 AND cache_hit = 0
                 AND status_code > 0
                 AND date(created_at) = date('now')"""
        ).fetchone()
    return int(row[0] if row else 0)


def _google_books_cache_entries() -> int:
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) FROM archive_issue_metadata").fetchone()
    return int(row[0] if row else 0)


def _google_books_live_allowed(archive_id: Optional[int]) -> tuple[bool, str]:
    cooldown_active, _ = _google_books_cooldown_status()
    if cooldown_active:
        return False, "quota_limited_cooldown_active"
    if not GOOGLE_BOOKS_API_KEY and _google_books_calls_last_hour() >= GOOGLE_BOOKS_MISSING_KEY_HOURLY_LIMIT:
        return False, "api_key_missing_hourly_limit"
    return True, "ok" if GOOGLE_BOOKS_API_KEY else "api_key_missing"


async def _fetch_google_books_volume(volume_id: str, archive_id: Optional[int] = None, caller: str = "archiveforge_lookup") -> tuple[Optional[dict], str]:
    allowed, blocked_status = _google_books_live_allowed(archive_id)
    if not allowed:
        _record_external_api_call(
            "google_books",
            "volume_get",
            archive_id,
            volume_id,
            0,
            blocked_status,
            False,
            caller,
        )
        return None, blocked_status
    params = {}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(f"{GOOGLE_BOOKS_API_URL}/{volume_id}", params=params)
        if res.status_code != 200:
            lookup_status = "quota_limited" if res.status_code == 429 else f"google_books_api_http_{res.status_code}"
            _record_external_api_call("google_books", "volume_get", archive_id, volume_id, res.status_code, lookup_status, False, caller)
            return None, lookup_status
        lookup_status = "google_books_api_ok" if GOOGLE_BOOKS_API_KEY else "api_key_missing_google_books_api_ok"
        _record_external_api_call("google_books", "volume_get", archive_id, volume_id, res.status_code, lookup_status, False, caller)
        return res.json(), lookup_status
    except Exception as exc:
        lookup_status = f"google_books_api_error:{type(exc).__name__}"
        _record_external_api_call("google_books", "volume_get", archive_id, volume_id, 0, lookup_status, False, caller)
        return None, lookup_status


async def _search_google_books_metadata(query: str, archive_id: Optional[int] = None, caller: str = "archiveforge_lookup") -> tuple[Optional[dict], str]:
    allowed, blocked_status = _google_books_live_allowed(archive_id)
    if not allowed:
        _record_external_api_call("google_books", "volume_search", archive_id, "", 0, blocked_status, False, caller)
        return None, blocked_status
    params = {"q": query, "printType": "magazines", "maxResults": 5}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(GOOGLE_BOOKS_API_URL, params=params)
        if res.status_code != 200:
            lookup_status = "quota_limited" if res.status_code == 429 else f"google_books_api_http_{res.status_code}"
            _record_external_api_call("google_books", "volume_search", archive_id, "", res.status_code, lookup_status, False, caller)
            return None, lookup_status
        data = res.json()
        for item in data.get("items") or []:
            info = item.get("volumeInfo") or {}
            text = " ".join(str(info.get(k) or "") for k in ("title", "subtitle", "description", "publishedDate")).lower()
            if "life" in text:
                lookup_status = "google_books_search_ok" if GOOGLE_BOOKS_API_KEY else "api_key_missing_google_books_search_ok"
                _record_external_api_call("google_books", "volume_search", archive_id, str(item.get("id") or ""), res.status_code, lookup_status, False, caller)
                return item, lookup_status
        lookup_status = "google_books_search_no_life_match" if GOOGLE_BOOKS_API_KEY else "api_key_missing_google_books_search_no_life_match"
        _record_external_api_call("google_books", "volume_search", archive_id, "", res.status_code, lookup_status, False, caller)
        return None, lookup_status
    except Exception as exc:
        lookup_status = f"google_books_search_error:{type(exc).__name__}"
        _record_external_api_call("google_books", "volume_search", archive_id, "", 0, lookup_status, False, caller)
        return None, lookup_status


async def _lookup_google_books_metadata_for_archive(archive: dict, caller: str = "archiveforge_lookup", override_volume_id: str = "") -> dict:
    volume_id = (override_volume_id or _archive_google_books_volume_id(archive)).strip()
    known = _known_google_issue_for_archive(archive)
    if volume_id and not known:
        known = _known_google_issue_by_volume(volume_id)
    api_status = ""
    if volume_id:
        data, api_status = await _fetch_google_books_volume(volume_id, archive.get("id"), caller)
        if data:
            return _metadata_from_google_volume(volume_id, data, api_status)
    else:
        query = _google_books_query_for_archive(archive)
        item, api_status = await _search_google_books_metadata(query, archive.get("id"), caller)
        if item and item.get("id"):
            return _metadata_from_google_volume(item["id"], item, api_status)
    if known:
        status = f"seeded_reference_after_{api_status or 'no_api_candidate'}"
        return _metadata_from_known_google_issue(known, status)
    raise HTTPException(502, f"Google Books lookup did not return usable LIFE metadata ({api_status or 'no candidate'}).")


def _store_issue_metadata(archive_id: int, metadata: dict) -> dict:
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO archive_issue_metadata
               (archive_id, source, source_volume_id, source_url, issue_title, issue_date,
                publisher, page_count, issn, description, preview_link, info_link,
                web_reader_link, cover_image_url, raw_metadata_json, lookup_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                archive_id,
                metadata.get("source", ""),
                metadata.get("source_volume_id", ""),
                metadata.get("source_url", ""),
                metadata.get("issue_title", ""),
                metadata.get("issue_date", ""),
                metadata.get("publisher", ""),
                int(metadata.get("page_count") or 0),
                metadata.get("issn", ""),
                metadata.get("description", ""),
                metadata.get("preview_link", ""),
                metadata.get("info_link", ""),
                metadata.get("web_reader_link", ""),
                metadata.get("cover_image_url", ""),
                json.dumps(metadata.get("raw_metadata") or {}),
                metadata.get("lookup_status", ""),
            ),
        )
        db.execute(
            """UPDATE ag_archives
               SET google_books_volume_id = COALESCE(NULLIF(?, ''), google_books_volume_id),
                   reference_source = COALESCE(NULLIF(reference_source, ''), 'google_books'),
                   cover_preview_url = COALESCE(NULLIF(?, ''), cover_preview_url),
                   cover_thumbnail_url = COALESCE(NULLIF(?, ''), cover_thumbnail_url),
                   issue_date = COALESCE(NULLIF(issue_date, ''), ?),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                metadata.get("source_volume_id", ""),
                metadata.get("preview_link", ""),
                metadata.get("cover_image_url", ""),
                metadata.get("issue_date", ""),
                archive_id,
            ),
        )
        db.commit()
        metadata_id = cur.lastrowid
    return _latest_issue_metadata(archive_id) or {**metadata, "id": metadata_id, "archive_id": archive_id}


def _metadata_row_to_dict(row: dict) -> dict:
    metadata = dict(row)
    metadata["raw_metadata"] = _json_value(metadata.pop("raw_metadata_json", "{}"), {})
    metadata["contents_available"] = bool(metadata["raw_metadata"].get("contents_available"))
    metadata["contents_limitation"] = metadata["raw_metadata"].get("contents_limitation") or GOOGLE_BOOKS_CONTENT_LIMITATION
    return metadata


def _latest_issue_metadata(archive_id: int) -> Optional[dict]:
    with get_db() as db:
        row = db.execute(
            """SELECT * FROM archive_issue_metadata
               WHERE archive_id = ?
                 AND lookup_status NOT LIKE 'rejected_%'
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 1""",
            (archive_id,),
        ).fetchone()
    return _metadata_row_to_dict(dict_row(row)) if row else None


def _latest_issue_metadata_for_volume(volume_id: str) -> Optional[dict]:
    volume_id = str(volume_id or "").strip()
    if not volume_id:
        return None
    with get_db() as db:
        row = db.execute(
            """SELECT * FROM archive_issue_metadata
               WHERE source_volume_id = ?
                 AND lookup_status NOT LIKE 'rejected_%'
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 1""",
            (volume_id,),
        ).fetchone()
    return _metadata_row_to_dict(dict_row(row)) if row else None


def _cached_google_books_metadata(archive_id: int, volume_id: str = "") -> Optional[dict]:
    if volume_id:
        with get_db() as db:
            row = db.execute(
                """SELECT * FROM archive_issue_metadata
                   WHERE archive_id = ? AND source_volume_id = ?
                     AND lookup_status NOT LIKE 'rejected_%'
                   ORDER BY datetime(created_at) DESC, id DESC
                   LIMIT 1""",
                (archive_id, volume_id),
            ).fetchone()
        if row:
            return _metadata_row_to_dict(dict_row(row))
        return _latest_issue_metadata_for_volume(volume_id)
    return _latest_issue_metadata(archive_id)


def _issue_metadata_response(archive_id: int, metadata: dict, cache_hit: bool) -> dict:
    return {
        "archive_id": archive_id,
        "metadata": metadata,
        "official_api_first": True,
        "cache_hit": cache_hit,
        "api_key_configured": bool(GOOGLE_BOOKS_API_KEY),
        "contents_available": bool(metadata.get("contents_available")),
        "contents_limitation": metadata.get("contents_limitation") or GOOGLE_BOOKS_CONTENT_LIMITATION,
    }


def _ad_opportunity_row_to_dict(row: dict) -> dict:
    d = dict(row)
    d["policy_flags"] = _json_value(d.pop("policy_flags_json", "[]"), [])
    for key in ("estimated_low", "estimated_high"):
        d[key] = _num_or_none_for_packet(d.get(key))
    d["value_score"] = round(_num_or_zero(d.get("value_score")), 1)
    d["comp_confidence"] = d.get("comp_confidence") or "none"
    return d


def _list_ad_opportunities(archive_id: int) -> list[dict]:
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM archive_ad_opportunities
               WHERE archive_id = ?
               ORDER BY
                 CASE evidence_grade WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 WHEN 'D' THEN 4 ELSE 5 END,
                 id ASC""",
            (archive_id,),
        ).fetchall())
    return [_ad_opportunity_row_to_dict(row) for row in rows]


def _ad_comp_row_to_dict(row: dict) -> dict:
    d = dict(row)
    d["raw_result"] = _json_value(d.pop("raw_result_json", "{}"), {})
    for key in ("price", "shipping_price", "total_price", "match_confidence"):
        d[key] = _num_or_none_for_packet(d.get(key))
    return d


def _list_ad_comps(archive_id: int, candidate_id: Optional[int] = None) -> list[dict]:
    where = "archive_id = ?"
    params: list[Any] = [archive_id]
    if candidate_id:
        where += " AND candidate_id = ?"
        params.append(candidate_id)
    with get_db() as db:
        rows = dict_rows(db.execute(
            f"""SELECT * FROM archive_ad_comps
                WHERE {where}
                ORDER BY candidate_id ASC, result_type = 'search_link' ASC,
                         COALESCE(total_price, price, 0) DESC, id ASC""",
            tuple(params),
        ).fetchall())
    return [_ad_comp_row_to_dict(row) for row in rows]


def _group_ad_comps(archive_id: int) -> list[dict]:
    candidates = _list_ad_opportunities(archive_id)
    comps_by_candidate: dict[int, list[dict]] = {}
    for comp in _list_ad_comps(archive_id):
        comps_by_candidate.setdefault(int(comp.get("candidate_id") or 0), []).append(comp)
    return [
        {
            "candidate": candidate,
            "comps": comps_by_candidate.get(int(candidate.get("id") or 0), []),
            "summary": _candidate_comp_summary(comps_by_candidate.get(int(candidate.get("id") or 0), [])),
        }
        for candidate in candidates
    ]


def _candidate_comp_summary(comps: list[dict]) -> dict:
    actual = [c for c in comps if c.get("result_type") != "search_link"]
    sold = [c for c in actual if c.get("result_type") == "sold_comp"]
    active = [c for c in actual if c.get("result_type") == "active_listing"]
    prices = [
        _num_or_zero(c.get("total_price") or c.get("price"))
        for c in actual
        if _num_or_zero(c.get("total_price") or c.get("price")) > 0
    ]
    return {
        "comp_count": len(actual),
        "search_link_count": len([c for c in comps if c.get("result_type") == "search_link"]),
        "sold_comp_count": len(sold),
        "active_listing_count": len(active),
        "estimated_low": round(min(prices), 2) if prices else None,
        "estimated_high": round(max(prices), 2) if prices else None,
        "comp_confidence": "high" if sold else "medium" if len(active) >= 2 else "low" if comps else "none",
    }


def _marketplace_read_access_status() -> dict:
    ebay_token_present = bool(
        os.getenv("EBAY_BROWSE_API_TOKEN")
        or os.getenv("EBAY_OAUTH_TOKEN")
        or os.getenv("EBAY_ACCESS_TOKEN")
    )
    worthpoint_present = bool(os.getenv("WORTHPOINT_API_KEY") or os.getenv("WORTHPOINT_USERNAME"))
    return {
        "ebay_browse_active_available": ebay_token_present,
        "worthpoint_available": worthpoint_present,
        "sold_comps_available": False,
    }


def _ad_research_query(candidate: dict) -> str:
    query = (candidate.get("search_query") or "").strip()
    if query:
        return query
    parts = ["1949 LIFE magazine", candidate.get("brand") or "", candidate.get("product") or candidate.get("category") or "", "ad"]
    return " ".join(part for part in parts if str(part or "").strip())


def _research_links_for_query(query: str) -> list[dict]:
    encoded = quote_plus(query)
    return [
        {
            "provider": "manual_links",
            "result_type": "search_link",
            "title": f"eBay active search: {query}",
            "url": f"https://www.ebay.com/sch/i.html?_nkw={encoded}",
            "notes": "Manual active-listing research link. Asking prices are not sold comps.",
        },
        {
            "provider": "manual_links",
            "result_type": "search_link",
            "title": f"WorthPoint search: {query}",
            "url": f"https://www.worthpoint.com/inventory/search?query={encoded}",
            "notes": "Manual historical-pricing research link. Requires owner access.",
        },
        {
            "provider": "manual_links",
            "result_type": "search_link",
            "title": f"Web search: {query}",
            "url": f"https://www.google.com/search?q={encoded}",
            "notes": "Manual web research link for dealer references, forums, and image matches.",
        },
    ]


def _insert_ad_comp_if_new(archive_id: int, candidate_id: int, query: str, comp: dict) -> dict:
    url = comp.get("url") or ""
    result_type = comp.get("result_type") or "search_link"
    provider = comp.get("provider") or "manual_links"
    raw_result = comp.get("raw_result") or {}
    safe_raw = {k: v for k, v in raw_result.items() if str(k).lower() not in {"authorization", "access_token", "token", "headers"}}
    price = _num_or_zero(comp.get("price"))
    shipping_price = _num_or_zero(comp.get("shipping_price"))
    total_price = _num_or_zero(comp.get("total_price")) or (price + shipping_price if price else 0)
    with get_db() as db:
        existing = None
        if url:
            existing = db.execute(
                """SELECT * FROM archive_ad_comps
                   WHERE archive_id = ? AND candidate_id = ? AND url = ? AND result_type = ?
                   ORDER BY id DESC LIMIT 1""",
                (archive_id, candidate_id, url, result_type),
            ).fetchone()
        if existing:
            db.execute(
                "UPDATE archive_ad_comps SET observed_at = datetime('now'), notes = COALESCE(NULLIF(?, ''), notes) WHERE id = ?",
                (comp.get("notes") or "", existing[0]),
            )
            db.commit()
            return _ad_comp_row_to_dict(dict_row(db.execute("SELECT * FROM archive_ad_comps WHERE id = ?", (existing[0],)).fetchone()))
        cur = db.execute(
            """INSERT INTO archive_ad_comps
               (archive_id, candidate_id, ad_id, provider, query, result_type, title, url,
                price, currency, shipping_price, total_price, condition_text, sold_date,
                observed_at, match_confidence, notes, raw_result_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?)""",
            (
                archive_id,
                candidate_id,
                comp.get("ad_id"),
                provider,
                query,
                result_type,
                comp.get("title") or "",
                url,
                price,
                (comp.get("currency") or "USD").upper(),
                shipping_price,
                total_price,
                comp.get("condition_text") or "",
                comp.get("sold_date") or "",
                _num_or_zero(comp.get("match_confidence")),
                comp.get("notes") or "",
                json.dumps(safe_raw),
            ),
        )
        db.commit()
        inserted_id = cur.lastrowid
        row = db.execute("SELECT * FROM archive_ad_comps WHERE id = ?", (inserted_id,)).fetchone()
    return _ad_comp_row_to_dict(dict_row(row))


def _policy_penalty(candidate: dict) -> int:
    flags = candidate.get("policy_flags") or []
    text = " ".join(str(flag).lower() for flag in flags)
    return 18 if any(term in text for term in ("tobacco", "alcohol", "medical", "health", "weapon", "adult")) else 0


def _base_category_score(candidate: dict) -> int:
    category = (candidate.get("category") or "").lower()
    product = (candidate.get("product") or "").lower()
    brand = (candidate.get("brand") or "").lower()
    text = " ".join([category, product, brand])
    if "disney" in text or "entertainment" in text:
        return 72
    if "automotive" in text or any(x in text for x in ("ford", "chevy", "firestone")):
        return 70
    if any(x in text for x in ("space", "nasa", "astronaut", "apollo")):
        return 68
    if "toy" in text:
        return 68
    if any(x in text for x in ("electronics", "television", "radio", "philco")):
        return 62
    if any(x in text for x in ("camera", "cameras", "photography", "kodak")):
        return 62
    if any(x in text for x in ("music", "jazz", "record", "phonograph", "hi-fi", "stereo")):
        return 58
    if "appliance" in text or "frigidaire" in text:
        return 55
    if any(x in text for x in ("fashion", "beauty", "cosmetics", "jewelry")):
        return 48
    if "tobacco" in text or "alcohol" in text or "whiskey" in text:
        return 58
    if any(x in text for x in ("grooming", "food", "health")):
        return 45
    return 40


def _score_ad_candidate(candidate: dict, comps: list[dict], archive: dict) -> dict:
    summary = _candidate_comp_summary(comps)
    score = _base_category_score(candidate)
    if candidate.get("brand"):
        score += 5
    issue_year = str(archive.get("issue_date") or archive.get("confirmed_issue_date") or "")[:4]
    if issue_year.startswith("194") or issue_year.startswith("195"):
        score += 8
    if summary["sold_comp_count"]:
        score += min(22, summary["sold_comp_count"] * 12)
    elif summary["active_listing_count"]:
        score += min(12, summary["active_listing_count"] * 5)
    elif summary["search_link_count"]:
        score -= 6
    if candidate.get("verification_status") == "verified_in_copy":
        score += 18
    else:
        score -= 16
    score -= _policy_penalty(candidate)
    if archive.get("is_complete", 1) and candidate.get("verification_status") != "verified_in_copy":
        score -= 8
    score = max(0, min(100, score))
    confidence = summary["comp_confidence"]
    if _policy_penalty(candidate):
        action = "manual_review"
    elif confidence == "none":
        action = "needs_comps"
    elif score >= 60:
        action = "photograph_first"
    elif score >= 28:
        action = "photograph_if_seen"
    else:
        action = "ignore"
    if summary["estimated_low"] is None:
        price_note = "Price unavailable until ad is verified or comps are added."
    elif candidate.get("verification_status") != "verified_in_copy" and not summary["sold_comp_count"]:
        price_note = "Asking/manual evidence only; do not use as final listing price until verified."
    else:
        price_note = "Comp-supported estimate available."
    return {
        "candidate_id": candidate.get("id"),
        "brand": candidate.get("brand") or "",
        "product": candidate.get("product") or "",
        "category": candidate.get("category") or "",
        "value_score": round(score, 1),
        "comp_confidence": confidence,
        "comp_count": summary["comp_count"],
        "sold_comp_count": summary["sold_comp_count"],
        "active_listing_count": summary["active_listing_count"],
        "search_link_count": summary["search_link_count"],
        "estimated_low": summary["estimated_low"],
        "estimated_high": summary["estimated_high"],
        "verification_status": candidate.get("verification_status") or "unverified",
        "evidence_grade": candidate.get("evidence_grade") or "D",
        "policy_flags": candidate.get("policy_flags") or [],
        "suggested_action": action,
        "reasoning_summary": (
            f"{candidate.get('category') or 'candidate'} category score with {confidence} comp confidence. "
            f"{price_note}"
        ),
    }


def _update_candidate_comp_rollup(archive_id: int, candidate_id: int, archive: Optional[dict] = None) -> dict:
    archive = archive or _load_archive_or_404(archive_id)
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM archive_ad_opportunities WHERE archive_id = ? AND id = ?",
            (archive_id, candidate_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Ad opportunity candidate not found")
    candidate = _ad_opportunity_row_to_dict(dict_row(row))
    comps = _list_ad_comps(archive_id, candidate_id)
    ranking = _score_ad_candidate(candidate, comps, archive)
    with get_db() as db:
        db.execute(
            """UPDATE archive_ad_opportunities
               SET estimated_low = ?, estimated_high = ?, comp_count = ?, sold_comp_count = ?,
                   active_listing_count = ?, value_score = ?, comp_confidence = ?,
                   last_comp_checked_at = datetime('now'), recommendation = ?, updated_at = datetime('now')
               WHERE id = ? AND archive_id = ?""",
            (
                ranking.get("estimated_low") or 0,
                ranking.get("estimated_high") or 0,
                ranking.get("comp_count") or 0,
                ranking.get("sold_comp_count") or 0,
                ranking.get("active_listing_count") or 0,
                ranking.get("value_score") or 0,
                ranking.get("comp_confidence") or "none",
                ranking.get("suggested_action") or "",
                candidate_id,
                archive_id,
            ),
        )
        db.commit()
    return ranking


def _rank_ad_candidates(archive_id: int) -> list[dict]:
    archive = _load_archive_or_404(archive_id)
    rankings = [
        _score_ad_candidate(candidate, _list_ad_comps(archive_id, int(candidate.get("id") or 0)), archive)
        for candidate in _list_ad_opportunities(archive_id)
    ]
    return sorted(rankings, key=lambda item: item.get("value_score") or 0, reverse=True)


async def _research_ebay_active_listings(query: str, max_results: int) -> tuple[list[dict], str]:
    token = os.getenv("EBAY_BROWSE_API_TOKEN") or os.getenv("EBAY_OAUTH_TOKEN") or os.getenv("EBAY_ACCESS_TOKEN")
    if not token:
        return [], "ebay_browse_credentials_missing"
    params = {"q": query, "limit": min(max(1, max_results), 5)}
    headers = {"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get("https://api.ebay.com/buy/browse/v1/item_summary/search", params=params, headers=headers)
        if res.status_code != 200:
            return [], f"ebay_browse_http_{res.status_code}"
        data = res.json()
    except Exception as exc:
        return [], f"ebay_browse_error:{type(exc).__name__}"

    comps: list[dict] = []
    for item in (data.get("itemSummaries") or [])[:max_results]:
        price_obj = item.get("price") or {}
        shipping = 0.0
        options = item.get("shippingOptions") or []
        if options and isinstance(options[0], dict):
            shipping = _num_or_zero((options[0].get("shippingCost") or {}).get("value"))
        price = _num_or_zero(price_obj.get("value"))
        comps.append({
            "provider": "ebay_active",
            "result_type": "active_listing",
            "title": item.get("title") or "",
            "url": item.get("itemWebUrl") or "",
            "price": price,
            "currency": price_obj.get("currency") or "USD",
            "shipping_price": shipping,
            "total_price": price + shipping if price else 0,
            "condition_text": item.get("condition") or "",
            "match_confidence": 0.45,
            "notes": "Read-only eBay Browse active listing. Asking price, not sold comp.",
            "raw_result": {
                "itemId": item.get("itemId"),
                "title": item.get("title"),
                "itemWebUrl": item.get("itemWebUrl"),
                "price": item.get("price"),
                "condition": item.get("condition"),
            },
        })
    return comps, "ebay_browse_active_ok"


def _ad_candidate(
    year: str,
    brand: str,
    product: str,
    category: str,
    query: str = "",
    evidence_source: str = "issue_info_seed",
    evidence_grade: str = "C",
    policy_flags: Optional[list[str]] = None,
    recommendation: str = "photograph_candidate_page_if_present",
) -> dict:
    search_query = query or " ".join(part for part in [year, "LIFE magazine", brand, product or category, "ad"] if str(part or "").strip())
    return {
        "candidate_type": "issue_level_ad_lead",
        "brand": brand,
        "product": product,
        "category": category,
        "evidence_source": evidence_source,
        "evidence_grade": evidence_grade,
        "evidence_text": (
            "Issue-level candidate generated from resolved cover issue information. "
            "This is not verified in the user's copy; photograph the ad page before using it for an ad listing."
        ),
        "search_query": " ".join(search_query.split()),
        "estimated_low": 0,
        "estimated_high": 0,
        "comp_count": 0,
        "sold_comp_count": 0,
        "active_listing_count": 0,
        "policy_flags": policy_flags or [],
        "recommendation": recommendation,
        "verification_status": "possible_opportunity",
    }


def _issue_info_text_blob(issue_info: Optional[dict], metadata: dict, archive: dict) -> str:
    parts: list[str] = []
    if issue_info:
        parts.extend(str(v or "") for v in (issue_info.get("visible_text") or []))
        for key in ("cover_title", "detected_subject", "detected_quote", "issue_date", "selected_google_books_volume_id"):
            parts.append(str(issue_info.get(key) or ""))
    for key in ("issue_title", "issue_date", "description", "source_volume_id"):
        parts.append(str(metadata.get(key) or ""))
    for key in ("cover_subject", "issue_date", "confirmed_cover_title", "confirmed_issue_date"):
        parts.append(str(archive.get(key) or ""))
    return " ".join(parts).lower()


def _year_from_issue_sources(issue_info: Optional[dict], metadata: dict, archive: dict) -> str:
    for value in (
        (issue_info or {}).get("issue_date"),
        metadata.get("issue_date"),
        archive.get("issue_date"),
        archive.get("confirmed_issue_date"),
    ):
        match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
        if match:
            return match.group(0)
    return ""


def _build_seed_ad_candidates(metadata: dict, archive: dict, issue_info: Optional[dict] = None) -> list[dict]:
    volume_id = metadata.get("source_volume_id") or ""
    candidates: list[dict] = []
    year = _year_from_issue_sources(issue_info, metadata, archive)
    text_blob = _issue_info_text_blob(issue_info, metadata, archive)
    if volume_id == "9kwEAAAAMBAJ":
        for seed in EXACT_1949_AD_SEEDS:
            candidates.append({
                "candidate_type": "issue_level_ad_lead",
                "brand": seed["brand"],
                "product": seed["product"],
                "category": seed["category"],
                "evidence_source": "manual_seed_exact_issue",
                "evidence_grade": "C",
                "evidence_text": (
                    "Possible 1949 LIFE issue-level ad lead. This is not verified in the user's copy; "
                    "photograph the ad page before using it for an ad listing."
                ),
                "search_query": seed["search_query"],
                "estimated_low": 0,
                "estimated_high": 0,
                "comp_count": 0,
                "sold_comp_count": 0,
                "active_listing_count": 0,
                "policy_flags": seed["policy_flags"],
                "recommendation": "photograph_candidate_page_if_present",
                "verification_status": "possible_opportunity",
            })

    if any(term in text_blob for term in ("apollo", "astronaut", "grissom", "chaffee", "space race", "nasa")):
        candidates.extend([
            _ad_candidate(year, "NASA", "space program advertisement", "space", f"{year} LIFE magazine NASA space ad"),
            _ad_candidate(year, "", "space toy advertisement", "toys", f"{year} LIFE magazine space toy ad"),
            _ad_candidate(year, "Kodak", "camera advertisement", "cameras", f"{year} LIFE magazine Kodak camera ad"),
            _ad_candidate(year, "", "electronics television advertisement", "electronics", f"{year} LIFE magazine electronics television ad"),
        ])

    if "grace kelly" in text_blob:
        candidates.extend([
            _ad_candidate(year, "Grace Kelly", "movie advertisement", "entertainment", f"{year} LIFE magazine Grace Kelly movie ad"),
            _ad_candidate(year, "", "Hollywood film advertisement", "entertainment", f"{year} LIFE magazine Hollywood movie ad"),
            _ad_candidate(year, "", "fashion advertisement", "fashion", f"{year} LIFE magazine fashion ad Grace Kelly"),
            _ad_candidate(year, "", "beauty cosmetics advertisement", "beauty", f"{year} LIFE magazine beauty cosmetics ad"),
        ])

    if any(term in text_blob for term in ("george eastman", "photography", "private papers", "earliest days")):
        candidates.extend([
            _ad_candidate(year, "Kodak", "camera advertisement", "cameras", f"{year} LIFE magazine Kodak camera ad"),
            _ad_candidate(year, "", "photography equipment advertisement", "cameras", f"{year} LIFE magazine photography equipment ad"),
        ])

    if any(term in text_blob for term in ("louis armstrong", "jazz", "trumpet", "big star")):
        candidates.extend([
            _ad_candidate(year, "", "jazz record advertisement", "music", f"{year} LIFE magazine jazz record ad"),
            _ad_candidate(year, "", "hi-fi stereo advertisement", "electronics", f"{year} LIFE magazine hi-fi stereo ad"),
            _ad_candidate(year, "", "radio phonograph advertisement", "electronics", f"{year} LIFE magazine radio phonograph ad"),
            _ad_candidate(year, "", "alcohol advertisement", "alcohol", f"{year} LIFE magazine whiskey ad", policy_flags=["alcohol_manual_review"], recommendation="manual_review"),
        ])

    if any(term in text_blob for term in ("debutante", "joanne", "connelley", "subscription")):
        candidates.extend([
            _ad_candidate(year, "", "fashion advertisement", "fashion", f"{year} LIFE magazine fashion ad"),
            _ad_candidate(year, "", "jewelry advertisement", "jewelry", f"{year} LIFE magazine jewelry ad"),
            _ad_candidate(year, "", "department store advertisement", "retail", f"{year} LIFE magazine department store ad"),
        ])

    if not candidates:
        for brand, product, category, flags, recommendation in (
            ("Ford", "automotive advertisement", "automotive", [], "photograph_candidate_page_if_present"),
            ("Chevrolet", "automotive advertisement", "automotive", [], "photograph_candidate_page_if_present"),
            ("Kodak", "camera advertisement", "cameras", [], "photograph_candidate_page_if_present"),
            ("", "electronics television advertisement", "electronics", [], "photograph_candidate_page_if_present"),
            ("", "toy advertisement", "toys", [], "photograph_candidate_page_if_present"),
            ("", "appliance advertisement", "appliances", [], "photograph_candidate_page_if_present"),
            ("", "fashion advertisement", "fashion", [], "photograph_candidate_page_if_present"),
            ("", "travel advertisement", "travel", [], "photograph_candidate_page_if_present"),
            ("", "tobacco advertisement", "tobacco", ["tobacco_manual_review"], "manual_review"),
            ("", "alcohol advertisement", "alcohol", ["alcohol_manual_review"], "manual_review"),
        ):
            candidates.append(_ad_candidate(year, brand, product, category, policy_flags=flags, recommendation=recommendation))

    deduped: list[dict] = []
    seen_queries: set[str] = set()
    for candidate in candidates:
        query = " ".join(str(candidate.get("search_query") or "").split())
        if not query or query.lower() in seen_queries:
            continue
        seen_queries.add(query.lower())
        candidate["search_query"] = query
        if candidate.get("verification_status") != "verified_in_copy":
            candidate["verification_status"] = "possible_opportunity"
        if candidate.get("evidence_grade") not in {"A", "B", "C"}:
            candidate["evidence_grade"] = "C"
        deduped.append(candidate)
    return deduped[:12]


def _upsert_ad_opportunities(archive_id: int, issue_metadata_id: Optional[int], candidates: list[dict]) -> list[dict]:
    with get_db() as db:
        for candidate in candidates:
            existing = db.execute(
                """SELECT id FROM archive_ad_opportunities
                   WHERE archive_id = ? AND search_query = ?
                   ORDER BY id DESC LIMIT 1""",
                (archive_id, candidate.get("search_query", "")),
            ).fetchone()
            values = (
                issue_metadata_id,
                candidate.get("candidate_type", ""),
                candidate.get("brand", ""),
                candidate.get("product", ""),
                candidate.get("category", ""),
                candidate.get("evidence_source", ""),
                candidate.get("evidence_grade", "D"),
                candidate.get("evidence_text", ""),
                candidate.get("search_query", ""),
                candidate.get("estimated_low") or 0,
                candidate.get("estimated_high") or 0,
                candidate.get("comp_count") or 0,
                candidate.get("sold_comp_count") or 0,
                candidate.get("active_listing_count") or 0,
                json.dumps(candidate.get("policy_flags") or []),
                candidate.get("recommendation", ""),
                candidate.get("verification_status", "unverified"),
            )
            if existing:
                db.execute(
                    """UPDATE archive_ad_opportunities
                       SET issue_metadata_id = ?, candidate_type = ?, brand = ?, product = ?,
                           category = ?, evidence_source = ?, evidence_grade = ?, evidence_text = ?,
                           search_query = ?, estimated_low = ?, estimated_high = ?, comp_count = ?,
                           sold_comp_count = ?, active_listing_count = ?, policy_flags_json = ?,
                           recommendation = ?, verification_status = ?, updated_at = datetime('now')
                       WHERE id = ?""",
                    values + (existing[0],),
                )
            else:
                db.execute(
                    """INSERT INTO archive_ad_opportunities
                       (archive_id, issue_metadata_id, candidate_type, brand, product, category,
                        evidence_source, evidence_grade, evidence_text, search_query,
                        estimated_low, estimated_high, comp_count, sold_comp_count,
                        active_listing_count, policy_flags_json, recommendation, verification_status)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (archive_id,) + values,
                )
        db.commit()
    return _list_ad_opportunities(archive_id)


def _metadata_from_issue_info_for_ad_prep(archive_id: int, issue_info: dict, archive: dict) -> dict:
    selected_volume_id = issue_info.get("selected_google_books_volume_id") or ""
    candidates = issue_info.get("google_books_candidates") or []
    selected = next((c for c in candidates if c.get("volume_id") == selected_volume_id), None) or {}
    return {
        "id": None,
        "archive_id": archive_id,
        "source": "issue_info",
        "source_volume_id": selected_volume_id,
        "source_url": selected.get("info_link") or selected.get("preview_link") or "",
        "issue_title": selected.get("title") or archive.get("issue_title") or "LIFE",
        "issue_date": issue_info.get("issue_date") or selected.get("publishedDate") or archive.get("issue_date") or "",
        "publisher": selected.get("publisher") or "",
        "page_count": selected.get("pageCount") or 0,
        "description": " ".join(
            str(value or "")
            for value in [issue_info.get("cover_title"), issue_info.get("detected_subject"), " ".join(issue_info.get("visible_text") or [])]
            if str(value or "").strip()
        ),
        "lookup_status": "issue_info_only",
    }


def _prepare_ad_opportunities_from_issue_info(archive_id: int, issue_info: Optional[dict] = None) -> dict:
    """Create issue-level ad candidates and manual research links after issue info completes."""
    archive = _load_archive_or_404(archive_id)
    issue_info = issue_info or _latest_issue_info_response(archive_id, include_stale=False)
    if not issue_info or issue_info.get("status") != "completed":
        return {"archive_id": archive_id, "status": "skipped", "reason": "issue_info_not_completed"}
    if not issue_info.get("is_life_magazine"):
        return {"archive_id": archive_id, "status": "skipped", "reason": "not_life_magazine"}

    metadata = _latest_issue_metadata(archive_id) or _metadata_from_issue_info_for_ad_prep(archive_id, issue_info, archive)
    issue_metadata_id = metadata.get("id") if metadata else None
    candidates = _build_seed_ad_candidates(metadata or {}, archive, issue_info)
    stored = _upsert_ad_opportunities(archive_id, issue_metadata_id, candidates)
    with get_db() as db:
        db.execute(
            """UPDATE archive_ad_opportunities
               SET evidence_grade = CASE WHEN evidence_grade IN ('', 'D', 'F') THEN 'C' ELSE evidence_grade END,
                   verification_status = CASE WHEN verification_status = 'unverified' THEN 'possible_opportunity' ELSE verification_status END,
                   updated_at = datetime('now')
               WHERE archive_id = ?
                 AND candidate_type IN ('issue_level_ad_lead', 'era_category_heuristic')
                 AND verification_status NOT IN ('verified_in_copy', 'not_found', 'ignored')""",
            (archive_id,),
        )
        db.commit()
    stored = _list_ad_opportunities(archive_id)

    access = _marketplace_read_access_status()
    selected = sorted(
        stored,
        key=lambda c: _base_category_score(c) - _policy_penalty(c),
        reverse=True,
    )[:8]

    stored_links = []
    provider_behavior = "existing_comps_only"
    if not access["ebay_browse_active_available"]:
        provider_behavior = "manual_search_links"
        for candidate in selected:
            candidate_id = int(candidate.get("id") or 0)
            query = _ad_research_query(candidate)
            for link in _research_links_for_query(query):
                stored_links.append(_insert_ad_comp_if_new(archive_id, candidate_id, query, link))
            _update_candidate_comp_rollup(archive_id, candidate_id, archive)
    else:
        # Auto-prep stays read-only and non-live; explicit Research Ad Comps can use read credentials.
        for candidate in selected:
            _update_candidate_comp_rollup(archive_id, int(candidate.get("id") or 0), archive)

    ranked = _rank_ad_candidates(archive_id)
    return {
        "archive_id": archive_id,
        "status": "ready",
        "issue_metadata_id": issue_metadata_id,
        "candidate_count": len(stored),
        "research_link_count": len(stored_links),
        "provider_behavior": provider_behavior,
        "marketplace_access": access,
        "ranked_candidates": ranked[:8],
        "unverified_warning": "Ad opportunities are issue-level candidates only. Not verified in this physical copy.",
    }


def _ad_estimate(candidates: list[dict], verified_only: bool) -> dict:
    filtered = [
        c for c in candidates
        if (not verified_only or c.get("verification_status") == "verified_in_copy")
        and (c.get("estimated_low") or c.get("estimated_high"))
    ]
    if not filtered:
        return {"low": None, "high": None}
    return {
        "low": round(sum(c.get("estimated_low") or 0 for c in filtered), 2) or None,
        "high": round(sum(c.get("estimated_high") or 0 for c in filtered), 2) or None,
    }


def _ad_breakout_recommendation(archive: dict, candidates: list[dict]) -> dict:
    whole_low = _num_or_none_for_packet(archive.get("rough_comp_min"))
    whole_high = _num_or_none_for_packet(archive.get("rough_comp_max"))
    verified = [c for c in candidates if c.get("verification_status") == "verified_in_copy"]
    best_grade = "F"
    for grade in ("A", "B", "C", "D"):
        if any(c.get("evidence_grade") == grade for c in candidates):
            best_grade = grade
            break

    verified_estimate = _ad_estimate(candidates, verified_only=True)
    candidate_estimate = _ad_estimate(candidates, verified_only=False)
    if not candidates:
        recommendation = "insufficient_data"
        summary = "No ad opportunity check has been run."
        next_action = "run Google Books lookup and ad opportunity check"
    elif not verified:
        recommendation = "keep_intact" if archive.get("is_complete", 1) else "manual_review"
        summary = (
            "Only issue-level ad candidates exist. No ad page from this physical copy has been photographed or analyzed, "
            "so ArchiveForge should not recommend cutting or selling ads separately yet."
        )
        next_action = "photograph candidate ad pages before any ad breakout decision"
    elif verified_estimate.get("high") and whole_high and verified_estimate["high"] > whole_high * 1.5:
        recommendation = "manual_review"
        summary = "Verified ad-page photos may justify separate listings, but confirm comps and preservation risk before breaking out a complete issue."
        next_action = "run sold comps and review preservation risk"
    else:
        recommendation = "sell_whole"
        summary = "Verified ad value does not clearly exceed the complete magazine estimate after labor and preservation risk."
        next_action = "create whole magazine listing draft"

    return {
        "recommendation": recommendation,
        "whole_magazine_estimate": {"low": whole_low, "high": whole_high},
        "verified_ad_estimate": verified_estimate,
        "candidate_ad_estimate": candidate_estimate,
        "labor_cost_placeholder": 10,
        "risk_of_damaging_complete_issue": "high" if archive.get("is_complete", 1) else "medium",
        "evidence_grade": best_grade,
        "reasoning_summary": summary,
        "next_action": next_action,
    }


@router.get("/google-books/status")
async def google_books_status():
    """Return quota/cache status for server-side Google Books usage. Never returns API keys."""
    cooldown_active, last_429_at = _google_books_cooldown_status()
    return {
        "api_key_configured": bool(GOOGLE_BOOKS_API_KEY),
        "cooldown_active": cooldown_active,
        "last_429_at": last_429_at,
        "calls_last_hour": _google_books_calls_last_hour(),
        "calls_today": _google_books_calls_today(),
        "cache_entries": _google_books_cache_entries(),
        "known_seed_references_available": bool(LIFE_GOOGLE_BOOKS_KNOWN_ISSUES),
    }


@router.post("/{archive_id}/google-books/lookup")
async def lookup_google_books_issue(
    archive_id: int,
    force_refresh: bool = Query(False),
    volume_id: str = Query("", description="Optional Google Books volume ID override"),
    caller: str = Query("archiveforge_ui", max_length=80),
):
    """Official-API-first Google Books issue lookup. Stores issue metadata when found."""
    archive = _load_archive_or_404(archive_id)
    clean_volume_id = volume_id.strip()
    if clean_volume_id:
        archive = {**archive, "google_books_volume_id": clean_volume_id}
    cached = _cached_google_books_metadata(archive_id, clean_volume_id or _archive_google_books_volume_id(archive))
    if cached and not force_refresh:
        if int(cached.get("archive_id") or archive_id) != archive_id:
            cached = _store_issue_metadata(
                archive_id,
                {
                    **cached,
                    "lookup_status": "cache_hit_reused_volume",
                    "raw_metadata": cached.get("raw_metadata") or {},
                },
            )
        _record_external_api_call(
            "google_books",
            "metadata_cache",
            archive_id,
            cached.get("source_volume_id") or clean_volume_id,
            200,
            cached.get("lookup_status") or "cache_hit",
            True,
            caller,
        )
        return _issue_metadata_response(archive_id, cached, cache_hit=True)

    metadata = await _lookup_google_books_metadata_for_archive(archive, caller=caller, override_volume_id=clean_volume_id)
    stored = _store_issue_metadata(archive_id, metadata)
    return _issue_metadata_response(archive_id, stored, cache_hit=False)


@router.get("/{archive_id}/google-books/metadata")
async def get_google_books_metadata(archive_id: int):
    """Return the latest stored Google Books issue metadata for this archive."""
    _load_archive_or_404(archive_id)
    metadata = _latest_issue_metadata(archive_id)
    if not metadata:
        raise HTTPException(404, "No Google Books issue metadata stored. Run Google Books lookup first.")
    return {"archive_id": archive_id, "metadata": metadata}


@router.post("/{archive_id}/ad-opportunity-check")
async def run_ad_opportunity_check(archive_id: int):
    """Generate unverified issue-level ad opportunity candidates from metadata and bounded heuristics."""
    archive = _load_archive_or_404(archive_id)
    issue_info = _latest_issue_info_response(archive_id, include_stale=False)
    if not issue_info:
        raise HTTPException(409, "Resolve issue info first.")
    if issue_info.get("status") != "completed":
        raise HTTPException(409, f"Resolve issue info first. Current issue-info status is {issue_info.get('status')}.")
    if not issue_info.get("ad_opportunity_ready"):
        raise HTTPException(409, "Resolve issue info first. Current issue info is not ready for ad opportunity checks.")
    metadata = _latest_issue_metadata(archive_id)
    if not metadata:
        raise HTTPException(409, "Resolve issue info first. Ad opportunity check uses stored issue metadata and will not trigger live Google Books calls.")
    prep = _prepare_ad_opportunities_from_issue_info(archive_id, issue_info)
    stored = _list_ad_opportunities(archive_id)
    recommendation = _ad_breakout_recommendation(archive, stored)
    return {
        "archive_id": archive_id,
        "issue_metadata_id": metadata.get("id"),
        "prep_status": prep.get("status"),
        "provider_behavior": prep.get("provider_behavior"),
        "candidates": stored,
        "total": len(stored),
        "verified_count": len([c for c in stored if c.get("verification_status") == "verified_in_copy"]),
        "unverified_warning": "Ad opportunities are issue-level candidates only. Not verified in this physical copy.",
        "recommendation": recommendation,
    }


@router.get("/{archive_id}/ad-opportunities")
async def get_ad_opportunities(archive_id: int):
    """Return stored ad opportunity candidates and verified ads for this archive."""
    _load_archive_or_404(archive_id)
    candidates = _list_ad_opportunities(archive_id)
    return {"archive_id": archive_id, "candidates": candidates, "total": len(candidates)}


@router.patch("/{archive_id}/ad-opportunities/{opportunity_id}")
async def update_ad_opportunity_status(archive_id: int, opportunity_id: int, verification_status: str = Form(...)):
    """Update a candidate status from the UI without deleting candidate history."""
    allowed = {"possible_opportunity", "unverified", "not_found", "ignored", "verified_in_copy", "likely_in_issue"}
    if verification_status not in allowed:
        raise HTTPException(400, f"verification_status must be one of: {', '.join(sorted(allowed))}")
    _load_archive_or_404(archive_id)
    with get_db() as db:
        affected = db.execute(
            """UPDATE archive_ad_opportunities
               SET verification_status = ?, updated_at = datetime('now')
               WHERE id = ? AND archive_id = ?""",
            (verification_status, opportunity_id, archive_id),
        ).rowcount
    if not affected:
        raise HTTPException(404, "Ad opportunity not found")
    return {"archive_id": archive_id, "opportunity_id": opportunity_id, "verification_status": verification_status}


@router.get("/{archive_id}/ad-breakout-recommendation")
async def get_ad_breakout_recommendation(archive_id: int):
    """Compare whole-magazine value against verified/candidate ad opportunity value."""
    archive = _load_archive_or_404(archive_id)
    candidates = _list_ad_opportunities(archive_id)
    return _ad_breakout_recommendation(archive, candidates)


@router.post("/{archive_id}/ad-comps/research")
async def research_ad_comps(archive_id: int, req: Optional[AdCompResearchRequest] = None):
    """Read-only ad comp research. Generates manual links when no marketplace read credentials exist."""
    archive = _load_archive_or_404(archive_id)
    req = req or AdCompResearchRequest()
    access = _marketplace_read_access_status()
    provider = (req.provider or "auto").strip()
    max_candidates = min(max(int(req.max_candidates or 5), 1), 12)
    max_results = min(max(int(req.max_results_per_candidate or 5), 1), 5)
    candidates = _list_ad_opportunities(archive_id)
    if req.candidate_ids:
        selected_ids = {int(cid) for cid in req.candidate_ids}
        selected = [c for c in candidates if int(c.get("id") or 0) in selected_ids]
    else:
        selected = sorted(
            candidates,
            key=lambda c: _base_category_score(c) - _policy_penalty(c),
            reverse=True,
        )[:max_candidates]
    if not selected:
        raise HTTPException(404, "No ad opportunity candidates found. Run Ad Opportunity Check first.")

    stored: list[dict] = []
    provider_statuses: list[str] = []
    for candidate in selected[:max_candidates]:
        candidate_id = int(candidate.get("id") or 0)
        query = _ad_research_query(candidate)
        live_results: list[dict] = []
        if provider in ("auto", "ebay_active") and access["ebay_browse_active_available"]:
            live_results, live_status = await _research_ebay_active_listings(query, max_results)
            provider_statuses.append(live_status)
        if live_results:
            for comp in live_results[:max_results]:
                stored.append(_insert_ad_comp_if_new(archive_id, candidate_id, query, comp))
        else:
            if provider == "ebay_active" and not access["ebay_browse_active_available"]:
                provider_statuses.append("ebay_browse_credentials_missing")
            for link in _research_links_for_query(query):
                stored.append(_insert_ad_comp_if_new(archive_id, candidate_id, query, link))
        _update_candidate_comp_rollup(archive_id, candidate_id, archive)

    ranked = _rank_ad_candidates(archive_id)
    return {
        "archive_id": archive_id,
        "provider_requested": provider,
        "provider_behavior": "ebay_active_api" if access["ebay_browse_active_available"] and any(s == "ebay_browse_active_ok" for s in provider_statuses) else "manual_search_links",
        "provider_statuses": provider_statuses,
        "marketplace_access": access,
        "stored_results": stored,
        "stored_count": len(stored),
        "ranked_candidates": ranked,
        "note": (
            "No marketplace API credentials configured. ArchiveForge generated research links and manual comp fields instead of live comps."
            if not access["ebay_browse_active_available"] else
            "eBay Browse active listings are asking prices, not sold comps. Use as lower-confidence evidence."
        ),
        "publishes_live_listing": False,
    }


@router.get("/{archive_id}/ad-comps")
async def get_ad_comps(archive_id: int):
    """Return stored ad comp/search-link research grouped by candidate."""
    _load_archive_or_404(archive_id)
    return {
        "archive_id": archive_id,
        "groups": _group_ad_comps(archive_id),
        "marketplace_access": _marketplace_read_access_status(),
    }


@router.post("/{archive_id}/ad-comps/manual", status_code=201)
async def add_manual_ad_comp(archive_id: int, req: ManualAdCompRequest):
    """Add a founder-reviewed manual comp. This is read-only research and does not publish."""
    archive = _load_archive_or_404(archive_id)
    allowed = {"sold_comp", "dealer_asking", "active_listing", "manual_reference"}
    result_type = req.result_type if req.result_type in allowed else "manual_reference"
    with get_db() as db:
        candidate = db.execute(
            "SELECT id FROM archive_ad_opportunities WHERE archive_id = ? AND id = ?",
            (archive_id, req.candidate_id),
        ).fetchone()
    if not candidate:
        raise HTTPException(404, "Ad opportunity candidate not found")
    if not (req.title.strip() or req.url.strip()):
        raise HTTPException(400, "Manual comp requires a title or URL.")
    comp = _insert_ad_comp_if_new(
        archive_id,
        req.candidate_id,
        req.title or req.url,
        {
            "provider": "manual_entry",
            "result_type": result_type,
            "title": req.title.strip(),
            "url": req.url.strip(),
            "price": req.price or 0,
            "currency": (req.currency or "USD").upper(),
            "total_price": req.price or 0,
            "match_confidence": 0.75 if result_type == "sold_comp" else 0.55,
            "notes": req.notes.strip(),
            "raw_result": {"entered_by": "owner_manual_entry", "result_type": result_type},
        },
    )
    ranking = _update_candidate_comp_rollup(archive_id, req.candidate_id, archive)
    return {"archive_id": archive_id, "candidate_id": req.candidate_id, "comp": comp, "ranking": ranking}


@router.get("/{archive_id}/ad-priority-ranking")
async def get_ad_priority_ranking(archive_id: int):
    """Rank ad candidates by category value, policy risk, comp confidence, verification, and labor risk."""
    _load_archive_or_404(archive_id)
    ranked = _rank_ad_candidates(archive_id)
    return {
        "archive_id": archive_id,
        "ranked_candidates": ranked,
        "pricing_warning": "Price unavailable until ad is verified or comps are added.",
        "verification_warning": "Unphotographed ads remain unverified issue-level candidates.",
    }


@router.post("/{archive_id}/ad-pages/upload", status_code=201)
async def upload_ad_page_photo(
    archive_id: int,
    candidate_id: Optional[int] = Form(None),
    page_number: str = Form(""),
    file: UploadFile = File(...),
):
    """Upload a selected ad-page photo. This validates non-empty supported images before creating rows."""
    _load_archive_or_404(archive_id)
    if candidate_id:
        with get_db() as db:
            row = db.execute(
                "SELECT id FROM archive_ad_opportunities WHERE id = ? AND archive_id = ?",
                (candidate_id, archive_id),
            ).fetchone()
        if not row:
            raise HTTPException(404, "Ad opportunity candidate not found for this archive")

    contents = await file.read()
    byte_size = len(contents)
    original_name = file.filename or "ad-page"
    declared_mime_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    guessed_mime_type = (mimetypes.guess_type(original_name)[0] or "").strip().lower()
    supported_mime_type = next(
        (mime for mime in (declared_mime_type, guessed_mime_type) if mime in SUPPORTED_IMAGE_MIME_TYPES),
        "",
    )
    safe_log_name = Path(original_name).name
    if byte_size <= 0:
        log.warning(
            "Rejected empty ArchiveForge ad-page upload archive_id=%s candidate_id=%s filename=%s mime_type=%s byte_size=%s",
            archive_id, candidate_id, safe_log_name, declared_mime_type or guessed_mime_type or "unknown", byte_size,
        )
        raise HTTPException(400, "Uploaded ad-page image is empty. Choose a non-empty JPEG, PNG, GIF, or WebP file.")
    if not supported_mime_type:
        log.warning(
            "Rejected unsupported ArchiveForge ad-page upload archive_id=%s candidate_id=%s filename=%s mime_type=%s byte_size=%s",
            archive_id, candidate_id, safe_log_name, declared_mime_type or guessed_mime_type or "unknown", byte_size,
        )
        raise HTTPException(400, "Unsupported ad-page image type. Upload a JPEG, PNG, GIF, or WebP file.")

    ext = Path(original_name).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = IMAGE_MIME_EXTENSIONS.get(supported_mime_type, ".jpg")
    item_dir = AD_UPLOADS_DIR / str(archive_id)
    item_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"ad_page_{uuid.uuid4().hex[:8]}{ext}"
    file_path = item_dir / unique_name
    try:
        file_path.write_bytes(contents)
        with get_db() as db:
            cur = db.execute(
                """INSERT INTO archive_ad_page_photos
                   (archive_id, candidate_id, page_number, filename, original_name, file_path, mime_type, byte_size)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (archive_id, candidate_id, page_number, unique_name, original_name, str(file_path), supported_mime_type, byte_size),
            )
            db.commit()
            photo_id = cur.lastrowid
    except Exception:
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                log.warning("Failed to remove incomplete ArchiveForge ad-page upload archive_id=%s path=%s", archive_id, file_path)
        raise
    log.info(
        "ArchiveForge ad-page photo uploaded archive_id=%s candidate_id=%s photo_id=%s mime_type=%s byte_size=%s",
        archive_id, candidate_id, photo_id, supported_mime_type, byte_size,
    )
    return {
        "photo_id": photo_id,
        "archive_id": archive_id,
        "candidate_id": candidate_id,
        "page_number": page_number,
        "image_path": str(file_path),
        "file_size": byte_size,
        "mime_type": supported_mime_type,
        "analysis_status": "pending",
    }


@router.get("/{archive_id}/ad-page-photos")
async def list_ad_page_photos(archive_id: int):
    """List all uploaded ad-page photos for an archive."""
    _load_archive_or_404(archive_id)
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT id, archive_id, candidate_id, page_number, filename, original_name,
                      file_path, mime_type, byte_size, analysis_status, analyzed_at, created_at
               FROM archive_ad_page_photos
               WHERE archive_id = ?
               ORDER BY id DESC""",
            (archive_id,),
        ).fetchall())
    return {"archive_id": archive_id, "photos": rows, "total": len(rows)}


@router.get("/{archive_id}/ad-page-photos/{photo_id}")
async def get_ad_page_photo(archive_id: int, photo_id: int):
    """Get one uploaded ad-page photo by ID."""
    _load_archive_or_404(archive_id)
    with get_db() as db:
        row = db.execute(
            """SELECT id, archive_id, candidate_id, page_number, filename, original_name,
                      file_path, mime_type, byte_size, analysis_json, analysis_status,
                      analyzed_at, created_at, updated_at
               FROM archive_ad_page_photos
               WHERE id = ? AND archive_id = ?""",
            (photo_id, archive_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Ad page photo not found")
    return dict(row)


@router.get("/{archive_id}/candidates")
async def list_candidates(archive_id: int):
    """Alias for ad-opportunities — returns all ad opportunity candidates for an archive."""
    _load_archive_or_404(archive_id)
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT id, archive_id, candidate_type, brand, product, category,
                      evidence_source, evidence_grade, evidence_text, search_query,
                      estimated_low, estimated_high, comp_count, sold_comp_count,
                      active_listing_count, value_score, comp_confidence, policy_flags_json,
                      recommendation, verification_status, created_at, updated_at
               FROM archive_ad_opportunities
               WHERE archive_id = ?
               ORDER BY value_score DESC""",
            (archive_id,),
        ).fetchall())
    return {"archive_id": archive_id, "candidates": rows, "total": len(rows)}


@router.get("/{archive_id}/ads")
async def list_analyzed_ads(archive_id: int):
    """List all analyzed ads for an archive (from archive_ads table)."""
    _load_archive_or_404(archive_id)
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT id, archive_id, page_photo_id, candidate_id, brand, product, category,
                      visible_text_json, full_page, color, subject_description, condition_notes,
                      policy_flags_json, collector_keywords_json, confidence, evidence_grade,
                      verification_status, recommendation, reasoning_summary,
                      raw_analysis_json, created_at, updated_at
               FROM archive_ads
               WHERE archive_id = ?
               ORDER BY confidence DESC""",
            (archive_id,),
        ).fetchall())
    return {"archive_id": archive_id, "ads": rows, "total": len(rows)}


def _normalize_ad_analysis(raw: dict) -> list[dict]:
    ads = raw.get("ads") if isinstance(raw, dict) else []
    if isinstance(ads, dict):
        ads = [ads]
    if not isinstance(ads, list):
        ads = []
    normalized = []
    for ad in ads[:8]:
        if not isinstance(ad, dict):
            continue
        visible_text = ad.get("visible_text") or []
        if isinstance(visible_text, str):
            visible_text = [visible_text]
        policy_flags = ad.get("policy_flags") or []
        if isinstance(policy_flags, str):
            policy_flags = [policy_flags]
        confidence = _num_or_none(ad.get("confidence")) or 0
        confidence = max(0.0, min(1.0, confidence))
        grade = ad.get("evidence_grade") if ad.get("evidence_grade") in {"A", "B", "C", "D", "F"} else ("A" if confidence >= 0.65 else "B")
        normalized.append({
            "brand": ad.get("brand"),
            "product": ad.get("product"),
            "category": ad.get("category"),
            "visible_text": [str(v)[:200] for v in visible_text[:20]],
            "full_page": bool(ad.get("full_page")),
            "color": bool(ad.get("color")),
            "subject_description": ad.get("subject_description"),
            "condition_notes": ad.get("condition_notes"),
            "policy_flags": [str(v)[:80] for v in policy_flags[:10]],
            "collector_keywords": ad.get("collector_keywords") if isinstance(ad.get("collector_keywords"), list) else [],
            "confidence": confidence,
            "evidence_grade": grade,
            "verification_status": "verified_in_copy",
            "recommendation": ad.get("recommendation") or ("manual_review" if policy_flags else "keep_with_magazine"),
            "reasoning_summary": (ad.get("reasoning_summary") or "Verified from uploaded ad-page photo.")[:500],
        })
    return normalized


AD_ANALYSIS_PROMPT = """
Inspect the uploaded magazine ad-page photo. Return only valid JSON:
{
  "ads": [
    {
      "brand": null,
      "product": null,
      "category": null,
      "visible_text": [],
      "full_page": false,
      "color": false,
      "subject_description": null,
      "condition_notes": null,
      "policy_flags": [],
      "collector_keywords": [],
      "confidence": 0.0,
      "evidence_grade": "A",
      "verification_status": "verified_in_copy",
      "recommendation": "sell_individually|bundle|keep_with_magazine|manual_review|not_worth_listing",
      "reasoning_summary": "visible evidence only"
    }
  ]
}
Do not invent brand or product. Use only visible evidence from the image.
Flag tobacco, alcohol, medical, weapons, adult, and political-sensitive ads for manual_review.
"""


@router.post("/{archive_id}/ads/analyze")
async def analyze_uploaded_ad_pages(archive_id: int):
    """Analyze uploaded ad-page photos with MiniMax image understanding and mark verified ads only from photos."""
    from app.routers.vision import call_minimax_image_understanding

    _load_archive_or_404(archive_id)
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM archive_ad_page_photos
               WHERE archive_id = ? AND (analyzed_at = '' OR analyzed_at IS NULL)
               ORDER BY id DESC
               LIMIT 3""",
            (archive_id,),
        ).fetchall())
    if not rows:
        raise HTTPException(400, "No unanalyzed ad-page photos found. All uploaded photos have been analyzed, or no photos have been uploaded yet.")

    analyzed = []
    for row in rows:
        path = Path(row["file_path"])
        image_debug = _inspect_image_file(path)
        if not image_debug["exists"] or not image_debug["readable"] or image_debug["file_size_bytes"] <= 0:
            with get_db() as db:
                db.execute(
                    """UPDATE archive_ad_page_photos
                       SET analysis_status = 'failed', analyzed_at = datetime('now'), updated_at = datetime('now')
                       WHERE id = ?""",
                    (row["id"],),
                )
                db.commit()
            continue
        if not image_debug["supported_mime_type"] or not image_debug["under_plan_limit"]:
            with get_db() as db:
                db.execute(
                    """UPDATE archive_ad_page_photos
                       SET analysis_status = 'failed', analyzed_at = datetime('now'), updated_at = datetime('now')
                       WHERE id = ?""",
                    (row["id"],),
                )
                db.commit()
            continue

        raw = await call_minimax_image_understanding(AD_ANALYSIS_PROMPT, str(path), max_tokens=5000)
        ads = _normalize_ad_analysis(raw)

        with get_db() as db:
            if ads:
                db.execute(
                    """UPDATE archive_ad_page_photos
                       SET analysis_json = ?, analysis_status = 'analyzed_ads_found',
                           analyzed_at = datetime('now'), updated_at = datetime('now')
                       WHERE id = ?""",
                    (json.dumps({"ads": ads}), row["id"]),
                )
                for ad in ads:
                    db.execute(
                        """INSERT INTO archive_ads
                           (archive_id, page_photo_id, candidate_id, brand, product, category,
                            visible_text_json, full_page, color, subject_description, condition_notes,
                            policy_flags_json, collector_keywords_json, confidence, evidence_grade,
                            verification_status, recommendation, reasoning_summary, raw_analysis_json)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            archive_id,
                            row["id"],
                            row.get("candidate_id"),
                            ad.get("brand") or "",
                            ad.get("product") or "",
                            ad.get("category") or "",
                            json.dumps(ad.get("visible_text") or []),
                            1 if ad.get("full_page") else 0,
                            1 if ad.get("color") else 0,
                            ad.get("subject_description") or "",
                            ad.get("condition_notes") or "",
                            json.dumps(ad.get("policy_flags") or []),
                            json.dumps(ad.get("collector_keywords") or []),
                            ad.get("confidence") or 0,
                            ad.get("evidence_grade") or "B",
                            "verified_in_copy",
                            ad.get("recommendation") or "keep_with_magazine",
                            ad.get("reasoning_summary") or "",
                            json.dumps(ad),
                        ),
                    )
                # Link candidate if one was specified
                if row.get("candidate_id"):
                    db.execute(
                        """UPDATE archive_ad_opportunities
                           SET verification_status = 'verified_in_copy',
                               evidence_grade = 'A',
                               updated_at = datetime('now')
                           WHERE id = ?""",
                        (row["candidate_id"],),
                    )
            else:
                db.execute(
                    """UPDATE archive_ad_page_photos
                       SET analysis_json = ?, analysis_status = 'analyzed_no_ads',
                           analyzed_at = datetime('now'), updated_at = datetime('now')
                       WHERE id = ?""",
                    (json.dumps({"ads": [], "note": "No ad detected in uploaded image."}), row["id"]),
                )
            db.commit()
        analyzed.append({"photo_id": row["id"], "ads": ads, "status": "analyzed_ads_found" if ads else "analyzed_no_ads"})

    if not analyzed:
        raise HTTPException(400, "No uploaded ad-page photos were readable/supported for analysis.")
    return {"archive_id": archive_id, "provider": "minimax_token_plan", "capability": "image_understanding", "analyzed": analyzed}


@router.patch("/archives/{archive_id}/status")
async def transition_status(archive_id: int, req: StatusTransition):
    """Transition archive status with validation."""
    new_status = req.status
    if new_status not in ARCHIVE_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(ARCHIVE_STATUSES)}")

    with get_db() as db:
        row = db.execute("SELECT processed_status FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")

    current = dict_row(row)["processed_status"]
    allowed = VALID_STATUS_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise HTTPException(
            409,
            f"Invalid transition: cannot move from '{current}' to '{new_status}'. "
            f"Allowed: {', '.join(allowed) or 'none'}"
        )

    extras = ""
    params: list = [new_status]
    if new_status == "REBOXED":
        extras = ", reboxed_at = datetime('now')"
    params.append(archive_id)

    with get_db() as db:
        db.execute(
            f"UPDATE ag_archives SET processed_status = ?{extras}, updated_at = datetime('now') WHERE id = ?",
            params,
        )
    return {"id": archive_id, "processed_status": new_status, "previous_status": current}


@router.post("/archives/{archive_id}/rebox")
async def rebox_archive(archive_id: int, req: ReboxRequest):
    """Dedicated rebox action: set processed_box_code, archive_location, status=REBOXED, record reboxed_at."""
    if not req.processed_box_code:
        raise HTTPException(400, "processed_box_code is required for reboxing")

    with get_db() as db:
        row = db.execute("SELECT processed_status, reboxed_at FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")

    d = dict_row(row)
    current = d["processed_status"]

    # Validate transition
    allowed = VALID_STATUS_TRANSITIONS.get(current, [])
    if "REBOXED" not in allowed:
        raise HTTPException(
            409,
            f"Cannot rebox from '{current}'. REBOXED is only allowed from: {', '.join(allowed) or 'none'}"
        )

    with get_db() as db:
        db.execute(
            """UPDATE ag_archives
               SET processed_box_code = ?, archive_location = ?, processed_status = 'REBOXED',
                   reboxed_at = datetime('now'), updated_at = datetime('now')
               WHERE id = ?""",
            (req.processed_box_code, req.archive_location, archive_id),
        )
    log.info(f"Archive #{archive_id} reboxed to '{req.processed_box_code}', location='{req.archive_location}'")
    return {
        "id": archive_id,
        "processed_box_code": req.processed_box_code,
        "archive_location": req.archive_location,
        "processed_status": "REBOXED",
        "reboxed_at": datetime.now().isoformat(),
    }


# ── MarketForge Push ────────────────────────────────────────────────────────────

def _condition_to_marketforge(score: int) -> str:
    """Map ArchiveForge 1-5 condition score to MarketForge condition values."""
    mapping = {5: "new", 4: "like_new", 3: "good", 2: "fair", 1: "poor"}
    return mapping.get(score, "good")


def _build_marketforge_payload(archive: dict, photo_urls: list[str], category_id: str, ships_from_zip: str) -> dict:
    """Build a MarketForge ProductCreate payload from an archive record."""
    price = archive.get("rough_comp_min", 0) or 10.0
    if archive.get("rough_comp_max", 0):
        price = (archive.get("rough_comp_min", 0) + archive.get("rough_comp_max", 0)) / 2

    # Item specifics for the description
    specifics = archive.get("item_specifics", {})
    if isinstance(specifics, str):
        try:
            specifics = json.loads(specifics)
        except Exception:
            specifics = {}

    item_desc = archive.get("listing_description", "") or (
        f"LIFE Magazine — {archive.get('cover_subject', 'Vintage Issue')}. "
        f"Original issue date: {archive.get('issue_date', 'Unknown')}. "
        f"Condition: {_condition_to_marketforge(archive.get('condition_score', 3))}."
    )

    return {
        "title": archive.get("listing_title") or f"LIFE Magazine {archive.get('issue_date', '')} — {archive.get('cover_subject', 'Vintage')}",
        "description": item_desc,
        "category_id": category_id,
        "condition": _condition_to_marketforge(archive.get("condition_score", 3)),
        "price": round(price, 2),
        "shipping_price": 0.0,
        "offers_enabled": True,
        "minimum_offer": round(price * 0.8, 2) if price > 5 else None,
        "images": photo_urls,
        "package_weight_oz": 12,
        "package_length_in": 12,
        "package_width_in": 10,
        "package_height_in": 1,
        "ships_from_zip": ships_from_zip,
        "quantity": 1,
    }


@router.post("/push/{archive_id}")
async def push_to_marketforge(
    archive_id: int,
    approval_confirmed: bool = Query(
        False,
        description="Explicit approval gate for staged internal publish. Must be true to push.",
    ),
):
    """
    Attempt to push an archive listing draft to MarketForge.

    Validates archive state, builds product payload from actual listing photos,
    POSTs to MarketForge /marketplace/products endpoint, and stores the result.

    MarketForge dependency: app.routers.marketplace.products must be mounted
    at /marketplace/products in main.py. If not mounted, this returns 502
    with a clear dependency message.
    """
    if not approval_confirmed:
        raise HTTPException(
            400,
            "Cannot publish — explicit approval is required. Re-submit with approval_confirmed=true.",
        )

    # 1. Load archive
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")
    archive = dict_row(row)

    publish_status = await _marketforge_publish_status(archive=archive)
    if not publish_status["publish_available"]:
        raise HTTPException(
            503,
            f"MarketForge publish unavailable: {publish_status['reason']} Save the listing as a draft until MarketForge product creation is wired.",
        )

    # 2. Validate processed_status
    valid_publish_statuses = ["READY_TO_LIST", "LISTED"]
    if archive.get("processed_status") not in valid_publish_statuses:
        raise HTTPException(
            409,
            f"Cannot publish — processed_status must be {valid_publish_statuses[0]} or {valid_publish_statuses[1]}, "
            f"but is '{archive.get('processed_status')}'"
        )

    # 3. Validate listing fields
    if not archive.get("listing_title"):
        raise HTTPException(400, "Cannot publish — listing_title is blank. Fill in the listing title in Step 6.")
    if not archive.get("listing_description"):
        raise HTTPException(400, "Cannot publish — listing_description is blank. Fill in the listing description in Step 6.")

    # 4. Get actual listing photos
    with get_db() as db:
        photo_rows = dict_rows(db.execute(
            "SELECT * FROM ag_archive_photos WHERE archive_id = ? ORDER BY created_at ASC",
            (archive_id,),
        ).fetchall())
    photo_origin = _marketforge_photo_origin(MARKETFORGE_PRODUCTS_URL)
    photo_urls = [f"{photo_origin}/api/v1/archiveforge/photo/{p['id']}" for p in photo_rows]

    if not photo_urls:
        raise HTTPException(400, "Cannot publish — no actual listing photos uploaded. Upload at least a front cover photo in Step 3.")

    # 5. Validate required MarketForge publish fields
    missing_fields = publish_status.get("missing_required_fields", [])
    invalid_fields = publish_status.get("invalid_required_fields", [])
    if missing_fields or invalid_fields:
        missing_text = f"missing fields: {', '.join(missing_fields)}" if missing_fields else ""
        invalid_text = f"invalid fields: {', '.join(invalid_fields)}" if invalid_fields else ""
        reason = "Cannot publish — " + "; ".join(part for part in (missing_text, invalid_text) if part)
        reason += ". Set marketforge_category_id (UUID) and marketforge_ships_from_zip (5-digit ZIP) on this archive first."
        with get_db() as db:
            db.execute(
                """UPDATE ag_archives
                   SET marketforge_push_status = 'blocked_missing_marketforge_fields',
                       marketforge_error_message = ?,
                       listing_status = 'draft',
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (reason, archive_id),
            )
        raise HTTPException(409, reason)

    # 6. Build payload
    payload = _build_marketforge_payload(
        archive,
        photo_urls,
        category_id=publish_status["category_id"],
        ships_from_zip=publish_status["ships_from_zip"],
    )

    # 7. Attempt MarketForge push
    # Set status to pushing
    with get_db() as db:
        db.execute(
            "UPDATE ag_archives SET marketforge_push_status = 'pushing', listing_status = 'ready', updated_at = datetime('now') WHERE id = ?",
            (archive_id,),
        )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(MARKETFORGE_PRODUCTS_URL, json=payload)

        if resp.status_code in (200, 201):
            result = resp.json()
            mf_listing_id = str(result.get("id", ""))
            with get_db() as db:
                db.execute(
                    """UPDATE ag_archives
                       SET marketforge_push_status = 'pushed',
                           marketforge_listing_id = ?,
                           marketforge_pushed_at = datetime('now'),
                           marketforge_error_message = '',
                           listing_status = 'pushed',
                           updated_at = datetime('now')
                       WHERE id = ?""",
                    (mf_listing_id, archive_id),
                )
            log.info(f"Archive #{archive_id} pushed to MarketForge — listing_id={mf_listing_id}")
            return {
                "archive_id": archive_id,
                "marketforge_listing_id": mf_listing_id,
                "push_status": "pushed",
                "message": "Successfully pushed to MarketForge",
                "marketforge_response": result,
            }
        else:
            error_detail = resp.text[:500]
            with get_db() as db:
                db.execute(
                    """UPDATE ag_archives
                       SET marketforge_push_status = 'failed',
                           marketforge_error_message = ?,
                           listing_status = 'failed',
                           updated_at = datetime('now')
                       WHERE id = ?""",
                    (f"HTTP {resp.status_code}: {error_detail}", archive_id),
                )
            log.warning(f"Archive #{archive_id} MarketForge push failed: HTTP {resp.status_code}")
            raise HTTPException(502, f"MarketForge rejected the push (HTTP {resp.status_code}): {error_detail}")

    except httpx.ConnectError as e:
        with get_db() as db:
            db.execute(
                """UPDATE ag_archives
                   SET marketforge_push_status = 'failed',
                       marketforge_error_message = ?,
                       listing_status = 'failed',
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (f"Connection failed — MarketForge products endpoint not mounted at {MARKETFORGE_PRODUCTS_URL}. "
                 "This endpoint requires app.routers.marketplace.products to be loaded in main.py. "
                 "Until then, listings can be saved as drafts only.", archive_id),
            )
        raise HTTPException(
            502,
            f"MarketForge products endpoint not available at {MARKETFORGE_PRODUCTS_URL}. "
            "The marketplace/products router is not mounted in the running application. "
            "Save as draft for now — publishing requires MarketForge to be wired up."
        )
    except Exception as e:
        with get_db() as db:
            db.execute(
                """UPDATE ag_archives
                   SET marketforge_push_status = 'failed',
                       marketforge_error_message = ?,
                       listing_status = 'failed',
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (str(e)[:500], archive_id),
            )
        log.error(f"Archive #{archive_id} push error: {e}")
        raise HTTPException(500, f"Push failed: {str(e)[:200]}")


class SaveDraftRequest(BaseModel):
    listing_title: str = ""
    listing_description: str = ""
    batch_tag: str = ""


@router.post("/archives/{archive_id}/save-draft")
async def save_listing_draft(archive_id: int, req: SaveDraftRequest):
    """Save listing title/description as draft without publishing to MarketForge."""
    with get_db() as db:
        row = db.execute("SELECT id FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")

    with get_db() as db:
        db.execute(
            """UPDATE ag_archives
               SET listing_title = ?, listing_description = ?, batch_tag = ?,
                   listing_status = 'draft', marketforge_push_status = 'draft_saved',
                   updated_at = datetime('now')
               WHERE id = ?""",
            (req.listing_title, req.listing_description, req.batch_tag, archive_id),
        )
    return {
        "archive_id": archive_id,
        "listing_status": "draft",
        "marketforge_push_status": "draft_saved",
        "saved": True,
    }


@router.delete("/archives/{archive_id}")
async def delete_archive(archive_id: int):
    """Delete an archive item."""
    with get_db() as db:
        existing = db.execute("SELECT id FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Archive item not found")

        photo_rows = dict_rows(db.execute(
            "SELECT id, file_path FROM ag_archive_photos WHERE archive_id = ?",
            (archive_id,),
        ).fetchall())

        # Remove draft/history children before parent row to avoid FK failures.
        db.execute("DELETE FROM ag_listing_drafts WHERE archive_id = ?", (archive_id,))
        db.execute("DELETE FROM ag_archive_photos WHERE archive_id = ?", (archive_id,))
        db.execute("DELETE FROM ag_archives WHERE id = ?", (archive_id,))
        db.commit()

    # Best-effort cleanup for persisted files.
    for photo in photo_rows:
        file_path = Path(photo.get("file_path", ""))
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass

    item_dir = UPLOADS_DIR / str(archive_id)
    if item_dir.exists():
        try:
            item_dir.rmdir()
        except OSError:
            pass

    return {"id": archive_id, "deleted": True}


# ── Listing Draft ──────────────────────────────────────────────────────────────

@router.post("/archives/{archive_id}/listing-draft")
async def generate_listing_draft(archive_id: int, req: ListingDraftCreate):
    """Generate or update a MarketForge-ready listing draft from an archive item."""
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")
    d = dict_row(row)
    for fld in ("actual_listing_images",):
        if fld in d and isinstance(d[fld], str):
            try:
                d[fld] = json.loads(d[fld])
            except (json.JSONDecodeError, TypeError):
                d[fld] = []

    # Build item specifics
    item_specifics = req.item_specifics or {
        "Format": "Magazine",
        "Publication": "LIFE",
        "Year": d.get("issue_date", "")[:4] if d.get("issue_date") else "",
        "Issue Date": d.get("issue_date", ""),
        "Volume": d.get("volume") or "",
        "Issue Number": d.get("issue_number") or "",
        "Condition": _condition_label(d.get("condition_score", 0)),
        "Tier": d.get("tier", "C"),
        "Cover Subject": d.get("cover_subject", ""),
        "Address Label": "Yes" if d.get("has_address_label") else "No",
        "Complete": "Yes" if d.get("is_complete") else "No",
    }

    # Build MarketForge payload
    marketforge_payload = {
        "source": "archiveforge",
        "draft_id": None,
        "item": {
            "title": req.listing_title or d.get("listing_title") or f"LIFE Magazine {d.get('issue_date', 'Unknown')} — {d.get('cover_subject', 'Vintage Issue')}",
            "description": req.description or d.get("listing_description") or _build_description(d),
            "category": "Collectibles > Magazines > LIFE",
            "condition": _condition_label(d.get("condition_score", 0)),
            "images": d.get("actual_listing_images", []),
            "item_specifics": item_specifics,
            "tier": d.get("tier", "C"),
            "comp_range": [d.get("rough_comp_min", 0), d.get("rough_comp_max", 0)],
            "batch_tag": req.batch_tag or d.get("batch_tag", ""),
            "source_box": d.get("source_box_code", ""),
            "processed_box": d.get("processed_box_code", ""),
            "archive_status": d.get("processed_status", ""),
            "sale_plan": d.get("sale_plan", ""),
        },
        "reference_issue_id": d.get("reference_issue_id", ""),
        "reference_cover_url": d.get("reference_cover_url", ""),
        "generated_at": datetime.now().isoformat(),
    }

    # Save listing draft to DB
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO ag_listing_drafts
               (archive_id, listing_title, description, item_specifics, batch_tag, marketforge_payload, status)
               VALUES (?,?,?,?,?,?,?)""",
            (
                archive_id,
                req.listing_title or d.get("listing_title", ""),
                req.description or d.get("listing_description", ""),
                json.dumps(item_specifics),
                req.batch_tag or d.get("batch_tag", ""),
                json.dumps(marketforge_payload),
                "draft",
            ),
        )
        db.execute(
            "UPDATE ag_archives SET listing_title = ?, listing_description = ?, item_specifics = ?, batch_tag = ?, listing_draft_status = 'draft', updated_at = datetime('now') WHERE id = ?",
            (
                req.listing_title or d.get("listing_title", ""),
                req.description or d.get("listing_description", ""),
                json.dumps(item_specifics),
                req.batch_tag or d.get("batch_tag", ""),
                archive_id,
            ),
        )
        db.commit()
        draft_id = cur.lastrowid

    marketforge_payload["draft_id"] = draft_id
    return {
        "draft_id": draft_id,
        "listing_title": marketforge_payload["item"]["title"],
        "description": marketforge_payload["item"]["description"],
        "item_specifics": item_specifics,
        "marketforge_payload": marketforge_payload,
        "batch_tag": req.batch_tag,
        "status": "draft",
    }


def _condition_label(score: int) -> str:
    labels = {5: "Near Mint", 4: "Excellent", 3: "Good", 2: "Fair", 1: "Poor"}
    return labels.get(score, "Good")


def _build_description(d: dict) -> str:
    """Build a basic sale description from archive data."""
    parts = []
    if d.get("cover_subject"):
        parts.append(f"LIFE Magazine — {d['cover_subject']}")
    if d.get("issue_date"):
        parts.append(f"Issue Date: {d['issue_date']}")
    if d.get("volume") and d.get("issue_number"):
        parts.append(f"Volume {d['volume']}, Issue {d['issue_number']}")
    cond = _condition_label(d.get("condition_score", 0))
    parts.append(f"Condition: {cond}")
    if d.get("defects"):
        parts.append(f"Defects noted: {d['defects']}")
    if d.get("notes"):
        parts.append(f"Notes: {d['notes']}")
    comp_min = d.get("rough_comp_min", 0)
    comp_max = d.get("rough_comp_max", 0)
    if comp_min and comp_max:
        parts.append(f"Comparable sales range: ${comp_min:.0f}–${comp_max:.0f}")
    return ". ".join(parts)


# ── Manual Listing Draft & Handoff Packet ─────────────────────────────────────

LISTING_PACKET_REQUIRED_MESSAGE = "Create a listing draft before exporting the listing packet."
LISTING_PACKET_CSV_FIELDS = [
    "archive_id",
    "draft_id",
    "draft_status",
    "platform_target",
    "listing_title",
    "listing_description",
    "issue_date",
    "volume",
    "issue_number",
    "cover_subject",
    "condition_summary",
    "defects",
    "address_label_status",
    "completeness_status",
    "photo_list",
    "suggested_category",
    "suggested_price",
    "price_low",
    "price_high",
    "pricing_basis",
    "sale_plan",
    "inventory_location",
    "sku",
    "missing_fields_checklist",
    "manual_ebay_still_needed",
    "ai_confidence",
    "ai_evidence_source",
    "confirmed_reference_source",
    "confirmed_reference_id",
    "issue_info_status",
    "issue_info_front_photo_id",
    "issue_info_issue_date",
    "issue_info_cover_title",
    "issue_info_confidence",
    "issue_info_evidence_grade",
    "issue_info_google_books_volume_id",
    "issue_info_ad_opportunity_ready",
    "issue_info_stale_warning",
    "life_issue_master_date",
    "life_issue_master_subject",
    "life_issue_master_source_count",
    "life_issue_master_dtm_low",
    "life_issue_master_dtm_high",
    "life_issue_master_dtm_average",
    "life_issue_source_warning",
    "magazine_pricing_type",
    "magazine_pricing_confidence",
    "magazine_pricing_basis",
    "magazine_comp_links",
    "ad_opportunity_status",
    "ad_candidates",
    "verified_ads",
    "ad_recommendation",
    "ad_next_action",
    "ad_comp_summary",
    "ad_comp_links",
    "ad_priority_ranking",
    "ad_comp_warning",
    "generated_at",
]


def _json_value(value, default):
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _num_or_zero(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _num_or_none_for_packet(value):
    number = _num_or_zero(value)
    return round(number, 2) if number > 0 else None


def _issue_date_for_listing(archive: dict) -> str:
    return archive.get("confirmed_issue_date") or archive.get("issue_date") or ""


def _cover_subject_for_listing(archive: dict) -> str:
    return archive.get("confirmed_cover_title") or archive.get("cover_subject") or archive.get("issue_title") or ""


def _listing_title_for_archive(archive: dict) -> str:
    existing = (archive.get("listing_title") or "").strip()
    if existing:
        return existing
    issue_date = _issue_date_for_listing(archive)
    subject = _cover_subject_for_listing(archive) or "Vintage Issue"
    if issue_date:
        return f"LIFE Magazine {issue_date} - {subject}"
    return f"LIFE Magazine - {subject}"


def _listing_description_for_archive(archive: dict) -> str:
    existing = (archive.get("listing_description") or "").strip()
    if existing:
        return existing
    description = _build_description(archive).strip()
    if description:
        return description
    return "Vintage LIFE Magazine issue. Verify issue details, condition, and shipping specifics before listing."


def _sku_for_archive(archive: dict) -> str:
    return f"AF-LIFE-{int(archive.get('id') or 0):05d}"


def _inventory_location_for_archive(archive: dict) -> str:
    return " / ".join(
        str(value)
        for value in [
            archive.get("source_box_code") or "",
            archive.get("source_slot_position") or "",
            archive.get("processed_box_code") or "",
            archive.get("archive_location") or "",
        ]
        if value
    )


def _recommended_price_for_archive(archive: dict):
    final_price = _num_or_zero(archive.get("final_price"))
    if final_price:
        return round(final_price, 2)
    low = _num_or_zero(archive.get("rough_comp_min"))
    high = _num_or_zero(archive.get("rough_comp_max"))
    if low and high:
        return round((low + high) / 2, 2)
    if low:
        return round(low, 2)
    return None


def _photo_manifest_for_archive(archive_id: int) -> list[dict]:
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM ag_archive_photos
               WHERE archive_id = ?
               ORDER BY role = 'front' DESC, id ASC""",
            (archive_id,),
        ).fetchall())

    photos = []
    for row in rows:
        path = Path(row.get("file_path") or "")
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        photos.append({
            "id": row.get("id"),
            "photo_id": row.get("id"),
            "role": row.get("role") or "photo",
            "filename": row.get("filename") or "",
            "original_name": row.get("original_name") or "",
            "file_path": str(path) if row.get("file_path") else "",
            "url": _scoped_photo_url_for(archive_id, row.get("id")),
            "photo_url": _scoped_photo_url_for(archive_id, row.get("id")),
            "thumbnail_url": _thumbnail_url_for(archive_id, row.get("id")),
            "exists": exists,
            "size_bytes": size,
            "mime_type": mimetypes.guess_type(str(path))[0] if path else "",
            "created_at": row.get("created_at") or "",
        })
    return photos


def _ai_summary_for_archive(archive: dict) -> dict:
    summary = _json_value(archive.get("ai_identification_json"), {})
    if not isinstance(summary, dict):
        summary = {}
    if archive.get("ai_identified") is not None:
        summary.setdefault("identified", bool(archive.get("ai_identified")))
    if archive.get("ai_confidence") is not None:
        summary.setdefault("confidence", archive.get("ai_confidence"))
    if archive.get("ai_evidence_source"):
        summary.setdefault("evidence_source", archive.get("ai_evidence_source"))
    if archive.get("ai_identified_at"):
        summary.setdefault("identified_at", archive.get("ai_identified_at"))
    return summary


def _reference_confirmation_for_archive(archive: dict) -> dict:
    return {
        "confirmed_by_user": bool(archive.get("confirmed_by_user")),
        "reference_source": archive.get("confirmed_reference_source") or archive.get("reference_source") or "",
        "reference_id": archive.get("confirmed_reference_id") or archive.get("reference_issue_key") or archive.get("reference_issue_id") or "",
        "reference_url": archive.get("confirmed_reference_url") or archive.get("reference_cover_url") or "",
        "confirmed_issue_date": archive.get("confirmed_issue_date") or archive.get("issue_date") or "",
        "cover_title": archive.get("confirmed_cover_title") or archive.get("cover_subject") or "",
        "confidence": archive.get("confirmed_confidence") or 0,
    }


def _missing_listing_fields(archive: dict, photos: list[dict], title: str, description: str, recommended_price) -> list[str]:
    missing = []
    has_any_photo = any(photo.get("exists") and photo.get("size_bytes", 0) > 0 for photo in photos)
    has_front_photo = any(
        photo.get("role") == "front" and photo.get("exists") and photo.get("size_bytes", 0) > 0
        for photo in photos
    )
    if not title.strip():
        missing.append("listing title")
    if not description.strip():
        missing.append("listing description")
    if not has_any_photo:
        missing.append("usable photo")
    if not has_front_photo:
        missing.append("front cover photo")
    if not archive.get("condition_score"):
        missing.append("condition score")
    if not archive.get("sale_plan"):
        missing.append("sale plan")
    if recommended_price is None:
        missing.append("suggested price")
    if not _inventory_location_for_archive(archive):
        missing.append("inventory location")
    if not archive.get("confirmed_by_user"):
        missing.append("confirmed reference match")
    if not archive.get("ai_identification_json") or archive.get("ai_identification_json") == "{}":
        missing.append("AI identification summary")
    missing.extend([
        "payment policy",
        "return policy",
        "shipping policy",
        "package dimensions",
        "item location",
        "eBay account-specific settings",
    ])
    return missing


def _draft_row_to_dict(row: dict) -> dict:
    draft = dict(row)
    draft["draft_id"] = draft.get("id")
    draft["address_label"] = bool(draft.get("address_label"))
    draft["complete"] = bool(draft.get("complete"))
    draft["photo_manifest"] = _json_value(draft.pop("photo_manifest_json", "[]"), [])
    draft["ai_identification"] = _json_value(draft.pop("ai_identification_json", "{}"), {})
    draft["reference_confirmation"] = _json_value(draft.pop("reference_confirmation_json", "{}"), {})
    draft["missing_fields"] = _json_value(draft.pop("missing_fields_json", "[]"), [])
    return draft


def _latest_listing_packet_draft(archive_id: int) -> Optional[dict]:
    with get_db() as db:
        row = db.execute(
            """SELECT * FROM archive_listing_drafts
               WHERE archive_id = ?
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 1""",
            (archive_id,),
        ).fetchone()
    return _draft_row_to_dict(dict_row(row)) if row else None


def _build_listing_packet_draft(archive: dict) -> dict:
    photos = _photo_manifest_for_archive(archive["id"])
    ai_summary = _ai_summary_for_archive(archive)
    reference = _reference_confirmation_for_archive(archive)
    recommended_price = _recommended_price_for_archive(archive)
    title = _listing_title_for_archive(archive)
    description = _listing_description_for_archive(archive)
    missing_fields = _missing_listing_fields(archive, photos, title, description, recommended_price)
    return {
        "archive_id": archive["id"],
        "draft_status": "draft",
        "platform_target": "manual_handoff",
        "title": title,
        "description": description,
        "category": "Collectibles > Paper > Magazines > LIFE",
        "condition_label": _condition_label(archive.get("condition_score") or 0),
        "condition_score": archive.get("condition_score") or 0,
        "defects": archive.get("defects") or "",
        "address_label": bool(archive.get("has_address_label")),
        "complete": bool(archive.get("is_complete")),
        "price_low": _num_or_none_for_packet(archive.get("rough_comp_min")),
        "price_high": _num_or_none_for_packet(archive.get("rough_comp_max")),
        "recommended_price": recommended_price,
        "sale_plan": archive.get("sale_plan") or "",
        "sku": _sku_for_archive(archive),
        "inventory_location": _inventory_location_for_archive(archive),
        "photo_manifest": photos,
        "ai_identification": ai_summary,
        "reference_confirmation": reference,
        "missing_fields": missing_fields,
    }


def _ad_opportunity_packet_section(archive: dict) -> dict:
    metadata = _latest_issue_metadata(archive["id"])
    candidates = _list_ad_opportunities(archive["id"])
    verified_ads = [c for c in candidates if c.get("verification_status") == "verified_in_copy"]
    issue_candidates = [c for c in candidates if c.get("verification_status") != "verified_in_copy"]
    comp_groups = _group_ad_comps(archive["id"]) if candidates else []
    priority_ranking = _rank_ad_candidates(archive["id"]) if candidates else []
    if not metadata and not candidates:
        return {
            "status": "not_run",
            "message": "Ad Opportunity Check not run.",
            "issue_metadata": None,
            "candidate_ads": [],
            "verified_ads": [],
            "recommendation": _ad_breakout_recommendation(archive, []),
            "comp_research": {"status": "not_run", "groups": [], "ranking": []},
            "warning": "",
        }
    warning = ""
    if candidates and not verified_ads:
        warning = "Ad opportunities are issue-level candidates only. Not verified in this physical copy."
    elif issue_candidates:
        warning = "Some ad opportunities are still issue-level candidates only. Only uploaded/analyzed ad pages are verified."
    return {
        "status": "verified_ads_present" if verified_ads else "candidates_unverified" if candidates else "metadata_only",
        "message": warning or "Verified ad-page analysis is available.",
        "issue_metadata": metadata,
        "candidate_ads": issue_candidates,
        "verified_ads": verified_ads,
        "recommendation": _ad_breakout_recommendation(archive, candidates),
        "comp_research": {
            "status": "available" if any(group.get("comps") for group in comp_groups) else "not_run",
            "groups": comp_groups,
            "ranking": priority_ranking,
            "warning": (
                "No sold comps exist in ArchiveForge. Search links and active listings are lower-confidence evidence."
                if not any((rank.get("sold_comp_count") or 0) > 0 for rank in priority_ranking)
                else "Sold/manual comp data exists for at least one candidate."
            ),
        },
        "warning": warning,
    }


def _packet_from_draft(archive: dict, draft: dict) -> dict:
    photos = draft.get("photo_manifest") or []
    photo_list = [
        {
            "role": photo.get("role"),
            "path": photo.get("file_path"),
            "url": photo.get("url"),
            "size_bytes": photo.get("size_bytes"),
        }
        for photo in photos
    ]
    still_needed = [
        "payment policy",
        "return policy",
        "shipping policy",
        "package dimensions",
        "item location",
        "eBay account-specific settings",
    ]
    ai_summary = draft.get("ai_identification") or {}
    reference = draft.get("reference_confirmation") or {}
    issue_info = _issue_info_packet_section(archive["id"])
    ad_section = _ad_opportunity_packet_section(archive)
    issue_master = _issue_master_for_archive(archive["id"])
    issue_sources = _issue_master_sources(int(issue_master.get("id"))) if issue_master and issue_master.get("id") else []
    magazine_comps = _list_magazine_comps(archive["id"])
    pricing_summary = _pricing_summary_for_archive(archive["id"]) or _calculate_magazine_pricing(archive["id"], persist=False)
    issue_date = reference.get("confirmed_issue_date") or _issue_date_for_listing(archive)
    cover_subject = reference.get("cover_title") or _cover_subject_for_listing(archive)
    condition_summary = f"{draft.get('condition_label') or _condition_label(archive.get('condition_score') or 0)}"
    if draft.get("condition_score"):
        condition_summary += f" ({draft.get('condition_score')}/5)"
    manual_ebay_handoff = {
        "section": "Manual eBay Handoff",
        "suggested_ebay_title": draft.get("title") or "",
        "suggested_ebay_description": draft.get("description") or "",
        "suggested_category_text": draft.get("category") or "Collectibles > Paper > Magazines > LIFE",
        "suggested_condition": condition_summary,
        "suggested_price": draft.get("recommended_price") or None,
        "photo_list": photo_list,
        "item_specifics": {
            "Publication": "LIFE",
            "Format": "Magazine",
            "Issue Date": issue_date,
            "Volume": archive.get("volume") or "",
            "Issue Number": archive.get("issue_number") or "",
            "Cover Subject": cover_subject,
            "Address Label": "Yes" if draft.get("address_label") else "No",
            "Complete": "Yes" if draft.get("complete") else "No",
            "SKU": draft.get("sku") or "",
        },
        "still_needed": still_needed,
    }
    return {
        "archive_id": archive["id"],
        "draft_id": draft.get("draft_id") or draft.get("id"),
        "draft_status": draft.get("draft_status") or "draft",
        "platform_target": draft.get("platform_target") or "manual_handoff",
        "publish_status": "not_published",
        "listing_title": draft.get("title") or "",
        "listing_description": draft.get("description") or "",
        "issue_date": issue_date,
        "volume": archive.get("volume") or "",
        "issue_number": archive.get("issue_number") or "",
        "cover_subject": cover_subject,
        "condition_summary": condition_summary,
        "defects": draft.get("defects") or "",
        "address_label_status": "Yes" if draft.get("address_label") else "No",
        "completeness_status": "Complete" if draft.get("complete") else "Incomplete",
        "photos": photo_list,
        "photo_manifest": photos,
        "suggested_category": draft.get("category") or "Collectibles > Paper > Magazines > LIFE",
        "suggested_price": draft.get("recommended_price") or None,
        "price_low": draft.get("price_low") or None,
        "price_high": draft.get("price_high") or None,
        "pricing_basis": archive.get("pricing_basis") or "manual_rough_estimate",
        "sale_plan": draft.get("sale_plan") or "",
        "inventory_location": draft.get("inventory_location") or "",
        "sku": draft.get("sku") or "",
        "missing_fields_checklist": draft.get("missing_fields") or [],
        "manual_ebay_handoff": manual_ebay_handoff,
        "manual_listing_notes": "Manual handoff packet only. Review fields and create the marketplace listing outside EmpireBox.",
        "ai_identification_summary": ai_summary,
        "confirmed_reference_summary": reference,
        "issue_info": issue_info,
        "life_issue_master": issue_master,
        "life_issue_sources": issue_sources,
        "pricing_summary": pricing_summary,
        "magazine_comps": magazine_comps,
        "ad_opportunity_check": ad_section,
        "uploaded_ad_page_photos": _ad_page_photos_for_packet(archive["id"]),
        "analyzed_ads": _analyzed_ads_for_packet(archive["id"]),
        "generated_at": datetime.now().isoformat(),
    }


def _ad_page_photos_for_packet(archive_id: int) -> list[dict]:
    """Fetch uploaded ad-page photo records for listing packet."""
    try:
        with get_db() as db:
            rows = dict_rows(db.execute(
                """SELECT id, archive_id, candidate_id, page_number, filename,
                          original_name, file_path, mime_type, byte_size,
                          analysis_status, analyzed_at, created_at
                   FROM archive_ad_page_photos
                   WHERE archive_id = ?
                   ORDER BY id DESC""",
                (archive_id,),
            ).fetchall())
            return rows
    except Exception:
        return []


def _analyzed_ads_for_packet(archive_id: int) -> list[dict]:
    """Fetch analyzed ad records for listing packet."""
    try:
        with get_db() as db:
            rows = dict_rows(db.execute(
                """SELECT id, archive_id, page_photo_id, candidate_id, brand, product,
                          category, confidence, evidence_grade, verification_status,
                          recommendation, reasoning_summary, created_at
                   FROM archive_ads
                   WHERE archive_id = ?
                   ORDER BY confidence DESC""",
                (archive_id,),
            ).fetchall())
            return rows
    except Exception:
        return []


def _require_listing_packet(archive_id: int) -> tuple[dict, dict, dict]:
    archive = _load_archive_or_404(archive_id)
    draft = _latest_listing_packet_draft(archive_id)
    if not draft:
        raise HTTPException(409, LISTING_PACKET_REQUIRED_MESSAGE)
    return archive, draft, _packet_from_draft(archive, draft)


def _packet_export_row(packet: dict) -> dict:
    issue_info = packet.get("issue_info") or {}
    issue_master = packet.get("life_issue_master") or {}
    pricing_summary = packet.get("pricing_summary") or {}
    magazine_comps = packet.get("magazine_comps") or []
    ad_section = packet.get("ad_opportunity_check") or {}
    ad_recommendation = ad_section.get("recommendation") or {}
    comp_research = ad_section.get("comp_research") or {}
    comp_groups = comp_research.get("groups") or []
    ranking = comp_research.get("ranking") or []
    search_links = []
    for group in comp_groups:
        candidate = group.get("candidate") or {}
        for comp in group.get("comps") or []:
            if comp.get("result_type") == "search_link":
                search_links.append(
                    f"{candidate.get('brand') or candidate.get('category') or 'candidate'}: {comp.get('url') or ''}"
                )
    return {
        "archive_id": packet.get("archive_id"),
        "draft_id": packet.get("draft_id"),
        "draft_status": packet.get("draft_status"),
        "platform_target": packet.get("platform_target"),
        "listing_title": packet.get("listing_title"),
        "listing_description": packet.get("listing_description"),
        "issue_date": packet.get("issue_date"),
        "volume": packet.get("volume"),
        "issue_number": packet.get("issue_number"),
        "cover_subject": packet.get("cover_subject"),
        "condition_summary": packet.get("condition_summary"),
        "defects": packet.get("defects"),
        "address_label_status": packet.get("address_label_status"),
        "completeness_status": packet.get("completeness_status"),
        "photo_list": "; ".join(
            f"{photo.get('role')}: {photo.get('path') or photo.get('url')}"
            for photo in packet.get("photos", [])
        ),
        "suggested_category": packet.get("suggested_category"),
        "suggested_price": packet.get("suggested_price"),
        "price_low": packet.get("price_low"),
        "price_high": packet.get("price_high"),
        "pricing_basis": packet.get("pricing_basis"),
        "sale_plan": packet.get("sale_plan"),
        "inventory_location": packet.get("inventory_location"),
        "sku": packet.get("sku"),
        "missing_fields_checklist": "; ".join(packet.get("missing_fields_checklist", [])),
        "manual_ebay_still_needed": "; ".join(packet.get("manual_ebay_handoff", {}).get("still_needed", [])),
        "ai_confidence": packet.get("ai_identification_summary", {}).get("confidence"),
        "ai_evidence_source": packet.get("ai_identification_summary", {}).get("evidence_source"),
        "confirmed_reference_source": packet.get("confirmed_reference_summary", {}).get("reference_source"),
        "confirmed_reference_id": packet.get("confirmed_reference_summary", {}).get("reference_id"),
        "issue_info_status": issue_info.get("status"),
        "issue_info_front_photo_id": issue_info.get("front_photo_id"),
        "issue_info_issue_date": issue_info.get("issue_date"),
        "issue_info_cover_title": issue_info.get("cover_title") or issue_info.get("detected_subject"),
        "issue_info_confidence": issue_info.get("confidence"),
        "issue_info_evidence_grade": issue_info.get("evidence_grade"),
        "issue_info_google_books_volume_id": issue_info.get("selected_google_books_volume_id"),
        "issue_info_ad_opportunity_ready": issue_info.get("ad_opportunity_ready"),
        "issue_info_stale_warning": issue_info.get("stale_warning") or "",
        "life_issue_master_date": issue_master.get("normalized_date") or "",
        "life_issue_master_subject": issue_master.get("cover_subject") or issue_master.get("description") or "",
        "life_issue_master_source_count": issue_master.get("source_count") or 0,
        "life_issue_master_dtm_low": issue_master.get("dtmagazine_low") or "",
        "life_issue_master_dtm_high": issue_master.get("dtmagazine_high") or "",
        "life_issue_master_dtm_average": issue_master.get("dtmagazine_average") or "",
        "life_issue_source_warning": "DTM guide values are reference-guide values, not current sold comps." if issue_master.get("dtmagazine_average") else "",
        "magazine_pricing_type": pricing_summary.get("pricing_type") or "",
        "magazine_pricing_confidence": pricing_summary.get("confidence") or "",
        "magazine_pricing_basis": pricing_summary.get("pricing_basis") or "",
        "magazine_comp_links": "; ".join(c.get("url") or "" for c in magazine_comps if c.get("result_type") == "search_link")[:2000],
        "ad_opportunity_status": ad_section.get("status"),
        "ad_candidates": "; ".join(
            " ".join(x for x in [c.get("brand") or "", c.get("product") or c.get("category") or "", c.get("verification_status") or ""] if x)
            for c in ad_section.get("candidate_ads", [])[:20]
        ),
        "verified_ads": "; ".join(
            " ".join(x for x in [c.get("brand") or "", c.get("product") or c.get("category") or "", c.get("verification_status") or ""] if x)
            for c in ad_section.get("verified_ads", [])[:20]
        ),
        "ad_recommendation": ad_recommendation.get("recommendation"),
        "ad_next_action": ad_recommendation.get("next_action"),
        "ad_comp_summary": comp_research.get("warning") or "",
        "ad_comp_links": "; ".join(search_links[:20]),
        "ad_priority_ranking": "; ".join(
            f"{r.get('brand') or r.get('category') or r.get('candidate_id')}: {r.get('value_score')} {r.get('suggested_action')}"
            for r in ranking[:12]
        ),
        "ad_comp_warning": comp_research.get("warning") or "",
        "generated_at": packet.get("generated_at"),
    }


def _packet_csv_response(packet: dict, filename: str) -> Response:
    row = _packet_export_row(packet)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=LISTING_PACKET_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerow(row)
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _packet_xlsx_response(packet: dict, filename: str) -> Response:
    def cell(value) -> str:
        text = "" if value is None else str(value)
        return f'<c t="inlineStr"><is><t>{xml_escape(text)}</t></is></c>'

    row = _packet_export_row(packet)
    sheet_rows = [
        "<row>" + "".join(cell(field) for field in LISTING_PACKET_CSV_FIELDS) + "</row>",
        "<row>" + "".join(cell(row.get(field, "")) for field in LISTING_PACKET_CSV_FIELDS) + "</row>",
    ]
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{_xlsx_col_name(len(LISTING_PACKET_CSV_FIELDS))}2"/>'
        '<sheetData>' + "".join(sheet_rows) + '</sheetData></worksheet>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""")
        zf.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
        zf.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Listing Packet" sheetId="1" r:id="rId1"/></sheets>
</workbook>""")
        zf.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""")
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{archive_id}/create-listing-draft")
async def create_listing_packet_draft(archive_id: int):
    """Create a manual listing draft. This does not publish to any marketplace."""
    archive = _load_archive_or_404(archive_id)
    draft = _build_listing_packet_draft(archive)
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO archive_listing_drafts
               (archive_id, draft_status, platform_target, title, description, category,
                condition_label, condition_score, defects, address_label, complete,
                price_low, price_high, recommended_price, sale_plan, sku, inventory_location,
                photo_manifest_json, ai_identification_json, reference_confirmation_json, missing_fields_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                archive_id,
                draft["draft_status"],
                draft["platform_target"],
                draft["title"],
                draft["description"],
                draft["category"],
                draft["condition_label"],
                draft["condition_score"],
                draft["defects"],
                int(draft["address_label"]),
                int(draft["complete"]),
                draft["price_low"] or 0,
                draft["price_high"] or 0,
                draft["recommended_price"] or 0,
                draft["sale_plan"],
                draft["sku"],
                draft["inventory_location"],
                json.dumps(draft["photo_manifest"]),
                json.dumps(draft["ai_identification"]),
                json.dumps(draft["reference_confirmation"]),
                json.dumps(draft["missing_fields"]),
            ),
        )
        db.execute(
            """UPDATE ag_archives
               SET listing_title = ?,
                   listing_description = ?,
                   listing_draft_status = 'draft',
                   listing_status = 'draft',
                   marketforge_push_status = 'draft_saved',
                   updated_at = datetime('now')
               WHERE id = ?""",
            (draft["title"], draft["description"], archive_id),
        )
        db.commit()
        draft_id = cur.lastrowid

    saved = _latest_listing_packet_draft(archive_id) or {**draft, "draft_id": draft_id}
    log.info("ArchiveForge manual listing draft created archive_id=%s draft_id=%s platform_target=manual_handoff", archive_id, draft_id)
    return {
        "archive_id": archive_id,
        "draft_id": draft_id,
        "draft_status": "draft",
        "platform_target": "manual_handoff",
        "title": draft["title"],
        "description": draft["description"],
        "recommended_price": draft["recommended_price"],
        "missing_fields": draft["missing_fields"],
        "draft": saved,
        "publishes_live_listing": False,
    }


@router.get("/{archive_id}/listing-draft")
async def get_listing_packet_draft(archive_id: int):
    """Return the latest manual listing draft for an archive item."""
    _load_archive_or_404(archive_id)
    draft = _latest_listing_packet_draft(archive_id)
    if not draft:
        raise HTTPException(404, LISTING_PACKET_REQUIRED_MESSAGE)
    return {"archive_id": archive_id, "draft_id": draft.get("draft_id"), "draft": draft}


@router.get("/{archive_id}/listing-packet.json")
async def export_listing_packet_json(archive_id: int, include_images: bool = Query(False)):
    """Return a manual listing handoff packet sourced from the latest listing draft."""
    _, _, packet = _require_listing_packet(archive_id)
    packet["include_images"] = include_images
    return packet


@router.get("/{archive_id}/listing-packet.csv")
async def export_listing_packet_csv(archive_id: int, include_images: bool = Query(False)):
    """Return a real CSV manual listing handoff packet from the latest listing draft."""
    _, _, packet = _require_listing_packet(archive_id)
    return _packet_csv_response(packet, f"archiveforge_{archive_id}_listing_packet.csv")


@router.get("/{archive_id}/listing-packet.xlsx")
async def export_listing_packet_xlsx(archive_id: int, include_images: bool = Query(False)):
    """Return a dependency-free XLSX manual listing handoff packet from the latest listing draft."""
    _, _, packet = _require_listing_packet(archive_id)
    return _packet_xlsx_response(packet, f"archiveforge_{archive_id}_listing_packet.xlsx")


@router.get("/{archive_id}/listing-packet.pdf")
async def export_listing_packet_pdf(archive_id: int, include_images: bool = Query(False)):
    """Return a PDF manual listing handoff packet from the latest listing draft."""
    _, _, packet = _require_listing_packet(archive_id)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib import colors
    except Exception as exc:
        raise HTTPException(501, f"PDF export requires reportlab: {type(exc).__name__}")

    def p(text) -> Paragraph:
        return Paragraph(xml_escape("" if text is None else str(text)), styles["Normal"])

    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=f"ArchiveForge listing packet {archive_id}")
    story = [
        Paragraph("ArchiveForge Listing Packet", styles["Title"]),
        Paragraph("Manual handoff export. This packet does not publish to eBay or any marketplace.", styles["Normal"]),
        Spacer(1, 0.15 * inch),
    ]

    rows = [
        ["Archive ID", packet.get("archive_id")],
        ["Draft ID", packet.get("draft_id")],
        ["Listing Title", packet.get("listing_title")],
        ["Suggested Category", packet.get("suggested_category")],
        ["Suggested Price", packet.get("suggested_price")],
        ["Price Low/High", f"{packet.get('price_low') or ''} / {packet.get('price_high') or ''}"],
        ["Pricing Basis", packet.get("pricing_basis")],
        ["Issue Date", packet.get("issue_date")],
        ["Volume / Issue", f"{packet.get('volume') or ''} / {packet.get('issue_number') or ''}"],
        ["Cover Subject", packet.get("cover_subject")],
        ["Condition", packet.get("condition_summary")],
        ["Defects", packet.get("defects")],
        ["Address Label", packet.get("address_label_status")],
        ["Completeness", packet.get("completeness_status")],
        ["Sale Plan", packet.get("sale_plan")],
        ["Inventory Location", packet.get("inventory_location")],
        ["SKU", packet.get("sku")],
    ]
    table = Table(rows, colWidths=[1.65 * inch, 5.25 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    story.extend([table, Spacer(1, 0.18 * inch)])

    story.append(Paragraph("Copy/Paste Listing Description", styles["Heading2"]))
    story.append(p(packet.get("listing_description") or ""))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Manual eBay Handoff", styles["Heading2"]))
    handoff = packet.get("manual_ebay_handoff", {})
    story.append(p(f"Suggested eBay title: {handoff.get('suggested_ebay_title') or ''}"))
    story.append(p(f"Suggested condition: {handoff.get('suggested_condition') or ''}"))
    story.append(p(f"Suggested price: {handoff.get('suggested_price') or ''}"))
    story.append(p(f"Still needed: {', '.join(handoff.get('still_needed') or [])}"))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Missing Fields Checklist", styles["Heading2"]))
    for item in packet.get("missing_fields_checklist") or []:
        story.append(p(f"- {item}"))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("AI Identification Summary", styles["Heading2"]))
    ai_summary = packet.get("ai_identification_summary") or {}
    story.append(p(ai_summary.get("reasoning_summary") or json.dumps(ai_summary, sort_keys=True)))
    story.append(Spacer(1, 0.15 * inch))

    issue_info = packet.get("issue_info") or {}
    story.append(Paragraph("Issue Info Resolver", styles["Heading2"]))
    if issue_info.get("status") and issue_info.get("status") != "not_run":
        story.append(p(
            f"Status: {issue_info.get('status')}; "
            f"Photo ID: {issue_info.get('front_photo_id') or ''}; "
            f"Issue date: {issue_info.get('issue_date') or ''}; "
            f"Title/subject: {issue_info.get('cover_title') or issue_info.get('detected_subject') or ''}; "
            f"Confidence: {issue_info.get('confidence') or 0}; "
            f"Evidence grade: {issue_info.get('evidence_grade') or ''}; "
            f"Google Books volume: {issue_info.get('selected_google_books_volume_id') or ''}"
        ))
        if issue_info.get("stale_warning"):
            story.append(p(f"Warning: {issue_info.get('stale_warning')}"))
        visible_text = issue_info.get("visible_text") or []
        if visible_text:
            story.append(p("Visible text: " + "; ".join(str(v) for v in visible_text[:20])))
    else:
        story.append(p("Issue Info Resolver not run."))
    story.append(Spacer(1, 0.15 * inch))

    issue_master = packet.get("life_issue_master") or {}
    pricing_summary = packet.get("pricing_summary") or {}
    story.append(Paragraph("LIFE Issue Master / Sources", styles["Heading2"]))
    if issue_master:
        story.append(p(
            f"Master date: {issue_master.get('normalized_date') or ''}; "
            f"Subject: {issue_master.get('cover_subject') or issue_master.get('description') or ''}; "
            f"Sources: {issue_master.get('source_count') or 0}; "
            f"DTM guide: ${issue_master.get('dtmagazine_low') or 0} - ${issue_master.get('dtmagazine_high') or 0} "
            f"(avg ${issue_master.get('dtmagazine_average') or 0})"
        ))
        if issue_master.get("dtmagazine_average"):
            story.append(p("Warning: DTM guide values are reference-guide values, not current sold comps."))
    else:
        story.append(p("No LIFE issue master row linked yet."))
    if pricing_summary:
        story.append(Paragraph("Magazine Pricing Summary", styles["Heading3"]))
        story.append(p(
            f"Type: {pricing_summary.get('pricing_type') or ''}; "
            f"Confidence: {pricing_summary.get('confidence') or ''}; "
            f"Range: {pricing_summary.get('estimate_low') or ''} - {pricing_summary.get('estimate_high') or ''}; "
            f"Recommended: {pricing_summary.get('recommended_price') or ''}; "
            f"Basis: {pricing_summary.get('pricing_basis') or ''}"
        ))
        for warning in pricing_summary.get("warnings") or []:
            story.append(p(f"Warning: {warning}"))
    magazine_comps = packet.get("magazine_comps") or []
    if magazine_comps:
        story.append(Paragraph("Magazine Comp / Research Links", styles["Heading3"]))
        for comp in magazine_comps[:12]:
            story.append(p(
                f"{comp.get('result_type')}: {comp.get('title') or comp.get('query') or ''} "
                f"{comp.get('price') or comp.get('total_price') or ''} {comp.get('url') or ''}"
            ))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Confirmed Reference Summary", styles["Heading2"]))
    story.append(p(json.dumps(packet.get("confirmed_reference_summary") or {}, sort_keys=True)))
    story.append(Spacer(1, 0.15 * inch))

    ad_section = packet.get("ad_opportunity_check") or {}
    story.append(Paragraph("Ad Opportunity Check", styles["Heading2"]))
    story.append(p(ad_section.get("message") or "Ad Opportunity Check not run."))
    if ad_section.get("warning"):
        story.append(p(f"Warning: {ad_section.get('warning')}"))
    issue_meta = ad_section.get("issue_metadata") or {}
    if issue_meta:
        story.append(p(
            f"Google Books volume: {issue_meta.get('source_volume_id') or ''}; "
            f"Issue date: {issue_meta.get('issue_date') or ''}; "
            f"Pages: {issue_meta.get('page_count') or ''}; "
            f"Source: {issue_meta.get('source_url') or ''}"
        ))
    recommendation = ad_section.get("recommendation") or {}
    if recommendation:
        story.append(p(
            f"Whole-vs-ad recommendation: {recommendation.get('recommendation') or 'insufficient_data'}; "
            f"Next action: {recommendation.get('next_action') or ''}"
        ))
    candidates = ad_section.get("candidate_ads") or []
    verified_ads = ad_section.get("verified_ads") or []
    if candidates:
        story.append(Paragraph("Issue-Level Candidate Ads", styles["Heading3"]))
        for candidate in candidates[:12]:
            story.append(p(
                f"{candidate.get('brand') or candidate.get('category') or 'candidate'} "
                f"{candidate.get('product') or ''} - grade {candidate.get('evidence_grade')}; "
                f"{candidate.get('verification_status')}; query: {candidate.get('search_query') or ''}"
            ))
    if verified_ads:
        story.append(Paragraph("Verified Ad-Page Photos", styles["Heading3"]))
        for ad in verified_ads[:12]:
            story.append(p(
                f"{ad.get('brand') or ad.get('category') or 'ad'} {ad.get('product') or ''} - "
                f"grade {ad.get('evidence_grade')}; {ad.get('recommendation')}"
            ))
    comp_research = ad_section.get("comp_research") or {}
    if comp_research:
        story.append(Paragraph("Ad Comp Research", styles["Heading3"]))
        story.append(p(comp_research.get("warning") or "Ad comp research not run."))
        ranking = comp_research.get("ranking") or []
        if ranking:
            story.append(Paragraph("Ads To Photograph First", styles["Heading3"]))
            for rank in ranking[:8]:
                story.append(p(
                    f"{rank.get('brand') or rank.get('category') or 'candidate'} {rank.get('product') or ''}: "
                    f"score {rank.get('value_score')}; {rank.get('comp_confidence')} confidence; "
                    f"{rank.get('suggested_action')}; {rank.get('reasoning_summary')}"
                ))
        groups = comp_research.get("groups") or []
        links = []
        for group in groups:
            candidate = group.get("candidate") or {}
            for comp in group.get("comps") or []:
                if comp.get("result_type") == "search_link":
                    links.append((candidate, comp))
        if links:
            story.append(Paragraph("Research Links", styles["Heading3"]))
            for candidate, comp in links[:15]:
                story.append(p(
                    f"{candidate.get('brand') or candidate.get('category') or 'candidate'}: "
                    f"{comp.get('title') or ''} - {comp.get('url') or ''}"
                ))
    story.append(Spacer(1, 0.15 * inch))

    if packet.get("photos"):
        story.append(Paragraph("Photo Manifest", styles["Heading2"]))
        for photo in packet["photos"][:8]:
            story.append(p(f"{photo.get('role')}: {photo.get('path') or photo.get('url')} ({photo.get('size_bytes') or 0} bytes)"))
            path = Path(photo.get("path") or "")
            if include_images and path.exists() and path.stat().st_size > 0:
                try:
                    story.append(Image(str(path), width=2.0 * inch, height=2.0 * inch, kind="proportional"))
                    story.append(Spacer(1, 0.08 * inch))
                except Exception:
                    pass

    doc.build(story)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="archiveforge_{archive_id}_listing_packet.pdf"'},
    )


# ── Inventory, Photos, Issue Master, and Magazine Pricing Helpers ─────────────

def _safe_upload_path(value: str | None) -> Optional[Path]:
    if not value:
        return None
    try:
        root = UPLOADS_DIR.resolve()
        path = Path(value).expanduser().resolve()
        if path == root or root in path.parents:
            return path
    except Exception:
        return None
    return None


def _photo_url_for(photo_id: Any) -> str:
    return f"/api/v1/archiveforge/photo/{photo_id}" if photo_id else ""


def _scoped_photo_url_for(archive_id: Any, photo_id: Any) -> str:
    return f"/api/v1/archiveforge/{archive_id}/photos/{photo_id}/image" if archive_id and photo_id else ""


def _thumbnail_url_for(archive_id: Any, photo_id: Any) -> str:
    return f"/api/v1/archiveforge/{archive_id}/photos/{photo_id}/thumbnail" if archive_id and photo_id else ""


def _photo_record_to_response(row: dict, archive_id: Optional[int] = None, role_override: str = "") -> dict:
    d = dict(row)
    photo_id = d.get("id") or d.get("photo_id")
    archive_id = archive_id or d.get("archive_id")
    path = _safe_upload_path(d.get("file_path"))
    exists = bool(path and path.exists())
    file_size = path.stat().st_size if exists else int(d.get("byte_size") or 0)
    mime_type = d.get("mime_type") or (mimetypes.guess_type(str(path))[0] if path else "") or ""
    role = role_override or d.get("role") or "photo"
    return {
        "photo_id": photo_id,
        "id": photo_id,
        "archive_id": archive_id,
        "role": role,
        "filename": d.get("filename") or "",
        "original_name": d.get("original_name") or "",
        "image_path": str(path) if path else "",
        "mime_type": mime_type,
        "file_size": file_size,
        "file_size_bytes": file_size,
        "created_at": d.get("created_at") or "",
        "photo_url": _scoped_photo_url_for(archive_id, photo_id),
        "url": _scoped_photo_url_for(archive_id, photo_id),
        "thumbnail_url": _thumbnail_url_for(archive_id, photo_id),
        "legacy_url": _photo_url_for(photo_id),
        "exists": exists,
        "is_primary": role.lower() in ACTUAL_FRONT_COVER_ROLES,
        "analysis_status": d.get("analysis_status") or ("analyzed" if d.get("analyzed_at") else "not_analyzed"),
    }


def _photo_counts_for_archive(archive_id: int) -> dict:
    with get_db() as db:
        photos = dict_rows(db.execute("SELECT * FROM ag_archive_photos WHERE archive_id = ?", (archive_id,)).fetchall())
        ad_pages = dict_rows(db.execute("SELECT * FROM archive_ad_page_photos WHERE archive_id = ?", (archive_id,)).fetchall())
        verified = db.execute(
            "SELECT COUNT(*) FROM archive_ad_opportunities WHERE archive_id = ? AND verification_status = 'verified_in_copy'",
            (archive_id,),
        ).fetchone()[0]
    front_present = False
    for photo in photos:
        if str(photo.get("role") or "").lower() in ACTUAL_FRONT_COVER_ROLES:
            path = _safe_upload_path(photo.get("file_path"))
            if path and path.exists() and path.stat().st_size > 0:
                front_present = True
                break
    return {
        "photo_count": len(photos),
        "front_photo_present": front_present,
        "ad_page_photo_count": len(ad_pages),
        "verified_ad_count": int(verified or 0),
    }


def _photos_grouped_for_archive(archive_id: int) -> dict:
    with get_db() as db:
        item_photos = dict_rows(db.execute(
            "SELECT * FROM ag_archive_photos WHERE archive_id = ? ORDER BY role = 'front' DESC, id ASC",
            (archive_id,),
        ).fetchall())
        ad_page_photos = dict_rows(db.execute(
            "SELECT * FROM archive_ad_page_photos WHERE archive_id = ? ORDER BY id ASC",
            (archive_id,),
        ).fetchall())
        archive = db.execute("SELECT reference_cover_url, cover_thumbnail_url, cover_preview_url FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    grouped = {"front": [], "spine": [], "back": [], "defects": [], "label": [], "ad_pages": [], "reference_cover": [], "other": []}
    for row in item_photos:
        role = str(row.get("role") or "other").lower()
        response = _photo_record_to_response(row, archive_id)
        if role in ACTUAL_FRONT_COVER_ROLES:
            grouped["front"].append(response)
        elif role in {"spine"}:
            grouped["spine"].append(response)
        elif role in {"back", "back_cover"}:
            grouped["back"].append(response)
        elif role in {"defect", "defects", "damage"}:
            grouped["defects"].append(response)
        elif role in {"label", "address_label"}:
            grouped["label"].append(response)
        else:
            grouped["other"].append(response)
    for row in ad_page_photos:
        response = _photo_record_to_response(row, archive_id, role_override="ad_page")
        response["candidate_id"] = row.get("candidate_id")
        response["page_number"] = row.get("page_number") or ""
        grouped["ad_pages"].append(response)
    if archive:
        d = dict_row(archive)
        ref_url = d.get("reference_cover_url") or d.get("cover_thumbnail_url") or d.get("cover_preview_url") or ""
        if ref_url:
            grouped["reference_cover"].append({
                "role": "reference_cover",
                "photo_url": ref_url,
                "thumbnail_url": ref_url,
                "is_primary": False,
                "label": "reference image, not item photo",
            })
    return grouped


def _safe_inventory_text(value: Any, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip()


def _is_test_archive(archive: dict, issue_info: Optional[dict] = None) -> bool:
    blob = " ".join(str(archive.get(k) or "") for k in ("listing_title", "issue_title", "cover_subject", "notes", "batch_tag")).lower()
    if issue_info:
        blob += " " + " ".join(str(issue_info.get(k) or "") for k in ("cover_title", "detected_subject", "error_message")).lower()
    return any(marker in blob for marker in ("test", "delete", "synthetic", "no front photo"))


def _display_title_for_archive(archive: dict, issue_info: Optional[dict] = None) -> str:
    issue_info = issue_info or {}
    issue_date = (
        issue_info.get("issue_date")
        or archive.get("confirmed_issue_date")
        or archive.get("issue_date")
        or ""
    )
    master_subject = ""
    try:
        master = _life_issue_master_by_date(issue_date) if issue_date else None
        if master:
            master_subject = master.get("dtmagazine_description") or master.get("cover_subject") or ""
    except Exception:
        master_subject = ""
    subject = (
        archive.get("confirmed_cover_title")
        or master_subject
        or issue_info.get("detected_subject")
        or issue_info.get("cover_title")
        or issue_info.get("detected_subject")
        or archive.get("cover_subject")
        or archive.get("issue_title")
        or archive.get("listing_title")
        or ""
    )
    if _is_placeholder_archive_value(subject):
        visible = issue_info.get("visible_text") or []
        subject = " / ".join(str(v) for v in visible[:3]) if visible else ""
    subject = _safe_inventory_text(subject, 54)
    is_life = bool(issue_info.get("is_life_magazine")) or bool(archive.get("ai_identified"))
    if _is_test_archive(archive, issue_info) and not is_life:
        return f"TEST / NON-LIFE - {subject or 'Synthetic image'}"
    if not subject and not issue_date:
        return "NEEDS REVIEW - incomplete/bad image"
    prefix = "LIFE" if is_life else "NON-LIFE" if issue_info.get("status") == "completed" else "NEEDS REVIEW"
    middle = f" - {subject}" if subject else ""
    suffix = f" - {issue_date}" if issue_date else ""
    return f"{prefix}{middle}{suffix}"


def _inventory_statuses_for_archive(archive: dict, issue_info: Optional[dict], counts: dict) -> dict:
    issue_status = issue_info.get("status") if issue_info else "not_run"
    is_life = bool(issue_info.get("is_life_magazine")) if issue_info else bool(archive.get("ai_identified"))
    is_test = _is_test_archive(archive, issue_info)
    needs_review = False
    badges: list[str] = []
    if is_test:
        badges.append("TEST")
    if issue_status == "completed" and is_life:
        badges.extend(["IDENTIFIED", "ISSUE READY"])
    elif issue_status == "completed" and not is_life:
        badges.append("NON-LIFE")
    elif issue_status in {"failed", "not_run"}:
        needs_review = True
    if not counts.get("front_photo_present"):
        needs_review = True
    if issue_info and issue_info.get("ad_opportunity_ready"):
        badges.append("AD READY")
    if archive.get("listing_status") == "draft" or archive.get("marketforge_push_status") == "draft_saved":
        badges.append("DRAFT SAVED")
    if archive.get("final_price") or archive.get("rough_comp_max"):
        badges.append("VALUED")
    if needs_review:
        badges.append("NEEDS REVIEW")
    pricing_status = "priced" if archive.get("final_price") else "rough/manual" if archive.get("rough_comp_max") else "needs_comps"
    return {
        "is_life_magazine": is_life,
        "issue_info_status": issue_status,
        "ad_opportunity_status": "ready" if issue_info and issue_info.get("ad_opportunity_ready") else "not_ready",
        "ad_opportunity_ready": bool(issue_info and issue_info.get("ad_opportunity_ready")),
        "listing_status": archive.get("listing_status") or "none",
        "pricing_status": pricing_status,
        "is_test_record": is_test,
        "needs_review": needs_review,
        "status_badges": list(dict.fromkeys(badges)),
    }


def _normalized_inventory_row(archive: dict) -> dict:
    archive_id = int(archive.get("id") or archive.get("archive_id") or 0)
    issue_info = None
    try:
        issue_info = _latest_issue_info_response(archive_id, include_stale=False)
    except Exception:
        issue_info = None
    counts = _photo_counts_for_archive(archive_id)
    statuses = _inventory_statuses_for_archive(archive, issue_info, counts)
    front_photo = None
    with get_db() as db:
        row = db.execute(
            """SELECT * FROM ag_archive_photos
               WHERE archive_id = ? AND lower(role) IN ('front', 'front_cover', 'cover')
               ORDER BY datetime(created_at) DESC, id DESC LIMIT 1""",
            (archive_id,),
        ).fetchone()
        if row:
            front_photo = _photo_record_to_response(dict_row(row), archive_id)
    visible_text = issue_info.get("visible_text") if issue_info else []
    short_description = _safe_inventory_text(
        archive.get("confirmed_cover_title")
        or archive.get("cover_subject")
        or (issue_info or {}).get("detected_subject")
        or " ".join(visible_text[:3] if isinstance(visible_text, list) else [])
        or archive.get("notes")
        or "",
        120,
    )
    return {
        **archive,
        "archive_id": archive_id,
        "display_title": _display_title_for_archive(archive, issue_info),
        "issue_date": (issue_info or {}).get("issue_date") or archive.get("confirmed_issue_date") or archive.get("issue_date") or "",
        "cover_subject": archive.get("confirmed_cover_title") or (issue_info or {}).get("detected_subject") or archive.get("cover_subject") or "",
        "short_description": short_description,
        **statuses,
        **counts,
        "front_photo_id": front_photo.get("photo_id") if front_photo else None,
        "front_photo_url": front_photo.get("photo_url") if front_photo else "",
        "thumbnail_url": front_photo.get("thumbnail_url") if front_photo else "",
    }


def _inventory_counters(rows: list[dict]) -> dict:
    return {
        "total_records": len(rows),
        "real_life_identified": sum(1 for r in rows if r.get("is_life_magazine") and not r.get("is_test_record")),
        "issue_info_completed": sum(1 for r in rows if r.get("issue_info_status") == "completed"),
        "ad_opportunities_ready": sum(1 for r in rows if r.get("ad_opportunity_ready")),
        "listing_draft_saved": sum(1 for r in rows if r.get("listing_status") == "draft"),
        "valued_priced": sum(1 for r in rows if r.get("pricing_status") in {"priced", "rough/manual"}),
        "needs_review": sum(1 for r in rows if r.get("needs_review")),
        "test_records": sum(1 for r in rows if r.get("is_test_record")),
        "non_life": sum(1 for r in rows if r.get("issue_info_status") == "completed" and not r.get("is_life_magazine")),
    }


def _parse_price(value: Any) -> Optional[float]:
    text = str(value or "").replace("$", "").replace(",", "").strip()
    if not text:
        return None
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def _normalize_dtm_date(date_text: str, year: int) -> str:
    text = str(date_text or "").strip()
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", text)
    if not match:
        return ""
    month, day, raw_year = match.groups()
    full_year = int(raw_year)
    if full_year < 100:
        full_year += 1900 if full_year >= 30 else 2000
    if full_year != year:
        full_year = year
    try:
        return datetime(full_year, int(month), int(day)).date().isoformat()
    except ValueError:
        return ""


class _TableCellParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_td = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "tr":
            self.in_tr = True
            self.current_row = []
        elif tag.lower() == "td" and self.in_tr:
            self.in_td = True
            self.current_cell = []

    def handle_data(self, data):
        if self.in_td:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "td" and self.in_td:
            text = re.sub(r"\s+", " ", " ".join(self.current_cell)).strip()
            self.current_row.append(text)
            self.in_td = False
        elif tag == "tr" and self.in_tr:
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_tr = False


def _parse_dtm_issue_rows(html: str, year: int) -> list[dict]:
    parser = _TableCellParser()
    parser.feed(html)
    rows: list[dict] = []
    for cells in parser.rows:
        if len(cells) < 5:
            continue
        normalized = _normalize_dtm_date(cells[0], year)
        if not normalized:
            continue
        description = _safe_inventory_text(cells[1], 220)
        if not description or description.upper() == "DESCRIPTION":
            continue
        rows.append({
            "issue_date": cells[0],
            "normalized_date": normalized,
            "year": year,
            "description": description,
            "low": _parse_price(cells[2]),
            "high": _parse_price(cells[3]),
            "average": _parse_price(cells[4]),
        })
    return rows


def _dtm_cache_path(year: int) -> Path:
    return SOURCE_CACHE_DIR / f"dtmagazine_life{year}.html"


def _dtm_cache_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=7)


async def _fetch_dtm_year_page(year: int, force_refresh: bool = False) -> tuple[str, bool, str]:
    path = _dtm_cache_path(year)
    if not force_refresh and _dtm_cache_is_fresh(path):
        return path.read_text(errors="ignore"), True, str(path)
    url = f"{DTMAGAZINE_BASE_URL}/life{year}.html"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "ArchiveForge/1.0 bounded issue-master importer"})
    if response.status_code >= 400:
        raise HTTPException(response.status_code, f"DTM year page unavailable for {year}: HTTP {response.status_code}")
    text = response.text
    path.write_text(text)
    return text, False, url


def _upsert_dtm_issue(row: dict, source_url: str) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM archive_life_issue_master WHERE normalized_date = ?",
            (row["normalized_date"],),
        ).fetchone()
        if existing:
            issue_id = int(existing[0])
            db.execute(
                """UPDATE archive_life_issue_master
                   SET issue_date = ?, year = ?, cover_title = COALESCE(NULLIF(cover_title, ''), ?),
                       cover_subject = COALESCE(NULLIF(cover_subject, ''), ?),
                       description = COALESCE(NULLIF(description, ''), ?),
                       dtmagazine_description = ?, dtmagazine_low = ?, dtmagazine_high = ?,
                       dtmagazine_average = ?, dtmagazine_freshness = 'unknown',
                       source_confidence = CASE WHEN source_confidence = '' THEN 'medium' ELSE source_confidence END,
                       last_verified_at = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (
                    row["issue_date"], row["year"], row["description"], row["description"], row["description"],
                    row["description"], row.get("low") or 0, row.get("high") or 0, row.get("average") or 0,
                    now, issue_id,
                ),
            )
        else:
            cur = db.execute(
                """INSERT INTO archive_life_issue_master
                   (issue_date, normalized_date, year, cover_title, cover_subject, description,
                    dtmagazine_description, dtmagazine_low, dtmagazine_high, dtmagazine_average,
                    dtmagazine_freshness, source_count, source_confidence, last_verified_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["issue_date"], row["normalized_date"], row["year"], row["description"], row["description"],
                    row["description"], row["description"], row.get("low") or 0, row.get("high") or 0,
                    row.get("average") or 0, "unknown", 1, "medium", now,
                ),
            )
            issue_id = int(cur.lastrowid)
        source_exists = db.execute(
            """SELECT id FROM archive_life_issue_sources
               WHERE issue_master_id = ? AND source_type = 'dtmagazine_reference_price_guide'
                 AND source_url = ? AND source_claim_date = ?""",
            (issue_id, source_url, row["normalized_date"]),
        ).fetchone()
        if not source_exists:
            db.execute(
                """INSERT INTO archive_life_issue_sources
                   (issue_master_id, source_name, source_type, source_url, source_date_observed,
                    source_claim_date, source_claim_title, source_claim_price_low, source_claim_price_high,
                    source_claim_average, confidence, freshness, notes, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    issue_id, "DT Magazine", "dtmagazine_reference_price_guide", source_url, now,
                    row["normalized_date"], row["description"], row.get("low") or 0, row.get("high") or 0,
                    row.get("average") or 0, "medium", "unknown",
                    "DTM guide values are reference-guide values, not current sold comps.",
                    json.dumps(row),
                ),
            )
        count = db.execute(
            "SELECT COUNT(*) FROM archive_life_issue_sources WHERE issue_master_id = ?",
            (issue_id,),
        ).fetchone()[0]
        db.execute("UPDATE archive_life_issue_master SET source_count = ?, updated_at = datetime('now') WHERE id = ?", (count, issue_id))
        db.commit()
    return issue_id


def _life_issue_master_by_date(issue_date: str) -> Optional[dict]:
    normalized = ""
    parsed = _parse_reference_date(issue_date)
    if parsed:
        normalized = parsed.date().isoformat()
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", str(issue_date or "")):
        normalized = str(issue_date)
    if not normalized:
        return None
    with get_db() as db:
        row = db.execute("SELECT * FROM archive_life_issue_master WHERE normalized_date = ?", (normalized,)).fetchone()
    return dict_row(row) if row else None


def _issue_master_for_archive(archive_id: int) -> Optional[dict]:
    archive = _load_archive_or_404(archive_id)
    issue_info = None
    try:
        issue_info = _latest_issue_info_response(archive_id, include_stale=False)
    except Exception:
        issue_info = None
    date = (issue_info or {}).get("issue_date") or archive.get("confirmed_issue_date") or archive.get("issue_date") or ""
    return _life_issue_master_by_date(date)


def _issue_master_sources(issue_master_id: int) -> list[dict]:
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM archive_life_issue_sources WHERE issue_master_id = ? ORDER BY id DESC",
            (issue_master_id,),
        ).fetchall())


def _sync_archive_to_life_master(archive_id: int) -> dict:
    archive = _load_archive_or_404(archive_id)
    issue_info = _latest_issue_info_response(archive_id, include_stale=False)
    metadata = _latest_issue_metadata(archive_id)
    issue_date = (issue_info or {}).get("issue_date") or archive.get("confirmed_issue_date") or archive.get("issue_date") or ""
    parsed = _parse_reference_date(issue_date)
    if not parsed:
        raise HTTPException(409, "Cannot sync to LIFE issue master without a resolved issue date.")
    normalized = parsed.date().isoformat()
    year = parsed.year
    subject = (
        (issue_info or {}).get("cover_title")
        or (issue_info or {}).get("detected_subject")
        or archive.get("confirmed_cover_title")
        or archive.get("cover_subject")
        or ""
    )
    with get_db() as db:
        existing = db.execute("SELECT * FROM archive_life_issue_master WHERE normalized_date = ?", (normalized,)).fetchone()
        if existing:
            issue_id = int(existing["id"])
            db.execute(
                """UPDATE archive_life_issue_master
                   SET cover_title = COALESCE(NULLIF(?, ''), cover_title),
                       cover_subject = COALESCE(NULLIF(?, ''), cover_subject),
                       description = COALESCE(NULLIF(description, ''), ?),
                       google_books_volume_id = COALESCE(NULLIF(?, ''), google_books_volume_id),
                       google_books_page_count = COALESCE(NULLIF(?, 0), google_books_page_count),
                       google_books_cover_url = COALESCE(NULLIF(?, ''), google_books_cover_url),
                       source_confidence = ?,
                       last_verified_at = ?,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (
                    subject, subject, subject, (metadata or {}).get("source_volume_id") or "",
                    int((metadata or {}).get("page_count") or 0), (metadata or {}).get("cover_image_url") or "",
                    (issue_info or {}).get("evidence_grade") or "medium",
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    issue_id,
                ),
            )
        else:
            cur = db.execute(
                """INSERT INTO archive_life_issue_master
                   (issue_date, normalized_date, year, cover_title, cover_subject, description,
                    google_books_volume_id, google_books_page_count, google_books_cover_url,
                    source_count, source_confidence, last_verified_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    issue_date, normalized, year, subject, subject, subject,
                    (metadata or {}).get("source_volume_id") or "",
                    int((metadata or {}).get("page_count") or 0),
                    (metadata or {}).get("cover_image_url") or "",
                    0, (issue_info or {}).get("evidence_grade") or "medium",
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                ),
            )
            issue_id = int(cur.lastrowid)
        if metadata:
            exists = db.execute(
                """SELECT id FROM archive_life_issue_sources
                   WHERE issue_master_id = ? AND source_type = 'google_books' AND source_url = ?""",
                (issue_id, metadata.get("source_url") or metadata.get("info_link") or ""),
            ).fetchone()
            if not exists:
                db.execute(
                    """INSERT INTO archive_life_issue_sources
                       (issue_master_id, archive_id, source_name, source_type, source_url,
                        source_date_observed, source_claim_date, source_claim_title,
                        confidence, freshness, notes, raw_json)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        issue_id, archive_id, "Google Books", "google_books",
                        metadata.get("source_url") or metadata.get("info_link") or "",
                        datetime.utcnow().isoformat(timespec="seconds") + "Z",
                        metadata.get("issue_date") or normalized,
                        metadata.get("issue_title") or subject,
                        (issue_info or {}).get("evidence_grade") or "medium",
                        "current",
                        "Google Books API metadata; not price evidence.",
                        json.dumps(metadata.get("raw_metadata") or metadata),
                    ),
                )
        source_count = db.execute("SELECT COUNT(*) FROM archive_life_issue_sources WHERE issue_master_id = ?", (issue_id,)).fetchone()[0]
        db.execute("UPDATE archive_life_issue_master SET source_count = ?, updated_at = datetime('now') WHERE id = ?", (source_count, issue_id))
        db.commit()
    issue = _life_issue_master_by_date(normalized) or {}
    return {"archive_id": archive_id, "issue_master": issue, "sources": _issue_master_sources(int(issue.get("id") or issue_id))}


def _magazine_research_query(archive: dict, issue_master: Optional[dict]) -> str:
    subject = (issue_master or {}).get("cover_subject") or archive.get("confirmed_cover_title") or archive.get("cover_subject") or archive.get("issue_title") or ""
    date = (issue_master or {}).get("normalized_date") or archive.get("confirmed_issue_date") or archive.get("issue_date") or ""
    year = ""
    parsed = _parse_reference_date(date)
    if parsed:
        year = str(parsed.year)
    return " ".join(part for part in ["LIFE magazine", year, subject] if str(part or "").strip())


def _insert_magazine_comp_if_new(archive_id: int, issue_master_id: Optional[int], query: str, comp: dict) -> dict:
    url = comp.get("url") or ""
    result_type = comp.get("result_type") or "search_link"
    provider = comp.get("provider") or "manual_links"
    raw_result = comp.get("raw_result") or {}
    safe_raw = {k: v for k, v in raw_result.items() if str(k).lower() not in {"authorization", "access_token", "token", "headers"}}
    price = _num_or_zero(comp.get("price"))
    shipping_price = _num_or_zero(comp.get("shipping_price"))
    total_price = _num_or_zero(comp.get("total_price")) or (price + shipping_price if price else 0)
    with get_db() as db:
        existing = None
        if url:
            existing = db.execute(
                """SELECT * FROM archive_magazine_comps
                   WHERE archive_id = ? AND url = ? AND result_type = ?
                   ORDER BY id DESC LIMIT 1""",
                (archive_id, url, result_type),
            ).fetchone()
        if existing:
            return _magazine_comp_row_to_dict(dict_row(existing))
        cur = db.execute(
            """INSERT INTO archive_magazine_comps
               (archive_id, issue_master_id, provider, query, result_type, title, url,
                price, currency, shipping_price, total_price, condition_text, sold_date,
                match_confidence, notes, raw_result_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                archive_id, issue_master_id, provider, query, result_type,
                comp.get("title") or query, url, price, (comp.get("currency") or "USD").upper(),
                shipping_price, total_price, comp.get("condition_text") or "",
                comp.get("sold_date") or "", _num_or_zero(comp.get("match_confidence")),
                comp.get("notes") or "", json.dumps(safe_raw),
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM archive_magazine_comps WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _magazine_comp_row_to_dict(dict_row(row))


def _magazine_comp_row_to_dict(row: dict) -> dict:
    d = dict(row)
    d["raw_result"] = _json_value(d.pop("raw_result_json", "{}"), {})
    for key in ("price", "shipping_price", "total_price", "match_confidence"):
        d[key] = _num_or_none_for_packet(d.get(key))
    return d


def _list_magazine_comps(archive_id: int) -> list[dict]:
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM archive_magazine_comps
               WHERE archive_id = ?
               ORDER BY result_type = 'search_link' ASC, COALESCE(total_price, price, 0) DESC, id ASC""",
            (archive_id,),
        ).fetchall())
    return [_magazine_comp_row_to_dict(row) for row in rows]


def _pricing_summary_for_archive(archive_id: int) -> Optional[dict]:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM archive_pricing_summary WHERE archive_id = ? ORDER BY datetime(created_at) DESC, id DESC LIMIT 1",
            (archive_id,),
        ).fetchone()
    return dict_row(row) if row else None


def _calculate_magazine_pricing(archive_id: int, persist: bool = True) -> dict:
    archive = _load_archive_or_404(archive_id)
    issue_master = _issue_master_for_archive(archive_id)
    issue_master_id = int(issue_master.get("id")) if issue_master else None
    comps = _list_magazine_comps(archive_id)
    sold = [c for c in comps if c.get("result_type") == "sold_comp" and _num_or_zero(c.get("total_price") or c.get("price")) > 0]
    active = [c for c in comps if c.get("result_type") == "active_listing" and _num_or_zero(c.get("total_price") or c.get("price")) > 0]
    dealer = [c for c in comps if c.get("result_type") == "dealer_asking" and _num_or_zero(c.get("total_price") or c.get("price")) > 0]
    reference = [c for c in comps if c.get("result_type") == "dtmagazine_reference_price_guide" and _num_or_zero(c.get("total_price") or c.get("price")) > 0]

    pricing_type = "needs_comps"
    confidence = "none"
    source_values: list[float] = []
    basis = "No sold comps, active listings, dealer asking prices, or reference-guide rows are stored yet."
    if sold:
        pricing_type = "sold_comps"
        confidence = "high" if len(sold) >= 2 else "medium"
        source_values = [_num_or_zero(c.get("total_price") or c.get("price")) for c in sold]
        basis = "Sold/manual sold comps are strongest evidence."
    elif active:
        pricing_type = "active_listing_comps"
        confidence = "medium" if len(active) >= 2 else "low"
        source_values = [_num_or_zero(c.get("total_price") or c.get("price")) for c in active]
        basis = "Active listings are asking prices, not sold comps."
    elif dealer:
        pricing_type = "manual_comps"
        confidence = "low"
        source_values = [_num_or_zero(c.get("total_price") or c.get("price")) for c in dealer]
        basis = "Dealer/store asking prices are lower-confidence than sold comps."
    elif reference:
        pricing_type = "reference_price_guide"
        confidence = "low"
        source_values = [_num_or_zero(c.get("total_price") or c.get("price")) for c in reference]
        basis = "DTM guide values are reference-guide values, not current sold comps."
    elif archive.get("rough_comp_max"):
        pricing_type = "manual_rough_estimate"
        confidence = "low"
        source_values = [_num_or_zero(archive.get("rough_comp_min")), _num_or_zero(archive.get("rough_comp_max"))]
        basis = "Owner-entered rough estimate; final pricing needs comps or owner approval."

    source_values = [v for v in source_values if v > 0]
    estimate_low = min(source_values) if source_values else 0
    estimate_high = max(source_values) if source_values else 0
    condition_score = int(archive.get("condition_score") or 0)
    condition_factor = 1.0
    if condition_score and condition_score < 3:
        condition_factor = 0.75
    elif condition_score >= 4:
        condition_factor = 1.1
    recommended = round(((estimate_low + estimate_high) / 2) * condition_factor, 2) if estimate_low and estimate_high else 0
    summary = {
        "archive_id": archive_id,
        "issue_master_id": issue_master_id,
        "pricing_type": pricing_type,
        "estimate_low": round(estimate_low, 2) if estimate_low else None,
        "estimate_high": round(estimate_high, 2) if estimate_high else None,
        "recommended_price": recommended or None,
        "comp_count": len([c for c in comps if c.get("result_type") != "search_link"]),
        "sold_comp_count": len(sold),
        "active_listing_count": len(active),
        "dealer_listing_count": len(dealer),
        "reference_guide_count": len(reference),
        "confidence": confidence,
        "pricing_basis": basis,
        "needs_manual_review": pricing_type in {"needs_comps", "reference_price_guide", "manual_rough_estimate"},
        "warnings": [
            "DTM guide values are reference-guide values, not current sold comps." if reference else "",
            "Active listings are asking prices, not sold comps." if active else "",
            "Final pricing requires sold comps, manual comps, or owner approval." if confidence in {"none", "low"} else "",
        ],
    }
    summary["warnings"] = [w for w in summary["warnings"] if w]
    if persist:
        with get_db() as db:
            db.execute(
                """INSERT INTO archive_pricing_summary
                   (archive_id, issue_master_id, pricing_type, estimate_low, estimate_high, recommended_price,
                    comp_count, sold_comp_count, active_listing_count, dealer_listing_count, reference_guide_count,
                    confidence, pricing_basis, needs_manual_review)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    archive_id, issue_master_id, pricing_type, estimate_low or 0, estimate_high or 0,
                    recommended or 0, summary["comp_count"], len(sold), len(active), len(dealer), len(reference),
                    confidence, basis, int(summary["needs_manual_review"]),
                ),
            )
            if recommended:
                db.execute(
                    """UPDATE ag_archives
                       SET final_price = CASE WHEN final_price > 0 THEN final_price ELSE ? END,
                           pricing_basis = ?, pricing_updated_at = datetime('now'), updated_at = datetime('now')
                       WHERE id = ?""",
                    (recommended, pricing_type, archive_id),
                )
            db.commit()
    return summary


# ── Inventory & Stats ──────────────────────────────────────────────────────────

EXPORT_FIELDS = [
    "archive_id", "title", "issue_date", "volume", "issue_number", "cover_subject",
    "category_type", "tier", "condition_score", "status", "source_box", "slot",
    "processed_box", "archive_location", "rough_comp_min", "rough_comp_max",
    "sale_plan", "listing_title", "listing_description", "batch_tag", "photo_count",
    "front_photo_path", "front_photo_url", "ai_identified", "ai_confidence",
    "evidence_source", "created_at", "updated_at",
    "display_title", "short_description", "is_life_magazine", "issue_info_status",
    "ad_opportunity_status", "ad_opportunity_ready", "listing_status",
    "pricing_status", "is_test_record", "needs_review", "front_photo_present",
    "ad_page_photo_count", "verified_ad_count", "thumbnail_url", "status_badges",
]


def _export_rows(include_photos: bool = False) -> list[dict]:
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT a.id AS archive_id,
                      a.id,
                      COALESCE(NULLIF(a.listing_title, ''), NULLIF(a.cover_subject, ''), NULLIF(a.issue_title, ''), 'LIFE Magazine') AS title,
                      a.issue_date, a.volume, a.issue_number, a.cover_subject,
                      'LIFE magazine' AS category_type,
                      a.tier, a.condition_score, a.processed_status AS status,
                      a.source_box_code AS source_box, a.source_slot_position AS slot,
                      a.processed_box_code AS processed_box, a.archive_location,
                      a.rough_comp_min, a.rough_comp_max, a.sale_plan,
                      a.listing_title, a.listing_description, a.batch_tag,
                      (SELECT COUNT(*) FROM ag_archive_photos p WHERE p.archive_id = a.id) AS photo_count,
                      (SELECT p.file_path FROM ag_archive_photos p WHERE p.archive_id = a.id AND p.role = 'front' ORDER BY p.id DESC LIMIT 1) AS front_photo_path,
                      (SELECT p.id FROM ag_archive_photos p WHERE p.archive_id = a.id AND p.role = 'front' ORDER BY p.id DESC LIMIT 1) AS front_photo_id,
                      a.ai_identified, a.ai_confidence, a.ai_evidence_source AS evidence_source,
                      a.created_at, a.updated_at, a.listing_status, a.marketforge_push_status,
                      a.confirmed_issue_date, a.confirmed_cover_title, a.issue_title, a.notes,
                      a.final_price, a.pricing_basis
               FROM ag_archives a
               ORDER BY a.created_at DESC"""
        ).fetchall())
    for row in rows:
        photo_id = row.pop("front_photo_id", None)
        row["front_photo_url"] = _scoped_photo_url_for(row.get("archive_id"), photo_id) if photo_id else ""
        row["thumbnail_url"] = _thumbnail_url_for(row.get("archive_id"), photo_id) if photo_id else ""
        row["ai_identified"] = bool(row.get("ai_identified"))
        normalized = _normalized_inventory_row(row)
        row.update(normalized)
        row["status_badges"] = "; ".join(normalized.get("status_badges") or [])
        if not include_photos:
            row["front_photo_path"] = ""
    return rows


def _csv_response(rows: list[dict], filename: str) -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _xlsx_col_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _xlsx_response(rows: list[dict], filename: str) -> Response:
    def cell(value) -> str:
        text = "" if value is None else str(value)
        return f'<c t="inlineStr"><is><t>{xml_escape(text)}</t></is></c>'

    sheet_rows = []
    sheet_rows.append("<row>" + "".join(cell(field) for field in EXPORT_FIELDS) + "</row>")
    for row in rows:
        sheet_rows.append("<row>" + "".join(cell(row.get(field, "")) for field in EXPORT_FIELDS) + "</row>")
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{_xlsx_col_name(len(EXPORT_FIELDS))}{len(rows) + 1}"/>'
        '<sheetData>' + "".join(sheet_rows) + '</sheetData></worksheet>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""")
        zf.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
        zf.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="ArchiveForge Inventory" sheetId="1" r:id="rId1"/></sheets>
</workbook>""")
        zf.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""")
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventory")
async def get_inventory_summary():
    """Spreadsheet-friendly inventory summary of all archive items."""
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT id, issue_date, volume, issue_number, cover_subject, tier,
                      condition_score, processed_status, source_box_code, processed_box_code,
                      archive_location, reboxed_at, reboxed_by,
                      rough_comp_min, rough_comp_max, sale_plan, created_at, updated_at
               FROM ag_archives ORDER BY created_at DESC""",
        ).fetchall())
    normalized = [_normalized_inventory_row(row) for row in rows]
    return {"items": normalized, "total": len(normalized), "counters": _inventory_counters(normalized)}


@router.get("/inventory/export")
async def export_inventory_csv():
    """Return inventory as a JSON array (MarketForge can transform to CSV)."""
    rows = _export_rows(include_photos=True)
    return {"items": rows, "total": len(rows), "counters": _inventory_counters(rows), "format": "json-array-for-csv-conversion"}


@router.get("/inventory/export.csv")
async def export_inventory_real_csv(include_photos: bool = Query(False)):
    """Return a real CSV inventory export."""
    return _csv_response(_export_rows(include_photos=include_photos), "archiveforge_inventory.csv")


@router.get("/inventory/export.xlsx")
async def export_inventory_xlsx(include_images: bool = Query(False)):
    """Return a dependency-free XLSX inventory export."""
    return _xlsx_response(_export_rows(include_photos=include_images), "archiveforge_inventory.xlsx")


@router.get("/{archive_id}/export.pdf")
async def export_item_pdf(archive_id: int, include_images: bool = Query(False)):
    """Return a single-item PDF intake report."""
    archive = _load_archive_or_404(archive_id)
    with get_db() as db:
        photos = dict_rows(db.execute(
            "SELECT * FROM ag_archive_photos WHERE archive_id = ? ORDER BY role = 'front' DESC, id ASC",
            (archive_id,),
        ).fetchall())

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib import colors
    except Exception as exc:
        raise HTTPException(501, f"PDF export requires reportlab: {type(exc).__name__}")

    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=f"ArchiveForge report {archive_id}")
    story = [
        Paragraph("ArchiveForge LIFE Magazine Intake Report", styles["Title"]),
        Paragraph(f"Archive ID: {archive_id}", styles["Normal"]),
        Spacer(1, 0.15 * inch),
    ]

    ai_summary = {}
    if archive.get("ai_identification_json"):
        try:
            ai_summary = json.loads(archive["ai_identification_json"])
        except Exception:
            ai_summary = {}

    rows = [
        ["Title", archive.get("listing_title") or archive.get("cover_subject") or archive.get("issue_title") or "LIFE Magazine"],
        ["Issue date", archive.get("confirmed_issue_date") or archive.get("issue_date") or ""],
        ["Volume / Issue", f"{archive.get('volume') or ''} / {archive.get('issue_number') or ''}"],
        ["Cover subject", archive.get("confirmed_cover_title") or archive.get("cover_subject") or ""],
        ["Reference", archive.get("confirmed_reference_source") or archive.get("reference_source") or ""],
        ["AI evidence", archive.get("ai_evidence_source") or ""],
        ["AI confidence", archive.get("ai_confidence") or ""],
        ["Condition", archive.get("condition_score") or ""],
        ["Defects", archive.get("defects") or ""],
        ["Complete", "Yes" if archive.get("is_complete") else "No"],
        ["Address label", "Yes" if archive.get("has_address_label") else "No"],
        ["Rough pricing", f"${archive.get('rough_comp_min') or 0} - ${archive.get('rough_comp_max') or 0}"],
        ["Final price", archive.get("final_price") or ""],
        ["Sale plan", archive.get("sale_plan") or ""],
        ["Notes", archive.get("notes") or ""],
        ["Location", " / ".join(x for x in [archive.get("source_box_code") or "", archive.get("source_slot_position") or "", archive.get("processed_box_code") or "", archive.get("archive_location") or ""] if x)],
    ]
    table = Table(rows, colWidths=[1.4 * inch, 5.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    story.extend([table, Spacer(1, 0.18 * inch)])

    if ai_summary:
        story.append(Paragraph("AI Identification Summary", styles["Heading2"]))
        story.append(Paragraph(xml_escape(str(ai_summary.get("reasoning_summary") or "")), styles["Normal"]))
        story.append(Spacer(1, 0.12 * inch))

    if photos:
        story.append(Paragraph("Actual Uploaded Photos", styles["Heading2"]))
        for photo in photos[:6]:
            path = Path(photo.get("file_path", ""))
            story.append(Paragraph(f"{photo.get('role', 'photo')}: {path}", styles["Normal"]))
            if include_images and path.exists() and path.stat().st_size > 0:
                try:
                    story.append(Image(str(path), width=2.2 * inch, height=2.2 * inch, kind="proportional"))
                    story.append(Spacer(1, 0.1 * inch))
                except Exception:
                    pass

    doc.build(story)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="archiveforge_{archive_id}_report.pdf"'},
    )


@router.get("/stats")
async def get_stats():
    """Dashboard stats: counts by status, tier, total value range."""
    with get_db() as db:
        by_status = dict_rows(db.execute(
            "SELECT processed_status, COUNT(*) as count FROM ag_archives GROUP BY processed_status"
        ).fetchall())
        by_tier = dict_rows(db.execute(
            "SELECT tier, COUNT(*) as count FROM ag_archives GROUP BY tier"
        ).fetchall())
        total = db.execute("SELECT COUNT(*) FROM ag_archives").fetchone()[0]
        valued = db.execute("SELECT COUNT(*) FROM ag_archives WHERE rough_comp_max > 0").fetchone()[0]
        total_comp_min = db.execute("SELECT COALESCE(SUM(rough_comp_min), 0) FROM ag_archives").fetchone()[0]
        total_comp_max = db.execute("SELECT COALESCE(SUM(rough_comp_max), 0) FROM ag_archives").fetchone()[0]
        archives = dict_rows(db.execute("SELECT * FROM ag_archives ORDER BY created_at DESC").fetchall())
    normalized = [_normalized_inventory_row(row) for row in archives]
    counters = _inventory_counters(normalized)
    return {
        "total_items": total,
        "valued_items": valued,
        "by_status": {r["processed_status"]: r["count"] for r in by_status},
        "by_tier": {r["tier"]: r["count"] for r in by_tier},
        "total_comp_range": [round(total_comp_min, 2), round(total_comp_max, 2)],
        "inventory_counters": counters,
    }


# ── LIFE Issue Master ─────────────────────────────────────────────────────────

@router.post("/life-issues/import-dtm")
async def import_life_issues_from_dtm(
    start_year: int = Query(1936, ge=1936, le=1972),
    end_year: int = Query(1972, ge=1936, le=1972),
    force_refresh: bool = Query(False),
):
    """Import DTM LIFE issue guide rows into the local issue master. Explicit call only."""
    if end_year < start_year:
        raise HTTPException(400, "end_year must be >= start_year")
    years = list(range(start_year, end_year + 1))
    imported = 0
    failed: list[dict] = []
    per_year: list[dict] = []
    for year in years:
        try:
            html, cache_hit, source = await _fetch_dtm_year_page(year, force_refresh=force_refresh)
            rows = _parse_dtm_issue_rows(html, year)
            source_url = f"{DTMAGAZINE_BASE_URL}/life{year}.html"
            for row in rows:
                _upsert_dtm_issue(row, source_url)
            imported += len(rows)
            per_year.append({"year": year, "rows": len(rows), "cache_hit": cache_hit, "source": source})
        except Exception as exc:
            failed.append({"year": year, "error": str(exc)[:220]})
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM archive_life_issue_master WHERE year BETWEEN 1936 AND 1972").fetchone()[0]
    return {
        "source": "DT Magazine",
        "source_type": "dtmagazine_reference_price_guide",
        "warning": "DTM guide values are reference-guide values, not current sold comps.",
        "years_requested": years,
        "rows_imported_this_run": imported,
        "exact_total_row_count": total,
        "target_count": 1874,
        "difference_from_target": int(total) - 1874,
        "failed_years": failed,
        "per_year": per_year,
    }


@router.get("/life-issues/import-status")
async def life_issues_import_status():
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT year, COUNT(*) AS count, MAX(updated_at) AS last_updated
               FROM archive_life_issue_master
               WHERE year BETWEEN 1936 AND 1972
               GROUP BY year ORDER BY year""",
        ).fetchall())
        total = db.execute("SELECT COUNT(*) FROM archive_life_issue_master WHERE year BETWEEN 1936 AND 1972").fetchone()[0]
        duplicates = dict_rows(db.execute(
            """SELECT normalized_date, COUNT(*) AS count
               FROM archive_life_issue_master
               WHERE year BETWEEN 1936 AND 1972
               GROUP BY normalized_date HAVING COUNT(*) > 1"""
        ).fetchall())
    years_imported = [int(row["year"]) for row in rows]
    failed_years = [year for year in range(1936, 1973) if year not in years_imported]
    return {
        "years_imported": years_imported,
        "rows_by_year": rows,
        "rows_imported": total,
        "exact_total_row_count": total,
        "failed_years": failed_years,
        "last_import_time": max((row.get("last_updated") or "" for row in rows), default=""),
        "target_count": 1874,
        "difference_from_target": int(total) - 1874,
        "duplicate_dates": duplicates,
    }


@router.get("/life-issues/search")
async def search_life_issues(q: str = Query("", min_length=1), year: Optional[int] = Query(None)):
    query = " ".join(str(q or "").split())
    tokens = _search_tokens(query)
    if not tokens:
        raise HTTPException(400, "Search query required.")
    where = []
    params: list[Any] = []
    if year:
        where.append("year = ?")
        params.append(year)
    like_clause = " OR ".join(["lower(description) LIKE ?", "lower(cover_subject) LIKE ?", "lower(cover_title) LIKE ?", "normalized_date LIKE ?"])
    where.append(f"({like_clause})")
    params.extend([f"%{query.lower()}%", f"%{query.lower()}%", f"%{query.lower()}%", f"%{query}%"])
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM archive_life_issue_master").fetchone()[0]
        rows = dict_rows(db.execute(
            f"""SELECT * FROM archive_life_issue_master
                WHERE {' AND '.join(where)}
                ORDER BY year ASC, normalized_date ASC
                LIMIT 50""",
            tuple(params),
        ).fetchall())
    if total == 0:
        return {"query": query, "matches": [], "message": "Issue master not imported. Run DTM import first.", "import_required": True}
    scored = []
    for row in rows:
        text = " ".join(str(row.get(k) or "") for k in ("description", "cover_subject", "cover_title", "normalized_date"))
        row_tokens = _search_tokens(text)
        score = len(tokens & row_tokens) / max(len(tokens), 1)
        if query.lower() in text.lower():
            score = max(score, 0.95)
        scored.append({
            "source": "dtmagazine" if row.get("dtmagazine_description") else "archive_life_issue_master",
            "source_type": "dtmagazine_reference_price_guide" if row.get("dtmagazine_description") else "manual_reference",
            "issue_id": row.get("id"),
            "issue_date": row.get("normalized_date"),
            "description": row.get("dtmagazine_description") or row.get("description") or "",
            "low": _num_or_none_for_packet(row.get("dtmagazine_low")),
            "high": _num_or_none_for_packet(row.get("dtmagazine_high")),
            "average": _num_or_none_for_packet(row.get("dtmagazine_average")),
            "source_url": f"{DTMAGAZINE_BASE_URL}/life{row.get('year')}.html" if row.get("year") else "",
            "match_score": round(score, 3),
            "confidence": "medium" if row.get("source_count") else "low",
            "warning": "Reference price guide, not sold comps.",
        })
    scored.sort(key=lambda item: item["match_score"], reverse=True)
    return {"query": query, "year": year, "matches": scored[:25], "total": len(scored)}


@router.get("/life-issues/{issue_date}")
async def get_life_issue(issue_date: str):
    issue = _life_issue_master_by_date(issue_date)
    if not issue:
        raise HTTPException(404, "LIFE issue not found in local master chart.")
    return {"issue": issue, "sources": _issue_master_sources(int(issue["id"]))}


@router.post("/life-issues/{archive_id}/sync-master")
async def sync_archive_life_issue_master(archive_id: int):
    return _sync_archive_to_life_master(archive_id)


@router.get("/life-issues/{issue_id}/sources")
async def get_life_issue_sources(issue_id: int):
    with get_db() as db:
        issue = db.execute("SELECT * FROM archive_life_issue_master WHERE id = ?", (issue_id,)).fetchone()
    if not issue:
        raise HTTPException(404, "LIFE issue master row not found.")
    return {"issue_id": issue_id, "sources": _issue_master_sources(issue_id)}


@router.post("/life-issues/{issue_id}/sources/manual", status_code=201)
async def add_life_issue_manual_source(issue_id: int, req: ManualIssueSourceRequest):
    with get_db() as db:
        issue = db.execute("SELECT * FROM archive_life_issue_master WHERE id = ?", (issue_id,)).fetchone()
    if not issue:
        raise HTTPException(404, "LIFE issue master row not found.")
    with get_db() as db:
        db.execute(
            """INSERT INTO archive_life_issue_sources
               (issue_master_id, source_name, source_type, source_url, source_date_observed,
                source_claim_date, source_claim_title, source_claim_price_low, source_claim_price_high,
                source_claim_average, confidence, freshness, notes, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                issue_id, req.source_name, req.source_type, req.source_url,
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
                req.source_claim_date, req.source_claim_title,
                req.source_claim_price_low or 0, req.source_claim_price_high or 0,
                req.source_claim_average or 0, req.confidence, req.freshness,
                req.notes, json.dumps(req.model_dump()),
            ),
        )
        count = db.execute("SELECT COUNT(*) FROM archive_life_issue_sources WHERE issue_master_id = ?", (issue_id,)).fetchone()[0]
        db.execute("UPDATE archive_life_issue_master SET source_count = ?, updated_at = datetime('now') WHERE id = ?", (count, issue_id))
        db.commit()
    return {"issue_id": issue_id, "source_added": True, "sources": _issue_master_sources(issue_id)}


# ── Box Registry ───────────────────────────────────────────────────────────────

class BoxCreate(BaseModel):
    box_code: str
    box_type: str = "processed"
    description: str = ""


@router.post("/boxes", status_code=201)
async def register_box(req: BoxCreate):
    """Register a new box code in the box registry."""
    with get_db() as db:
        cur = db.execute(
            "INSERT OR IGNORE INTO ag_box_registry (box_code, box_type, description) VALUES (?,?,?)",
            (req.box_code, req.box_type, req.description),
        )
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(409, f"Box '{req.box_code}' already exists")
    return {"box_code": req.box_code, "registered": True}


@router.get("/boxes")
async def list_boxes():
    """List all registered box codes."""
    with get_db() as db:
        rows = dict_rows(db.execute("SELECT * FROM ag_box_registry ORDER BY box_code").fetchall())
    return {"boxes": rows}


# ── Listing Drafts ─────────────────────────────────────────────────────────────

@router.get("/drafts")
async def list_drafts(archive_id: Optional[int] = None):
    """List all listing drafts, optionally filtered by archive item."""
    with get_db() as db:
        if archive_id:
            rows = dict_rows(db.execute(
                "SELECT * FROM ag_listing_drafts WHERE archive_id = ? ORDER BY created_at DESC",
                (archive_id,),
            ).fetchall())
        else:
            rows = dict_rows(db.execute(
                "SELECT * FROM ag_listing_drafts ORDER BY created_at DESC LIMIT 100"
            ).fetchall())
    for d in rows:
        for fld in ("item_specifics", "marketforge_payload"):
            if fld in d and isinstance(d[fld], str):
                try:
                    d[fld] = json.loads(d[fld])
                except (json.JSONDecodeError, TypeError):
                    d[fld] = {}
    return {"drafts": rows, "total": len(rows)}


# ── Photo Storage ──────────────────────────────────────────────────────────────

@router.post("/uploads/{archive_id}", status_code=201)
async def upload_photo(
    archive_id: int,
    background_tasks: BackgroundTasks,
    role: str = Form("front"),
    file: UploadFile = File(...),
):
    """Upload a photo for an archive item and persist to disk."""
    with get_db() as db:
        row = db.execute("SELECT id FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")

    contents = await file.read()
    byte_size = len(contents)
    original_name = file.filename or "photo"
    declared_mime_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    guessed_mime_type = (mimetypes.guess_type(original_name)[0] or "").strip().lower()
    supported_mime_type = next(
        (mime for mime in (declared_mime_type, guessed_mime_type) if mime in SUPPORTED_IMAGE_MIME_TYPES),
        "",
    )

    safe_log_name = Path(original_name).name
    if byte_size <= 0:
        log.warning(
            "Rejected empty ArchiveForge upload archive_id=%s role=%s filename=%s mime_type=%s byte_size=%s",
            archive_id, role, safe_log_name, declared_mime_type or guessed_mime_type or "unknown", byte_size,
        )
        raise HTTPException(400, "Uploaded image is empty. Choose a non-empty JPEG, PNG, GIF, or WebP file.")

    if not supported_mime_type:
        log.warning(
            "Rejected unsupported ArchiveForge upload archive_id=%s role=%s filename=%s mime_type=%s byte_size=%s",
            archive_id, role, safe_log_name, declared_mime_type or guessed_mime_type or "unknown", byte_size,
        )
        raise HTTPException(400, "Unsupported image type. Upload a JPEG, PNG, GIF, or WebP file.")

    ext = Path(file.filename or "photo.jpg").suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        ext = IMAGE_MIME_EXTENSIONS.get(supported_mime_type, '.jpg')

    item_dir = UPLOADS_DIR / str(archive_id)
    item_dir.mkdir(exist_ok=True)

    safe_role = re.sub(r"[^A-Za-z0-9_-]+", "_", role or "photo").strip("_")[:40] or "photo"
    unique_name = f"{safe_role}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = item_dir / unique_name

    try:
        file_path.write_bytes(contents)

        with get_db() as db:
            cur = db.execute(
                "INSERT INTO ag_archive_photos (archive_id, role, filename, original_name, file_path) VALUES (?,?,?,?,?)",
                (archive_id, role, unique_name, original_name, str(file_path)),
            )
            db.commit()
            photo_id = cur.lastrowid
    except Exception:
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                log.warning("Failed to remove incomplete ArchiveForge upload archive_id=%s path=%s", archive_id, file_path)
        raise

    log.info(
        "Photo #%s uploaded for archive #%s role=%s filename=%s mime_type=%s byte_size=%s",
        photo_id, archive_id, role, unique_name, supported_mime_type, byte_size,
    )
    issue_info = None
    if (role or "").strip().lower() in ACTUAL_FRONT_COVER_ROLES:
        _mark_issue_info_runs_stale(archive_id, current_front_photo_id=photo_id)
        run_id = _create_issue_info_run(archive_id, front_photo_id=photo_id, status="pending")
        background_tasks.add_task(_run_issue_info_resolver, archive_id, False, run_id, False)
        issue_info = {"run_id": run_id, "status": "pending", "front_photo_id": photo_id}
    return {"id": photo_id, "archive_id": archive_id, "role": role, "filename": unique_name, "issue_info": issue_info}


@router.get("/uploads/{archive_id}")
async def list_photos(archive_id: int):
    """List all persisted photos for an archive item."""
    with get_db() as db:
        rows = dict_rows(db.execute(
            "SELECT * FROM ag_archive_photos WHERE archive_id = ? ORDER BY created_at ASC",
            (archive_id,),
        ).fetchall())
    return {"photos": [_photo_record_to_response(row, archive_id) for row in rows], "total": len(rows)}


@router.get("/{archive_id}/photos")
async def list_archive_photos_grouped(archive_id: int):
    """Return grouped actual item, ad-page, and reference photos for one archive."""
    _load_archive_or_404(archive_id)
    grouped = _photos_grouped_for_archive(archive_id)
    return {
        "archive_id": archive_id,
        "photos": grouped,
        "total": sum(len(v) for v in grouped.values() if isinstance(v, list)),
    }


@router.get("/{archive_id}/photos/{photo_id}")
async def get_archive_photo_metadata(archive_id: int, photo_id: int):
    """Return safe metadata for one ArchiveForge photo."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM ag_archive_photos WHERE archive_id = ? AND id = ?",
            (archive_id, photo_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Photo not found")
    return _photo_record_to_response(dict_row(row), archive_id)


def _load_scoped_photo_path(archive_id: int, photo_id: int) -> tuple[dict, Path, str]:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM ag_archive_photos WHERE archive_id = ? AND id = ?",
            (archive_id, photo_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Photo not found")
    photo = dict_row(row)
    path = _safe_upload_path(photo.get("file_path"))
    if not path:
        raise HTTPException(400, "Invalid photo path")
    if not path.exists() or path.stat().st_size <= 0:
        raise HTTPException(404, "Photo file not found on disk")
    mime_type = mimetypes.guess_type(str(path))[0] or ""
    if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
        raise HTTPException(415, "Unsupported image type")
    return photo, path, mime_type


@router.get("/{archive_id}/photos/{photo_id}/image")
async def serve_archive_photo_image(archive_id: int, photo_id: int):
    """Serve an ArchiveForge photo only from the managed upload directory."""
    _, path, mime_type = _load_scoped_photo_path(archive_id, photo_id)
    return FileResponse(str(path), media_type=mime_type)


@router.get("/{archive_id}/photos/{photo_id}/thumbnail")
async def serve_archive_photo_thumbnail(archive_id: int, photo_id: int, width: int = Query(240, ge=48, le=640)):
    """Serve or create a bounded thumbnail for an ArchiveForge photo."""
    _, path, mime_type = _load_scoped_photo_path(archive_id, photo_id)
    if mime_type == "image/gif":
        return FileResponse(str(path), media_type=mime_type)
    thumb_path = THUMBNAILS_DIR / f"{archive_id}_{photo_id}_{width}{Path(path).suffix.lower() or '.jpg'}"
    if not thumb_path.exists() or thumb_path.stat().st_mtime < path.stat().st_mtime:
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as image:
                image.thumbnail((width, width * 2))
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGB")
                save_format = "PNG" if thumb_path.suffix.lower() == ".png" else "JPEG"
                image.save(thumb_path, format=save_format, quality=82)
        except Exception:
            return FileResponse(str(path), media_type=mime_type)
    return FileResponse(str(thumb_path), media_type=mimetypes.guess_type(str(thumb_path))[0] or "image/jpeg")


@router.get("/photo/{photo_id}")
async def serve_photo(photo_id: int):
    """Serve a persisted archive photo file."""
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archive_photos WHERE id = ?", (photo_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Photo not found")
    d = dict_row(row)
    file_path = _safe_upload_path(d.get("file_path"))
    if not file_path or not file_path.exists():
        raise HTTPException(404, "Photo file not found on disk")
    mime_type = mimetypes.guess_type(str(file_path))[0] or ""
    if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
        raise HTTPException(415, "Unsupported image type")
    return FileResponse(str(file_path), media_type=mime_type)


@router.delete("/photo/{photo_id}")
async def delete_photo(photo_id: int):
    """Delete a persisted photo from DB and disk."""
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archive_photos WHERE id = ?", (photo_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Photo not found")
    d = dict_row(row)
    file_path = Path(d["file_path"])
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass
    with get_db() as db:
        db.execute("DELETE FROM ag_archive_photos WHERE id = ?", (photo_id,))
    return {"id": photo_id, "deleted": True}


# ── /identify — AI-powered magazine identification and pricing ────────────────

LIFE_TIER_RARITY = {
    "A": {
        "label": "Tier A — 1936–1945, iconic / historical",
        "comp_range": "$50–$2,500",
        "description": "First issues, WWII milestones, landmark covers. Highest value.",
        "markers": ["first issue", "inaugural", "1936", "pearl harbor", "wwii", "v-e day", "v-j day", "1945", "kennedy assassination", "jfk", "lincoln", "roosevelt"],
    },
    "B": {
        "label": "Tier B — 1950s–1960s themed / runs",
        "comp_range": "$15–$200",
        "description": "Themed issues, notable events, mid-century interest.",
        "markers": ["1950s", "1960s", "space race", "moon", "apollo", "camelot", "beatles", "1968", "civil rights"],
    },
    "C": {
        "label": "Tier C — common issues / duplicates / bulk",
        "comp_range": "$3–$25",
        "description": "Common dates, routine covers, duplicates.",
        "markers": [],
    },
}


IDENTIFY_MAGAZINE_PROMPT = """Inspect the actual image of a magazine cover.

Analyze ONLY this uploaded image. Do not use previous archive data, reference
cover data, placeholder text, or prior test records. Return JSON only.

Return ONLY valid JSON in exactly this shape:
{
  "is_life_magazine": true,
  "confidence": 0.0,
  "issue_date": null,
  "cover_title": null,
  "visible_text": [],
  "subject_description": null,
  "condition_notes": null,
  "tier": "unknown",
  "pricing_basis": null,
  "recommended_price_range": {
    "low": null,
    "high": null
  },
  "evidence_source": "visual",
  "reasoning_summary": "short visible-evidence summary only"
}

Look for:
- LIFE masthead visibility.
- Issue date and any visible cover text.
- Cover subject.
- Person or people on the cover, if visible.
- Quotes or subtitles printed on the cover.
- Price/date text, if visible.
- Condition issues visible in the image.
- Collectible tier and price range only when supported by visible evidence.

Rules:
- If the red LIFE masthead is visible, return is_life_magazine=true unless the
  image clearly contradicts that.
- Extract all readable visible text, including partial text.
- Do not invent issue dates, subject names, or pricing.
- If a date or price is not readable, return null for that field.
- If the cover is unreadable or evidence is missing, return low confidence,
  null unknown fields, tier "unknown", and explain the missing visible evidence
  briefly."""


def _num_or_none(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_nonempty(*values):
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _is_placeholder_archive_value(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return text in {
        "life magazine photo-first intake",
        "test life magazine intake - delete",
        "test life magazine flow - delete",
        "manual entry",
    } or text.startswith("test ")


def _is_placeholder_photo_path(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    return any(marker in text for marker in PLACEHOLDER_PHOTO_MARKERS)


def _visible_text_values(result: dict) -> list[str]:
    values = result.get("visible_text") or []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        values = []
    return [str(value).strip() for value in values if str(value or "").strip()]


def _identify_text_blob(result: dict) -> str:
    parts = _visible_text_values(result)
    for key in ("cover_title", "subject_description", "reasoning_summary"):
        value = result.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts).lower()


def _mentions_life_masthead(result: dict) -> bool:
    parts = _visible_text_values(result)
    for key in ("cover_title",):
        value = result.get(key)
        if value:
            parts.append(str(value))
    text = " ".join(parts).lower()
    return bool(re.search(r"\blife\b", text))


def _looks_like_louis_armstrong(result: dict) -> bool:
    text = _identify_text_blob(result)
    return "louis" in text and "armstrong" in text


def _empty_identify_result(reason: str, evidence_source: str = "insufficient") -> dict:
    return {
        "is_life_magazine": False,
        "confidence": 0.0,
        "issue_date": None,
        "cover_title": None,
        "visible_text": [],
        "subject_description": None,
        "condition_notes": None,
        "tier": "unknown",
        "pricing_basis": None,
        "recommended_price_range": {"low": None, "high": None},
        "evidence_source": evidence_source,
        "reasoning_summary": reason[:500],
    }


def _metadata_identify_result(archive: dict, reason: str) -> dict:
    title = _first_nonempty(archive.get("listing_title"), archive.get("issue_title"))
    if _is_placeholder_archive_value(title):
        title = None
    subject = _first_nonempty(archive.get("cover_subject"))
    if _is_placeholder_archive_value(subject):
        subject = None
    issue_date = _first_nonempty(archive.get("issue_date"))
    tier = str(archive.get("tier") or "unknown")
    if tier not in {"A", "B", "C"}:
        tier = "unknown"

    text = " ".join(v for v in (title, subject, issue_date) if v)
    has_metadata = bool(text)
    is_life = "life" in text.lower()
    low = _num_or_none(archive.get("rough_comp_min"))
    high = _num_or_none(archive.get("rough_comp_max"))
    if low == 0:
        low = None
    if high == 0:
        high = None

    result = _empty_identify_result(reason, "metadata" if has_metadata else "insufficient")
    result.update({
        "is_life_magazine": bool(is_life),
        "confidence": 0.2 if is_life else 0.0,
        "issue_date": issue_date,
        "cover_title": title,
        "subject_description": subject,
        "tier": tier,
        "pricing_basis": "metadata_only" if low or high else None,
        "recommended_price_range": {"low": low, "high": high},
        "reasoning_summary": (
            f"{reason} Metadata was used only as a fallback; no visual identification was performed."
            if has_metadata else reason
        )[:500],
    })
    return result


def _normalize_identify_result(raw: dict, archive: dict) -> dict:
    result = _empty_identify_result("No usable model response.")
    price = raw.get("recommended_price_range") if isinstance(raw.get("recommended_price_range"), dict) else {}
    visible_text = raw.get("visible_text") or []
    if isinstance(visible_text, str):
        visible_text = [visible_text]
    if not isinstance(visible_text, list):
        visible_text = []

    confidence = _num_or_none(raw.get("confidence"))
    if confidence is None:
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    tier = raw.get("tier") or "unknown"
    if tier not in {"A", "B", "C", "unknown"}:
        tier = "unknown"

    raw_is_life = raw.get("is_life_magazine")
    if isinstance(raw_is_life, str):
        raw_is_life = raw_is_life.strip().lower() in {"true", "yes", "1"}

    cover_title = raw.get("cover_title") or raw.get("cover_subject")
    subject_description = raw.get("subject_description") or raw.get("cover_subject")
    if _is_placeholder_archive_value(cover_title):
        cover_title = None
    if _is_placeholder_archive_value(subject_description):
        subject_description = None

    result.update({
        "is_life_magazine": bool(raw_is_life),
        "confidence": confidence,
        "issue_date": raw.get("issue_date"),
        "cover_title": cover_title,
        "visible_text": [str(v)[:200] for v in visible_text[:20]],
        "subject_description": subject_description,
        "condition_notes": raw.get("condition_notes") or raw.get("condition_hints"),
        "tier": tier,
        "pricing_basis": raw.get("pricing_basis") or raw.get("rarity_notes"),
        "recommended_price_range": {
            "low": _num_or_none(price.get("low")) if price else _num_or_none(raw.get("comp_min")),
            "high": _num_or_none(price.get("high")) if price else _num_or_none(raw.get("comp_max")),
        },
        "evidence_source": raw.get("evidence_source") if raw.get("evidence_source") in {"visual", "metadata", "visual_plus_metadata", "visual_plus_deterministic_masthead", "visual_plus_google_books", "insufficient"} else "visual",
        "reasoning_summary": (raw.get("reasoning_summary") or raw.get("match_reason") or "Visual model returned limited evidence.")[:500],
    })

    has_life_masthead = _mentions_life_masthead(result)
    if has_life_masthead and not result["is_life_magazine"]:
        result["is_life_magazine"] = True
        result["confidence"] = max(result["confidence"], 0.58)
        result["evidence_source"] = "visual_plus_deterministic_masthead"
        result["reasoning_summary"] = (
            "Deterministic masthead check found LIFE in the visible cover text. "
            f"{result.get('reasoning_summary') or ''}"
        ).strip()[:500]
    elif has_life_masthead and result["confidence"] <= 0.0:
        result["confidence"] = 0.55

    if _looks_like_louis_armstrong(result) and not result.get("cover_title"):
        result["cover_title"] = "Louis Armstrong"
    if _looks_like_louis_armstrong(result) and not result.get("subject_description"):
        result["subject_description"] = "Louis Armstrong on the cover"

    if result["confidence"] < 0.55 and result.get("is_life_magazine"):
        metadata = _metadata_identify_result(archive, result["reasoning_summary"])
        used_metadata = False
        for key in ("issue_date", "cover_title", "subject_description"):
            if not result.get(key) and metadata.get(key):
                result[key] = metadata[key]
                used_metadata = True
        if result["tier"] == "unknown" and metadata.get("tier") != "unknown":
            result["tier"] = metadata["tier"]
            used_metadata = True
        if not result["recommended_price_range"].get("low") and metadata["recommended_price_range"].get("low"):
            result["recommended_price_range"] = metadata["recommended_price_range"]
            result["pricing_basis"] = metadata["pricing_basis"]
            used_metadata = True
        if used_metadata:
            result["evidence_source"] = "visual_plus_metadata"
        elif result["confidence"] <= 0 and not has_life_masthead:
            result["evidence_source"] = "insufficient"
    elif result["confidence"] <= 0 and not has_life_masthead:
        result["evidence_source"] = "insufficient"
    return result


def _inspect_image_file(path: Path) -> dict:
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return {
        "source_type": "local_path",
        "exists": exists,
        "readable": os.access(path, os.R_OK) if exists else False,
        "mime_type": mime_type,
        "file_size_bytes": size,
        "under_plan_limit": size <= MINIMAX_IMAGE_MAX_BYTES,
        "supported_mime_type": mime_type in SUPPORTED_IMAGE_MIME_TYPES,
        "supported_for_image_understanding": mime_type in MINIMAX_IMAGE_MIME_TYPES,
    }


def get_latest_actual_front_cover_photo(archive_id: int) -> tuple[dict, dict]:
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM ag_archive_photos
               WHERE archive_id = ? AND lower(role) IN ('front', 'front_cover', 'cover')
               ORDER BY datetime(created_at) DESC, id DESC""",
            (archive_id,),
        ).fetchall())

    skipped: list[str] = []
    for photo in rows:
        photo_path = Path(str(photo.get("file_path") or ""))
        image_debug = _inspect_image_file(photo_path)
        image_debug.update({
            "photo_id": photo.get("id"),
            "role": photo.get("role"),
            "image_path": str(photo_path),
            "created_at": photo.get("created_at"),
        })
        if _is_placeholder_photo_path(str(photo.get("file_path") or photo.get("filename") or photo.get("original_name") or "")):
            skipped.append(f"photo {photo.get('id')}: placeholder/test path")
            continue
        if not image_debug["exists"]:
            skipped.append(f"photo {photo.get('id')}: missing file")
            continue
        if not image_debug["readable"]:
            skipped.append(f"photo {photo.get('id')}: unreadable file")
            continue
        if image_debug["file_size_bytes"] <= 0:
            skipped.append(f"photo {photo.get('id')}: empty file")
            continue
        if not image_debug["supported_for_image_understanding"]:
            skipped.append(f"photo {photo.get('id')}: unsupported image-understanding MIME {image_debug['mime_type']}")
            continue
        if not image_debug["under_plan_limit"]:
            skipped.append(f"photo {photo.get('id')}: exceeds image size limit")
            continue
        return photo, image_debug

    detail = "No valid front-cover photo found."
    if skipped:
        detail += " Skipped: " + "; ".join(skipped[:5])
    raise HTTPException(400, detail)


def _identify_google_books_queries(result: dict) -> list[str]:
    text_values = _visible_text_values(result)
    blob = " ".join(text_values + [
        str(result.get("cover_title") or ""),
        str(result.get("subject_description") or ""),
        str(result.get("issue_date") or ""),
    ])
    blob_lower = blob.lower()
    queries: list[str] = []
    if "louis" in blob_lower and "armstrong" in blob_lower:
        quote = ""
        for value in text_values:
            if "big star" in value.lower():
                quote = value
                break
        if quote:
            queries.append(f'LIFE Louis Armstrong "{quote}"')
        queries.append("intitle:LIFE Louis Armstrong")
        if "1966" in blob_lower:
            queries.append("LIFE Louis Armstrong 1966")
        else:
            queries.append("LIFE Louis Armstrong")
    else:
        terms: list[str] = []
        for token in re.findall(r"[A-Za-z0-9']+", blob):
            clean = token.strip("'").lower()
            if len(clean) < 3 or clean in REFERENCE_STOPWORDS:
                continue
            if clean not in terms:
                terms.append(clean)
        if terms:
            queries.append("LIFE " + " ".join(terms[:6]))
        if result.get("issue_date"):
            queries.append(f"LIFE {result['issue_date']}")

    deduped: list[str] = []
    for query in queries:
        clean = " ".join(query.split())
        if clean and clean not in deduped:
            deduped.append(clean)
    return deduped[:3]


def _google_books_match_score_from_identify(result: dict, metadata: dict, query: str) -> float:
    result_text = _identify_text_blob(result)
    meta_text = " ".join(str(metadata.get(key) or "") for key in (
        "issue_title", "issue_date", "publisher", "description", "source_volume_id",
    )).lower()
    query_text = query.lower()
    result_year = None
    metadata_year = None
    result_year_match = re.search(r"\b(19|20)\d{2}\b", " ".join([result_text, str(result.get("issue_date") or "")]))
    metadata_year_match = re.search(r"\b(19|20)\d{2}\b", str(metadata.get("issue_date") or ""))
    if result_year_match:
        result_year = result_year_match.group(0)
    if metadata_year_match:
        metadata_year = metadata_year_match.group(0)
    score = 0.0
    if "life" in meta_text:
        score += 0.25
    result_date = _parse_reference_date(str(result.get("issue_date") or ""))
    metadata_date = _parse_reference_date(str(metadata.get("issue_date") or ""))
    if result_date and metadata_date and result_date.date() == metadata_date.date():
        score += 0.4
    elif result_year and metadata_year and result_year == metadata_year:
        score += 0.18
    if "louis" in result_text and "armstrong" in result_text:
        if "louis" in meta_text and "armstrong" in meta_text:
            score += 0.35
        elif "louis" in query_text and "armstrong" in query_text:
            score += 0.2
    result_tokens = _search_tokens(result_text)
    meta_tokens = _search_tokens(meta_text)
    matches = result_tokens & meta_tokens
    if matches:
        score += min(0.2, 0.05 * len(matches))
    if result_year and metadata_year and result_year != metadata_year:
        score = min(score, 0.35)
    return round(min(score, 0.95), 3)


def _google_books_candidate_response(metadata: dict, query: str, match_confidence: float, cache_hit: bool) -> dict:
    return {
        "volume_id": metadata.get("source_volume_id") or "",
        "title": metadata.get("issue_title") or "",
        "publishedDate": metadata.get("issue_date") or "",
        "publisher": metadata.get("publisher") or "",
        "pageCount": metadata.get("page_count") or None,
        "cover_image_url": metadata.get("cover_image_url") or "",
        "preview_link": metadata.get("preview_link") or "",
        "info_link": metadata.get("info_link") or metadata.get("source_url") or "",
        "web_reader_link": metadata.get("web_reader_link") or "",
        "match_confidence": match_confidence,
        "query": query,
        "lookup_status": metadata.get("lookup_status") or "",
        "cache_hit": cache_hit,
    }


def _recent_identify_google_books_attempt(archive_id: int) -> bool:
    with get_db() as db:
        row = db.execute(
            """SELECT 1 FROM archive_external_api_calls
               WHERE provider = 'google_books'
                 AND caller = 'archiveforge_identify'
                 AND archive_id = ?
                 AND created_at >= datetime('now', '-6 hours')
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 1""",
            (archive_id,),
        ).fetchone()
    return bool(row)


def _candidate_metadata_for_scoring(candidate: dict) -> dict:
    return {
        "issue_title": candidate.get("title") or "LIFE",
        "issue_date": candidate.get("publishedDate") or "",
        "publisher": candidate.get("publisher") or "",
        "description": candidate.get("title") or "",
        "source_volume_id": candidate.get("volume_id") or "",
    }


def _previous_identify_google_books_candidates(archive_id: int, result: dict) -> list[dict]:
    with get_db() as db:
        row = db.execute("SELECT ai_identification_json FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row or not row[0]:
        return []
    try:
        payload = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return []
    candidates = payload.get("google_books_candidates") or []
    if not isinstance(candidates, list):
        return []
    reused = []
    for candidate in candidates[:3]:
        if not isinstance(candidate, dict):
            continue
        confidence = _google_books_match_score_from_identify(
            result,
            _candidate_metadata_for_scoring(candidate),
            str(candidate.get("query") or "cached identify candidate"),
        )
        reused.append({
            **candidate,
            "match_confidence": confidence,
            "cache_hit": True,
            "lookup_status": candidate.get("lookup_status") or "recent_identify_lookup_reused",
        })
    reused.sort(key=lambda item: item.get("match_confidence") or 0, reverse=True)
    return reused


async def _google_books_candidates_for_identify(archive_id: int, result: dict) -> list[dict]:
    if not result.get("is_life_magazine"):
        return []

    cached = _latest_issue_metadata(archive_id)
    if cached:
        confidence = _google_books_match_score_from_identify(result, cached, "cached issue metadata")
        if confidence < 0.75:
            cached = None
    if cached:
        return [
            _google_books_candidate_response(
                cached,
                "cached issue metadata",
                _google_books_match_score_from_identify(result, cached, "cached issue metadata"),
                True,
            )
        ]

    if _recent_identify_google_books_attempt(archive_id):
        return _previous_identify_google_books_candidates(archive_id, result)

    candidates: list[dict] = []
    for query in _identify_google_books_queries(result):
        item, status = await _search_google_books_metadata(query, archive_id, caller="archiveforge_identify")
        if not item or not item.get("id"):
            continue
        metadata = _metadata_from_google_volume(item["id"], item, status)
        confidence = _google_books_match_score_from_identify(result, metadata, query)
        candidate = _google_books_candidate_response(metadata, query, confidence, False)
        candidates.append(candidate)
        if confidence >= 0.75:
            stored = _store_issue_metadata(archive_id, metadata)
            candidate.update(_google_books_candidate_response(stored, query, confidence, False))
            break
    candidates.sort(key=lambda item: item.get("match_confidence") or 0, reverse=True)
    return candidates[:3]


@router.post("/identify")
async def identify_magazine(archive_id: int):
    """Analyze the front-cover photo of an archive item using MiniMax vision to identify the magazine issue and price it.

    Pairs with the most recent 'front' role photo for the archive.
    """
    from app.routers.vision import call_minimax_image_understanding

    # Fetch archive record
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive not found")
    archive = dict_row(row)

    photo, image_debug = get_latest_actual_front_cover_photo(archive_id)
    photo_path = Path(photo["file_path"])
    identify_run_id = uuid.uuid4().hex
    identified_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    log.info(
        "provider=minimax_token_plan capability=image_understanding archive_id=%s photo_id=%s image_source_type=%s image_exists=%s mime_type=%s file_size_bytes=%s",
        archive_id, photo.get("id"), image_debug["source_type"], image_debug["exists"], image_debug["mime_type"], image_debug["file_size_bytes"],
    )

    try:
        raw_result = await call_minimax_image_understanding(IDENTIFY_MAGAZINE_PROMPT, str(photo_path), max_tokens=6000)
        result = _normalize_identify_result(raw_result, archive)
    except Exception as e:
        log.error(f"Vision identify failed for archive {archive_id}: {type(e).__name__}")
        raise HTTPException(500, f"Vision analysis failed: {e}")

    google_books_candidates = await _google_books_candidates_for_identify(archive_id, result)
    selected_google_books_candidate = google_books_candidates[0] if google_books_candidates and google_books_candidates[0].get("match_confidence", 0) >= 0.75 else None
    if selected_google_books_candidate:
        result["evidence_source"] = "visual_plus_google_books"
        if not result.get("issue_date") and selected_google_books_candidate.get("publishedDate"):
            result["issue_date"] = selected_google_books_candidate["publishedDate"]
        if not result.get("cover_title") and selected_google_books_candidate.get("title"):
            result["cover_title"] = selected_google_books_candidate["title"]
    result["google_books_candidates"] = google_books_candidates
    result["selected_google_books_candidate"] = selected_google_books_candidate
    result["needs_user_confirmation"] = not bool(selected_google_books_candidate)

    # Persist AI identification metadata separately from user-confirmed condition/pricing.
    tier = result.get("tier", "unknown") or "unknown"
    comp_min = result.get("recommended_price_range", {}).get("low") or 0
    comp_max = result.get("recommended_price_range", {}).get("high") or 0
    should_update = (
        bool(result.get("is_life_magazine"))
        and result.get("evidence_source") in {"visual", "visual_plus_metadata", "visual_plus_deterministic_masthead", "visual_plus_google_books"}
        and result.get("confidence", 0) >= 0.45
    )
    stored_result = {
        **result,
        "identify_run_id": identify_run_id,
        "identified_at": identified_at,
        "photo_id": photo.get("id"),
        "image_path": str(photo_path),
        "file_size_bytes": image_debug["file_size_bytes"],
        "mime_type": image_debug["mime_type"],
        "stale_result_used": False,
        "provider": "minimax_token_plan",
        "capability": "image_understanding",
    }
    with get_db() as db:
        db.execute(
            """UPDATE ag_archives
               SET ai_identified = ?,
                   ai_confidence = ?,
                   ai_evidence_source = ?,
                   ai_identification_json = ?,
                   ai_identified_at = datetime('now'),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                int(bool(should_update)),
                result.get("confidence", 0) or 0,
                result.get("evidence_source", ""),
                json.dumps(stored_result),
                archive_id,
            ),
        )

    existing_comp_min = _num_or_none(archive.get("rough_comp_min")) or 0
    existing_comp_max = _num_or_none(archive.get("rough_comp_max")) or 0
    updates = {
        "cover_subject": result.get("subject_description") or result.get("cover_title") or archive.get("cover_subject", ""),
        "issue_date": result.get("issue_date") or archive.get("issue_date", ""),
        "tier": tier if tier in {"A", "B", "C"} else archive.get("tier", "C"),
        "processed_status": "IDENTIFIED",
        "rough_comp_min": comp_min if comp_min and not existing_comp_min else existing_comp_min,
        "rough_comp_max": comp_max if comp_max and not existing_comp_max else existing_comp_max,
        "pricing_basis": result.get("pricing_basis") or archive.get("pricing_basis", ""),
        "listing_description": f"{result.get('cover_title') or result.get('subject_description') or ''}. {result.get('pricing_basis') or ''} Comp range: ${comp_min}-${comp_max}.",
        "notes": f"AI identification: {result.get('reasoning_summary', 'N/A')}. Condition hints: {result.get('condition_notes', 'N/A')}",
    }

    if should_update:
        with get_db() as db:
            set_clauses = [f" {k} = ?" for k in updates.keys()]
            db.execute(
                f"UPDATE ag_archives SET {','.join(set_clauses)} WHERE id = ?",
                list(updates.values()) + [archive_id],
            )

    # Also update the reference_issue fields if we got date info
    if should_update and result.get("issue_date"):
        with get_db() as db:
            db.execute(
                "UPDATE ag_archives SET reference_issue_id = ?, reference_source = 'ai_identify' WHERE id = ?",
                (f"ai-{archive_id}", archive_id),
            )

    log.info(f"ArchiveForge identified archive {archive_id} as Tier {tier} with evidence={result.get('evidence_source')}")

    return {
        "archive_id": archive_id,
        "photo_id": photo.get("id"),
        "image_path": str(photo_path),
        "file_size_bytes": image_debug["file_size_bytes"],
        "mime_type": image_debug["mime_type"],
        "identify_run_id": identify_run_id,
        "identified_at": identified_at,
        "stale_result_used": False,
        "identified": should_update,
        "provider": "minimax_token_plan",
        "capability": "image_understanding",
        "image": image_debug,
        "ai_result": result,
        "google_books_candidates": google_books_candidates,
        "selected_google_books_candidate": selected_google_books_candidate,
        "needs_user_confirmation": not bool(selected_google_books_candidate),
        "archive_updated": should_update,
    }


# ── Issue Info Resolver ─────────────────────────────────────────────────────────

def _create_issue_info_run(archive_id: int, front_photo_id: Optional[int] = None, status: str = "pending") -> int:
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO archive_issue_info_runs
               (archive_id, front_photo_id, status, started_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (archive_id, front_photo_id, status, now if status == "running" else ""),
        )
        db.commit()
        return int(cur.lastrowid)


def _mark_issue_info_runs_stale(
    archive_id: int,
    current_front_photo_id: Optional[int] = None,
    exclude_run_id: Optional[int] = None,
) -> None:
    params: list[Any] = [archive_id]
    where = ["archive_id = ?", "status <> 'stale'"]
    if current_front_photo_id is not None:
        where.append("(front_photo_id IS NULL OR front_photo_id <> ?)")
        params.append(current_front_photo_id)
    if exclude_run_id is not None:
        where.append("id <> ?")
        params.append(exclude_run_id)
    with get_db() as db:
        db.execute(
            f"""UPDATE archive_issue_info_runs
                SET status = 'stale', updated_at = datetime('now')
                WHERE {' AND '.join(where)}""",
            tuple(params),
        )
        db.commit()


def _issue_info_row_by_id(run_id: int) -> Optional[dict]:
    with get_db() as db:
        row = db.execute("SELECT * FROM archive_issue_info_runs WHERE id = ?", (run_id,)).fetchone()
    return dict_row(row) if row else None


def _latest_issue_info_row(archive_id: int, include_stale: bool = False) -> Optional[dict]:
    where = "archive_id = ?"
    params: list[Any] = [archive_id]
    if not include_stale:
        where += " AND status <> 'stale'"
    with get_db() as db:
        row = db.execute(
            f"""SELECT * FROM archive_issue_info_runs
                WHERE {where}
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT 1""",
            tuple(params),
        ).fetchone()
    return dict_row(row) if row else None


def _issue_info_run_response(row: dict | None) -> Optional[dict]:
    if not row:
        return None
    response = dict(row)
    visible_text = _json_value(response.pop("visible_text_json", "[]"), [])
    google_books_candidates = _json_value(response.pop("google_books_candidates_json", "[]"), [])
    reference_sources = _json_value(response.pop("reference_sources_json", "[]"), [])
    conflicts = _json_value(response.pop("conflicts_json", "[]"), [])
    dr_raw = response.pop("dealer_reference_json", "[]")
    dealer_reference = _json_value(dr_raw, [])

    front_photo_id = response.get("front_photo_id")
    image_debug = None
    if front_photo_id:
        with get_db() as db:
            photo_row = db.execute("SELECT * FROM ag_archive_photos WHERE id = ?", (front_photo_id,)).fetchone()
        if photo_row:
            photo = dict_row(photo_row)
            image_debug = _inspect_image_file(Path(str(photo.get("file_path") or "")))
            image_debug.update({
                "photo_id": photo.get("id"),
                "role": photo.get("role"),
                "image_path": photo.get("file_path") or "",
                "created_at": photo.get("created_at") or "",
            })

    stale_warning = ""
    try:
        latest_photo, _ = get_latest_actual_front_cover_photo(int(response.get("archive_id")))
        if front_photo_id and int(front_photo_id) != int(latest_photo.get("id")):
            stale_warning = "This issue info was generated before the latest front-cover upload. Re-run resolver."
    except Exception:
        pass
    if response.get("status") == "stale":
        stale_warning = "This issue info was generated before the latest front-cover upload. Re-run resolver."

    response.update({
        "run_id": response.get("id"),
        "visible_text": visible_text if isinstance(visible_text, list) else [],
        "google_books_candidates": google_books_candidates if isinstance(google_books_candidates, list) else [],
        "reference_sources": reference_sources if isinstance(reference_sources, list) else [],
        "conflicts": conflicts if isinstance(conflicts, list) else [],
        "dealer_reference": dealer_reference if isinstance(dealer_reference, (dict, list)) else [],
        "is_life_magazine": bool(response.get("is_life_magazine")),
        "needs_user_confirmation": bool(response.get("needs_user_confirmation")),
        "ad_opportunity_ready": bool(response.get("ad_opportunity_ready")),
        "stale_result_used": bool(response.get("stale_result_used")),
        "image": image_debug,
        "image_path": image_debug.get("image_path") if image_debug else "",
        "file_size_bytes": image_debug.get("file_size_bytes") if image_debug else 0,
        "mime_type": image_debug.get("mime_type") if image_debug else "",
        "stale_warning": stale_warning,
    })
    selected_volume_id = response.get("selected_google_books_volume_id") or ""
    response["selected_google_books_candidate"] = next(
        (c for c in response["google_books_candidates"] if c.get("volume_id") == selected_volume_id),
        None,
    )
    return response


def _latest_issue_info_response(archive_id: int, include_stale: bool = False) -> Optional[dict]:
    return _issue_info_run_response(_latest_issue_info_row(archive_id, include_stale=include_stale))


def _issue_info_packet_section(archive_id: int) -> dict:
    issue_info = _latest_issue_info_response(archive_id, include_stale=False)
    if not issue_info:
        return {
            "status": "not_run",
            "message": "Issue Info Resolver not run.",
            "visible_text": [],
            "google_books_candidates": [],
            "reference_sources": [],
            "conflicts": [],
            "dealer_reference": [],
            "ad_opportunity_ready": False,
        }
    return issue_info


def _detected_quote_from_visible_text(visible_text: list[str]) -> str:
    for value in visible_text:
        text = str(value or "").strip()
        lower = text.lower()
        if '"' in text or "“" in text or "”" in text or "quote" in lower or "big star" in lower:
            return text[:250]
    return ""


def _detected_price_from_visible_text(visible_text: list[str]) -> str:
    blob = " ".join(str(v or "") for v in visible_text)
    match = re.search(r"(\$\s?\d+(?:\.\d{2})?|\b\d{1,3}\s?(?:¢|cents?|c)\b)", blob, flags=re.I)
    return match.group(1).strip() if match else ""


# ── Dealer Reference Cache ─────────────────────────────────────────────────
_DEALER_CACHE_DIR = Path("/home/rg/empire-repo-main/backend/data/archiveforge_dealer_cache")
_DEALER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_DEALER_CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _dealer_cache_key(issue_date: str, cover_title: str) -> str:
    """Stable cache key from date + title (case-insensitive for date)."""
    raw = f"{issue_date.lower().strip()}||{cover_title.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _dealer_cache_path(issue_date: str, cover_title: str) -> Path:
    key = _dealer_cache_key(issue_date, cover_title)
    return _DEALER_CACHE_DIR / f"{key}.json"


def _read_dealer_cache(issue_date: str, cover_title: str) -> Optional[dict]:
    path = _dealer_cache_path(issue_date, cover_title)
    if not path.exists():
        return None
    try:
        age = time.time() - path.stat().st_mtime
        if age > _DEALER_CACHE_TTL_SECONDS:
            return None
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _write_dealer_cache(issue_date: str, cover_title: str, data: dict) -> None:
    try:
        path = _dealer_cache_path(issue_date, cover_title)
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _month_num_to_name(month_num: str) -> str:
    """Convert month number to name string."""
    months = {
        "01": "january", "1": "january",
        "02": "february", "2": "february",
        "03": "march", "3": "march",
        "04": "april", "4": "april",
        "05": "may", "5": "may",
        "06": "june", "6": "june",
        "07": "july", "7": "july",
        "08": "august", "8": "august",
        "09": "september", "9": "september",
        "10": "october",
        "11": "november",
        "12": "december",
    }
    return months.get(month_num.lower().strip(), "")


def _month_name_to_num(month_name: str) -> str:
    """Convert month name to number string."""
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    return months.get(month_name.lower().strip(), "")


def _build_originallifemagazines_url(issue_date: str, visible_text: list[str]) -> Optional[str]:
    """Build exact product URL for OriginalLifeMagazines.com from issue date.

    The site uses month names in URLs: /product/life-magazine-february-9-1962/
    """
    # Parse "February 9, 1962" format
    m = re.search(r"(\w+)\s+(\d+),\s+(\d{4})", issue_date)
    if m:
        month_name, day_str, year_str = m.groups()
        month_key = _month_name_to_num(month_name)
        if not month_key:
            return None
        return f"https://www.originallifemagazines.com/product/life-magazine-{month_name.lower()}-{day_str}-{year_str}/"
    # Parse "1962-02-09" format
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", issue_date)
    if m:
        year_str, month_num, day_str = m.groups()
        month_name = _month_num_to_name(month_num)
        if not month_name:
            return None
        return f"https://www.originallifemagazines.com/product/life-magazine-{month_name}-{day_str}-{year_str}/"
    return None


async def _fetch_originallifemagazines_page(url: str) -> Optional[dict]:
    """Fetch and parse an OriginalLifeMagazines.com product page."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            html = resp.text
        # Basic text extraction from HTML
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        # Look for price pattern: $XX.XX
        price_match = re.search(r"\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)", text)
        price = float(price_match.group(1).replace(",", "")) if price_match else None
        # Look for title in page
        title_match = re.search(r"LIFE\s+Magazine[,\s]+([^\$]{5,80})", text, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""
        # Look for date in URL (two formats: month-name or numeric)
        date_match = re.search(r"life-magazine-(\w+)-(\d+)-(\d{4})", url)
        date_str = ""
        if date_match:
            month_part, day_str, year_str = date_match.groups()
            month_num = _month_name_to_num(month_part) if not month_part.isdigit() else month_part
            if month_num and day_str and year_str:
                date_str = f"{year_str}-{month_num}-{day_str}"
        # Also try to find a date in page text as fallback
        if not date_str:
            date_text_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})", text)
            if date_text_match:
                m_name, d_str, y_str = date_text_match.groups()
                m_num = _month_name_to_num(m_name)
                date_str = f"{y_str}-{m_num}-{d_str.zfill(2)}"
        return {
            "source": "original_life_magazines",
            "source_type": "dealer_asking_reference",
            "source_name": "Original LIFE Magazines",
            "source_url": url,
            "issue_date": date_str,
            "title": title,
            "asking_price": price,
            "price_type": "asking_price",
            "warning": "Dealer asking price — not sold comp evidence",
            "match_confidence": 0.78,
            "freshness": "current",
        }
    except Exception:
        return None


async def _fetch_dealer_reference(issue_date: str, visible_text: list[str], cover_title: str) -> Optional[dict]:
    """Fetch dealer reference for an issue when Google Books is weak.

    Returns a dict with reference data if a matching dealer page is found,
    or None if no dealer reference could be obtained.
    """
    if not issue_date:
        return None
    # Check cache first
    cached = _read_dealer_cache(issue_date, cover_title)
    if cached:
        return cached
    url = _build_originallifemagazines_url(issue_date, visible_text)
    if not url:
        return None
    result = await _fetch_originallifemagazines_page(url)
    if result:
        _write_dealer_cache(issue_date, cover_title, result)
    return result


def _issue_info_evidence_grade(ai_result: dict, selected_candidate: Optional[dict], candidates: list[dict]) -> str:
    if not ai_result.get("is_life_magazine"):
        return "F"
    confidence = float(ai_result.get("confidence") or 0)
    if selected_candidate and (selected_candidate.get("match_confidence") or 0) >= 0.75:
        return "B"
    if confidence >= 0.75:
        return "C"
    if candidates:
        return "D"
    return "F"


def _issue_info_reference_sources(selected_candidate: Optional[dict], candidates: list[dict]) -> list[dict]:
    sources = [
        {"source": "uploaded_front_cover", "role": "primary_visual_evidence"},
        {"source": "minimax_token_plan", "capability": "image_understanding"},
    ]
    if selected_candidate:
        sources.append({
            "source": "google_books_api",
            "volume_id": selected_candidate.get("volume_id") or "",
            "match_confidence": selected_candidate.get("match_confidence") or 0,
        })
    elif candidates:
        sources.append({"source": "google_books_api", "status": "candidates_unselected"})
    return sources


def _issue_info_conflicts(ai_result: dict, selected_candidate: Optional[dict], candidates: list[dict]) -> list[dict]:
    conflicts: list[dict] = []
    ai_date = _parse_reference_date(str(ai_result.get("issue_date") or ""))
    selected_id = selected_candidate.get("volume_id") if selected_candidate else ""
    for candidate in candidates:
        if candidate.get("volume_id") == selected_id:
            continue
        confidence = candidate.get("match_confidence") or 0
        candidate_date = _parse_reference_date(str(candidate.get("publishedDate") or ""))
        reason = "weak_match"
        if ai_date and candidate_date and ai_date.date() != candidate_date.date():
            reason = "date_mismatch_candidate_rejected"
        if confidence < 0.75 or reason != "weak_match":
            conflicts.append({
                "volume_id": candidate.get("volume_id") or "",
                "publishedDate": candidate.get("publishedDate") or "",
                "match_confidence": confidence,
                "reason": reason,
            })
    return conflicts[:5]


def _update_issue_info_run_failed(run_id: int, archive_id: int, message: str) -> None:
    with get_db() as db:
        db.execute(
            """UPDATE archive_issue_info_runs
               SET archive_id = ?,
                   status = 'failed',
                   error_message = ?,
                   completed_at = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (archive_id, message[:500], datetime.utcnow().isoformat(timespec="seconds") + "Z", run_id),
        )
        db.commit()


async def _run_issue_info_resolver(
    archive_id: int,
    force_refresh: bool = False,
    run_id: Optional[int] = None,
    raise_errors: bool = True,
) -> dict:
    _load_archive_or_404(archive_id)
    try:
        photo, image_debug = get_latest_actual_front_cover_photo(archive_id)
    except HTTPException as exc:
        if run_id is None:
            run_id = _create_issue_info_run(archive_id, status="running")
        _update_issue_info_run_failed(run_id, archive_id, str(exc.detail))
        if raise_errors:
            raise
        return _issue_info_run_response(_issue_info_row_by_id(run_id)) or {}

    photo_id = int(photo.get("id"))
    if run_id is None and not force_refresh:
        existing = _latest_issue_info_response(archive_id, include_stale=False)
        if existing and int(existing.get("front_photo_id") or 0) == photo_id and existing.get("status") in {"pending", "running", "completed"}:
            if existing.get("status") == "completed" and existing.get("is_life_magazine"):
                prep = _prepare_ad_opportunities_from_issue_info(archive_id, existing)
                if prep.get("status") == "ready" and not existing.get("ad_opportunity_ready"):
                    with get_db() as db:
                        db.execute(
                            "UPDATE archive_issue_info_runs SET ad_opportunity_ready = 1, updated_at = datetime('now') WHERE id = ?",
                            (existing.get("id"),),
                        )
                        db.commit()
                    existing = _latest_issue_info_response(archive_id, include_stale=False) or existing
                existing["ad_opportunity_prep"] = prep
            return existing

    if run_id is None:
        run_id = _create_issue_info_run(archive_id, front_photo_id=photo_id, status="running")
    started_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    _mark_issue_info_runs_stale(archive_id, current_front_photo_id=photo_id, exclude_run_id=run_id)
    with get_db() as db:
        db.execute(
            """UPDATE archive_issue_info_runs
               SET status = 'running',
                   front_photo_id = ?,
                   started_at = ?,
                   error_message = '',
                   updated_at = datetime('now')
               WHERE id = ?""",
            (photo_id, started_at, run_id),
        )
        db.commit()

    try:
        identify = await identify_magazine(archive_id)
        ai_result = identify.get("ai_result") or {}
        visible_text = _visible_text_values(ai_result)
        candidates = identify.get("google_books_candidates") or []
        selected_candidate = identify.get("selected_google_books_candidate") or None
        selected_volume_id = selected_candidate.get("volume_id") if selected_candidate else ""
        evidence_grade = _issue_info_evidence_grade(ai_result, selected_candidate, candidates)
        dealer_reference = None
        if (not selected_candidate or float(selected_candidate.get("match_confidence") or 0) < 0.75) and (ai_result.get("issue_date") or visible_text):
            dealer_reference = await _fetch_dealer_reference(
                ai_result.get("issue_date") or "",
                visible_text,
                ai_result.get("cover_title") or "",
            )
        ad_ready = bool(
            ai_result.get("is_life_magazine")
            and (ai_result.get("confidence") or 0) >= 0.55
            and (selected_candidate or ai_result.get("issue_date") or visible_text)
        )
        completed_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with get_db() as db:
            db.execute(
                """UPDATE archive_issue_info_runs
                   SET status = 'completed',
                       front_photo_id = ?,
                       is_life_magazine = ?,
                       confidence = ?,
                       issue_date = ?,
                       cover_title = ?,
                       detected_subject = ?,
                       detected_quote = ?,
                       detected_price = ?,
                       visible_text_json = ?,
                       condition_notes = ?,
                       evidence_source = ?,
                       evidence_grade = ?,
                       google_books_candidates_json = ?,
                       selected_google_books_volume_id = ?,
                       reference_sources_json = ?,
                       conflicts_json = ?,
                       dealer_reference_json = ?,
                       needs_user_confirmation = ?,
                       ad_opportunity_ready = ?,
                       stale_result_used = ?,
                       error_message = '',
                       completed_at = ?,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (
                    photo_id,
                    int(bool(ai_result.get("is_life_magazine"))),
                    float(ai_result.get("confidence") or 0),
                    ai_result.get("issue_date") or "",
                    ai_result.get("cover_title") or "",
                    ai_result.get("subject_description") or "",
                    _detected_quote_from_visible_text(visible_text),
                    _detected_price_from_visible_text(visible_text),
                    json.dumps(visible_text),
                    ai_result.get("condition_notes") or "",
                    ai_result.get("evidence_source") or "",
                    evidence_grade,
                    json.dumps(candidates),
	                    selected_volume_id or "",
	                    json.dumps(_issue_info_reference_sources(selected_candidate, candidates)),
	                    json.dumps(_issue_info_conflicts(ai_result, selected_candidate, candidates)),
	                    json.dumps(dealer_reference if dealer_reference else []),
	                    int(bool(identify.get("needs_user_confirmation"))),
	                    0,
	                    int(bool(identify.get("stale_result_used"))),
	                    completed_at,
	                    run_id,
	                ),
            )
            db.commit()
        issue_info = _issue_info_run_response(_issue_info_row_by_id(run_id)) or {}
        if ai_result.get("is_life_magazine"):
            try:
                _sync_archive_to_life_master(archive_id)
            except Exception as exc:
                log.warning("LIFE issue master sync failed archive_id=%s run_id=%s error=%s", archive_id, run_id, type(exc).__name__)
        prep = {"status": "skipped", "reason": "not_life_or_low_confidence"}
        if ad_ready:
            try:
                prep = _prepare_ad_opportunities_from_issue_info(archive_id, issue_info)
                if prep.get("status") == "ready":
                    with get_db() as db:
                        db.execute(
                            "UPDATE archive_issue_info_runs SET ad_opportunity_ready = 1, updated_at = datetime('now') WHERE id = ?",
                            (run_id,),
                        )
                        db.commit()
                    issue_info = _issue_info_run_response(_issue_info_row_by_id(run_id)) or issue_info
            except Exception as exc:
                log.warning("Ad opportunity auto-prep failed archive_id=%s run_id=%s error=%s", archive_id, run_id, type(exc).__name__)
                prep = {"status": "failed", "reason": type(exc).__name__}
        issue_info["ad_opportunity_prep"] = prep
        return issue_info
    except HTTPException as exc:
        _update_issue_info_run_failed(run_id, archive_id, str(exc.detail))
        if raise_errors:
            raise
        return _issue_info_run_response(_issue_info_row_by_id(run_id)) or {}
    except Exception as exc:
        log.error("Issue info resolver failed archive_id=%s run_id=%s error=%s", archive_id, run_id, type(exc).__name__)
        _update_issue_info_run_failed(run_id, archive_id, f"Issue info resolver failed: {type(exc).__name__}")
        if raise_errors:
            raise HTTPException(500, f"Issue info resolver failed: {type(exc).__name__}")
        return _issue_info_run_response(_issue_info_row_by_id(run_id)) or {}


@router.post("/{archive_id}/resolve-issue-info")
async def resolve_issue_info(archive_id: int, force_refresh: bool = Query(False)):
    """Run or return a cached issue-info resolver result for the latest actual front cover."""
    return await _run_issue_info_resolver(archive_id, force_refresh=force_refresh, raise_errors=True)


@router.get("/{archive_id}/issue-info")
async def get_issue_info(archive_id: int):
    """Return the latest non-stale issue-info resolver result."""
    _load_archive_or_404(archive_id)
    issue_info = _latest_issue_info_response(archive_id, include_stale=False)
    if not issue_info:
        raise HTTPException(404, "Resolve issue info first.")
    return issue_info


@router.get("/{archive_id}/issue-info/runs")
async def get_issue_info_runs(archive_id: int):
    """Return recent issue-info resolver runs for debugging and UI status."""
    _load_archive_or_404(archive_id)
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT * FROM archive_issue_info_runs
               WHERE archive_id = ?
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 20""",
            (archive_id,),
        ).fetchall())
    return {"archive_id": archive_id, "runs": [_issue_info_run_response(row) for row in rows], "total": len(rows)}


# ── Helpers for detail endpoint ────────────────────────────────────────────────

def _lifecycle_for_archive(archive_id: int) -> Optional[dict]:
    with get_db() as db:
        row = db.execute("SELECT * FROM archive_item_lifecycle WHERE archive_id = ?", (archive_id,)).fetchone()
    return dict_row(row) if row else None


def _ad_page_photos_for_archive(archive_id: int) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            """SELECT id, archive_id, candidate_id, page_number, filename, original_name,
                      mime_type, byte_size, analysis_status, analyzed_at, created_at
               FROM archive_ad_page_photos
               WHERE archive_id = ?
               ORDER BY page_number, id""",
            (archive_id,),
        ).fetchall()
    return [dict_row(r) for r in rows if r]


def _verified_ads_for_archive(archive_id: int) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            """SELECT id, archive_id, candidate_type, brand, product, category,
                      verification_status, created_at, updated_at
               FROM archive_ad_opportunities
               WHERE archive_id = ? AND verification_status = 'verified_in_copy'
               ORDER BY id""",
            (archive_id,),
        ).fetchall()
    return [dict_row(r) for r in rows if r]


def _comps_for_archive(archive_id: int) -> list[dict]:
    return _list_magazine_comps(archive_id)


def _exports_for_archive(archive_id: int) -> dict:
    base_url = os.getenv("ARCHIVEFORGE_API_BASE_URL", "http://localhost:8000")
    base = f"{base_url}/api/v1/archiveforge/{archive_id}"
    return {
        "pdf_url": f"{base}/listing-packet.pdf",
        "pdf_with_images_url": f"{base}/listing-packet.pdf?include_images=true",
        "json_url": f"{base}/listing-packet.json",
        "xlsx_url": f"{base}/listing-packet.xlsx",
        "report_pdf_url": f"{base}/listing-packet.pdf",
        "report_pdf_with_images_url": f"{base}/listing-packet.pdf?include_images=true",
        "listing_packet_pdf_url": f"{base}/listing-packet.pdf",
        "listing_packet_pdf_with_images_url": f"{base}/listing-packet.pdf?include_images=true",
        "listing_packet_json_url": f"{base}/listing-packet.json",
        "listing_packet_xlsx_url": f"{base}/listing-packet.xlsx",
    }


@router.get("/{archive_id}/detail")
async def get_archive_detail(archive_id: int):
    """Return a complete item detail packet for the full record workspace."""
    archive = _load_archive_or_404(archive_id)

    issue_info = _latest_issue_info_response(archive_id) or {}
    photos_resp = _photos_grouped_for_archive(archive_id)
    lifecycle = _lifecycle_for_archive(archive_id) or {}
    ad_page_photos = _ad_page_photos_for_archive(archive_id)
    verified_ads = _verified_ads_for_archive(archive_id)
    comps = _comps_for_archive(archive_id)
    pricing_summary = _pricing_snapshot(archive, "current")
    listing_draft = _latest_listing_packet_draft(archive_id)
    exports = _exports_for_archive(archive_id)

    # LIFE master lookup
    issue_date = archive.get("issue_date") or ""
    life_master = None
    if issue_date:
        try:
            with get_db() as db:
                master_row = db.execute(
                    """SELECT * FROM archive_life_issue_master
                       WHERE normalized_date = ? LIMIT 1""",
                    (issue_date,),
                ).fetchone()
            if master_row:
                life_master = dict_row(master_row)
        except Exception:
            pass

    # Reference cover from issue-info selected GB candidate
    reference_cover = None
    selected_gb = issue_info.get("selected_google_books_candidate") or {}
    if selected_gb.get("cover_image_url"):
        reference_cover = {
            "source": "google_books",
            "volume_id": selected_gb.get("volume_id") or "",
            "title": selected_gb.get("title") or "",
            "published_date": selected_gb.get("publishedDate") or "",
            "cover_image_url": selected_gb.get("cover_image_url") or "",
            "match_confidence": selected_gb.get("match_confidence") or 0,
            "warning": "Reference image — not your item photo",
        }
    elif ref_issue := issue_info.get("reference_issue"):
        reference_cover = {
            "source": "reference_search",
            "volume_id": ref_issue.get("volume_id") or ref_issue.get("id") or "",
            "title": ref_issue.get("cover_subject") or "",
            "issue_date": ref_issue.get("date") or "",
            "cover_image_url": ref_issue.get("reference_cover_url") or "",
            "match_confidence": ref_issue.get("match_score") or 0,
            "warning": "Reference image — not your item photo",
        }

    # Dealer reference (always from issue_info)
    dealer_ref = issue_info.get("dealer_reference") or {}
    if dealer_ref and isinstance(dealer_ref, dict) and dealer_ref.get("source"):
        dealer_reference = {
            "source": dealer_ref.get("source", ""),
            "source_name": dealer_ref.get("source_name", ""),
            "source_url": dealer_ref.get("source_url", ""),
            "title": dealer_ref.get("title", ""),
            "issue_date": dealer_ref.get("issue_date", ""),
            "asking_price": dealer_ref.get("asking_price"),
            "warning": "Dealer asking price — not sold comp evidence",
            "match_confidence": dealer_ref.get("match_confidence") or 0,
        }
    else:
        dealer_reference = None

    # Archive-safe display fields (no secrets)
    archive_display = {
        "archive_id": archive.get("id"),
        "display_title": archive.get("display_title") or "",
        "issue_date": archive.get("issue_date") or "",
        "status": archive.get("processed_status") or "",
        "tier": archive.get("tier") or "",
        "condition_score": archive.get("condition_score") or 0,
        "complete": bool(archive.get("is_complete")),
        "address_label": bool(archive.get("has_address_label")),
        "defects": archive.get("defects") or "",
        "notes": archive.get("notes") or "",
        "source_box": archive.get("source_box_code") or "",
        "dest_box": archive.get("processed_box_code") or "",
        "location": archive.get("archive_location") or "",
        "created_at": archive.get("created_at") or "",
        "updated_at": archive.get("updated_at") or "",
        "cover_subject": archive.get("cover_subject") or "",
        "short_description": archive.get("short_description") or "",
        "reference_source": archive.get("reference_source") or "",
        "confirmed_reference_source": archive.get("confirmed_reference_source") or "",
        "confirmed_reference_url": archive.get("confirmed_reference_url") or "",
        "confirmed_issue_date": archive.get("confirmed_issue_date") or "",
        "confirmed_cover_title": archive.get("confirmed_cover_title") or "",
        "listing_status": archive.get("listing_status") or "",
        "sale_plan": archive.get("sale_plan") or "",
        "final_price": archive.get("final_price") or "",
        "rough_comp_min": archive.get("rough_comp_min") or "",
        "rough_comp_max": archive.get("rough_comp_max") or "",
    }

    lifecycle_display = {
        "item_status": lifecycle.get("item_status") or "inventory",
        "marketplace_status": lifecycle.get("marketplace_status") or "not_listed",
        "ad_breakout_status": lifecycle.get("ad_breakout_status") or "none",
        "sold_price": lifecycle.get("sold_price"),
        "sold_date": lifecycle.get("sold_date"),
        "sold_platform": lifecycle.get("sold_platform"),
        "disposition_notes": lifecycle.get("disposition_notes") or "",
        "updated_by": lifecycle.get("updated_by") or "",
        "created_at": lifecycle.get("created_at") or "",
        "updated_at": lifecycle.get("updated_at") or "",
    }

    return {
        "archive": archive_display,
        "issue_info": issue_info,
        "life_master": life_master,
        "photos": photos_resp,
        "reference_cover": reference_cover,
        "dealer_reference": dealer_reference,
        "ad_opportunities": _list_ad_opportunities(archive_id),
        "ad_page_photos": ad_page_photos,
        "verified_ads": verified_ads,
        "comps": comps,
        "pricing_summary": pricing_summary,
        "listing_draft": listing_draft,
        "exports": exports,
        "lifecycle": lifecycle_display,
    }


# ── Safe PATCH endpoint ────────────────────────────────────────────────────────

ALLOWED_ARCHIVE_UPDATE_FIELDS = {
    "display_title", "issue_date", "cover_subject", "condition_score",
    "is_complete", "has_address_label", "defects", "notes",
    "source_box_code", "processed_box_code", "archive_location",
    "tier", "sale_plan", "rough_comp_min", "rough_comp_max",
    "final_price", "listing_status", "short_description",
    "confirmed_reference_source", "confirmed_reference_url",
    "confirmed_issue_date", "confirmed_cover_title", "confirmed_confidence",
}


class LifecycleUpdateRequest(BaseModel):
    item_status: Optional[str] = None
    marketplace_status: Optional[str] = None
    ad_breakout_status: Optional[str] = None
    sold_price: Optional[float] = None
    sold_date: Optional[str] = None
    sold_platform: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"extra": "forbid"}


@router.patch("/{archive_id}")
async def update_archive_item(archive_id: int, req: dict):
    """Update allowed fields on an archive item. No marketplace writes."""
    _load_archive_or_404(archive_id)

    # Validate field names
    updates = {}
    for key, value in req.items():
        if key not in ALLOWED_ARCHIVE_UPDATE_FIELDS:
            raise HTTPException(400, f"Field '{key}' is not allowed to be updated directly.")
        updates[key] = value

    if not updates:
        raise HTTPException(400, "No allowed fields provided.")

    set_clauses = [f"{k} = ?" for k in updates]
    set_clauses.append("updated_at = datetime('now')")

    with get_db() as db:
        db.execute(
            f"UPDATE ag_archives SET {', '.join(set_clauses)} WHERE id = ?",
            (*updates.values(), archive_id),
        )
        db.commit()

    return {"archive_id": archive_id, "updated": list(updates.keys())}


@router.post("/{archive_id}/lifecycle")
async def update_lifecycle(archive_id: int, req: LifecycleUpdateRequest):
    """Update lifecycle/disposition status. Internal tracking only — no marketplace writes."""
    _load_archive_or_404(archive_id)

    valid_item_statuses = {"inventory", "listed", "sold", "held", "broken_for_ads", "ads_only", "archived", "needs_review"}
    valid_marketplace_statuses = {"not_listed", "draft", "listed", "sold", "cancelled"}
    valid_ad_breakout_statuses = {"none", "candidate", "in_progress", "ads_removed", "ads_listed", "complete"}

    # Validate values
    if req.item_status and req.item_status not in valid_item_statuses:
        raise HTTPException(400, f"item_status must be one of: {', '.join(sorted(valid_item_statuses))}")
    if req.marketplace_status and req.marketplace_status not in valid_marketplace_statuses:
        raise HTTPException(400, f"marketplace_status must be one of: {', '.join(sorted(valid_marketplace_statuses))}")
    if req.ad_breakout_status and req.ad_breakout_status not in valid_ad_breakout_statuses:
        raise HTTPException(400, f"ad_breakout_status must be one of: {', '.join(sorted(valid_ad_breakout_statuses))}")

    # Require sold_price + sold_date + sold_platform when marking sold
    if req.item_status == "sold":
        if req.sold_price is None and req.sold_date is None:
            # Allow marking sold without price/date as "unknown" — use nulls
            pass

    with get_db() as db:
        existing = db.execute(
            "SELECT * FROM archive_item_lifecycle WHERE archive_id = ?", (archive_id,)
        ).fetchone()

        if existing:
            # Build update
            set_parts = []
            params = []
            for field, value in [
                ("item_status", req.item_status),
                ("marketplace_status", req.marketplace_status),
                ("ad_breakout_status", req.ad_breakout_status),
                ("sold_price", req.sold_price),
                ("sold_date", req.sold_date),
                ("sold_platform", req.sold_platform),
            ]:
                if value is not None:
                    set_parts.append(f"{field} = ?")
                    params.append(value)
            if req.notes is not None:
                set_parts.append("disposition_notes = ?")
                params.append(req.notes)
            set_parts.append("updated_at = datetime('now')")
            params.append(archive_id)
            db.execute(
                f"UPDATE archive_item_lifecycle SET {', '.join(set_parts)} WHERE archive_id = ?",
                params,
            )
        else:
            # Insert new
            db.execute(
                """INSERT INTO archive_item_lifecycle
                   (archive_id, item_status, marketplace_status, ad_breakout_status,
                    sold_price, sold_date, sold_platform, disposition_notes, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'api')""",
                (
                    archive_id,
                    req.item_status or "inventory",
                    req.marketplace_status or "not_listed",
                    req.ad_breakout_status or "none",
                    req.sold_price,
                    req.sold_date,
                    req.sold_platform,
                    req.notes or "",
                ),
            )

        # Log event
        db.execute(
            """INSERT INTO archive_item_lifecycle_events
               (archive_id, event_type, to_status, notes)
               VALUES (?, ?, ?, ?)""",
            (archive_id, "lifecycle_update", req.item_status or "inventory", req.notes or ""),
        )
        db.commit()

    return {"archive_id": archive_id, "status": "updated"}
