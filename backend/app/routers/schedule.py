"""
Schedule Control & Pickup/Drop-Off Log API.
Endpoints for CRUD operations, date range filtering, and pickup/drop-off logging.
All times are stored as ISO-8601 strings (America/New_York timezone context).
"""
import uuid
import re
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.database import get_db, dict_row, dict_rows
from app.services.organizer.constants import CALENDAR_EVENT_TYPES, ITEM_KINDS
from app.services.organizer.parse import parse_quick_add, parse_quick_add_lines
from app.services.organizer.resolve import attach_matches
from app.services.organizer.store import (
    conflicts_for_payload,
    ensure_schema,
    hydrate_event_row,
    insert_schedule_event,
    load_event,
    now_iso,
    parse_ids,
    replace_assignments,
)

def get_schedule_db() -> str:
    from app.db.database import DB_PATH
    import os
    return os.environ.get("EMPIRE_TASK_DB", DB_PATH)

router = APIRouter(tags=["schedule"])

# Public calendar types (new kinds persist as event_kind; type stays CHECK-safe).
VALID_EVENT_TYPES = set(CALENDAR_EVENT_TYPES)

VALID_EVENT_STATUSES = {'planned', 'confirmed', 'done', 'cancelled'}
VALID_LOG_DIRECTIONS = {'picked_up', 'dropped_off'}

# ── Pydantic Schemas ───────────────────────────────────────────────

class ScheduleEventCreate(BaseModel):
    title: str
    type: str = "other"
    job_id: Optional[str] = None
    customer_id: Optional[str] = None
    customer_vendor: Optional[str] = None
    location_address: Optional[str] = None
    phone: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    status: str = "planned"
    notes: Optional[str] = None
    created_by: str = "manual"
    assigned_resource_ids: Optional[List[str]] = None
    travel_minutes: Optional[int] = None
    reminder_draft: Optional[str] = None
    confirm_conflicts: bool = False

class ScheduleEventUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    job_id: Optional[str] = None
    customer_id: Optional[str] = None
    customer_vendor: Optional[str] = None
    location_address: Optional[str] = None
    phone: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_resource_ids: Optional[List[str]] = None
    travel_minutes: Optional[int] = None
    reminder_draft: Optional[str] = None
    confirm_conflicts: bool = False


class ScheduleEventMove(BaseModel):
    start_time: str
    end_time: Optional[str] = None
    confirm_conflicts: bool = False
    notify_crew: bool = False

class PickupDropoffLogCreate(BaseModel):
    schedule_event_id: Optional[str] = None
    job_id: Optional[str] = None
    timestamp: Optional[str] = None
    direction: str  # picked_up or dropped_off
    items: str      # items like 'cushion covers', 'drapery', 'romans', 'fabric'
    party: str      # from/to party (e.g. Whittington Design)
    notes: Optional[str] = None
    created_by: str = "manual"

class DraftEventProposalRequest(BaseModel):
    text: str


def _enrich_event(event: dict) -> dict:
    return event


def _conflict_http(conflicts: list):
    raise HTTPException(
        status_code=409,
        detail={
            "code": "schedule_conflict",
            "message": "This change was not saved. Confirm the warning to keep it anyway.",
            "conflicts": conflicts,
            "silent_overwrite": False,
            "hint": "Resubmit with confirm_conflicts=true if you still want this slot.",
        },
    )


# ── Schedule Event Endpoints ────────────────────────────────────────

@router.get("/events")
def list_schedule_events(
    start_date: Optional[str] = Query(None, description="ISO start date or datetime YYYY-MM-DD or YYYY-MM-DDTHH:MM"),
    end_date: Optional[str] = Query(None, description="ISO end date or datetime YYYY-MM-DD or YYYY-MM-DDTHH:MM"),
    job_id: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """List schedule events by date range, job_id, type, or status."""
    query = """
        SELECT e.*, j.title as job_title, j.customer_id, c.name as customer_name,
               c.phone as customer_phone, c.address as customer_address, j.address as job_address,
               j.client_name
        FROM schedule_events e
        LEFT JOIN jobs j ON e.job_id = j.id
        LEFT JOIN customers c ON COALESCE(e.customer_id, j.customer_id) = c.id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND e.start_time >= ?"
        params.append(start_date)

    if end_date:
        # If end_date is just a date like YYYY-MM-DD, include the entire day
        end_val = f"{end_date}T23:59:59" if len(end_date) == 10 else end_date
        query += " AND e.start_time <= ?"
        params.append(end_val)

    if job_id:
        query += " AND e.job_id = ?"
        params.append(job_id)

    if type:
        query += " AND (e.type = ? OR e.event_kind = ?)"
        params.extend([type, type])

    if status:
        query += " AND e.status = ?"
        params.append(status)

    query += " ORDER BY e.start_time ASC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        ensure_schema(conn)
        rows = conn.execute(query, params).fetchall()
        events_list = [hydrate_event_row(conn, r) for r in rows]
        return {
            "count": len(events_list),
            "events": events_list,
        }


@router.get("/events/{event_id}")
def get_schedule_event(event_id: str):
    """Get single schedule event with linked job and logs."""
    with get_db() as conn:
        ensure_schema(conn)
        event = load_event(conn, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Schedule event not found")
        log_rows = conn.execute(
            "SELECT * FROM pickup_dropoff_logs WHERE schedule_event_id = ? ORDER BY timestamp DESC",
            (event_id,)
        ).fetchall()
        event["logs"] = [dict_row(r) for r in log_rows]
        event["pickup_dropoff_logs"] = event["logs"]
        return event


@router.post("/events")
def create_schedule_event(req: ScheduleEventCreate):
    """Create a new schedule event."""
    if req.type not in VALID_EVENT_TYPES and req.type not in ITEM_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid event type '{req.type}'. Valid types: {', '.join(sorted(VALID_EVENT_TYPES))}")

    if req.status not in VALID_EVENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status '{req.status}'. Valid statuses: {', '.join(sorted(VALID_EVENT_STATUSES))}")

    if req.created_by not in ('max', 'manual'):
        req.created_by = 'manual'

    payload = req.model_dump()
    payload["kind"] = req.type
    with get_db() as conn:
        ensure_schema(conn)
        conflicts = conflicts_for_payload(conn, payload)
        if conflicts and not req.confirm_conflicts:
            _conflict_http(conflicts)
        event = insert_schedule_event(conn, payload)
        event["conflicts"] = []
        return event


@router.put("/events/{event_id}")
def update_schedule_event(event_id: str, req: ScheduleEventUpdate):
    """Update a schedule event. Conflicts refuse the write unless confirm_conflicts=true."""
    with get_db() as conn:
        ensure_schema(conn)
        existing = conn.execute("SELECT * FROM schedule_events WHERE id = ?", (event_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Schedule event not found")

        cur = dict(existing)
        updates = []
        params = []

        if req.title is not None:
            updates.append("title = ?")
            params.append(req.title.strip())
            cur["title"] = req.title.strip()

        if req.type is not None:
            if req.type not in VALID_EVENT_TYPES and req.type not in ITEM_KINDS:
                raise HTTPException(status_code=400, detail=f"Invalid event type '{req.type}'")
            from app.services.organizer.store import legacy_type_for
            updates.append("type = ?")
            params.append(legacy_type_for(req.type))
            updates.append("event_kind = ?")
            params.append(req.type)
            cur["type"] = req.type
            cur["event_kind"] = req.type

        if req.job_id is not None:
            updates.append("job_id = ?")
            params.append(req.job_id if req.job_id != "" else None)

        if req.customer_id is not None:
            updates.append("customer_id = ?")
            params.append(req.customer_id or None)

        if req.customer_vendor is not None:
            updates.append("customer_vendor = ?")
            params.append(req.customer_vendor.strip() if req.customer_vendor else None)

        if req.location_address is not None:
            updates.append("location_address = ?")
            params.append(req.location_address.strip() if req.location_address else None)
            cur["location_address"] = req.location_address

        if req.phone is not None:
            updates.append("phone = ?")
            params.append(req.phone.strip() if req.phone else None)

        if req.start_time is not None:
            updates.append("start_time = ?")
            params.append(req.start_time.strip())
            cur["start_time"] = req.start_time.strip()

        if req.end_time is not None:
            updates.append("end_time = ?")
            params.append(req.end_time.strip() if req.end_time else None)
            cur["end_time"] = req.end_time

        if req.status is not None:
            if req.status not in VALID_EVENT_STATUSES:
                raise HTTPException(status_code=400, detail=f"Invalid status '{req.status}'")
            updates.append("status = ?")
            params.append(req.status)

        if req.notes is not None:
            updates.append("notes = ?")
            params.append(req.notes.strip() if req.notes else None)

        if req.travel_minutes is not None:
            updates.append("travel_minutes = ?")
            params.append(req.travel_minutes)
            cur["travel_minutes"] = req.travel_minutes

        if req.reminder_draft is not None:
            updates.append("reminder_draft = ?")
            params.append(req.reminder_draft)

        if req.assigned_resource_ids is not None:
            replace_assignments(conn, parse_ids(req.assigned_resource_ids), event_id=event_id)
            cur["assigned_resource_ids"] = parse_ids(req.assigned_resource_ids)
        else:
            cur["assigned_resource_ids"] = parse_ids(cur.get("assigned_resource_ids")) or []
            # load current assignments for conflict check
            from app.services.organizer.store import assignment_ids
            cur["assigned_resource_ids"] = assignment_ids(conn, event_id=event_id)

        conflicts = conflicts_for_payload(conn, cur, exclude_id=event_id)
        if conflicts and not req.confirm_conflicts:
            _conflict_http(conflicts)

        if updates:
            updates.append("updated_at = ?")
            params.append(now_iso())
            params.append(event_id)
            conn.execute(f"UPDATE schedule_events SET {', '.join(updates)} WHERE id = ?", params)

        event = load_event(conn, event_id)
        event["conflicts"] = []
        return event


@router.post("/events/{event_id}/move")
async def move_schedule_event(event_id: str, req: ScheduleEventMove):
    """Drag/resize an event. Refuses overlapping assignments unless confirm_conflicts=true."""
    event = update_schedule_event(
        event_id,
        ScheduleEventUpdate(
            start_time=req.start_time,
            end_time=req.end_time,
            confirm_conflicts=req.confirm_conflicts,
        ),
    )
    if req.notify_crew:
        from app.services.organizer.actions import run_action
        with get_db() as conn:
            notify = await run_action(conn, action="notify_crew", item=event)
        event["crew_draft"] = notify
        event["sent"] = False
        event["message"] = "Calendar updated. Crew message drafted — Approve & Send required."
    return event


@router.delete("/events/{event_id}")
def delete_schedule_event(event_id: str):
    """Delete a schedule event."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM schedule_events WHERE id = ?", (event_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Schedule event not found")

        try:
            conn.execute("DELETE FROM organizer_assignments WHERE event_id = ?", (event_id,))
        except Exception:
            pass
        conn.execute("DELETE FROM schedule_events WHERE id = ?", (event_id,))
        return {"success": True, "deleted": True, "deleted_id": event_id}


# ── Pickup & Drop-Off Log Endpoints ─────────────────────────────────

@router.get("/pickup-dropoff-logs")
def list_pickup_dropoff_logs(
    job_id: Optional[str] = None,
    schedule_event_id: Optional[str] = None,
    direction: Optional[str] = None,
    limit: int = 100
):
    """List pickup and drop-off logs."""
    query = """
        SELECT l.*, j.title as job_title, e.title as event_title
        FROM pickup_dropoff_logs l
        LEFT JOIN jobs j ON l.job_id = j.id
        LEFT JOIN schedule_events e ON l.schedule_event_id = e.id
        WHERE 1=1
    """
    params = []

    if job_id:
        query += " AND l.job_id = ?"
        params.append(job_id)

    if schedule_event_id:
        query += " AND l.schedule_event_id = ?"
        params.append(schedule_event_id)

    if direction:
        query += " AND l.direction = ?"
        params.append(direction)

    query += " ORDER BY l.timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        logs_list = [dict_row(r) for r in rows]
        return {
            "count": len(logs_list),
            "logs": logs_list,
        }


@router.post("/pickup-dropoff-logs")
def create_pickup_dropoff_log(req: PickupDropoffLogCreate):
    """Record a pickup or drop-off log entry."""
    if req.direction not in VALID_LOG_DIRECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid direction '{req.direction}'. Must be 'picked_up' or 'dropped_off'"
        )

    log_id = str(uuid.uuid4())[:8]
    ts = req.timestamp or datetime.now().isoformat()
    now = datetime.now().isoformat()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO pickup_dropoff_logs
               (id, schedule_event_id, job_id, timestamp, direction, items, party, notes, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_id,
                req.schedule_event_id,
                req.job_id,
                ts,
                req.direction,
                req.items.strip(),
                req.party.strip(),
                req.notes.strip() if req.notes else None,
                req.created_by if req.created_by in ('max', 'manual') else 'manual',
                now,
            )
        )

        # If schedule_event_id was provided and event is not yet 'done', check if we should auto-mark or keep
        if req.schedule_event_id:
            conn.execute(
                "UPDATE schedule_events SET status = 'done', updated_at = ? WHERE id = ? AND status != 'cancelled'",
                (now, req.schedule_event_id)
            )

        row = conn.execute(
            """SELECT l.*, j.title as job_title, e.title as event_title
               FROM pickup_dropoff_logs l
               LEFT JOIN jobs j ON l.job_id = j.id
               LEFT JOIN schedule_events e ON l.schedule_event_id = e.id
               WHERE l.id = ?""",
            (log_id,)
        ).fetchone()
        return dict_row(row)


# ── Today's Schedule & Summary ──────────────────────────────────────

@router.get("/today-summary")
def get_today_summary():
    """Summary of events and pickup/drop-offs for today in America/New_York context."""
    today_str = date.today().isoformat()
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

    with get_db() as conn:
        ensure_schema(conn)
        # Today's events
        today_events = conn.execute(
            """SELECT e.*, j.title as job_title, c.name as customer_name,
                      c.phone as customer_phone, j.address as job_address, j.client_name
               FROM schedule_events e
               LEFT JOIN jobs j ON e.job_id = j.id
               LEFT JOIN customers c ON COALESCE(e.customer_id, j.customer_id) = c.id
               WHERE e.start_time >= ? AND e.start_time < ?
               ORDER BY e.start_time ASC""",
            (today_str, tomorrow_str)
        ).fetchall()

        # Counts
        counts_by_type = {}
        for r in today_events:
            t = r["type"]
            counts_by_type[t] = counts_by_type.get(t, 0) + 1

        # Today's pickup/drop-off logs
        today_logs = conn.execute(
            """SELECT l.*, j.title as job_title
               FROM pickup_dropoff_logs l
               LEFT JOIN jobs j ON l.job_id = j.id
               WHERE l.timestamp >= ? AND l.timestamp < ?
               ORDER BY l.timestamp DESC""",
            (today_str, tomorrow_str)
        ).fetchall()

        # Upcoming upcoming 7 days count
        week_end = (date.today() + timedelta(days=7)).isoformat()
        upcoming_count = conn.execute(
            "SELECT COUNT(*) FROM schedule_events WHERE start_time >= ? AND start_time <= ? AND status != 'cancelled'",
            (today_str, week_end)
        ).fetchone()[0]

        return {
            "date": today_str,
            "total_events_today": len(today_events),
            "events": [hydrate_event_row(conn, r) for r in today_events],
            "counts_by_type": counts_by_type,
            "today_logs_count": len(today_logs),
            "today_logs": [dict_row(r) for r in today_logs],
            "upcoming_7_days_count": upcoming_count,
            "open_organizer_href": "/?screen=calendar",
        }


# ── Draft-Only Event Extraction / Proposal Helper ────────────────────

def extract_draft_events_from_text(text: str) -> list:
    text = (text or "").strip()
    if not text:
        return []

    drafts = parse_quick_add_lines(text)
    proposals = []
    for d in drafts:
        proposals.append({
            "type": d.get("kind") or "other",
            "kind": d.get("kind") or "other",
            "title": d.get("title"),
            "start_time": d.get("start_time"),
            "end_time": d.get("end_time"),
            "due_at": d.get("due_at"),
            "subject_name": d.get("subject_name"),
            "followup_kind": d.get("followup_kind"),
            "original_snippet": d.get("original_text"),
            "requires_confirmation": True,
            "is_draft_only": True,
            "notes": d.get("notes"),
            "outbound_blocked": True,
        })
    if proposals:
        return proposals

    # Fallback: keep a single draft so callers always get something to confirm.
    proposals = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Simple heuristic regexes for date, time, action
    date_pattern = re.compile(
        r'(\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,\s*\d{4})?|\btomorrow\b|\btoday\b|\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))',
        re.IGNORECASE
    )
    time_pattern = re.compile(r'(\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\bnoon\b|\bmorning\b|\bafternoon\b)', re.IGNORECASE)

    current_year = date.today().year

    # Check for keywords
    keywords_map = {
        'install': 'install',
        'installation': 'install',
        'delivery': 'delivery',
        'deliver': 'delivery',
        'pick up': 'pickup',
        'pickup': 'pickup',
        'drop off': 'drop_off',
        'dropoff': 'drop_off',
        'drop-off': 'drop_off',
        'fabric': 'fabric_pickup',
        'measure': 'measure',
        'measurement': 'measure',
        'loading dock': 'loading_dock',
        'dock': 'loading_dock',
        'errand': 'errand'
    }

    # Extract sentences/lines
    for line in lines:
        matched_type = "other"
        line_lower = line.lower()
        for kw, t in keywords_map.items():
            if kw in line_lower:
                matched_type = t
                break

        d_match = date_pattern.search(line)
        t_match = time_pattern.search(line)

        # Rough target date string
        start_date_str = date.today().isoformat()
        if d_match:
            raw_d = d_match.group(1).lower()
            if "tomorrow" in raw_d:
                start_date_str = (date.today() + timedelta(days=1)).isoformat()
            elif "today" in raw_d:
                start_date_str = date.today().isoformat()
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', raw_d):
                start_date_str = raw_d

        time_str = "09:00"
        if t_match:
            raw_t = t_match.group(1).lower()
            if "pm" in raw_t:
                digits = re.findall(r'\d+', raw_t)
                hr = int(digits[0]) if digits else 12
                if hr < 12:
                    hr += 12
                mn = digits[1] if len(digits) > 1 else "00"
                time_str = f"{hr:02d}:{mn}"
            elif "am" in raw_t:
                digits = re.findall(r'\d+', raw_t)
                hr = int(digits[0]) if digits else 9
                if hr == 12:
                    hr = 0
                mn = digits[1] if len(digits) > 1 else "00"
                time_str = f"{hr:02d}:{mn}"
            elif "afternoon" in raw_t:
                time_str = "14:00"

        # Heuristic title
        clean_title = line
        if len(clean_title) > 60:
            clean_title = clean_title[:57] + "..."

        if d_match or t_match or matched_type != "other":
            proposals.append({
                "type": matched_type,
                "title": f"{matched_type.replace('_', ' ').capitalize()}: {clean_title}" if not clean_title.lower().startswith(matched_type) else clean_title,
                "start_time": f"{start_date_str}T{time_str}",
                "original_snippet": line,
                "requires_confirmation": True,
                "notes": f"Proposed from text: {line}"
            })

    # If nothing matched specific lines, produce at least one proposal from full text if it's not empty
    if not proposals and text:
        proposals.append({
            "type": "other",
            "title": text[:60] if len(text) <= 60 else text[:57] + "...",
            "start_time": f"{date.today().isoformat()}T10:00",
            "original_snippet": text[:120],
            "requires_confirmation": True,
            "notes": "Proposed from text context"
        })

    return proposals


@router.post("/propose-events")
def propose_events_from_text(req: DraftEventProposalRequest):
    """
    DRAFT-ONLY helper that extracts proposed schedule events from an email/message text.
    Accepts raw text (e.g. from an email summary or client message).
    DOES NOT create any events in the database — returns proposals for review and confirmation.
    """
    text = req.text.strip()
    if not text:
        return {"proposals": [], "message": "No text provided"}

    proposals = extract_draft_events_from_text(text)
    with get_db() as conn:
        ensure_schema(conn)
        proposals = [attach_matches(conn, p) for p in proposals]
    return {
        "is_draft_only": True,
        "requires_confirmation": True,
        "proposals": proposals,
        "message": "These events are draft proposals only. Nothing has been scheduled or created without user confirmation. Nothing is sent to a customer."
    }
