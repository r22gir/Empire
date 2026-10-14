"""Persist viewer publish records. Isolated temp DBs in tests; never live writes."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_viewers (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    quote_id TEXT,
    slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft',
    title TEXT,
    public_url TEXT,
    html_sha TEXT,
    published_at TEXT,
    unpublished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_job_viewers_job ON job_viewers(job_id);
CREATE INDEX IF NOT EXISTS idx_job_viewers_quote ON job_viewers(quote_id);
"""


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id() -> str:
    return secrets.token_hex(8)


def new_slug() -> str:
    """Unguessable public folder name (like the Marley b7k2q page)."""
    alphabet = "abcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def get_record(conn, *, job_id: Optional[str] = None, quote_id: Optional[str] = None,
               slug: Optional[str] = None) -> Optional[dict]:
    ensure_schema(conn)
    if slug:
        row = conn.execute("SELECT * FROM job_viewers WHERE slug = ?", (slug,)).fetchone()
    elif job_id:
        row = conn.execute(
            "SELECT * FROM job_viewers WHERE job_id = ? ORDER BY updated_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    elif quote_id:
        row = conn.execute(
            "SELECT * FROM job_viewers WHERE quote_id = ? ORDER BY updated_at DESC LIMIT 1",
            (quote_id,),
        ).fetchone()
    else:
        return None
    if not row:
        return None
    return dict(row) if not isinstance(row, dict) else row


def upsert_record(conn, *, job_id=None, quote_id=None, slug=None, status="draft",
                  title=None, public_url=None, html_sha=None) -> dict:
    ensure_schema(conn)
    existing = get_record(conn, job_id=job_id, quote_id=quote_id)
    now = _now()
    if existing:
        slug = existing["slug"]
        conn.execute(
            """UPDATE job_viewers SET status=?, title=?, public_url=?, html_sha=?,
               published_at=CASE WHEN ?='published' THEN ? ELSE published_at END,
               unpublished_at=CASE WHEN ?='unpublished' THEN ? ELSE unpublished_at END,
               updated_at=?
               WHERE id=?""",
            (status, title or existing.get("title"), public_url, html_sha,
             status, now, status, now, now, existing["id"]),
        )
        return get_record(conn, slug=slug)
    slug = slug or new_slug()
    rec_id = _new_id()
    conn.execute(
        """INSERT INTO job_viewers
           (id, job_id, quote_id, slug, status, title, public_url, html_sha,
            published_at, unpublished_at, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)""",
        (rec_id, job_id, quote_id, slug, status, title, public_url, html_sha,
         now if status == "published" else None, now, now),
    )
    return get_record(conn, slug=slug)


def record_to_status(rec: Optional[dict]) -> dict:
    if not rec:
        return {
            "published": False,
            "status": "none",
            "slug": None,
            "url": None,
            "published_at": None,
        }
    return {
        "published": rec.get("status") == "published",
        "status": rec.get("status") or "draft",
        "slug": rec.get("slug"),
        "url": rec.get("public_url") if rec.get("status") == "published" else None,
        "published_at": rec.get("published_at"),
        "title": rec.get("title"),
    }
