"""Max-e resumes a pending WhatsApp guide only on explicit setup intent.

Temp EMPIRE_DATA_DIR only. No live Meta sends, no real contacts, no keys in chat.
Juan's facts stay under this instance root — never Rafael / Workroom.
Greetings and first-turn questions must not hijack the reply.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


WEBHOOK_QUESTION = "pega el webhook de ESTA instancia"
SECURE_QUESTION = "Ahora abre /amp/whatsapp"
OWN_ACCOUNT_QUESTION = "TU cuenta de Meta y TU número de WhatsApp Business"


def _env(monkeypatch, tmp_path, *, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e" if edition == "amp" else "Maxine")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-amp-jwt-secret")
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))
    for key in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_OWNER_NUMBERS",
    ):
        monkeypatch.delenv(key, raising=False)


def _seed_pending(tmp_path, *, key="pendiente_whatsapp_famp", step="webhook"):
    from app.services.edition_facts import upsert_fact

    return upsert_fact(
        key=key,
        text=f"WhatsApp guía pendiente en {step}",
        value=step,
        label="WhatsApp pendiente",
        source="test",
        visibility="confidential",
    )


def _client(monkeypatch):
    from app.services.max.ai_router import AIResponse, ai_router

    async def forbidden_chat(*_a, **_k):
        raise AssertionError("pending WhatsApp resume must not call the model")

    async def forbidden_stream(*_a, **_k):
        raise AssertionError("pending WhatsApp resume must not stream the model")
        yield "nope", "none"

    monkeypatch.setattr(ai_router, "chat", forbidden_chat)
    monkeypatch.setattr(ai_router, "chat_stream", forbidden_stream)

    from app.routers.max.router import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _stream_text(response) -> tuple[str, str]:
    text = []
    model = ""
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        event = json.loads(line[6:])
        if event.get("type") == "text" and event.get("content"):
            text.append(event["content"])
        if event.get("type") == "done":
            model = event.get("model_used") or ""
    return "".join(text), model


def _fact_step(tmp_path) -> str:
    from app.services.edition_facts import list_facts

    rows = [row for row in list_facts() if str(row.get("key") or "").startswith("pendiente_")]
    assert rows, f"expected pendiente fact under {tmp_path}"
    return str(rows[0].get("value") or "")


def test_explicit_setup_intent_resumes_saved_step_and_persists(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _seed_pending(tmp_path, step="webhook")
    sent = []

    def boom(*_a, **_k):
        sent.append(True)
        raise AssertionError("Juan's WhatsApp must not send")

    monkeypatch.setattr("app.services.whatsapp_cloud._graph_json", boom)
    client = _client(monkeypatch)

    payload = {
        "message": "cómo activo WhatsApp",
        "history": [],
        "conversation_id": "new-session-1",
        "channel": "dashboard",
        "usage_source": "web",
    }
    chat = client.post("/api/v1/max/chat", json=payload)
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["model_used"] == "whatsapp-setup-guide"
    assert WEBHOOK_QUESTION in body["response"]
    assert "/amp/whatsapp" in body["response"]
    assert "Nunca pegues el token" in body["response"]
    assert OWN_ACCOUNT_QUESTION not in body["response"]
    assert "EAA" not in body["response"]
    assert "WHATSAPP_ACCESS_TOKEN" not in body["response"]
    tools = body.get("tool_results") or []
    assert tools and tools[0]["tool"] == "whatsapp_setup_guide"
    assert tools[0]["result"]["step"] == "webhook"
    assert tools[0]["result"]["secrets_in_chat"] is False
    assert tools[0]["result"]["juan_number_not_rafael"] is True
    assert _fact_step(tmp_path) == "webhook"
    assert sent == []

    from app.routers.max.router import ChatRequest, _maybe_resume_whatsapp_guide

    skipped = _maybe_resume_whatsapp_guide(
        ChatRequest(
            message="Nueva sesión. ¿Cómo se llama mi empresa?",
            history=[],
            conversation_id="new-session-2",
        )
    )
    assert skipped is None
    assert _fact_step(tmp_path) == "webhook"


def test_stream_new_session_same_spanish_step(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _seed_pending(tmp_path, key="pendiente_whatsapp_famp", step="secure_screen")
    client = _client(monkeypatch)
    stream = client.post(
        "/api/v1/max/chat/stream",
        json={
            "message": "configurar WhatsApp",
            "history": [],
            "conversation_id": "new-session-stream",
            "channel": "dashboard",
            "usage_source": "web",
        },
    )
    assert stream.status_code == 200, stream.text
    text, model = _stream_text(stream)
    assert model == "whatsapp-setup-guide"
    assert SECURE_QUESTION in text
    assert "/amp/whatsapp" in text
    assert "Nunca los escribas en este chat" in text or "Nunca pegues el token" in text
    assert OWN_ACCOUNT_QUESTION not in text
    assert _fact_step(tmp_path) == "secure_screen"


def test_frontend_style_history_resumes_only_on_explicit_intent(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _seed_pending(tmp_path, step="developers")
    client = _client(monkeypatch)
    from app.routers.max.router import ChatRequest, _maybe_resume_whatsapp_guide

    skipped = _maybe_resume_whatsapp_guide(
        ChatRequest(
            message="empezamos",
            history=[
                {"role": "assistant", "content": "¡Hola! Soy **Max-e**, tu asistente de EmpireBox."},
                {"role": "user", "content": "empezamos"},
            ],
            conversation_id="ui-new-chat",
        )
    )
    assert skipped is None

    message = "conectar mi número de WhatsApp"
    chat = client.post(
        "/api/v1/max/chat",
        json={
            "message": message,
            "history": [
                {"role": "assistant", "content": "¡Hola! Soy **Max-e**, tu asistente de EmpireBox."},
                {"role": "user", "content": message},
            ],
            "conversation_id": "ui-whatsapp-intent",
            "channel": "dashboard",
            "usage_source": "web",
        },
    )
    assert chat.status_code == 200, chat.text
    assert "developers.facebook.com" in chat.json()["response"]
    assert _fact_step(tmp_path) == "developers"


def test_enabled_whatsapp_does_not_hijack_greeting(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "juan-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "juan-phone-id")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "juan-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "juan-verify")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "573001112233")
    _seed_pending(tmp_path, step="webhook")
    from app.services.max.quick_replies import greeting_reply

    from app.routers.max.router import ChatRequest, _maybe_resume_whatsapp_guide

    request = ChatRequest(message="hola", history=[], conversation_id="x")
    assert _maybe_resume_whatsapp_guide(request) is None
    text = greeting_reply()
    assert WEBHOOK_QUESTION not in text
    assert _fact_step(tmp_path) == "webhook"


def test_owner_greeting_is_not_the_whatsapp_guide(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _seed_pending(tmp_path, step="meta_business")
    from app.edition import greeting

    public = greeting("es", include_owner=False)
    assert "business.facebook.com" not in public
    owner = greeting("es", include_owner=True)
    assert owner.startswith("¡Quiubo manito!")
    assert "business.facebook.com" not in owner
    assert "/amp/whatsapp" not in owner
    assert OWN_ACCOUNT_QUESTION not in owner
    assert _fact_step(tmp_path) == "meta_business"


def test_tool_persists_step_and_refuses_keys(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _seed_pending(tmp_path, step="own_account")
    from app.services.maxe_guides import run_whatsapp_setup_guide, secret_refusal

    guide = run_whatsapp_setup_guide("system_user", persist=True)
    assert guide["step"] == "system_user"
    assert _fact_step(tmp_path) == "system_user"
    assert "/amp/whatsapp" in guide["message"]
    assert "token permanente" in guide["question"]
    refusal = secret_refusal()
    assert "/amp/whatsapp" in refusal
    facts = (tmp_path / "facts.json").read_text(encoding="utf-8")
    assert "juan-token" not in facts
    assert str(tmp_path) in str(Path(tmp_path / "facts.json").resolve())
    assert "empire-data" not in facts


def test_use_chat_does_not_open_new_session_on_edition_guide():
    hook = Path(__file__).resolve().parents[2].joinpath(
        "empire-command-center/app/hooks/useChat.ts"
    ).read_text(encoding="utf-8")
    assert "whatsapp_guide" not in hook
    assert "guideWelcomeRef" not in hook
