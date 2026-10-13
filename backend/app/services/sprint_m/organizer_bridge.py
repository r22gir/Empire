"""Publish Sprint M work orders as tasks on the founder Organizer.

Does not create a second Organizer. Items land in Workroom / Empire / Family
spaces on the existing /api/v1/organizer board (WorkroomOrganizer).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.services.sprint_m.fabric import strip_client_facing

logger = logging.getLogger("sprint_m.organizer")

SPACE_BY_UNIT = {
    "workroom": "workroom",
    "nelmas": "empire",
    "nelma": "empire",
    "empire": "empire",
    "luxe": "empire",
    "family": "family",
}


def space_for_job(job: dict) -> str:
    unit = str(job.get("business_unit") or "workroom").strip().lower()
    return SPACE_BY_UNIT.get(unit, "workroom")


def _task_title(job: dict) -> str:
    number = job.get("job_number") or "WO"
    title = strip_client_facing(job.get("title") or "Work order")
    return f"{number}: {title}"


def publish_work_order_tasks(job: dict, conn) -> list[dict]:
    """Insert founder Organizer tasks for a work order on `conn`.

    Isolated tests pass the Sprint M sqlite connection (never live empire.db).
    Production passes the founder Organizer database via get_db().
    """
    from app.services.organizer.store import ensure_schema, insert_item

    ensure_schema(conn)
    space = space_for_job(job)
    job_id = str(job.get("id") or "")
    if not job_id:
        return []

    existing = conn.execute(
        "SELECT id FROM organizer_items WHERE job_id = ?",
        (job_id,),
    ).fetchall()
    if existing:
        return [dict(r) if hasattr(r, "keys") else {"id": r[0]} for r in existing]

    created: list[dict] = []
    due = job.get("due_date")
    fabrics = [c for c in (job.get("fabric_codes") or []) if c]
    notes = strip_client_facing(
        " · ".join(
            p
            for p in (
                job.get("style") or "",
                ", ".join(fabrics),
                f"due {due}" if due else "",
            )
            if p
        )
    )

    created.append(
        insert_item(
            conn,
            {
                "kind": "deadline" if due else "todo",
                "title": _task_title(job),
                "job_id": job_id,
                "customer_id": job.get("customer_id"),
                "due_at": due,
                "status": "open",
                "space_id": space,
                "quote_id": job.get("quote_id"),
                "notes": notes,
                "created_by": "max",
            },
        )
    )

    if due:
        created.append(
            insert_item(
                conn,
                {
                    "kind": "job_milestone",
                    "title": strip_client_facing(f"Due · {job.get('job_number') or job_id}"),
                    "job_id": job_id,
                    "customer_id": job.get("customer_id"),
                    "due_at": due,
                    "start_time": f"{str(due)[:10]}T09:00:00",
                    "status": "planned",
                    "space_id": space,
                    "quote_id": job.get("quote_id"),
                    "created_by": "max",
                },
            )
        )

    for code in fabrics:
        created.append(
            insert_item(
                conn,
                {
                    "kind": "material_order",
                    "title": f"Cut {code}",
                    "job_id": job_id,
                    "order_ref": code,
                    "status": "open",
                    "space_id": space,
                    "quote_id": job.get("quote_id"),
                    "created_by": "max",
                },
            )
        )

    return created


def publish_to_founder_organizer(job: dict) -> list[dict]:
    """Write to live Organizer only when we are not in an isolated test DB."""
    if os.getenv("SPRINT_M_DB"):
        return []
    try:
        from app.db.database import get_db

        db = get_db()
        items = publish_work_order_tasks(job, db)
        try:
            db.commit()
        except Exception:
            pass
        return items
    except Exception:
        logger.exception("founder Organizer publish skipped")
        return []


def list_tasks_for_job(conn, job_id: str) -> list[dict]:
    try:
        rows = conn.execute(
            """SELECT id, kind, title, space_id, job_id, due_at, status, order_ref, quote_id
               FROM organizer_items WHERE job_id = ? ORDER BY created_at""",
            (job_id,),
        ).fetchall()
    except Exception:
        return []
    out = []
    for row in rows:
        item = dict(row) if hasattr(row, "keys") else {}
        if item:
            out.append(item)
    return out


def task_summaries(items: list[dict[str, Any]]) -> list[dict]:
    return [
        {
            "id": i.get("id"),
            "kind": i.get("kind"),
            "title": i.get("title"),
            "space_id": i.get("space_id"),
            "status": i.get("status"),
            "due_at": i.get("due_at"),
            "order_ref": i.get("order_ref"),
        }
        for i in items
    ]
