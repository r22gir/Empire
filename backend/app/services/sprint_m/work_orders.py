"""Create an Organizer job from an approved quote.

Carries fabric (V###-Color only), style, photos, seamstress hours/pay, and due date.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from app.services.sprint_m.fabric import FabricCodeError, sanitize_fabric_code, strip_client_facing
from app.services.sprint_m.measurements import normalize_dimensions, normalize_measurement
from app.services.sprint_m.organizer_bridge import (
    list_tasks_for_job,
    publish_to_founder_organizer,
    publish_work_order_tasks,
    space_for_job,
    task_summaries,
)
from app.services.sprint_m.store import audit, get_store, now_iso, row_to_dict

APPROVED_STATUSES = {"approved", "accepted", "ordered", "signed", "proposal_signed"}


class QuoteNotApproved(ValueError):
    pass


def _next_job_number(conn) -> str:
    year = datetime.now().year
    row = conn.execute(
        "SELECT job_number FROM sm_organizer_jobs WHERE job_number LIKE ? ORDER BY job_number DESC LIMIT 1",
        (f"ORG-{year}-%",),
    ).fetchone()
    last = 0
    if row:
        try:
            last = int(str(row[0]).split("-")[-1])
        except (ValueError, IndexError):
            last = 0
    return f"ORG-{year}-{last + 1:03d}"


def _parse_json(value: Any, default):
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _line_items(quote: dict) -> list[dict]:
    items = quote.get("line_items") or quote.get("items") or []
    if items:
        return list(items)
    rooms = quote.get("rooms") or []
    out = []
    for room in rooms:
        room_name = room.get("name") or room.get("room") or ""
        for item in room.get("items") or room.get("windows") or []:
            cloned = dict(item)
            cloned.setdefault("room", room_name)
            out.append(cloned)
    return out


def _photos(quote: dict, item: dict | None = None) -> list[str]:
    urls: list[str] = []
    sources = []
    if item:
        sources.extend(item.get("photos") or item.get("photo_urls") or [])
        photo_ids = _parse_json(item.get("photo_ids_json"), [])
        sources.extend(photo_ids)
    sources.extend(quote.get("photos") or [])
    sources.extend(_parse_json(quote.get("photos_json"), []))
    for photo in sources:
        if isinstance(photo, str) and photo:
            urls.append(photo)
        elif isinstance(photo, dict):
            url = photo.get("url") or photo.get("filepath") or photo.get("path") or photo.get("filename")
            if url:
                urls.append(url)
    # de-dupe preserving order
    seen = set()
    unique = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _item_fabric(item: dict, conn) -> str | None:
    raw = item.get("fabric_code") or item.get("fabric") or item.get("fabric_name")
    material_type = item.get("material_type") or item.get("fabric_type")
    return sanitize_fabric_code(raw, conn=conn, material_type=material_type)


def _item_style(item: dict) -> str:
    return (
        item.get("item_style")
        or item.get("style")
        or item.get("treatment")
        or item.get("type")
        or item.get("item_type")
        or ""
    )


def _item_hours(item: dict) -> tuple[float, float, float]:
    hours = float(item.get("seamstress_hours") or item.get("labor_hours") or 0)
    rate = float(item.get("seamstress_rate") or item.get("labor_rate") or 0)
    pay = float(item.get("seamstress_pay") or item.get("labor_total") or 0)
    if not pay and hours and rate:
        pay = round(hours * rate, 2)
    return hours, rate, pay


def _item_measurements(item: dict) -> dict:
    dims = item.get("measurements") or item.get("dimensions") or {}
    if not dims:
        dims = {
            "width": item.get("width"),
            "height": item.get("height"),
            "depth": item.get("depth"),
        }
    return normalize_dimensions(dims)


def create_organizer_job_from_quote(quote: dict, *, actor: str = "owner") -> dict:
    status = str(quote.get("status") or "").lower()
    if status not in APPROVED_STATUSES:
        raise QuoteNotApproved(
            f"Quote must be approved before creating a work order (current: {quote.get('status')!r})"
        )

    quote_id = str(quote.get("id") or quote.get("quote_id") or "")
    if not quote_id:
        raise ValueError("quote id is required")

    items = _line_items(quote)
    fabric_codes: list[str] = []
    built_items: list[dict] = []
    total_hours = 0.0
    total_pay = 0.0
    blended_rate = 0.0
    styles: list[str] = []
    all_photos = _photos(quote)

    with get_store() as conn:
        existing = conn.execute(
            "SELECT * FROM sm_organizer_jobs WHERE quote_id = ?", (quote_id,)
        ).fetchone()
        if existing:
            return get_organizer_job(existing["id"])

        for idx, raw in enumerate(items, start=1):
            try:
                fabric = _item_fabric(raw, conn)
            except FabricCodeError:
                fabric = None
            if fabric:
                fabric_codes.append(fabric)
            style = strip_client_facing(_item_style(raw))
            if style:
                styles.append(style)
            hours, rate, pay = _item_hours(raw)
            total_hours += hours
            total_pay += pay
            if rate:
                blended_rate = rate
            photos = _photos(quote, raw)
            for url in photos:
                if url not in all_photos:
                    all_photos.append(url)
            built_items.append(
                {
                    "line_number": raw.get("line_number") or idx,
                    "item_type": raw.get("item_type") or raw.get("type") or "",
                    "style": style,
                    "description": strip_client_facing(raw.get("description") or raw.get("name") or ""),
                    "room": raw.get("room") or "",
                    "fabric_code": fabric,
                    "measurements": _item_measurements(raw),
                    "photos": photos,
                    "seamstress_hours": hours,
                    "seamstress_rate": rate,
                    "seamstress_pay": pay,
                    "quantity": float(raw.get("quantity") or 1),
                }
            )

        if total_hours and not blended_rate:
            blended_rate = round(total_pay / total_hours, 2) if total_hours else 0

        due_date = (
            quote.get("due_date")
            or quote.get("production_due_date")
            or quote.get("install_date")
            or (quote.get("seamstress") or {}).get("due_date")
        )
        quoted_amount = float(quote.get("total") or quote.get("grand_total") or quote.get("quoted_amount") or 0)
        job_id = str(uuid.uuid4())[:12]
        now = now_iso()

        job_number = _next_job_number(conn)
        title = strip_client_facing(
            quote.get("project_name") or quote.get("title") or f"Job from {quote.get('quote_number') or quote_id}"
        )
        job_stub = {
            "id": job_id,
            "job_number": job_number,
            "quote_id": quote_id,
            "customer_id": quote.get("customer_id"),
            "title": title,
            "style": ", ".join(dict.fromkeys(styles)),
            "fabric_codes": fabric_codes,
            "due_date": due_date,
            "business_unit": quote.get("business_unit") or "workroom",
        }
        org_tasks = publish_work_order_tasks(job_stub, conn)
        conn.execute(
            """INSERT INTO sm_organizer_jobs (
                id, job_number, quote_id, quote_number, customer_id, customer_name,
                business_unit, status, title, style, photos_json, fabric_codes_json,
                seamstress_hours, seamstress_rate, seamstress_pay, due_date,
                quoted_amount, notes, measurements_json, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'sold', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                job_number,
                quote_id,
                quote.get("quote_number"),
                quote.get("customer_id"),
                quote.get("customer_name") or quote.get("client_name") or "",
                quote.get("business_unit") or "workroom",
                title,
                ", ".join(dict.fromkeys(styles)),
                json.dumps(all_photos),
                json.dumps(fabric_codes),
                total_hours,
                blended_rate,
                total_pay,
                due_date,
                quoted_amount,
                strip_client_facing(quote.get("notes") or ""),
                json.dumps(quote.get("measurements") or {}),
                json.dumps(
                    {
                        "source": "approved_quote",
                        "quote_status": quote.get("status"),
                        "fabric_policy": "docs/FABRIC_CODES.csv sequential registry",
                        "measurements": "fractions",
                        "organizer_space": space_for_job(job_stub),
                        "organizer_item_ids": [t.get("id") for t in org_tasks if t.get("id")],
                    }
                ),
                now,
                now,
            ),
        )
        for item in built_items:
            conn.execute(
                """INSERT INTO sm_job_items (
                    id, job_id, line_number, item_type, style, description, room,
                    fabric_code, measurements_json, photo_urls_json,
                    seamstress_hours, seamstress_rate, seamstress_pay, quantity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4())[:12],
                    job_id,
                    item["line_number"],
                    item["item_type"],
                    item["style"],
                    item["description"],
                    item["room"],
                    item["fabric_code"],
                    json.dumps(item["measurements"]),
                    json.dumps(item["photos"]),
                    item["seamstress_hours"],
                    item["seamstress_rate"],
                    item["seamstress_pay"],
                    item["quantity"],
                ),
            )
        audit(conn, "organizer_job", job_id, "created_from_quote", actor, quote_id)

    job = get_organizer_job(job_id)
    publish_to_founder_organizer(job)
    return job


def get_organizer_job(job_id: str) -> dict:
    with get_store() as conn:
        row = conn.execute("SELECT * FROM sm_organizer_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise KeyError(f"Organizer job {job_id} not found")
        job = row_to_dict(row)
        items = conn.execute(
            "SELECT * FROM sm_job_items WHERE job_id = ? ORDER BY line_number", (job_id,)
        ).fetchall()
        job["items"] = [_hydrate_item(row_to_dict(i)) for i in items]
        job["photos"] = _parse_json(job.pop("photos_json", "[]"), [])
        job["fabric_codes"] = _parse_json(job.pop("fabric_codes_json", "[]"), [])
        job["measurements"] = _parse_json(job.pop("measurements_json", "{}"), {})
        job["metadata"] = _parse_json(job.pop("metadata_json", "{}"), {})
        job["organizer_tasks"] = task_summaries(list_tasks_for_job(conn, job_id))
        job["organizer_space"] = job["metadata"].get("organizer_space") or space_for_job(job)
        return job


def _hydrate_item(item: dict) -> dict:
    item["measurements"] = _parse_json(item.pop("measurements_json", "{}"), {})
    item["photos"] = _parse_json(item.pop("photo_urls_json", "[]"), [])
    return item


def list_organizer_jobs(status: str | None = None, limit: int = 50) -> list[dict]:
    with get_store() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM sm_organizer_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sm_organizer_jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        jobs = []
        for row in rows:
            job = row_to_dict(row)
            job_id = job["id"]
            items = conn.execute(
                "SELECT * FROM sm_job_items WHERE job_id = ? ORDER BY line_number",
                (job_id,),
            ).fetchall()
            job["items"] = [_hydrate_item(row_to_dict(i)) for i in items]
            job["photos"] = _parse_json(job.pop("photos_json", "[]"), [])
            job["fabric_codes"] = _parse_json(job.pop("fabric_codes_json", "[]"), [])
            job["measurements"] = _parse_json(job.pop("measurements_json", "{}"), {})
            job["metadata"] = _parse_json(job.pop("metadata_json", "{}"), {})
            job["organizer_tasks"] = task_summaries(list_tasks_for_job(conn, job_id))
            job["organizer_space"] = job["metadata"].get("organizer_space") or space_for_job(job)
            jobs.append(job)
        return jobs


def update_job_status(job_id: str, status: str, *, actor: str = "system") -> dict:
    with get_store() as conn:
        exists = conn.execute("SELECT id FROM sm_organizer_jobs WHERE id = ?", (job_id,)).fetchone()
        if not exists:
            raise KeyError(f"Organizer job {job_id} not found")
        now = now_iso()
        extra = ""
        params: list[Any] = [status, now, job_id]
        if status == "scheduled":
            extra = ", scheduled_at = ?"
            params = [status, now, now, job_id]
        conn.execute(
            f"UPDATE sm_organizer_jobs SET status = ?, updated_at = ?{extra} WHERE id = ?",
            params,
        )
        audit(conn, "organizer_job", job_id, "status_changed", actor, status)
    return get_organizer_job(job_id)


def schedule_job(job_id: str, when: str | None = None, *, actor: str = "owner") -> dict:
    when = when or now_iso()
    with get_store() as conn:
        exists = conn.execute("SELECT id FROM sm_organizer_jobs WHERE id = ?", (job_id,)).fetchone()
        if not exists:
            raise KeyError(f"Organizer job {job_id} not found")
        now = now_iso()
        conn.execute(
            "UPDATE sm_organizer_jobs SET status = 'scheduled', scheduled_at = ?, updated_at = ? WHERE id = ?",
            (when, now, job_id),
        )
        audit(conn, "organizer_job", job_id, "scheduled", actor, when)
    return get_organizer_job(job_id)
