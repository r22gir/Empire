"""WhatsApp Cloud API webhook, owner credential setup, and read-only chat log.

Draft-only toward clients. Secrets are stored under EMPIRE_DATA_DIR and
never echoed. Family editions refuse without EMPIRE_DATA_DIR.

Family admin and chat-log routes require an authenticated owner session
(middleware 403 plus this dependency). The Meta webhook stays exempt.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.edition import is_family_edition, sin_acceso_body
from app.services.whatsapp_cloud import (
    channel_status,
    get_credentials_safe,
    handle_webhook,
    save_stored_credentials,
    test_connection,
    verify_handshake,
)

router = APIRouter(tags=["whatsapp"])


class WhatsAppCredentialsBody(BaseModel):
    phone_number_id: str = Field(default="")
    access_token: str = Field(default="")
    app_secret: str = Field(default="")
    verify_token: Optional[str] = Field(default="")
    owner_numbers: Optional[list[str]] = None


class WhatsAppTestBody(BaseModel):
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None


def require_family_whatsapp_login(request: Request) -> None:
    """401/403 when a family edition has no owner/admin session.

    Webhook routes must not use this. Workroom is unchanged.
    """
    if not is_family_edition():
        return
    email = getattr(request.state, "amp_email", None)
    if not email:
        raise HTTPException(status_code=401, detail=sin_acceso_body()["detail"])
    from app.services import amp_allowlist

    role = amp_allowlist.entry_role(email=email, username=None)
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Sin acceso. Se requiere una cuenta administrador.")


def _require_admin(request: Request) -> None:
    """Same owner/admin gate as edition.py."""
    require_family_whatsapp_login(request)
    from app.services import amp_allowlist

    email = getattr(request.state, "amp_email", None)
    role = amp_allowlist.entry_role(email=email, username=None)
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Sin acceso. Se requiere una cuenta administrador.")


@router.get("/whatsapp/status")
def whatsapp_status(_auth: None = Depends(require_family_whatsapp_login)):
    return channel_status()


@router.get("/whatsapp/setup")
def whatsapp_setup_meta(_auth: None = Depends(require_family_whatsapp_login)):
    """Owner-session metadata for the in-site Spanish guide. No secrets."""
    status = channel_status()
    return {
        "edition": status.get("edition"),
        "webhook_url": status.get("webhook_url"),
        "webhook_path": status.get("webhook_path"),
        "setup_path": status.get("setup_path"),
        "chats_path": status.get("chats_path"),
        "secret_file": status.get("secret_file"),
        "documents_auto_send": False,
        "draft_only": True,
        "client_sends": False,
        "usage_cap_pct": status.get("usage_cap_pct"),
        "owner_last4": status.get("owner_last4") or [],
        "status": status.get("status"),
        "secrets_in_page": False,
        "secrets_in_chat": False,
    }


@router.get("/whatsapp/credentials")
def whatsapp_get_credentials(request: Request):
    _require_admin(request)
    return get_credentials_safe()


@router.post("/whatsapp/credentials")
def whatsapp_save_credentials(body: WhatsAppCredentialsBody, request: Request):
    _require_admin(request)
    try:
        safe = save_stored_credentials(
            phone_number_id=body.phone_number_id,
            access_token=body.access_token,
            app_secret=body.app_secret,
            verify_token=body.verify_token or "",
            owner_numbers=body.owner_numbers,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "credentials": safe}


@router.post("/whatsapp/test")
def whatsapp_test_connection(request: Request, body: Optional[WhatsAppTestBody] = None):
    """Read-only Graph check. Does not send WhatsApp messages."""
    _require_admin(request)
    pid = body.phone_number_id if body else ""
    tok = body.access_token if body else ""
    result = test_connection(phone_number_id=pid or "", access_token=tok or "")
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    dumped = json_safe(result)
    return dumped


def json_safe(result: dict) -> dict:
    """Drop raw tokens if a caller stuffed them into the result."""
    banned = ("access_token", "app_secret", "token")
    return {k: v for k, v in result.items() if k not in banned}


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


@router.get("/whatsapp/chats")
def whatsapp_list_chats(_auth: None = Depends(require_family_whatsapp_login)):
    """Read-only conversation list for this edition."""
    from app.services.whatsapp_store import list_conversations

    return {"conversations": list_conversations(), "readonly": True, "draft_only": True}


@router.get("/whatsapp/chats/search")
def whatsapp_search_chats(q: str = "", _auth: None = Depends(require_family_whatsapp_login)):
    from app.services.whatsapp_store import search_messages

    return {"matches": search_messages(q), "readonly": True}


@router.get("/whatsapp/chats/{wa_id}/messages")
def whatsapp_conversation_messages(
    wa_id: str,
    limit: int = 100,
    before: int | None = None,
    _auth: None = Depends(require_family_whatsapp_login),
):
    from app.services.whatsapp_store import list_messages

    return {
        "wa_id": wa_id,
        "messages": list_messages(wa_id, limit=limit, before=before),
        "readonly": True,
    }
