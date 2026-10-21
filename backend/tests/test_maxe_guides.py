"""Max-e chat guides + Rafael alerts never leave Juan's WhatsApp. Temp dirs only."""
from __future__ import annotations

import json


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


class _Result:
    def __init__(self, tool, success=True, result=None, error=None):
        self.tool = tool
        self.success = success
        self.result = result
        self.error = error


def _registry():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "tools_maxe_guides.py"
    spec = importlib.util.spec_from_file_location("tools_maxe_guides_isolated", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    register_tools = mod.register_tools

    tools = {}

    def tool(name):
        def deco(fn):
            tools[name] = fn
            return fn
        return deco

    register_tools(tool, _Result)
    return tools


def test_chat_tools_confirm_and_never_echo_secrets(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    tools = _registry()

    listed = tools["list_companies"]({})
    assert listed.success is True
    slugs = [row["slug"] for row in listed.result["companies"]]
    assert "amp" in slugs

    preview = tools["save_company"]({"name": "Taller Norte", "industry": "cursos"})
    assert preview.success is True
    assert preview.result["needs_confirmation"] is True

    saved = tools["save_company"]({"name": "Taller Norte", "industry": "cursos", "confirm": True})
    assert saved.success is True
    assert saved.result["ok"] is True

    first = tools["company_setup_guide"]({})
    assert first.result["question"].startswith("¿Cómo se llama")
    assert first.result["done"] is False

    wa = tools["whatsapp_setup_guide"]({"step": "secure_screen"})
    assert "/amp/whatsapp" in wa.result["setup_path"]
    assert wa.result["secrets_in_chat"] is False
    assert "juan-token" not in json.dumps(wa.result)

    refused = tools["whatsapp_setup_guide"]({"text": "EAA1234567890supersecrettokenvalue"})
    assert refused.result["refused"] is True
    assert "EAA123" not in json.dumps(refused.result)


def test_juan_whatsapp_never_sends_rafael_help_alert(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.whatsapp_cloud import refuse_rafael_alert_from_family_whatsapp, send_alert_text

    sent = []

    def boom(*_a, **_k):
        sent.append(True)
        raise AssertionError("Juan's WhatsApp must not send Rafael alerts")

    monkeypatch.setattr("app.services.whatsapp_cloud._graph_json", boom)
    result = send_alert_text("573009998877", "Juan pidió ayuda")
    assert result["sent"] is False
    assert result["reason"] == "family_number_not_for_rafael_alerts"
    assert sent == []

    refuse = refuse_rafael_alert_from_family_whatsapp()
    assert refuse["sent"] is False
    assert refuse["reason"] == "family_number_not_for_rafael_alerts"
    from app.services.family_help import notify_new_ticket

    notice = notify_new_ticket({
        "id": "t-1",
        "edition": "amp",
        "message": "no abre el chat",
        "request_type": "Arreglo",
        "attachments": [],
    })
    assert notice["whatsapp_alert"]["sent"] is False
    assert notice["whatsapp_alert"]["reason"] == "family_number_not_for_rafael_alerts"
