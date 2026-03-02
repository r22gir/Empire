"""Email service for MAX — sends emails with optional PDF attachments.

Uses Python stdlib smtplib + email.mime. Works with Gmail (app password),
Outlook, or any standard SMTP provider.

Env vars:
  SMTP_HOST       — SMTP server (default: smtp.gmail.com)
  SMTP_PORT       — SMTP port (default: 587 for STARTTLS)
  SMTP_USER       — login email address
  SMTP_PASSWORD   — app password (NOT regular password)
  SMTP_FROM_NAME  — sender display name (default: "MAX — Empire AI")
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

logger = logging.getLogger("max.email_service")


class EmailService:
    def __init__(self):
        self.host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.from_name = os.environ.get("SMTP_FROM_NAME", "MAX — Empire AI")

    @property
    def is_configured(self) -> bool:
        return bool(self.user and self.password)

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
        cc: str | None = None,
    ) -> bool:
        """Send an email. Returns True on success.

        Args:
            to: recipient email address
            subject: email subject line
            body_html: HTML body content
            attachments: list of file paths to attach
            cc: optional CC address
        """
        if not self.is_configured:
            raise RuntimeError("Email not configured — set SMTP_USER and SMTP_PASSWORD env vars")

        msg = MIMEMultipart()
        msg["From"] = f"{self.from_name} <{self.user}>"
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        msg.attach(MIMEText(body_html, "html"))

        # Attach files
        for filepath in (attachments or []):
            path = Path(filepath)
            if not path.exists():
                logger.warning(f"Attachment not found: {filepath}")
                continue
            part = MIMEBase("application", "octet-stream")
            part.set_payload(path.read_bytes())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{path.name}"',
            )
            msg.attach(part)

        recipients = [to]
        if cc:
            recipients.append(cc)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.user, self.password)
                server.sendmail(self.user, recipients, msg.as_string())
            logger.info(f"Email sent to {to} — subject: {subject}")
            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            raise
