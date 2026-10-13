"""IMP-0004: recipient lock + founder voice send/approve.

Mandatory lock (Rafael, 2026-10-10): MAX may send email ONLY to
empirebox2026@gmail.com — no cc/bcc (incl. rafa22giraldo@gmail.com),
never to clients, from voice or any path. Enforced server-side.
"""
import pytest

FOUNDER = "empirebox2026@gmail.com"


# ── Guard unit tests ───────────────────────────────────────────────

def test_guard_allows_single_founder_address():
    from app.services.max.email_recipient_guard import validate_outbound_email
    assert validate_outbound_email(FOUNDER) == FOUNDER
    assert validate_outbound_email("  EmpireBox2026@GMAIL.COM  ") == FOUNDER
    assert validate_outbound_email("Founder <empirebox2026@gmail.com>") == FOUNDER


def test_guard_rejects_other_to_addresses():
    from app.services.max.email_recipient_guard import RecipientRejected, validate_outbound_email
    for bad in ("rafa22giraldo@gmail.com", "client@example.com", "someone@else.org"):
        with pytest.raises(RecipientRejected) as exc:
            validate_outbound_email(bad)
        assert FOUNDER in str(exc.value)
    with pytest.raises(RecipientRejected):
        validate_outbound_email("")


def test_guard_rejects_cc_bcc_reply_to_overrides():
    from app.services.max.email_recipient_guard import RecipientRejected, validate_outbound_email
    with pytest.raises(RecipientRejected) as exc:
        validate_outbound_email(FOUNDER, cc="rafa22giraldo@gmail.com")
    assert "cc" in str(exc.value).lower()
    with pytest.raises(RecipientRejected) as exc:
        validate_outbound_email(FOUNDER, bcc="client@example.com")
    assert "bcc" in str(exc.value).lower()
    with pytest.raises(RecipientRejected) as exc:
        validate_outbound_email(FOUNDER, reply_to="client@example.com")
    assert "reply-to" in str(exc.value).lower()


def test_guard_rejects_multiple_recipients():
    from app.services.max.email_recipient_guard import RecipientRejected, validate_outbound_email
    with pytest.raises(RecipientRejected):
        validate_outbound_email(f"{FOUNDER}, client@example.com")


# ── EmailService enforcement (server-side, all paths) ──────────────

def _configured_env(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "workroom@empirebox.store")


def test_email_service_blocks_client_address_before_provider(monkeypatch):
    from app.services.max.email_service import EmailService
    from app.services.max.unified_message_store import UnifiedMessageStore
    import tempfile, os
    tmp = tempfile.mkdtemp()
    store = UnifiedMessageStore(os.path.join(tmp, "u.db"))
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)
    _configured_env(monkeypatch)
    called = []
    monkeypatch.setattr("httpx.post", lambda *a, **k: called.append(True))
    svc = EmailService()
    with pytest.raises(ValueError) as exc:
        svc.send(to="client@example.com", subject="Hi", body_html="<p>Hi</p>")
    assert FOUNDER in str(exc.value)
    assert called == []


def test_email_service_blocks_cc_even_for_founder_address(monkeypatch):
    from app.services.max.email_service import EmailService
    _configured_env(monkeypatch)
    svc = EmailService()
    with pytest.raises(ValueError) as exc:
        svc.send(to=FOUNDER, subject="Hi", body_html="<p>Hi</p>", cc="rafa22giraldo@gmail.com")
    assert "cc" in str(exc.value).lower()


def test_email_service_sends_to_founder_address(monkeypatch):
    from app.services.max.email_service import EmailService
    from app.services.max.unified_message_store import UnifiedMessageStore
    import tempfile, os
    tmp = tempfile.mkdtemp()
    store = UnifiedMessageStore(os.path.join(tmp, "u.db"))
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)
    _configured_env(monkeypatch)

    class FakeResponse:
        status_code = 202
        text = ""
    monkeypatch.setattr("httpx.post", lambda *a, **k: FakeResponse())
    svc = EmailService()
    assert svc.send(to=FOUNDER, subject="Hi", body_html="<p>Hi</p>") is True


# ── tool_executor: send_email lock + approve founder bypass ────────

def test_tool_send_email_blocks_client_for_founder_and_non_founder():
    from app.services.max.tool_executor import _send_email
    for params in (
        {"to": "client@example.com", "subject": "Q", "body": "hi"},
        {"to": "client@example.com", "subject": "Q", "body": "hi", "_founder": True},
        {"to": FOUNDER, "subject": "Q", "body": "hi", "cc": "rafa22giraldo@gmail.com"},
    ):
        result = _send_email(dict(params))
        assert result.success is False
        assert FOUNDER in (result.error or "") or "cc" in (result.error or "").lower()


def test_tool_send_email_sends_to_founder_on_founder_session(monkeypatch):
    from app.services.max import tool_executor
    import app.services.max.email_service as email_service_mod

    class FakeSvc:
        is_configured = True
        def __init__(self):
            pass
        def send(self, **kwargs):
            assert kwargs["to"] == FOUNDER
            return True

    monkeypatch.setattr(email_service_mod, "EmailService", FakeSvc)
    result = tool_executor._send_email(
        {"to": FOUNDER, "subject": "Quote", "body": "<p>hi</p>", "_founder": True}
    )
    assert result.success is True
    assert result.result["sent_to"] == FOUNDER


def test_tool_send_quote_email_blocks_client_address():
    from app.services.max.tool_executor import _send_quote_email
    result = _send_quote_email({"quote_id": "Q-1", "to": "client@example.com"})
    assert result.success is False
    assert FOUNDER in (result.error or "")


def test_tool_approve_quote_denies_non_founder_without_pin(monkeypatch):
    from app.services.max import tool_executor
    import app.services.max.access_control as access_control
    monkeypatch.setattr(access_control, "FOUNDER_APPROVAL_PIN", "test-pin-123")
    result = tool_executor._approve_quote({"quote_id": "Q-1", "channel": "voice"})
    assert result.success is False
    assert "founder approval required" in (result.error or "")


def test_tool_approve_quote_founder_session_bypasses_pin_prompt(monkeypatch):
    from app.services.max import tool_executor
    import app.services.max.access_control as access_control
    import app.services.quote_service as quote_service
    monkeypatch.setattr(access_control, "FOUNDER_APPROVAL_PIN", "test-pin-123")
    seen = {}

    def fake_approve(quote_id, changed_by="founder", reason=None, founder_pin=None):
        seen["founder_pin"] = founder_pin
        return {"id": quote_id, "quote_number": "EST-2026-001", "status": "sent"}

    monkeypatch.setattr(quote_service, "approve_quote", fake_approve)
    result = tool_executor._approve_quote({"quote_id": "Q-1", "_founder": True})
    assert result.success is True
    assert result.result["status"] == "sent"
    # Server-side PIN forwarded without exposing it to the caller
    assert seen["founder_pin"] == "test-pin-123"


# ── voice_documents router ─────────────────────────────────────────

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_voice_send_email_non_founder_is_queued_not_sent(client):
    r = client.post(
        "/api/v1/voice/documents/send-email",
        json={"to": FOUNDER, "subject": "Hi", "body": "hi",
              "channel": "voice", "chat_id": "unknown"},
    )
    assert r.status_code == 403
    assert "queued for founder approval" in r.json()["detail"].lower()


def test_voice_send_email_founder_to_client_is_rejected(client):
    r = client.post(
        "/api/v1/voice/documents/send-email",
        json={"to": "client@example.com", "subject": "Quote", "body": "hi",
              "channel": "web_cc"},
    )
    assert r.status_code == 403
    assert FOUNDER in r.json()["detail"]


def test_voice_send_email_founder_to_founder_sends(monkeypatch, client):
    import app.services.max.email_service as email_service_mod

    class FakeSvc:
        is_configured = True
        def send(self, **kwargs):
            assert kwargs["to"] == FOUNDER
            return True

    monkeypatch.setattr(email_service_mod, "EmailService", FakeSvc)
    r = client.post(
        "/api/v1/voice/documents/send-email",
        json={"to": FOUNDER, "subject": "Quote", "body": "<p>hi</p>",
              "channel": "web_cc"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "sent"


def test_voice_approve_quote_non_founder_is_queued(client):
    r = client.post(
        "/api/v1/voice/documents/approve-quote/Q-1",
        json={"channel": "voice", "chat_id": "unknown"},
    )
    assert r.status_code == 403
    assert "queued for founder approval" in r.json()["detail"].lower()


def test_voice_approval_queue_is_read_only(monkeypatch, client):
    import app.services.quote_service as quote_service
    monkeypatch.setattr(
        quote_service, "list_quotes_awaiting_review", lambda business_unit=None: {"quotes": []}
    )
    r = client.get("/api/v1/voice/documents/approval-queue")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
