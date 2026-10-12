"""Simli session tokens. The API key never leaves this process."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.max.simli_avatar import (
    create_session,
    record_usage,
    running_avatar_edition,
    simli_status,
    usage_card,
)

router = APIRouter()


def _require_avatar_access(request: Request) -> None:
    from app.services.max.voice_live import authorize_websocket

    ok, via, _user = authorize_websocket(request, surface="http")
    if not ok:
        raise HTTPException(status_code=401, detail="unauthorized")


def _bound_edition() -> str:
    """Running checkout only. Client ?edition= / body.edition is not trusted."""
    return running_avatar_edition()


class SessionIn(BaseModel):
    # Accepted for older clients; ignored. Face/minutes follow the process edition.
    edition: str = "workroom"


class UsageIn(BaseModel):
    edition: str = "workroom"
    seconds: float = 0
    source: str = "simli"


@router.get("/avatar/simli/status")
async def simli_avatar_status(request: Request, edition: str = Query("workroom")):
    del edition  # untrusted; face is the running checkout
    _require_avatar_access(request)
    return simli_status(_bound_edition())


@router.post("/avatar/simli/session")
async def simli_avatar_session(body: SessionIn, request: Request):
    _require_avatar_access(request)
    return await create_session(_bound_edition())


@router.get("/avatar/simli/usage")
async def simli_avatar_usage(request: Request, edition: str = Query("")):
    del edition  # untrusted; minutes are the running checkout
    _require_avatar_access(request)
    return usage_card(_bound_edition())


@router.post("/avatar/simli/usage")
async def simli_avatar_usage_log(body: UsageIn, request: Request):
    _require_avatar_access(request)
    return record_usage(_bound_edition(), body.seconds, body.source)
