from pathlib import Path

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
    # From header is RFC 2047 encoded; check decoded content contains the alias
    import email.header
    msg = sent_records[0]["msg"]
    from_line = msg.split("From:")[1].split("\n")[0]
    from_decoded = email.header.decode_header(from_line.strip())[0]
    from_text = from_decoded[0]
    if isinstance(from_text, bytes):
        from_text = from_text.decode("utf-8")
    assert "max@empirebox.store" in from_text
    assert "MAX" in from_text


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
    # Reply-To header must be present
    assert "Reply-To:" in msg
    reply_to_line = msg.split("Reply-To:")[1].split("\n")[0]
    assert "max@empirebox.store" in reply_to_line
    # From header should use alias (RFC 2047 encoded)
    import email.header
    from_line = msg.split("From:")[1].split("\n")[0]
    from_decoded = email.header.decode_header(from_line.strip())[0]
    from_text = from_decoded[0]
    if isinstance(from_text, bytes):
        from_text = from_text.decode("utf-8")
    assert "max@empirebox.store" in from_text


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
