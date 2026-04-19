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

    # Gmail OAuth is verified working — MAX can now truthfully describe inbox access
    assert "max@empirebox.store" in prompt  # MAX mentions max@ inbox correctly
    assert "Gmail OAuth" in prompt or "gmail" in prompt.lower()  # references the OAuth read path
    # Does NOT overclaim: no "unless" caveat implying Gmail is blocked
    assert "unless the check_email tool or /max/gmail/inbox returns success" not in prompt
