"""MiniMax hidden-reasoning leak — reply, history, search, streaming.

Incident (Max-e / Juan, 2026-10-21 ~11:27 AM ET): MiniMax English
<think> / reasoning_content leaked into the visible reply, was saved
twice in chat history, and became the web_search query. Juan asked
«¿por qué en inglés?».

These tests pin the central stripper and the three consumer paths.
No live model calls, no real sends.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.max.thinking import (
    ThinkingStreamFilter,
    raw_visible_text_from_provider_payload,
    sanitize_history_messages,
    sanitize_tool_call,
    sanitize_tool_query,
    stream_visible_text,
    strip_thinking,
    visible_text_from_provider_payload,
)

# ── Oct 21 2026 sample (reconstructed from the leak shape Juan hit) ──

BEFORE_REPLY = (
    "<think>\n"
    "The user asked \"qué pasó hoy en Colombia\" in Spanish. I should "
    "search in English for better results about current Colombian news "
    "and then summarize.\n"
    "</think>\n"
    "\n"
    "Hoy en Colombia hay varias noticias: te resumo lo principal en "
    "español, Juan."
)

AFTER_REPLY = (
    "Hoy en Colombia hay varias noticias: te resumo lo principal en "
    "español, Juan."
)

THINKING_ENGLISH = "The user asked \"qué pasó hoy en Colombia\""


def test_strip_think_block_keeps_spanish_reply():
    cleaned = strip_thinking(BEFORE_REPLY)
    assert cleaned == AFTER_REPLY
    assert THINKING_ENGLISH not in cleaned
    assert "<think>" not in cleaned
    assert "español, Juan" in cleaned


def test_reasoning_content_is_dropped_not_concatenated():
    """Thinking field + think-tagged content used to appear twice in history."""
    message = {
        "role": "assistant",
        "content": BEFORE_REPLY,
        "reasoning_content": (
            "The user asked \"qué pasó hoy en Colombia\" in Spanish. "
            "I should search in English."
        ),
    }
    visible = visible_text_from_provider_payload(message)
    assert visible == AFTER_REPLY
    assert visible.count(THINKING_ENGLISH) == 0
    assert "I should search in English" not in visible


def test_reasoning_parts_in_multipart_content_are_ignored():
    payload = {
        "content": [
            {"type": "reasoning", "text": "The user wants weather in English."},
            {"type": "text", "text": "El clima en Bogotá está nublado."},
        ],
        "reasoning_content": "Hidden English self-talk.",
    }
    assert visible_text_from_provider_payload(payload) == "El clima en Bogotá está nublado."
    raw = raw_visible_text_from_provider_payload(payload)
    assert "Hidden English" not in raw
    assert "weather in English" not in raw


def test_unclosed_think_is_dropped_not_unwrapped():
    leaked = "<think>The user is greeting me. I should reply in Spanish."
    assert strip_thinking(leaked) == ""
    assert "The user is greeting" not in strip_thinking(leaked)


def test_minimax_special_tokens_and_fences():
    samples = [
        "◁think▷English plan◁/think▷\nListo.",
        "<|think|>English plan<|/think|>\nListo.",
        "```thinking\nEnglish plan\n```\nListo.",
        "<thinking>English plan</thinking>\nListo.",
        "<minimax:thinking>English plan</minimax:thinking>\nListo.",
    ]
    for raw in samples:
        cleaned = strip_thinking(raw)
        assert cleaned == "Listo.", raw
        assert "English plan" not in cleaned


def test_streaming_split_think_tags_do_not_leak():
    chunks = [
        "<th",
        "ink>\nThe user asked about Colombian news in English.\n</th",
        "ink>\nHoy hay noticias para ti, Juan.",
    ]
    rendered = stream_visible_text(chunks)
    assert rendered == "Hoy hay noticias para ti, Juan."
    assert "The user asked" not in rendered
    assert "<think>" not in rendered


def test_streaming_filter_holds_partial_open_tag():
    filt = ThinkingStreamFilter()
    assert filt.feed("<thi") == ""
    visible = filt.feed("nk>secret English</think>\nHola")
    assert "secret English" not in visible
    assert "Hola" in visible
    assert filt.flush() == ""


def test_router_stream_sanitizer_matches_filter():
    from app.services.max.guardrails import new_thinking_stream_sanitizer

    push, finish = new_thinking_stream_sanitizer()
    out = push("<think>English") + push(" reasoning</think>\n¡Hola Juan!") + finish()
    assert "English" not in out
    assert "¡Hola Juan!" in out


def test_saved_history_strips_thinking(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    from app.services.chat_history_store import persist_exchange

    chat_id = "juan-think-leak-20261021"
    saved = persist_exchange(
        chat_id=chat_id,
        user_message="qué pasó hoy en Colombia",
        assistant_message=BEFORE_REPLY,
        model="MiniMax-M3",
        workroom_dir=tmp_path,
    )
    assistant = saved["messages"][-1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == AFTER_REPLY
    assert THINKING_ENGLISH not in assistant["content"]
    on_disk = json.loads((tmp_path / "founder" / f"{chat_id}.json").read_text(encoding="utf-8"))
    assert on_disk["messages"][-1]["content"] == AFTER_REPLY
    blob = json.dumps(on_disk, ensure_ascii=False)
    assert blob.count(THINKING_ENGLISH) == 0
    assert blob.count(AFTER_REPLY) == 1


def test_upsert_strips_thinking_so_history_does_not_double(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    from app.services.chat_history_store import persist_exchange, upsert_chat

    chat_id = "juan-think-double-20261021"
    upsert_chat(
        chat_id=chat_id,
        messages=[
            {"role": "user", "content": "qué pasó hoy"},
            {"role": "assistant", "content": BEFORE_REPLY},
        ],
        workroom_dir=tmp_path,
    )
    persist_exchange(
        chat_id=chat_id,
        user_message="qué pasó hoy",
        assistant_message=BEFORE_REPLY,
        model="MiniMax-M3",
        workroom_dir=tmp_path,
    )
    data = json.loads((tmp_path / "founder" / f"{chat_id}.json").read_text(encoding="utf-8"))
    assistant_texts = [m["content"] for m in data["messages"] if m.get("role") == "assistant"]
    assert assistant_texts
    assert all(t == AFTER_REPLY for t in assistant_texts)
    assert json.dumps(data).count(THINKING_ENGLISH) == 0


def test_search_query_does_not_use_thinking_from_history():
    from app.services.max.search_context import build_search_query

    history = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": BEFORE_REPLY},
    ]
    out = build_search_query("qué pasó hoy", history=history)
    assert THINKING_ENGLISH not in out["query"]
    assert "I should search in English" not in out["query"]
    assert "qué pasó hoy" in out["query"]
    # Spanish current-event path may add Colombia / hoy from the cleaned reply.
    assert "<think>" not in out["query"]


def test_search_query_strips_thinking_if_message_is_model_output():
    from app.services.max.search_context import build_search_query

    out = build_search_query(BEFORE_REPLY, history=None)
    assert out["query"] == AFTER_REPLY
    assert "I should search" not in out["query"]


def test_web_search_tool_query_strips_thinking():
    from app.services.max.tool_executor import parse_tool_blocks

    raw = (
        BEFORE_REPLY
        + "\n```tool\n"
        + json.dumps({
            "tool": "web_search",
            "query": "<think>The user asked about Colombia. Search in English.</think>"
                     "qué pasó hoy en Colombia",
        }, ensure_ascii=False)
        + "\n```\n"
    )
    calls = parse_tool_blocks(raw)
    assert len(calls) == 1
    assert calls[0]["tool"] == "web_search"
    assert calls[0]["query"] == "qué pasó hoy en Colombia"
    assert "Search in English" not in calls[0]["query"]


def test_tool_call_inside_think_block_is_not_executed():
    from app.services.max.tool_executor import parse_tool_blocks

    raw = (
        "<think>\n```tool\n"
        '{"tool": "web_search", "query": "The user asked about Colombia news in English"}\n'
        "```\n</think>\n"
        "Claro, ya lo busco."
    )
    assert parse_tool_blocks(raw) == []


def test_web_search_executor_sends_stripped_query(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200
        text = ""

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["q"] = (kwargs.get("params") or {}).get("q")
        return _Resp()

    import httpx
    from app.services.max.tool_executor import execute_tool

    monkeypatch.setattr(httpx, "get", fake_get)
    result = execute_tool(
        {
            "tool": "web_search",
            "query": "<think>The user asked in English</think>noticias de Colombia hoy",
        },
        founder=True,
    )
    assert captured.get("q") == "noticias de Colombia hoy"
    assert "The user asked" not in (captured.get("q") or "")
    assert result.tool == "web_search"


def test_sanitize_tool_query_helper():
    assert sanitize_tool_query(
        "<think>search English</think>noticias de Colombia hoy"
    ) == "noticias de Colombia hoy"
    assert sanitize_tool_call({"tool": "web_search", "query": BEFORE_REPLY})["query"] == AFTER_REPLY


def test_minimax_sanitizer_uses_central_stripper():
    from app.services.max.ai_router import AIRouter

    router = AIRouter()
    assert router._sanitize_minimax_content(BEFORE_REPLY) == AFTER_REPLY
    payload = {
        "content": BEFORE_REPLY,
        "reasoning_content": "The user asked twice.",
    }
    assert router._sanitize_minimax_content(payload) == AFTER_REPLY


def test_history_sanitizer_drops_reasoning_fields():
    cleaned = sanitize_history_messages([
        {
            "role": "assistant",
            "content": BEFORE_REPLY,
            "reasoning_content": "duplicate English thinking",
        }
    ])
    assert cleaned[0]["content"] == AFTER_REPLY
    assert "reasoning_content" not in cleaned[0]


def test_whitespace_streaming_still_preserves_spaces():
    from app.services.max.guardrails import sanitize_output_streaming

    rendered = "".join(
        sanitize_output_streaming(chunk)
        for chunk in ("Hi", " again. How", " can I help you today?")
    )
    assert "Hi again. How can I help you today?" in rendered
    assert "Hiagain" not in rendered


def test_before_after_transcript_matches_proof_file():
    """Keep the PR proof file honest — same sample the tests assert."""
    proof = Path(__file__).resolve().parents[2] / "reports" / "2026-10-22_minimax_thinking_strip.md"
    text = proof.read_text(encoding="utf-8")
    assert BEFORE_REPLY in text
    assert AFTER_REPLY in text
    assert "¿por qué en inglés?" in text
