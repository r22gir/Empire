"""Regression: founder imperative actions must not hit research uncertainty fallback.

Reproduces Web MAX turning create-estimate / create_contact flows into
"I don't have verified information on \"<entire prompt>\" from reliable Empire sources".
"""
from __future__ import annotations

import asyncio
import importlib

from fastapi import BackgroundTasks, Response

from app.services.max.ai_router import AIResponse
from app.services.max.tool_executor import ToolResult

max_router = importlib.import_module("app.routers.max.router")
guardrails = importlib.import_module("app.services.max.guardrails")

REPRO1_MESSAGE = (
    "Create two NEW estimates (treat as new projects) for Marley's Hyattsville, Attn Devon. "
    "Estimate A — U-banquette: U-banquette seat backs, plain large panels: 72.65 sf @ $45.00 = $3,269.25. "
    "Save both as estimates and generate the client PDFs. Then email both PDFs ONLY to the founder at "
    "rafa22giraldo@gmail.com."
)

REPRO2_MESSAGE = (
    "Founder action request:\n"
    "1) Create a CRM contact for Marley's Hyattsville Attn Devon\n"
    "2) Use create_engine_quote to create Estimate A with the line items below\n"
    "3) Use create_engine_quote to create Estimate B with the line items below\n"
    "4) Generate both PDFs and email them ONLY to rafa22giraldo@gmail.com\n"
    "Estimate A line: Panel fabrication 10 ea @ 120.00"
)


def test_should_not_defer_on_estimate_action_request():
    assert guardrails.is_imperative_action_request(REPRO1_MESSAGE)
    assert not guardrails.should_defer_uncertain(REPRO1_MESSAGE)


def test_should_not_defer_after_successful_write_tools():
    assert not guardrails.should_defer_uncertain(
        REPRO2_MESSAGE,
        tool_results=[{"tool": "create_contact", "success": True, "result": {"contact_id": "c-1"}}],
    )


def test_uncertainty_fallback_truncates_topic():
    long = "x" * 500
    out = guardrails.uncertainty_fallback(long)
    assert long not in out
    assert "…" in out or len(long) > guardrails._UNCERTAINTY_FALLBACK_TOPIC_MAX_LEN


def test_founder_action_tools_remaining_after_contact_only():
    remaining = guardrails.founder_action_tools_remaining(
        REPRO2_MESSAGE,
        [{"tool": "create_contact", "success": True, "result": {"contact_id": "c-1"}}],
    )
    assert "create_engine_quote" in remaining


def test_repro1_search_contacts_does_not_replace_with_research_fallback(monkeypatch):
    chat_calls: list[int] = []

    async def fake_chat(*args, **kwargs):
        chat_calls.append(1)
        if len(chat_calls) == 1:
            blocks = "\n".join(
                f'{{"tool": "search_contacts", "search": "{term}"}}'
                for term in ("Devon", "Marley", "Hyattsville")
            )
            return AIResponse(
                content=f"```tool\n{blocks}\n```",
                model_used="minimax-MiniMax-M3",
            )
        return AIResponse(
            content="Both estimates are saved; PDFs are ready for founder email.",
            model_used="minimax-MiniMax-M3",
        )

    def fake_execute(tool_call, *args, **kwargs):
        tool = tool_call.get("tool")
        if tool == "search_contacts":
            return ToolResult(tool=tool, success=True, result={"contacts": [], "count": 0})
        if tool == "web_search":
            return ToolResult(tool=tool, success=True, result={"results": []})
        raise AssertionError(f"unexpected tool {tool!r}")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute)
    monkeypatch.setattr(max_router, "is_factual_question", lambda _message: False)

    request = max_router.ChatRequest(message=REPRO1_MESSAGE, history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert "reliable Empire sources" not in response.response
    assert "Hermes memory" not in response.response
    assert "Both estimates are saved" in response.response
    tools = [r.get("tool") for r in (response.tool_results or [])]
    assert tools.count("search_contacts") == 3


def test_repro2_continues_to_create_engine_quote_after_contact(monkeypatch):
    chat_calls: list[int] = []
    executed: list[str] = []

    async def fake_chat(*args, **kwargs):
        chat_calls.append(1)
        n = len(chat_calls)
        if n == 1:
            return AIResponse(
                content='```tool\n{"tool":"create_contact","name":"Marley Hyattsville","type":"client"}\n```',
                model_used="minimax-MiniMax-M3",
            )
        if n == 2:
            return AIResponse(content="Contact created. Proceeding with quotes.", model_used="minimax-MiniMax-M3")
        if n == 3:
            return AIResponse(
                content=(
                    '```tool\n{"tool":"create_engine_quote","customer_name":"Marley",'
                    '"line_items":[{"description":"Panel fabrication","qty":10,"unit":"ea","unit_price":120}]}\n```'
                ),
                model_used="minimax-MiniMax-M3",
            )
        return AIResponse(content="Estimate A created in quotes_v2.", model_used="minimax-MiniMax-M3")

    def fake_execute(tool_call, *args, **kwargs):
        tool = tool_call.get("tool")
        executed.append(tool)
        if tool == "create_contact":
            return ToolResult(tool=tool, success=True, result={"contact_id": "crm-99", "name": tool_call.get("name")})
        if tool == "create_engine_quote":
            return ToolResult(
                tool=tool,
                success=True,
                result={"quote_id": "EST-A", "store": "quotes_v2", "engine": "pricing_engine_v1"},
            )
        raise AssertionError(f"unexpected tool {tool!r}")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute)
    monkeypatch.setattr(max_router, "is_factual_question", lambda _message: False)

    request = max_router.ChatRequest(message=REPRO2_MESSAGE, history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert "reliable Empire sources" not in response.response
    assert "create_contact" in executed
    assert "create_engine_quote" in executed
    assert "Estimate A created" in response.response or "quotes_v2" in response.response.lower()
