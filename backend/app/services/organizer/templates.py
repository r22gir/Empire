"""Checklist and recurring templates. Any space — Workroom job is one seeded example."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

from app.services.organizer.edition import edition_sql, normalize_space, process_edition
from app.services.organizer.store import insert_item, new_id, now_iso

JOB_STEPS = (
    "Order materials",
    "Cut",
    "Build",
    "Upholster",
    "Install",
    "Invoice",
    "Collect balance",
)


def seed_templates(conn) -> list[dict]:
    edition = process_edition()
    seeds = [
        {"slug": "job", "label": "Job", "kind": "job", "space_id": "workroom", "steps": list(JOB_STEPS)},
        {"slug": "family-week", "label": "Family week", "kind": "checklist", "space_id": "family",
         "steps": ["School forms", "Groceries", "Activities", "Bills"]},
        {"slug": "personal-reset", "label": "Personal reset", "kind": "checklist", "space_id": "personal",
         "steps": ["Health", "Errands", "Admin"]},
    ]
    out = []
    for seed in seeds:
        existing = conn.execute(
            "SELECT * FROM organizer_templates WHERE edition = ? AND slug = ?",
            (edition, seed["slug"]),
        ).fetchone()
        if existing:
            out.append(dict(existing))
            continue
        tid = new_id()
        conn.execute(
            """INSERT INTO organizer_templates
               (id, edition, space_id, slug, label, kind, steps_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tid, edition, seed["space_id"], seed["slug"], seed["label"], seed["kind"],
             json.dumps(seed["steps"]), now_iso()),
        )
        out.append(dict(conn.execute("SELECT * FROM organizer_templates WHERE id = ?", (tid,)).fetchone()))
    return out


def list_templates(conn) -> list[dict]:
    seed_templates(conn)
    clause, params = edition_sql()
    rows = conn.execute(
        f"SELECT * FROM organizer_templates WHERE {clause} ORDER BY label",
        params,
    ).fetchall()
    out = []
    for r in rows:
        data = dict(r)
        try:
            data["steps"] = json.loads(data.get("steps_json") or "[]")
        except Exception:
            data["steps"] = []
        out.append(data)
    return out


def save_template(conn, *, label: str, steps: list[str], space_id: Optional[str] = None, slug: Optional[str] = None, kind: str = "custom") -> dict:
    edition = process_edition()
    slug = (slug or label.lower().replace(" ", "-"))[:40]
    clean = [str(s).strip() for s in steps if str(s).strip()]
    space = normalize_space(space_id) if space_id else None
    existing = conn.execute(
        "SELECT id FROM organizer_templates WHERE edition = ? AND slug = ?",
        (edition, slug),
    ).fetchone()
    if existing:
        tid = existing[0] if not hasattr(existing, "keys") else existing["id"]
        conn.execute(
            """UPDATE organizer_templates
               SET space_id = ?, label = ?, kind = ?, steps_json = ?
             WHERE id = ?""",
            (space, label, kind, json.dumps(clean), tid),
        )
    else:
        tid = new_id()
        conn.execute(
            """INSERT INTO organizer_templates
               (id, edition, space_id, slug, label, kind, steps_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tid, edition, space, slug, label, kind, json.dumps(clean), now_iso()),
        )
    row = conn.execute("SELECT * FROM organizer_templates WHERE id = ?", (tid,)).fetchone()
    data = dict(row)
    data["steps"] = json.loads(data.get("steps_json") or "[]")
    return data


def apply_template(conn, template_id: str, *, space_id: Optional[str] = None, job_id: Optional[str] = None, title: Optional[str] = None) -> dict:
    clause, params = edition_sql()
    row = conn.execute(
        f"SELECT * FROM organizer_templates WHERE id = ? AND {clause}",
        (template_id, *params),
    ).fetchone()
    if not row:
        return {"ok": False, "created": [], "sent": False, "message": "Template not found"}
    tpl = dict(row)
    steps = json.loads(tpl.get("steps_json") or "[]")
    space = normalize_space(space_id or tpl.get("space_id"))
    created = []
    for i, step in enumerate(steps):
        created.append(insert_item(conn, {
            "kind": "todo",
            "title": f"{title + ' · ' if title else ''}{step}",
            "space_id": space,
            "job_id": job_id,
            "template_id": tpl["id"],
            "status": "open",
            "notes": f"Checklist {i + 1}/{len(steps)}",
            "created_by": "manual",
        }))
    return {
        "ok": True,
        "created": created,
        "sent": False,
        "count": len(created),
        "fraction": f"0/{len(created)}" if created else "0/0",
        "template": tpl.get("label"),
    }


def set_recurrence(conn, *, item_id: str, freq: str = "weekly") -> dict:
    if freq not in {"daily", "weekly", "monthly"}:
        freq = "weekly"
    delta = {"daily": 1, "weekly": 7, "monthly": 30}[freq]
    next_due = (date.today() + timedelta(days=delta)).isoformat() + "T09:00:00"
    rid = new_id()
    conn.execute(
        """INSERT INTO organizer_recurrence (id, edition, item_id, freq, next_due, active, created_at)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        (rid, process_edition(), item_id, freq, next_due, now_iso()),
    )
    try:
        conn.execute(
            "UPDATE organizer_items SET recurrence_freq = ?, updated_at = ? WHERE id = ?",
            (freq, now_iso(), item_id),
        )
    except Exception:
        pass
    return {"ok": True, "id": rid, "freq": freq, "next_due": next_due, "sent": False}


def spawn_due_recurring(conn) -> dict:
    """When a recurring item is due, create the next copy. Never sends."""
    clause, params = edition_sql()
    today = date.today().isoformat()
    rows = conn.execute(
        f"""SELECT * FROM organizer_recurrence
            WHERE {clause} AND active = 1 AND next_due IS NOT NULL AND substr(next_due,1,10) <= ?""",
        (*params, today),
    ).fetchall()
    spawned = []
    for r in rows:
        rec = dict(r)
        src = conn.execute("SELECT * FROM organizer_items WHERE id = ?", (rec.get("item_id"),)).fetchone()
        if not src:
            continue
        item = dict(src)
        created = insert_item(conn, {
            "kind": item.get("kind") or "todo",
            "title": item.get("title"),
            "space_id": item.get("space_id"),
            "job_id": item.get("job_id"),
            "due_at": rec.get("next_due"),
            "status": "open",
            "notes": "Recurring copy. Original stays.",
        })
        delta = {"daily": 1, "weekly": 7, "monthly": 30}.get(rec.get("freq") or "weekly", 7)
        nxt = (date.today() + timedelta(days=delta)).isoformat() + "T09:00:00"
        conn.execute(
            "UPDATE organizer_recurrence SET next_due = ? WHERE id = ?",
            (nxt, rec["id"]),
        )
        spawned.append(created)
    return {"ok": True, "spawned": spawned, "sent": False, "count": len(spawned)}
