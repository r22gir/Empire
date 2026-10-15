"""Family send_me_link — owner allowlist from env, mocked sends only.

Fake numbers only. Never live WhatsApp, email, or production data writes.
Studio send_me_this_link must stay unregistered.
"""
from __future__ import annotations

import os

import pytest

from app.services.max import send_me_link as sml


FAKE_OWNER_WA = "573002223344"
FAKE_OWNER_EMAIL = "camilo.owner@example.com"
FAKE_OWNER_EMAIL_2 = "camilo.work@example.com"
FAKE_SIBLING_WA = "573001112233"
FAKE_SIBLING_EMAIL = "juan.owner@example.com"
FAKE_CLIENT_EMAIL = "client@example.com"
FAKE_CLIENT_WA = "15551234999"
FAKE_FOUNDER_EMAIL = "founder.internal@example.com"
FAKE_AMP_OWNER_EMAIL = "amp.env-owner@example.com"
FAKE_BUSINESS_PHONE = "15557000000"


def _maxine_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine")
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
def maxine(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", f"{FAKE_OWNER_EMAIL},{FAKE_OWNER_EMAIL_2}")
    monkeypatch.setenv("EDITION_DENY_WHATSAPP", FAKE_SIBLING_WA)
    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_SIBLING_EMAIL)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    monkeypatch.setattr(sml, "whatsapp_cloud_ready", lambda: True)
    yield tmp_path


def test_maxine_greeting_is_quiubo_without_juan(maxine):
    from app.edition import greeting

    es = greeting("es")
    assert es.startswith("¡Quiubo manito!")
    assert "Juan" not in es


def test_studio_send_me_this_link_is_absent(maxine):
    from app.services.max.tool_executor import TOOL_REGISTRY
    from app.services.max import voice_live as vl

    assert "send_me_this_link" not in TOOL_REGISTRY
    assert "send_me_this_link" not in vl.voice_tool_allowlist()
    assert "send_me_this_link" in vl.VOICE_DENIED_EXAMPLES
    refused = vl.run_voice_tool("send_me_this_link", {"query": "https://x.example/a", "to": "me"})
    assert refused["success"] is False


def test_family_send_me_link_is_registered_when_maxine(maxine):
    from app.services.max.tool_executor import TOOL_REGISTRY
    from app.services.max import voice_live as vl

    assert "send_me_link" in TOOL_REGISTRY
    assert "send_me_link" in vl.voice_tool_allowlist()


def test_sends_to_configured_owner_email(maxine, monkeypatch):
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


def test_second_owner_email_in_comma_list_is_allowed(maxine, monkeypatch):
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


def test_sends_to_configured_owner_whatsapp(maxine, monkeypatch):
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


def test_whatsapp_owner_numbers_is_not_a_fallback(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.delenv("EDITION_OWNER_WHATSAPP", raising=False)
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    gate = sml.authorize_recipient("whatsapp", "me")
    assert gate["authorized"] is False
    assert "WhatsApp configurado" in (gate.get("error") or "")


def test_refuses_when_owner_config_missing(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    mail = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": "me"})
    assert not mail["success"]
    assert "correo configurado" in (mail.get("error") or "")
    wa = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": "me"})
    assert not wa["success"]
    assert "WhatsApp configurado" in (wa.get("error") or "")


def test_refuses_founder_amp_owner_and_business_phone_as_owner_config(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    monkeypatch.setattr(sml, "studio_business_phone", lambda: FAKE_BUSINESS_PHONE)
    monkeypatch.setenv("FOUNDER_EMAIL", FAKE_FOUNDER_EMAIL)
    monkeypatch.setenv("AMP_OWNER_EMAIL", FAKE_AMP_OWNER_EMAIL)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_FOUNDER_EMAIL)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_BUSINESS_PHONE)
    mail = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": "me"})
    assert not mail["success"]
    assert "correo configurado" in (mail.get("error") or "")
    wa = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": "me"})
    assert not wa["success"]
    assert "WhatsApp configurado" in (wa.get("error") or "")

    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_AMP_OWNER_EMAIL)
    alt = sml.authorize_recipient("email", "me")
    assert alt["authorized"] is False


def test_ignores_amp_owner_email_and_founder_email(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setenv("AMP_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    monkeypatch.setenv("FOUNDER_EMAIL", FAKE_OWNER_EMAIL)
    monkeypatch.delenv("EDITION_OWNER_EMAIL", raising=False)
    assert sml.owner_email() == ""
    gate = sml.authorize_recipient("email", "me")
    assert gate["authorized"] is False
    assert "correo configurado" in gate["error"]


def test_refuses_across_editions_sibling_owner(maxine, monkeypatch):
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    for to in (FAKE_SIBLING_EMAIL, FAKE_SIBLING_WA, "Juan", "Juan Diego Giraldo"):
        mail = sml.authorize_recipient("email", to)
        wa = sml.authorize_recipient("whatsapp", to)
        assert mail["authorized"] is False, to
        assert wa["authorized"] is False, to
        out = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": to})
        assert not out["success"]


def test_sibling_value_as_owner_config_is_refused(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
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


def test_refuses_client_and_does_not_send(maxine, monkeypatch):
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


def test_email_send_passes_empty_cc(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    captured = {}

    def fake_send(self, **kwargs):
        captured.update(kwargs)
        self.last_message_id = "<no-cc>"
        return True

    monkeypatch.setattr(sml, "_refuse_live_send", lambda *_a, **_k: None)
    monkeypatch.setattr("app.services.max.email_service.EmailService.send", fake_send)
    out = sml.send_me_link({
        "url": "https://example.test/agenda",
        "via": "email",
        "to": "me",
    })
    assert out["success"], out.get("error")
    assert captured.get("to") == FAKE_OWNER_EMAIL
    assert captured.get("cc") in (None, "", [])
    assert out["result"]["cc"] is None


def test_whatsapp_missing_cloud_keys_offers_email(maxine, monkeypatch):
    monkeypatch.setattr(sml, "whatsapp_cloud_ready", lambda: False)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    out = sml.send_me_link({
        "url": "https://example.test/a",
        "via": "whatsapp",
        "to": "me",
    })
    assert not out["success"]
    err = out.get("error") or ""
    assert "WhatsApp no está configurado" in err
    assert "correo" in err.lower()


def test_spanish_send_triggers_and_via(maxine):
    assert sml.asked_to_send("puedes enviarme el enlace")
    assert sml.asked_to_send("¿me puedes mandar el link?")
    assert sml.asked_to_send("envíame esto")
    assert sml.asked_to_send("mándame el dibujo")
    assert sml.asked_to_send("mándalo por WhatsApp")
    assert sml.asked_to_send("pásame el enlace")
    assert sml.asked_to_send("pásalo")
    assert sml.asked_to_send("mandarlo ahora")
    assert sml.infer_via("mándame el enlace") == "whatsapp"
    assert sml.infer_via("envíame el enlace a mi correo") == "email"
    assert sml.infer_via("send it to my email") == "email"
    assert sml.infer_via("can you send me this link") == "whatsapp"


def test_asked_to_send_ignores_model_caption_and_subject(maxine):
    from app.services.max import voice_live as vl
    refused = vl.run_voice_tool(
        "send_me_link",
        {
            "url": "https://example.test/3d",
            "via": "email",
            "to": "me",
            "caption": "mándame este enlace",
            "subject": "envíame el link",
        },
        user_text="what's on today",
    )
    assert refused["success"] is False
    assert "not ask" in (refused.get("error") or "").lower() or "not sent" in (refused.get("error") or "").lower()


def test_voice_authorized_send_is_mocked(maxine, monkeypatch):
    from app.services.max import voice_live as vl
    sent = []

    def fake_email(payload, *, to, subject, body):
        sent.append({"payload": payload, "to": to})
        return {"message_id": "<voice-mock>"}

    monkeypatch.setattr(sml, "_deliver_email", fake_email)
    out = vl.run_voice_tool(
        "send_me_link",
        {"url": "https://example.test/3d", "via": "email", "to": "me"},
        user_text="can you send me this link by email",
    )
    assert out["success"], out.get("error")
    assert sent[0]["to"] == FAKE_OWNER_EMAIL


def test_voice_send_requires_ask(maxine, monkeypatch):
    from app.services.max import voice_live as vl
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    refused = vl.run_voice_tool(
        "send_me_link",
        {"url": "https://example.test/3d", "via": "email", "to": "me"},
    )
    assert refused["success"] is False
    assert "not ask" in (refused.get("error") or "").lower() or "not sent" in (refused.get("error") or "").lower()


def test_family_default_email_cc_is_empty(maxine):
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC, default_email_cc
    assert default_email_cc() == ()
    assert list(DEFAULT_EMAIL_CC) == []


def test_send_email_me_uses_edition_owner_and_no_cc(maxine, monkeypatch):
    from app.services.max.tool_executor import _send_email
    captured = {}

    class _Svc:
        last_message_id = "<fam>"
        is_configured = True

        def send(self, **kwargs):
            captured.update(kwargs)
            return True

    monkeypatch.setattr("app.services.max.email_service.EmailService", _Svc)
    result = _send_email({"to": "me", "subject": "hola", "body": "link https://example.test/a"})
    assert result.success, result.error
    assert captured.get("to") == FAKE_OWNER_EMAIL
    assert captured.get("cc") in (None, "", [])
    assert result.result["cc"] == []


def test_send_email_me_refuses_when_owner_email_unset(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    from app.services.max.tool_executor import _send_email
    result = _send_email({"to": "me", "subject": "hola", "body": "link https://example.test/a"})
    assert not result.success
    assert "correo configurado" in (result.error or "")
