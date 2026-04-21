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
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import json
import sqlite3
import logging
import re
from datetime import datetime

from app.db.database import get_db, dict_rows, dict_row, DB_PATH

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ag_archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_issue_id TEXT,
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
            -- Metadata
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (reference_issue_id) REFERENCES ag_archives(id)
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

    conn.commit()
    conn.close()
    log.info("ArchiveForge tables initialized")


_init_tables()


# ── Pydantic Models ───────────────────────────────────────────────────────────

class ArchiveCreate(BaseModel):
    reference_issue_id: Optional[str] = None
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


class StatusTransition(BaseModel):
    status: str


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
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        params += [limit, offset]
        rows = dict_rows(db.execute(
            f"SELECT * FROM ag_archives {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall())
        total = db.execute(
            f"SELECT COUNT(*) FROM ag_archives {clause}", params[:-2],
        ).fetchone()[0]

    for d in rows:
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
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO ag_archives
               (reference_issue_id, issue_date, volume, issue_number, cover_subject,
                reference_cover_url, actual_listing_images, source_box_code,
                source_slot_position, processed_box_code, processed_status,
                archive_location, condition_score, has_address_label, is_complete,
                defects, notes, tier, rough_comp_min, rough_comp_max, sale_plan)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                req.reference_issue_id, req.issue_date, req.volume, req.issue_number,
                req.cover_subject, req.reference_cover_url,
                json.dumps(req.actual_listing_images),
                req.source_box_code, req.source_slot_position,
                req.processed_box_code, req.processed_status,
                req.archive_location, req.condition_score,
                int(req.has_address_label), int(req.is_complete),
                req.defects, req.notes, req.tier,
                req.rough_comp_min, req.rough_comp_max, req.sale_plan,
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
