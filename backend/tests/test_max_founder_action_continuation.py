"""Founder action continuation: no dangling PDF/email promises."""
from __future__ import annotations

import asyncio
import importlib
import json

from fastapi import BackgroundTasks, Response

from app.services.max.ai_router import AIResponse
from app.services.max.tool_executor import ToolResult

max_router = importlib.import_module("app.routers.max.router")
guardrails = importlib.import_module("app.services.max.guardrails")
continuation = importlib.import_module("app.services.max.founder_action_continuation")

FOUNDER_REQUEST = (
    "Founder action request:\n"
    "1) Create a CRM contact for Marley's Hyattsville Attn Devon\n"
    "2) Use create_engine_quote for Estimate A\n"
    "3) Use create_engine_quote for Estimate B\n"
    "4) Generate both PDFs and email them ONLY to rafa22giraldo@gmail.com\n"
    "Estimate A line: Panel fabrication 10 ea @ 120.00"
)


def test_assistant_announces_future_work_detects_dangling_promise():
    assert continuation.assistant_announces_future_work(
        "Both estimates created. Now generating and emailing both PDFs to x@y.com."
    )


def test_dangling_promise_after_quotes_triggers_send_quote_email(monkeypatch):
    chat_calls: list[int] = []
    executed: list[str] = []

    async def fake_chat(*args, **kwargs):
        chat_calls.append(1)
        n = len(chat_calls)
        if n == 1:
            return AIResponse(
                content=(
                    '```tool\n'
                    '{"tool":"create_engine_quote","customer_name":"Marley","line_items":[{"description":"A","qty":1,"unit":"ea","unit_price":100}]}\n'
                    '{"tool":"create_engine_quote","customer_name":"Marley","line_items":[{"description":"B","qty":1,"unit":"ea","unit_price":200}]}\n'
                    "```"
                ),
                model_used="test-model",
            )
        if n == 2:
            return AIResponse(
                content=(
                    "Both estimates created. Now generating and emailing both PDFs to "
                    "rafa22giraldo@gmail.com."
                ),
                model_used="test-model",
            )
        return AIResponse(
            content=(
                '```tool\n'
                '{"tool":"send_quote_email","quote_id":"q-a","to":"rafa22giraldo@gmail.com"}\n'
                '{"tool":"send_quote_email","quote_id":"q-b","to":"rafa22giraldo@gmail.com"}\n'
                "```"
            ),
            model_used="test-model",
        )

    quote_seq = iter(["q-a", "q-b"])

    def fake_execute(tool_call, *args, **kwargs):
        tool = tool_call.get("tool")
        executed.append(tool)
        if tool == "create_engine_quote":
            qid = next(quote_seq)
            return ToolResult(
                tool=tool,
                success=True,
                result={
                    "quote_id": qid,
                    "quote_number": f"EST-2026-{qid[-1]}",
                    "total": 5605.94,
                },
            )
        if tool == "send_quote_email":
            return ToolResult(
                tool=tool,
                success=True,
                result={
                    "quote_id": tool_call.get("quote_id"),
                    "to": tool_call.get("to"),
                    "quote_number": "EST-2026-A",
                },
            )
        raise AssertionError(f"unexpected tool {tool!r}")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute)
    monkeypatch.setattr(max_router, "is_factual_question", lambda _message: False)

    request = max_router.ChatRequest(message=FOUNDER_REQUEST, history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert "send_quote_email" in executed
    assert continuation.assistant_announces_future_work(response.response) is False
    assert "**Status**" not in response.response or "**Not done**" not in response.response
    assert response.steps
    assert any("Email sent" in s or "emailed" in s for s in response.steps)


def test_blocked_email_ends_with_status_not_done(monkeypatch):
    async def fake_chat(*args, **kwargs):
        return AIResponse(
            content=(
                '```tool\n'
                '{"tool":"send_quote_email","quote_id":"q-1","to":"stranger@example.com"}\n'
                "```\n"
                "Email sent successfully."
            ),
            model_used="test-model",
        )

    def fake_execute(tool_call, *args, **kwargs):
        return ToolResult(
            tool="send_quote_email",
            success=False,
            error="recipient_not_in_whitelist: stranger@example.com",
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute)
    monkeypatch.setattr(max_router, "is_factual_question", lambda _message: False)

    request = max_router.ChatRequest(
        message="Email the estimate PDF to stranger@example.com",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert "**Not done**" in response.response
    assert "whitelist" in response.response.lower() or "blocked" in response.response.lower()
    assert "Now generating" not in response.response


def test_stream_progress_event_shape():
    entry = {
        "tool": "create_engine_quote",
        "success": True,
        "result": {"quote_id": "q-99", "quote_number": "EST-2026-294", "total": 5605.94},
    }
    msg = continuation.format_tool_progress_message(entry)
    evt = max_router._tool_progress_event(entry)
    assert evt["type"] == "progress"
    assert evt["phase"] == "tool"
    assert evt["message"] == msg
    assert "EST-2026-294" in msg
    assert "5,605.94" in msg
