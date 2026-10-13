"""Voice documents router (IMP-0004).

Voice-driven document dispatch: direct email sending and queued-task
(quote) approval from voice on verified founder sessions.

Safety contract:
- Verified founder session (Command Center / web_cc, or Telegram founder
  chat_id, via is_founder_message) → direct send + direct approval.
- Anything else → read-only / queued-for-founder-approval. Nothing is
  sent and nothing is approved; the request is returned as a draft/queue
  entry for a founder tap.
- The founder recipient lock (only empirebox2026@gmail.com, no cc/bcc/
  reply-to overrides, never clients) is enforced server-side for EVERYONE,
  founder sessions included. Quotes/client emails remain drafts only.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("empire.voice_documents")
router = APIRouter()


# ── Request models ─────────────────────────────────────────────────

class VoiceSendEmailRequest(BaseModel):
    to: str = Field(default="", description="Recipient (must be empirebox2026@gmail.com)")
    subject: str = ""
    body: str = ""
    channel: str = Field(default="", description="Caller channel, e.g. web_cc, telegram, voice")
    chat_id: Optional[str] = None
    cc: Optional[str] = None
    bcc: Optional[str] = None
    reply_to: Optional[str] = None


class VoiceApproveRequest(BaseModel):
    channel: str = Field(default="")
    chat_id: Optional[str] = None
    reason: Optional[str] = ""


# ── Helpers ────────────────────────────────────────────────────────

def _is_founder_session(channel: str, chat_id: Optional[str]) -> bool:
    """True only for verified founder sessions (CC/web, Telegram founder)."""
    from app.services.max.guardrails import is_founder_message
    return bool(is_founder_message({"channel": channel or "", "chat_id": chat_id or ""}))


def _queued_denial(action: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail=(
            f"Not a verified founder session: {action} is queued for founder "
            "approval. Nothing was sent and nothing was approved — a founder "
            "tap is required (outreach stays draft-only)."
        ),
    )


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/voice/documents/approval-queue")
def voice_approval_queue():
    """Read-only: quotes awaiting founder review (safe for any caller)."""
    from app.services.quote_service import list_quotes_awaiting_review
    return {"status": "ok", "queue": list_quotes_awaiting_review()}


@router.post("/voice/documents/send-email")
def voice_send_email(req: VoiceSendEmailRequest):
    """Direct email dispatch from voice on founder sessions.

    Founder session → validates the recipient lock, then sends via
    EmailService (only empirebox2026@gmail.com; cc/bcc/reply-to rejected).
    Non-founder → 403 queued-for-founder-approval; nothing is sent.
    """
    if not _is_founder_session(req.channel, req.chat_id):
        raise _queued_denial("voice email send")

    from app.services.max.email_recipient_guard import RecipientRejected, validate_outbound_email
    try:
        recipient = validate_outbound_email(req.to, cc=req.cc, bcc=req.bcc, reply_to=req.reply_to)
    except RecipientRejected as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not req.subject.strip() or not req.body.strip():
        raise HTTPException(status_code=422, detail="subject and body are required")

    from app.services.max.email_service import EmailService
    svc = EmailService()
    if not svc.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Email not configured — set SENDGRID_API_KEY or SMTP_USER/SMTP_PASSWORD in .env",
        )
    try:
        sent = svc.send(to=recipient, subject=req.subject.strip(), body_html=req.body)
    except RecipientRejected as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("voice email send failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Email send failed: {e}")
    if not sent:
        raise HTTPException(status_code=502, detail="Email provider did not verify send acceptance")
    return {"status": "sent", "to": recipient, "subject": req.subject.strip()}


@router.post("/voice/documents/approve-quote/{quote_id}")
def voice_approve_quote(quote_id: str, req: VoiceApproveRequest):
    """Approve a queued quote from voice on founder sessions.

    Founder session → approves founder_review → sent via the service layer
    using the server-side FOUNDER_APPROVAL_PIN (never exposed to the caller).
    Non-founder → 403 queued-for-founder-approval; nothing is approved.
    Approving does NOT send the PDF/email — sending stays explicit.
    """
    if not _is_founder_session(req.channel, req.chat_id):
        raise _queued_denial("voice quote approval")

    from app.services.max.access_control import FOUNDER_APPROVAL_PIN
    if not FOUNDER_APPROVAL_PIN:
        raise HTTPException(
            status_code=503,
            detail="FOUNDER_APPROVAL_PIN is not configured on the server.",
        )
    try:
        from app.services.quote_service import InvalidFounderPin, InvalidTransition, approve_quote
        q = approve_quote(
            quote_id,
            changed_by="founder",
            reason=req.reason or "approved from voice on founder session",
            founder_pin=os.getenv("FOUNDER_APPROVAL_PIN", ""),
        )
    except InvalidFounderPin as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("voice quote approval failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Approval failed: {e}")
    if not q:
        raise HTTPException(status_code=404, detail=f"quote {quote_id} not found")
    return {
        "status": "approved",
        "quote_id": q.get("id"),
        "quote_number": q.get("quote_number"),
        "note": "Transition only. To send the PDF/email, use voice email send separately.",
    }
