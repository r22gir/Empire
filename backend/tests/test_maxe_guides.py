"""Max-e chat guides + Rafael alerts never leave Juan's WhatsApp. Temp dirs only."""
from __future__ import annotations


def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "juan-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "juan-phone-id")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "juan-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "juan-verify")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "573001112233")


def test_chat_tools_confirm_and_never_echo_secrets(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.max.tool_executor import execute_tool

    listed = execute_tool({"tool": "list_companies", "params": {}}, founder=True)
    assert listed.success is True
    slugs = [row["slug"] for row in listed.result["companies"]]
    assert "amp" in slugs

    preview = execute_tool({
        "tool": "save_company",
        "params": {"name": "Taller Norte", "industry": "cursos"},
    }, founder=True)
    assert preview.success is True
    assert preview.result["needs_confirmation"] is True

    saved = execute_tool({
        "tool": "save_company",
        "params": {"name": "Taller Norte", "industry": "cursos", "confirm": True},
    }, founder=True)
    assert saved.success is True
    assert saved.result["ok"] is True

    first = execute_tool({"tool": "company_setup_guide", "params": {}}, founder=True)
    assert first.result["question"].startswith("¿Cómo se llama")
    assert first.result["done"] is False

    wa = execute_tool({"tool": "whatsapp_setup_guide", "params": {"step": "secure_screen"}}, founder=True)
    assert "/amp/whatsapp" in wa.result["setup_path"]
    assert wa.result["secrets_in_chat"] is False
    assert "juan-token" not in str(wa.result)

    refused = execute_tool({
        "tool": "whatsapp_setup_guide",
        "params": {"text": "EAA1234567890supersecrettokenvalue"},
    }, founder=True)
    assert refused.result["refused"] is True
    assert "EAA123" not in json_blob(refused.result)


def json_blob(value) -> str:
    import json

    return json.dumps(value)


def test_juan_whatsapp_never_sends_rafael_help_alert(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.family_help import notify_new_ticket
    from app.services.whatsapp_cloud import send_alert_text

    sent = []

    def boom(*_a, **_k):
        sent.append(True)
        raise AssertionError("Juan's WhatsApp must not send Rafael alerts")

    monkeypatch.setattr("app.services.whatsapp_cloud._graph_json", boom)
    result = send_alert_text("573009998877", "Juan pidió ayuda")
    assert result["sent"] is False
    assert result["reason"] == "family_number_not_for_rafael_alerts"
    assert sent == []

    notice = notify_new_ticket({
        "id": "t-1",
        "edition": "amp",
        "message": "no abre el chat",
        "request_type": "Arreglo",
        "attachments": [],
    })
    assert notice["whatsapp_alert"]["sent"] is False
    assert notice["whatsapp_alert"]["reason"] == "family_number_not_for_rafael_alerts"
