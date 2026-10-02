"""WhatsApp Business Cloud API webhook. Disabled unless the four env vars are set."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

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


@router.get("/whatsapp/status")
async def whatsapp_status():
    return channel_status()


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
