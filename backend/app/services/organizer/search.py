"""Smart search across organizer items, jobs, clients, estimates. Edition-gated."""

from __future__ import annotations

from app.services.organizer.edition import can_read_workroom_jobs, edition_sql, process_edition


def search_organizer(conn, query: str, *, limit: int = 30) -> dict:
    q = (query or "").strip()
    if not q:
        return {"q": q, "items": [], "jobs": [], "clients": [], "estimates": [], "edition": process_edition()}
    like = f"%{q}%"
    clause, params = edition_sql()
    items = []
    try:
        rows = conn.execute(
            f"""SELECT id, title, kind, space_id, status, due_at, job_id
                FROM organizer_items
                WHERE {clause} AND (title LIKE ? OR notes LIKE ? OR waiting_on LIKE ?)
                ORDER BY updated_at DESC LIMIT ?""",
            (*params, like, like, like, limit),
        ).fetchall()
        items = [dict(r) for r in rows]
    except Exception:
        try:
            rows = conn.execute(
                f"""SELECT id, title, kind, space_id, status, due_at, job_id
                    FROM organizer_items
                    WHERE {clause} AND (title LIKE ? OR notes LIKE ?)
                    ORDER BY updated_at DESC LIMIT ?""",
                (*params, like, like, limit),
            ).fetchall()
            items = [dict(r) for r in rows]
        except Exception:
            items = []

    jobs, clients, estimates = [], [], []
    if can_read_workroom_jobs():
        try:
            jobs = [dict(r) for r in conn.execute(
                """SELECT id, title, client_name, status, customer_id FROM jobs
                   WHERE title LIKE ? OR client_name LIKE ? OR job_number LIKE ?
                   LIMIT ?""",
                (like, like, like, limit),
            ).fetchall()]
        except Exception:
            try:
                jobs = [dict(r) for r in conn.execute(
                    "SELECT id, title, status FROM jobs WHERE title LIKE ? LIMIT ?",
                    (like, limit),
                ).fetchall()]
            except Exception:
                jobs = []
        try:
            clients = [dict(r) for r in conn.execute(
                "SELECT id, name, phone, email FROM customers WHERE name LIKE ? OR phone LIKE ? LIMIT ?",
                (like, like, limit),
            ).fetchall()]
        except Exception:
            clients = []
        try:
            estimates = [dict(r) for r in conn.execute(
                """SELECT id, quote_number, customer_name, status, total, job_id
                   FROM quotes_v2
                   WHERE quote_number LIKE ? OR customer_name LIKE ? OR project_name LIKE ?
                   LIMIT ?""",
                (like, like, like, limit),
            ).fetchall()]
        except Exception:
            estimates = []

    return {
        "q": q,
        "edition": process_edition(),
        "items": items,
        "jobs": jobs,
        "clients": clients,
        "estimates": estimates,
        "hrefs": {
            "item": "/?screen=calendar",
            "job": "/?product=workroom&section=jobhub&job=",
            "client": "/?screen=calendar&customer=",
            "estimate": "/?screen=quote&id=",
        },
    }
