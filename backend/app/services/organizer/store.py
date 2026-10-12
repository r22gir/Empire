"""Shared read/write helpers for schedule events + organizer items."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote

from app.services.organizer.constants import (
    BOARD_COLUMNS,
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
    try:
        conn.commit()
    except Exception:
        pass


def seed_spaces(conn) -> None:
    ed = process_edition()
    existing = {
        (r[0] if not hasattr(r, "keys") else r["slug"])
        for r in conn.execute(
            "SELECT slug FROM organizer_spaces WHERE edition = ?", (ed,)
        ).fetchall()
    }
    stamp = now_iso()
    for i, space in enumerate(default_spaces()):
        if space["slug"] in existing:
            conn.execute(
                """
                UPDATE organizer_spaces
                   SET icon = COALESCE(NULLIF(icon, ''), ?),
                       accent_color = COALESCE(NULLIF(accent_color, ''), ?)
                 WHERE edition = ? AND slug = ?
                """,
                (space.get("icon"), space.get("accent_color"), ed, space["slug"]),
            )
            continue
        sid = f"{ed}:{space['slug']}"
        conn.execute(
            """
            INSERT OR IGNORE INTO organizer_spaces
                (id, edition, slug, label, kind, sort_order, icon, accent_color, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid, ed, space["slug"], space["label"], space["kind"], i,
                space.get("icon"), space.get("accent_color"), stamp,
            ),
        )


def new_id() -> str:
    """Unique id for every insert. Never reuse a timestamp or last-row lookup."""
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def column_for_status(status: Optional[str]) -> str:
    key = (status or "open").strip()
    for col in BOARD_COLUMNS:
        if key in col["statuses"]:
            return col["id"]
    if key == "cancelled":
        return "done"
    return "open"


def status_for_column(column: str, current: Optional[str] = None) -> str:
    col = (column or "").strip().lower()
    if col == "done":
        return "done"
    if col in ("doing", "in_progress"):
        return "in_progress"
    if col == "open":
        return "open" if (current or "") != "planned" else "planned"
    return current if current in ITEM_STATUSES else "open"


def list_spaces(conn) -> list[dict]:
    ensure_schema(conn)
    clause, eparams = edition_sql()
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM organizer_spaces WHERE {clause} ORDER BY sort_order, slug",
        eparams,
    ).fetchall()]
    if rows:
        return [style_space(r) for r in rows]
    return [style_space(s) for s in default_spaces()]


def style_space(row: dict) -> dict:
    slug = row.get("slug") or default_space_slug()
    defaults = next((s for s in default_spaces() if s["slug"] == slug), None) or {
        "icon": "●",
        "accent_color": "#57534e",
        "label": slug,
        "kind": "life",
    }
    return {
        "id": row.get("id") or slug,
        "slug": slug,
        "label": row.get("label") or defaults.get("label") or slug,
        "kind": row.get("kind") or defaults.get("kind") or "life",
        "icon": row.get("icon") or defaults.get("icon") or "●",
        "accent_color": row.get("accent_color") or defaults.get("accent_color") or "#57534e",
        "sort_order": row.get("sort_order", 0),
        "edition": row.get("edition") or process_edition(),
    }


def update_space(conn, slug: str, updates: dict) -> Optional[dict]:
    ensure_schema(conn)
    space = normalize_space(slug)
    clause, eparams = edition_sql()
    row = conn.execute(
        f"SELECT * FROM organizer_spaces WHERE slug = ? AND {clause}",
        (space, *eparams),
    ).fetchone()
    if not row:
        return None
    allowed = {"icon", "accent_color", "label"}
    fields, params = [], []
    for key, val in updates.items():
        if key not in allowed or val is None:
            continue
        text = str(val).strip()
        if not text:
            continue
        if key == "accent_color" and not text.startswith("#"):
            continue
        fields.append(f"{key} = ?")
        params.append(text[:32] if key != "label" else text[:80])
    if fields:
        params.append(space)
        conn.execute(
            f"UPDATE organizer_spaces SET {', '.join(fields)} WHERE slug = ? AND edition = ?",
            (*params, process_edition()),
        )
    return next((s for s in list_spaces(conn) if s["slug"] == space), None)


def lookup_quote_id(conn, *, job_id=None, customer_id=None, quote_id=None) -> Optional[str]:
    if quote_id:
        return str(quote_id)
    if not can_read_workroom_jobs():
        return None
    try:
        if job_id:
            row = conn.execute(
                "SELECT quote_id FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row and (row[0] if not hasattr(row, "keys") else row["quote_id"]):
                return str(row[0] if not hasattr(row, "keys") else row["quote_id"])
            row = conn.execute(
                "SELECT id FROM quotes_v2 WHERE job_id = ? ORDER BY updated_at DESC LIMIT 1",
                (job_id,),
            ).fetchone()
            if row:
                return str(row[0] if not hasattr(row, "keys") else row["id"])
        if customer_id:
            row = conn.execute(
                "SELECT id FROM quotes_v2 WHERE customer_id = ? ORDER BY updated_at DESC LIMIT 1",
                (customer_id,),
            ).fetchone()
            if row:
                return str(row[0] if not hasattr(row, "keys") else row["id"])
    except Exception:
        return None
    return None


def record_links(item: dict) -> list[dict]:
    """One-tap hrefs: estimate, client, job, calendar event. Family editions skip Workroom records."""
    links = []
    job_id = item.get("job_id")
    customer_id = item.get("customer_id")
    quote_id = item.get("quote_id")
    event_id = item.get("schedule_event_id")
    if item.get("source") == "schedule_event" and item.get("id"):
        event_id = event_id or item.get("id")
    if job_id and can_read_workroom_jobs():
        links.append({
            "kind": "job",
            "id": str(job_id),
            "label": item.get("job_title") or "Job",
            "href": f"/?product=workroom&section=jobhub&job={job_id}",
        })
    if customer_id:
        links.append({
            "kind": "client",
            "id": str(customer_id),
            "label": item.get("customer_vendor") or "Client",
            "href": f"/?screen=calendar&customer={customer_id}",
        })
    if quote_id and can_read_workroom_jobs():
        links.append({
            "kind": "estimate",
            "id": str(quote_id),
            "label": "Estimate",
            "href": f"/?screen=quote&id={quote_id}",
        })
    if event_id:
        links.append({
            "kind": "calendar",
            "id": str(event_id),
            "label": "Calendar",
            "href": f"/?screen=calendar&event={event_id}",
        })
    return links


def job_progress(conn, job_id: str) -> dict:
    """Progress as a fraction of linked tasks (organizer items + desk tasks)."""
    statuses: list[str] = []
    clause, params = edition_sql()
    try:
        for r in conn.execute(
            f"SELECT status FROM organizer_items WHERE job_id = ? AND {clause}",
            (job_id, *params),
        ).fetchall():
            statuses.append((r[0] if not hasattr(r, "keys") else r["status"]) or "open")
    except Exception:
        pass
    try:
        for r in conn.execute(
            "SELECT status, metadata FROM tasks WHERE metadata LIKE ?",
            (f'%"{job_id}"%',),
        ).fetchall():
            meta_raw = r[1] if not hasattr(r, "keys") else r["metadata"]
            try:
                meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
            except json.JSONDecodeError:
                meta = {}
            if str(meta.get("job_id") or "") != str(job_id):
                continue
            statuses.append((r[0] if not hasattr(r, "keys") else r["status"]) or "open")
    except Exception:
        pass
    total = len(statuses)
    done = sum(1 for s in statuses if str(s) in ("done", "cancelled"))
    return {
        "job_id": job_id,
        "total": total,
        "done": done,
        "open": max(0, total - done),
        "percent": int(round(100 * done / total)) if total else 0,
        "fraction": f"{done}/{total}" if total else "0/0",
    }


def attach_progress(conn, rows: list[dict]) -> list[dict]:
    job_ids = {str(r.get("job_id")) for r in rows if r.get("job_id")}
    cache = {jid: job_progress(conn, jid) for jid in job_ids}
    for row in rows:
        jid = str(row.get("job_id") or "")
        if jid and jid in cache:
            row["progress"] = cache[jid]
    return rows


def board_columns(rows: list[dict]) -> list[dict]:
    grouped = {col["id"]: [] for col in BOARD_COLUMNS}
    for row in rows:
        col = column_for_status(row.get("status"))
        grouped.setdefault(col, []).append(row["id"])
        row["column"] = col
    return [
        {"id": col["id"], "label": col["label"], "item_ids": grouped.get(col["id"], [])}
        for col in BOARD_COLUMNS
    ]


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
    out["column"] = column_for_status(out.get("status"))
    out["record_links"] = record_links(out)
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
    if item.get("job_id") and (not item.get("customer_id") or not item.get("job_title")) and can_read_workroom_jobs():
        try:
            job = conn.execute(
                "SELECT title, client_name, customer_id FROM jobs WHERE id = ?",
                (item["job_id"],),
            ).fetchone()
            if job:
                data = dict(job)
                item["customer_id"] = item.get("customer_id") or data.get("customer_id")
                item["job_title"] = item.get("job_title") or data.get("title")
                item["customer_vendor"] = item.get("customer_vendor") or data.get("client_name")
        except Exception:
            pass
    if not item.get("quote_id"):
        item["quote_id"] = lookup_quote_id(
            conn, job_id=item.get("job_id"), customer_id=item.get("customer_id")
        )
    item["record_links"] = record_links(item)
    return item


def load_event(conn, event_id: str) -> Optional[dict]:
    clause, params = edition_sql("e")
    row = conn.execute(
        event_select_sql(conn) + f" WHERE e.id = ? AND {clause}",
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


def event_select_sql(conn=None) -> str:
    bare = """
            SELECT e.*, NULL as job_title, NULL as client_name, NULL as job_address,
                   NULL as job_customer_id, NULL as customer_name,
                   NULL as customer_phone, NULL as customer_address
            FROM schedule_events e
        """
    if not can_read_workroom_jobs():
        return bare
    names: set[str] = set()
    if conn is not None:
        try:
            names = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        except Exception:
            names = set()
        if not names:
            return bare
    title = "j.title" if (not names or "title" in names) else "NULL"
    client = "j.client_name" if (not names or "client_name" in names) else "NULL"
    addr = "j.address" if (not names or "address" in names) else "NULL"
    cust = "j.customer_id" if (not names or "customer_id" in names) else "NULL"
    join_cust = cust if cust != "NULL" else "NULL"
    return f"""
        SELECT e.*, {title} as job_title, {client} as client_name, {addr} as job_address,
               {join_cust} as job_customer_id, c.name as customer_name,
               c.phone as customer_phone, c.address as customer_address
        FROM schedule_events e
        LEFT JOIN jobs j ON e.job_id = j.id
        LEFT JOIN customers c ON COALESCE(e.customer_id, {join_cust}) = c.id
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
            created_at, updated_at, edition, space_id, quote_id, reminder_at, capture_id, project_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            payload.get("quote_id") or None,
            payload.get("reminder_at") or payload.get("due_at"),
            payload.get("capture_id") or None,
            payload.get("project_id") or payload.get("job_id") or None,
        ),
    )
    replace_assignments(conn, resource_ids or ([primary] if primary else []), item_id=item_id)
    row = conn.execute(
        "SELECT * FROM organizer_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if not row:
        return enrich_item(conn, {"id": item_id, **payload, "kind": kind, "created_at": stamp})
    return enrich_item(conn, dict(row))


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
