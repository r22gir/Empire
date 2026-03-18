"""Email service for MAX — sends emails with optional PDF attachments.

Priority: SendGrid API (if SENDGRID_API_KEY is set) -> SMTP (if configured).

SendGrid env vars:
  SENDGRID_API_KEY    — SendGrid API key
  SENDGRID_FROM_EMAIL — sender address (default: workroom@empirebox.store)

SMTP env vars (fallback):
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
        # SendGrid config
        self.sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
        self.sendgrid_from = os.environ.get("SENDGRID_FROM_EMAIL", "workroom@empirebox.store")

        # SMTP config (fallback)
        self.host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.from_name = os.environ.get("SMTP_FROM_NAME", "MAX — Empire AI")

    @property
    def is_configured(self) -> bool:
        """True if SendGrid OR SMTP credentials are available."""
        return bool(self.sendgrid_key) or bool(self.user and self.password)

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
        cc: str | None = None,
    ) -> bool:
        """Send an email. Returns True on success.

        Tries SendGrid first (if configured), then SMTP fallback.

        Args:
            to: recipient email address
            subject: email subject line
            body_html: HTML body content
            attachments: list of file paths to attach
            cc: optional CC address
        """
        if not self.is_configured:
            raise RuntimeError(
                "Email not configured — set SENDGRID_API_KEY or SMTP_USER/SMTP_PASSWORD env vars"
            )

        if self.sendgrid_key:
            return self._send_sendgrid(to, subject, body_html, attachments, cc)

        return self._send_smtp(to, subject, body_html, attachments, cc)

    def _send_sendgrid(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
        cc: str | None = None,
    ) -> bool:
        """Send via SendGrid API."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import (
                Mail, Attachment, FileContent, FileName, FileType, Disposition,
            )
            import base64
            import mimetypes

            message = Mail(
                from_email=self.sendgrid_from,
                to_emails=to,
                subject=subject,
                html_content=body_html,
            )

            if cc:
                from sendgrid.helpers.mail import Cc
                message.add_cc(Cc(cc))

            # Attach files
            for filepath in (attachments or []):
                path = Path(filepath)
                if not path.exists():
                    logger.warning(f"Attachment not found: {filepath}")
                    continue
                with open(path, "rb") as f:
                    file_data = f.read()
                encoded_file = base64.b64encode(file_data).decode()
                mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(path.name),
                    FileType(mime_type),
                    Disposition("attachment"),
                )
                message.add_attachment(attachment)

            sg = SendGridAPIClient(self.sendgrid_key)
            response = sg.send(message)
            if response.status_code < 300:
                logger.info(f"Email sent via SendGrid to {to} — subject: {subject}")
                return True
            else:
                logger.error(f"SendGrid returned status {response.status_code} for {to}")
                raise RuntimeError(f"SendGrid error: status {response.status_code}")
        except ImportError:
            logger.error("sendgrid package not installed — run: pip install sendgrid")
            raise RuntimeError("sendgrid package not installed")
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            raise

    def _send_smtp(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
        cc: str | None = None,
    ) -> bool:
        """Send via SMTP (original method)."""
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
            logger.info(f"Email sent via SMTP to {to} — subject: {subject}")
            return True
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            raise
