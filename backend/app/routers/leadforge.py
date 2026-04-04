"""
LeadForge — Aggressive lead generation & sales machine.
Finds prospects, reaches out, follows up, and converts.
Tables auto-created on import. All tables prefixed lf_.
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# ── DB Setup ──────────────────────────────────────────────────────────

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path(__file__).resolve().parent.parent.parent / "data" / "empire.db"),
)


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


def _dict(row):
    if row is None:
        return None
    d = dict(row)
    for k in ("score_factors", "tags", "follow_up_sequence"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _dicts(rows):
    return [_dict(r) for r in rows]


# ── Table creation ────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lf_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_unit TEXT NOT NULL DEFAULT 'empire_saas'
        CHECK(business_unit IN ('workroom','woodcraft','empire_saas')),
    first_name TEXT,
    last_name TEXT,
    company TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    source TEXT,
    source_url TEXT,
    score INTEGER DEFAULT 0 CHECK(score BETWEEN 0 AND 100),
    score_factors TEXT DEFAULT '{}',
    status TEXT DEFAULT 'new'
        CHECK(status IN ('new','contacted','responded','qualified',
              'proposal_sent','negotiating','won','lost','nurture')),
    temperature TEXT DEFAULT 'cold'
        CHECK(temperature IN ('cold','warm','hot')),
    estimated_value REAL DEFAULT 0,
    assigned_to TEXT,
    tags TEXT DEFAULT '[]',
    notes TEXT,
    next_action TEXT,
    next_action_date TEXT,
    last_contacted TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lf_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES lf_leads(id) ON DELETE CASCADE,
    type TEXT NOT NULL
        CHECK(type IN ('email_sent','email_received','call_made','call_received',
              'sms_sent','social_dm','site_visit','proposal_sent','meeting','note')),
    channel TEXT,
    subject TEXT,
    content TEXT,
    ai_generated INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    scheduled_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lf_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    business_unit TEXT DEFAULT 'empire_saas',
    target_audience TEXT,
    channel TEXT,
    template_subject TEXT,
    template_body TEXT,
    follow_up_sequence TEXT DEFAULT '[]',
    status TEXT DEFAULT 'draft'
        CHECK(status IN ('draft','active','paused','completed')),
    total_leads INTEGER DEFAULT 0,
    sent INTEGER DEFAULT 0,
    opened INTEGER DEFAULT 0,
    responded INTEGER DEFAULT 0,
    converted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lf_prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER REFERENCES lf_campaigns(id) ON DELETE SET NULL,
    name TEXT,
    business_name TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    platform TEXT,
    platform_url TEXT,
    location TEXT,
    category TEXT,
    imported_at TEXT DEFAULT (datetime('now')),
    converted_to_lead INTEGER DEFAULT 0,
    lead_id INTEGER REFERENCES lf_leads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS lf_followup_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES lf_leads(id) ON DELETE CASCADE,
    campaign_id INTEGER REFERENCES lf_campaigns(id) ON DELETE SET NULL,
    sequence_step INTEGER DEFAULT 1,
    channel TEXT,
    subject TEXT,
    body TEXT,
    scheduled_for TEXT,
    sent INTEGER DEFAULT 0,
    sent_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def _init_tables():
    with _db() as conn:
        conn.executescript(_SCHEMA)


_init_tables()

# ── Router ────────────────────────────────────────────────────────────

router = APIRouter(prefix="/leads", tags=["leadforge"])


# ── Pydantic models ───────────────────────────────────────────────────

class LeadCreate(BaseModel):
    business_unit: str = "empire_saas"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    score: int = 0
    score_factors: Optional[dict] = None
    status: str = "new"
    temperature: str = "cold"
    estimated_value: float = 0
    assigned_to: Optional[str] = None
    tags: Optional[list] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[str] = None


class LeadUpdate(BaseModel):
    business_unit: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    estimated_value: Optional[float] = None
    assigned_to: Optional[str] = None
    tags: Optional[list] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


class ScoreUpdate(BaseModel):
    score: int = Field(ge=0, le=100)
    score_factors: Optional[dict] = None


class ActivityCreate(BaseModel):
    type: str
    channel: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    ai_generated: bool = False
    status: str = "completed"
    scheduled_at: Optional[str] = None
    completed_at: Optional[str] = None


class CampaignCreate(BaseModel):
    name: str
    business_unit: str = "empire_saas"
    target_audience: Optional[str] = None
    channel: Optional[str] = None
    template_subject: Optional[str] = None
    template_body: Optional[str] = None
    follow_up_sequence: Optional[list] = None
    status: str = "draft"


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    business_unit: Optional[str] = None
    target_audience: Optional[str] = None
    channel: Optional[str] = None
    template_subject: Optional[str] = None
    template_body: Optional[str] = None
    follow_up_sequence: Optional[list] = None
    status: Optional[str] = None


class ProspectSearch(BaseModel):
    business_unit: str = "empire_saas"
    industry: Optional[str] = None
    location: Optional[str] = None
    platform: str = "google_maps"
    keywords: Optional[str] = None
    max_results: int = 20


class EnrichRequest(BaseModel):
    lead_id: int


class ScoreRequest(BaseModel):
    lead_id: int


class OutreachDraft(BaseModel):
    lead_id: int
    channel: str = "email"
    tone: str = "professional"


class FollowupDraft(BaseModel):
    lead_id: int
    previous_activity_id: Optional[int] = None
    channel: str = "email"


class PipelineAnalysis(BaseModel):
    business_unit: Optional[str] = None


# ── CRUD: Leads ───────────────────────────────────────────────────────

@router.get("/")
def list_leads(
    business_unit: Optional[str] = None,
    status: Optional[str] = None,
    temperature: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = None,
    assigned_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List leads with filters."""
    clauses, params = [], []
    if business_unit:
        clauses.append("business_unit = ?"); params.append(business_unit)
    if status:
        clauses.append("status = ?"); params.append(status)
    if temperature:
        clauses.append("temperature = ?"); params.append(temperature)
    if source:
        clauses.append("source = ?"); params.append(source)
    if min_score is not None:
        clauses.append("score >= ?"); params.append(min_score)
    if assigned_to:
        clauses.append("assigned_to = ?"); params.append(assigned_to)
    if search:
        clauses.append(
            "(first_name LIKE ? OR last_name LIKE ? OR company LIKE ? OR email LIKE ?)"
        )
        q = f"%{search}%"
        params.extend([q, q, q, q])

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with _db() as conn:
        rows = conn.execute(
            f"SELECT * FROM lf_leads{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM lf_leads{where}", params
        ).fetchone()[0]
    return {"leads": _dicts(rows), "total": total}


@router.post("/")
def create_lead(lead: LeadCreate):
    """Create a new lead."""
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO lf_leads
               (business_unit, first_name, last_name, company, email, phone,
                address, city, state, zip, source, source_url, score,
                score_factors, status, temperature, estimated_value,
                assigned_to, tags, notes, next_action, next_action_date)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                lead.business_unit, lead.first_name, lead.last_name,
                lead.company, lead.email, lead.phone, lead.address,
                lead.city, lead.state, lead.zip, lead.source, lead.source_url,
                lead.score, json.dumps(lead.score_factors or {}),
                lead.status, lead.temperature, lead.estimated_value,
                lead.assigned_to, json.dumps(lead.tags or []),
                lead.notes, lead.next_action, lead.next_action_date,
            ),
        )
        row = conn.execute(
            "SELECT * FROM lf_leads WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return {"lead": _dict(row)}


@router.get("/pipeline")
def get_pipeline(business_unit: Optional[str] = None):
    """Pipeline view — counts per status."""
    clause = " WHERE business_unit = ?" if business_unit else ""
    params = [business_unit] if business_unit else []
    with _db() as conn:
        rows = conn.execute(
            f"""SELECT status, COUNT(*) as count,
                       SUM(estimated_value) as total_value
                FROM lf_leads{clause}
                GROUP BY status ORDER BY
                CASE status
                    WHEN 'new' THEN 1 WHEN 'contacted' THEN 2
                    WHEN 'responded' THEN 3 WHEN 'qualified' THEN 4
                    WHEN 'proposal_sent' THEN 5 WHEN 'negotiating' THEN 6
                    WHEN 'won' THEN 7 WHEN 'lost' THEN 8 WHEN 'nurture' THEN 9
                END""",
            params,
        ).fetchall()
    return {"pipeline": _dicts(rows)}


@router.get("/hot")
def get_hot_leads(limit: int = Query(20, ge=1, le=100)):
    """Hot leads — score >= 70 or temperature = hot."""
    with _db() as conn:
        rows = conn.execute(
            """SELECT * FROM lf_leads
               WHERE (score >= 70 OR temperature = 'hot')
                 AND status NOT IN ('won','lost')
               ORDER BY score DESC, updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"leads": _dicts(rows), "total": len(rows)}


@router.get("/stale")
def get_stale_leads(days: int = Query(7, ge=1)):
    """Leads with no activity for N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _db() as conn:
        rows = conn.execute(
            """SELECT * FROM lf_leads
               WHERE status NOT IN ('won','lost')
                 AND (last_contacted IS NULL OR last_contacted < ?)
               ORDER BY last_contacted ASC NULLS FIRST""",
            (cutoff,),
        ).fetchall()
    return {"leads": _dicts(rows), "total": len(rows), "stale_days": days}


@router.get("/{lead_id}")
def get_lead(lead_id: int):
    """Get a single lead."""
    with _db() as conn:
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (lead_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    return {"lead": _dict(row)}


@router.put("/{lead_id}")
def update_lead(lead_id: int, update: LeadUpdate):
    """Full update a lead."""
    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "No fields to update")
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM lf_leads WHERE id = ?", (lead_id,)).fetchone():
            raise HTTPException(404, "Lead not found")
        sets, vals = [], []
        for k, v in data.items():
            if k == "tags":
                v = json.dumps(v)
            sets.append(f"{k} = ?")
            vals.append(v)
        sets.append("updated_at = datetime('now')")
        vals.append(lead_id)
        conn.execute(f"UPDATE lf_leads SET {', '.join(sets)} WHERE id = ?", vals)
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (lead_id,)).fetchone()
    return {"lead": _dict(row)}


@router.patch("/{lead_id}/status")
def update_lead_status(lead_id: int, body: StatusUpdate):
    """Update lead status."""
    valid = ('new', 'contacted', 'responded', 'qualified',
             'proposal_sent', 'negotiating', 'won', 'lost', 'nurture')
    if body.status not in valid:
        raise HTTPException(400, f"status must be one of {valid}")
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM lf_leads WHERE id = ?", (lead_id,)).fetchone():
            raise HTTPException(404, "Lead not found")
        conn.execute(
            "UPDATE lf_leads SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (body.status, lead_id),
        )
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (lead_id,)).fetchone()
    return {"lead": _dict(row)}


@router.patch("/{lead_id}/score")
def update_lead_score(lead_id: int, body: ScoreUpdate):
    """Update lead score."""
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM lf_leads WHERE id = ?", (lead_id,)).fetchone():
            raise HTTPException(404, "Lead not found")
        temp = "hot" if body.score >= 70 else ("warm" if body.score >= 40 else "cold")
        conn.execute(
            """UPDATE lf_leads SET score = ?, score_factors = ?, temperature = ?,
               updated_at = datetime('now') WHERE id = ?""",
            (body.score, json.dumps(body.score_factors or {}), temp, lead_id),
        )
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (lead_id,)).fetchone()
    return {"lead": _dict(row)}


# ── Activities ────────────────────────────────────────────────────────

@router.get("/{lead_id}/activities")
def list_activities(lead_id: int):
    """List activities for a lead."""
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM lf_leads WHERE id = ?", (lead_id,)).fetchone():
            raise HTTPException(404, "Lead not found")
        rows = conn.execute(
            "SELECT * FROM lf_activities WHERE lead_id = ? ORDER BY created_at DESC",
            (lead_id,),
        ).fetchall()
    return {"activities": _dicts(rows)}


@router.post("/{lead_id}/activities")
def create_activity(lead_id: int, act: ActivityCreate):
    """Log an activity for a lead."""
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM lf_leads WHERE id = ?", (lead_id,)).fetchone():
            raise HTTPException(404, "Lead not found")
        cur = conn.execute(
            """INSERT INTO lf_activities
               (lead_id, type, channel, subject, content, ai_generated, status,
                scheduled_at, completed_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                lead_id, act.type, act.channel, act.subject, act.content,
                1 if act.ai_generated else 0, act.status,
                act.scheduled_at, act.completed_at,
            ),
        )
        # Update last_contacted on the lead
        conn.execute(
            "UPDATE lf_leads SET last_contacted = datetime('now'), updated_at = datetime('now') WHERE id = ?",
            (lead_id,),
        )
        row = conn.execute(
            "SELECT * FROM lf_activities WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return {"activity": _dict(row)}


# ── AI Endpoints (stubs — realistic placeholders) ────────────────────

@router.post("/ai/find-prospects")
def ai_find_prospects(req: ProspectSearch):
    """AI-powered prospect finder. Stub returns sample data."""
    now = datetime.utcnow().isoformat()
    industry = req.industry or "general services"
    loc = req.location or "Washington, DC"

    samples = [
        {
            "name": "Maria Rodriguez",
            "business_name": "Rodriguez Interior Design",
            "email": "maria@rodriguezdesign.com",
            "phone": "(202) 555-0142",
            "website": "https://rodriguezdesign.com",
            "platform": req.platform,
            "platform_url": f"https://maps.google.com/place/rodriguez-design",
            "location": loc,
            "category": industry,
            "relevance_score": 92,
            "reason": f"Active {industry} business in {loc}, recently posted about needing new suppliers",
        },
        {
            "name": "James Thompson",
            "business_name": "Thompson & Associates Architects",
            "email": "james@thompsonarch.com",
            "phone": "(301) 555-0198",
            "website": "https://thompsonarch.com",
            "platform": req.platform,
            "platform_url": f"https://maps.google.com/place/thompson-architects",
            "location": loc,
            "category": industry,
            "relevance_score": 87,
            "reason": "Architecture firm handling luxury residential projects, high-value potential",
        },
        {
            "name": "Sarah Chen",
            "business_name": "Chen Home Staging",
            "email": "sarah@chenstaging.com",
            "phone": "(703) 555-0267",
            "website": "https://chenstaging.com",
            "platform": req.platform,
            "platform_url": f"https://maps.google.com/place/chen-staging",
            "location": loc,
            "category": industry,
            "relevance_score": 81,
            "reason": "Home staging company that regularly needs custom window treatments and upholstery",
        },
        {
            "name": "David Park",
            "business_name": "Park Property Management",
            "email": "david@parkproperties.com",
            "phone": "(202) 555-0311",
            "website": "https://parkproperties.com",
            "platform": req.platform,
            "platform_url": f"https://maps.google.com/place/park-properties",
            "location": loc,
            "category": industry,
            "relevance_score": 78,
            "reason": "Manages 40+ rental properties, repeat business potential for furnishing/repairs",
        },
        {
            "name": "Lisa Washington",
            "business_name": "Elegant Events DC",
            "email": "lisa@eleganteventsdc.com",
            "phone": "(202) 555-0455",
            "website": "https://eleganteventsdc.com",
            "platform": req.platform,
            "platform_url": f"https://maps.google.com/place/elegant-events-dc",
            "location": loc,
            "category": industry,
            "relevance_score": 74,
            "reason": "Event planning company, seasonal demand for custom drapes and decor",
        },
    ]

    prospects = samples[: req.max_results]
    return {
        "prospects": prospects,
        "total_found": len(prospects),
        "search_params": req.model_dump(),
        "ai_note": f"Found {len(prospects)} prospects in {loc} matching '{industry}'. "
                   "Review and import the best matches as leads.",
        "generated_at": now,
    }


@router.post("/ai/enrich")
def ai_enrich_lead(req: EnrichRequest):
    """AI enrichment — adds data from web search. Stub."""
    with _db() as conn:
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (req.lead_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    lead = _dict(row)
    return {
        "lead_id": req.lead_id,
        "enrichment": {
            "company_size": "10-50 employees",
            "annual_revenue": "$500K - $2M (estimated)",
            "industry": "Interior Design & Home Services",
            "linkedin_url": f"https://linkedin.com/company/{(lead.get('company') or 'unknown').lower().replace(' ', '-')}",
            "social_profiles": {
                "instagram": f"@{(lead.get('company') or 'unknown').lower().replace(' ', '')}",
                "facebook": f"facebook.com/{(lead.get('company') or 'unknown').lower().replace(' ', '')}",
            },
            "recent_activity": [
                "Posted 3 job listings in last 30 days — growing",
                "Active on Instagram with 2.3K followers",
                "Website updated within last 7 days",
            ],
            "decision_maker": lead.get("first_name", "Contact") + " " + (lead.get("last_name") or ""),
            "recommended_score_adjustment": "+15 (growth signals detected)",
        },
        "ai_note": "Enrichment complete. Company shows growth signals — recommend upgrading temperature to warm.",
    }


@router.post("/ai/score")
def ai_score_lead(req: ScoreRequest):
    """AI lead scoring. Stub returns calculated score."""
    with _db() as conn:
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (req.lead_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    lead = _dict(row)

    factors = {
        "email_provided": 15 if lead.get("email") else 0,
        "phone_provided": 10 if lead.get("phone") else 0,
        "company_identified": 10 if lead.get("company") else 0,
        "location_match": 15,
        "industry_fit": 20,
        "engagement_signals": 12,
        "budget_indicators": 8,
    }
    total = min(sum(factors.values()), 100)
    temp = "hot" if total >= 70 else ("warm" if total >= 40 else "cold")

    # Actually update the lead
    with _db() as conn:
        conn.execute(
            """UPDATE lf_leads SET score = ?, score_factors = ?, temperature = ?,
               updated_at = datetime('now') WHERE id = ?""",
            (total, json.dumps(factors), temp, req.lead_id),
        )

    return {
        "lead_id": req.lead_id,
        "score": total,
        "temperature": temp,
        "factors": factors,
        "ai_note": f"Lead scored {total}/100 ({temp}). "
                   f"{'Ready for outreach!' if total >= 70 else 'Needs more qualification.' if total >= 40 else 'Consider nurture sequence.'}",
    }


@router.post("/ai/draft-outreach")
def ai_draft_outreach(req: OutreachDraft):
    """AI-drafted initial outreach message. Stub."""
    with _db() as conn:
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (req.lead_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    lead = _dict(row)

    first = lead.get("first_name") or "there"
    company = lead.get("company") or "your company"
    bu = lead.get("business_unit", "empire_saas")

    service_map = {
        "workroom": ("custom window treatments, upholstery, and drapery", "Empire Workroom"),
        "woodcraft": ("custom woodwork, CNC fabrication, and furniture", "WoodCraft"),
        "empire_saas": ("business automation and AI-powered tools", "EmpireBox"),
    }
    service_desc, brand = service_map.get(bu, service_map["empire_saas"])

    if req.channel == "email":
        draft = {
            "subject": f"Quick question about {company}'s upcoming projects",
            "body": (
                f"Hi {first},\n\n"
                f"I came across {company} and was impressed by your work. "
                f"We specialize in {service_desc} and have helped similar businesses "
                f"save 30-40% on their project timelines.\n\n"
                f"Would you have 15 minutes this week for a quick call? "
                f"I'd love to learn about your current projects and see if there's a fit.\n\n"
                f"Best regards,\n{brand} Team"
            ),
            "channel": "email",
        }
    elif req.channel == "sms":
        draft = {
            "body": (
                f"Hi {first}, this is the {brand} team. "
                f"We help businesses like {company} with {service_desc}. "
                f"Would love to chat about your upcoming projects. Free for a quick call?"
            ),
            "channel": "sms",
        }
    else:
        draft = {
            "body": (
                f"Hi {first}! Love what {company} is doing. "
                f"We work with similar businesses providing {service_desc}. "
                f"Would you be open to connecting?"
            ),
            "channel": req.channel,
        }

    return {
        "lead_id": req.lead_id,
        "draft": draft,
        "tone": req.tone,
        "ai_note": "Draft ready for review. Personalize with specific details about their recent projects for best results.",
    }


@router.post("/ai/draft-followup")
def ai_draft_followup(req: FollowupDraft):
    """AI-drafted follow-up message. Stub."""
    with _db() as conn:
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (req.lead_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    lead = _dict(row)

    first = lead.get("first_name") or "there"
    company = lead.get("company") or "your company"

    draft = {
        "subject": f"Following up — {company}",
        "body": (
            f"Hi {first},\n\n"
            f"I wanted to follow up on my previous message. I understand you're busy, "
            f"so I'll keep this brief.\n\n"
            f"We recently completed a project similar to what {company} does, "
            f"and the client saw a 25% improvement in their workflow. "
            f"I thought you might find it relevant.\n\n"
            f"Would a 10-minute call work sometime this week? "
            f"Happy to work around your schedule.\n\n"
            f"Best,\nEmpire Team"
        ),
        "channel": req.channel,
    }

    return {
        "lead_id": req.lead_id,
        "draft": draft,
        "followup_number": 2,
        "ai_note": "Follow-up adds social proof and lowers commitment ask to 10 minutes. Send within 3-5 days of initial outreach.",
    }


@router.post("/ai/analyze-pipeline")
def ai_analyze_pipeline(req: PipelineAnalysis):
    """AI pipeline analysis with recommendations. Stub."""
    clause = " WHERE business_unit = ?" if req.business_unit else ""
    params = [req.business_unit] if req.business_unit else []

    with _db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM lf_leads{clause}", params).fetchone()[0]
        by_status = conn.execute(
            f"SELECT status, COUNT(*) as cnt, SUM(estimated_value) as val FROM lf_leads{clause} GROUP BY status",
            params,
        ).fetchall()
        hot_count = conn.execute(
            f"SELECT COUNT(*) FROM lf_leads{clause}{' AND' if clause else ' WHERE'} temperature = 'hot'",
            params,
        ).fetchone()[0]
        stale_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        stale_count = conn.execute(
            f"""SELECT COUNT(*) FROM lf_leads{clause}
                {' AND' if clause else ' WHERE'} status NOT IN ('won','lost')
                AND (last_contacted IS NULL OR last_contacted < ?)""",
            params + [stale_cutoff],
        ).fetchone()[0]

    status_data = {r["status"]: {"count": r["cnt"], "value": r["val"] or 0} for r in by_status}

    won = status_data.get("won", {}).get("count", 0)
    lost = status_data.get("lost", {}).get("count", 0)
    conv_rate = round(won / max(won + lost, 1) * 100, 1)

    recommendations = []
    if stale_count > 0:
        recommendations.append(f"ACTION: {stale_count} leads are stale (no contact in 7+ days). Schedule follow-ups immediately.")
    if hot_count > 0:
        recommendations.append(f"PRIORITY: {hot_count} hot leads need immediate attention — call today.")
    new_count = status_data.get("new", {}).get("count", 0)
    if new_count > 5:
        recommendations.append(f"BOTTLENECK: {new_count} new leads haven't been contacted. Assign and reach out within 24h.")
    if conv_rate < 20:
        recommendations.append("CONCERN: Conversion rate below 20%. Review qualification criteria and outreach messaging.")
    if not recommendations:
        recommendations.append("Pipeline is healthy. Keep up the momentum.")

    return {
        "total_leads": total,
        "by_status": status_data,
        "hot_leads": hot_count,
        "stale_leads": stale_count,
        "conversion_rate": conv_rate,
        "total_pipeline_value": sum(s.get("value", 0) for s in status_data.values()),
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ── Campaigns ─────────────────────────────────────────────────────────

@router.get("/campaigns")
def list_campaigns(
    status: Optional[str] = None,
    business_unit: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """List campaigns."""
    clauses, params = [], []
    if status:
        clauses.append("status = ?"); params.append(status)
    if business_unit:
        clauses.append("business_unit = ?"); params.append(business_unit)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with _db() as conn:
        rows = conn.execute(
            f"SELECT * FROM lf_campaigns{where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
    return {"campaigns": _dicts(rows), "total": len(rows)}


@router.post("/campaigns")
def create_campaign(camp: CampaignCreate):
    """Create a campaign."""
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO lf_campaigns
               (name, business_unit, target_audience, channel,
                template_subject, template_body, follow_up_sequence, status)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                camp.name, camp.business_unit, camp.target_audience, camp.channel,
                camp.template_subject, camp.template_body,
                json.dumps(camp.follow_up_sequence or []), camp.status,
            ),
        )
        row = conn.execute(
            "SELECT * FROM lf_campaigns WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return {"campaign": _dict(row)}


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: int):
    """Get a single campaign."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM lf_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Campaign not found")
    return {"campaign": _dict(row)}


@router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, update: CampaignUpdate):
    """Update a campaign."""
    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(400, "No fields to update")
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM lf_campaigns WHERE id = ?", (campaign_id,)).fetchone():
            raise HTTPException(404, "Campaign not found")
        sets, vals = [], []
        for k, v in data.items():
            if k == "follow_up_sequence":
                v = json.dumps(v)
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(campaign_id)
        conn.execute(f"UPDATE lf_campaigns SET {', '.join(sets)} WHERE id = ?", vals)
        row = conn.execute(
            "SELECT * FROM lf_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
    return {"campaign": _dict(row)}


@router.post("/campaigns/{campaign_id}/launch")
def launch_campaign(campaign_id: int):
    """Activate a campaign."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM lf_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Campaign not found")
        if row["status"] not in ("draft", "paused"):
            raise HTTPException(400, f"Cannot launch campaign in '{row['status']}' status")
        conn.execute(
            "UPDATE lf_campaigns SET status = 'active' WHERE id = ?", (campaign_id,)
        )
        row = conn.execute(
            "SELECT * FROM lf_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
    return {"campaign": _dict(row), "message": "Campaign launched"}


@router.post("/campaigns/{campaign_id}/pause")
def pause_campaign(campaign_id: int):
    """Pause an active campaign."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM lf_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Campaign not found")
        if row["status"] != "active":
            raise HTTPException(400, "Only active campaigns can be paused")
        conn.execute(
            "UPDATE lf_campaigns SET status = 'paused' WHERE id = ?", (campaign_id,)
        )
        row = conn.execute(
            "SELECT * FROM lf_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
    return {"campaign": _dict(row), "message": "Campaign paused"}


# ── Follow-up Queue ──────────────────────────────────────────────────

@router.get("/followups/queue")
def get_followup_queue(
    pending_only: bool = True,
    limit: int = Query(50, ge=1, le=200),
):
    """Get follow-up queue."""
    clause = " WHERE sent = 0" if pending_only else ""
    with _db() as conn:
        rows = conn.execute(
            f"""SELECT q.*, l.first_name, l.last_name, l.company, l.email
                FROM lf_followup_queue q
                JOIN lf_leads l ON l.id = q.lead_id
                {clause}
                ORDER BY q.scheduled_for ASC LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"queue": _dicts(rows), "total": len(rows)}


@router.post("/followups/process")
def process_followups():
    """Process due follow-ups. Stub — marks as sent."""
    now = datetime.utcnow().isoformat()
    with _db() as conn:
        due = conn.execute(
            """SELECT * FROM lf_followup_queue
               WHERE sent = 0 AND scheduled_for <= ?""",
            (now,),
        ).fetchall()
        processed = 0
        for item in due:
            conn.execute(
                "UPDATE lf_followup_queue SET sent = 1, sent_at = ? WHERE id = ?",
                (now, item["id"]),
            )
            # Log activity
            conn.execute(
                """INSERT INTO lf_activities
                   (lead_id, type, channel, subject, content, ai_generated, status, completed_at)
                   VALUES (?, 'email_sent', ?, ?, ?, 1, 'sent', ?)""",
                (item["lead_id"], item["channel"], item["subject"], item["body"], now),
            )
            conn.execute(
                "UPDATE lf_leads SET last_contacted = ?, updated_at = ? WHERE id = ?",
                (now, now, item["lead_id"]),
            )
            processed += 1
    return {"processed": processed, "message": f"Processed {processed} follow-ups"}


@router.patch("/followups/{followup_id}/skip")
def skip_followup(followup_id: int):
    """Skip a queued follow-up."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM lf_followup_queue WHERE id = ?", (followup_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Follow-up not found")
        conn.execute(
            "UPDATE lf_followup_queue SET sent = -1, sent_at = datetime('now') WHERE id = ?",
            (followup_id,),
        )
    return {"status": "skipped", "followup_id": followup_id}


# ── Reports ───────────────────────────────────────────────────────────

@router.get("/reports/conversion")
def report_conversion(business_unit: Optional[str] = None):
    """Conversion report."""
    clause = " WHERE business_unit = ?" if business_unit else ""
    params = [business_unit] if business_unit else []
    with _db() as conn:
        rows = conn.execute(
            f"""SELECT status, COUNT(*) as count, SUM(estimated_value) as value
                FROM lf_leads{clause} GROUP BY status""",
            params,
        ).fetchall()
    data = {r["status"]: {"count": r["count"], "value": r["value"] or 0} for r in rows}
    won = data.get("won", {}).get("count", 0)
    total_closed = won + data.get("lost", {}).get("count", 0)
    return {
        "by_status": data,
        "conversion_rate": round(won / max(total_closed, 1) * 100, 1),
        "total_won_value": data.get("won", {}).get("value", 0),
    }


@router.get("/reports/sources")
def report_sources(business_unit: Optional[str] = None):
    """Source effectiveness report."""
    clause = " WHERE business_unit = ?" if business_unit else ""
    params = [business_unit] if business_unit else []
    with _db() as conn:
        rows = conn.execute(
            f"""SELECT source, COUNT(*) as count,
                       AVG(score) as avg_score,
                       SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                       SUM(estimated_value) as total_value
                FROM lf_leads{clause} GROUP BY source ORDER BY count DESC""",
            params,
        ).fetchall()
    return {"sources": _dicts(rows)}


@router.get("/reports/revenue")
def report_revenue(business_unit: Optional[str] = None):
    """Revenue report — won deals."""
    clause = " AND business_unit = ?" if business_unit else ""
    params = [business_unit] if business_unit else []
    with _db() as conn:
        won = conn.execute(
            f"""SELECT SUM(estimated_value) as total, COUNT(*) as deals,
                       AVG(estimated_value) as avg_deal
                FROM lf_leads WHERE status = 'won'{clause}""",
            params,
        ).fetchone()
        pipeline = conn.execute(
            f"""SELECT SUM(estimated_value) as total, COUNT(*) as deals
                FROM lf_leads WHERE status NOT IN ('won','lost'){clause}""",
            params,
        ).fetchone()
    return {
        "won": {
            "total_revenue": won["total"] or 0,
            "deals_closed": won["deals"] or 0,
            "avg_deal_value": round(won["avg_deal"] or 0, 2),
        },
        "pipeline": {
            "total_value": pipeline["total"] or 0,
            "active_deals": pipeline["deals"] or 0,
        },
    }


@router.get("/reports/activity")
def report_activity(days: int = Query(30, ge=1, le=365)):
    """Activity report for last N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _db() as conn:
        rows = conn.execute(
            """SELECT type, COUNT(*) as count
               FROM lf_activities WHERE created_at >= ?
               GROUP BY type ORDER BY count DESC""",
            (cutoff,),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM lf_activities WHERE created_at >= ?",
            (cutoff,),
        ).fetchone()[0]
    return {
        "period_days": days,
        "total_activities": total,
        "by_type": _dicts(rows),
    }


# ════════════════════════════════════════════════════
# PROSPECT FINDER — Real multi-service search
# ════════════════════════════════════════════════════

from pydantic import BaseModel as _BM

class ProspectSearchRequest(_BM):
    business_unit: str = "workroom"
    location: str = "DMV"
    target_type: str = "interior designers"

@router.post("/leadforge/prospects/search")
async def search_prospects(req: ProspectSearchRequest):
    """Run real multi-service prospect search (Brave + Google + Yelp)."""
    from app.services.leadforge.prospect_engine import run_prospect_search
    result = await run_prospect_search(req.business_unit, req.location, req.target_type)
    return result

@router.get("/leadforge/prospects")
def list_prospects(
    score_min: int = Query(0, ge=0, le=100),
    outreach_ready: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = 0,
):
    """List prospects with filters."""
    from app.services.leadforge.prospect_engine import get_prospects
    return {"prospects": get_prospects(
        min_score=score_min,
        outreach_ready=outreach_ready,
        limit=limit, offset=offset,
    )}

@router.get("/leadforge/prospects/stats")
def prospect_stats():
    """Prospect statistics."""
    from app.services.leadforge.prospect_engine import get_prospect_stats
    return get_prospect_stats()

@router.get("/leadforge/prospects/{prospect_id}")
def get_prospect_detail(prospect_id: int):
    """Get full prospect detail with scoring breakdown."""
    from app.services.leadforge.prospect_engine import get_prospect
    p = get_prospect(prospect_id)
    if not p:
        raise HTTPException(404, "Prospect not found")
    return p

@router.post("/leadforge/prospects/{prospect_id}/pipeline")
def add_prospect_to_pipeline(prospect_id: int, assigned_unit: Optional[str] = None):
    """Add prospect to pipeline (duplicate-safe)."""
    from app.services.leadforge.prospect_engine import add_to_pipeline
    return add_to_pipeline(prospect_id, assigned_unit)

@router.get("/leadforge/prospect-pipeline")
def list_pipeline(status: Optional[str] = None, limit: int = 50):
    """List prospect pipeline entries."""
    from app.services.leadforge.prospect_engine import get_pipeline
    return get_pipeline(status=status, limit=limit)

@router.get("/leadforge/search-runs")
def list_search_runs(limit: int = 20):
    """View past search runs with provider results."""
    from app.services.leadforge.prospect_engine import get_search_runs
    return get_search_runs(limit=limit)

@router.get("/leadforge/providers")
def list_providers():
    """Check which search providers are available."""
    from app.services.leadforge.prospect_engine import expand_location
    import os
    providers = []
    if os.getenv("BRAVE_API_KEY"):
        providers.append({"name": "brave", "status": "configured", "type": "web_search"})
    if os.getenv("GOOGLE_PLACES_API_KEY"):
        providers.append({"name": "google_places", "status": "configured", "type": "places"})
    else:
        providers.append({"name": "google_places", "status": "not_configured", "type": "places"})
    if os.getenv("YELP_FUSION_API_KEY"):
        providers.append({"name": "yelp", "status": "configured", "type": "business"})
    else:
        providers.append({"name": "yelp", "status": "not_configured", "type": "business"})
    return {
        "providers": providers,
        "configured_count": sum(1 for p in providers if p["status"] == "configured"),
        "dmv_locations": len(expand_location("DMV")),
        "nationwide_metros": len(expand_location("nationwide")),
    }
