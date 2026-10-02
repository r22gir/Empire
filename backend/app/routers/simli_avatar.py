"""Simli session tokens. The API key never leaves this process."""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.max.simli_avatar import create_session, record_usage, simli_status, usage_card

router = APIRouter()


class SessionIn(BaseModel):
    edition: str = "workroom"


class UsageIn(BaseModel):
    edition: str = "workroom"
    seconds: float = 0
    source: str = "simli"


@router.get("/avatar/simli/status")
async def simli_avatar_status(edition: str = Query("workroom")):
    return simli_status(edition)


@router.post("/avatar/simli/session")
async def simli_avatar_session(body: SessionIn):
    return await create_session(body.edition)


@router.get("/avatar/simli/usage")
async def simli_avatar_usage(edition: str = Query("")):
    return usage_card(edition or None)


@router.post("/avatar/simli/usage")
async def simli_avatar_usage_log(body: UsageIn):
    return record_usage(body.edition, body.seconds, body.source)
