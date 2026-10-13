"""Public LeadForge quote intake.

Creates a new lead from a Link-in-Bio quote form. Isolated from the
operator LeadForge write surfaces except for the shared lf_leads table
when EMPIRE_TASK_DB / LEADFORGE_PUBLIC_DB points at the same file.

Tests must set LEADFORGE_PUBLIC_DB or EMPIRE_TASK_DB to a temp path so
this module never writes the live empire.db.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.middleware.rate_limiter import limiter
from app.routers.linkinbio import resolve_business

router = APIRouter(prefix="/leadforge/public", tags=["leadforge-public"])

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
"""


def _db_path() -> str:
    return os.getenv("LEADFORGE_PUBLIC_DB") or os.getenv(
        "EMPIRE_TASK_DB",
        str(Path.home() / "empire-data" / "empire.db"),
    )


@contextmanager
def _db():
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class PublicQuoteIntake(BaseModel):
    business_slug: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    project: str = Field(..., min_length=1, max_length=2000)
    city: Optional[str] = Field(None, max_length=100)
    source_url: Optional[str] = Field(None, max_length=400)


def _split_name(name: str) -> tuple[str, str]:
    parts = (name or "").strip().split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


@limiter.limit("8/hour")
@router.post("/quote-intake")
async def public_quote_intake(request: Request, req: PublicQuoteIntake):
    """Public quote intake from a Link-in-Bio page. Creates a LeadForge lead."""
    biz = resolve_business(req.business_slug)
    if biz is None:
        raise HTTPException(status_code=404, detail="Unknown business")
    if "@" not in req.email or "." not in req.email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Invalid email address")

    first, last = _split_name(req.name)
    now = datetime.utcnow().isoformat()
    tags = json.dumps(["link_in_bio", req.business_slug])
    notes = f"Link-in-Bio quote intake ({req.business_slug}): {req.project}"
    source_url = req.source_url or f"/b/{req.business_slug}"

    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO lf_leads
               (business_unit, first_name, last_name, email, phone, city,
                source, source_url, score, score_factors, status, temperature,
                tags, notes, next_action, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                biz["business_unit"],
                first,
                last,
                req.email.strip().lower(),
                req.phone,
                req.city,
                "link_in_bio",
                source_url,
                40,
                json.dumps({"source": "link_in_bio", "slug": req.business_slug}),
                "new",
                "warm",
                tags,
                notes,
                "Review public quote intake",
                now,
                now,
            ),
        )
        lead_id = cur.lastrowid
        row = conn.execute("SELECT id, business_unit, status, source FROM lf_leads WHERE id = ?", (lead_id,)).fetchone()

    return {
        "ok": True,
        "lead_id": lead_id,
        "business_slug": req.business_slug,
        "business_unit": row["business_unit"],
        "status": row["status"],
        "source": row["source"],
        "message": "Request received. We will follow up from LeadForge.",
    }


@router.get("/config")
async def public_quote_config(business: Optional[str] = None):
    biz = resolve_business(business) if business else None
    return {
        "business": {
            "slug": biz["slug"],
            "name": biz["name"],
            "business_unit": biz["business_unit"],
        }
        if biz
        else None,
        "source": "link_in_bio",
    }
