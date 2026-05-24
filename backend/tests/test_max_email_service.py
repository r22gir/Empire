from pathlib import Path
from email import message_from_string
from email.header import decode_header, make_header
from email.utils import parseaddr

from app.services.max.capability_loader import generate_capability_prompt
from app.services.max.email_service import EmailService
from app.services.max.unified_message_store import UnifiedMessageStore


class FakeResponse:
    status_code = 202
    text = ""


def test_max_email_service_uses_sendgrid_http_without_sdk(monkeypatch, tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)
    sent = {}

    def fake_post(url, headers, json, timeout):
        sent["url"] = url
        sent["headers"] = headers
        sent["json"] = json
        sent["timeout"] = timeout
        return FakeResponse()

    attachment = tmp_path / "proof.txt"
    attachment.write_text("proof")

    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "max@empirebox.store")
    monkeypatch.setattr("httpx.post", fake_post)

    svc = EmailService()
    assert svc.send(
        to="founder@example.com",
        subject="Audit",
        body_html="<p>Body</p>",
        attachments=[str(attachment)],
        cc="copy@example.com",
    ) is True

    assert sent["url"] == "https://api.sendgrid.com/v3/mail/send"
    assert sent["headers"]["Authorization"] == "Bearer SG.test"
    assert sent["json"]["from"]["email"] == "max@empirebox.store"
    assert sent["json"]["personalizations"][0]["to"][0]["email"] == "founder@example.com"
    assert sent["json"]["personalizations"][0]["cc"][0]["email"] == "copy@example.com"
    assert sent["json"]["attachments"][0]["filename"] == Path(attachment).name


def test_capability_prompt_does_not_overclaim_inbox_access():
    prompt = generate_capability_prompt("web_cc")

    assert "max@empirebox.store" in prompt
    assert "Do not claim max@empirebox.store inbox access unless check_email" in prompt
    assert "not a verified MAX auto-reply loop" in prompt
    assert "Telegram is configured/partial until a live send/receive test passes" in prompt
    assert "Hermes email is not implemented" in prompt
    assert "Verified working. Returns real emails" not in prompt


class FakeSMTPServer:
    """Fake SMTP to capture _send_smtp message construction without sending."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.sent = []

    def ehlo(self):
        pass

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def sendmail(self, from_addr, to_addrs, msg_str):
        self.sent.append({"from": from_addr, "to": to_addrs, "msg": msg_str})

    def quit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _decoded_address(msg_str: str, header_name: str) -> tuple[str, str]:
    msg = message_from_string(msg_str)
    header_value = msg[header_name]
    assert header_value
    decoded = str(make_header(decode_header(header_value)))
    return parseaddr(decoded)


def test_smtp_uses_smtp_from_when_set(monkeypatch, tmp_path):
    """SMTP From header uses SMTP_FROM when configured, not SMTP_USER."""
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "empirebox2026@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-app-password")
    monkeypatch.setenv("SMTP_FROM", "max@empirebox.store")
    monkeypatch.setenv("SMTP_FROM_NAME", "MAX — Empire AI")
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

    sent_records = []

    class FakeSMTPServer:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def sendmail(self, from_addr, to_addrs, msg_str):
            sent_records.append({"from": from_addr, "to": to_addrs, "msg": msg_str})

        def quit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            self._server = FakeSMTPServer(*args, **kwargs)

        def __enter__(self):
            return self._server

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    svc = EmailService()
    svc.send(to="founder@example.com", subject="Test", body_html="<p>Hi</p>")

    assert len(sent_records) == 1
    assert sent_records[0]["from"] == "max@empirebox.store"
    assert sent_records[0]["to"] == ["founder@example.com"]
    from_name, from_addr = _decoded_address(sent_records[0]["msg"], "From")
    assert from_name == "MAX — Empire AI"
    assert from_addr == "max@empirebox.store"


def test_smtp_reply_to_header_when_configured(monkeypatch, tmp_path):
    """SMTP Reply-To header is included when SMTP_REPLY_TO is set."""
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "empirebox2026@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-password")
    monkeypatch.setenv("SMTP_FROM", "max@empirebox.store")
    monkeypatch.setenv("SMTP_FROM_NAME", "MAX — Empire AI")
    monkeypatch.setenv("SMTP_REPLY_TO", "max@empirebox.store")
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

    sent_records = []

    class FakeSMTPServer:
        def __init__(self, *args, **kwargs):
            pass

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, *args):
            pass

        def sendmail(self, from_addr, to_addrs, msg_str):
            sent_records.append(msg_str)

        def quit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            self._server = FakeSMTPServer(*args, **kwargs)

        def __enter__(self):
            return self._server

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    svc = EmailService()
    svc.send(to="founder@example.com", subject="MAX Test", body_html="<p>Test body</p>")

    assert len(sent_records) == 1
    msg = sent_records[0]
    from_name, from_addr = _decoded_address(msg, "From")
    assert from_name == "MAX — Empire AI"
    assert from_addr == "max@empirebox.store"
    reply_name, reply_addr = _decoded_address(msg, "Reply-To")
    assert reply_name == ""
    assert reply_addr == "max@empirebox.store"


def test_email_service_rejects_empty_body_before_send(monkeypatch, tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "empirebox2026@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-password")
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

    svc = EmailService()
    try:
        svc.send(to="founder@example.com", subject="Empty", body_html="   ")
    except ValueError as exc:
        assert "Email body is empty" in str(exc)
    else:
        raise AssertionError("empty email body should fail before send")


def test_email_service_rejects_missing_attachment_before_send(monkeypatch, tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "empirebox2026@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-password")
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

    svc = EmailService()
    try:
        svc.send(
            to="founder@example.com",
            subject="Missing attachment",
            body_html="<p>Body</p>",
            attachments=[str(tmp_path / "missing.pdf")],
        )
    except FileNotFoundError as exc:
        assert "Email attachment not found" in str(exc)
    else:
        raise AssertionError("missing attachment should fail before send")


def test_no_secrets_in_status_check(monkeypatch, tmp_path):
    """EmailService.is_configured reveals no secret values."""
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    monkeypatch.setenv("SMTP_USER", "empirebox2026@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "super-secret-app-password")
    monkeypatch.setenv("SMTP_FROM", "max@empirebox.store")
    monkeypatch.setenv("SMTP_FROM_NAME", "MAX — Empire AI")
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.very-secret-key")
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

    svc = EmailService()
    # is_configured should be True without exposing any values in repr
    assert svc.is_configured is True
    # Password field value does not appear in repr string
    repr_str = repr(svc)
    assert "super-secret-app-password" not in repr_str
    assert "SG.very-secret-key" not in repr_str
