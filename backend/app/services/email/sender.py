"""
Email sending service for Empire workroom communications.

Priority: SendGrid API (if SENDGRID_API_KEY is set) -> SMTP (if configured).
Falls back gracefully if neither is configured.
"""

import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("empire.email")

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "workroom@empirebox.store")

# SMTP configuration from env (fallback)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")


def _write_outbound_ledger(to: str, subject: str, html_body: str, service: str) -> None:
    """Best-effort continuity ledger write after confirmed successful send."""
    try:
        from app.services.max.unified_message_store import unified_store
        sender = os.getenv("SENDGRID_FROM_EMAIL", "") or SENDGRID_FROM_EMAIL or SMTP_FROM or "MAX"
        inserted = unified_store.add_outbound_email(
            recipient=to,
            subject=subject,
            body_html=html_body,
            sender=sender,
            attachments=[],
            metadata={"service": service},
        )
        if not inserted:
            logger.info("Outbound email ledger entry already exists for %s: %s", to, subject)
    except Exception as exc:
        logger.warning("Outbound email sent but unified ledger write failed: %s", exc)


def _sendgrid_configured() -> bool:
    return bool(os.getenv("SENDGRID_API_KEY", "") or SENDGRID_API_KEY)


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM)


def _build_message(to: str, subject: str, html_body: str) -> MIMEMultipart:
    """Build a MIME email message."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


async def _send_via_sendgrid(to: str, subject: str, html_body: str) -> bool:
    """Send email using SendGrid v3 API via httpx."""
    try:
        import httpx
        api_key = os.getenv("SENDGRID_API_KEY", "") or SENDGRID_API_KEY
        from_email = os.getenv("SENDGRID_FROM_EMAIL", "") or SENDGRID_FROM_EMAIL
        r = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": from_email, "name": "Empire Workroom"},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_body}],
            },
            timeout=30,
        )
        if r.status_code < 300:
            logger.info("Email sent via SendGrid to %s: %s (status %s)", to, subject, r.status_code)
            return True
        else:
            logger.error("SendGrid returned %s for %s: %s", r.status_code, to, r.text)
            return False
    except Exception as e:
        logger.error("SendGrid send failed for %s: %s", to, e)
        return False


async def _send_via_smtp(to: str, subject: str, html_body: str) -> bool:
    """Send email using SMTP (async or sync fallback)."""
    msg = _build_message(to, subject, html_body)

    # Try async SMTP first
    try:
        import aiosmtplib
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=SMTP_PORT == 465,
            start_tls=SMTP_PORT != 465,
        )
        logger.info("Email sent via SMTP to %s: %s", to, subject)
        return True
    except ImportError:
        pass
    except Exception as e:
        logger.error("aiosmtplib failed for %s: %s", to, e)
        return False

    # Fallback: blocking smtplib in a thread
    try:
        import asyncio
        import smtplib

        def _send_sync():
            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
            else:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())
            server.quit()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_sync)
        logger.info("Email sent (sync fallback) to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("smtplib failed for %s: %s", to, e)
        return False


async def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Send an HTML email. Tries SendGrid first, then SMTP.

    Returns True on success, False on failure or missing config.
    """
    # Re-check env vars at call time (modules may load before .env is sourced)
    if _sendgrid_configured():
        sent = await _send_via_sendgrid(to, subject, html_body)
        if sent:
            _write_outbound_ledger(to, subject, html_body, "app.services.email.sender.send_email/sendgrid")
        return sent

    if _smtp_configured():
        sent = await _send_via_smtp(to, subject, html_body)
        if sent:
            _write_outbound_ledger(to, subject, html_body, "app.services.email.sender.send_email/smtp")
        return sent

    logger.warning(
        "Email not configured — SENDGRID_API_KEY=%s, SMTP_HOST=%s. "
        "Email to %s not sent.",
        "SET" if os.getenv("SENDGRID_API_KEY") else "EMPTY",
        "SET" if os.getenv("SMTP_HOST") else "EMPTY",
        to,
    )
    return False
