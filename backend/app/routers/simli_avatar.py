"""Simli session tokens. The API key never leaves this process."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.max.simli_avatar import create_session, record_usage, simli_status, usage_card

router = APIRouter()


def _require_avatar_access(request: Request) -> None:
    """Same Tailscale / AMP / Access gate as /avatar/live and presentation HTTP."""
    from app.services.max.voice_live import authorize_websocket

    ok, via, _user = authorize_websocket(request, surface="http")
    if not ok:
        raise HTTPException(status_code=401, detail="unauthorized")


class SessionIn(BaseModel):
    edition: str = "workroom"


class UsageIn(BaseModel):
    edition: str = "workroom"
    seconds: float = 0
    source: str = "simli"


@router.get("/avatar/simli/status")
async def simli_avatar_status(request: Request, edition: str = Query("workroom")):
    _require_avatar_access(request)
    return simli_status(edition)


@router.post("/avatar/simli/session")
async def simli_avatar_session(request: Request, body: SessionIn):
    _require_avatar_access(request)
    return await create_session(body.edition)


@router.get("/avatar/simli/usage")
async def simli_avatar_usage(request: Request, edition: str = Query("")):
    _require_avatar_access(request)
    return usage_card(edition or None)


@router.post("/avatar/simli/usage")
async def simli_avatar_usage_log(request: Request, body: UsageIn):
    _require_avatar_access(request)
    return record_usage(body.edition, body.seconds, body.source)
