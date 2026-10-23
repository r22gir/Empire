"""Many-to-many job ↔ customer links.

A job can have several clients (Le Midi: Maggie + Lauren). One customer can
sit on several jobs (Maggie on Willard and Le Midi) — we never split or copy
the customer row. jobs.customer_id stays the primary client for older callers.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from app.db.database import dict_row

VALID_ROLES = ("primary", "designer", "contact")


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _cols(conn, table: str) -> set[str]:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.Error:
        return set()


def ensure_job_clients_schema(conn) -> None:
    """Create job_clients and backfill jobs.customer_id as role=primary."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_clients (
            job_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'primary',
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (job_id, customer_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_clients_customer ON job_clients(customer_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_clients_job ON job_clients(job_id)"
    )
    migrate_primary_clients(conn)


def migrate_primary_clients(conn) -> int:
    """Keep existing jobs.customer_id as the primary link. Idempotent."""
    if not _table_exists(conn, "jobs"):
        return 0
    jcols = _cols(conn, "jobs")
    if "customer_id" not in jcols:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM job_clients").fetchone()[0]
    conn.execute(
        """
        INSERT OR IGNORE INTO job_clients (job_id, customer_id, role)
        SELECT id, customer_id, 'primary'
        FROM jobs
        WHERE customer_id IS NOT NULL AND TRIM(customer_id) != ''
        """
    )
    after = conn.execute("SELECT COUNT(*) FROM job_clients").fetchone()[0]
    return int(after) - int(before)


def normalize_role(role: str | None) -> str:
    raw = (role or "contact").strip().lower()
    if raw in ("client", "owner", "primary_client"):
        return "primary"
    if raw in VALID_ROLES:
        return raw
    return "contact"


def customer_ids_for_job(conn, job_id: str, job: dict | None = None) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        cid = str(raw or "").strip()
        if not cid or cid in seen:
            return
        seen.add(cid)
        ids.append(cid)

    if job and job.get("customer_id"):
        add(job.get("customer_id"))
    elif _table_exists(conn, "jobs"):
        row = conn.execute("SELECT customer_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row:
            add(row[0] if not isinstance(row, sqlite3.Row) else row["customer_id"])
    if _table_exists(conn, "job_clients"):
        for row in conn.execute(
            "SELECT customer_id FROM job_clients WHERE job_id = ?", (job_id,)
        ).fetchall():
            add(row[0] if not isinstance(row, sqlite3.Row) else row["customer_id"])
    return ids


def job_ids_for_customer(conn, customer_id: str) -> list[str]:
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    ids: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        jid = str(raw or "").strip()
        if not jid or jid in seen:
            return
        seen.add(jid)
        ids.append(jid)

    if _table_exists(conn, "jobs"):
        for row in conn.execute("SELECT id FROM jobs WHERE customer_id = ?", (cid,)).fetchall():
            add(row[0] if not isinstance(row, sqlite3.Row) else row["id"])
    if _table_exists(conn, "job_clients"):
        for row in conn.execute(
            "SELECT job_id FROM job_clients WHERE customer_id = ?", (cid,)
        ).fetchall():
            add(row[0] if not isinstance(row, sqlite3.Row) else row["job_id"])
    return ids


def shared_customer_ids(conn, customer_ids: Iterable[str]) -> set[str]:
    shared: set[str] = set()
    for cid in customer_ids:
        if len(job_ids_for_customer(conn, cid)) > 1:
            shared.add(str(cid))
    return shared


def _customer_row(conn, customer_id: str) -> dict:
    if not customer_id or not _table_exists(conn, "customers"):
        return {}
    try:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    except sqlite3.Error:
        return {}
    return dict_row(row) if row else {}


def _client_payload(conn, job_id: str, customer_id: str, role: str) -> dict:
    cust = _customer_row(conn, customer_id)
    return {
        "job_id": job_id,
        "customer_id": customer_id,
        "id": customer_id,
        "role": role,
        "name": cust.get("name"),
        "email": cust.get("email"),
        "phone": cust.get("phone"),
        "address": cust.get("address"),
        "company": cust.get("company"),
        "type": cust.get("type"),
    }


def list_clients(conn, job_id: str) -> list[dict]:
    ensure_job_clients_schema(conn)
    rows = conn.execute(
        "SELECT job_id, customer_id, role FROM job_clients WHERE job_id = ? ORDER BY CASE role WHEN 'primary' THEN 0 WHEN 'designer' THEN 1 ELSE 2 END, created_at",
        (job_id,),
    ).fetchall()
    out = [
        _client_payload(
            conn,
            str(r[0] if not isinstance(r, sqlite3.Row) else r["job_id"]),
            str(r[1] if not isinstance(r, sqlite3.Row) else r["customer_id"]),
            str(r[2] if not isinstance(r, sqlite3.Row) else r["role"]),
        )
        for r in rows
    ]
    if out:
        return out
    # Fallback before/without a backfill: synthesize from jobs.customer_id
    if _table_exists(conn, "jobs"):
        row = conn.execute(
            "SELECT customer_id FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        cid = None
        if row:
            cid = row[0] if not isinstance(row, sqlite3.Row) else row["customer_id"]
        if cid:
            return [_client_payload(conn, job_id, str(cid), "primary")]
    return []


def clients_by_job_ids(conn, job_ids: Iterable[str]) -> dict[str, list[dict]]:
    ensure_job_clients_schema(conn)
    ids = [str(j) for j in job_ids if j]
    out: dict[str, list[dict]] = {jid: [] for jid in ids}
    if not ids:
        return out
    ph = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT job_id, customer_id, role FROM job_clients WHERE job_id IN ({ph})",
        ids,
    ).fetchall()
    for r in rows:
        job_id = str(r[0] if not isinstance(r, sqlite3.Row) else r["job_id"])
        customer_id = str(r[1] if not isinstance(r, sqlite3.Row) else r["customer_id"])
        role = str(r[2] if not isinstance(r, sqlite3.Row) else r["role"])
        out.setdefault(job_id, []).append(_client_payload(conn, job_id, customer_id, role))
    missing = [jid for jid, clients in out.items() if not clients]
    if missing and _table_exists(conn, "jobs"):
        mph = ",".join("?" * len(missing))
        for r in conn.execute(
            f"SELECT id, customer_id FROM jobs WHERE id IN ({mph})", missing
        ).fetchall():
            job_id = str(r[0] if not isinstance(r, sqlite3.Row) else r["id"])
            cid = r[1] if not isinstance(r, sqlite3.Row) else r["customer_id"]
            if cid:
                out[job_id] = [_client_payload(conn, job_id, str(cid), "primary")]
    return out


def attach_clients(conn, jobs: list[dict]) -> list[dict]:
    if not jobs:
        return jobs
    by_job = clients_by_job_ids(conn, [j.get("id") for j in jobs if j.get("id")])
    for job in jobs:
        job["clients"] = by_job.get(str(job.get("id") or ""), [])
    return jobs


def link_primary_client(conn, job_id: str, customer_id: str) -> dict:
    """Set / keep jobs.customer_id as the primary job_clients row."""
    return add_client(conn, job_id, customer_id, role="primary")


def add_client(conn, job_id: str, customer_id: str, role: str | None = "contact") -> dict:
    ensure_job_clients_schema(conn)
    cid = str(customer_id or "").strip()
    if not cid:
        raise ValueError("customer_id is required")
    if not _table_exists(conn, "jobs"):
        raise ValueError("jobs table missing")
    job = conn.execute("SELECT id, customer_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        raise KeyError("job not found")
    if _table_exists(conn, "customers"):
        exists = conn.execute("SELECT id FROM customers WHERE id = ?", (cid,)).fetchone()
        if not exists:
            raise KeyError("customer not found")
    role_n = normalize_role(role)
    if role_n == "primary":
        conn.execute(
            "UPDATE job_clients SET role = 'contact' WHERE job_id = ? AND role = 'primary' AND customer_id != ?",
            (job_id, cid),
        )
        conn.execute("UPDATE jobs SET customer_id = ?, updated_at = datetime('now') WHERE id = ?", (cid, job_id))
    conn.execute(
        """
        INSERT INTO job_clients (job_id, customer_id, role)
        VALUES (?, ?, ?)
        ON CONFLICT(job_id, customer_id) DO UPDATE SET role = excluded.role
        """,
        (job_id, cid, role_n),
    )
    return _client_payload(conn, job_id, cid, role_n)


def remove_client(conn, job_id: str, customer_id: str) -> dict:
    ensure_job_clients_schema(conn)
    cid = str(customer_id or "").strip()
    existing = conn.execute(
        "SELECT role FROM job_clients WHERE job_id = ? AND customer_id = ?",
        (job_id, cid),
    ).fetchone()
    if not existing:
        raise KeyError("client not on job")
    role = existing[0] if not isinstance(existing, sqlite3.Row) else existing["role"]
    remaining = conn.execute(
        "SELECT COUNT(*) FROM job_clients WHERE job_id = ?", (job_id,)
    ).fetchone()[0]
    if remaining <= 1:
        raise ValueError("cannot remove the last client from a job")
    conn.execute(
        "DELETE FROM job_clients WHERE job_id = ? AND customer_id = ?",
        (job_id, cid),
    )
    if role == "primary":
        nxt = conn.execute(
            "SELECT customer_id FROM job_clients WHERE job_id = ? ORDER BY created_at LIMIT 1",
            (job_id,),
        ).fetchone()
        if nxt:
            new_primary = nxt[0] if not isinstance(nxt, sqlite3.Row) else nxt["customer_id"]
            conn.execute(
                "UPDATE job_clients SET role = 'primary' WHERE job_id = ? AND customer_id = ?",
                (job_id, new_primary),
            )
            conn.execute(
                "UPDATE jobs SET customer_id = ?, updated_at = datetime('now') WHERE id = ?",
                (new_primary, job_id),
            )
    return {"removed": cid, "job_id": job_id}
