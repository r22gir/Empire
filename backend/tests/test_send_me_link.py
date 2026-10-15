"""Family send_me_link — owner allowlist from env, mocked sends only.

Fake numbers only. Never live WhatsApp, email, or production data writes.
Studio send_me_this_link must stay unregistered.
"""
from __future__ import annotations

import hashlib
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
FAKE_FOUNDER_EMAIL = "founder.internal@example.com"
FAKE_AMP_OWNER_EMAIL = "amp.env-owner@example.com"
FAKE_DENIED_EMAIL = "studio.denied@example.com"
FAKE_DENIED_EMAIL_2 = "founder.denied@example.com"
FAKE_DENIED_PHONE_10 = "5550100999"
FAKE_DENIED_PHONE_11 = "15550100999"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _patch_studio_hashes(monkeypatch):
    monkeypatch.setattr(
        sml,
        "STUDIO_CONTACT_HASHES",
        frozenset(
            {
                _sha(FAKE_DENIED_EMAIL),
                _sha(FAKE_DENIED_EMAIL_2),
                _sha(FAKE_DENIED_PHONE_10),
                _sha(FAKE_DENIED_PHONE_11),
            }
        ),
    )


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
    monkeypatch.setattr(sml, "whatsapp_cloud_ready", lambda: True)
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


def test_whatsapp_owner_numbers_is_not_a_fallback(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.delenv("EDITION_OWNER_WHATSAPP", raising=False)
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    gate = sml.authorize_recipient("whatsapp", "me")
    assert gate["authorized"] is False
    assert "WhatsApp configurado" in (gate.get("error") or "")


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


def test_refuses_founder_amp_owner_and_deny_env_as_owner_config(tmp_path, monkeypatch):
    """EDITION_OWNER_* equal to FOUNDER_EMAIL / AMP_OWNER_EMAIL / EDITION_DENY_* is refused.

    Family editions do not load business.json, so denial cannot use business_phone.
    """
    _amp_env(monkeypatch, tmp_path)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)
    monkeypatch.setenv("FOUNDER_EMAIL", FAKE_FOUNDER_EMAIL)
    monkeypatch.setenv("AMP_OWNER_EMAIL", FAKE_AMP_OWNER_EMAIL)
    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_SIBLING_EMAIL)
    monkeypatch.setenv("EDITION_DENY_WHATSAPP", FAKE_SIBLING_WA)

    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_FOUNDER_EMAIL)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_OWNER_WA)
    mail = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": "me"})
    assert not mail["success"]
    assert "solo te puedo mandar" in (mail.get("error") or "")
    assert "correo configurado" not in (mail.get("error") or "")

    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_SIBLING_WA)
    wa = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": "me"})
    assert not wa["success"]
    assert "solo te puedo mandar" in (wa.get("error") or "")
    assert "WhatsApp configurado" not in (wa.get("error") or "")

    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_AMP_OWNER_EMAIL)
    alt = sml.authorize_recipient("email", "me")
    assert alt["authorized"] is False
    assert "solo te puedo mandar" in (alt.get("error") or "")

    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_SIBLING_EMAIL)
    deny = sml.authorize_recipient("email", "me")
    assert deny["authorized"] is False
    assert "solo te puedo mandar" in (deny.get("error") or "")


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
    assert "solo te puedo mandar" in (mail.get("error") or "")
    assert "solo te puedo mandar" in (wa.get("error") or "")


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


def test_email_send_passes_empty_cc(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
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


def test_whatsapp_missing_cloud_keys_offers_email(amp, monkeypatch):
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


def test_spanish_send_triggers_and_via(amp):
    assert sml.asked_to_send("puedes enviarme el enlace")
    assert sml.asked_to_send("¿me puedes mandar el link?")
    assert sml.asked_to_send("envíame esto")
    assert sml.asked_to_send("mándame el dibujo")
    assert sml.asked_to_send("mándalo por WhatsApp")
    assert sml.asked_to_send("pásame el enlace")
    assert sml.asked_to_send("pásalo")
    assert sml.asked_to_send("mandarlo ahora")
    assert sml.asked_to_send("mándamelo")
    assert sml.asked_to_send("envíamelo")
    assert sml.asked_to_send("pásamelo")
    assert sml.asked_to_send("me lo envías")
    assert sml.asked_to_send("me lo pasas")
    assert sml.asked_to_send("me lo mandas")
    assert sml.infer_via("mándame el enlace") == "whatsapp"
    assert sml.infer_via("envíame el enlace a mi correo") == "email"
    assert sml.infer_via("mándamelo al correo") == "email"
    assert sml.infer_via("me lo envías al correo") == "email"
    assert sml.infer_via("send it to my email") == "email"
    assert sml.infer_via("can you send me this link") == "whatsapp"


def test_asked_to_send_ignores_model_caption_and_subject(amp):
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
        user_text="can you send me this link by email",
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


def test_family_default_email_cc_is_empty(amp):
    from app.services.max.tool_executor import DEFAULT_EMAIL_CC, default_email_cc
    assert default_email_cc() == ()
    assert list(DEFAULT_EMAIL_CC) == []


def test_send_email_me_uses_edition_owner_and_no_cc(amp, monkeypatch):
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
    _amp_env(monkeypatch, tmp_path)
    from app.services.max.tool_executor import _send_email
    result = _send_email({"to": "me", "subject": "hola", "body": "link https://example.test/a"})
    assert not result.success
    assert "correo configurado" in (result.error or "")


def test_drawing_email_me_goes_to_edition_owner_no_cc(amp, monkeypatch, tmp_path):
    from app.services.max.tool_executor import _auto_email_pdf

    pdf = tmp_path / "drawing.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    captured = {}

    class _Svc:
        is_configured = True
        last_message_id = "<draw>"

        def send(self, **kwargs):
            captured.update(kwargs)
            return True

    monkeypatch.setattr("app.services.max.email_service.EmailService", _Svc)
    result = _auto_email_pdf(str(pdf), "me", "Bench")
    assert result["emailed"] is True
    assert captured.get("to") == FAKE_OWNER_EMAIL
    assert captured.get("cc") in (None, "", [])
    assert result.get("cc") is None
    assert result.get("sent_to") == FAKE_OWNER_EMAIL


def test_drawing_email_refuses_client_sibling_rafael_founder(amp, monkeypatch, tmp_path):
    from app.services.max.tool_executor import _auto_email_pdf

    pdf = tmp_path / "drawing.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("FOUNDER_EMAIL", FAKE_FOUNDER_EMAIL)
    monkeypatch.setenv("AMP_OWNER_EMAIL", FAKE_AMP_OWNER_EMAIL)
    monkeypatch.setattr(
        "app.services.max.email_service.EmailService.send",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("live send must not run")),
    )
    for to in (FAKE_CLIENT_EMAIL, FAKE_SIBLING_EMAIL, FAKE_FOUNDER_EMAIL, FAKE_AMP_OWNER_EMAIL, "Rafael"):
        result = _auto_email_pdf(str(pdf), to, "Bench")
        assert result["emailed"] is False, to
        assert "solo te puedo mandar" in (result.get("error") or ""), to
        assert result.get("cc") is None


def test_send_quote_email_family_allows_only_edition_owner(amp, monkeypatch, tmp_path):
    from app.services.max.tool_executor import _send_quote_email

    pdf = tmp_path / "quote.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    captured = {}

    class _Svc:
        is_configured = True
        last_message_id = "<quote>"

        def send(self, **kwargs):
            captured.update(kwargs)
            return True

    monkeypatch.setenv("FOUNDER_EMAIL", FAKE_FOUNDER_EMAIL)
    monkeypatch.setattr(
        "app.services.quote_service.resolve_quote",
        lambda qid: {"id": qid, "quote_number": "EST-1", "customer_name": "A", "total": 1},
    )
    def _fake_run_async(coro):
        if hasattr(coro, "close"):
            coro.close()
        return str(pdf)

    monkeypatch.setattr("app.services.max.tool_executor._run_async", _fake_run_async)
    monkeypatch.setattr("app.services.max.tool_executor.dp.quote_pdf_dir", lambda: tmp_path)
    monkeypatch.setattr("app.services.max.email_service.EmailService", _Svc)

    ok = _send_quote_email({"quote_id": "q-1", "to": "me"})
    assert ok.success, ok.error
    assert captured.get("to") == FAKE_OWNER_EMAIL
    assert captured.get("cc") in (None, "", [])
    assert ok.result.get("cc") is None

    captured.clear()
    bad = _send_quote_email({"quote_id": "q-1", "to": FAKE_FOUNDER_EMAIL})
    assert not bad.success
    assert "solo te puedo mandar" in (bad.error or "")
    assert not captured

    client = _send_quote_email({"quote_id": "q-1", "to": FAKE_CLIENT_EMAIL})
    assert not client.success
    assert "solo te puedo mandar" in (client.error or "")


def test_studio_contact_hash_set_is_opaque():
    """Production hashes are opaque SHA-256 hex. No decodable contacts in tests."""
    hashes = sml.STUDIO_CONTACT_HASHES
    assert len(hashes) == 4
    for item in hashes:
        assert isinstance(item, str)
        assert len(item) == 64
        assert all(c in "0123456789abcdef" for c in item)
    for fake in (
        FAKE_OWNER_EMAIL,
        FAKE_OWNER_EMAIL_2,
        FAKE_SIBLING_EMAIL,
        FAKE_DENIED_EMAIL,
        FAKE_DENIED_EMAIL_2,
        FAKE_DENIED_PHONE_10,
        FAKE_DENIED_PHONE_11,
    ):
        assert _sha(fake) not in hashes


def test_studio_contact_hash_set_matches_fake_forms(monkeypatch):
    """Hash set matches SHA-256 of fake example.com emails and fake phones."""
    _patch_studio_hashes(monkeypatch)
    computed = {
        _sha(item)
        for item in (
            FAKE_DENIED_EMAIL,
            FAKE_DENIED_EMAIL_2,
            FAKE_DENIED_PHONE_10,
            FAKE_DENIED_PHONE_11,
        )
    }
    assert sml.STUDIO_CONTACT_HASHES == computed


def test_hashed_studio_owner_and_recipients_are_refused(tmp_path, monkeypatch):
    """FOUNDER_EMAIL unset: hashed Studio email/phone still cannot be owner or recipient."""
    _amp_env(monkeypatch, tmp_path)
    _patch_studio_hashes(monkeypatch)
    monkeypatch.setattr(sml, "_deliver_email", _boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", _boom)

    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_OWNER_WA)
    for owner_email in (FAKE_DENIED_EMAIL, FAKE_DENIED_EMAIL_2):
        monkeypatch.setenv("EDITION_OWNER_EMAIL", owner_email)
        mail = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": "me"})
        assert not mail["success"], owner_email
        assert "solo te puedo mandar" in (mail.get("error") or "")

    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    for owner_wa in (FAKE_DENIED_PHONE_10, FAKE_DENIED_PHONE_11, f"+1{FAKE_DENIED_PHONE_10}"):
        monkeypatch.setenv("EDITION_OWNER_WHATSAPP", owner_wa)
        wa = sml.send_me_link({"url": "https://example.test/a", "via": "whatsapp", "to": "me"})
        assert not wa["success"], owner_wa
        assert "solo te puedo mandar" in (wa.get("error") or "")

    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", FAKE_OWNER_WA)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)
    for to in (FAKE_DENIED_EMAIL, FAKE_DENIED_EMAIL_2):
        gate = sml.authorize_recipient("email", to)
        assert gate["authorized"] is False, to
        assert "solo te puedo mandar" in (gate.get("error") or "")
        out = sml.send_me_link({"url": "https://example.test/a", "via": "email", "to": to})
        assert not out["success"], to
    for to in (FAKE_DENIED_PHONE_10, FAKE_DENIED_PHONE_11):
        gate = sml.authorize_recipient("whatsapp", to)
        assert gate["authorized"] is False, to
        assert "solo te puedo mandar" in (gate.get("error") or "")


def test_hashed_studio_blocked_on_send_email_drawing_and_quote(amp, monkeypatch, tmp_path):
    from app.services.max.tool_executor import _auto_email_pdf, _send_email, _send_quote_email

    _patch_studio_hashes(monkeypatch)
    studio_email = FAKE_DENIED_EMAIL
    other_studio_email = FAKE_DENIED_EMAIL_2
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
    monkeypatch.delenv("AMP_OWNER_EMAIL", raising=False)

    mail = _send_email({"to": studio_email, "subject": "hola", "body": "link https://example.test/a"})
    assert not mail.success
    assert "solo te puedo mandar" in (mail.error or "")

    monkeypatch.setenv("EDITION_OWNER_EMAIL", studio_email)
    me_mail = _send_email({"to": "me", "subject": "hola", "body": "link https://example.test/a"})
    assert not me_mail.success
    assert "solo te puedo mandar" in (me_mail.error or "")
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER_EMAIL)

    pdf = tmp_path / "drawing.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "app.services.max.email_service.EmailService.send",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("live send must not run")),
    )
    for to in (studio_email, other_studio_email):
        drawn = _auto_email_pdf(str(pdf), to, "Bench")
        assert drawn["emailed"] is False, to
        assert "solo te puedo mandar" in (drawn.get("error") or ""), to

    quote_pdf = tmp_path / "quote.pdf"
    quote_pdf.write_bytes(b"%PDF-1.4\n")

    def _fake_run_async(coro):
        if hasattr(coro, "close"):
            coro.close()
        return str(quote_pdf)

    monkeypatch.setattr(
        "app.services.quote_service.resolve_quote",
        lambda qid: {"id": qid, "quote_number": "EST-1", "customer_name": "A", "total": 1},
    )
    monkeypatch.setattr("app.services.max.tool_executor._run_async", _fake_run_async)
    monkeypatch.setattr("app.services.max.tool_executor.dp.quote_pdf_dir", lambda: tmp_path)
    quoted = _send_quote_email({"quote_id": "q-1", "to": studio_email})
    assert not quoted.success
    assert "solo te puedo mandar" in (quoted.error or "")
