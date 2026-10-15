"""Family send_me_link — owner allowlist from env, mocked sends only.

Fake numbers only. Never live WhatsApp, email, or production data writes.
Studio send_me_this_link must stay unregistered.
"""
from __future__ import annotations

import os

import pytest

from app.services.max import send_me_link as sml


FAKE_OWNER_WA = "573001112233"
FAKE_OWNER_EMAIL = "juan.owner@example.com"
FAKE_OWNER_EMAIL_2 = "juan.work@example.com"
FAKE_SIBLING_WA = "573009998888"
FAKE_SIBLING_EMAIL = "camilo.owner@example.com"
FAKE_CLIENT_EMAIL = "client@example.com"
FAKE_CLIENT_WA = "15551234999"
STUDIO_PHONE = "17032136484"
FOUNDER_EMAIL = "empirebox2026@gmail.com"
FOUNDER_ALT = "rafa22giraldo@gmail.com"


def _amp_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
    monkeypatch.delenv("AMP_OWNER_EMAIL", raising=False)
    monkeypatch.delenv("EDITION_OWNER_WHATSAPP", raising=False)
    monkeypatch.delenv("EDITION_OWNER_EMAIL", raising=False)
    monkeypatch.delenv("EDITION_DENY_WHATSAPP", raising=False)
    monkeypatch.delenv("EDITION_DENY_EMAIL", raising=False)
    monkeypatch.delenv("WHATSAPP_OWNER_NUMBERS", raising=False)


def _boom(*_a, **_k):
    raise AssertionError("live send must not run")


@pytest.fixture()
def amp(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", f"{FAKE_OWNER_EMAIL},{FAKE_OWNER_EMAIL_2}")
    monkeypatch.setenv("EDITION_DENY_WHATSAPP", FAKE_SIBLING_WA)
    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_SIBLING_EMAIL)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    yield tmp_path


def test_studio_send_me_this_link_is_absent(amp):
    from app.services.max.tool_executor import TOOL_REGISTRY
    from app.services.max import voice_live as vl

    assert "send_me_this_link" not in TOOL_REGISTRY
    assert "send_me_this_link" not in vl.voice_tool_allowlist()
    assert "send_me_this_link" in vl.VOICE_DENIED_EXAMPLES
    refused = vl.run_voice_tool("send_me_this_link", {"query": "https://x.example/a", "to": "me"})
    assert refused["success"] is False


def test_family_send_me_link_is_registered_when_amp(amp):
    from app.services.max.tool_executor import TOOL_REGISTRY
    from app.services.max import voice_live as vl

    assert "send_me_link" in TOOL_REGISTRY
    assert "send_me_link" in vl.voice_tool_allowlist()


def test_sends_to_configured_owner_email(amp, monkeypatch):
    sent = []

    def fake_email(payload, *, to, subject, body):
        sent.append({"payload": payload, "to": to, "subject": subject, "body": body})
        return {"message_id": "<mock>"}

    monkeypatch.setattr(sml, "_deliver_email", fake_email)
    out = sml.send_me_link({
        "url": "https://example.test/agenda",
        "via": "email",
        "to": "me",
    })
    assert out["success"], out.get("error")
    assert sent[0]["to"] == FAKE_OWNER_EMAIL
    assert out["result"]["sent_to"] == FAKE_OWNER_EMAIL


def test_second_owner_email_in_comma_list_is_allowed(amp, monkeypatch):
    sent = []
    monkeypatch.setattr(
        sml, "_deliver_email",
        lambda payload, *, to, subject, body: sent.append(to) or {"message_id": "<mock>"},
    )
    out = sml.send_me_link({
        "url": "https://example.test/doc",
        "via": "email",
        "to": FAKE_OWNER_EMAIL_2,
    })
    assert out["success"], out.get("error")
    assert sent == [FAKE_OWNER_EMAIL_2]


def test_sends_to_configured_owner_whatsapp(amp, monkeypatch):
    sent = []

    def fake_wa(payload, *, to, caption):
        sent.append({"payload": payload, "to": to, "caption": caption})
        return {"media_id": "MEDIA-MOCK"}

    monkeypatch.setattr(sml, "_deliver_whatsapp", fake_wa)
    out = sml.send_me_link({
        "query": "https://example.test/drawing",
        "via": "whatsapp",
        "to": "me",
    })
    assert out["success"], out.get("error")
    assert sent[0]["to"] == FAKE_OWNER_WA
    assert out["result"]["sent_to"] == "owner_whatsapp"


def test_whatsapp_owner_numbers_is_phone_fallback(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.delenv("EDITION_OWNER_WHATSAPP", raising=False)
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    gate = sml.authorize_recipient("whatsapp", "me")
    assert gate["authorized"] is True
    assert gate["to"] == FAKE_OWNER_WA


def test_refuses_when_owner_config_missing(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    mail = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": "me"})
    assert not mail["success"]
    assert "correo configurado" in (mail.get("error") or "")
    wa = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": "me"})
    assert not wa["success"]
    assert "WhatsApp configurado" in (wa.get("error") or "")


def test_refuses_founder_and_studio_denylist_as_owner_config(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FOUNDER_EMAIL)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", STUDIO_PHONE)
    mail = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": "me"})
    assert not mail["success"]
    assert "correo configurado" in (mail.get("error") or "")
    wa = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": "me"})
    assert not wa["success"]
    assert "WhatsApp configurado" in (wa.get("error") or "")

    monkeypatch.setenv("EDITION_OWNER_EMAIL", FOUNDER_ALT)
    alt = sml.authorize_recipient("email", "me")
    assert alt["authorized"] is False


def test_ignores_amp_owner_email_and_founder_email(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.setenv("AMP_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    monkeypatch.setenv("FOUNDER_EMAIL", FAKE_OWNER_EMAIL)
    monkeypatch.delenv("EDITION_OWNER_EMAIL", raising=False)
    assert sml.owner_email() == ""
    gate = sml.authorize_recipient("email", "me")
    assert gate["authorized"] is False
    assert "correo configurado" in gate["error"]


def test_refuses_across_editions_sibling_owner(amp, monkeypatch):
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    for to in (FAKE_SIBLING_EMAIL, FAKE_SIBLING_WA, "Camilo", "Camilo Giraldo"):
        mail = sml.authorize_recipient("email", to)
        wa = sml.authorize_recipient("whatsapp", to)
        assert mail["authorized"] is False, to
        assert wa["authorized"] is False, to
        out = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": to})
        assert not out["success"]


def test_sibling_value_as_owner_config_is_refused(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.setenv("EDITION_DENY_WHATSAPP", FAKE_SIBLING_WA)
    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_SIBLING_EMAIL)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_SIBLING_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_SIBLING_EMAIL)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    assert sml.owner_email() == ""
    assert sml.owner_whatsapp() == ""
    mail = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": "me"})
    wa = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": "me"})
    assert not mail["success"]
    assert not wa["success"]


def test_refuses_client_and_does_not_send(amp, monkeypatch):
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    out = sml.send_me_link({
        "url": "https://example.test/a",
        "via": "email",
        "to": FAKE_CLIENT_EMAIL,
    })
    assert not out["success"]
    wa = sml.send_me_link({
        "url": "https://example.test/a",
        "via": "whatsapp",
        "to": FAKE_CLIENT_WA,
    })
    assert not wa["success"]


def test_voice_authorized_send_is_mocked(amp, monkeypatch):
    from app.services.max import voice_live as vl
    sent = []

    def fake_email(payload, *, to, subject, body):
        sent.append({"payload": payload, "to": to})
        return {"message_id": "<voice-mock>"}

    monkeypatch.setattr(sml, "_deliver_email", fake_email)
    out = vl.run_voice_tool(
        "send_me_link",
        {"url": "https://example.test/3d", "via": "email", "to": "me"},
        user_text="can you send me this link",
    )
    assert out["success"], out.get("error")
    assert sent[0]["to"] == FAKE_OWNER_EMAIL


def test_voice_send_requires_ask(amp, monkeypatch):
    from app.services.max import voice_live as vl
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    refused = vl.run_voice_tool(
        "send_me_link",
        {"url": "https://example.test/3d", "via": "email", "to": "me"},
    )
    assert refused["success"] is False
    assert "not ask" in (refused.get("error") or "").lower() or "not sent" in (refused.get("error") or "").lower()
