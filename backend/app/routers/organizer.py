"""
Organizer API — one calendar for every life and business area.
Draft-only outbound: nothing is sent without the owner's tap.
Editions (Max / Max-e / Maxine) are isolated. EMPIRE_EDITION is fail-closed.
"""

from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.db.database import get_db, dict_row
from app.services.organizer.constants import (
    DEFAULT_TRAVEL_GAP_MINUTES,
    FOLLOWUP_KINDS,
    ITEM_KINDS,
    ITEM_STATUSES,
    ORGANIZER_ITEM_KINDS,
    OUTBOUND_POLICY,
    RESOURCE_ROLES,
)
from app.services.organizer.google_sync import google_sync_push, google_sync_status
from app.services.organizer.ics import build_calendar
from app.services.organizer.parse import parse_quick_add, parse_quick_add_lines
from app.services.organizer.resolve import attach_matches
from app.services.organizer.edition import (
    can_read_business_directory,
    can_read_workroom_jobs,
    edition_public,
    edition_sql,
    normalize_space,
    process_edition,
    reject_if_blocked,
)
from app.services.organizer.usage import UsageCapExceeded, consume, snapshot as usage_snapshot
from app.services.organizer.store import (
    assignment_ids,
    conflicts_for_payload,
    enrich_event,
    enrich_item,
    enrich_links,
    ensure_schema,
    event_select_sql,
    hydrate_event_row,
    insert_item,
    insert_schedule_event,
    is_calendar_kind,
    load_event,
    new_id,
    now_iso,
    parse_ids,
    project_job_dates,
    replace_assignments,
)

router = APIRouter(tags=["organizer"])


class ResourceIn(BaseModel):
    name: str
    role: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    availability_json: Optional[str] = None
    notes: Optional[str] = None
    source: str = "manual"
    source_id: Optional[str] = None
    active: bool = True


class ItemIn(BaseModel):
    kind: str = "todo"
    title: str
    job_id: Optional[str] = None
    customer_id: Optional[str] = None
    resource_id: Optional[str] = None
    assigned_resource_ids: Optional[List[str]] = None
    due_at: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "open"
    followup_kind: Optional[str] = None
    phone: Optional[str] = None
    location_address: Optional[str] = None
    material_eta: Optional[str] = None
    order_ref: Optional[str] = None
    reminder_draft: Optional[str] = None
    notes: Optional[str] = None
    confirm_conflicts: bool = False
    created_by: str = "manual"
    space_id: Optional[str] = None


class ItemUpdate(BaseModel):
    kind: Optional[str] = None
    title: Optional[str] = None
    job_id: Optional[str] = None
    customer_id: Optional[str] = None
    resource_id: Optional[str] = None
    assigned_resource_ids: Optional[List[str]] = None
    due_at: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None
    followup_kind: Optional[str] = None
    phone: Optional[str] = None
    location_address: Optional[str] = None
    material_eta: Optional[str] = None
    order_ref: Optional[str] = None
    reminder_draft: Optional[str] = None
    notes: Optional[str] = None
    confirm_conflicts: bool = False
    space_id: Optional[str] = None


class QuickAddIn(BaseModel):
    text: str
    confirm: bool = False
    created_by: str = "manual"
    space_id: Optional[str] = None


class ReminderDraftIn(BaseModel):
    title: str
    job_id: Optional[str] = None
    customer_id: Optional[str] = None
    due_at: Optional[str] = None
    body: str
    channel: str = "sms"


class MoveIn(BaseModel):
    start_time: str
    end_time: Optional[str] = None
    confirm_conflicts: bool = False
    notify_crew: bool = False


class ActionIn(BaseModel):
    action: str
    item_id: Optional[str] = None
    item: Optional[dict] = None
    confirm: bool = False
    confirm_conflicts: bool = False
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    body: Optional[str] = None
    approval_id: Optional[int] = None
    assigned_resource_ids: Optional[List[str]] = None
    job_id: Optional[str] = None
    ask: Optional[str] = None


class CommandIn(BaseModel):
    text: str
    confirm: bool = False


class MailActionIn(BaseModel):
    action: str
    source: str = "gmail"
    message_id: str
    body: Optional[str] = None
    snooze_until: Optional[str] = None
    confirm: bool = False


def _usage_http(exc: UsageCapExceeded):
    raise HTTPException(
        status_code=429,
        detail={
            "code": "usage_cap",
            "bucket": exc.bucket,
            "used": exc.used,
            "cap": exc.cap,
            "message": str(exc),
            "edition": process_edition(),
        },
    )


def _blocked_http(message: str):
    raise HTTPException(status_code=400, detail={"code": "edition_blocked", "message": message})


def _conflict_response(conflicts: list[dict]):
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


def _directory_people(conn) -> list[dict]:
    if not can_read_business_directory():
        return []
    people = []
    # Customers
    try:
        for r in conn.execute(
            "SELECT id, name, phone, email, address, type FROM customers"
        ).fetchall():
            row = dict(r)
            role = row.get("type") if row.get("type") in RESOURCE_ROLES else "client"
            if role == "contractor":
                role = "installer"
            people.append(
                {
                    "id": f"cust-{row['id']}",
                    "name": row.get("name"),
                    "role": role,
                    "phone": row.get("phone"),
                    "email": row.get("email"),
                    "address": row.get("address"),
                    "source": "customer",
                    "source_id": row["id"],
                    "directory": True,
                    "active": True,
                }
            )
    except Exception:
        pass
    try:
        for r in conn.execute(
            "SELECT id, name, type, phone, email, address FROM contacts"
        ).fetchall():
            row = dict(r)
            role = {
                "client": "client",
                "contractor": "installer",
                "vendor": "vendor",
                "other": "supplier",
            }.get(row.get("type") or "other", "supplier")
            people.append(
                {
                    "id": f"contact-{row['id']}",
                    "name": row.get("name"),
                    "role": role,
                    "phone": row.get("phone"),
                    "email": row.get("email"),
                    "address": row.get("address"),
                    "source": "contact",
                    "source_id": row["id"],
                    "directory": True,
                    "active": True,
                }
            )
    except Exception:
        pass
    try:
        for r in conn.execute(
            "SELECT id, name, contact_name, phone, email, address FROM vendors"
        ).fetchall():
            row = dict(r)
            people.append(
                {
                    "id": f"vendor-{row['id']}",
                    "name": row.get("name"),
                    "role": "vendor",
                    "phone": row.get("phone"),
                    "email": row.get("email"),
                    "address": row.get("address"),
                    "source": "vendor",
                    "source_id": row["id"],
                    "directory": True,
                    "active": True,
                    "notes": row.get("contact_name"),
                }
            )
    except Exception:
        pass
    return people


def _resource_row(conn, resource_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM organizer_resources WHERE id = ?", (resource_id,)
    ).fetchone()
    return dict(row) if row else None


def _list_events(conn, start_date=None, end_date=None, job_id=None, kind=None, status=None, resource_id=None, space_id=None, limit=400):
    clause, eparams = edition_sql("e")
    query = event_select_sql() + f" WHERE {clause}"
    params: list = list(eparams)
    if start_date:
        query += " AND COALESCE(e.end_time, e.start_time) >= ?"
        params.append(start_date)
    if end_date:
        end_val = f"{end_date}T23:59:59" if len(str(end_date)) == 10 else end_date
        query += " AND e.start_time <= ?"
        params.append(end_val)
    if job_id:
        query += " AND e.job_id = ?"
        params.append(job_id)
    if kind:
        query += " AND (e.event_kind = ? OR e.type = ?)"
        params.extend([kind, kind])
    if space_id:
        query += " AND COALESCE(e.space_id, '') = ?"
        params.append(normalize_space(space_id))
    if status:
        query += " AND e.status = ?"
        params.append(status)
    query += " ORDER BY e.start_time ASC LIMIT ?"
    params.append(limit)
    events = [hydrate_event_row(conn, r) for r in conn.execute(query, params).fetchall()]
    if resource_id:
        events = [e for e in events if resource_id in (e.get("assigned_resource_ids") or [])]
    return events


def _list_items(conn, start_date=None, end_date=None, job_id=None, kind=None, status=None, resource_id=None, space_id=None, limit=400):
    clause, eparams = edition_sql()
    query = f"SELECT * FROM organizer_items WHERE {clause}"
    params: list = list(eparams)
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    if status:
        query += " AND status = ?"
        params.append(status)
    if resource_id:
        query += " AND (resource_id = ? OR id IN (SELECT item_id FROM organizer_assignments WHERE resource_id = ?))"
        params.extend([resource_id, resource_id])
    if space_id:
        query += " AND COALESCE(space_id, '') = ?"
        params.append(normalize_space(space_id))
    if start_date or end_date:
        start = start_date or "0000-01-01"
        end = end_date or "9999-12-31"
        end_val = f"{end}T23:59:59" if len(str(end)) == 10 else end
        query += """ AND (
            (start_time IS NOT NULL AND start_time <= ? AND COALESCE(end_time, start_time) >= ?)
            OR (due_at IS NOT NULL AND due_at >= ? AND due_at <= ?)
        )"""
        params.extend([end_val, start, start, end_val])
    query += " ORDER BY COALESCE(start_time, due_at) ASC LIMIT ?"
    params.append(limit)
    items = [enrich_item(conn, dict(r)) for r in conn.execute(query, params).fetchall()]
    return items


def _decorate(conn, rows: list[dict]) -> list[dict]:
    from app.services.organizer.actions import attach_actions
    return attach_actions(conn, rows)


def _unify(events, items, job_dates, *, include_job_dates=True):
    board = []
    event_ids = set()
    for e in events:
        event_ids.add(str(e.get("id")))
        board.append({**e, "source": "schedule_event", "board": "calendar"})
    for it in items:
        linked = str(it.get("schedule_event_id") or "")
        if linked and linked in event_ids:
            continue
        board.append({**it, "source": "organizer_item", "board": "task" if it.get("kind") in ORGANIZER_ITEM_KINDS else "calendar"})
    if include_job_dates:
        for jd in job_dates:
            board.append({**jd, "board": "calendar"})
    def sort_key(row):
        return row.get("start_time") or row.get("due_at") or "9999"
    board.sort(key=sort_key)
    return board


def _overdue(board, today: str) -> list[dict]:
    out = []
    for row in board:
        if str(row.get("status") or "") in ("done", "cancelled"):
            continue
        due = (row.get("due_at") or row.get("start_time") or "")[:19]
        if due and due < today and (row.get("kind") in ORGANIZER_ITEM_KINDS or row.get("kind") == "deadline"):
            out.append({**row, "overdue": True})
        elif due and due < today and str(row.get("status") or "") in ("open", "planned"):
            out.append({**row, "overdue": True})
    return out


@router.get("/meta")
def organizer_meta():
    return {
        "roles": sorted(RESOURCE_ROLES),
        "kinds": sorted(ITEM_KINDS),
        "followup_kinds": sorted(FOLLOWUP_KINDS),
        "outbound_policy": OUTBOUND_POLICY,
        "google_calendar": google_sync_status(),
        "default_travel_gap_minutes": DEFAULT_TRAVEL_GAP_MINUTES,
        "spaces": edition_public()["spaces"],
        "edition": edition_public(),
        "model": "grok-4.6",
        "actions": [
            "navigate", "call", "text", "email",
            "send_quote", "order_fabric", "request_deposit", "book_install",
            "approve_send", "attach_file", "ask_max", "notify_crew",
            "open", "draft_reply", "snooze", "todo", "followup",
        ],
        "mail": {
            "read_only": True,
            "pending_path": "/api/v1/organizer/pending-mail",
        },
    }


@router.get("/board")
def organizer_board(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    job_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    space_id: Optional[str] = None,
    include_job_dates: bool = True,
    limit: int = 400,
):
    with get_db() as conn:
        ensure_schema(conn)
        events = _list_events(conn, start_date, end_date, job_id, kind, status, resource_id, space_id, limit)
        items = _list_items(conn, start_date, end_date, job_id, kind, status, resource_id, space_id, limit)
        job_dates = project_job_dates(conn) if include_job_dates and can_read_workroom_jobs() else []
        if space_id and normalize_space(space_id) != "workroom":
            job_dates = []
        if job_id:
            job_dates = [j for j in job_dates if str(j.get("job_id")) == str(job_id)]
        if kind:
            job_dates = [j for j in job_dates if j.get("kind") == kind]
        board = _decorate(conn, _unify(events, items, job_dates, include_job_dates=include_job_dates))
        today = date.today().isoformat()
        return {
            "count": len(board),
            "items": board,
            "overdue": _overdue(board, today),
            "outbound_policy": OUTBOUND_POLICY,
        }


@router.get("/today")
def organizer_today():
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with get_db() as conn:
        ensure_schema(conn)
        events = _list_events(conn, today, today)
        items = _list_items(conn, today, today)
        job_dates = [j for j in project_job_dates(conn) if (j.get("start_time") or "")[:10] == today]
        board = _decorate(conn, _unify(events, items, job_dates))
        week_end = (date.today() + timedelta(days=7)).isoformat()
        upcoming = _list_events(conn, today, week_end)
        return {
            "date": today,
            "items": board,
            "total_today": len(board),
            "overdue": _overdue(
                _unify(_list_events(conn, None, today), _list_items(conn, None, today), project_job_dates(conn)),
                today,
            ),
            "upcoming_7_days_count": len(upcoming),
            "open_organizer_href": "/?screen=calendar",
            "outbound_policy": OUTBOUND_POLICY,
        }


@router.get("/resources")
def list_resources(include_directory: bool = True, role: Optional[str] = None, active_only: bool = True):
    with get_db() as conn:
        ensure_schema(conn)
        clause, eparams = edition_sql()
        query = f"SELECT * FROM organizer_resources WHERE {clause}"
        params: list = list(eparams)
        if active_only:
            query += " AND active = 1"
        if role:
            query += " AND role = ?"
            params.append(role)
        query += " ORDER BY role, name"
        crew = [dict(r) for r in conn.execute(query, params).fetchall()]
        directory = _directory_people(conn) if include_directory and can_read_business_directory() else []
        if role:
            directory = [p for p in directory if p.get("role") == role]
        return {"resources": crew, "directory": directory, "roles": sorted(RESOURCE_ROLES)}


@router.post("/resources")
def create_resource(req: ResourceIn):
    if req.role not in RESOURCE_ROLES:
        raise HTTPException(400, f"Invalid role '{req.role}'. Valid: {', '.join(sorted(RESOURCE_ROLES))}")
    blocked = reject_if_blocked(req.name, req.notes, req.address)
    if blocked:
        _blocked_http(blocked)
    rid = new_id()
    stamp = now_iso()
    with get_db() as conn:
        ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO organizer_resources
                (id, name, role, phone, email, address, availability_json, notes, source, source_id, active, created_at, updated_at, edition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid, req.name.strip(), req.role, req.phone, req.email, req.address,
                req.availability_json, req.notes, req.source, req.source_id,
                1 if req.active else 0, stamp, stamp, process_edition(),
            ),
        )
        return _resource_row(conn, rid)


@router.put("/resources/{resource_id}")
def update_resource(resource_id: str, req: ResourceIn):
    if req.role not in RESOURCE_ROLES:
        raise HTTPException(400, f"Invalid role '{req.role}'")
    with get_db() as conn:
        ensure_schema(conn)
        existing = _resource_row(conn, resource_id)
        if not existing:
            raise HTTPException(404, "Resource not found")
        conn.execute(
            """
            UPDATE organizer_resources SET
                name=?, role=?, phone=?, email=?, address=?, availability_json=?,
                notes=?, source=?, source_id=?, active=?, updated_at=?
            WHERE id=?
            """,
            (
                req.name.strip(), req.role, req.phone, req.email, req.address,
                req.availability_json, req.notes, req.source, req.source_id,
                1 if req.active else 0, now_iso(), resource_id,
            ),
        )
        return _resource_row(conn, resource_id)


@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: str):
    with get_db() as conn:
        ensure_schema(conn)
        if not _resource_row(conn, resource_id):
            raise HTTPException(404, "Resource not found")
        conn.execute("UPDATE organizer_resources SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), resource_id))
        return {"success": True, "deleted": False, "deactivated": True, "id": resource_id}


@router.get("/resources/lanes")
def resource_lanes(date_from: Optional[str] = None, date_to: Optional[str] = None):
    day = date_from or date.today().isoformat()
    end = date_to or day
    with get_db() as conn:
        ensure_schema(conn)
        clause, eparams = edition_sql()
        resources = [dict(r) for r in conn.execute(
            f"SELECT * FROM organizer_resources WHERE active = 1 AND {clause} ORDER BY role, name",
            eparams,
        ).fetchall()]
        events = _list_events(conn, day, end)
        items = [i for i in _list_items(conn, day, end) if i.get("start_time")]
        lanes = []
        for res in resources:
            rid = res["id"]
            evs = [e for e in events if rid in (e.get("assigned_resource_ids") or [])]
            its = [i for i in items if rid in (i.get("assigned_resource_ids") or []) or i.get("resource_id") == rid]
            lanes.append({"resource": res, "items": evs + its})
        unassigned = [e for e in events if not e.get("assigned_resource_ids")]
        return {"date_from": day, "date_to": end, "lanes": lanes, "unassigned": unassigned}


@router.get("/items")
def list_items(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    job_id: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    resource_id: Optional[str] = None,
    limit: int = 200,
):
    with get_db() as conn:
        ensure_schema(conn)
        return {"items": _decorate(conn, _list_items(conn, start_date, end_date, job_id, kind, status, resource_id, None, limit))}


@router.post("/items")
def create_item(req: ItemIn):
    if req.kind not in ITEM_KINDS:
        raise HTTPException(400, f"Invalid kind '{req.kind}'")
    if req.followup_kind and req.followup_kind not in FOLLOWUP_KINDS:
        raise HTTPException(400, f"Invalid followup_kind '{req.followup_kind}'")
    payload = req.model_dump()
    blocked = reject_if_blocked(payload.get("title"), payload.get("notes"), payload.get("reminder_draft"))
    if blocked:
        _blocked_http(blocked)
    payload["space_id"] = normalize_space(payload.get("space_id"))
    with get_db() as conn:
        ensure_schema(conn)
        try:
            consume(conn, "items")
        except UsageCapExceeded as exc:
            _usage_http(exc)
        if payload.get("start_time"):
            conflicts = conflicts_for_payload(conn, payload)
            if conflicts and not req.confirm_conflicts:
                _conflict_response(conflicts)
        try:
            if is_calendar_kind(req.kind) and payload.get("start_time"):
                payload["type"] = req.kind
                payload["customer_vendor"] = None
                event = insert_schedule_event(conn, payload)
                item = insert_item(conn, {**payload, "schedule_event_id": event["id"], "status": "planned"})
                return {"item": item, "event": event, "conflicts": []}
            item = insert_item(conn, payload)
            return {"item": item, "event": None, "conflicts": []}
        except ValueError as exc:
            _blocked_http(str(exc))


@router.put("/items/{item_id}")
def update_item(item_id: str, req: ItemUpdate):
    with get_db() as conn:
        ensure_schema(conn)
        clause, eparams = edition_sql()
        existing = conn.execute(
            f"SELECT * FROM organizer_items WHERE id = ? AND {clause}",
            (item_id, *eparams),
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Organizer item not found")
        row = dict(existing)
        updates = req.model_dump(exclude_unset=True)
        blocked = reject_if_blocked(updates.get("title"), updates.get("notes"), updates.get("reminder_draft"))
        if blocked:
            _blocked_http(blocked)
        if "space_id" in updates:
            updates["space_id"] = normalize_space(updates.get("space_id"))
        updates.pop("confirm_conflicts", None)
        if "assigned_resource_ids" in updates:
            replace_assignments(conn, parse_ids(updates.pop("assigned_resource_ids")), item_id=item_id)
        fields = []
        params = []
        for key, val in updates.items():
            if key not in row:
                continue
            fields.append(f"{key} = ?")
            params.append(val)
        if fields:
            fields.append("updated_at = ?")
            params.append(now_iso())
            params.append(item_id)
            conn.execute(f"UPDATE organizer_items SET {', '.join(fields)} WHERE id = ?", params)
        merged = {**row, **{k: v for k, v in updates.items() if k in row}}
        if merged.get("start_time"):
            conflicts = conflicts_for_payload(
                conn,
                {
                    "id": merged.get("schedule_event_id"),
                    "start_time": merged.get("start_time"),
                    "end_time": merged.get("end_time"),
                    "title": merged.get("title"),
                    "location_address": merged.get("location_address"),
                    "assigned_resource_ids": assignment_ids(conn, item_id=item_id),
                },
                exclude_id=merged.get("schedule_event_id"),
            )
            if conflicts and not req.confirm_conflicts:
                _conflict_response(conflicts)
        fresh = conn.execute("SELECT * FROM organizer_items WHERE id = ?", (item_id,)).fetchone()
        return enrich_item(conn, dict(fresh))


@router.delete("/items/{item_id}")
def delete_item(item_id: str):
    with get_db() as conn:
        ensure_schema(conn)
        clause, eparams = edition_sql()
        existing = conn.execute(
            f"SELECT * FROM organizer_items WHERE id = ? AND {clause}",
            (item_id, *eparams),
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Organizer item not found")
        conn.execute("DELETE FROM organizer_assignments WHERE item_id = ?", (item_id,))
        conn.execute(f"DELETE FROM organizer_items WHERE id = ? AND {clause}", (item_id, *eparams))
        return {"success": True, "deleted": True, "id": item_id}


@router.get("/jobs/{job_id}/todos")
def job_todos(job_id: str):
    with get_db() as conn:
        ensure_schema(conn)
        items = _list_items(conn, job_id=job_id, limit=200)
        events = _list_events(conn, job_id=job_id, limit=200)
        dates = [j for j in project_job_dates(conn) if str(j.get("job_id")) == str(job_id)]
        return {
            "job_id": job_id,
            "todos": [i for i in items if i.get("kind") in ORGANIZER_ITEM_KINDS or i.get("kind") == "todo"],
            "items": items,
            "events": events,
            "job_dates": dates,
        }


@router.post("/quick-add")
def quick_add(req: QuickAddIn):
    drafts = parse_quick_add_lines(req.text)
    if not drafts:
        return {"is_draft_only": True, "requires_confirmation": True, "drafts": [], "created": []}
    with get_db() as conn:
        ensure_schema(conn)
        resolved = [attach_matches(conn, d) for d in drafts]
        if not req.confirm:
            return {
                "is_draft_only": True,
                "requires_confirmation": True,
                "drafts": resolved,
                "created": [],
                "outbound_policy": OUTBOUND_POLICY,
                "message": "Draft only. Confirm to save. Nothing is sent to a customer.",
            }
        created = []
        for draft in resolved:
            payload = {
                "kind": draft.get("kind"),
                "title": draft.get("title"),
                "job_id": draft.get("job_id"),
                "customer_id": draft.get("customer_id"),
                "start_time": draft.get("start_time"),
                "end_time": draft.get("end_time"),
                "due_at": draft.get("due_at"),
                "phone": draft.get("phone"),
                "location_address": draft.get("location_address"),
                "assigned_resource_ids": draft.get("assigned_resource_ids") or [],
                "followup_kind": draft.get("followup_kind"),
                "notes": draft.get("notes"),
                "created_by": req.created_by if req.created_by in ("max", "manual") else "manual",
                "status": "planned" if draft.get("start_time") else "open",
                "space_id": normalize_space(req.space_id or draft.get("space_id")),
            }
            blocked = reject_if_blocked(payload.get("title"), payload.get("notes"))
            if blocked:
                created.append({"draft": draft, "saved": False, "blocked": blocked})
                continue
            try:
                consume(conn, "items")
            except UsageCapExceeded as exc:
                _usage_http(exc)
            if draft.get("start_time"):
                conflicts = conflicts_for_payload(conn, payload)
                if conflicts:
                    created.append({"draft": draft, "conflicts": conflicts, "saved": False})
                    continue
            if is_calendar_kind(payload["kind"]) and payload.get("start_time"):
                event = insert_schedule_event(conn, payload)
                item = insert_item(conn, {**payload, "schedule_event_id": event["id"]})
                created.append({"item": item, "event": event, "saved": True, "conflicts": []})
            else:
                item = insert_item(conn, payload)
                created.append({"item": item, "event": None, "saved": True, "conflicts": []})
        return {"is_draft_only": False, "drafts": resolved, "created": created, "outbound_policy": OUTBOUND_POLICY}


@router.post("/reminder-draft")
def reminder_draft(req: ReminderDraftIn):
    """Store a customer reminder as a draft. Never sends."""
    with get_db() as conn:
        ensure_schema(conn)
        item = insert_item(
            conn,
            {
                "kind": "reminder",
                "title": req.title,
                "job_id": req.job_id,
                "customer_id": req.customer_id,
                "due_at": req.due_at,
                "reminder_draft": f"[{req.channel}] {req.body}",
                "notes": "Draft reminder — founder approval required before any send.",
                "status": "open",
            },
        )
        return {
            "item": item,
            "sent": False,
            "outbound_blocked": True,
            "outbound_policy": OUTBOUND_POLICY,
            "message": "Reminder saved as a draft. It was not sent.",
        }


@router.get("/actions")
def list_item_actions(item_id: Optional[str] = None):
    from app.services.organizer.actions import available_actions, load_board_item, _job_row
    with get_db() as conn:
        ensure_schema(conn)
        if not item_id:
            return {
                "actions": [
                    {"id": "navigate", "label": "Navigate", "group": "stop"},
                    {"id": "call", "label": "Call", "group": "stop"},
                    {"id": "text", "label": "Text", "group": "stop", "draft": True},
                    {"id": "send_quote", "label": "Send quote", "group": "job", "draft": True},
                    {"id": "order_fabric", "label": "Order fabric", "group": "job", "draft": True},
                    {"id": "request_deposit", "label": "Request deposit", "group": "job", "draft": True},
                    {"id": "book_install", "label": "Book install", "group": "job"},
                    {"id": "approve_send", "label": "Approve & Send", "group": "followup", "requires_confirm": True},
                    {"id": "attach_file", "label": "Attach to email/quote", "group": "file", "draft": True},
                    {"id": "ask_max", "label": "Ask Max", "group": "file"},
                    {"id": "notify_crew", "label": "Notify crew (draft)", "group": "move", "draft": True},
                ],
                "outbound_policy": OUTBOUND_POLICY,
            }
        item = load_board_item(conn, item_id)
        if not item:
            raise HTTPException(404, "Item not found")
        job = _job_row(conn, item.get("job_id"))
        return {"item_id": item_id, "actions": available_actions(item, job), "outbound_policy": OUTBOUND_POLICY}


@router.post("/actions")
async def perform_action(req: ActionIn):
    """See, click, go and do. Outbound stays draft until confirm=true on Approve & Send."""
    from app.services.organizer.actions import load_board_item, run_action
    with get_db() as conn:
        ensure_schema(conn)
        item = req.item or load_board_item(conn, req.item_id) or {}
        if req.job_id and not item.get("job_id"):
            item["job_id"] = req.job_id
        extra = {
            "job_id": req.job_id or item.get("job_id"),
            "start_time": req.start_time,
            "end_time": req.end_time,
            "body": req.body,
            "approval_id": req.approval_id,
            "assigned_resource_ids": req.assigned_resource_ids,
            "confirm_conflicts": req.confirm_conflicts,
            "ask": req.ask,
        }
        try:
            consume(conn, "actions")
        except UsageCapExceeded as exc:
            _usage_http(exc)
        result = await run_action(conn, action=req.action, item=item, confirm=req.confirm, extra=extra)
        if result.get("conflicts") and not req.confirm_conflicts:
            _conflict_response(result["conflicts"])
        return result


@router.post("/command")
async def organizer_command(req: CommandIn):
    """Natural language: 'move Marley's install to Friday and tell the crew'."""
    from app.services.organizer.actions import run_command
    with get_db() as conn:
        ensure_schema(conn)
        result = await run_command(conn, req.text, confirm=req.confirm)
        if result.get("conflicts") and not req.confirm:
            _conflict_response(result["conflicts"])
        return result


@router.get("/conflicts")
def list_conflicts(start_date: Optional[str] = None, end_date: Optional[str] = None):
    with get_db() as conn:
        ensure_schema(conn)
        events = _list_events(conn, start_date, end_date, limit=400)
        found = []
        for ev in events:
            others = [e for e in events if e["id"] != ev["id"]]
            from app.services.organizer.conflicts import detect_conflicts
            hits = detect_conflicts(ev, others)
            if hits:
                found.append({"event": ev, "conflicts": hits})
        return {"count": len(found), "items": found}


@router.get("/export.ics")
def export_ics(start_date: Optional[str] = None, end_date: Optional[str] = None, job_id: Optional[str] = None):
    with get_db() as conn:
        ensure_schema(conn)
        events = _list_events(conn, start_date, end_date, job_id=job_id, limit=500)
        items = [i for i in _list_items(conn, start_date, end_date, job_id=job_id, limit=500) if i.get("start_time") or i.get("due_at")]
        ics = build_calendar(events + items)
    return PlainTextResponse(ics, media_type="text/calendar")


@router.post("/subscribe-token")
def create_subscribe_token(label: str = "founder"):
    token = secrets.token_hex(16)
    with get_db() as conn:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO organizer_ics_tokens (id, token, label, created_at) VALUES (?, ?, ?, ?)",
            (new_id(), token, label, now_iso()),
        )
    return {
        "token": token,
        "subscribe_path": f"/api/v1/organizer/feed/{token}.ics",
        "note": "Add this ICS URL to a calendar app. It is read-only.",
    }


@router.get("/feed/{token}.ics")
def subscribe_feed(token: str):
    with get_db() as conn:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT token FROM organizer_ics_tokens WHERE token = ?", (token,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Unknown subscribe token")
        events = _list_events(conn, limit=500)
        items = [i for i in _list_items(conn, limit=500) if i.get("start_time") or i.get("due_at")]
        ics = build_calendar(events + items)
    return PlainTextResponse(ics, media_type="text/calendar")


@router.get("/google-sync/status")
def google_status():
    return google_sync_status()


@router.post("/google-sync/push")
def google_push():
    return google_sync_push([])


@router.get("/day-plan")
def get_day_plan(plan_date: Optional[str] = None):
    day = plan_date or date.today().isoformat()
    with get_db() as conn:
        ensure_schema(conn)
        from app.services.organizer.dayplan import propose_day
        events = _list_events(conn, day, day, limit=400)
        items = _list_items(conn, None, day, limit=400)
        board = _unify(events, items, project_job_dates(conn) if can_read_workroom_jobs() else [])
        clause, eparams = edition_sql()
        resources = [dict(r) for r in conn.execute(
            f"SELECT * FROM organizer_resources WHERE active = 1 AND {clause}",
            eparams,
        ).fetchall()]
        plan = propose_day(board, resources, day=day)
        row = conn.execute(
            "SELECT * FROM organizer_day_plans WHERE plan_date = ? AND edition = ? ORDER BY created_at DESC LIMIT 1",
            (day, process_edition()),
        ).fetchone()
        if row:
            saved = dict(row)
            plan["approved"] = bool(saved.get("approved"))
            plan["plan_id"] = saved.get("id")
        plan["edition"] = process_edition()
        return plan


@router.post("/day-plan/approve")
def approve_day_plan(plan_date: Optional[str] = None, apply_times: bool = True):
    """One-tap approve. Optionally writes suggested start times. Never sends."""
    plan = get_day_plan(plan_date)
    stamp = now_iso()
    with get_db() as conn:
        ensure_schema(conn)
        pid = new_id()
        conn.execute(
            """
            INSERT INTO organizer_day_plans (id, edition, plan_date, payload_json, approved, approved_at, created_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (pid, process_edition(), plan["date"], json.dumps({"headline": plan["headline"], "count": len(plan["proposed_order"])}), stamp, stamp),
        )
        applied = []
        if apply_times:
            for stop in plan.get("proposed_order") or []:
                if stop.get("kept_existing_time") or stop.get("read_only"):
                    continue
                if stop.get("source") == "schedule_event" and stop.get("id"):
                    clause, eparams = edition_sql()
                    conn.execute(
                        f"UPDATE schedule_events SET start_time = ?, end_time = ?, updated_at = ? WHERE id = ? AND {clause}",
                        (stop.get("suggested_start"), stop.get("suggested_end"), stamp, stop["id"], *eparams),
                    )
                    applied.append(stop["id"])
        plan["approved"] = True
        plan["plan_id"] = pid
        plan["applied_ids"] = applied
        plan["sent"] = False
        return plan


@router.get("/route")
def today_route(plan_date: Optional[str] = None):
    day = plan_date or date.today().isoformat()
    with get_db() as conn:
        ensure_schema(conn)
        from app.services.organizer.route import build_route
        events = _list_events(conn, day, day)
        items = [i for i in _list_items(conn, day, day) if i.get("location_address") or i.get("start_time")]
        return build_route(events + items)


@router.get("/jobs/{job_id}/timeline")
def job_timeline(job_id: str):
    with get_db() as conn:
        ensure_schema(conn)
        from app.services.organizer.timeline import build_job_timeline
        row = conn.execute(
            """SELECT j.*, c.name as customer_name FROM jobs j
               LEFT JOIN customers c ON j.customer_id = c.id WHERE j.id = ?""",
            (job_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Job not found")
        if not can_read_workroom_jobs():
            raise HTTPException(404, "Job not found")
        items = _list_items(conn, job_id=job_id) + _list_events(conn, job_id=job_id)
        return build_job_timeline(dict(row), items)


@router.get("/follow-ups")
def smart_followups(persist_drafts: bool = False):
    """Detect stale quotes, unpaid deposits, late fabric. Drafts only."""
    with get_db() as conn:
        ensure_schema(conn)
        from app.services.organizer.followups import detect_followups
        quotes = []
        jobs = []
        if can_read_workroom_jobs():
            try:
                quotes = [dict(r) for r in conn.execute("SELECT * FROM quotes_v2").fetchall()]
            except Exception:
                quotes = []
            try:
                jobs = [dict(r) for r in conn.execute("SELECT * FROM jobs").fetchall()]
            except Exception:
                jobs = []
        drafts = detect_followups(quotes=quotes, jobs=jobs)
        created = []
        if persist_drafts:
            from app.services.organizer.store import insert_item
            for d in drafts:
                created.append(insert_item(conn, {**d, "status": "open", "created_by": "max"}))
        decorated = _decorate(conn, drafts)
        return {
            "drafts": decorated,
            "created": created,
            "sent": False,
            "outbound_blocked": True,
            "outbound_policy": OUTBOUND_POLICY,
            "edition": process_edition(),
        }


@router.post("/captures")
async def upload_capture(
    source: str = "upload",
    caption: str = "",
    job_id: Optional[str] = None,
    filename: str = "upload.bin",
    mime: str = "application/octet-stream",
):
    """JSON body is not used for bytes — see /captures/file."""
    raise HTTPException(400, "Use POST /organizer/captures/file with multipart")


@router.post("/captures/file")
async def upload_capture_file(
    request=None,
    source: str = Query("upload"),
    caption: Optional[str] = None,
    job_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    event_id: Optional[str] = None,
):
    from fastapi import Request
    # FastAPI multipart via request.form to avoid extra python-multipart surprises in tests.
    raise HTTPException(status_code=415, detail="Use the JSON /captures/ingest endpoint in this revision")


@router.post("/captures/ingest")
def ingest_capture(req: dict):
    """Ingest a capture. `content_b64` is the file. Never creates a public link."""
    import base64
    from app.services.organizer.capture import CaptureRejected, write_bytes, guess_links
    raw_b64 = req.get("content_b64") or ""
    try:
        raw = base64.b64decode(raw_b64)
    except Exception:
        raise HTTPException(400, "content_b64 is not valid base64")
    filename = req.get("filename") or "upload.bin"
    mime = req.get("mime") or "application/octet-stream"
    try:
        stored = write_bytes(raw, filename=filename, mime=mime, edition=process_edition())
    except CaptureRejected as exc:
        raise HTTPException(400, str(exc))
    caption = (req.get("caption") or req.get("text") or "").strip()
    blocked = reject_if_blocked(caption, filename)
    if blocked:
        _blocked_http(blocked)
    with get_db() as conn:
        ensure_schema(conn)
        try:
            consume(conn, "captures")
        except UsageCapExceeded as exc:
            _usage_http(exc)
        draft = guess_links(conn, caption) if caption and can_read_workroom_jobs() else {}
        cap_id = new_id()
        conn.execute(
            """
            INSERT INTO organizer_captures (
                id, edition, source, source_ref, filename, mime, bytes, sha256, relpath,
                job_id, resource_id, event_id, item_id, caption, public_url_blocked, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 1, ?)
            """,
            (
                cap_id, process_edition(), req.get("source") or "upload", req.get("source_ref"),
                stored["filename"], stored["mime"], stored["bytes"], stored["sha256"], stored["relpath"],
                req.get("job_id") or draft.get("job_id"),
                req.get("resource_id") or draft.get("resource_id"),
                req.get("event_id"),
                caption, now_iso(),
            ),
        )
    return {
        "capture": {"id": cap_id, **stored, "job_id": req.get("job_id") or draft.get("job_id"), "caption": caption},
        "draft": draft,
        "public_url": None,
        "public_url_blocked": True,
        "edition": process_edition(),
    }


@router.get("/captures")
def list_captures(job_id: Optional[str] = None, limit: int = 80):
    with get_db() as conn:
        ensure_schema(conn)
        clause, eparams = edition_sql()
        q = f"SELECT * FROM organizer_captures WHERE {clause}"
        params: list = list(eparams)
        if job_id:
            q += " AND job_id = ?"
            params.append(job_id)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
        for r in rows:
            r["public_url"] = None
            r["download_path"] = f"/api/v1/organizer/captures/{r['id']}/file"
        return {"captures": rows}


@router.get("/captures/{capture_id}/file")
def download_capture(capture_id: str):
    from fastapi.responses import FileResponse
    from app.services.organizer.capture import CaptureRejected, read_file
    with get_db() as conn:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT * FROM organizer_captures WHERE id = ? AND edition = ?",
            (capture_id, process_edition()),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Capture not found")
        data = dict(row)
    try:
        path = read_file(data["edition"], data["relpath"])
    except (CaptureRejected, FileNotFoundError):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=data.get("filename") or "file", media_type=data.get("mime") or "application/octet-stream")


@router.post("/crew-tokens")
def issue_crew_token(resource_id: str, label: str = "crew"):
    with get_db() as conn:
        ensure_schema(conn)
        clause, eparams = edition_sql()
        res = conn.execute(
            f"SELECT id, name FROM organizer_resources WHERE id = ? AND {clause}",
            (resource_id, *eparams),
        ).fetchone()
        if not res:
            raise HTTPException(404, "Resource not found")
        token = secrets.token_hex(16)
        conn.execute(
            "INSERT INTO organizer_crew_tokens (id, edition, resource_id, token, label, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (new_id(), process_edition(), resource_id, token, label, now_iso()),
        )
    return {
        "token": token,
        "crew_path": f"/api/v1/organizer/crew/{token}/today",
        "note": "This link shows only that person's day. No public file links.",
    }


def _crew_from_token(conn, token: str):
    row = conn.execute(
        """SELECT t.*, r.name, r.role, r.phone
           FROM organizer_crew_tokens t
           JOIN organizer_resources r ON r.id = t.resource_id
           WHERE t.token = ? AND t.edition = ?""",
        (token, process_edition()),
    ).fetchone()
    return dict(row) if row else None


@router.get("/crew/{token}/today")
def crew_today(token: str, plan_date: Optional[str] = None):
    day = plan_date or date.today().isoformat()
    with get_db() as conn:
        ensure_schema(conn)
        crew = _crew_from_token(conn, token)
        if not crew:
            raise HTTPException(404, "Unknown crew link")
        rid = crew["resource_id"]
        events = _list_events(conn, day, day, resource_id=rid)
        items = _list_items(conn, day, day, resource_id=rid)
        slim = []
        for ev in _decorate(conn, events + items):
            slim.append({
                "id": ev.get("id"),
                "kind": ev.get("kind") or ev.get("type"),
                "title": ev.get("title"),
                "start_time": ev.get("start_time"),
                "end_time": ev.get("end_time"),
                "location_address": ev.get("location_address"),
                "phone": ev.get("phone"),
                "notes": ev.get("notes"),
                "map_link": ev.get("map_link"),
                "call_link": ev.get("call_link"),
                "status": ev.get("status"),
                "actions": [a for a in (ev.get("actions") or []) if a.get("group") == "stop"],
                "source": ev.get("source") if ev.get("source") else ("schedule_event" if ev.get("start_time") else "organizer_item"),
            })
        return {
            "date": day,
            "crew": {"id": rid, "name": crew.get("name"), "role": crew.get("role")},
            "items": slim,
            "only_own_day": True,
        }


@router.post("/crew/{token}/check-in")
def crew_checkin(token: str, event_id: Optional[str] = None, item_id: Optional[str] = None, note: str = ""):
    with get_db() as conn:
        ensure_schema(conn)
        crew = _crew_from_token(conn, token)
        if not crew:
            raise HTTPException(404, "Unknown crew link")
        cid = new_id()
        conn.execute(
            """INSERT INTO organizer_checkins (id, edition, resource_id, event_id, item_id, kind, note, created_at)
               VALUES (?, ?, ?, ?, ?, 'check_in', ?, ?)""",
            (cid, process_edition(), crew["resource_id"], event_id, item_id, note, now_iso()),
        )
        return {"ok": True, "checkin_id": cid, "kind": "check_in"}


@router.post("/crew/{token}/done")
def crew_done(token: str, req: dict):
    """Mark done and optionally file a photo (content_b64). Never public."""
    import base64
    from app.services.organizer.capture import CaptureRejected, write_bytes
    with get_db() as conn:
        ensure_schema(conn)
        crew = _crew_from_token(conn, token)
        if not crew:
            raise HTTPException(404, "Unknown crew link")
        event_id = req.get("event_id")
        item_id = req.get("item_id")
        capture_id = None
        if req.get("content_b64"):
            try:
                raw = base64.b64decode(req["content_b64"])
                stored = write_bytes(
                    raw,
                    filename=req.get("filename") or "done.jpg",
                    mime=req.get("mime") or "image/jpeg",
                    edition=process_edition(),
                )
            except (CaptureRejected, Exception) as exc:
                raise HTTPException(400, f"photo rejected: {exc}")
            capture_id = new_id()
            conn.execute(
                """INSERT INTO organizer_captures (
                    id, edition, source, source_ref, filename, mime, bytes, sha256, relpath,
                    job_id, resource_id, event_id, item_id, caption, public_url_blocked, created_at
                ) VALUES (?, ?, 'crew_done', ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 'done photo', 1, ?)""",
                (
                    capture_id, process_edition(), crew["resource_id"], stored["filename"], stored["mime"],
                    stored["bytes"], stored["sha256"], stored["relpath"], crew["resource_id"],
                    event_id, item_id, now_iso(),
                ),
            )
        clause, eparams = edition_sql()
        if event_id:
            conn.execute(
                f"UPDATE schedule_events SET status = 'done', updated_at = ? WHERE id = ? AND {clause}",
                (now_iso(), event_id, *eparams),
            )
        if item_id:
            conn.execute(
                f"UPDATE organizer_items SET status = 'done', updated_at = ? WHERE id = ? AND {clause}",
                (now_iso(), item_id, *eparams),
            )
        conn.execute(
            """INSERT INTO organizer_checkins (id, edition, resource_id, event_id, item_id, kind, note, capture_id, created_at)
               VALUES (?, ?, ?, ?, ?, 'done', ?, ?, ?)""",
            (new_id(), process_edition(), crew["resource_id"], event_id, item_id, req.get("note"), capture_id, now_iso()),
        )
        return {"ok": True, "status": "done", "capture_id": capture_id, "public_url": None}


@router.get("/spaces")
def list_spaces():
    with get_db() as conn:
        ensure_schema(conn)
        clause, eparams = edition_sql()
        rows = [dict(r) for r in conn.execute(
            f"SELECT * FROM organizer_spaces WHERE {clause} ORDER BY sort_order, slug",
            eparams,
        ).fetchall()]
    return {"spaces": rows or edition_public()["spaces"], "unified": True, "edition": process_edition()}


@router.get("/usage")
def organizer_usage():
    with get_db() as conn:
        ensure_schema(conn)
        return usage_snapshot(conn)


@router.get("/edition")
def organizer_edition():
    return edition_public()


@router.get("/pending-mail")
def pending_mail(limit: int = 40):
    """Unanswered / waiting mail for this edition's owner only. Read-only."""
    from app.services.organizer.mail import list_pending
    with get_db() as conn:
        ensure_schema(conn)
        return list_pending(conn, limit=limit)


@router.post("/pending-mail/actions")
def pending_mail_action(req: MailActionIn):
    """Open / draft reply / snooze / turn into to-do or follow-up. Never sends."""
    from app.services.organizer.mail import run_mail_action
    with get_db() as conn:
        ensure_schema(conn)
        try:
            consume(conn, "actions")
        except UsageCapExceeded as exc:
            _usage_http(exc)
        result = run_mail_action(
            conn,
            action=req.action,
            source=req.source,
            message_id=req.message_id,
            extra={"body": req.body, "snooze_until": req.snooze_until, "confirm": req.confirm},
        )
        if not result.get("ok"):
            raise HTTPException(404 if "not found" in (result.get("message") or "").lower() else 400, result.get("message"))
        return result
