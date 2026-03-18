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


def _sendgrid_configured() -> bool:
    return bool(SENDGRID_API_KEY)


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
    """Send email using SendGrid API."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to,
            subject=subject,
            html_content=html_body,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code < 300:
            logger.info("Email sent via SendGrid to %s: %s (status %s)", to, subject, response.status_code)
            return True
        else:
            logger.error("SendGrid returned status %s for %s", response.status_code, to)
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
    if _sendgrid_configured():
        return await _send_via_sendgrid(to, subject, html_body)

    if _smtp_configured():
        return await _send_via_smtp(to, subject, html_body)

    logger.warning(
        "Email not configured — set SENDGRID_API_KEY or SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM. "
        "Email to %s not sent.", to
    )
    return False
