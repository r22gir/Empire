"""Spanish factual-guard and search-query behavior for Max-e."""
from app.services.max.factual_guard import (
    is_factual_question,
    search_unavailable_reply,
)
from app.services.max.runtime_truth_check import _is_performative_web_search_request
from app.services.max.search_context import build_search_query


def test_spanish_news_question_triggers_search():
    assert is_factual_question("Que paso en Panama")
    assert is_factual_question("Qué pasó en Panamá")
    assert is_factual_question("qué está pasando en Colombia")
    assert is_factual_question("noticias de hoy")
    assert is_factual_question("última hora en Bogotá")
    assert is_factual_question("quién ganó las elecciones")
    assert is_factual_question("cuánto cuesta el dólar")
    assert is_factual_question("cómo está el clima en Medellín")
    assert is_factual_question("cuál es la TRM")
    assert is_factual_question("resultados del partido de ayer")


def test_spanish_evergreen_questions_trigger_search():
    assert is_factual_question("qué es el coaching ontológico")
    assert is_factual_question("cómo funciona una VPN")
    assert is_factual_question("por qué sube el dólar")
    assert is_factual_question("diferencia entre coaching y mentoring")


def test_spanish_chitchat_does_not_trigger_search():
    assert not is_factual_question("hola")
    assert not is_factual_question("gracias")
    assert not is_factual_question("buenos días")
    assert not is_factual_question("cómo estás")


def test_casual_spanish_does_not_trigger_search():
    assert not is_factual_question("hoy no puedo")
    assert not is_factual_question("voy a casa hoy")
    assert not is_factual_question("como puedo ayudarte")
    assert not is_factual_question("cómo puedo ayudarte")
    assert not is_factual_question("que es eso")
    assert not is_factual_question("qué es eso")
    assert not is_factual_question("por que no funciona")
    assert not is_factual_question("por qué no funciona")
    assert not is_factual_question("buenos dias, que tal hoy")
    assert not is_factual_question("buenos días, qué tal hoy")


def test_spanish_news_phrases_still_trigger_search():
    assert is_factual_question("que paso en Panama")
    assert is_factual_question("Que paso en Panama")
    assert is_factual_question("noticias de hoy")
    assert is_factual_question("cuanto esta el dolar hoy")
    assert is_factual_question("cuánto está el dólar hoy")


def test_max_e_and_spanish_words_do_not_suppress_search():
    assert is_factual_question("Max-e, qué pasó en Panamá")
    assert is_factual_question("dime el máximo de la TRM hoy")
    assert is_factual_question("alexandra, qué es una VPN")
    assert is_factual_question("el empirebox de Juan: noticias de hoy")


def test_internal_markers_still_block_search():
    assert not is_factual_question("What is the status of quote # EST-2026-293?")
    assert not is_factual_question("What is our founder pricing rule for goblet pleats?")
    assert not is_factual_question("job status of the work order")


def test_spanish_search_verbs_are_performative():
    assert _is_performative_web_search_request("busca las noticias de Panamá")
    assert _is_performative_web_search_request("investiga el dólar hoy")
    assert _is_performative_web_search_request("búscame el clima en Bogotá")
    assert _is_performative_web_search_request("averigua en internet quién ganó")


def test_spanish_news_query_keeps_spanish_place_and_hoy():
    out = build_search_query("Que paso en Panama")
    assert "Panama" in out["query"] or "Panamá" in out["query"]
    assert "hoy" in out["query"].lower()
    assert "Que paso" in out["query"] or "paso" in out["query"].lower()


def test_search_failure_reply_is_short_spanish():
    reply = search_unavailable_reply()
    assert "no tengo información" not in reply.lower()
    assert "No pude consultar" in reply


def test_family_search_failure_uses_chat_response_field():
    import importlib

    max_router = importlib.import_module("app.routers.max.router")
    out = max_router.family_search_failure_response()
    assert out.response == search_unavailable_reply()
    assert not hasattr(out, "content") or getattr(out, "content", None) is None
    assert out.model_used == "search-unavailable"
    assert out.metadata["pre_search_failed"] is True


def test_search_failure_reaches_chat_response(monkeypatch):
    """Non-stream search failure must land on ChatResponse.response, not .content."""
    import asyncio
    import importlib

    from fastapi import BackgroundTasks, Response

    from app.services.max.tool_executor import ToolResult

    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setattr(max_router, "_is_family_edition", lambda: True)
    monkeypatch.setattr(max_router, "_family_pre_search_open", lambda _desk: True)

    chat_called: list[int] = []

    async def fake_chat(*args, **kwargs):
        chat_called.append(1)
        raise AssertionError("model must not run after family search failure")

    def fake_execute(tool_call, *args, **kwargs):
        tool = tool_call.get("tool")
        if tool == "web_search":
            return ToolResult(tool=tool, success=False, error="search unavailable")
        raise AssertionError(f"unexpected tool {tool!r}")

    async def no_link(*args, **kwargs):
        return None

    dummy = type("Handoff", (), {
        "is_drawing_intent": False,
        "ready": False,
        "missing": [],
        "intent_mode": "unknown",
    })()

    monkeypatch.setattr(max_router, "execute_tool", fake_execute)
    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)
    monkeypatch.setattr(max_router, "_link_intelligence_response", no_link)
    monkeypatch.setattr(max_router, "_maybe_handle_direct_route_request", lambda *_a, **_k: None)
    monkeypatch.setattr(max_router, "_maybe_handle_gpu_safety_request", lambda *_a, **_k: None)
    monkeypatch.setattr(max_router, "should_run_whats_new_summary", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "should_force_runtime_truth_check", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "should_clarify_inventory_request", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "build_drawing_handoff", lambda *_a, **_k: dummy)

    try:
        import app.services.max.continuity_compaction as continuity
        monkeypatch.setattr(continuity, "should_handle_continuity_command", lambda *_a, **_k: False)
        monkeypatch.setattr(continuity, "should_run_continuity_audit", lambda *_a, **_k: False)
    except Exception:
        pass

    request = max_router.ChatRequest(message="Que paso en Panama", history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.response == search_unavailable_reply()
    assert "no tengo información" not in response.response.lower()
    assert "No pude consultar" in response.response
    assert response.model_used == "search-unavailable"
    assert not chat_called
