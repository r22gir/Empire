"""Safe MAX channel verification endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.channels import build_channel_status, build_dry_run_result

router = APIRouter(prefix="/channels", tags=["channels"])


class ChannelDryRunRequest(BaseModel):
    channel: str = Field(..., description="email, telegram, web_chat, or hermes")
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
async def get_channel_status() -> dict[str, Any]:
    """Return layered, non-secret channel readiness for MAX communication surfaces."""
    return build_channel_status()


@router.post("/test/dry-run")
async def channel_dry_run(request: ChannelDryRunRequest) -> dict[str, Any]:
    """Build channel test payloads without sending live email, Telegram, or model calls."""
    return build_dry_run_result(request.channel, request.payload)
