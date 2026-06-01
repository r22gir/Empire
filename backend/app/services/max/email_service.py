"""Email service for MAX — sends emails with optional PDF attachments.

Priority: SendGrid API (if SENDGRID_API_KEY is set) -> SMTP (if configured).

SendGrid env vars:
  SENDGRID_API_KEY    — SendGrid API key
  SENDGRID_FROM_EMAIL — sender address (default: workroom@empirebox.store)

SMTP env vars (fallback):
  SMTP_HOST       — SMTP server (default: smtp.gmail.com)
  SMTP_PORT       — SMTP port (default: 587 for STARTTLS)
  SMTP_USER       — login email address (authenticated Gmail account)
  SMTP_PASSWORD   — app password (NOT regular password)
  SMTP_FROM       — sender address for From/Reply-To headers and envelope
                    (only needed if different from SMTP_USER, e.g. max@empirebox.store alias)
  SMTP_FROM_NAME  — sender display name (default: "MAX — Empire AI")
  SMTP_REPLY_TO   — Reply-To header address (default: same as SMTP_FROM if set)
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
from pathlib import Path

import httpx

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
        # Explicit sender address (allows Gmail send-as alias, e.g. max@empirebox.store)
        self.from_addr = os.environ.get("SMTP_FROM", "") or self.user
        self.reply_to = os.environ.get("SMTP_REPLY_TO", "") or self.from_addr

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
        in_reply_to: str | None = None,
        references: str | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """Send an email. Returns True on success.

        Tries SendGrid first (if configured), then SMTP fallback.

        Args:
            to: recipient email address
            subject: email subject line
            body_html: HTML body content
            attachments: list of file paths to attach
            cc: optional CC address
            in_reply_to: Message-ID this email replies to (sets In-Reply-To)
            references: accumulated References header for threading
            reply_to: override Reply-To address
        """
        if not self.is_configured:
            raise RuntimeError(
                "Email not configured — set SENDGRID_API_KEY or SMTP_USER/SMTP_PASSWORD env vars"
            )
        self._verify_send_payload(to, subject, body_html, attachments)

        if self.sendgrid_key:
            sent = self._send_sendgrid(to, subject, body_html, attachments, cc, in_reply_to, references, reply_to)
        else:
            sent = self._send_smtp(to, subject, body_html, attachments, cc, in_reply_to, references, reply_to)
        if sent:
            self._write_outbound_ledger(to, subject, body_html, attachments, cc)
        return sent

    def _verify_send_payload(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
    ) -> None:
        """Fail before provider calls when the message or attachments are not real."""
        if not str(to or "").strip():
            raise ValueError("Email recipient is required")
        if not str(subject or "").strip():
            raise ValueError("Email subject is required")
        if not str(body_html or "").strip():
            raise ValueError("Email body is empty; refusing to report a delivered analysis")
        missing = [str(path) for path in (attachments or []) if not Path(str(path)).exists()]
        if missing:
            raise FileNotFoundError(f"Email attachment not found: {', '.join(missing)}")

    def _write_outbound_ledger(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
        cc: str | None = None,
    ) -> None:
        """Best-effort continuity ledger write after confirmed successful send."""
        try:
            from app.services.max.unified_message_store import unified_store
            inserted = unified_store.add_outbound_email(
                recipient=to,
                subject=subject,
                body_html=body_html,
                sender=self.sendgrid_from if self.sendgrid_key else (self.user or self.sendgrid_from),
                cc=cc,
                attachments=attachments or [],
                metadata={"service": "app.services.max.email_service.EmailService"},
            )
            if not inserted:
                logger.info("Outbound email ledger entry already exists for %s: %s", to, subject)
        except Exception as exc:
            logger.warning("Outbound email sent but unified ledger write failed: %s", exc)

    def _send_sendgrid(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachments: list[str] | None = None,
        cc: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """Send via SendGrid v3 API using httpx.

        The backend already depends on httpx. Keeping this path SDK-free avoids
        a false "configured but unusable" state when the optional sendgrid
        package is not installed.
        """
        try:
            import base64
            import mimetypes
            import httpx

            personalization: dict = {"to": [{"email": to}]}
            if cc:
                personalization["cc"] = [{"email": cc}]

            payload: dict = {
                "personalizations": [personalization],
                "from": {"email": self.sendgrid_from, "name": self.from_name},
                "subject": subject,
                "content": [{"type": "text/html", "value": body_html}],
            }

            # Threading / reply headers (SendGrid custom args)
            sg_headers: dict = {}
            if in_reply_to:
                sg_headers["In-Reply-To"] = in_reply_to
            if references:
                sg_headers["References"] = references
            if reply_to:
                sg_headers["Reply-To"] = reply_to
            elif self.reply_to:
                sg_headers["Reply-To"] = self.reply_to
            if sg_headers:
                # Per personalization for reply threading
                personalization["headers"] = sg_headers

            encoded_attachments = []
            for filepath in (attachments or []):
                path = Path(filepath)
                encoded_attachments.append({
                    "content": base64.b64encode(path.read_bytes()).decode("ascii"),
                    "filename": path.name,
                    "type": mimetypes.guess_type(str(path))[0] or "application/octet-stream",
                    "disposition": "attachment",
                })
            if encoded_attachments:
                payload["attachments"] = encoded_attachments

            response = httpx.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self.sendgrid_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            if response.status_code < 300:
                logger.info(f"Email sent via SendGrid to {to} — subject: {subject}")
                return True
            logger.error(
                "SendGrid returned status %s for %s: %s",
                response.status_code,
                to,
                response.text[:500],
            )
            raise RuntimeError(f"SendGrid error: status {response.status_code}")
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
        in_reply_to: str | None = None,
        references: str | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """Send via SMTP with full threading header support."""
        msg = MIMEMultipart()
        msg["From"] = formataddr((self.from_name, self.from_addr))
        msg["To"] = to
        msg["Subject"] = subject
        # Threading headers
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        reply_to_addr = reply_to or self.reply_to
        if reply_to_addr:
            msg["Reply-To"] = reply_to_addr
        if cc:
            msg["Cc"] = cc

        msg.attach(MIMEText(body_html, "html"))

        # Attach files
        for filepath in (attachments or []):
            path = Path(filepath)
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
                server.sendmail(self.from_addr, recipients, msg.as_string())
            logger.info(f"Email sent via SMTP to {to} — subject: {subject}")
            return True
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            raise


# ---------------------------------------------------------------------------
# Dry-run MAX email response generation (no send)
# ---------------------------------------------------------------------------

# Explicit states for dry-run response generation
DRY_RUN_STATE_GENERATED = "response_generated"
DRY_RUN_STATE_TIMEOUT = "response_generation_timeout"
DRY_RUN_STATE_BLOCKED = "response_generation_blocked"
DRY_RUN_STATE_SKIPPED = "response_generation_skipped"

# Direct MAX chat call timeout — must be long enough for DeepSeek to respond
# but bounded to avoid hanging dry-run requests indefinitely.
_DRY_RUN_MAX_CHAT_TIMEOUT = 90


def generate_email_reply_draft(
    sender: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
    source_message_id: str | None = None,
    tiny_test_prompt: str | None = None,
) -> dict:
    """Run the full inbound-email pipeline and produce a draft MAX reply.

    Pipeline: allowlist check -> classification -> MAX chat (DeepSeek) -> draft.

    This function NEVER sends email. It returns a draft payload that the caller
    may review before any live send.

    If *tiny_test_prompt* is given, the email body is replaced with that prompt
    (prefixed by 'Reply only:') so the model returns a bounded deterministic
    response suitable for smoke-testing the pipeline.

    Returns a dict with keys:
        sender_authorized, blocked_reason, classification,
        response_state, timeout_seconds, provider, model, fallback_used,
        max_response_text, draft_subject, draft_in_reply_to,
        draft_references, would_send (always False), error
    """
    from app.services.max.email_sender_whitelist import authorize_email_sender
    from app.routers.webhooks import classify_max_email

    result: dict = {
        "sender_authorized": False,
        "blocked_reason": None,
        "classification": None,
        "response_state": DRY_RUN_STATE_SKIPPED,
        "timeout_seconds": _DRY_RUN_MAX_CHAT_TIMEOUT,
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "selected_provider_source": "routing_state",
        "fallback_used": False,
        "max_response_text": None,
        "draft_subject": None,
        "draft_in_reply_to": source_message_id,
        "draft_references": source_message_id,
        "would_send": False,
        "error": None,
    }

    # 1. Allowlist check
    auth = authorize_email_sender(sender)
    result["sender_authorized"] = auth["sender_authorized"]
    result["blocked_reason"] = auth["blocked_reason"]

    if not auth["sender_authorized"]:
        result["response_state"] = DRY_RUN_STATE_BLOCKED
        result["error"] = f"Sender not authorized: {auth['blocked_reason']}"
        return result

    # 2. Classification (intent tags)
    classification = classify_max_email(subject, body, None)
    result["classification"] = classification

    # 2b. Capability classification (what kind of request, what's allowed)
    from app.services.max.email_capability_router import classify_email_capability
    capability = classify_email_capability(
        sender_authorized=result["sender_authorized"],
        subject=subject,
        body=body,
        has_attachments=False,
    )
    result["capability"] = capability

    # 3. Read active routing state to determine provider/model.
    #    Never calls internal HTTP — avoids single-worker deadlock.
    fallback_enabled = False
    try:
        from app.services.max.routing_state import load_routing_state
        routing = load_routing_state()
        result["provider"] = routing.selected_provider
        result["model"] = routing.selected_model
        fallback_enabled = routing.fallback_enabled
        result["selected_provider_source"] = "routing_state"
    except Exception:
        # Fallback: read from env (degraded but safe)
        result["provider"] = "deepseek"
        result["model"] = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        result["selected_provider_source"] = "env_fallback"

    result["fallback_used"] = fallback_enabled

    # 4. Resolve provider API config
    provider_key = result["provider"]
    if provider_key == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        openai_compatible = True
    elif provider_key == "minimax":
        api_key = os.getenv("MINIMAX_API_KEY", "")
        base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
        openai_compatible = True
    elif provider_key == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = "https://api.openai.com/v1"
        openai_compatible = True
    elif provider_key in ("qwen", "openrouter", "groq", "xai"):
        api_key = os.getenv(f"{provider_key.upper()}_API_KEY", "")
        openai_compatible = True
        base_url = {
            "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "groq": "https://api.groq.com/openai/v1",
            "xai": "https://api.x.ai/v1",
        }.get(provider_key, "")
    else:
        openai_compatible = False
        api_key = ""
        base_url = ""

    if not openai_compatible or not api_key:
        result["response_state"] = DRY_RUN_STATE_BLOCKED
        result["error"] = (
            f"Provider '{provider_key}' is not supported for email response "
            f"generation or API key is missing"
        )
        return result

    # 5. Build prompt
    if tiny_test_prompt:
        prompt = f"Reply only: {tiny_test_prompt}"
    else:
        prompt = (
            f"You received an email from {sender}.\n\n"
            f"Subject: {subject}\n\n"
            f"Body:\n{body}\n\n"
            f"Draft a concise, helpful reply. Do not include "
            f"the sender's email address or full name in the greeting."
        )

    # 6. Call provider directly (OpenAI-compatible chat completions).
    #    Never calls internal MAX HTTP — avoids single-worker deadlock.
    payload = {
        "model": result["model"],
        "messages": [
            {"role": "system", "content": "You are MAX, the AI Assistant Manager for Empire. Keep replies concise, practical, and friendly."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=_DRY_RUN_MAX_CHAT_TIMEOUT) as client:
            api_resp = client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            if api_resp.status_code == 200:
                data = api_resp.json()
                result["max_response_text"] = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                result["model_used"] = f"{provider_key}-{result['model']}"
                result["response_state"] = DRY_RUN_STATE_GENERATED
                result["fallback_used"] = False  # primary provider worked
            else:
                result["response_state"] = DRY_RUN_STATE_BLOCKED
                result["error"] = f"Provider '{provider_key}' returned status {api_resp.status_code}"
    except httpx.TimeoutException:
        result["response_state"] = DRY_RUN_STATE_TIMEOUT
        result["error"] = f"Provider '{provider_key}' timed out after {_DRY_RUN_MAX_CHAT_TIMEOUT}s"
    except Exception as exc:
        logger.error(f"Email reply draft generation failed: {exc}")
        result["response_state"] = DRY_RUN_STATE_BLOCKED
        result["error"] = str(exc)

    # 6. Build draft subject (Re: prefix)
    draft_subject = subject or "(no subject)"
    if not draft_subject.lower().startswith("re:"):
        draft_subject = f"Re: {draft_subject}"
    result["draft_subject"] = draft_subject

    return result
