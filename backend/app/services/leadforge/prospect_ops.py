"""
LeadForge prospect operations shared by the API and Max tools.

  outreach_score()       rank prospects by fit + reachability (contact found, email, Instagram)
  promote_to_lead()      prospect -> pipeline entry + LeadForge lead (lf_leads); idempotent
  draft_outreach()       email or Instagram DM text, saved as a DRAFT only (nothing here can send)
  daily_brief()          top new prospects: who, why, suggested first message
  segments()/segment_ids()  pipeline / prospect segments other modules can target
  social_targets()       prospects with Instagram / Facebook / LinkedIn links (SocialForge feed)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.services.leadforge import prospect_engine as pe

_UNIT_MAP = {"workroom": "workroom", "empire workroom": "workroom", "woodcraft": "woodcraft",
             "craft": "woodcraft", "empire_saas": "empire_saas", "saas": "empire_saas"}
_WORKROOM_FITS = ("designer_fit", "window_treatments_fit", "upholstery_fit", "hospitality_fit")


def _ensure_lead_link(conn) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(lf_leads)").fetchall()}
    if cols and "prospect_id" not in cols:
        conn.execute("ALTER TABLE lf_leads ADD COLUMN prospect_id INTEGER")
    if cols:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lf_leads_prospect ON lf_leads(prospect_id)")


# ── Scoring ──────────────────────────────────────────────────────────────

def outreach_score(p: dict) -> Dict[str, object]:
    """Base listing score (rating/reviews/relevance) plus reachability bonuses."""
    base = int(p.get("score") or 0)
    pts, why = 0, []
    if p.get("rating"):
        why.append(f"{p['rating']}★ from {p.get('review_count') or 0} reviews")
    fits = [f.replace("_fit", "").replace("_", " ") for f in
            ("designer_fit", "window_treatments_fit", "upholstery_fit", "hospitality_fit", "restaurant_fit",
             "gc_fit", "millwork_fit", "cabinetry_fit") if p.get(f)]
    if any(p.get(f) for f in _WORKROOM_FITS):
        pts += 5
    if fits:
        why.append("fit: " + ", ".join(fits[:3]))
    if p.get("contact_name"):
        pts += 8
        why.append(f"named contact: {p['contact_name']}" + (f" ({p['contact_title']})" if p.get("contact_title") else ""))
    if p.get("contact_email") or p.get("email"):
        pts += 8
        why.append("email found")
    if p.get("instagram"):
        pts += 4
        why.append("on Instagram")
    if p.get("phone"):
        pts += 3
    if p.get("website") and not p.get("is_directory_page"):
        pts += 3
    if p.get("is_directory_page"):
        pts -= 25
        why.append("directory/list page, not a single business")
    if p.get("display_city"):
        why.append(p["display_city"])
    return {"outreach_score": max(0, min(100, base + pts)), "base_score": base, "bonus": pts, "why": why}


def _ranked(rows: List[dict]) -> List[dict]:
    out = []
    for p in rows:
        p = pe.decorate_prospect(p)
        p.update(outreach_score(p))
        out.append(p)
    out.sort(key=lambda x: (x["outreach_score"], x.get("score") or 0), reverse=True)
    return out


def top_prospects(limit: int = 10, min_score: int = 0, only_new: bool = False, days: Optional[int] = None,
                  exclude_pipeline: bool = False) -> List[dict]:
    where, params = ["1=1"], []
    if min_score:
        where.append("p.score >= ?"); params.append(min_score)
    if days:
        where.append("p.first_seen_at >= ?"); params.append((datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"))
    if only_new:
        where.append("COALESCE(p.status, 'new') = 'new'")
    if exclude_pipeline:
        where.append("p.id NOT IN (SELECT prospect_id FROM prospect_pipeline)")
    with pe._db() as conn:
        rows = conn.execute(f"SELECT p.* FROM prospects p WHERE {' AND '.join(where)} ORDER BY p.score DESC LIMIT 600",
                            params).fetchall()
    return _ranked(pe._dicts(rows))[: max(1, min(int(limit), 100))]


def card(p: dict) -> dict:
    """Compact who-is-this summary for chat / brief."""
    return {
        "prospect_id": p["id"], "name": p.get("display_name"), "city": p.get("display_city"),
        "type": p.get("client_type"), "category": p.get("category"),
        "score": p.get("score"), "outreach_score": p.get("outreach_score"),
        "contact": ({"name": p.get("contact_name"), "title": p.get("contact_title"),
                     "email": p.get("contact_email") or p.get("email"), "phone": p.get("contact_phone") or p.get("phone")}
                    if (p.get("contact_name") or p.get("contact_email") or p.get("email")) else "unknown"),
        "phone": p.get("phone"), "website": p.get("website"), "instagram": p.get("instagram"),
        "maps_url": p.get("maps_url"), "enrichment_status": p.get("enrichment_status") or "not_run",
        "why": p.get("why", []),
    }


# ── Prospect -> pipeline -> lead ─────────────────────────────────────────

def promote_to_lead(prospect_id: int, business_unit: Optional[str] = None) -> dict:
    """Add to prospect pipeline AND create (or return) the matching LeadForge lead."""
    p = pe.get_prospect(prospect_id)
    if not p:
        return {"status": "error", "error": f"Prospect {prospect_id} not found"}
    p.update(outreach_score(p))
    unit = _UNIT_MAP.get((business_unit or "workroom").strip().lower(), "workroom")
    pipe = pe.add_to_pipeline(prospect_id, status="new", assigned_unit=unit)
    with pe._db() as conn:
        _ensure_lead_link(conn)
        row = conn.execute("SELECT id FROM lf_leads WHERE prospect_id = ? ORDER BY id LIMIT 1", (prospect_id,)).fetchone()
        if row:
            return {"status": pipe["status"], "prospect_id": prospect_id, "lead_id": row["id"], "lead_created": False}
        first = last = None
        if p.get("contact_name"):
            bits = p["contact_name"].split()
            first, last = bits[0], " ".join(bits[1:]) or None
        city_state = (p.get("display_city") or "").split(", ")
        score = int(p["outreach_score"])
        temp = "hot" if score >= 70 else ("warm" if score >= 40 else "cold")
        notes = " · ".join(x for x in (p.get("card_summary"), f"Angle: {p['recommended_angle']}" if p.get("recommended_angle") else None) if x)
        cur = conn.execute(
            """INSERT INTO lf_leads (business_unit, first_name, last_name, company, email, phone, address, city, state,
                   source, source_url, score, score_factors, status, temperature, tags, notes, intake_payload, prospect_id,
                   next_action, next_action_date)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (unit, first, last, p.get("display_name"), p.get("contact_email") or p.get("email"),
             p.get("phone") or p.get("contact_phone"), p.get("address"),
             city_state[0] or None, city_state[1] if len(city_state) > 1 else p.get("state"),
             "leadforge_prospect", p.get("website") or p.get("maps_url"), score,
             json.dumps({"base_score": p["base_score"], "bonus": p["bonus"], "why": p["why"]}),
             "new", temp, json.dumps(["prospect_finder", p.get("client_type") or "unknown"]), notes or None,
             json.dumps({"prospect_id": prospect_id, "source": p.get("source"), "instagram": p.get("instagram")}),
             prospect_id, "First contact (review the draft, then reach out)",
             (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")),
        )
        lead_id = cur.lastrowid
    return {"status": pipe["status"], "prospect_id": prospect_id, "lead_id": lead_id, "lead_created": True}


# ── Drafts (never sent from here) ────────────────────────────────────────

def _hook(p: dict) -> tuple:
    t = (p.get("client_type") or "").lower()
    n = (p.get("display_name") or p.get("name") or "").lower()
    named_designer = any(w in n for w in ("interior", "design")) and not any(w in n for w in ("remodel", "build", "kitchen", "bath", "construction"))
    if p.get("designer_fit") or t == "designer" or named_designer:
        return "your design work", "designers"
    if p.get("hospitality_fit") or p.get("restaurant_fit") or t == "commercial":
        return "your space", "hospitality and commercial projects"
    if p.get("gc_fit") or t == "contractor":
        return "your remodeling projects", "builders and remodelers"
    return "what you do", "local projects"


def compose_message(p: dict, channel: str = "email") -> Dict[str, Optional[str]]:
    first = (p.get("contact_name") or "").split()[0] if p.get("contact_name") else None
    company = p.get("display_name") or "your team"
    city = (p.get("display_city") or "").split(",")[0]
    hook, audience = _hook(p)
    angle = (p.get("recommended_angle") or "").strip().rstrip(".")
    if channel in ("instagram", "instagram_dm", "dm"):
        body = (f"Hi {first or 'there'}! Love {hook} at {company}. I run Empire Workroom"
                f"{' near ' + city if city else ''}: custom drapery, shades and upholstery for {audience}. "
                f"Open to connecting? Happy to send our trade lookbook.")
        return {"channel": "instagram_dm", "subject": None, "body": body,
                "to_address": p.get("instagram"), "to_name": p.get("contact_name") or company}
    angle_line = f"We'd be glad to be your {angle}." if angle else "We'd be glad to be your go-to workroom."
    body = (f"Hi {first or 'there'},\n\n"
            f"I came across {company}{' in ' + city if city else ''} and liked {hook}. I run Empire Workroom, "
            f"a local custom workroom (drapery, Roman shades, cushions and upholstery) that works with {audience}.\n\n"
            f"{angle_line} Would you be open to a quick call, or a visit to see fabric samples and our trade pricing?\n\n"
            f"Best,\nRafael\nEmpire Workroom")
    return {"channel": "email", "subject": f"Custom workroom partner for {company}", "body": body,
            "to_address": p.get("contact_email") or p.get("email"), "to_name": p.get("contact_name") or company}


def draft_outreach(prospect_id: int, channel: str = "email", save: bool = True) -> dict:
    p = pe.get_prospect(prospect_id)
    if not p:
        return {"status": "error", "error": f"Prospect {prospect_id} not found"}
    msg = compose_message(p, channel)
    draft_id = None
    if save:
        with pe._db() as conn:
            cur = conn.execute(
                """INSERT INTO prospect_outreach_drafts (prospect_id, channel, to_name, to_address, subject, body, status)
                   VALUES (?,?,?,?,?,?, 'draft')""",
                (prospect_id, msg["channel"], msg["to_name"], msg["to_address"], msg["subject"], msg["body"]))
            draft_id = cur.lastrowid
    queue_id = None
    if save and draft_id:
        try:  # every draft lands in the one approval queue (Rafael taps to send / copy)
            from app.services.leadforge import growth
            q = growth.enqueue(channel=msg["channel"], body=msg["body"], source="prospect_draft",
                               source_ref=str(draft_id), title=f"{msg['channel'].replace('_', ' ').title()} to {p.get('display_name') or p.get('name')}",
                               to_name=msg.get("to_name") or "", to_address=msg.get("to_address") or "",
                               subject=msg.get("subject") or "", prospect_id=prospect_id,
                               open_url=(p.get("instagram") or "") if msg["channel"] != "email" else "")
            queue_id = q["id"]
        except Exception:
            queue_id = None
    return {"status": "draft", "draft_id": draft_id, "approval_queue_id": queue_id, "prospect_id": prospect_id, **msg,
            "missing_address": not msg["to_address"],
            "send_policy": "Draft only. Nothing is sent. Ask Rafael before any send; sending is a separate, manual step."}


def list_drafts(prospect_id: Optional[int] = None, limit: int = 50) -> List[dict]:
    with pe._db() as conn:
        if prospect_id:
            rows = conn.execute("SELECT * FROM prospect_outreach_drafts WHERE prospect_id = ? ORDER BY id DESC LIMIT ?",
                                (prospect_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM prospect_outreach_drafts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return pe._dicts(rows)


# ── Daily brief ──────────────────────────────────────────────────────────

def daily_brief(limit: int = 7, days: int = 1) -> dict:
    limit = max(5, min(int(limit or 7), 10))
    picks = [p for p in top_prospects(limit=60, days=days, exclude_pipeline=True) if not p.get("is_directory_page")]
    widened = False
    if len(picks) < limit:
        # not enough brand-new rows today: widen to the best not-yet-contacted prospects
        widened = True
        seen = {p["id"] for p in picks}
        picks += [p for p in top_prospects(limit=100, exclude_pipeline=True)
                  if p["id"] not in seen and not p.get("is_directory_page")]
    items = []
    for p in picks[:limit]:
        channel = "email" if (p.get("contact_email") or p.get("email")) else ("instagram_dm" if p.get("instagram") else "email")
        msg = compose_message(p, channel)
        items.append({**card(p), "suggested_channel": msg["channel"] if msg["to_address"] else
                      ("phone" if p.get("phone") else "website_form" if p.get("website") else
                       "run prospect_enrich (discover_websites) or open the Maps link"),
                      "suggested_first_message": msg["body"], "subject": msg["subject"]})
    return {"generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z", "window_days": days,
            "widened_to_backlog": widened, "count": len(items), "items": items,
            "next_steps": "Ask Rafael which to add to the pipeline / draft. Never send without his yes."}


# ── Segments + social feed (for SocialForge / campaigns) ─────────────────

_SEGMENT_SQL = {
    "designers": "(p.designer_fit = 1 OR p.client_type = 'designer')",
    "contractors": "(p.gc_fit = 1 OR p.client_type = 'contractor')",
    "hospitality": "(p.hospitality_fit = 1 OR p.restaurant_fit = 1 OR p.client_type = 'commercial')",
    "has_email": "(COALESCE(p.contact_email, p.email, '') != '')",
    "has_instagram": "(COALESCE(p.instagram, '') != '')",
    "named_contact": "(COALESCE(p.contact_name, '') != '')",
    "phone_only": "(COALESCE(p.phone, '') != '' AND COALESCE(p.contact_email, p.email, '') = '')",
    "high_score": "(p.score >= 70)",
    "in_pipeline": "(p.id IN (SELECT prospect_id FROM prospect_pipeline))",
}


def segments(in_pipeline_only: bool = False) -> dict:
    base = "p.id IN (SELECT prospect_id FROM prospect_pipeline)" if in_pipeline_only else "1=1"
    out = {}
    with pe._db() as conn:
        for name, cond in _SEGMENT_SQL.items():
            out[name] = conn.execute(f"SELECT COUNT(*) FROM prospects p WHERE {base} AND {cond}").fetchone()[0]
        total = conn.execute(f"SELECT COUNT(*) FROM prospects p WHERE {base}").fetchone()[0]
    return {"scope": "pipeline" if in_pipeline_only else "all_prospects", "total": total, "segments": out,
            "how_to_use": "GET /api/v1/leads/leadforge/segments/{name}?in_pipeline_only=true returns the prospect list"}


def segment_members(name: str, in_pipeline_only: bool = False, limit: int = 200) -> dict:
    conds = [c for n in name.split("+") if (c := _SEGMENT_SQL.get(n.strip()))]
    if not conds:
        return {"error": f"Unknown segment '{name}'. Known: {', '.join(_SEGMENT_SQL)} (combine with +)"}
    if in_pipeline_only:
        conds.append(_SEGMENT_SQL["in_pipeline"])
    with pe._db() as conn:
        rows = conn.execute(f"SELECT p.* FROM prospects p WHERE {' AND '.join(conds)} ORDER BY p.score DESC LIMIT ?",
                            (limit,)).fetchall()
    members = [card(p) for p in _ranked(pe._dicts(rows))]
    return {"segment": name, "in_pipeline_only": in_pipeline_only, "count": len(members), "members": members}


def social_targets(limit: int = 100) -> dict:
    with pe._db() as conn:
        rows = conn.execute(
            """SELECT p.* FROM prospects p
               WHERE COALESCE(p.instagram, '') != '' OR COALESCE(p.facebook, '') != '' OR COALESCE(p.linkedin, '') != ''
               ORDER BY p.score DESC LIMIT ?""", (limit,)).fetchall()
    items = []
    for p in _ranked(pe._dicts(rows)):
        items.append({"prospect_id": p["id"], "name": p["display_name"], "city": p.get("display_city"),
                      "type": p.get("client_type"), "instagram": p.get("instagram"), "facebook": p.get("facebook"),
                      "linkedin": p.get("linkedin"), "contact_name": p.get("contact_name"),
                      "outreach_score": p["outreach_score"]})
    return {"count": len(items), "targets": items,
            "note": "Engage/follow list from LeadForge free contact lookup. DMs are drafted only, never auto-sent."}
