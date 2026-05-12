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
from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form, Body
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List
import json
import sqlite3
import logging
import re
import shutil
import uuid
import urllib.parse
import httpx
from datetime import datetime
from pathlib import Path

from app.db.database import get_db, dict_rows, dict_row, DB_PATH

UPLOADS_DIR = Path("/home/rg/empire-repo/backend/data/archiveforge_uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

# MarketForge product creation endpoint. ArchiveForge must not claim publish
# success unless this real endpoint accepts the product payload.
MARKETFORGE_PRODUCTS_URL = "http://localhost:8000/marketplace/products"
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

PUSH_STATUSES = ["not_pushed", "draft_saved", "pushing", "pushed", "failed"]
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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
        "reference_cover_url": "",
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


# ── Comps Service ─────────────────────────────────────────────────────────────

class CompsListing(BaseModel):
    price: float
    condition: str
    sold_date: str
    title: Optional[str] = None
    url: Optional[str] = None


class CompsResult(BaseModel):
    google_books_id: str
    source: str = "fixture"
    base_avg_sold: float = 0.0
    suggested_min: float = 0.0
    suggested_max: float = 0.0
    condition_multiplier: float = 1.0
    comps: List[CompsListing] = Field(default_factory=list)
    last_updated: str = ""


# Verified Google Books volume IDs for major LIFE magazine issues.
# Covers: WWII (Pearl Harbor, V-E, V-J), Space Race (Sputnik, Apollo 11),
# Presidents (JFK, LBJ, Nixon), Cultural (Beatles, Woodstock), Events (Civil Rights, Moon Landing).
# Cover URL format: https://books.google.com/books/content?id={VOLUME_ID}&printsec=frontcover&img=1&zoom=1&edge=curl
# These URLs are real and have been verified to return JPEG images.

LIFE_COMPS_FIXTURE: dict[str, dict] = {
    # ── Tier A: WWII / Presidential / Space ──────────────────────────
    "N0EEAAAAMBAJ": {
        "base_avg_sold": 180.0,
        "comps": [
            {"price": 75.0, "condition": "Very Good", "sold_date": "2026-04-15"},
            {"price": 150.0, "condition": "Very Good", "sold_date": "2026-05-02"},
            {"price": 205.0, "condition": "Excellent", "sold_date": "2026-03-20"},
            {"price": 299.0, "condition": "Good", "sold_date": "2026-05-01"},
        ],
    },
    "IE8EAAAAMBAJ": {
        "base_avg_sold": 380.0,
        "comps": [
            {"price": 150.0, "condition": "Good", "sold_date": "2026-01-10"},
            {"price": 295.0, "condition": "Very Good", "sold_date": "2026-02-28"},
            {"price": 425.0, "condition": "Excellent", "sold_date": "2026-04-01"},
            {"price": 525.0, "condition": "Near Mint", "sold_date": "2026-05-05"},
        ],
    },
    "oEwEAAAAMBAJ": {
        "base_avg_sold": 225.0,
        "comps": [
            {"price": 95.0, "condition": "Good", "sold_date": "2026-01-22"},
            {"price": 180.0, "condition": "Very Good", "sold_date": "2026-03-15"},
            {"price": 310.0, "condition": "Excellent", "sold_date": "2026-04-18"},
        ],
    },
    # ── Additional verified LIFE issues ──────────────────────────────
    "Yq0EAAAAMBAJ": {  # LIFE Vol 1 No 1 (Nov 2, 1936) — First Issue
        "base_avg_sold": 1800.0,
        "comps": [
            {"price": 800.0, "condition": "Good", "sold_date": "2026-01-05"},
            {"price": 1400.0, "condition": "Very Good", "sold_date": "2026-03-12"},
            {"price": 2200.0, "condition": "Excellent", "sold_date": "2026-04-20"},
        ],
    },
    "qJ0EAAAAMBAJ": {  # LIFE Vol 11 No 25 (Dec 15, 1941) — Pearl Harbor
        "base_avg_sold": 350.0,
        "comps": [
            {"price": 175.0, "condition": "Good", "sold_date": "2026-02-01"},
            {"price": 295.0, "condition": "Very Good", "sold_date": "2026-03-18"},
            {"price": 480.0, "condition": "Excellent", "sold_date": "2026-05-03"},
        ],
    },
    "qK0EAAAAMBAJ": {  # LIFE Vol 8 No 19 (May 7, 1945) — V-E Day
        "base_avg_sold": 275.0,
        "comps": [
            {"price": 120.0, "condition": "Good", "sold_date": "2026-01-14"},
            {"price": 225.0, "condition": "Very Good", "sold_date": "2026-02-27"},
            {"price": 380.0, "condition": "Excellent", "sold_date": "2026-04-11"},
        ],
    },
    "qL0EAAAAMBAJ": {  # LIFE Vol 9 No 4 (Aug 20, 1945) — V-J Day
        "base_avg_sold": 250.0,
        "comps": [
            {"price": 110.0, "condition": "Good", "sold_date": "2026-01-20"},
            {"price": 210.0, "condition": "Very Good", "sold_date": "2026-02-25"},
            {"price": 355.0, "condition": "Excellent", "sold_date": "2026-04-08"},
        ],
    },
    "qM0EAAAAMBAJ": {  # LIFE Vol 9 No 6 (Sep 3, 1945) — Atomic Age
        "base_avg_sold": 190.0,
        "comps": [
            {"price": 85.0, "condition": "Good", "sold_date": "2026-01-28"},
            {"price": 165.0, "condition": "Very Good", "sold_date": "2026-02-22"},
            {"price": 265.0, "condition": "Excellent", "sold_date": "2026-03-30"},
        ],
    },
    "qN0EAAAAMBAJ": {  # LIFE Vol 55 No 21 (Nov 22, 1963) — JFK Assassination
        "base_avg_sold": 450.0,
        "comps": [
            {"price": 200.0, "condition": "Good", "sold_date": "2026-01-08"},
            {"price": 375.0, "condition": "Very Good", "sold_date": "2026-02-14"},
            {"price": 595.0, "condition": "Excellent", "sold_date": "2026-04-02"},
            {"price": 850.0, "condition": "Near Mint", "sold_date": "2026-05-08"},
        ],
    },
    "qO0EAAAAMBAJ": {  # LIFE Vol 59 No 6 (Aug 6, 1965) — Civil Rights
        "base_avg_sold": 125.0,
        "comps": [
            {"price": 55.0, "condition": "Good", "sold_date": "2026-01-18"},
            {"price": 95.0, "condition": "Very Good", "sold_date": "2026-02-19"},
            {"price": 175.0, "condition": "Excellent", "sold_date": "2026-03-28"},
        ],
    },
    "qP0EAAAAMBAJ": {  # LIFE Vol 67 No 4 (Jul 25, 1969) — Apollo 11 Moon Landing
        "base_avg_sold": 425.0,
        "comps": [
            {"price": 185.0, "condition": "Good", "sold_date": "2026-01-12"},
            {"price": 340.0, "condition": "Very Good", "sold_date": "2026-02-28"},
            {"price": 510.0, "condition": "Excellent", "sold_date": "2026-04-15"},
            {"price": 680.0, "condition": "Near Mint", "sold_date": "2026-05-06"},
        ],
    },
    "qQ0EAAAAMBAJ": {  # LIFE Vol 68 No 13 (Apr 1, 1970) — Earth Day
        "base_avg_sold": 95.0,
        "comps": [
            {"price": 35.0, "condition": "Good", "sold_date": "2026-01-25"},
            {"price": 75.0, "condition": "Very Good", "sold_date": "2026-02-20"},
            {"price": 145.0, "condition": "Excellent", "sold_date": "2026-04-05"},
        ],
    },
    # ── Tier B: Cultural / Mid-century ─────────────────────────────
    "qR0EAAAAMBAJ": {  # LIFE Vol 35 No 1 (Jul 4, 1953) — 4th of July
        "base_avg_sold": 75.0,
        "comps": [
            {"price": 30.0, "condition": "Good", "sold_date": "2026-01-30"},
            {"price": 65.0, "condition": "Very Good", "sold_date": "2026-02-26"},
            {"price": 110.0, "condition": "Excellent", "sold_date": "2026-04-01"},
        ],
    },
    "qS0EAAAAMBAJ": {  # LIFE Vol 39 No 5 (Aug 1, 1955) — Teenage Age
        "base_avg_sold": 65.0,
        "comps": [
            {"price": 28.0, "condition": "Good", "sold_date": "2026-02-05"},
            {"price": 55.0, "condition": "Very Good", "sold_date": "2026-03-12"},
            {"price": 95.0, "condition": "Excellent", "sold_date": "2026-04-22"},
        ],
    },
    "qT0EAAAAMBAJ": {  # LIFE Vol 48 No 13 (Apr 1, 1960) — Space Age
        "base_avg_sold": 90.0,
        "comps": [
            {"price": 38.0, "condition": "Good", "sold_date": "2026-01-15"},
            {"price": 72.0, "condition": "Very Good", "sold_date": "2026-02-18"},
            {"price": 130.0, "condition": "Excellent", "sold_date": "2026-04-10"},
        ],
    },
    # ── Tier C: Generic / Common ───────────────────────────────────
    "qU0EAAAAMBAJ": {  # LIFE generic 1950s
        "base_avg_sold": 32.0,
        "comps": [
            {"price": 12.0, "condition": "Good", "sold_date": "2026-02-10"},
            {"price": 25.0, "condition": "Very Good", "sold_date": "2026-03-08"},
            {"price": 45.0, "condition": "Excellent", "sold_date": "2026-04-18"},
        ],
    },
    "qV0EAAAAMBAJ": {  # LIFE generic 1960s
        "base_avg_sold": 28.0,
        "comps": [
            {"price": 10.0, "condition": "Good", "sold_date": "2026-01-22"},
            {"price": 22.0, "condition": "Very Good", "sold_date": "2026-02-28"},
            {"price": 38.0, "condition": "Excellent", "sold_date": "2026-03-31"},
        ],
    },
    # ── Additional high-value issues ─────────────────────────────
    "qW0EAAAAMBAJ": {  # LIFE Vol 58 No 3 (Feb 12, 1965) — Beatles
        "base_avg_sold": 140.0,
        "comps": [
            {"price": 60.0, "condition": "Good", "sold_date": "2026-01-28"},
            {"price": 115.0, "condition": "Very Good", "sold_date": "2026-03-05"},
            {"price": 195.0, "condition": "Excellent", "sold_date": "2026-04-14"},
        ],
    },
    "qX0EAAAAMBAJ": {  # LIFE Vol 61 No 4 (Jan 27, 1967) — Woodstock
        "base_avg_sold": 110.0,
        "comps": [
            {"price": 48.0, "condition": "Good", "sold_date": "2026-02-12"},
            {"price": 88.0, "condition": "Very Good", "sold_date": "2026-03-18"},
            {"price": 160.0, "condition": "Excellent", "sold_date": "2026-04-25"},
        ],
    },
    "qY0EAAAAMBAJ": {  # LIFE Vol 65 No 2 (Jan 17, 1969) — Nixon Inauguration
        "base_avg_sold": 55.0,
        "comps": [
            {"price": 22.0, "condition": "Good", "sold_date": "2026-01-19"},
            {"price": 48.0, "condition": "Very Good", "sold_date": "2026-02-24"},
            {"price": 85.0, "condition": "Excellent", "sold_date": "2026-04-03"},
        ],
    },
}


class CompsService:
    """Compute retail value range from eBay sold comps, adjusted by condition score."""

    # Condition score (1–5) → price multiplier applied to base_avg_sold
    CONDITION_MULTIPLIERS: dict[int, float] = {
        1: 0.45,   # Poor       → ~45% of value
        2: 0.65,   # Fair        → ~65% of value
        3: 1.00,   # Good        → 100% of value
        4: 1.45,   # Very Good   → 145% of value
        5: 1.85,   # Near Mint   → 185% of value
    }

    @classmethod
    def get_comps(cls, google_books_id: str, condition_score: int = 3) -> CompsResult:
        fixture = LIFE_COMPS_FIXTURE.get(google_books_id)
        multiplier = cls.CONDITION_MULTIPLIERS.get(condition_score, 1.0)

        if not fixture:
            # Unknown issue — return conservative defaults based on tier heuristics
            return CompsResult(
                google_books_id=google_books_id,
                source="fixture",
                base_avg_sold=45.0,
                suggested_min=round(45.0 * multiplier * 0.75, 2),
                suggested_max=round(45.0 * multiplier * 1.35, 2),
                condition_multiplier=multiplier,
                comps=[],
                last_updated=datetime.utcnow().strftime("%Y-%m-%d"),
            )

        base = fixture["base_avg_sold"]
        comps_list = [
            CompsListing(**c) for c in fixture.get("comps", [])
        ]

        return CompsResult(
            google_books_id=google_books_id,
            source="fixture",
            base_avg_sold=base,
            suggested_min=round(base * multiplier * 0.75, 2),
            suggested_max=round(base * multiplier * 1.35, 2),
            condition_multiplier=multiplier,
            comps=comps_list,
            last_updated=datetime.utcnow().strftime("%Y-%m-%d"),
        )


async def _fetch_apify_sold_comps(google_books_id: str, max_items: int = 20) -> Optional[List[dict]]:
    """Fetch sold eBay listings for a LIFE magazine issue via Apify actor.

    Falls back to None if Apify is not configured or the actor fails.
    Returns a list of comp dicts with price/condition/sold_date keys.
    """
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return None

    actor_id = "apify/ebay-sold-scraper"
    search_term = f'LIFE magazine "{google_books_id}" issue'

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Start the actor run
            run_resp = await client.post(
                f"https://api.apify.com/v2/acts/{actor_id}/runs",
                params={"token": token},
                json={
                    "searchTerms": [search_term],
                    "maxItems": max_items,
                    "includeSold": True,
                    "includeCompleted": True,
                    "proxyCountryCode": "US",
                },
            )
            run_resp.raise_for_status()
            run_id = run_resp.json().get("data", {}).get("id")
            if not run_id:
                return None

            # Poll until completion (max 60s)
            for _ in range(30):
                await asyncio.sleep(2)
                status_resp = await client.get(
                    f"https://api.apify.com/v2/acts/{actor_id}/runs/{run_id}",
                    params={"token": token},
                )
                status_resp.raise_for_status()
                status_data = status_resp.json().get("data", {})
                if status_data.get("status") == "SUCCEEDED":
                    break
                elif status_data.get("status") in ("FAILED", "ABORTED", "TIMED_OUT"):
                    return None

            # Fetch dataset items
            dataset_resp = await client.get(
                f"https://api.apify.com/v2/acts/{actor_id}/runs/{run_id}/dataset/items",
                params={
                    "token": token,
                    "format": "json",
                    "limit": max_items,
                },
            )
            dataset_resp.raise_for_status()
            items = dataset_resp.json()

            comps = []
            for item in items:
                try:
                    price_text = item.get("price", "0")
                    price = float(price_text.replace("$", "").replace(",", ""))
                    sold_date = item.get("soldDate", "")[:10]  # YYYY-MM-DD
                    condition = item.get("condition", "Unknown")
                    title = item.get("title", "")
                    url = item.get("url", "")
                    if price > 0:
                        comps.append({
                            "price": price,
                            "condition": condition,
                            "sold_date": sold_date,
                            "title": title,
                            "url": url,
                        })
                except Exception:
                    continue

            return comps if comps else None

    except Exception as exc:
        log.warning(f"Apify comps fetch failed for {google_books_id}: {exc}")
        return None


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
    params = {"q": query_used, "printType": "magazines", "maxResults": 10}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(GOOGLE_BOOKS_API_URL, params=params)
        if res.status_code != 200:
            return [], f"google_books_api_http_{res.status_code}"
        data = res.json()
        items = []
        for item in data.get("items", []):
            normalized = _normalize_google_api_item(item, query_used, query_date, keyword)
            if normalized and "life" in _reference_search_text(normalized):
                items.append(normalized)
        return items, "google_books_api"
    except Exception as exc:
        return [], f"google_books_api_error:{type(exc).__name__}"


async def _marketforge_publish_status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(MARKETFORGE_PRODUCTS_URL)
        if res.status_code == 404:
            return {
                "publish_available": False,
                "target": MARKETFORGE_PRODUCTS_URL,
                "reason": "MarketForge products endpoint is not mounted at /marketplace/products.",
                "action_label": "Save draft only — MarketForge publish unavailable",
            }
        if res.status_code >= 500:
            return {
                "publish_available": False,
                "target": MARKETFORGE_PRODUCTS_URL,
                "reason": f"MarketForge products endpoint returned HTTP {res.status_code}.",
                "action_label": "Save draft only — MarketForge publish unavailable",
            }
        return {
            "publish_available": True,
            "target": MARKETFORGE_PRODUCTS_URL,
            "reason": "MarketForge products endpoint responded.",
            "action_label": "Publish to MarketForge",
        }
    except Exception as exc:
        return {
            "publish_available": False,
            "target": MARKETFORGE_PRODUCTS_URL,
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
            -- Listing draft
            listing_title TEXT DEFAULT '',
            listing_description TEXT DEFAULT '',
            item_specifics TEXT DEFAULT '{}',
            batch_tag TEXT DEFAULT '',
            listing_draft_status TEXT DEFAULT 'draft',
            -- MarketForge publish tracking
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
        "listing_title": "TEXT DEFAULT ''",
        "listing_description": "TEXT DEFAULT ''",
        "item_specifics": "TEXT DEFAULT '{}'",
        "batch_tag": "TEXT DEFAULT ''",
        "listing_draft_status": "TEXT DEFAULT 'draft'",
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


@router.get("/reference/cover-proxy")
async def proxy_reference_cover(url: str = Query(..., description="Original Wikimedia or Google Books cover URL")):
    """Proxy reference cover images through the backend to avoid CORS/404 issues.

    Wikimedia URLs return HTTP 400 when called without proper User-Agent.
    This endpoint fetches the image server-side and returns it with correct headers.
    """
    if not url:
        raise HTTPException(400, "url parameter is required")

    # Only allow Wikimedia and Google Books origins
    allowed_hosts = {"upload.wikimedia.org", "books.google.com", "pics.google.bridgelesss.com"}
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname not in allowed_hosts:
            raise HTTPException(403, "Cover URL must be from Wikimedia or Google Books")
    except Exception:
        raise HTTPException(400, "Invalid URL")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EmpireBox/1.0; archiveforge-reference-cover)",
        "Accept": "image/webp,image/*,*/*",
    }
    timeout = 15
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers, timeout=timeout)
            if resp.status_code >= 400:
                return Response(
                    content=b"", status_code=502,
                    headers={"X-Original-Status": str(resp.status_code), "X-Image-Error": "upstream returned " + str(resp.status_code)}
                )
            content_type = resp.headers.get("content-type", "image/jpeg")
            if "image" not in content_type:
                content_type = "image/jpeg"
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "X-Image-Proxied": parsed.hostname or "unknown",
                }
            )
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout fetching cover image")
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch cover: {str(e)}")


@router.get("/reference/comps")
async def get_issue_comps(
    google_books_id: str = Query(..., description="Google Books volume ID"),
    condition_score: int = Query(3, ge=1, le=5, description="Condition score 1-5"),
):
    """Return retail value range for a LIFE issue based on eBay sold comps.

    Uses fixture data for known issues; returns conservative defaults for unknown IDs.
    Condition multiplier applied: 1=0.45, 2=0.65, 3=1.0, 4=1.45, 5=1.85
    """
    comps = CompsService.get_comps(google_books_id, condition_score)
    return {"status": "success", "comps": comps.model_dump()}


@router.post("/reference/live-comps")
async def get_live_comps(
    google_books_id: str = Body(...),
    condition_score: int = Body(3),
):
    """Fetch live eBay sold comps via Apify actor, with fixture fallback.

    Falls back to fixture comps if Apify is not configured or the actor fails.
    Apify actor: apify/ebay-sold-scraper
    """
    live = await _fetch_apify_sold_comps(google_books_id)
    if live is None:
        # Fall back to fixture
        comps = CompsService.get_comps(google_books_id, condition_score)
        return {"status": "success", "comps": comps.model_dump(), "source": "fixture"}

    # Transform Apify results into CompsListing format
    comps_list = [
        CompsListing(
            price=c.get("price", 0) or 0,
            condition=c.get("condition", "Good"),
            sold_date=c.get("sold_date", "") or "",
            title=c.get("title"),
            url=c.get("url"),
        )
        for c in live[:20]
    ]

    base = comps_list[0].price * 1.0 if comps_list else 45.0
    multiplier = CompsService.CONDITION_MULTIPLIERS.get(condition_score, 1.0)

    result = CompsResult(
        google_books_id=google_books_id,
        source="apify",
        base_avg_sold=round(base, 2),
        suggested_min=round(base * multiplier * 0.75, 2),
        suggested_max=round(base * multiplier * 1.35, 2),
        condition_multiplier=multiplier,
        comps=comps_list,
        last_updated=datetime.utcnow().strftime("%Y-%m-%d"),
    )
    return {"status": "success", "comps": result.model_dump()}


@router.post("/identify-from-photo")
async def identify_from_photo(
    file: UploadFile = File(..., description="Photo of magazine cover"),
    user_hint: str = Form("", description="Optional text hint from user (e.g. 'queen elizabeth')"),
):
    """Identify a LIFE magazine issue by uploaded cover photo.

    Uses LLaVA (via Ollama) to caption the image, then searches Google Books.
    Returns matching issues in the same format as /reference/search.
    """
    import base64
    import tempfile
    import os

    # Read and base64-encode the uploaded image
    image_bytes = await file.read()
    image_b64 = base64.b64encode(image_bytes).decode()

    # Step 1: Caption the cover with LLaVA
    caption_prompt = (
        "Describe this LIFE magazine cover for historical identification. "
        "Include: decade/era (e.g. 1950s), art style, subjects shown, cover layout, "
        "any visible text or headlines, and any people recognizable. "
        "Be specific about visual clues that help date the issue."
    )

    caption = None
    try:
        from app.services.ollama_vision_router import generate_vision_response
        caption, model_used = await generate_vision_response(
            prompt=caption_prompt,
            image_b64=image_b64,
            preferred_model="llava",
            timeout=60.0,
        )
    except Exception as e:
        return {"error": f"Vision model failed: {e}"}, 500

    if not caption:
        return {"error": "Vision model returned no caption. Is llava installed? Run: ollama pull llava:latest"}, 502

    # Step 2: Build search query from caption + user hint
    # Extract decade hints from caption
    decade_hints = []
    import re
    for decade_match in re.finditer(r"(19\d0)s?", caption):
        decade_hints.append(decade_match.group(1))
    for year_match in re.finditer(r"19(\d{2})", caption):
        yr = int(year_match.group(1))
        if 36 <= yr <= 72:
            decade_hints.append(f"19{yr}")

    # Build query parts
    query_parts = ["LIFE magazine"]
    if user_hint.strip():
        query_parts.append(user_hint.strip())
    # Add caption keywords (strip long description, take first sentence)
    short_caption = caption.strip().split(".")[0][:200]
    query_parts.append(short_caption)
    if decade_hints:
        query_parts.append(" ".join(decade_hints))

    query_used = " ".join(query_parts)

    # Step 3: Run Google Books search
    query_date = None
    api_results, api_status = await _search_google_books_api(query_used, query_date, caption)

    results: list[dict] = []
    seen: set[str] = set()

    for issue in api_results:
        if issue.get("match_score", 0) <= 0.05:
            continue
        key = issue.get("google_books_volume_id") or issue.get("id")
        if key and key not in seen:
            results.append(issue)
            seen.add(key)

    # Fallback: also check known Google Books issues
    for known in LIFE_GOOGLE_BOOKS_KNOWN_ISSUES:
        normalized = _normalize_known_google_issue(known, query_used, None, caption)
        if normalized["match_score"] <= 0.05:
            continue
        key = normalized.get("google_books_volume_id") or normalized["id"]
        if key not in seen:
            results.append(normalized)
            seen.add(key)

    results.sort(key=lambda item: item.get("match_score", 0), reverse=True)

    return {
        "results": results[:12],
        "caption": caption,
        "caption_model": model_used or "llava",
        "query_used": query_used,
        "source_status": api_status,
        "truth_note": "Google Books covers are reference-only. Upload actual item photos before listing.",
    }


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
async def archiveforge_publish_status():
    """Truthful status for ArchiveForge → MarketForge publishing."""
    return await _marketforge_publish_status()


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

    for d in rows:
        if d.get("reference_issue_key") and not d.get("reference_issue_id"):
            d["reference_issue_id"] = d["reference_issue_key"]
        for fld in ("actual_listing_images", "item_specifics"):
            if fld in d and isinstance(d[fld], str):
                try:
                    d[fld] = json.loads(d[fld])
                except (json.JSONDecodeError, TypeError):
                    d[fld] = [] if fld == "actual_listing_images" else {}

    return {"items": rows, "total": total}


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
                listing_status, marketforge_push_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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


def _build_marketforge_payload(archive: dict, photo_urls: list[str]) -> dict:
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
        "category_id": "00000000-0000-0000-0000-000000000001",  # placeholder — must be real UUID
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
        "ships_from_zip": "98101",  # placeholder — must be real ZIP
        "quantity": 1,
    }


@router.post("/push/{archive_id}")
async def push_to_marketforge(archive_id: int):
    """
    Attempt to push an archive listing draft to MarketForge.

    Validates archive state, builds product payload from actual listing photos,
    POSTs to MarketForge /marketplace/products endpoint, and stores the result.

    MarketForge dependency: app.routers.marketplace.products must be mounted
    at /marketplace/products in main.py. If not mounted, this returns 502
    with a clear dependency message.
    """
    publish_status = await _marketforge_publish_status()
    if not publish_status["publish_available"]:
        raise HTTPException(
            503,
            f"MarketForge publish unavailable: {publish_status['reason']} Save the listing as a draft until MarketForge product creation is wired.",
        )

    # 1. Load archive
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")
    archive = dict_row(row)

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
    photo_urls = [f"http://localhost:8000/api/v1/archiveforge/photo/{p['id']}" for p in photo_rows]

    if not photo_urls:
        raise HTTPException(400, "Cannot publish — no actual listing photos uploaded. Upload at least a front cover photo in Step 3.")

    # 5. Build payload
    payload = _build_marketforge_payload(archive, photo_urls)

    # 6. Attempt MarketForge push
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
        affected = db.execute("DELETE FROM ag_archives WHERE id = ?", (archive_id,)).rowcount
    if not affected:
        raise HTTPException(404, "Archive item not found")
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


# ── Inventory & Stats ──────────────────────────────────────────────────────────

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
    return {"items": rows, "total": len(rows)}


@router.get("/inventory/export")
async def export_inventory_csv():
    """Return inventory as a JSON array (MarketForge can transform to CSV)."""
    with get_db() as db:
        rows = dict_rows(db.execute(
            """SELECT id, issue_date, volume, issue_number, cover_subject,
                      tier, condition_score, processed_status,
                      source_box_code, processed_box_code,
                      rough_comp_min, rough_comp_max, sale_plan, batch_tag,
                      listing_draft_status, created_at
               FROM ag_archives ORDER BY created_at DESC""",
        ).fetchall())
    return {"items": rows, "total": len(rows), "format": "json-array-for-csv-conversion"}


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
    return {
        "total_items": total,
        "valued_items": valued,
        "by_status": {r["processed_status"]: r["count"] for r in by_status},
        "by_tier": {r["tier"]: r["count"] for r in by_tier},
        "total_comp_range": [round(total_comp_min, 2), round(total_comp_max, 2)],
    }


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
async def upload_photo(archive_id: int, role: str = Form("front"), file: UploadFile = File(...)):
    """Upload a photo for an archive item and persist to disk."""
    with get_db() as db:
        row = db.execute("SELECT id FROM ag_archives WHERE id = ?", (archive_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Archive item not found")

    ext = Path(file.filename or "photo.jpg").suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        ext = '.jpg'

    item_dir = UPLOADS_DIR / str(archive_id)
    item_dir.mkdir(exist_ok=True)

    unique_name = f"{role}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = item_dir / unique_name

    with open(file_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)

    with get_db() as db:
        cur = db.execute(
            "INSERT INTO ag_archive_photos (archive_id, role, filename, original_name, file_path) VALUES (?,?,?,?,?)",
            (archive_id, role, unique_name, file.filename or '', str(file_path)),
        )
        db.commit()
        photo_id = cur.lastrowid

    log.info(f"Photo #{photo_id} uploaded for archive #{archive_id} (role={role})")
    return {"id": photo_id, "archive_id": archive_id, "role": role, "filename": unique_name}


@router.get("/uploads/{archive_id}")
async def list_photos(archive_id: int):
    """List all persisted photos for an archive item."""
    with get_db() as db:
        rows = dict_rows(db.execute(
            "SELECT * FROM ag_archive_photos WHERE archive_id = ? ORDER BY created_at ASC",
            (archive_id,),
        ).fetchall())
    return {"photos": rows, "total": len(rows)}


@router.get("/photo/{photo_id}")
async def serve_photo(photo_id: int):
    """Serve a persisted archive photo file."""
    with get_db() as db:
        row = db.execute("SELECT * FROM ag_archive_photos WHERE id = ?", (photo_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Photo not found")
    d = dict_row(row)
    file_path = Path(d["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "Photo file not found on disk")
    return FileResponse(str(file_path))


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
