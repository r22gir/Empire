"""WhatsApp Business Cloud API webhook plus founder chat-log reads.

The webhook stays public (Meta signature). Conversation reads require
the founder PIN. This module does not delete messages and does not send
from the chats viewer.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
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


class RefileIn(BaseModel):
    job_slug: str


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
    from app.services.max.whatsapp_log import get_active_job

    return {
        "wa_id": wa_id,
        "display_label": get_display_label(wa_id),
        "messages": messages,
        "total": total,
        "limit": limit,
        "offset": offset,
        "active_job": get_active_job(wa_id),
    }


@router.get("/whatsapp/jobs")
async def whatsapp_list_jobs(
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _require_founder(x_founder_pin)
    from app.services.max.doc_lookup import list_job_folders

    return {"jobs": list_job_folders()}


@router.get("/whatsapp/media/{attachment_id}")
async def whatsapp_media(
    attachment_id: int,
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _require_founder(x_founder_pin)
    from app.services.max.whatsapp_log import attachment_file_path, get_attachment

    att = get_attachment(attachment_id)
    path = attachment_file_path(attachment_id)
    if not att or path is None:
        raise HTTPException(status_code=404, detail="attachment not found")
    return FileResponse(
        path,
        media_type=att.get("mime_type") or "application/octet-stream",
        filename=att.get("filename") or path.name,
    )


@router.post("/whatsapp/attachments/{attachment_id}/refile")
async def whatsapp_refile(
    attachment_id: int,
    body: RefileIn,
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    """Only write on the chats page: move an attachment into a job folder."""
    _require_founder(x_founder_pin)
    from app.services.max.whatsapp_log import refile_attachment

    try:
        return refile_attachment(attachment_id, body.job_slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/whatsapp/chats/{wa_id}/copy")
async def whatsapp_copy_chat(
    wa_id: str,
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _require_founder(x_founder_pin)
    from app.services.max.whatsapp_log import conversation_copy_text

    return {"wa_id": wa_id, "text": conversation_copy_text(wa_id)}


@router.get("/whatsapp/chats/{wa_id}/export")
async def whatsapp_export_chat(
    wa_id: str,
    format: str = Query("pdf"),
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _require_founder(x_founder_pin)
    from app.services.max.whatsapp_log import conversation_copy_text, conversation_export_pdf, get_display_label

    label = get_display_label(wa_id).replace(" ", "-")
    if (format or "pdf").lower() == "txt":
        text = conversation_copy_text(wa_id)
        return PlainTextResponse(text, headers={
            "Content-Disposition": f'attachment; filename="whatsapp-{label}.txt"',
        })
    pdf = conversation_export_pdf(wa_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="whatsapp-{label}.pdf"'},
    )


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
