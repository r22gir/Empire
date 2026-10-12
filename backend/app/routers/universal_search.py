"""GET /api/v1/universal-search — edition-isolated Command Center search."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.search.edition import process_edition
from app.services.search.universal import enqueue_draft_reply, run_universal_search

router = APIRouter()


@router.get("/universal-search")
def universal_search(
    q: str = Query("", max_length=200),
    query: str = Query("", max_length=200),
):
    text = (q or query or "").strip()
    return run_universal_search(text)


class DraftReplyBody(BaseModel):
    mail_id: str = Field(..., min_length=1, max_length=200)
    source: str = "gmail"
    body: str = ""
    subject: str = ""
    to_address: str = ""
    to_name: str = ""
    confirm: Optional[bool] = None  # accepted and ignored — never sends


@router.post("/universal-search/draft-reply")
def draft_reply(payload: DraftReplyBody):
    """Enqueue a draft reply. Never sends, even when confirm=true."""
    result = enqueue_draft_reply(
        mail_id=payload.mail_id,
        source=payload.source,
        body=payload.body,
        subject=payload.subject,
        to_address=payload.to_address,
        to_name=payload.to_name,
    )
    result["sent"] = False
    result["edition"] = process_edition()
    return result
