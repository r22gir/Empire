"""WhatsApp Cloud API webhook and edition credential management."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.services.whatsapp_cloud import (
    channel_status,
    get_credentials_safe,
    handle_webhook,
    save_stored_credentials,
    test_connection,
    verify_handshake,
    webhook_callback_url,
)

router = APIRouter(tags=["whatsapp"])


class WhatsAppCredentialsBody(BaseModel):
    phone_number_id: str = Field(default="", description="Meta Phone Number ID")
    access_token: str = Field(default="", description="Meta System User / User Access Token")
    app_secret: str = Field(default="", description="Meta App Secret")
    verify_token: Optional[str] = Field(default="", description="Optional custom verify token")
    owner_numbers: Optional[list[str]] = Field(default=None, description="Allowlisted owner phone numbers")


class WhatsAppTestBody(BaseModel):
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None


@router.get("/whatsapp/status")
def whatsapp_status():
    return channel_status()


@router.get("/whatsapp/credentials")
def whatsapp_get_credentials():
    """Returns safe masked WhatsApp configuration status and webhook connection info.
    Secrets (token, app secret) are never returned.
    """
    return get_credentials_safe()


@router.post("/whatsapp/credentials")
def whatsapp_save_credentials(body: WhatsAppCredentialsBody):
    """Store WhatsApp credentials securely in this edition's private storage (mode 0600).
    Never echoes raw secrets back.
    """
    safe_result = save_stored_credentials(
        phone_number_id=body.phone_number_id,
        access_token=body.access_token,
        app_secret=body.app_secret,
        verify_token=body.verify_token or "",
        owner_numbers=body.owner_numbers,
    )
    return {"ok": True, "credentials": safe_result}


@router.post("/whatsapp/test")
def whatsapp_test_connection(body: Optional[WhatsAppTestBody] = None):
    """Calls Meta Graph API in read-only mode to verify credentials and phone number.
    Does NOT send any WhatsApp messages.
    """
    pid = body.phone_number_id if body else ""
    tok = body.access_token if body else ""
    result = test_connection(phone_number_id=pid or "", access_token=tok or "")
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return result


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

