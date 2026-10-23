"""Desk prompt cache order: fixed first, changing last; pin per desk; prefix stable."""
from __future__ import annotations

from datetime import datetime

from app.services.max.ai_router import DESK_MODEL_ROUTING, AIModel
from app.services.max.desk_prompt import (
    CHANGING_START_MARKER,
    DESK_CACHE_PINS,
    FIXED_END_MARKER,
    assemble_desk_chat_messages,
    assemble_desk_prompt_parts,
    measure_desk_prefix_stability,
    resolve_desk_cache_pin,
)


CONFIG = {
    "system_prompt": (
        "You are Kai on ForgeDesk. Follow Empire Workroom rules. "
        "Never invent dimensions. Never send to clients."
    ),
}


def test_pins_match_desk_model_routing():
    for desk_id, model in DESK_MODEL_ROUTING.items():
        pin = resolve_desk_cache_pin(desk_id)
        assert pin, desk_id
        assert pin["model"] == model.value
        assert pin["cacheable"] is True
        assert DESK_CACHE_PINS[desk_id]["model"] == model.value
    assert resolve_desk_cache_pin("finance") is None
    assert AIModel.MINIMAX.value == "minimax"


def test_fixed_content_comes_before_changing_values():
    persona = "PERSONA_RULES"
    conduct = "## Code of Conduct — Forge"
    tools = "## Available Tools (1 total)\n- search_quotes"
    date = "October 23, 2026"
    live = "Current forge desk tasks: 3 to-do"
    fixed, changing = assemble_desk_prompt_parts(
        persona=persona,
        conduct=conduct,
        tools=tools,
        pin={"provider": "minimax", "model": "minimax"},
        date_text=date,
        live_context=live,
        order="cache",
    )
    assert fixed.index(persona) < fixed.index(conduct) < fixed.index(tools)
    assert "provider=minimax" in fixed
    assert date not in fixed
    assert live not in fixed
    assert date in changing
    assert live in changing
    assert FIXED_END_MARKER in fixed
    assert CHANGING_START_MARKER in changing
    blob = fixed + "\n\n" + changing
    assert blob.index(FIXED_END_MARKER) < blob.index(CHANGING_START_MARKER)
    assert blob.index(tools) < blob.index(date)
    assert blob.index(tools) < blob.index(live)


def test_legacy_order_puts_live_context_before_tools():
    fixed, changing = assemble_desk_prompt_parts(
        persona="PERSONA",
        conduct="CONDUCT",
        tools="TOOLS",
        date_text="October 23, 2026",
        live_context="LIVE_COUNTS",
        order="legacy",
    )
    blob = fixed + "\n\n" + changing
    assert blob.index("LIVE_COUNTS") < blob.index("TOOLS")


def test_chat_path_puts_user_message_last_and_keeps_prefix():
    first = assemble_desk_chat_messages(
        "forge",
        "Need a drawing for the mock bench.",
        now=datetime(2026, 10, 22, 8, 0, 0),
        task_counts={"todo": 1, "in_progress": 0, "waiting": 0, "done": 0},
        config=CONFIG,
    )
    second = assemble_desk_chat_messages(
        "forge",
        "Different user turn about an invoice.",
        now=datetime(2026, 10, 23, 18, 0, 0),
        task_counts={"todo": 9, "in_progress": 2, "waiting": 1, "done": 3},
        config=CONFIG,
    )
    assert first["messages"][0]["role"] == "system"
    assert first["messages"][-1]["role"] == "user"
    assert first["messages"][-1]["content"] == "Need a drawing for the mock bench."
    assert second["messages"][-1]["content"] == "Different user turn about an invoice."
    assert first["prefix_hash"] == second["prefix_hash"]
    assert first["fixed_prefix"] == second["fixed_prefix"]
    assert first["changing_suffix"] != second["changing_suffix"]
    assert "October 22, 2026" in first["changing_suffix"]
    assert "October 23, 2026" in second["changing_suffix"]
    assert first["cache_pin"]["provider"] == "minimax"
    assert first["cacheable"] is True


def test_before_after_prefix_stability_numbers():
    report = measure_desk_prefix_stability("forge", config=CONFIG)
    before = report["before"]
    after = report["after"]
    assert before["order"] == "legacy"
    assert after["order"] == "cache"
    assert after["lcp_chars"] > before["lcp_chars"]
    assert after["prefix_hash_stable"] is True
    assert after["fixed_marker_in_lcp"] is True
    assert after["cache_hit"] is True
    assert before["fixed_marker_in_lcp"] is False
    assert before["cache_hit"] is False
    assert report["lcp_gain_chars"] > 0
    assert after["user_last_a"] and after["user_last_b"]
