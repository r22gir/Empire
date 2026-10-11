"""Max home center: the user's own Research interests and Growth lists.

Stored per user in the edition's own SQLite DB (``EMPIRE_TASK_DB``), so each
family edition keeps its own lists. Nothing here reads business data and
nothing is sent anywhere. Lists start empty; the studio offers neutral
suggestions the user can add with one tap.

    GET  /api/v1/home-center/state?user=owner
    PUT  /api/v1/home-center/state/{kind}?user=owner   {"items": [...]}

kind: interests | goals | learning | projects
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/home-center", tags=["home-center"])

KINDS = ("interests", "goals", "learning", "projects")
MAX_ITEMS = 40
_USER_RE = re.compile(r"^[a-z0-9_-]{1,40}$")
# fields kept per item; anything else is dropped
_TEXT_FIELDS = {"id": 40, "name": 80, "icon": 24, "note": 240, "unit": 24, "query": 160, "due": 24}
_NUM_FIELDS = ("progress", "done", "total")


class ItemsBody(BaseModel):
    items: list[dict]


def _user(user: str) -> str:
    u = (user or "owner").strip().lower()
    if not _USER_RE.match(u):
        raise HTTPException(400, "user must be 1-40 chars of a-z, 0-9, _ or -")
    return u


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS home_center_state (
            user_key TEXT NOT NULL,
            kind TEXT NOT NULL,
            items_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_key, kind)
        )
        """
    )


def clean_items(items: list) -> list[dict]:
    """Keep only known fields, trim text, clamp numbers. Drops items without a name."""
    out: list[dict] = []
    for raw in (items or [])[:MAX_ITEMS]:
        if not isinstance(raw, dict):
            continue
        item: dict = {}
        for key, limit in _TEXT_FIELDS.items():
            val = raw.get(key)
            if val is None:
                continue
            text = str(val).strip()[:limit]
            if text:
                item[key] = text
        for key in _NUM_FIELDS:
            val = raw.get(key)
            if val is None or val == "":
                continue
            try:
                num = float(val)
            except (TypeError, ValueError):
                continue
            if num != num:  # NaN
                continue
            item[key] = max(0.0, min(num, 100.0 if key == "progress" else 1_000_000.0))
        if not item.get("name"):
            continue
        item.setdefault("id", re.sub(r"[^a-z0-9]+", "-", item["name"].lower()).strip("-")[:40] or "item")
        out.append(item)
    return out


@router.get("/state")
async def get_state(user: str = Query("owner")):
    from app.db.database import get_db

    key = _user(user)
    state = {kind: [] for kind in KINDS}
    updated: dict[str, str] = {}
    with get_db() as conn:
        # Read-only: the table is created by the first PUT, so opening the home never writes.
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'home_center_state'"
        ).fetchone()
        rows = conn.execute(
            "SELECT kind, items_json, updated_at FROM home_center_state WHERE user_key = ?", (key,)
        ).fetchall() if exists else []
    for row in rows:
        if row["kind"] in state:
            try:
                state[row["kind"]] = clean_items(json.loads(row["items_json"] or "[]"))
            except ValueError:
                state[row["kind"]] = []
            updated[row["kind"]] = row["updated_at"]
    return {"user": key, **state, "updated_at": updated}


@router.put("/state/{kind}")
async def put_state(kind: str, body: ItemsBody, user: str = Query("owner")):
    from app.db.database import get_db

    if kind not in KINDS:
        raise HTTPException(404, f"unknown list '{kind}'. Use one of: {', '.join(KINDS)}")
    key = _user(user)
    items = clean_items(body.items)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO home_center_state (user_key, kind, items_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_key, kind) DO UPDATE SET items_json = excluded.items_json, updated_at = excluded.updated_at
            """,
            (key, kind, json.dumps(items), now),
        )
    return {"user": key, "kind": kind, "items": items, "updated_at": now}
