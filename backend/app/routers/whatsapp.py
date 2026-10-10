"""WhatsApp Business Cloud API webhook plus founder chat-log reads.

The webhook stays public (Meta signature). Conversation reads require
the founder PIN. This module does not delete messages and does not send
from the chats viewer.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from app.services.accounts.founder import FounderAuthError, assert_founder
from app.services.max.whatsapp_channel import (
    WhatsAppSendBlocked,
    channel_status,
    process_webhook,
    reply_in_window,
    send_template,
    subscription_challenge,
)

router = APIRouter()


class OutboundIn(BaseModel):
    to: str
    text: str = ""
    template_name: str = ""
    language: str = "en"
    confirmed: bool = False


def _require_founder(pin: str | None) -> None:
    try:
        assert_founder(pin)
    except FounderAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/whatsapp/status")
async def whatsapp_status():
    return channel_status()


@router.get("/whatsapp/chats")
async def whatsapp_list_chats(
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    """List conversations for this edition. Founder PIN required."""
    _require_founder(x_founder_pin)
    from app.services.max.whatsapp_log import list_conversations

    return {"conversations": list_conversations()}


@router.get("/whatsapp/chats/search")
async def whatsapp_search_chats(
    q: str = Query("", min_length=0),
    limit: int = Query(50, ge=1, le=200),
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    """Simple text search across this edition's WhatsApp log."""
    _require_founder(x_founder_pin)
    from app.services.max.whatsapp_log import search_all_messages

    return {"query": q, "messages": search_all_messages(q, limit=limit)}


@router.get("/whatsapp/chats/{wa_id}/messages")
async def whatsapp_conversation_messages(
    wa_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str = Query("", min_length=0),
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    """Page one conversation. Read-only."""
    _require_founder(x_founder_pin)
    from app.services.max.whatsapp_log import get_conversation_messages, get_display_label

    messages, total = get_conversation_messages(
        wa_id,
        limit=limit,
        offset=offset,
        search=q or None,
    )
    return {
        "wa_id": wa_id,
        "display_label": get_display_label(wa_id),
        "messages": messages,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/whatsapp/webhook")
async def whatsapp_verify(request: Request):
    status = channel_status()
    if not status["enabled"]:
        return JSONResponse(status, status_code=503)
    challenge = subscription_challenge(
        request.query_params.get("hub.mode"),
        request.query_params.get("hub.verify_token"),
        request.query_params.get("hub.challenge"),
    )
    if challenge is None:
        return JSONResponse({"ok": False, "reason": "verify token rejected"}, status_code=403)
    return PlainTextResponse(challenge)


@router.post("/whatsapp/webhook")
async def whatsapp_inbound(request: Request):
    raw = await request.body()
    result = await process_webhook(raw, request.headers.get("x-hub-signature-256"))
    code = int(result.get("http_status") or 200)
    return JSONResponse(result, status_code=code)


@router.post("/whatsapp/send")
async def whatsapp_send(body: OutboundIn):
    """Explicit confirm path. Inbound webhooks never call this."""
    if body.confirmed is not True:
        raise HTTPException(status_code=403, detail="drafts are not sent without explicit confirmation")
    try:
        if body.template_name.strip():
            return await send_template(
                body.to,
                body.template_name,
                confirmed=True,
                language=body.language or "en",
            )
        if not body.text.strip():
            raise HTTPException(status_code=400, detail="text or an approved template name is required")
        return await reply_in_window(body.to, body.text)
    except WhatsAppSendBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
