from pathlib import Path
import asyncio

from app.services.max.email_service import EmailService
from app.services.max.unified_message_store import UnifiedMessageStore


class FakeResponse:
    def __init__(self, status_code=202, text=""):
        self.status_code = status_code
        self.text = text


def test_successful_max_email_send_writes_unified_ledger_once(monkeypatch, tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    def fake_post(url, headers, json, timeout):
        return FakeResponse(202)

    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "max@empirebox.store")
    monkeypatch.setattr("httpx.post", fake_post)

    svc = EmailService()
    kwargs = {
        "to": "founder@example.com",
        "subject": "Ledger proof",
        "body_html": "<p>Ledger body</p>",
        "attachments": [],
        "cc": None,
    }

    assert svc.send(**kwargs) is True
    assert svc.send(**kwargs) is True

    rows = store.list_memory_bank(channel="email", limit=10)
    assert len(rows) == 1
    row = rows[0]
    assert row["channel"] == "email"
    assert row["direction"] == "outbound"
    assert row["role"] == "assistant"
    assert row["sender"] == "max@empirebox.store"
    assert row["recipient"] == "founder@example.com"
    assert row["subject"] == "Ledger proof"
    assert row["source_message_id"].startswith("outbound-email:")
    assert row["metadata"]["identifier_fallback"] == "conversation_id_from_outbound_email_hash"


def test_failed_max_email_send_does_not_write_unified_ledger(monkeypatch, tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    def fake_post(url, headers, json, timeout):
        return FakeResponse(500, "nope")

    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    monkeypatch.setattr("httpx.post", fake_post)

    svc = EmailService()
    try:
        svc.send(to="founder@example.com", subject="Failure", body_html="<p>No write</p>")
    except RuntimeError:
        pass

    assert store.list_memory_bank(channel="email", limit=10) == []


def test_outbound_email_channel_falls_back_when_registry_unavailable(monkeypatch, tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")

    def broken_registry(surface_key):
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr("app.services.max.operating_registry.get_surface_truth", broken_registry)

    inserted = store.add_outbound_email(
        recipient="founder@example.com",
        subject="Fallback channel",
        body_html="<p>Registry down</p>",
        sender="max@empirebox.store",
    )

    assert inserted is True
    rows = store.list_memory_bank(channel="email", limit=10)
    assert len(rows) == 1
    assert rows[0]["channel"] == "email"


def test_business_email_sender_success_writes_unified_ledger(monkeypatch, tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    def fake_post(url, headers, json, timeout):
        return FakeResponse(202)

    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "workroom@empirebox.store")
    monkeypatch.setattr("httpx.post", fake_post)

    from app.services.email import sender

    sent = asyncio.run(sender.send_email("client@example.com", "Business path", "<p>Invoice body</p>"))

    assert sent is True
    rows = store.list_memory_bank(channel="email", limit=10)
    assert len(rows) == 1
    assert rows[0]["channel"] == "email"
    assert rows[0]["sender"] == "workroom@empirebox.store"
    assert rows[0]["recipient"] == "client@example.com"
    assert rows[0]["metadata"]["service"] == "app.services.email.sender.send_email/sendgrid"
