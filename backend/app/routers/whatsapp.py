"""WhatsApp Cloud API webhook plus a read-only chat log.

Draft-only. This router never sends to clients. Secrets stay in the
instance env file — they are never accepted on these routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.services.whatsapp_cloud import channel_status, handle_webhook, verify_handshake

router = APIRouter(tags=["whatsapp"])


@router.get("/whatsapp/status")
def whatsapp_status():
    return channel_status()


@router.get("/whatsapp/setup")
def whatsapp_setup_meta():
    """Public metadata for the in-site Spanish guide. No secrets."""
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
    }


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
def whatsapp_list_chats():
    """Read-only conversation list for this edition."""
    from app.services.whatsapp_store import list_conversations

    return {"conversations": list_conversations(), "readonly": True, "draft_only": True}


@router.get("/whatsapp/chats/search")
def whatsapp_search_chats(q: str = ""):
    from app.services.whatsapp_store import search_messages

    return {"matches": search_messages(q), "readonly": True}


@router.get("/whatsapp/chats/{wa_id}/messages")
def whatsapp_conversation_messages(wa_id: str, limit: int = 100, before: int | None = None):
    from app.services.whatsapp_store import list_messages

    return {
        "wa_id": wa_id,
        "messages": list_messages(wa_id, limit=limit, before=before),
        "readonly": True,
    }
