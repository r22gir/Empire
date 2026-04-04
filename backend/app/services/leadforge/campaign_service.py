"""
LeadForge Campaign Service — multi-step outreach campaigns with enrollment,
execution engine, outcome tracking, and follow-up management.

Tables auto-created on import (IF NOT EXISTS). Uses same empire.db as the
rest of LeadForge.
"""

import asyncio
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── DB Setup ────────────────────────────────────────────────────────────

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "empire.db"),
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
    for k in ("details",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _dicts(rows):
    return [_dict(r) for r in rows]


# ── Table Creation ──────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    business_unit TEXT NOT NULL DEFAULT 'workroom',
    target_type TEXT,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK(status IN ('draft','active','paused','completed')),
    prospects_count INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    responded_count INTEGER DEFAULT 0,
    bounced_count INTEGER DEFAULT 0,
    reply_rate REAL DEFAULT 0.0,
    send_window_start TEXT DEFAULT '08:00',
    send_window_end TEXT DEFAULT '18:00',
    skip_weekends INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS campaign_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_type TEXT NOT NULL DEFAULT 'email'
        CHECK(step_type IN ('email','follow_up_email','phone_script','linkedin','sms')),
    subject TEXT,
    body_template TEXT,
    delay_days INTEGER DEFAULT 0,
    is_manual INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS campaign_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    prospect_id INTEGER NOT NULL,
    current_step INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active','completed','responded','opted_out','bounced')),
    outcome TEXT,
    can_email INTEGER DEFAULT 1,
    can_call INTEGER DEFAULT 1,
    can_linkedin INTEGER DEFAULT 1,
    last_action_type TEXT,
    last_action_at TEXT,
    next_step_at TEXT,
    enrolled_at TEXT DEFAULT (datetime('now')),
    UNIQUE(campaign_id, prospect_id)
);

CREATE TABLE IF NOT EXISTS campaign_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    enrollment_id INTEGER,
    prospect_id INTEGER,
    step_id INTEGER,
    action_type TEXT,
    details TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def _init_tables():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _db() as conn:
        conn.executescript(_SCHEMA)


try:
    _init_tables()
except Exception as e:
    print(f"[LeadForge Campaign Service] Table init warning: {e}")


# ── Template Rendering ──────────────────────────────────────────────────

def render_template(template: str, prospect: dict) -> str:
    """Replace placeholders with prospect data. Safe fallbacks for all."""
    if not template:
        return ""
    name = prospect.get("name") or prospect.get("business_name") or "there"
    first_name = name.split()[0] if name and name != "there" else "there"
    replacements = {
        "{name}": name,
        "{first_name}": first_name,
        "{business}": prospect.get("business_name") or prospect.get("name") or "your company",
        "{location}": prospect.get("location") or prospect.get("city") or "your area",
        "{angle}": prospect.get("angle") or "custom drapery, upholstery, and millwork",
        "{phone}": prospect.get("phone") or "",
        "{website}": prospect.get("website") or "",
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, str(value))
    return result


# ── Campaign CRUD ───────────────────────────────────────────────────────

def create_campaign(data: dict) -> dict:
    """Create a new campaign."""
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO campaigns (name, description, business_unit, target_type,
               status, send_window_start, send_window_end, skip_weekends)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("name", "Untitled Campaign"),
                data.get("description"),
                data.get("business_unit", "workroom"),
                data.get("target_type"),
                data.get("status", "draft"),
                data.get("send_window_start", "08:00"),
                data.get("send_window_end", "18:00"),
                1 if data.get("skip_weekends", True) else 0,
            ),
        )
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _dict(row)


def get_campaign(campaign_id: int) -> Optional[dict]:
    """Get campaign with steps and computed stats."""
    with _db() as conn:
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if not row:
            return None
        campaign = _dict(row)

        # Steps
        steps = conn.execute(
            "SELECT * FROM campaign_steps WHERE campaign_id = ? ORDER BY step_number",
            (campaign_id,),
        ).fetchall()
        campaign["steps"] = _dicts(steps)

        # Live stats
        stats = conn.execute(
            """SELECT
                COUNT(*) as total_enrolled,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'responded' THEN 1 ELSE 0 END) as responded,
                SUM(CASE WHEN status = 'opted_out' THEN 1 ELSE 0 END) as opted_out,
                SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced
               FROM campaign_enrollments WHERE campaign_id = ?""",
            (campaign_id,),
        ).fetchone()
        campaign["enrollment_stats"] = _dict(stats)

    return campaign


def list_campaigns(status: Optional[str] = None, business_unit: Optional[str] = None) -> List[dict]:
    """List all campaigns with optional filters."""
    clauses, params = [], []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if business_unit:
        clauses.append("business_unit = ?")
        params.append(business_unit)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with _db() as conn:
        rows = conn.execute(
            f"SELECT * FROM campaigns{where} ORDER BY updated_at DESC", params
        ).fetchall()
    return _dicts(rows)


def update_campaign(campaign_id: int, data: dict) -> Optional[dict]:
    """Update campaign fields."""
    allowed = {"name", "description", "business_unit", "target_type", "status",
               "send_window_start", "send_window_end", "skip_weekends"}
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}
    if not updates:
        return get_campaign(campaign_id)
    if "skip_weekends" in updates:
        updates["skip_weekends"] = 1 if updates["skip_weekends"] else 0
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values())
    vals.append(campaign_id)
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,)).fetchone():
            return None
        conn.execute(
            f"UPDATE campaigns SET {sets}, updated_at = datetime('now') WHERE id = ?", vals
        )
    return get_campaign(campaign_id)


def delete_campaign(campaign_id: int) -> bool:
    """Delete a campaign and all related data (cascaded)."""
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,)).fetchone():
            return False
        conn.execute("DELETE FROM campaign_activity WHERE campaign_id = ?", (campaign_id,))
        conn.execute("DELETE FROM campaign_enrollments WHERE campaign_id = ?", (campaign_id,))
        conn.execute("DELETE FROM campaign_steps WHERE campaign_id = ?", (campaign_id,))
        conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    return True


# ── Step Management ─────────────────────────────────────────────────────

def add_step(campaign_id: int, data: dict) -> Optional[dict]:
    """Add a step to a campaign."""
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,)).fetchone():
            return None
        # Auto-assign step_number if not given
        step_number = data.get("step_number")
        if step_number is None:
            max_row = conn.execute(
                "SELECT COALESCE(MAX(step_number), 0) as mx FROM campaign_steps WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
            step_number = max_row["mx"] + 1
        cur = conn.execute(
            """INSERT INTO campaign_steps (campaign_id, step_number, step_type,
               subject, body_template, delay_days, is_manual)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                campaign_id,
                step_number,
                data.get("step_type", "email"),
                data.get("subject"),
                data.get("body_template"),
                data.get("delay_days", 0),
                1 if data.get("is_manual", False) else 0,
            ),
        )
        row = conn.execute("SELECT * FROM campaign_steps WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _dict(row)


def update_step(campaign_id: int, step_id: int, data: dict) -> Optional[dict]:
    """Update a campaign step."""
    allowed = {"step_number", "step_type", "subject", "body_template", "delay_days", "is_manual"}
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}
    if "is_manual" in updates:
        updates["is_manual"] = 1 if updates["is_manual"] else 0
    if not updates:
        with _db() as conn:
            row = conn.execute(
                "SELECT * FROM campaign_steps WHERE id = ? AND campaign_id = ?",
                (step_id, campaign_id),
            ).fetchone()
        return _dict(row) if row else None
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values())
    vals.extend([step_id, campaign_id])
    with _db() as conn:
        conn.execute(
            f"UPDATE campaign_steps SET {sets} WHERE id = ? AND campaign_id = ?", vals
        )
        row = conn.execute(
            "SELECT * FROM campaign_steps WHERE id = ? AND campaign_id = ?",
            (step_id, campaign_id),
        ).fetchone()
    return _dict(row) if row else None


def delete_step(campaign_id: int, step_id: int) -> bool:
    """Delete a step from a campaign."""
    with _db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM campaign_steps WHERE id = ? AND campaign_id = ?",
            (step_id, campaign_id),
        ).fetchone()
        if not existing:
            return False
        conn.execute(
            "DELETE FROM campaign_steps WHERE id = ? AND campaign_id = ?",
            (step_id, campaign_id),
        )
    return True


# ── Enrollment ──────────────────────────────────────────────────────────

def enrollment_preview(campaign_id: int, prospect_ids: List[int]) -> dict:
    """Preview enrollment impact before committing."""
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,)).fetchone():
            return {"error": "Campaign not found"}

        already_in_campaign = []
        already_in_other = []
        eligible = []

        for pid in prospect_ids:
            # Check same campaign
            dup = conn.execute(
                "SELECT id FROM campaign_enrollments WHERE campaign_id = ? AND prospect_id = ?",
                (campaign_id, pid),
            ).fetchone()
            if dup:
                already_in_campaign.append(pid)
                continue

            # Check other active campaigns
            other = conn.execute(
                """SELECT c.name FROM campaign_enrollments ce
                   JOIN campaigns c ON c.id = ce.campaign_id
                   WHERE ce.prospect_id = ? AND ce.status = 'active' AND ce.campaign_id != ?""",
                (pid, campaign_id),
            ).fetchone()
            if other:
                already_in_other.append({"prospect_id": pid, "campaign": other["name"]})
            else:
                eligible.append(pid)

        step_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM campaign_steps WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()["cnt"]

    return {
        "campaign_id": campaign_id,
        "requested": len(prospect_ids),
        "eligible": len(eligible),
        "eligible_ids": eligible,
        "already_in_campaign": already_in_campaign,
        "already_in_other_active": already_in_other,
        "step_count": step_count,
    }


def enroll_prospects(campaign_id: int, prospect_ids: List[int]) -> dict:
    """Enroll prospects into a campaign. Duplicate-safe, cross-campaign aware."""
    with _db() as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if not campaign:
            return {"error": "Campaign not found"}

        first_step = conn.execute(
            "SELECT * FROM campaign_steps WHERE campaign_id = ? ORDER BY step_number LIMIT 1",
            (campaign_id,),
        ).fetchone()

        now = datetime.utcnow().isoformat()
        next_step_at = now if first_step else None
        enrolled = []
        skipped_dup = []
        skipped_active = []

        for pid in prospect_ids:
            # Check duplicate in same campaign
            dup = conn.execute(
                "SELECT id FROM campaign_enrollments WHERE campaign_id = ? AND prospect_id = ?",
                (campaign_id, pid),
            ).fetchone()
            if dup:
                skipped_dup.append(pid)
                continue

            # Cross-campaign protection: warn but still allow
            other = conn.execute(
                """SELECT campaign_id FROM campaign_enrollments
                   WHERE prospect_id = ? AND status = 'active' AND campaign_id != ?""",
                (pid, campaign_id),
            ).fetchone()
            if other:
                skipped_active.append(pid)
                continue

            # Fetch prospect channel capabilities
            prospect = conn.execute(
                "SELECT email, phone FROM prospects WHERE id = ?", (pid,)
            ).fetchone()
            can_email = 1 if (prospect and prospect["email"]) else 0
            can_call = 1 if (prospect and prospect["phone"]) else 0

            conn.execute(
                """INSERT INTO campaign_enrollments
                   (campaign_id, prospect_id, current_step, status, can_email, can_call,
                    can_linkedin, next_step_at, enrolled_at)
                   VALUES (?, ?, 0, 'active', ?, ?, 1, ?, ?)""",
                (campaign_id, pid, can_email, can_call, next_step_at, now),
            )
            enrolled.append(pid)

        # Update prospects_count
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM campaign_enrollments WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()["cnt"]
        conn.execute(
            "UPDATE campaigns SET prospects_count = ?, updated_at = datetime('now') WHERE id = ?",
            (total, campaign_id),
        )

    return {
        "campaign_id": campaign_id,
        "enrolled": len(enrolled),
        "enrolled_ids": enrolled,
        "skipped_duplicate": skipped_dup,
        "skipped_active_elsewhere": skipped_active,
        "total_enrolled": total,
    }


def get_enrollments(campaign_id: int) -> List[dict]:
    """List enrollments for a campaign with prospect info."""
    with _db() as conn:
        rows = conn.execute(
            """SELECT ce.*, p.name, p.business_name, p.email, p.phone, p.location
               FROM campaign_enrollments ce
               LEFT JOIN prospects p ON p.id = ce.prospect_id
               WHERE ce.campaign_id = ?
               ORDER BY ce.enrolled_at DESC""",
            (campaign_id,),
        ).fetchall()
    return _dicts(rows)


# ── Execution Engine ────────────────────────────────────────────────────

def _advance_enrollment(conn, enrollment: dict):
    """Advance an enrollment to its next step or mark completed."""
    from datetime import timedelta
    now_iso = datetime.utcnow().isoformat()
    cid = enrollment["campaign_id"]
    step_num = enrollment.get("step_number", enrollment.get("current_step", 0))
    next_step = conn.execute(
        "SELECT * FROM campaign_steps WHERE campaign_id = ? AND step_number > ? ORDER BY step_number LIMIT 1",
        (cid, step_num)).fetchone()
    if next_step:
        ns = _dict(next_step)
        next_at = (datetime.utcnow() + timedelta(days=ns["delay_days"])).isoformat()
        conn.execute("UPDATE campaign_enrollments SET current_step = ?, next_step_at = ?, last_action_at = ? WHERE id = ?",
                     (step_num, next_at, now_iso, enrollment["id"]))
    else:
        conn.execute("UPDATE campaign_enrollments SET current_step = ?, status = 'completed', next_step_at = NULL, last_action_at = ? WHERE id = ?",
                     (step_num, now_iso, enrollment["id"]))


async def execute_next_steps() -> dict:
    """Find and execute all due enrollment steps. Async for non-blocking use."""
    now = datetime.utcnow()
    now_iso = now.isoformat()
    results = {"executed": 0, "skipped": 0, "errors": 0, "manual_tasks": 0, "details": []}

    # Send window check
    current_time = now.strftime("%H:%M")

    with _db() as conn:
        # Get campaigns config for window/weekend checks
        campaigns_cache = {}

        # Find due enrollments
        due = conn.execute(
            """SELECT ce.*, cs.id as step_id, cs.step_type, cs.subject, cs.body_template,
                      cs.is_manual, cs.step_number
               FROM campaign_enrollments ce
               JOIN campaign_steps cs ON cs.campaign_id = ce.campaign_id
                   AND cs.step_number = ce.current_step + 1
               WHERE ce.status = 'active'
                 AND ce.next_step_at IS NOT NULL
                 AND ce.next_step_at <= ?
               ORDER BY ce.next_step_at""",
            (now_iso,),
        ).fetchall()

        for enrollment in due:
            e = _dict(enrollment)
            cid = e["campaign_id"]

            # Cache campaign settings
            if cid not in campaigns_cache:
                c = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
                campaigns_cache[cid] = _dict(c) if c else None

            camp = campaigns_cache.get(cid)
            if not camp or camp["status"] != "active":
                results["skipped"] += 1
                results["details"].append({
                    "enrollment_id": e["id"], "reason": "campaign_not_active"
                })
                continue

            # Weekend check
            if camp.get("skip_weekends") and now.weekday() >= 5:
                results["skipped"] += 1
                results["details"].append({
                    "enrollment_id": e["id"], "reason": "weekend_skip"
                })
                continue

            # Send window check
            if current_time < camp.get("send_window_start", "08:00") or \
               current_time > camp.get("send_window_end", "18:00"):
                results["skipped"] += 1
                results["details"].append({
                    "enrollment_id": e["id"], "reason": "outside_send_window"
                })
                continue

            # Channel check
            step_type = e["step_type"]
            channel_ok = True
            if step_type in ("email", "follow_up_email") and not e.get("can_email"):
                channel_ok = False
            elif step_type == "phone_script" and not e.get("can_call"):
                channel_ok = False
            elif step_type == "linkedin" and not e.get("can_linkedin"):
                channel_ok = False

            if not channel_ok:
                # Still create the draft (founder can add contact info later)
                # but log as skipped and advance to next step
                try:
                    prospect = conn.execute("SELECT * FROM prospects WHERE id = ?", (e["prospect_id"],)).fetchone()
                    prospect_data = _dict(prospect) if prospect else {}
                    rendered_subject = render_template(e.get("subject") or "", prospect_data)
                    rendered_body = render_template(e.get("body_template") or "", prospect_data)
                    # Insert draft row for founder review
                    conn.execute("""INSERT INTO campaign_drafts
                        (campaign_id, enrollment_id, prospect_id, step_id, step_type,
                         to_email, to_name, subject, body, phone_number, script, linkedin_message, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
                        (cid, e["id"], e["prospect_id"], e["step_id"], step_type,
                         prospect_data.get("email"),
                         prospect_data.get("name") or prospect_data.get("business_name"),
                         rendered_subject, rendered_body,
                         prospect_data.get("phone"),
                         rendered_body if step_type == 'phone_script' else None,
                         rendered_body if step_type == 'linkedin' else None))
                    conn.execute("""INSERT INTO campaign_activity
                        (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
                        VALUES (?, ?, ?, ?, 'drafted_no_channel', ?)""",
                        (cid, e["id"], e["prospect_id"], e["step_id"],
                         json.dumps({"step_type": step_type, "subject": rendered_subject,
                                     "body": rendered_body[:500], "reason": f"missing {step_type} contact"})))
                    _advance_enrollment(conn, e)
                except Exception:
                    pass
                results["skipped"] += 1
                results["details"].append({
                    "enrollment_id": e["id"], "reason": f"missing_channel_{step_type}_drafted_and_advanced"
                })
                continue

            try:
                # Fetch prospect for rendering
                prospect = conn.execute(
                    "SELECT * FROM prospects WHERE id = ?", (e["prospect_id"],)
                ).fetchone()
                prospect_data = _dict(prospect) if prospect else {}

                rendered_subject = render_template(e.get("subject") or "", prospect_data)
                rendered_body = render_template(e.get("body_template") or "", prospect_data)

                # Insert draft row for all step types
                conn.execute("""INSERT INTO campaign_drafts
                    (campaign_id, enrollment_id, prospect_id, step_id, step_type,
                     to_email, to_name, subject, body, phone_number, script, linkedin_message, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
                    (cid, e["id"], e["prospect_id"], e["step_id"], step_type,
                     prospect_data.get("email"),
                     prospect_data.get("name") or prospect_data.get("business_name"),
                     rendered_subject, rendered_body,
                     prospect_data.get("phone"),
                     rendered_body if step_type == 'phone_script' else None,
                     rendered_body if step_type == 'linkedin' else None))

                if e["is_manual"]:
                    # Create a manual task instead of auto-sending
                    conn.execute(
                        """INSERT INTO campaign_activity
                           (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
                           VALUES (?, ?, ?, ?, 'manual_task_created', ?)""",
                        (
                            cid, e["id"], e["prospect_id"], e["step_id"],
                            json.dumps({
                                "step_type": step_type,
                                "subject": rendered_subject,
                                "body": rendered_body,
                                "status": "pending",
                            }),
                        ),
                    )
                    results["manual_tasks"] += 1
                    results["details"].append({
                        "enrollment_id": e["id"], "action": "manual_task_created",
                        "step_type": step_type,
                    })
                else:
                    # Auto-execute: log the send
                    conn.execute(
                        """INSERT INTO campaign_activity
                           (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
                           VALUES (?, ?, ?, ?, 'auto_sent', ?)""",
                        (
                            cid, e["id"], e["prospect_id"], e["step_id"],
                            json.dumps({
                                "step_type": step_type,
                                "subject": rendered_subject,
                                "body": rendered_body,
                                "recipient_email": prospect_data.get("email"),
                                "recipient_phone": prospect_data.get("phone"),
                            }),
                        ),
                    )
                    # Update campaign sent count
                    conn.execute(
                        "UPDATE campaigns SET sent_count = sent_count + 1, updated_at = datetime('now') WHERE id = ?",
                        (cid,),
                    )
                    results["executed"] += 1
                    results["details"].append({
                        "enrollment_id": e["id"], "action": "auto_sent",
                        "step_type": step_type, "prospect_id": e["prospect_id"],
                    })

                # Advance enrollment to next step
                next_step = conn.execute(
                    """SELECT * FROM campaign_steps
                       WHERE campaign_id = ? AND step_number > ?
                       ORDER BY step_number LIMIT 1""",
                    (cid, e["step_number"]),
                ).fetchone()

                if next_step:
                    ns = _dict(next_step)
                    next_at = (now + timedelta(days=ns["delay_days"])).isoformat()
                    conn.execute(
                        """UPDATE campaign_enrollments
                           SET current_step = ?, last_action_type = ?, last_action_at = ?,
                               next_step_at = ?
                           WHERE id = ?""",
                        (e["step_number"], step_type, now_iso, next_at, e["id"]),
                    )
                else:
                    # No more steps — mark completed
                    conn.execute(
                        """UPDATE campaign_enrollments
                           SET current_step = ?, status = 'completed',
                               last_action_type = ?, last_action_at = ?,
                               next_step_at = NULL
                           WHERE id = ?""",
                        (e["step_number"], step_type, now_iso, e["id"]),
                    )

            except Exception as exc:
                results["errors"] += 1
                results["details"].append({
                    "enrollment_id": e["id"], "error": str(exc),
                })

    return results


# ── Outcomes ────────────────────────────────────────────────────────────

# Pipeline backflow mapping: outcome -> lead status
_OUTCOME_TO_STATUS = {
    "responded": "contacted",
    "meeting_booked": "qualified",
    "converted": "won",
    "not_interested": "lost",
    "wrong_contact": "nurture",
}


def set_enrollment_outcome(enrollment_id: int, outcome: str) -> Optional[dict]:
    """Set outcome on an enrollment, with pipeline backflow."""
    with _db() as conn:
        enrollment = conn.execute(
            "SELECT * FROM campaign_enrollments WHERE id = ?", (enrollment_id,)
        ).fetchone()
        if not enrollment:
            return None
        e = _dict(enrollment)

        new_status = "responded" if outcome in ("responded", "meeting_booked", "converted") else e["status"]
        if outcome in ("not_interested", "wrong_contact"):
            new_status = "opted_out"

        conn.execute(
            """UPDATE campaign_enrollments
               SET outcome = ?, status = ?, last_action_type = 'outcome_set',
                   last_action_at = datetime('now'), next_step_at = NULL
               WHERE id = ?""",
            (outcome, new_status, enrollment_id),
        )

        # Update campaign responded count
        if outcome in ("responded", "meeting_booked", "converted"):
            conn.execute(
                "UPDATE campaigns SET responded_count = responded_count + 1, updated_at = datetime('now') WHERE id = ?",
                (e["campaign_id"],),
            )
            # Update reply rate
            camp = conn.execute("SELECT * FROM campaigns WHERE id = ?", (e["campaign_id"],)).fetchone()
            if camp and camp["sent_count"] > 0:
                rate = round((camp["responded_count"] / camp["sent_count"]) * 100, 1)
                conn.execute(
                    "UPDATE campaigns SET reply_rate = ? WHERE id = ?",
                    (rate, e["campaign_id"]),
                )

        # Pipeline backflow — update prospect_pipeline if exists
        lead_status = _OUTCOME_TO_STATUS.get(outcome)
        if lead_status:
            conn.execute(
                """UPDATE prospect_pipeline SET status = ?, updated_at = datetime('now')
                   WHERE prospect_id = ?""",
                (lead_status, e["prospect_id"]),
            )

        # Log activity
        conn.execute(
            """INSERT INTO campaign_activity
               (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
               VALUES (?, ?, ?, NULL, 'outcome_set', ?)""",
            (
                e["campaign_id"], enrollment_id, e["prospect_id"],
                json.dumps({"outcome": outcome, "new_status": new_status}),
            ),
        )

        row = conn.execute(
            "SELECT * FROM campaign_enrollments WHERE id = ?", (enrollment_id,)
        ).fetchone()
    return _dict(row)


# ── Follow-ups ──────────────────────────────────────────────────────────

def get_followups() -> dict:
    """Return follow-up tasks grouped by urgency."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0).isoformat()
    today_end = now.replace(hour=23, minute=59, second=59).isoformat()
    seven_days = (now + timedelta(days=7)).isoformat()
    now_iso = now.isoformat()

    with _db() as conn:
        due_today = conn.execute(
            """SELECT ce.*, p.name, p.business_name, p.email, cs.step_type, cs.subject
               FROM campaign_enrollments ce
               LEFT JOIN prospects p ON p.id = ce.prospect_id
               LEFT JOIN campaign_steps cs ON cs.campaign_id = ce.campaign_id
                   AND cs.step_number = ce.current_step + 1
               WHERE ce.status = 'active'
                 AND ce.next_step_at >= ? AND ce.next_step_at <= ?""",
            (today_start, today_end),
        ).fetchall()

        overdue = conn.execute(
            """SELECT ce.*, p.name, p.business_name, p.email, cs.step_type, cs.subject
               FROM campaign_enrollments ce
               LEFT JOIN prospects p ON p.id = ce.prospect_id
               LEFT JOIN campaign_steps cs ON cs.campaign_id = ce.campaign_id
                   AND cs.step_number = ce.current_step + 1
               WHERE ce.status = 'active'
                 AND ce.next_step_at < ?""",
            (today_start,),
        ).fetchall()

        upcoming = conn.execute(
            """SELECT ce.*, p.name, p.business_name, p.email, cs.step_type, cs.subject
               FROM campaign_enrollments ce
               LEFT JOIN prospects p ON p.id = ce.prospect_id
               LEFT JOIN campaign_steps cs ON cs.campaign_id = ce.campaign_id
                   AND cs.step_number = ce.current_step + 1
               WHERE ce.status = 'active'
                 AND ce.next_step_at > ? AND ce.next_step_at <= ?""",
            (today_end, seven_days),
        ).fetchall()

    return {
        "due_today": _dicts(due_today),
        "overdue": _dicts(overdue),
        "upcoming_7_days": _dicts(upcoming),
        "counts": {
            "due_today": len(due_today),
            "overdue": len(overdue),
            "upcoming_7_days": len(upcoming),
        },
    }


# ── Activity Feed ───────────────────────────────────────────────────────

def get_activity(campaign_id: int, limit: int = 50) -> List[dict]:
    """Get activity feed for a campaign."""
    with _db() as conn:
        rows = conn.execute(
            """SELECT ca.*, p.name, p.business_name
               FROM campaign_activity ca
               LEFT JOIN prospects p ON p.id = ca.prospect_id
               WHERE ca.campaign_id = ?
               ORDER BY ca.created_at DESC LIMIT ?""",
            (campaign_id, limit),
        ).fetchall()
    return _dicts(rows)


# ── Preview ─────────────────────────────────────────────────────────────

def preview_step(campaign_id: int, step_id: int, prospect_id: int) -> Optional[dict]:
    """Preview a rendered step with real prospect data."""
    with _db() as conn:
        step = conn.execute(
            "SELECT * FROM campaign_steps WHERE id = ? AND campaign_id = ?",
            (step_id, campaign_id),
        ).fetchone()
        if not step:
            return None
        s = _dict(step)

        prospect = conn.execute(
            "SELECT * FROM prospects WHERE id = ?", (prospect_id,)
        ).fetchone()
        prospect_data = _dict(prospect) if prospect else {}

        return {
            "step": s,
            "prospect": prospect_data,
            "rendered_subject": render_template(s.get("subject") or "", prospect_data),
            "rendered_body": render_template(s.get("body_template") or "", prospect_data),
        }


# ── Seed Default Templates ─────────────────────────────────────────────

def _seed_default_templates():
    """Seed 3 default campaign templates on first import."""
    with _db() as conn:
        existing = conn.execute("SELECT COUNT(*) as cnt FROM campaigns").fetchone()["cnt"]
        if existing > 0:
            return  # Already have campaigns, skip seeding

    # Template 1: DMV Interior Designers
    t1 = create_campaign({
        "name": "DMV Interior Designers — Cold Outreach",
        "description": "Multi-step cold outreach campaign targeting interior designers in the DC/Maryland/Virginia area for custom drapery and upholstery partnerships.",
        "business_unit": "workroom",
        "target_type": "interior_designer",
        "status": "draft",
    })
    t1_steps = [
        {
            "step_number": 1, "step_type": "email", "delay_days": 0,
            "subject": "Custom drapery & upholstery for {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "I came across {business} in {location} and love the work you're doing. "
                "I'm reaching out from Empire Workroom — we're a local drapery and upholstery "
                "workroom serving the DMV area.\n\n"
                "We partner with interior designers to provide:\n"
                "- Custom window treatments (drapes, Roman shades, valances)\n"
                "- Upholstery & reupholstery\n"
                "- Soft furnishings and pillows\n\n"
                "We handle the fabrication so you can focus on design. Would you be open to a "
                "quick call this week to see if there's a fit?\n\n"
                "Best,\nEmpire Workroom Team"
            ),
        },
        {
            "step_number": 2, "step_type": "follow_up_email", "delay_days": 3,
            "subject": "Re: Custom drapery & upholstery for {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "Just bumping this to the top of your inbox. I know things get busy — "
                "wanted to make sure you saw my note about partnering on custom window "
                "treatments and upholstery.\n\n"
                "We recently completed a 12-window drapery project for a designer in {location} "
                "and would love to share photos. Would a 10-minute call work this week?\n\n"
                "Best,\nEmpire Workroom Team"
            ),
        },
        {
            "step_number": 3, "step_type": "phone_script", "delay_days": 7, "is_manual": True,
            "subject": "Phone follow-up with {first_name}",
            "body_template": (
                "PHONE SCRIPT:\n"
                "\"Hi {first_name}, this is [name] from Empire Workroom. I sent you a couple "
                "emails about custom drapery and upholstery services for {business}. "
                "We work with several interior designers in {location} and I'd love to learn "
                "about your upcoming projects. Do you have two minutes?\"\n\n"
                "KEY POINTS:\n"
                "- We're a local workroom, not a national chain\n"
                "- Fast turnaround (2-3 weeks typical)\n"
                "- Trade pricing for design partners\n"
                "- We do the measuring and installation too"
            ),
        },
        {
            "step_number": 4, "step_type": "follow_up_email", "delay_days": 14,
            "subject": "One more thought for {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "I wanted to share one more thought — we recently launched a trade program "
                "specifically for interior designers. It includes:\n\n"
                "- Priority scheduling\n"
                "- Trade pricing (20-30% below retail)\n"
                "- Free site visits and measuring\n"
                "- Dedicated project coordinator\n\n"
                "If you ever need a reliable workroom partner for {business}, we'd love to "
                "earn your trust. No pressure — just wanted you to know we're here.\n\n"
                "Best,\nEmpire Workroom Team"
            ),
        },
        {
            "step_number": 5, "step_type": "linkedin", "delay_days": 21, "is_manual": True,
            "subject": "LinkedIn connection with {first_name}",
            "body_template": (
                "LINKEDIN MESSAGE:\n"
                "\"Hi {first_name} — I'm with Empire Workroom, a custom drapery and upholstery "
                "workroom in the DMV area. I see {business} does beautiful work in {location}. "
                "Would love to connect and explore how we might collaborate on upcoming projects. "
                "We offer trade pricing for design partners.\""
            ),
        },
    ]
    for s in t1_steps:
        add_step(t1["id"], s)

    # Template 2: General Contractors — Millwork Partner
    t2 = create_campaign({
        "name": "General Contractors — Millwork Partner",
        "description": "Outreach to general contractors for custom millwork, cabinetry, and CNC work through WoodCraft.",
        "business_unit": "woodcraft",
        "target_type": "general_contractor",
        "status": "draft",
    })
    t2_steps = [
        {
            "step_number": 1, "step_type": "email", "delay_days": 0,
            "subject": "Custom millwork partner for {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "I'm reaching out from WoodCraft — we specialize in custom millwork, "
                "cabinetry, and CNC fabrication for residential and commercial projects "
                "in {location}.\n\n"
                "We work with general contractors who need a reliable millwork partner for:\n"
                "- Custom cabinetry and built-ins\n"
                "- Architectural millwork (crown molding, wainscoting, trim)\n"
                "- CNC-cut panels and custom components\n"
                "- Commercial fit-out millwork\n\n"
                "Would {business} be interested in getting a quote on an upcoming project?\n\n"
                "Best,\nWoodCraft Team"
            ),
        },
        {
            "step_number": 2, "step_type": "follow_up_email", "delay_days": 4,
            "subject": "Re: Custom millwork for {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "Following up on my note about custom millwork services. We recently "
                "completed a full kitchen cabinetry package for a contractor in {location} — "
                "delivered on time and under budget.\n\n"
                "If you have any projects coming up that need millwork, I'd love to "
                "put together a quick estimate. No obligation.\n\n"
                "Best,\nWoodCraft Team"
            ),
        },
        {
            "step_number": 3, "step_type": "phone_script", "delay_days": 10, "is_manual": True,
            "subject": "Call {first_name} at {business}",
            "body_template": (
                "PHONE SCRIPT:\n"
                "\"Hi {first_name}, this is [name] from WoodCraft. I sent you a couple "
                "emails about custom millwork and cabinetry for your projects at {business}. "
                "We do everything from kitchen cabinets to architectural trim, all CNC-precision. "
                "Do you have any projects coming up where you need a millwork partner?\"\n\n"
                "KEY POINTS:\n"
                "- CNC precision manufacturing\n"
                "- 3-4 week turnaround on most jobs\n"
                "- Competitive contractor pricing\n"
                "- We handle delivery and can assist with install"
            ),
        },
        {
            "step_number": 4, "step_type": "follow_up_email", "delay_days": 18,
            "subject": "Still here when you need millwork — {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "Just a final note — I know timing is everything in construction. "
                "Whenever {business} has a project that needs custom cabinetry, millwork, "
                "or CNC components, WoodCraft is ready to quote.\n\n"
                "We keep our minimums low and our quality high. Feel free to reach out "
                "anytime — we're a quick email or call away.\n\n"
                "Best,\nWoodCraft Team"
            ),
        },
    ]
    for s in t2_steps:
        add_step(t2["id"], s)

    # Template 3: Restaurants & Hotels — Commercial Fit-Out
    t3 = create_campaign({
        "name": "Restaurants & Hotels — Commercial Fit-Out",
        "description": "Combined Empire Workroom + WoodCraft outreach for commercial hospitality fit-outs including upholstery, drapery, and custom millwork.",
        "business_unit": "workroom",
        "target_type": "hospitality",
        "status": "draft",
    })
    t3_steps = [
        {
            "step_number": 1, "step_type": "email", "delay_days": 0,
            "subject": "Custom furnishings & millwork for {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "I'm reaching out because {business} in {location} caught my eye — "
                "beautiful space. I'm with Empire Workroom and WoodCraft, and we provide "
                "full-service custom furnishing and millwork for restaurants, hotels, and "
                "hospitality venues.\n\n"
                "Our commercial services include:\n"
                "- Banquette and booth upholstery\n"
                "- Custom drapery and window treatments\n"
                "- Millwork: bars, host stands, shelving, wall paneling\n"
                "- Outdoor cushions and awning fabrication\n\n"
                "Whether you're renovating, refreshing, or opening a new location, we'd "
                "love to be your go-to fabrication partner. Can I send over our commercial "
                "portfolio?\n\n"
                "Best,\nEmpire Workroom & WoodCraft"
            ),
        },
        {
            "step_number": 2, "step_type": "follow_up_email", "delay_days": 5,
            "subject": "Re: Custom furnishings for {business}",
            "body_template": (
                "Hi {first_name},\n\n"
                "Just following up — I wanted to mention that we recently completed a full "
                "reupholstery of 40 dining chairs and 6 banquettes for a restaurant in "
                "{location}. The turnaround was 3 weeks.\n\n"
                "If {business} has any upcoming refresh or renovation plans, I'd love to "
                "put together a no-obligation quote.\n\n"
                "Best,\nEmpire Workroom & WoodCraft"
            ),
        },
        {
            "step_number": 3, "step_type": "phone_script", "delay_days": 12, "is_manual": True,
            "subject": "Call {first_name} — {business} fit-out",
            "body_template": (
                "PHONE SCRIPT:\n"
                "\"Hi {first_name}, this is [name] from Empire Workroom and WoodCraft. "
                "I reached out via email about custom upholstery and millwork for {business}. "
                "We handle everything from booth seating to custom bar tops for restaurants "
                "and hotels in {location}. Do you have a few minutes to discuss any upcoming "
                "projects?\"\n\n"
                "KEY POINTS:\n"
                "- Full commercial upholstery (booths, chairs, barstools)\n"
                "- Custom millwork (bars, host stands, shelving)\n"
                "- Drapery and window treatments\n"
                "- Fast turnaround for commercial deadlines"
            ),
        },
        {
            "step_number": 4, "step_type": "sms", "delay_days": 20,
            "subject": "Text follow-up — {business}",
            "body_template": (
                "Hi {first_name}, this is Empire Workroom. We specialize in commercial "
                "upholstery & millwork for restaurants/hotels in {location}. If {business} "
                "ever needs booth reupholstery, custom drapery, or millwork — we'd love to help. "
                "Reply STOP to opt out."
            ),
        },
    ]
    for s in t3_steps:
        add_step(t3["id"], s)


try:
    _seed_default_templates()
except Exception as e:
    print(f"[LeadForge Campaign Service] Seed warning: {e}")


# ── List Seeded Templates ──────────────────────────────────────────────

def get_templates() -> List[dict]:
    """Return all campaigns in draft status as available templates."""
    return list_campaigns(status="draft")


# ── Draft Management ──────────────────────────────────────────────────

def get_drafts(campaign_id: Optional[int] = None, status: Optional[str] = None, limit: int = 50) -> List[dict]:
    """List drafts with prospect info."""
    clauses, params = [], []
    if campaign_id is not None:
        clauses.append("d.campaign_id = ?")
        params.append(campaign_id)
    if status:
        clauses.append("d.status = ?")
        params.append(status)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with _db() as conn:
        rows = conn.execute(
            f"""SELECT d.*, p.name as prospect_name, p.business_name, p.email as prospect_email,
                       p.phone as prospect_phone, p.location
                FROM campaign_drafts d
                LEFT JOIN prospects p ON p.id = d.prospect_id
                {where}
                ORDER BY d.created_at DESC LIMIT ?""",
            params + [limit],
        ).fetchall()
    return _dicts(rows)


def get_draft(draft_id: int) -> Optional[dict]:
    """Get single draft with full detail."""
    with _db() as conn:
        row = conn.execute(
            """SELECT d.*, p.name as prospect_name, p.business_name, p.email as prospect_email,
                      p.phone as prospect_phone, p.location, p.website,
                      c.name as campaign_name, c.target_type, c.business_unit
               FROM campaign_drafts d
               LEFT JOIN prospects p ON p.id = d.prospect_id
               LEFT JOIN campaigns c ON c.id = d.campaign_id
               WHERE d.id = ?""",
            (draft_id,),
        ).fetchone()
    return _dict(row) if row else None


def update_draft(draft_id: int, updates: dict) -> Optional[dict]:
    """Edit draft subject/body/attachments. Sets status='edited'."""
    allowed = {"subject", "body", "to_email", "to_name", "phone_number",
               "script", "linkedin_message", "attachments"}
    data = {k: v for k, v in updates.items() if k in allowed and v is not None}
    if not data:
        return get_draft(draft_id)
    # Serialize attachments if it's a list
    if "attachments" in data and isinstance(data["attachments"], list):
        data["attachments"] = json.dumps(data["attachments"])
    sets = ", ".join(f"{k} = ?" for k in data)
    vals = list(data.values())
    vals.append(draft_id)
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM campaign_drafts WHERE id = ?", (draft_id,)).fetchone():
            return None
        conn.execute(
            f"UPDATE campaign_drafts SET {sets}, status = 'edited', edited_at = datetime('now') WHERE id = ?",
            vals,
        )
    return get_draft(draft_id)


async def send_draft(draft_id: int) -> dict:
    """Send one draft via email service. Updates status to 'sent' or 'failed'."""
    from app.services.max.email_service import EmailService

    draft = get_draft(draft_id)
    if not draft:
        return {"error": "Draft not found"}

    if not draft.get("to_email"):
        return {"error": "No recipient email on this draft"}

    email_svc = EmailService()
    if not email_svc.is_configured:
        return {"error": "Email service not configured (no SendGrid/SMTP credentials)"}

    try:
        success = email_svc.send(
            to=draft["to_email"],
            subject=draft.get("subject") or "(no subject)",
            body_html=draft.get("body") or "",
        )
    except Exception as exc:
        success = False
        send_result = str(exc)
    else:
        send_result = "sent" if success else "send_failed"

    new_status = "sent" if success else "failed"
    with _db() as conn:
        conn.execute(
            """UPDATE campaign_drafts
               SET status = ?, sent_at = datetime('now'), send_result = ?
               WHERE id = ?""",
            (new_status, send_result, draft_id),
        )
        if success:
            # Log activity
            conn.execute(
                """INSERT INTO campaign_activity
                   (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
                   VALUES (?, ?, ?, ?, 'email_sent', ?)""",
                (
                    draft.get("campaign_id"), draft.get("enrollment_id"),
                    draft.get("prospect_id"), draft.get("step_id"),
                    json.dumps({"draft_id": draft_id, "to": draft["to_email"],
                                "subject": draft.get("subject")}),
                ),
            )
            # Update campaign sent_count
            if draft.get("campaign_id"):
                conn.execute(
                    "UPDATE campaigns SET sent_count = sent_count + 1, updated_at = datetime('now') WHERE id = ?",
                    (draft["campaign_id"],),
                )

    return {"draft_id": draft_id, "status": new_status, "send_result": send_result}


async def send_all_reviewed(campaign_id: int) -> dict:
    """Batch send all drafts with status='reviewed' or 'edited' that have to_email."""
    with _db() as conn:
        rows = conn.execute(
            """SELECT id FROM campaign_drafts
               WHERE campaign_id = ? AND status IN ('reviewed', 'edited')
                 AND to_email IS NOT NULL AND to_email != ''""",
            (campaign_id,),
        ).fetchall()

    results = {"sent": 0, "failed": 0, "details": []}
    for row in rows:
        r = await send_draft(row["id"])
        if r.get("status") == "sent":
            results["sent"] += 1
        else:
            results["failed"] += 1
        results["details"].append(r)

    return results


# ── Attachments ────────────────────────────────────────────────────────

def get_attachments(target_audience: Optional[str] = None) -> List[dict]:
    """List available attachments, optionally filtered by audience."""
    with _db() as conn:
        if target_audience:
            rows = conn.execute(
                "SELECT * FROM campaign_attachments WHERE target_audience = ? ORDER BY filename",
                (target_audience,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM campaign_attachments ORDER BY filename"
            ).fetchall()
    return _dicts(rows)


def get_recommended_attachments(target_type: str) -> List[str]:
    """Return recommended attachment filenames based on campaign target type."""
    mapping = {
        "interior_designer": "Workroom Lookbook",
        "designer": "Workroom Lookbook",
        "general_contractor": "WoodCraft Capabilities",
        "contractor": "WoodCraft Capabilities",
        "hospitality": "Commercial Fit-Out",
        "restaurant": "Commercial Fit-Out",
        "hotel": "Commercial Fit-Out",
    }
    keyword = mapping.get(target_type)
    if not keyword:
        return []
    with _db() as conn:
        rows = conn.execute(
            "SELECT filename FROM campaign_attachments WHERE filename LIKE ?",
            (f"%{keyword}%",),
        ).fetchall()
    return [r["filename"] for r in rows]


# ── Enrollment Controls ──────────────────────────────────────────────

def snooze_enrollment(enrollment_id: int, days: int) -> Optional[dict]:
    """Delay next_step_at by N days."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM campaign_enrollments WHERE id = ?", (enrollment_id,)
        ).fetchone()
        if not row:
            return None
        e = _dict(row)
        current_next = e.get("next_step_at")
        if current_next:
            try:
                base = datetime.fromisoformat(current_next)
            except (ValueError, TypeError):
                base = datetime.utcnow()
        else:
            base = datetime.utcnow()
        new_next = (base + timedelta(days=days)).isoformat()
        conn.execute(
            "UPDATE campaign_enrollments SET next_step_at = ? WHERE id = ?",
            (new_next, enrollment_id),
        )
        # Log activity
        conn.execute(
            """INSERT INTO campaign_activity
               (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
               VALUES (?, ?, ?, NULL, 'snoozed', ?)""",
            (e["campaign_id"], enrollment_id, e["prospect_id"],
             json.dumps({"days": days, "new_next_step_at": new_next})),
        )
        updated = conn.execute(
            "SELECT * FROM campaign_enrollments WHERE id = ?", (enrollment_id,)
        ).fetchone()
    return _dict(updated)


def skip_enrollment_step(enrollment_id: int) -> Optional[dict]:
    """Skip current step, advance to next."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM campaign_enrollments WHERE id = ?", (enrollment_id,)
        ).fetchone()
        if not row:
            return None
        e = _dict(row)
        cid = e["campaign_id"]
        current_step = e.get("current_step", 0)

        # Find the next step after current
        next_step = conn.execute(
            """SELECT * FROM campaign_steps
               WHERE campaign_id = ? AND step_number > ?
               ORDER BY step_number LIMIT 1""",
            (cid, current_step + 1),
        ).fetchone()

        now_iso = datetime.utcnow().isoformat()
        if next_step:
            ns = _dict(next_step)
            next_at = (datetime.utcnow() + timedelta(days=ns["delay_days"])).isoformat()
            conn.execute(
                """UPDATE campaign_enrollments
                   SET current_step = ?, next_step_at = ?, last_action_type = 'step_skipped',
                       last_action_at = ?
                   WHERE id = ?""",
                (current_step + 1, next_at, now_iso, enrollment_id),
            )
        else:
            conn.execute(
                """UPDATE campaign_enrollments
                   SET current_step = ?, status = 'completed', next_step_at = NULL,
                       last_action_type = 'step_skipped', last_action_at = ?
                   WHERE id = ?""",
                (current_step + 1, now_iso, enrollment_id),
            )

        # Log activity
        conn.execute(
            """INSERT INTO campaign_activity
               (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
               VALUES (?, ?, ?, NULL, 'step_skipped', ?)""",
            (cid, enrollment_id, e["prospect_id"],
             json.dumps({"skipped_step": current_step + 1})),
        )

        updated = conn.execute(
            "SELECT * FROM campaign_enrollments WHERE id = ?", (enrollment_id,)
        ).fetchone()
    return _dict(updated)


def add_enrollment_note(enrollment_id: int, text: str) -> Optional[dict]:
    """Add a note to an enrollment's activity log."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM campaign_enrollments WHERE id = ?", (enrollment_id,)
        ).fetchone()
        if not row:
            return None
        e = _dict(row)
        conn.execute(
            """INSERT INTO campaign_activity
               (campaign_id, enrollment_id, prospect_id, step_id, action_type, details)
               VALUES (?, ?, ?, NULL, 'note', ?)""",
            (e["campaign_id"], enrollment_id, e["prospect_id"],
             json.dumps({"text": text})),
        )
        note_row = conn.execute(
            "SELECT * FROM campaign_activity WHERE enrollment_id = ? ORDER BY id DESC LIMIT 1",
            (enrollment_id,),
        ).fetchone()
    return _dict(note_row)
