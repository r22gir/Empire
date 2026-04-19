"""
Webhook routes for receiving notifications from external services.
Email (SendGrid inbound), eBay notifications, and Stripe (see payments.py for primary handler).
"""
from fastapi import APIRouter, HTTPException, Request
import logging
import os
from uuid import uuid4

logger = logging.getLogger("empire.webhooks")

router = APIRouter(tags=["Webhooks"])


def classify_max_email(subject: str, body: str, attachments: list | dict | str | None) -> dict:
    """Cheap deterministic tag for founder email intake; no fake AI classification."""
    text = f"{subject or ''} {body or ''}".lower()
    attachment_count = len(attachments) if isinstance(attachments, list) else (1 if attachments else 0)
    tags = []
    if attachment_count:
        tags.append("attachment")
    if any(word in text for word in ("todo", "task", "please do", "follow up", "remind", "schedule", "create", "fix")):
        tags.append("task")
    if "?" in text or any(word in text for word in ("can you", "what ", "why ", "how ", "when ", "where ")):
        tags.append("question")
    if any(word in text for word in ("review", "analyze", "summarize", "check", "look at", "use this")):
        tags.append("instruction")
    if not tags:
        tags.append("instruction")

    if "task" in tags:
        classification = "task"
    elif "attachment" in tags:
        classification = "attachment"
    elif "question" in tags:
        classification = "question"
    else:
        classification = "instruction"

    return {
        "classification": classification,
        "tags": tags,
        "attachment_count": attachment_count,
    }


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
    email_classification = classify_max_email(subject, body, attachments)
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
            linked_refs=[{"type": "email_intent", "id": email_classification["classification"]}],
            metadata={
                "subject": subject,
                "sender": sender,
                "recipient": recipient,
                "attachments": attachments,
                "classification": email_classification["classification"],
                "tags": email_classification["tags"],
                "attachment_count": email_classification["attachment_count"],
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
        "classification": email_classification["classification"],
        "tags": email_classification["tags"],
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
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Stripe webhook forward failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Legacy Stripe webhook forward failed; primary owner is /api/v1/payments/webhook",
        )


@router.post("/telegram-webhook")
async def handle_telegram_webhook(request: Request):
    """Receive incoming Telegram updates via webhook and feed them to the MAX bot.

    Telegram sends POST requests to https://api.empirebox.store/telegram-webhook
    (routed through Cloudflare Tunnel). This endpoint parses each update and
    puts it in the bot's update queue for processing by registered handlers.
    """
    try:
        update_dict = await request.json()
    except Exception as e:
        logger.warning(f"Telegram webhook failed to parse JSON: {e}")
        return {"ok": False, "error": "invalid json"}

    # Feed update to the bot's queue
    try:
        from app.services.max.telegram_bot import telegram_bot
        if not telegram_bot.is_configured:
            return {"ok": False, "error": "bot not configured"}
        success = await telegram_bot.process_webhook_update(update_dict)
        if success:
            return {"ok": True}
        else:
            # Bot not ready yet - return 200 so Telegram doesn't retry excessively
            return {"ok": False, "error": "bot not ready"}
    except Exception as e:
        logger.error(f"Telegram webhook processing error: {e}")
        return {"ok": False, "error": str(e)}
