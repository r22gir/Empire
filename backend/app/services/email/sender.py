"""
Email sending service for Empire workroom communications.

Priority: SendGrid API (if SENDGRID_API_KEY is set) -> SMTP (if configured).
Falls back gracefully if neither is configured.

Optional in-memory attachments (filename + bytes). Never inline HTML/SVG.
Callers must not pass public or signed URLs — this sender only attaches bytes.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from app.config.workroom_billing import get_workroom_billing

logger = logging.getLogger("empire.email")

_HTML_LIKE_EXT = frozenset({
    ".html", ".htm", ".shtml", ".xhtml", ".svg", ".xml", ".js", ".mjs",
})
_HTML_LIKE_MIME = frozenset({
    "text/html", "application/xhtml+xml", "image/svg+xml",
    "text/xml", "application/xml", "text/javascript",
    "application/javascript", "application/x-javascript",
})
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

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


def _safe_attach_name(name: str) -> str:
    raw = (name or "").split("/")[-1].split("\\")[-1].strip() or "adjunto"
    cleaned = _SAFE_NAME_RE.sub("_", raw).strip("._") or "adjunto"
    return cleaned[:120]


def sanitize_email_attachments(attachments: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Keep only in-memory file bytes. Drop HTML/SVG. Never accept URL fields."""
    out: list[dict[str, Any]] = []
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        data = item.get("data")
        if not isinstance(data, (bytes, bytearray)) or not data:
            continue
        filename = _safe_attach_name(str(item.get("filename") or "adjunto"))
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()
        mime = str(item.get("content_type") or "").split(";")[0].strip().lower()
        if ext in _HTML_LIKE_EXT or mime in _HTML_LIKE_MIME or mime.startswith("text/html"):
            continue
        if not mime or mime.startswith("text/html"):
            mime = "application/octet-stream"
        out.append({
            "filename": filename,
            "content_type": mime,
            "data": bytes(data),
        })
    return out


def _sendgrid_attachment_payload(item: dict[str, Any]) -> dict[str, str]:
    return {
        "content": base64.b64encode(item["data"]).decode("ascii"),
        "filename": item["filename"],
        "type": item["content_type"],
        "disposition": "attachment",
    }


def _build_message(
    to: str,
    subject: str,
    html_body: str,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> MIMEMultipart:
    """Build a MIME email message. Attachments are always disposition=attachment."""
    files = sanitize_email_attachments(attachments)
    if files:
        msg = MIMEMultipart("mixed")
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt)
        for item in files:
            main, _, sub = (item["content_type"] or "application/octet-stream").partition("/")
            part = MIMEBase(main or "application", sub or "octet-stream")
            part.set_payload(item["data"])
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{item["filename"]}"')
            part.add_header("X-Content-Type-Options", "nosniff")
            msg.attach(part)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    return msg


async def _send_via_sendgrid(
    to: str,
    subject: str,
    html_body: str,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> bool:
    """Send email using SendGrid v3 API via httpx."""
    try:
        import httpx
        api_key = os.getenv("SENDGRID_API_KEY", "") or SENDGRID_API_KEY
        from_email = os.getenv("SENDGRID_FROM_EMAIL", "") or SENDGRID_FROM_EMAIL
        payload: dict[str, Any] = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": from_email, "name": get_workroom_billing().name},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }
        encoded = [
            _sendgrid_attachment_payload(item)
            for item in sanitize_email_attachments(attachments)
        ]
        if encoded:
            payload["attachments"] = encoded
        r = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
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


async def _send_via_smtp(
    to: str,
    subject: str,
    html_body: str,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> bool:
    """Send email using SMTP (async or sync fallback)."""
    msg = _build_message(to, subject, html_body, attachments)

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


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> bool:
    """
    Send an HTML email. Tries SendGrid first, then SMTP.

    ``attachments`` is an optional list of ``{filename, content_type, data}``.
    Bytes only — no URLs. HTML/SVG are dropped. Disposition is always
    attachment (never inline).

    Returns True on success, False on failure or missing config.
    """
    # Re-check env vars at call time (modules may load before .env is sourced)
    if _sendgrid_configured():
        sent = await _send_via_sendgrid(to, subject, html_body, attachments)
        if sent:
            _write_outbound_ledger(to, subject, html_body, "app.services.email.sender.send_email/sendgrid")
        return sent

    if _smtp_configured():
        sent = await _send_via_smtp(to, subject, html_body, attachments)
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
