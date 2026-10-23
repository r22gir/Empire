"""WhatsApp setup guide fires only on explicit setup intent.

Covers amp (Max-e) and maxine. Temp EMPIRE_DATA_DIR only. No live Meta,
no keys in chat. Does not export EMPIRE_EDITION to the parent shell.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


OWN_ACCOUNT = "TU cuenta de Meta y TU número de WhatsApp Business"
WEBHOOK_QUESTION = "pega el webhook de ESTA instancia"

NORMAL_PROMPTS = (
    "Qué es el Workroom",
    "Quién es Rafael Giraldo",
    "Quién es Rafael Giraldo y cuáles son sus clientes",
    "Qué datos tiene la edición de Maxine",
    "hola",
    "Nueva sesión. ¿Cómo se llama mi empresa?",
    "Recuerda que mi empresa se llama Empresa Prueba.",
    "mándame esto por WhatsApp",
    "qué es WhatsApp",
)

INTENT_PROMPTS = (
    "cómo activo WhatsApp",
    "configurar WhatsApp",
    "conectar mi número de WhatsApp",
    "cómo configuro WhatsApp",
    "guía de WhatsApp",
    "how do I set up WhatsApp",
)


def _env(monkeypatch, tmp_path, edition: str):
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


def _seed_pending(tmp_path, *, edition: str, step: str = "own_account"):
    from app.services.edition_facts import upsert_fact

    key = "pendiente_whatsapp_famp" if edition == "amp" else "pendiente_whatsapp_maxine"
    return upsert_fact(
        key=key,
        text=f"WhatsApp guía pendiente en {step}",
        value=step,
        label="WhatsApp pendiente",
        source="test",
        visibility="confidential",
    )


def _client(monkeypatch):
    from app.services.max.ai_router import ai_router

    async def forbidden_chat(*_a, **_k):
        raise AssertionError("WhatsApp guide intercept must not call the model")

    async def forbidden_stream(*_a, **_k):
        raise AssertionError("WhatsApp guide intercept must not stream the model")
        yield "nope", "none"

    monkeypatch.setattr(ai_router, "chat", forbidden_chat)
    monkeypatch.setattr(ai_router, "chat_stream", forbidden_stream)

    from app.routers.max.router import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _chat(client, message: str, history=None):
    return client.post(
        "/api/v1/max/chat",
        json={
            "message": message,
            "history": list(history or []),
            "conversation_id": "intent-test",
            "channel": "web",
            "usage_source": "web",
        },
    )


def _is_guide(body: dict) -> bool:
    text = str(body.get("response") or "")
    model = str(body.get("model_used") or "")
    if model == "whatsapp-setup-guide":
        return True
    if OWN_ACCOUNT in text:
        return True
    if "Pantalla segura:" in text and "whatsapp" in text.lower():
        return True
    return False


@pytest.mark.parametrize("edition", ("amp", "maxine"))
@pytest.mark.parametrize("prompt", NORMAL_PROMPTS)
def test_normal_prompts_do_not_trigger_guide(monkeypatch, tmp_path, edition, prompt):
    _env(monkeypatch, tmp_path, edition)
    _seed_pending(tmp_path, edition=edition, step="own_account")
    from app.services.maxe_guides import is_whatsapp_setup_intent, maybe_resume_whatsapp_guide

    assert is_whatsapp_setup_intent(prompt) is False
    assert maybe_resume_whatsapp_guide(prompt, [], persist=False) is None

    from app.routers.max.router import ChatRequest, _maybe_resume_whatsapp_guide

    request = ChatRequest(message=prompt, history=[], conversation_id="x")
    assert _maybe_resume_whatsapp_guide(request) is None


@pytest.mark.parametrize("edition", ("amp", "maxine"))
@pytest.mark.parametrize("prompt", INTENT_PROMPTS)
def test_explicit_whatsapp_setup_prompts_trigger_guide(monkeypatch, tmp_path, edition, prompt):
    _env(monkeypatch, tmp_path, edition)
    _seed_pending(tmp_path, edition=edition, step="webhook")
    from app.services.maxe_guides import is_whatsapp_setup_intent, maybe_resume_whatsapp_guide, whatsapp_setup_path

    assert is_whatsapp_setup_intent(prompt) is True
    guide = maybe_resume_whatsapp_guide(prompt, [], persist=False)
    assert guide is not None
    assert WEBHOOK_QUESTION in (guide.get("message") or "")
    assert whatsapp_setup_path() in (guide.get("message") or "")
    assert OWN_ACCOUNT not in (guide.get("message") or "")

    client = _client(monkeypatch)
    resp = _chat(client, prompt)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model_used"] == "whatsapp-setup-guide"
    assert WEBHOOK_QUESTION in body["response"]
    assert whatsapp_setup_path() in body["response"]
    assert "EAA" not in body["response"]
    assert "WHATSAPP_ACCESS_TOKEN" not in body["response"]


@pytest.mark.parametrize("edition", ("amp", "maxine"))
def test_empty_history_workroom_is_isolation_not_guide(monkeypatch, tmp_path, edition):
    _env(monkeypatch, tmp_path, edition)
    _seed_pending(tmp_path, edition=edition, step="own_account")
    client = _client(monkeypatch)
    resp = _chat(client, "Qué es el Workroom")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert _is_guide(body) is False
    assert "No conozco el Workroom" in body["response"]
    assert "no tiene sus datos" in body["response"]
    assert body["model_used"] == "empire-module-knowledge"


def test_intent_detector_rejects_send_and_what_is():
    from app.services.maxe_guides import is_whatsapp_setup_intent

    assert is_whatsapp_setup_intent("enviar por WhatsApp") is False
    assert is_whatsapp_setup_intent("WhatsApp") is False
    assert is_whatsapp_setup_intent("qué es WhatsApp") is False
    assert is_whatsapp_setup_intent("hola manito") is False
    assert is_whatsapp_setup_intent("") is False


def test_system_prompt_restricts_whatsapp_tool_to_explicit_intent(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.max.system_prompt import get_system_prompt, _prompt_cache

    _prompt_cache.update({"prompt": None, "expires": 0, "edition": None})
    prompt = get_system_prompt()
    assert "whatsapp_setup_guide SOLO si pide explícitamente" in prompt
    assert "Preguntas normales" in prompt


def test_use_chat_does_not_replace_welcome_with_guide():
    hook = (
        __import__("pathlib")
        .Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("empire-command-center/app/hooks/useChat.ts")
        .read_text(encoding="utf-8")
    )
    assert "whatsapp_guide" not in hook
    assert "guideWelcomeRef" not in hook
