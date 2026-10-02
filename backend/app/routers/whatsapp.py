"""WhatsApp Cloud API webhook. Disabled until this instance's env is set."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.services.whatsapp_cloud import channel_status, handle_webhook, verify_handshake

router = APIRouter(tags=["whatsapp"])


@router.get("/whatsapp/status")
def whatsapp_status():
    return channel_status()


@router.get("/whatsapp/webhook")
def whatsapp_verify(request: Request):
    challenge = verify_handshake(
        request.query_params.get("hub.mode") or "",
        request.query_params.get("hub.verify_token") or "",
        request.query_params.get("hub.challenge") or "",
    )
    if challenge is None:
        return JSONResponse({"ok": False, "status": channel_status()["status"]}, status_code=403)
    return Response(content=challenge, media_type="text/plain")


@router.post("/whatsapp/webhook")
async def whatsapp_inbound(request: Request):
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256") or ""
    result = handle_webhook(body, signature)
    status = int(result.get("http_status") or 200)
    return JSONResponse(result, status_code=status)
