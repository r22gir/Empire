"""Night Lab RED — Max-e must never show MiniMax think tags to Juan.

Covers the single sanitizer (sanitize_output / strip_thinking) used by
chat, stream, WhatsApp, Telegram, and email. Closed, unclosed, nested,
split-across-chunks, and provider variants.

Mock data only. No live model. No real WhatsApp / Telegram / email sends.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.max.guardrails import (
    new_thinking_stream_sanitizer,
    sanitize_output,
    sanitize_output_streaming,
)
from app.services.max.thinking import stream_visible_text, strip_thinking

VISIBLE = "Claro, Juan. Aquí tienes lo que pediste."
SECRET = "secret plan developer says not ask tokens"


def _assert_clean(text: str) -> None:
    assert VISIBLE in text
    assert SECRET not in text
    assert "developer says" not in text
    assert "mm:think" not in text.lower()
    assert "<think" not in text.lower()
    assert "</think" not in text.lower()
    assert "◁think" not in text.lower()


# ── Closed / unclosed / nested / variants ──────────────────────────


def test_closed_mm_think_and_variants():
    samples = [
        f"<mm:think>{SECRET}</mm:think>{VISIBLE}",
        f"<MM:THINK>{SECRET}</MM:THINK>{VISIBLE}",
        f"<minimax:think>{SECRET}</minimax:think>\n{VISIBLE}",
        f"<foo:thinking>{SECRET}</foo:thinking>\n{VISIBLE}",
        f"<think hidden=\"1\">{SECRET}</think>{VISIBLE}",
        f"<thinking>{SECRET}</thinking>{VISIBLE}",
        f"<reasoning>{SECRET}</reasoning>{VISIBLE}",
        f"◁think▷{SECRET}◁/think▷\n{VISIBLE}",
        f"<|think|>{SECRET}<|/think|>\n{VISIBLE}",
        f"```thinking\n{SECRET}\n```\n{VISIBLE}",
    ]
    for raw in samples:
        cleaned = sanitize_output(raw)
        _assert_clean(cleaned)
        assert cleaned.endswith("pediste.") or VISIBLE in cleaned


def test_unclosed_think_is_dropped():
    assert sanitize_output(f"<mm:think>{SECRET}") == ""
    assert SECRET not in sanitize_output(f"<think>{SECRET} still going")
    assert sanitize_output(f"{VISIBLE}\n<mm:think>{SECRET}") == VISIBLE


def test_nested_think_keeps_visible_prefix_and_suffix():
    raw = (
        f"Hola Juan <mm:think>outer <think>{SECRET}</think> "
        f"still hidden</mm:think> {VISIBLE}"
    )
    cleaned = sanitize_output(raw)
    assert "Hola Juan" in cleaned
    _assert_clean(cleaned)
    # One-pass non-greedy strip used to orphan-close and eat "Hola Juan".
    assert cleaned.startswith("Hola Juan")


def test_orphan_close_drops_reasoning_not_just_tag():
    assert sanitize_output(f"{SECRET}</mm:think>{VISIBLE}") == VISIBLE
    assert sanitize_output(f"{SECRET}</think>{VISIBLE}") == VISIBLE


def test_div_and_real_answer_are_kept():
    kept = "<div>panel</div> The user should confirm the deposit tomorrow."
    assert sanitize_output(kept) == kept


# ── Streaming: split mid-tag ───────────────────────────────────────


def test_stream_split_mid_open_and_close():
    chunks = [
        "<mm:",
        f"think>{SECRET}</mm:",
        f"think>{VISIBLE}",
    ]
    rendered = stream_visible_text(chunks)
    _assert_clean(rendered)
    assert rendered == VISIBLE


def test_stream_split_nested_and_special():
    chunks = [
        "Hola ",
        "<th",
        f"ink>inner {SECRET}</th",
        "ink>\n",
        VISIBLE,
    ]
    rendered = stream_visible_text(chunks)
    assert "Hola" in rendered
    _assert_clean(rendered)


def test_stateful_sanitizer_holds_partial_namespaced_tag():
    push, finish = new_thinking_stream_sanitizer()
    assert push("<mm:th") == ""
    mid = push(f"ink>{SECRET}</mm:think>{VISIBLE}")
    out = (mid + finish()).strip()
    _assert_clean(out)


def test_per_chunk_helper_does_not_unwrap_partial_open():
    # Incomplete open tag must not become visible English reasoning.
    assert SECRET not in sanitize_output_streaming("<mm:thi")
    assert sanitize_output_streaming(f"<mm:think>{SECRET}") == ""


# ── Chat + stream doors Juan's Command Center hits ─────────────────


def _family_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.delenv("FOUNDER_PIN", raising=False)


def _patch_chat_path(monkeypatch, fake_chat, fake_stream):
    import importlib

    from app.services.max.ai_router import ai_router
    from app.services.max.tool_executor import ToolResult

    max_router = importlib.import_module("app.routers.max.router")
    dummy = type("Handoff", (), {
        "is_drawing_intent": False,
        "ready": False,
        "missing": [],
        "intent_mode": "unknown",
    })()

    async def no_link(*_a, **_k):
        return None

    def fake_execute(tool_call, *_a, **_k):
        tool = str((tool_call or {}).get("tool") or "x")
        return ToolResult(tool=tool, success=False, error="unused")

    monkeypatch.setattr(max_router, "_is_family_edition", lambda: True)
    monkeypatch.setattr(max_router, "_family_pre_search_open", lambda _desk: False)
    monkeypatch.setattr(max_router, "_link_intelligence_response", no_link)
    monkeypatch.setattr(max_router, "_maybe_handle_direct_route_request", lambda *_a, **_k: None)
    monkeypatch.setattr(max_router, "_maybe_handle_gpu_safety_request", lambda *_a, **_k: None)
    monkeypatch.setattr(max_router, "should_run_whats_new_summary", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "should_force_runtime_truth_check", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "should_clarify_inventory_request", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "build_drawing_handoff", lambda *_a, **_k: dummy)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute)
    monkeypatch.setattr(ai_router, "chat", fake_chat)
    monkeypatch.setattr(ai_router, "chat_stream", fake_stream)
    try:
        from app.services.max import factual_guard
        monkeypatch.setattr(factual_guard, "is_factual_question", lambda *_a, **_k: False)
    except Exception:
        pass
    try:
        import app.services.max.continuity_compaction as continuity
        monkeypatch.setattr(continuity, "should_handle_continuity_command", lambda *_a, **_k: False)
        monkeypatch.setattr(continuity, "should_run_continuity_audit", lambda *_a, **_k: False)
    except Exception:
        pass
    return max_router


def _sse_text(raw: str) -> str:
    parts: list[str] = []
    for line in (raw or "").splitlines():
        if not line.startswith("data: "):
            continue
        try:
            payload = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("type") == "text":
            parts.append(str(payload.get("content") or ""))
    return "\n".join(parts)


NESTED_LEAK = (
    f"Hola. <mm:think>outer <think>{SECRET}</think> leftover</mm:think>\n"
    f"{VISIBLE}"
)


def test_chat_and_stream_strip_nested_mm_think(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router
    from app.services.max.ai_router import AIResponse

    _family_env(monkeypatch, tmp_path)

    async def fake_chat(*_a, **_k):
        return AIResponse(content=NESTED_LEAK, model_used="MiniMax-M3")

    async def fake_stream(*_a, **_k):
        yield "Hola. <mm:", "MiniMax-M3"
        yield f"think>outer <think>{SECRET}</think> leftover</mm:", "MiniMax-M3"
        yield f"think>\n{VISIBLE}", "MiniMax-M3"

    _patch_chat_path(monkeypatch, fake_chat, fake_stream)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    chat = client.post(
        "/api/v1/max/chat",
        json={"message": "hola", "channel": "dashboard", "usage_source": "web"},
    )
    assert chat.status_code == 200, chat.text
    chat_text = chat.json()["response"]
    _assert_clean(chat_text)
    assert "Hola." in chat_text

    stream = client.post(
        "/api/v1/max/chat/stream",
        json={"message": "hola", "channel": "dashboard", "usage_source": "web"},
    )
    assert stream.status_code == 200, stream.text
    streamed = _sse_text(stream.text)
    _assert_clean(streamed)
    assert "Hola." in streamed
    assert SECRET not in stream.text
    assert "</mm:think>" not in stream.text

    proof = Path(__file__).resolve().parents[2] / "reports" / "2026-10-23_maxe_think_tag_chat_path.json"
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(json.dumps({
        "endpoint_chat": "/api/v1/max/chat",
        "endpoint_stream": "/api/v1/max/chat/stream",
        "model_payload": NESTED_LEAK,
        "chat_response": chat_text,
        "stream_decoded": streamed,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


# ── WhatsApp / Telegram / email (mocked, no real sends) ────────────


def test_whatsapp_session_text_strips_think_tags(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "5551234")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "+57 300 111 2233")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")

    from app.services import whatsapp_cloud as wa

    captured = {}

    def fake_graph(method, url, *, token="", body=None, headers=None):
        captured["body"] = body
        captured["url"] = url
        return 200, b'{"messages":[{"id":"wamid.fake"}]}'

    monkeypatch.setattr(wa, "graph_request", fake_graph)
    now = int(__import__("time").time())
    wa.remember_inbound("573001112233", now)

    leaked = f"<mm:think>{SECRET}</mm:think>{VISIBLE}"
    result = wa.send_session_text("573001112233", leaked, now=now)
    assert result.get("sent") is True
    raw = captured.get("body") or b""
    payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    body = ((payload.get("text") or {}).get("body")) or ""
    _assert_clean(body)
    assert SECRET.encode() not in raw if isinstance(raw, bytes) else SECRET not in json.dumps(payload)


def test_telegram_chat_strips_leaky_service_response(monkeypatch, tmp_path):
    import asyncio
    import importlib

    from app.services.max.telegram_bot import TelegramBot
    from app.routers.max.router import ChatResponse

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0:fake")
    monkeypatch.setenv("TELEGRAM_FOUNDER_CHAT_ID", "123")

    async def leaky(_request, **_k):
        return ChatResponse(
            response=f"<mm:think>{SECRET}</mm:think>{VISIBLE}",
            model_used="MiniMax-M3",
            fallback_used=False,
        )

    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "_chat_with_max_service", leaky)
    monkeypatch.setattr("app.services.max.telegram_bot._get_history", lambda *_a, **_k: [])
    monkeypatch.setattr("app.services.max.telegram_bot._append_and_save", lambda *_a, **_k: None)

    bot = TelegramBot()
    html, plain, _tools = asyncio.run(bot._chat_with_max("hola", chat_id="123"))
    _assert_clean(plain)
    _assert_clean(html)


def test_email_draft_and_send_strip_think_tags(monkeypatch, tmp_path):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "juan@example.com")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "maxe@example.com")

    from app.services.max.email_service import EmailService, generate_email_reply_draft
    from app.services.max.routing_state import RoutingState

    monkeypatch.setattr(
        "app.services.max.routing_state.load_routing_state",
        lambda: RoutingState(
            selected_provider="deepseek",
            selected_model="deepseek-v4-flash",
            fallback_enabled=False,
            ai_calls_disabled=False,
            lane="test",
            updated_at="2026-01-01T00:00:00+00:00",
            updated_by="test",
            last_switch_reason="test_isolation",
        ),
    )

    class _Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": f"<mm:think>{SECRET}</mm:think>{VISIBLE}"}}]}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr("app.services.max.email_service.httpx.Client", _Client)

    draft = generate_email_reply_draft(
        sender="juan@example.com",
        subject="Hola",
        body="ping",
        tiny_test_prompt="ok",
    )
    assert draft["would_send"] is False
    _assert_clean(draft["max_response_text"] or "")

    sent = {}

    class FakeSG:
        status_code = 202
        text = ""

    def fake_post(url, headers, json, timeout):
        sent["json"] = json
        return FakeSG()

    monkeypatch.setattr("httpx.post", fake_post)
    monkeypatch.setattr(
        "app.services.max.unified_message_store.unified_store.add_message",
        lambda *_a, **_k: None,
    )
    svc = EmailService()
    assert svc.send(
        to="juan@example.com",
        subject=f"<think>{SECRET}</think>Agenda",
        body_text=f"<mm:think>{SECRET}</mm:think>{VISIBLE}",
    ) is True
    content = sent["json"]["content"]
    blob = json.dumps(content, ensure_ascii=False)
    assert SECRET not in blob
    assert "mm:think" not in blob.lower()
    assert VISIBLE in blob
    assert sent["json"]["subject"] == "Agenda" or "Agenda" in sent["json"]["personalizations"][0].get("subject", sent["json"].get("subject", "Agenda"))


def test_strip_thinking_matches_sanitize_output_layer():
    raw = f"<mm:think>{SECRET}</mm:think>{VISIBLE}"
    assert sanitize_output(raw) == strip_thinking(raw) == VISIBLE
