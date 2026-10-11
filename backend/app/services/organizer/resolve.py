"""Resolve job / customer / person names for Organizer drafts."""

from __future__ import annotations

import re
from typing import Optional


def _name_variants(name: str) -> list[str]:
    raw = (name or "").strip()
    if not raw:
        return []
    variants = [raw]
    stripped = re.sub(r"'s\b", "", raw, flags=re.I).strip()
    if stripped and stripped.lower() != raw.lower():
        variants.append(stripped)
    return variants


def search_jobs(conn, name: str, limit: int = 8) -> list[dict]:
    from app.services.organizer.edition import can_read_workroom_jobs
    if not name or not can_read_workroom_jobs():
        return []
    seen = set()
    out = []
    for token in _name_variants(name):
        q = f"%{token}%"
        rows = conn.execute(
            """
            SELECT j.id, j.title, j.job_number, j.client_name, j.address,
                   j.customer_id, j.status, c.name as customer_name, c.phone as customer_phone,
                   c.address as customer_address
            FROM jobs j
            LEFT JOIN customers c ON j.customer_id = c.id
            WHERE j.title LIKE ? OR j.job_number LIKE ? OR j.client_name LIKE ?
                  OR c.name LIKE ?
            ORDER BY j.updated_at DESC
            LIMIT ?
            """,
            (q, q, q, q, limit),
        ).fetchall()
        for r in rows:
            data = dict(r)
            if data["id"] in seen:
                continue
            seen.add(data["id"])
            out.append(data)
            if len(out) >= limit:
                return out
    return out


def search_customers(conn, name: str, limit: int = 8) -> list[dict]:
    from app.services.organizer.edition import can_read_business_directory
    if not name or not can_read_business_directory():
        return []
    q = f"%{name.strip()}%"
    rows = conn.execute(
        """
        SELECT id, name, phone, email, address, type
        FROM customers
        WHERE name LIKE ? OR company LIKE ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (q, q, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def search_resources(conn, name: str, limit: int = 8) -> list[dict]:
    from app.services.organizer.edition import edition_sql
    if not name:
        return []
    clause, eparams = edition_sql()
    q = f"%{name.strip()}%"
    rows = conn.execute(
        f"""
        SELECT id, name, role, phone, email, address, source, source_id
        FROM organizer_resources
        WHERE active = 1 AND {clause} AND (name LIKE ? OR role LIKE ?)
        ORDER BY name
        LIMIT ?
        """,
        (*eparams, q, q, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def attach_matches(conn, draft: dict) -> dict:
    """Fill job_id / customer / phone / address from a parsed subject name."""
    name = (draft.get("subject_name") or "").strip()
    out = dict(draft)
    out["matched_jobs"] = []
    out["matched_people"] = []
    if not name:
        return out
    jobs = search_jobs(conn, name)
    people = search_resources(conn, name)
    customers = search_customers(conn, name)
    out["matched_jobs"] = jobs
    out["matched_people"] = people
    if jobs:
        job = jobs[0]
        out["job_id"] = job.get("id")
        out["job_title"] = job.get("title")
        out["customer_id"] = job.get("customer_id")
        out["customer_vendor"] = job.get("client_name") or job.get("customer_name")
        out["phone"] = out.get("phone") or job.get("customer_phone")
        out["location_address"] = (
            out.get("location_address") or job.get("address") or job.get("customer_address")
        )
    elif customers:
        cust = customers[0]
        out["customer_id"] = cust.get("id")
        out["customer_vendor"] = cust.get("name")
        out["phone"] = out.get("phone") or cust.get("phone")
        out["location_address"] = out.get("location_address") or cust.get("address")
    if people and not out.get("resource_id"):
        out["resource_id"] = people[0].get("id")
        out["assigned_resource_ids"] = [people[0].get("id")]
    return out
