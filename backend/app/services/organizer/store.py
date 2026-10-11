"""Shared read/write helpers for schedule events + organizer items."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote

from app.services.organizer.constants import (
    DEFAULT_TRAVEL_GAP_MINUTES,
    EVENT_STATUSES,
    ITEM_KINDS,
    ITEM_STATUSES,
    KIND_TO_LEGACY_TYPE,
    LEGACY_EVENT_TYPES,
    ORGANIZER_ITEM_KINDS,
    OUTBOUND_POLICY,
)
from app.services.organizer.conflicts import detect_conflicts
from app.services.organizer.edition import (
    can_read_workroom_jobs,
    default_space_slug,
    default_spaces,
    edition_sql,
    normalize_space,
    process_edition,
    redact_blocked,
    reject_if_blocked,
)
from app.services.organizer.schema import migrate_organizer_tables


def ensure_schema(conn) -> None:
    migrate_organizer_tables(conn)
    seed_spaces(conn)


def seed_spaces(conn) -> None:
    stamp = now_iso()
    for i, space in enumerate(default_spaces()):
        sid = f"{process_edition()}:{space['slug']}"
        conn.execute(
            """
            INSERT OR IGNORE INTO organizer_spaces (id, edition, slug, label, kind, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (sid, process_edition(), space["slug"], space["label"], space["kind"], i, stamp),
        )


def new_id() -> str:
    return str(uuid.uuid4())[:8]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def public_kind(row: dict) -> str:
    kind = (row.get("event_kind") or row.get("kind") or row.get("type") or "other").strip()
    return kind if kind in ITEM_KINDS else (row.get("type") or "other")


def legacy_type_for(kind: str) -> str:
    if kind in LEGACY_EVENT_TYPES:
        return kind
    return KIND_TO_LEGACY_TYPE.get(kind, "other")


def map_link(address: Optional[str]) -> Optional[str]:
    if not address or not str(address).strip():
        return None
    return f"https://maps.google.com/?q={quote(str(address).strip())}"


def call_link(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")
    if len(digits) < 7:
        return None
    return f"tel:{digits}"


def parse_ids(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [str(v) for v in data if v]
            except json.JSONDecodeError:
                pass
        return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def assignment_ids(conn, *, event_id: Optional[str] = None, item_id: Optional[str] = None) -> list[str]:
    if event_id:
        rows = conn.execute(
            "SELECT resource_id FROM organizer_assignments WHERE event_id = ?",
            (event_id,),
        ).fetchall()
    elif item_id:
        rows = conn.execute(
            "SELECT resource_id FROM organizer_assignments WHERE item_id = ?",
            (item_id,),
        ).fetchall()
    else:
        return []
    return [r[0] if not hasattr(r, "keys") else r["resource_id"] for r in rows]


def assignment_rows(conn, *, event_id: Optional[str] = None, item_id: Optional[str] = None) -> list[dict]:
    if event_id:
        rows = conn.execute(
            """
            SELECT a.id, a.resource_id, r.name, r.role, r.phone
            FROM organizer_assignments a
            LEFT JOIN organizer_resources r ON r.id = a.resource_id
            WHERE a.event_id = ?
            """,
            (event_id,),
        ).fetchall()
    elif item_id:
        rows = conn.execute(
            """
            SELECT a.id, a.resource_id, r.name, r.role, r.phone
            FROM organizer_assignments a
            LEFT JOIN organizer_resources r ON r.id = a.resource_id
            WHERE a.item_id = ?
            """,
            (item_id,),
        ).fetchall()
    else:
        return []
    return [dict(r) for r in rows]


def replace_assignments(conn, resource_ids: list[str], *, event_id=None, item_id=None) -> None:
    if event_id:
        conn.execute("DELETE FROM organizer_assignments WHERE event_id = ?", (event_id,))
    if item_id:
        conn.execute("DELETE FROM organizer_assignments WHERE item_id = ?", (item_id,))
    stamp = now_iso()
    for rid in resource_ids:
        if not rid:
            continue
        conn.execute(
            """
            INSERT INTO organizer_assignments (id, event_id, item_id, resource_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (new_id(), event_id, item_id, str(rid), stamp),
        )


def enrich_links(item: dict) -> dict:
    out = dict(item)
    out["kind"] = public_kind(out)
    out["type"] = out["kind"]
    out["space_id"] = out.get("space_id") or default_space_slug()
    for key in ("title", "notes", "reminder_draft", "location_address", "customer_vendor", "job_title"):
        if out.get(key):
            out[key] = redact_blocked(str(out[key]))
    out["map_link"] = map_link(out.get("location_address"))
    out["call_link"] = call_link(out.get("phone"))
    out["outbound_blocked"] = True
    out["outbound_policy"] = OUTBOUND_POLICY
    return out


def enrich_event(conn, row: dict) -> dict:
    event = enrich_links(dict(row))
    assigned = assignment_rows(conn, event_id=event.get("id"))
    event["assignments"] = assigned
    event["assigned_resource_ids"] = [a["resource_id"] for a in assigned if a.get("resource_id")]
    event["assigned_names"] = [a["name"] for a in assigned if a.get("name")]
    if not event.get("phone"):
        for a in assigned:
            if a.get("phone"):
                event["phone"] = a["phone"]
                event["call_link"] = call_link(a["phone"])
                break
    return event


def enrich_item(conn, row: dict) -> dict:
    item = enrich_links(dict(row))
    assigned = assignment_rows(conn, item_id=item.get("id"))
    if item.get("resource_id") and item["resource_id"] not in [a.get("resource_id") for a in assigned]:
        extra = conn.execute(
            "SELECT id as resource_id, name, role, phone FROM organizer_resources WHERE id = ?",
            (item["resource_id"],),
        ).fetchone()
        if extra:
            assigned = assigned + [dict(extra)]
    item["assignments"] = assigned
    item["assigned_resource_ids"] = [a.get("resource_id") for a in assigned if a.get("resource_id")]
    item["assigned_names"] = [a.get("name") for a in assigned if a.get("name")]
    if not item.get("phone"):
        for a in assigned:
            if a.get("phone"):
                item["phone"] = a["phone"]
                item["call_link"] = call_link(a["phone"])
                break
    return item


def load_event(conn, event_id: str) -> Optional[dict]:
    clause, params = edition_sql("e")
    row = conn.execute(
        event_select_sql() + f" WHERE e.id = ? AND {clause}",
        (event_id, *params),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    if not data.get("phone"):
        data["phone"] = data.get("customer_phone")
    if not data.get("location_address"):
        data["location_address"] = data.get("job_address") or data.get("customer_address")
    if not data.get("customer_vendor"):
        data["customer_vendor"] = data.get("client_name") or data.get("customer_name")
    return enrich_event(conn, data)


def list_timed_for_conflicts(conn, start: Optional[str], end: Optional[str], exclude_id: Optional[str] = None) -> list[dict]:
    clause, eparams = edition_sql("e")
    query = f"""
        SELECT e.id, e.title, e.start_time, e.end_time, e.location_address,
               e.status, e.travel_minutes, e.event_kind, e.type
        FROM schedule_events e
        WHERE e.status != 'cancelled' AND {clause}
    """
    params: list = list(eparams)
    if start:
        query += " AND COALESCE(e.end_time, e.start_time) >= ?"
        params.append(start)
    if end:
        end_val = f"{end}T23:59:59" if len(end) == 10 else end
        query += " AND e.start_time <= ?"
        params.append(end_val)
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    out = []
    for row in rows:
        if exclude_id and row["id"] == exclude_id:
            continue
        row["assigned_resource_ids"] = assignment_ids(conn, event_id=row["id"])
        names = []
        if row["assigned_resource_ids"]:
            qmarks = ",".join("?" * len(row["assigned_resource_ids"]))
            name_rows = conn.execute(
                f"SELECT name FROM organizer_resources WHERE id IN ({qmarks})",
                row["assigned_resource_ids"],
            ).fetchall()
            names = [n[0] if not hasattr(n, "keys") else n["name"] for n in name_rows]
        row["assigned_names"] = names
        out.append(row)
    return out


def conflicts_for_payload(conn, payload: dict, *, exclude_id: Optional[str] = None) -> list[dict]:
    existing = list_timed_for_conflicts(
        conn,
        payload.get("start_time"),
        payload.get("end_time") or payload.get("start_time"),
        exclude_id=exclude_id,
    )
    travel = int(payload.get("travel_minutes") or DEFAULT_TRAVEL_GAP_MINUTES)
    return detect_conflicts({**payload, "travel_minutes": travel}, existing)


def event_select_sql() -> str:
    if not can_read_workroom_jobs():
        return """
            SELECT e.*, NULL as job_title, NULL as client_name, NULL as job_address,
                   NULL as job_customer_id, NULL as customer_name,
                   NULL as customer_phone, NULL as customer_address
            FROM schedule_events e
        """
    return """
        SELECT e.*, j.title as job_title, j.client_name, j.address as job_address,
               j.customer_id as job_customer_id, c.name as customer_name,
               c.phone as customer_phone, c.address as customer_address
        FROM schedule_events e
        LEFT JOIN jobs j ON e.job_id = j.id
        LEFT JOIN customers c ON COALESCE(e.customer_id, j.customer_id) = c.id
    """


def hydrate_event_row(conn, row) -> dict:
    data = dict(row)
    if not data.get("phone"):
        data["phone"] = data.get("customer_phone")
    if not data.get("location_address"):
        data["location_address"] = data.get("job_address") or data.get("customer_address")
    if not data.get("customer_vendor"):
        data["customer_vendor"] = data.get("client_name") or data.get("customer_name")
    return enrich_event(conn, data)


def insert_schedule_event(conn, payload: dict) -> dict:
    ensure_schema(conn)
    blocked = reject_if_blocked(payload.get("title"), payload.get("notes"), payload.get("location_address"))
    if blocked:
        raise ValueError(blocked)
    kind = payload.get("kind") or payload.get("type") or "other"
    if kind not in ITEM_KINDS:
        kind = "other"
    event_id = payload.get("id") or new_id()
    stamp = now_iso()
    conn.execute(
        """
        INSERT INTO schedule_events
            (id, type, title, job_id, customer_vendor, location_address, start_time, end_time,
             status, notes, created_by, created_at, updated_at, phone, customer_id, event_kind,
             travel_minutes, reminder_draft, all_day, edition, space_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            legacy_type_for(kind),
            (payload.get("title") or "").strip(),
            payload.get("job_id") or None,
            (payload.get("customer_vendor") or "").strip() or None,
            (payload.get("location_address") or "").strip() or None,
            (payload.get("start_time") or "").strip(),
            (payload.get("end_time") or None),
            payload.get("status") if payload.get("status") in EVENT_STATUSES else "planned",
            (payload.get("notes") or None),
            payload.get("created_by") if payload.get("created_by") in ("max", "manual") else "manual",
            stamp,
            stamp,
            (payload.get("phone") or None),
            payload.get("customer_id") or None,
            kind,
            payload.get("travel_minutes"),
            payload.get("reminder_draft"),
            1 if payload.get("all_day") else 0,
            process_edition(),
            normalize_space(payload.get("space_id") or payload.get("space")),
        ),
    )
    replace_assignments(conn, parse_ids(payload.get("assigned_resource_ids")), event_id=event_id)
    return load_event(conn, event_id)


def is_calendar_kind(kind: str) -> bool:
    return kind not in ORGANIZER_ITEM_KINDS or kind == "call"


def insert_item(conn, payload: dict) -> dict:
    ensure_schema(conn)
    blocked = reject_if_blocked(payload.get("title"), payload.get("notes"), payload.get("reminder_draft"))
    if blocked:
        raise ValueError(blocked)
    kind = payload.get("kind") or payload.get("type") or "todo"
    if kind not in ITEM_KINDS:
        kind = "todo"
    item_id = new_id()
    stamp = now_iso()
    resource_ids = parse_ids(payload.get("assigned_resource_ids"))
    primary = payload.get("resource_id") or (resource_ids[0] if resource_ids else None)
    conn.execute(
        """
        INSERT INTO organizer_items (
            id, kind, title, job_id, customer_id, resource_id, due_at, start_time, end_time,
            status, followup_kind, phone, location_address, material_eta, order_ref,
            reminder_draft, outbound_blocked, notes, schedule_event_id, created_by,
            created_at, updated_at, edition, space_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            kind,
            (payload.get("title") or "").strip(),
            payload.get("job_id") or None,
            payload.get("customer_id") or None,
            primary,
            payload.get("due_at"),
            payload.get("start_time"),
            payload.get("end_time"),
            payload.get("status") if payload.get("status") in ITEM_STATUSES else "open",
            payload.get("followup_kind"),
            payload.get("phone"),
            payload.get("location_address"),
            payload.get("material_eta"),
            payload.get("order_ref"),
            payload.get("reminder_draft"),
            payload.get("notes"),
            payload.get("schedule_event_id"),
            payload.get("created_by") if payload.get("created_by") in ("max", "manual") else "manual",
            stamp,
            stamp,
            process_edition(),
            normalize_space(payload.get("space_id") or payload.get("space")),
        ),
    )
    replace_assignments(conn, resource_ids or ([primary] if primary else []), item_id=item_id)
    clause, params = edition_sql()
    row = conn.execute(
        f"SELECT * FROM organizer_items WHERE id = ? AND {clause}",
        (item_id, *params),
    ).fetchone()
    return enrich_item(conn, dict(row)) if row else None


def load_item(conn, item_id: str) -> Optional[dict]:
    clause, params = edition_sql()
    row = conn.execute(
        f"SELECT * FROM organizer_items WHERE id = ? AND {clause}",
        (item_id, *params),
    ).fetchone()
    if not row:
        return None
    return enrich_item(conn, dict(row))


def project_job_dates(conn) -> list[dict]:
    """Read-only projections of job milestone dates. Main edition only."""
    if not can_read_workroom_jobs():
        return []
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    fields = [
        ("install_date", "install", "Install"),
        ("site_visit_date", "measure", "Site visit"),
        ("scheduled_date", "appointment", "Scheduled"),
        ("due_date", "deadline", "Job due"),
        ("pickup_delivery_date", "delivery", "Pickup/delivery"),
    ]
    available = [(col, kind, label) for col, kind, label in fields if col in cols]
    if not available:
        return []
    select_cols = ", ".join(
        ["j.id", "j.title", "j.job_number", "j.client_name", "j.address", "j.customer_id", "j.status"]
        + [f"j.{col}" for col, _, _ in available]
        + ["c.name as customer_name", "c.phone as customer_phone"]
    )
    rows = conn.execute(
        f"""
        SELECT {select_cols}
        FROM jobs j
        LEFT JOIN customers c ON j.customer_id = c.id
        """
    ).fetchall()
    items = []
    for row in rows:
        data = dict(row)
        for col, kind, label in available:
            raw = data.get(col)
            if not raw:
                continue
            start = str(raw)
            items.append(
                enrich_links(
                    {
                        "id": f"jobdate-{data['id']}-{col}",
                        "source": "job_date",
                        "read_only": True,
                        "kind": kind,
                        "type": kind,
                        "title": f"{label} · {data.get('client_name') or data.get('customer_name') or data.get('title') or 'job'}",
                        "job_id": data.get("id"),
                        "job_title": data.get("title"),
                        "customer_id": data.get("customer_id"),
                        "customer_vendor": data.get("client_name") or data.get("customer_name"),
                        "location_address": data.get("address"),
                        "phone": data.get("customer_phone"),
                        "start_time": start if "T" in start else f"{start[:10]}T09:00:00",
                        "end_time": None,
                        "due_at": start if kind == "deadline" else None,
                        "status": "planned" if str(data.get("status") or "") not in ("completed", "cancelled") else "done",
                        "assigned_resource_ids": [],
                        "assignments": [],
                        "space_id": "workroom",
                    }
                )
            )
    return items


def job_has_column(conn, name: str) -> bool:
    return name in {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
