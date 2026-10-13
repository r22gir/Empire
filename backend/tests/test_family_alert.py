"""Rafael-only family-help WhatsApp/SMS alerts. No live send."""
from __future__ import annotations

from pathlib import Path


def _family(monkeypatch, tmp_path, edition: str = "amp"):
    root = tmp_path / edition
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "100000")
    monkeypatch.delenv("FAMILY_HELP_INBOX_DIR", raising=False)
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    return root


def test_alerts_off_unless_env_true(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    from app.services.family_alert import alerts_enabled, notify_rafael_alert

    monkeypatch.delenv("FAMILY_ALERT_ENABLED", raising=False)
    assert alerts_enabled() is False
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "yes")
    assert alerts_enabled() is False
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "true")
    assert alerts_enabled() is True
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "false")
    result = notify_rafael_alert({"edition": "amp", "message": "hola", "request_type": "Ajuste"})
    assert result["status"] == "off"
    assert result["channel"] is None


def test_noop_without_phone_or_creds(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "true")
    monkeypatch.delenv("FAMILY_ALERT_PHONE", raising=False)
    from app.services.family_alert import notify_rafael_alert

    assert notify_rafael_alert({"edition": "amp", "message": "x"})["status"] == "no_phone"

    monkeypatch.setenv("FAMILY_ALERT_PHONE", "+57 300 555 0000")
    for name in (
        "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER",
    ):
        monkeypatch.delenv(name, raising=False)
    result = notify_rafael_alert({"edition": "amp", "message": "x", "request_type": "Arreglo"})
    assert result["status"] == "not_configured"


def test_never_sends_to_owner_numbers(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "true")
    monkeypatch.setenv("FAMILY_ALERT_PHONE", "573001112233")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "573001112233")
    from app.services.family_alert import destination_allowed, notify_rafael_alert

    assert destination_allowed("573001112233") is False
    result = notify_rafael_alert({"edition": "amp", "message": "no mandar a Juan"})
    assert result["status"] == "blocked_destination"


def test_message_bilingual_who_type_and_studio_link(monkeypatch):
    from app.services.family_alert import build_alert_text, studio_assist_url

    text = build_alert_text({
        "edition": "amp",
        "sender": "Juan",
        "message": "no funciona el historial de chats",
        "request_type": "Arreglo",
    })
    assert "Juan (Max-e)" in text
    assert "pidió ayuda" in text
    assert "asked for help" in text
    assert "historial" in text
    assert "arreglo" in text.lower()
    assert "fix" in text
    assert studio_assist_url() in text
    assert "/?screen=family-help" in text

    camilo = build_alert_text({
        "edition": "maxine",
        "message": "quisiera que el PDF abra",
        "request_type": "Ajuste",
    })
    assert "Camilo (Maxine)" in camilo
    assert "ajuste" in camilo.lower()
    assert "adjust" in camilo


def test_whatsapp_preferred_then_sms_fake(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "true")
    monkeypatch.setenv("FAMILY_ALERT_PHONE", "573009998877")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "555")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "573000000000")
    sent = []

    def _wa(to, text):
        sent.append(("wa", to, text))
        return {"sent": True, "id": "wamid.fake"}

    monkeypatch.setattr("app.services.family_alert.send_whatsapp", _wa)
    monkeypatch.setattr(
        "app.services.family_alert.send_sms",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("SMS must not run when WhatsApp sent")),
    )
    from app.services.family_alert import notify_rafael_alert

    result = notify_rafael_alert({
        "edition": "maxine",
        "message": "puedes agregar un botón",
        "request_type": "Crear",
    })
    assert result["status"] == "whatsapp"
    assert result["channel"] == "whatsapp"
    assert sent and sent[0][0] == "wa"
    assert sent[0][1] == "573009998877"
    assert "Camilo (Maxine)" in sent[0][2]
    assert "create" in sent[0][2]
    assert "/?screen=family-help" in sent[0][2]


def test_sms_fallback_when_whatsapp_off(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "true")
    monkeypatch.setenv("FAMILY_ALERT_PHONE", "573001234567")
    for name in (
        "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACfake")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15700000000")
    sent = []

    def _sms(to, text):
        sent.append((to, text))
        return {"sent": True}

    monkeypatch.setattr("app.services.family_alert.send_sms", _sms)
    from app.services.family_alert import notify_rafael_alert

    result = notify_rafael_alert({
        "edition": "amp",
        "message": "no abre el chat",
        "request_type": "Arreglo",
    })
    assert result["status"] == "sms"
    assert sent[0][0] == "573001234567"
    assert "Juan (Max-e)" in sent[0][1]


def test_create_ticket_calls_alert_alongside_email(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("FAMILY_ALERT_ENABLED", "true")
    monkeypatch.setenv("FAMILY_ALERT_PHONE", "573009991111")
    alerts = []

    async def _fake_email(*a, **k):
        return True

    def _alert(ticket):
        alerts.append(ticket["id"])
        return {"status": "whatsapp", "channel": "whatsapp"}

    monkeypatch.setattr("app.services.email.sender.send_email", _fake_email)
    monkeypatch.setattr("app.services.family_alert.notify_rafael_alert", _alert)
    from app.services.family_help import create_ticket, notify_new_ticket

    ticket = create_ticket(message="no funciona el PDF", notify=True, request_type="Arreglo")
    assert alerts == [ticket["id"]]
    again = notify_new_ticket(ticket)
    assert again.get("alert", {}).get("status") == "whatsapp"


def test_env_examples_document_family_alert_vars():
    root = Path(__file__).resolve().parents[2]
    for rel in (
        "backend/.env.example",
        "deploy/empire-amp.env.example",
        "deploy/empire-maxine.env.example",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert "FAMILY_ALERT_ENABLED" in text
        assert "FAMILY_ALERT_PHONE" in text
        assert "TWILIO_ACCOUNT_SID" in text
        assert "FAMILY_ALERT_ENABLED=true" in text
        assert "never" in text.lower()
