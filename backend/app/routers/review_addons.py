"""Owner-only review notes for the EmpireBox add-on directory."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.database import dict_rows, get_db
from app.routers.auth import _get_current_user, security

router = APIRouter(prefix="/review", tags=["addon-review"])

SEED_TEXT = "Theme isn't consistent across pages and modules; some pages look archaic. Need a unified visual redesign."
SEED_TAG = "visual/theme"


class AppliesTo(BaseModel):
    all: bool = False
    modules: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class ReviewCommentIn(BaseModel):
    module_id: str = Field(default="", max_length=120)
    category: str = Field(default="", max_length=120)
    scope: str = Field(default="module", max_length=24)
    tags: list[str] = Field(default_factory=list, max_length=8)
    applies_to: AppliesTo = Field(default_factory=AppliesTo)
    text: str = Field(min_length=1, max_length=5000)
    status: str = Field(default="open", max_length=12)


class ReviewCommentPatch(BaseModel):
    status: Optional[str] = None
    tags: Optional[list[str]] = Field(default=None, max_length=8)
    text: Optional[str] = Field(default=None, min_length=1, max_length=5000)


def _owner(request: Request, credentials = Depends(security)) -> dict:
    """Accept the normal Bearer owner token or the private Studio Access session.

    Studio is protected by Cloudflare Access before it reaches this service. When
    that session is present, cloudflared supplies both the authenticated email
    and Access JWT assertion headers. Never trust the public API hostname for
    this fallback; the Studio Access policy is the owner gate.
    """
    if credentials:
        user = _get_current_user(credentials)
    else:
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",", 1)[0].split(":", 1)[0].strip().lower()
        email = request.headers.get("cf-access-authenticated-user-email", "").strip().lower()
        access_assertion = request.headers.get("cf-access-jwt-assertion", "").strip()
        if host != "studio.empirebox.store" or not email or not access_assertion:
            raise HTTPException(status_code=401, detail="Owner session required")
        # The Studio Access policy is the owner gate. The local founder row
        # predates email-based Access identities and may not have an email, so
        # do not require a second app-account lookup here.
        user = {"role": "founder", "email": email}
    role = str(user.get("role") or "").strip().lower()
    if role not in {"founder", "owner"}:
        raise HTTPException(status_code=403, detail="Owner access required")
    return user


def _ensure_schema(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS review_comments (
            id TEXT PRIMARY KEY,
            module_id TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            scope TEXT NOT NULL DEFAULT 'module',
            tags TEXT NOT NULL DEFAULT '[]',
            applies_to TEXT NOT NULL DEFAULT '{}',
            text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL
        )
        """
    )
    # Seed exactly once, without exposing any private data.
    row = conn.execute(
        "SELECT id FROM review_comments WHERE scope = 'general' AND text = ? LIMIT 1",
        (SEED_TEXT,),
    ).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO review_comments
              (id, module_id, category, scope, tags, applies_to, text, status, created_at)
            VALUES (?, '', '', 'general', ?, ?, ?, 'open', ?)
            """,
            (
                f"seed-{uuid.uuid4().hex}",
                json.dumps([SEED_TAG]),
                json.dumps({"all": True, "modules": [], "categories": []}),
                SEED_TEXT,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def _row(row) -> dict[str, Any]:
    item = dict(row)
    for key, fallback in (("tags", []), ("applies_to", {})):
        try:
            item[key] = json.loads(item.get(key) or ("[]" if key == "tags" else "{}"))
        except (TypeError, ValueError):
            item[key] = fallback
    return item


@router.get("/addons")
def list_addon_review_comments(_user: dict = Depends(_owner)):
    with get_db() as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, module_id, category, scope, tags, applies_to, text, status, created_at "
            "FROM review_comments ORDER BY created_at ASC, id ASC"
        ).fetchall()
    return {"comments": [_row(row) for row in rows]}


@router.post("/addons", status_code=201)
def create_addon_review_comment(payload: ReviewCommentIn, _user: dict = Depends(_owner)):
    scope = payload.scope.strip().lower()
    if scope not in {"module", "category", "general"}:
        raise HTTPException(status_code=422, detail="scope must be module, category, or general")
    status = payload.status.strip().lower()
    if status not in {"open", "done"}:
        raise HTTPException(status_code=422, detail="status must be open or done")
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required")
    comment_id = uuid.uuid4().hex
    tags = sorted({tag.strip()[:60] for tag in payload.tags if tag.strip()})
    applies_to = payload.applies_to.model_dump()
    with get_db() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO review_comments
              (id, module_id, category, scope, tags, applies_to, text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comment_id,
                payload.module_id.strip(),
                payload.category.strip(),
                scope,
                json.dumps(tags, ensure_ascii=False),
                json.dumps(applies_to, ensure_ascii=False),
                text,
                status,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        row = conn.execute(
            "SELECT id, module_id, category, scope, tags, applies_to, text, status, created_at "
            "FROM review_comments WHERE id = ?",
            (comment_id,),
        ).fetchone()
    return {"comment": _row(row)}


@router.patch("/addons/{comment_id}")
def update_addon_review_comment(comment_id: str, payload: ReviewCommentPatch, _user: dict = Depends(_owner)):
    updates = []
    values: list[Any] = []
    if payload.status is not None:
        status = payload.status.strip().lower()
        if status not in {"open", "done"}:
            raise HTTPException(status_code=422, detail="status must be open or done")
        updates.append("status = ?")
        values.append(status)
    if payload.tags is not None:
        tags = sorted({tag.strip()[:60] for tag in payload.tags if tag.strip()})
        updates.append("tags = ?")
        values.append(json.dumps(tags, ensure_ascii=False))
    if payload.text is not None:
        text = payload.text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="text is required")
        updates.append("text = ?")
        values.append(text)
    if not updates:
        raise HTTPException(status_code=422, detail="at least one field is required")
    values.append(comment_id)
    with get_db() as conn:
        _ensure_schema(conn)
        cur = conn.execute(f"UPDATE review_comments SET {', '.join(updates)} WHERE id = ?", values)
        if cur.rowcount != 1:
            raise HTTPException(status_code=404, detail="Review comment not found")
        row = conn.execute(
            "SELECT id, module_id, category, scope, tags, applies_to, text, status, created_at "
            "FROM review_comments WHERE id = ?", (comment_id,)
        ).fetchone()
    return {"comment": _row(row)}


@router.delete("/addons/{comment_id}")
def delete_addon_review_comment(comment_id: str, _user: dict = Depends(_owner)):
    with get_db() as conn:
        _ensure_schema(conn)
        cur = conn.execute("DELETE FROM review_comments WHERE id = ?", (comment_id,))
        if cur.rowcount != 1:
            raise HTTPException(status_code=404, detail="Review comment not found")
    return {"deleted": comment_id}
