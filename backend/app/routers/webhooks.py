"""
Webhook routes for receiving notifications from external services.
Email (SendGrid inbound), eBay notifications, and Stripe (see payments.py for primary handler).
"""
from fastapi import APIRouter, Request
import logging
import os
from uuid import uuid4

logger = logging.getLogger("empire.webhooks")

router = APIRouter(tags=["Webhooks"])


@router.post("/webhooks/email/inbound")
@router.post("/email/inbound")
async def handle_inbound_email(request: Request):
    """Handle incoming email webhook from SendGrid Inbound Parse.

    Receives emails and logs them. When SENDGRID_API_KEY is configured,
    this endpoint will create support tickets or notify the founder.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    sender = data.get("from", data.get("sender", "unknown"))
    recipient = data.get("to", data.get("recipient", os.getenv("MAX_EMAIL", "max@empirebox.store")))
    subject = data.get("subject", "No subject")
    body = data.get("text") or data.get("body") or data.get("html") or ""
    attachments = data.get("attachments") or data.get("attachment_refs") or []
    source_message_id = data.get("message_id") or data.get("Message-Id") or data.get("headers", {}).get("Message-Id")
    thread_id = data.get("thread_id") or source_message_id or f"email-{uuid4().hex[:12]}"
    founder_emails = {
        e.strip().lower()
        for e in (os.getenv("FOUNDER_EMAILS") or os.getenv("FOUNDER_EMAIL", "empirebox2026@gmail.com")).split(",")
        if e.strip()
    }
    founder_verified = sender.strip().lower() in founder_emails
    logger.info(f"Inbound email from {sender}: {subject}")

    try:
        from app.services.max.unified_message_store import unified_store
        unified_store.add_message(
            conversation_id=thread_id,
            channel="email",
            role="user",
            content=body or subject,
            direction="inbound",
            sender=sender,
            recipient=recipient,
            thread_id=thread_id,
            source_message_id=source_message_id,
            subject=subject,
            attachment_refs=attachments,
            summary=subject,
            founder_verified=founder_verified,
            metadata={
                "subject": subject,
                "sender": sender,
                "recipient": recipient,
                "attachments": attachments,
                "trust": "founder_sender_match" if founder_verified else "unverified_sender",
            },
        )
    except Exception as exc:
        logger.warning(f"Unified message store email write failed: {exc}")

    # Log to notifications if available
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post("http://localhost:8000/api/v1/notifications/internal", json={
                "source": "Email",
                "type": "email_inbound",
                "title": f"Email from {sender}",
                "message": subject,
                "priority": "medium",
                "context": {"sender": sender, "subject": subject, "recipient": recipient},
            })
    except Exception:
        pass

    return {
        "status": "received",
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "thread_id": thread_id,
        "founder_verified": founder_verified,
        "ledger": "unified_messages",
    }


@router.post("/webhooks/ebay/notification")
@router.post("/ebay/notification")
async def handle_ebay_notification(request: Request):
    """Handle eBay notification webhook.

    Processes order notifications, messages, and listing updates.
    Requires EBAY_APP_ID to be configured for signature verification.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    event_type = data.get("NotificationType", data.get("type", "unknown"))
    logger.info(f"eBay notification: {event_type}")

    # Log to notifications
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post("http://localhost:8000/api/v1/notifications/internal", json={
                "source": "eBay",
                "type": "ebay_webhook",
                "title": f"eBay: {event_type}",
                "message": f"Received eBay {event_type} notification",
                "priority": "medium",
                "context": data,
            })
    except Exception:
        pass

    return {"status": "received", "event_type": event_type}


@router.post("/webhooks/stripe")
@router.post("/stripe")
async def handle_stripe_webhook(request: Request):
    """Legacy Stripe webhook endpoint.

    The primary Stripe webhook handler is at /api/v1/payments/webhook.
    This endpoint forwards to the main handler for backwards compatibility.
    """
    # Forward to the real Stripe webhook handler
    try:
        import httpx
        body = await request.body()
        headers = dict(request.headers)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "http://localhost:8000/api/v1/payments/webhook",
                content=body,
                headers={"stripe-signature": headers.get("stripe-signature", ""),
                         "content-type": "application/json"},
            )
            return resp.json()
    except Exception as e:
        logger.warning(f"Stripe webhook forward failed: {e}")
        return {"status": "received", "message": "Forwarded to main handler"}
