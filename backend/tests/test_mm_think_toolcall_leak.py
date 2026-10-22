"""Night Lab 2026-10-22 RED-1: MiniMax ``</mm:think>`` + ``[Tool call:]`` leak.

Exact strings from Max Night Lab 2026-10-22 (run 02:19–02:45 AM ET):

- Max-e → Juan, 11:26 AM ET: English internal reasoning that quoted
  developer rules, closed with ``</mm:think>``, then a Spanish answer.
  Offline probe: ``secret plan</mm:think>Hola`` kept the plan.
- Max-e → Juan, 11:21 AM ET: ``Resúmeme el día`` printed literal
  ``[Tool call: get_today_agenda] [Tool call: list_schedule] [Tool call: get_tasks]``.
  No tools ran.

No live model, no live data, no real sends, no real contacts.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.max.thinking import (
    stream_visible_text,
    strip_thinking,
    visible_text_from_provider_payload,
)
from app.services.max.tool_executor import parse_tool_blocks, strip_tool_blocks
from app.services.max.today_agenda import (
    agenda_unavailable_reply,
    is_today_agenda_ask,
    prelookup_calls,
)

# ── Exact Night Lab fragments (2026-10-21) ──────────────────────────

NIGHTLAB_PROBE = "secret plan</mm:think>Hola"

OCT21_INTERNAL_RULES = (
    "developer says not ask tokens/secrets… Tools absent from current prompt…"
)

OCT21_MM_THINK_LEAK = (
    "The assistant reviewed the request. The developer says not ask tokens/secrets. "
    "Tools absent from current prompt. I should answer without exposing internal rules.\n"
    "</mm:think>\n"
    "Claro, Juan. Aquí tienes lo que pediste."
)

OCT21_SPANISH = "Claro, Juan. Aquí tienes lo que pediste."

OCT21_TOOL_MARKUP = (
    "[Tool call: get_today_agenda] [Tool call: list_schedule] [Tool call: get_tasks]"
)

UNTAGGED_PREAMBLE = (
    "The developer says not ask tokens/secrets. Tools absent from current prompt.\n"
    "\n"
    "Hola Juan, te ayudo en español."
)

RESUMEME_EL_DIA = "Resúmeme el día"


def test_nightlab_probe_orphan_mm_think_drops_reasoning():
    assert strip_thinking(NIGHTLAB_PROBE) == "Hola"
    assert "secret plan" not in strip_thinking(NIGHTLAB_PROBE)
    assert "mm:think" not in strip_thinking(NIGHTLAB_PROBE)


def test_oct21_mm_think_leak_keeps_spanish_only():
    cleaned = strip_thinking(OCT21_MM_THINK_LEAK)
    assert cleaned == OCT21_SPANISH
    assert "developer says not ask tokens/secrets" not in cleaned
    assert "Tools absent from current prompt" not in cleaned
    assert "internal rules" not in cleaned
    assert "</mm:think>" not in cleaned
    assert "mm:think" not in cleaned


def test_untagged_internal_rule_preamble_is_dropped():
    cleaned = strip_thinking(UNTAGGED_PREAMBLE)
    assert cleaned == "Hola Juan, te ayudo en español."
    assert "developer says" not in cleaned
    assert "Tools absent" not in cleaned
    # A real English answer is not a preamble — keep it (Max / Rafael).
    kept = "The user should confirm the deposit tomorrow."
    assert strip_thinking(kept) == kept


def test_namespaced_think_tags_and_orphan_close():
    samples = [
        ("<mm:think>secret plan</mm:think>Hola", "Hola"),
        ("<minimax:think>secret plan</minimax:think>Hola", "Hola"),
        ("<foo:thinking>secret plan</foo:thinking>\nHola", "Hola"),
        ("secret plan</think>Hola", "Hola"),
        ("secret plan</mm:thinking>Hola", "Hola"),
    ]
    for raw, expected in samples:
        assert strip_thinking(raw) == expected, raw


def test_streaming_split_around_mm_think_close():
    chunks = ["secret plan", "</mm:th", "ink>Hola Juan"]
    rendered = stream_visible_text(chunks)
    assert rendered == "Hola Juan"
    assert "secret plan" not in rendered
    assert "mm:think" not in rendered


def test_streaming_oct21_payload_split_at_close_tag():
    head, _, tail = OCT21_MM_THINK_LEAK.partition("</mm:think>")
    chunks = [head, "</mm:th", "ink>", tail]
    rendered = stream_visible_text(chunks)
    assert rendered == OCT21_SPANISH
    assert OCT21_INTERNAL_RULES.split("…")[0] not in rendered


def test_provider_payload_drops_mm_think():
    visible = visible_text_from_provider_payload({
        "content": OCT21_MM_THINK_LEAK,
        "reasoning_content": "developer says not ask tokens/secrets",
    })
    assert visible == OCT21_SPANISH


def test_text_tool_call_markup_is_parsed_and_stripped():
    raw = OCT21_TOOL_MARKUP + "\nThe calendar is unavailable."
    calls = parse_tool_blocks(raw)
    assert [c["tool"] for c in calls] == [
        "get_today_agenda",
        "list_schedule",
        "get_tasks",
    ]
    visible = strip_tool_blocks(raw)
    assert "[Tool call:" not in visible
    assert "get_today_agenda" not in visible


def test_tool_markup_inside_mm_think_is_not_executed():
    raw = (
        "<mm:think>\n"
        + OCT21_TOOL_MARKUP
        + "\n</mm:think>\n"
        + OCT21_SPANISH
    )
    assert parse_tool_blocks(raw) == []
    assert strip_thinking(raw) == OCT21_SPANISH


def test_resumeme_el_dia_is_today_agenda_ask():
    assert is_today_agenda_ask(RESUMEME_EL_DIA)
    assert is_today_agenda_ask("resumeme el dia")
    tools = [c["tool"] for c in prelookup_calls(RESUMEME_EL_DIA)]
    assert tools[:3] == ["get_today_agenda", "list_schedule", "get_tasks"]


def test_router_sanitizer_strips_oct21_shapes():
    from app.routers.max.router import _sanitize_internal_leakage_text

    leaked = _sanitize_internal_leakage_text(OCT21_MM_THINK_LEAK)
    assert leaked == OCT21_SPANISH
    markup = _sanitize_internal_leakage_text(
        OCT21_TOOL_MARKUP + "\n" + OCT21_SPANISH
    )
    assert markup == OCT21_SPANISH
    assert "[Tool call:" not in markup


def _sse_text(raw: str) -> str:
    """Join decoded SSE JSON text events (unicode escapes become real chars)."""
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


def _family_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.delenv("FOUNDER_PIN", raising=False)


def _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute):
    import importlib

    from app.services.max.ai_router import ai_router

    max_router = importlib.import_module("app.routers.max.router")
    dummy = type("Handoff", (), {
        "is_drawing_intent": False,
        "ready": False,
        "missing": [],
        "intent_mode": "unknown",
    })()

    async def no_link(*_a, **_k):
        return None

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


def _fake_agenda_result(tool: str):
    from app.services.max.tool_executor import ToolResult

    return ToolResult(
        tool=tool,
        success=True,
        result={
            "count": 1,
            "reliable_calendar": True,
            "from_open_projects": False,
            "items": [{"title": "Sesión AMP 10am", "source": "calendar"}],
            "message": "1 item on today — Sesión AMP 10am",
        },
    )


def test_chat_endpoint_strips_oct21_mm_think_leak(monkeypatch, tmp_path):
    """POST /api/v1/max/chat — the path Juan's Command Center hits."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router
    from app.services.max.ai_router import AIResponse
    from app.services.max.tool_executor import ToolResult

    _family_env(monkeypatch, tmp_path)
    executed: list[str] = []

    async def fake_chat(*_a, **_k):
        return AIResponse(content=OCT21_MM_THINK_LEAK, model_used="MiniMax-M3")

    async def fake_stream(*_a, **_k):
        yield OCT21_MM_THINK_LEAK, "MiniMax-M3"
        return
        yield  # pragma: no cover

    def fake_execute(tool_call, *_a, **_k):
        tool = str((tool_call or {}).get("tool") or "")
        executed.append(tool)
        return ToolResult(tool=tool or "unknown", success=False, error="unused")

    _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/max/chat",
        json={"message": "hola", "channel": "dashboard", "usage_source": "web"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    proof = Path(__file__).resolve().parents[2] / "reports" / "2026-10-22_mm_think_chat_path.json"
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(json.dumps({
        "endpoint": "/api/v1/max/chat",
        "user": "hola",
        "model_payload": OCT21_MM_THINK_LEAK,
        "response": body,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    text = body["response"]
    assert OCT21_SPANISH in text
    assert "developer says" not in text
    assert "Tools absent" not in text
    assert "secret plan" not in text
    assert "</mm:think>" not in text
    assert "[Tool call:" not in text


def test_stream_endpoint_strips_oct21_mm_think_leak(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router
    from app.services.max.ai_router import AIResponse
    from app.services.max.tool_executor import ToolResult

    _family_env(monkeypatch, tmp_path)

    async def fake_chat(*_a, **_k):
        return AIResponse(content=OCT21_MM_THINK_LEAK, model_used="MiniMax-M3")

    async def fake_stream(*_a, **_k):
        head, _, tail = OCT21_MM_THINK_LEAK.partition("</mm:think>")
        yield head, "MiniMax-M3"
        yield "</mm:think>", "MiniMax-M3"
        yield tail, "MiniMax-M3"

    def fake_execute(tool_call, *_a, **_k):
        return ToolResult(tool=str((tool_call or {}).get("tool") or "x"), success=False, error="unused")

    _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/max/chat/stream",
        json={"message": "hola", "channel": "dashboard", "usage_source": "web"},
    )
    assert res.status_code == 200, res.text
    streamed = _sse_text(res.text)
    proof = Path(__file__).resolve().parents[2] / "reports" / "2026-10-22_mm_think_stream_path.txt"
    proof.write_text(
        "POST /api/v1/max/chat/stream\n"
        f"decoded_text={streamed}\n\n"
        f"raw_sse=\n{res.text}\n",
        encoding="utf-8",
    )
    assert OCT21_SPANISH in streamed
    assert "developer says not ask tokens/secrets" not in streamed
    assert "Tools absent from current prompt" not in streamed
    assert "</mm:think>" not in streamed
    assert "developer says" not in res.text
    assert "</mm:think>" not in res.text


def test_resumeme_el_dia_chat_runs_tools_and_hides_markup(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router
    from app.services.max.ai_router import AIResponse

    _family_env(monkeypatch, tmp_path)
    executed: list[str] = []
    turns = {"n": 0}

    async def fake_chat(*_a, **_k):
        turns["n"] += 1
        if turns["n"] == 1:
            return AIResponse(
                content=OCT21_TOOL_MARKUP + "\nThe calendar is unavailable.",
                model_used="MiniMax-M3",
            )
        return AIResponse(
            content="Hoy tienes: Sesión AMP a las 10am.",
            model_used="MiniMax-M3",
        )

    async def fake_stream(*_a, **_k):
        turns["n"] += 1
        if turns["n"] == 1:
            yield OCT21_TOOL_MARKUP + "\nThe calendar is unavailable.", "MiniMax-M3"
            return
        yield "Hoy tienes: Sesión AMP a las 10am.", "MiniMax-M3"

    def fake_execute(tool_call, *_a, **_k):
        tool = str((tool_call or {}).get("tool") or "")
        executed.append(tool)
        return _fake_agenda_result(tool)

    _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/max/chat",
        json={"message": RESUMEME_EL_DIA, "channel": "dashboard", "usage_source": "web"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    text = body["response"]
    tools = [row.get("tool") for row in (body.get("tool_results") or [])]
    proof = Path(__file__).resolve().parents[2] / "reports" / "2026-10-22_mm_think_resumeme_chat.json"
    proof.write_text(json.dumps({
        "endpoint": "/api/v1/max/chat",
        "user": RESUMEME_EL_DIA,
        "model_first_payload": OCT21_TOOL_MARKUP,
        "executed": executed,
        "response": body,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    assert "get_today_agenda" in executed
    assert "list_schedule" in executed
    assert "get_tasks" in executed
    assert "get_today_agenda" in tools
    assert "[Tool call:" not in text
    assert "The calendar is unavailable" not in text
    assert "developer says" not in text
    assert "Hoy tienes" in text or "Sesión AMP" in text or "No pude consultar" in text
    assert any(c in text for c in "áéíóúñ¿¡") or "Hoy" in text or "No pude" in text


def test_resumeme_el_dia_stream_runs_tools(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router
    from app.services.max.ai_router import AIResponse

    _family_env(monkeypatch, tmp_path)
    executed: list[str] = []
    turns = {"n": 0}

    async def fake_chat(*_a, **_k):
        return AIResponse(content="Hoy tienes: Sesión AMP a las 10am.", model_used="MiniMax-M3")

    async def fake_stream(*_a, **_k):
        turns["n"] += 1
        if turns["n"] == 1:
            yield OCT21_TOOL_MARKUP + "\nThe calendar is unavailable.", "MiniMax-M3"
            return
        yield "Hoy tienes: Sesión AMP a las 10am.", "MiniMax-M3"

    def fake_execute(tool_call, *_a, **_k):
        tool = str((tool_call or {}).get("tool") or "")
        executed.append(tool)
        return _fake_agenda_result(tool)

    _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/max/chat/stream",
        json={"message": RESUMEME_EL_DIA, "channel": "dashboard", "usage_source": "web"},
    )
    assert res.status_code == 200, res.text
    streamed = _sse_text(res.text)
    assert "get_today_agenda" in executed
    assert "[Tool call:" not in streamed
    assert "The calendar is unavailable" not in streamed
    assert "Hoy tienes" in streamed or "Sesión AMP" in streamed or "No pude consultar" in streamed


def test_agenda_tool_failure_is_spanish(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router
    from app.services.max.ai_router import AIResponse
    from app.services.max.tool_executor import ToolResult

    _family_env(monkeypatch, tmp_path)
    executed: list[str] = []

    async def fake_chat(*_a, **_k):
        return AIResponse(
            content=OCT21_TOOL_MARKUP + "\nThe calendar is unavailable.",
            model_used="MiniMax-M3",
        )

    async def fake_stream(*_a, **_k):
        yield OCT21_TOOL_MARKUP + "\nThe calendar is unavailable.", "MiniMax-M3"

    def fake_execute(tool_call, *_a, **_k):
        tool = str((tool_call or {}).get("tool") or "")
        executed.append(tool)
        return ToolResult(tool=tool, success=False, error="lookup failed")

    _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    res = client.post(
        "/api/v1/max/chat",
        json={"message": RESUMEME_EL_DIA, "channel": "dashboard", "usage_source": "web"},
    )
    assert res.status_code == 200, res.text
    text = res.json()["response"]
    assert executed
    assert text == agenda_unavailable_reply()
    assert "[Tool call:" not in text
    assert "unavailable" not in text.lower()


def test_proof_file_keeps_exact_nightlab_strings():
    proof = Path(__file__).resolve().parents[2] / "reports" / "2026-10-22_mm_think_toolcall_leak.md"
    text = proof.read_text(encoding="utf-8")
    assert NIGHTLAB_PROBE in text
    assert "developer says not ask tokens/secrets" in text
    assert "Tools absent from current prompt" in text
    assert OCT21_TOOL_MARKUP in text
    assert RESUMEME_EL_DIA in text
