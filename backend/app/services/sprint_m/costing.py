"""Planned vs actual materials and labor per job, with margin."""

from __future__ import annotations

import uuid
from app.services.sprint_m.store import audit, get_store, now_iso, row_to_dict
from app.services.sprint_m.work_orders import get_organizer_job


def seed_planned_from_job(job_id: str) -> dict:
    job = get_organizer_job(job_id)
    existing = list_cost_lines(job_id)
    if existing:
        return summarize_job_cost(job_id)
    labor_planned = float(job.get("seamstress_pay") or 0)
    materials_planned = 0.0
    for item in job.get("items") or []:
        # Materials are not always priced on the organizer snapshot; treat
        # remaining quoted amount minus labor as planned materials.
        pass
    quoted = float(job.get("quoted_amount") or 0)
    materials_planned = max(round(quoted - labor_planned, 2), 0)
    with get_store() as conn:
        if materials_planned:
            conn.execute(
                """INSERT INTO sm_job_costs
                   (id, job_id, kind, category, description, planned_amount, actual_amount)
                   VALUES (?, ?, 'planned', 'materials', 'Quote materials', ?, 0)""",
                (str(uuid.uuid4())[:12], job_id, materials_planned),
            )
        if labor_planned:
            conn.execute(
                """INSERT INTO sm_job_costs
                   (id, job_id, kind, category, description, planned_amount, actual_amount)
                   VALUES (?, ?, 'planned', 'labor', 'Seamstress hours/pay from quote', ?, 0)""",
                (str(uuid.uuid4())[:12], job_id, labor_planned),
            )
        audit(conn, "job_cost", job_id, "seeded_from_quote", "system", None)
    return summarize_job_cost(job_id)


def add_cost_line(
    job_id: str,
    *,
    category: str,
    description: str,
    planned_amount: float = 0,
    actual_amount: float = 0,
    actor: str = "owner",
) -> dict:
    if category not in {"materials", "labor"}:
        raise ValueError("category must be materials or labor")
    get_organizer_job(job_id)
    line_id = str(uuid.uuid4())[:12]
    now = now_iso()
    kind = "actual" if actual_amount and not planned_amount else "mixed"
    with get_store() as conn:
        conn.execute(
            """INSERT INTO sm_job_costs
               (id, job_id, kind, category, description, planned_amount, actual_amount, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (line_id, job_id, kind, category, description, planned_amount, actual_amount, now, now),
        )
        audit(conn, "job_cost", line_id, "added", actor, category)
    return summarize_job_cost(job_id)


def update_actual(line_id: str, actual_amount: float, *, actor: str = "owner") -> dict:
    with get_store() as conn:
        row = conn.execute("SELECT job_id FROM sm_job_costs WHERE id = ?", (line_id,)).fetchone()
        if not row:
            raise KeyError(f"Cost line {line_id} not found")
        now = now_iso()
        conn.execute(
            "UPDATE sm_job_costs SET actual_amount = ?, updated_at = ? WHERE id = ?",
            (actual_amount, now, line_id),
        )
        audit(conn, "job_cost", line_id, "actual_updated", actor, str(actual_amount))
        job_id = row["job_id"]
    return summarize_job_cost(job_id)


def list_cost_lines(job_id: str) -> list[dict]:
    with get_store() as conn:
        rows = conn.execute(
            "SELECT * FROM sm_job_costs WHERE job_id = ? ORDER BY created_at",
            (job_id,),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


def summarize_job_cost(job_id: str) -> dict:
    job = get_organizer_job(job_id)
    lines = list_cost_lines(job_id)
    planned_materials = sum(float(l["planned_amount"] or 0) for l in lines if l["category"] == "materials")
    actual_materials = sum(float(l["actual_amount"] or 0) for l in lines if l["category"] == "materials")
    planned_labor = sum(float(l["planned_amount"] or 0) for l in lines if l["category"] == "labor")
    actual_labor = sum(float(l["actual_amount"] or 0) for l in lines if l["category"] == "labor")
    revenue = float(job.get("quoted_amount") or 0)
    planned_cost = planned_materials + planned_labor
    actual_cost = actual_materials + actual_labor
    planned_profit = round(revenue - planned_cost, 2)
    actual_profit = round(revenue - actual_cost, 2)
    planned_margin = round((planned_profit / revenue) * 100, 2) if revenue else 0.0
    actual_margin = round((actual_profit / revenue) * 100, 2) if revenue else 0.0
    return {
        "job_id": job_id,
        "job_number": job.get("job_number"),
        "revenue": revenue,
        "planned": {
            "materials": round(planned_materials, 2),
            "labor": round(planned_labor, 2),
            "total": round(planned_cost, 2),
            "profit": planned_profit,
            "margin_pct": planned_margin,
        },
        "actual": {
            "materials": round(actual_materials, 2),
            "labor": round(actual_labor, 2),
            "total": round(actual_cost, 2),
            "profit": actual_profit,
            "margin_pct": actual_margin,
        },
        "variance": {
            "materials": round(actual_materials - planned_materials, 2),
            "labor": round(actual_labor - planned_labor, 2),
            "total": round(actual_cost - planned_cost, 2),
            "margin_pct": round(actual_margin - planned_margin, 2),
        },
        "lines": lines,
    }
