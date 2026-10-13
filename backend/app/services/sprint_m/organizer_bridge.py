"""Publish Sprint M work orders as tasks on the founder Organizer.

Depends on PRs #111 / #120 / #129 (`app.services.organizer`, WorkroomOrganizer,
/?screen=calendar, /api/v1/organizer/*). This module does not copy that stack.

When the founder Organizer is on the tree, items are inserted with
`organizer.store.insert_item` into the Workroom / Empire / Family space.
Isolated Sprint M tests write the same task shape into the sidecar DB only.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from app.services.sprint_m.fabric import strip_client_facing
from app.services.sprint_m.store import now_iso

logger = logging.getLogger("sprint_m.organizer")

SPACE_BY_UNIT = {
    "workroom": "workroom",
    "nelmas": "empire",
    "nelma": "empire",
    "empire": "empire",
    "luxe": "empire",
    "family": "family",
}

LOCAL_ITEMS_SQL = """
CREATE TABLE IF NOT EXISTS organizer_items (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    job_id TEXT,
    customer_id TEXT,
    due_at TEXT,
    start_time TEXT,
    status TEXT DEFAULT 'open',
    space_id TEXT,
    quote_id TEXT,
    order_ref TEXT,
    notes TEXT,
    created_by TEXT DEFAULT 'max',
    created_at TEXT
);
"""


def space_for_job(job: dict) -> str:
    unit = str(job.get("business_unit") or "workroom").strip().lower()
    return SPACE_BY_UNIT.get(unit, "workroom")


def _task_title(job: dict) -> str:
    number = job.get("job_number") or "WO"
    title = strip_client_facing(job.get("title") or "Work order")
    return f"{number}: {title}"


def _founder_insert():
    try:
        from app.services.organizer.store import ensure_schema, insert_item

        return ensure_schema, insert_item
    except ImportError:
        return None


def _insert_local(conn, payload: dict) -> dict:
    conn.executescript(LOCAL_ITEMS_SQL)
    item_id = uuid.uuid4().hex
    stamp = now_iso()
    row = {
        "id": item_id,
        "kind": payload.get("kind") or "todo",
        "title": (payload.get("title") or "").strip(),
        "job_id": payload.get("job_id"),
        "customer_id": payload.get("customer_id"),
        "due_at": payload.get("due_at"),
        "start_time": payload.get("start_time"),
        "status": payload.get("status") or "open",
        "space_id": payload.get("space_id") or "workroom",
        "quote_id": payload.get("quote_id"),
        "order_ref": payload.get("order_ref"),
        "notes": payload.get("notes"),
        "created_by": "max",
        "created_at": stamp,
    }
    conn.execute(
        """INSERT INTO organizer_items
           (id, kind, title, job_id, customer_id, due_at, start_time, status,
            space_id, quote_id, order_ref, notes, created_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            row["id"],
            row["kind"],
            row["title"],
            row["job_id"],
            row["customer_id"],
            row["due_at"],
            row["start_time"],
            row["status"],
            row["space_id"],
            row["quote_id"],
            row["order_ref"],
            row["notes"],
            row["created_by"],
            row["created_at"],
        ),
    )
    return row


def _insert_item(conn, payload: dict) -> dict:
    founder = _founder_insert()
    if founder is not None:
        ensure_schema, insert_item = founder
        try:
            ensure_schema(conn)
            return insert_item(conn, payload)
        except Exception:
            logger.exception("founder insert_item failed; using Sprint M sidecar")
    return _insert_local(conn, payload)


def publish_work_order_tasks(job: dict, conn) -> list[dict]:
    """Create Organizer tasks for a work order on `conn` (sidecar in tests)."""
    conn.executescript(LOCAL_ITEMS_SQL)
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
        _insert_item(
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
            _insert_item(
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
            _insert_item(
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
    if _founder_insert() is None:
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
        conn.executescript(LOCAL_ITEMS_SQL)
        rows = conn.execute(
            """SELECT id, kind, title, space_id, job_id, due_at, status, order_ref, quote_id
               FROM organizer_items WHERE job_id = ? ORDER BY created_at""",
            (job_id,),
        ).fetchall()
    except Exception:
        return []
    return [dict(row) for row in rows if hasattr(row, "keys")]


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
