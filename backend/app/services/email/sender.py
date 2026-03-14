"""
Email sending service for Empire workroom communications.

Uses SMTP configuration from environment variables.
Falls back gracefully if SMTP is not configured.
"""

import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("empire.email")

# SMTP configuration from env
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")


def _is_configured() -> bool:
    """Check if SMTP is configured."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM)


def _build_message(to: str, subject: str, html_body: str) -> MIMEMultipart:
    """Build a MIME email message."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


async def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Send an HTML email via SMTP.

    Returns True on success, False on failure or missing config.
    Uses aiosmtplib if available, otherwise falls back to smtplib in a thread.
    """
    if not _is_configured():
        logger.warning("SMTP not configured — email to %s not sent. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM.", to)
        return False

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
        logger.info("Email sent to %s: %s", to, subject)
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
