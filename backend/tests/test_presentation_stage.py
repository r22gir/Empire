"""Presentation stage artifacts. No network, no send."""
from pathlib import Path

from app.services.max.presentation_stage import (
    CLIENT_BRAND,
    package_turn,
    stage_event,
)


def test_spoken_line_drops_fences_and_keeps_two_sentences():
    packed = package_turn(
        "hello",
        "Hi there. Second sentence. Third should drop.\n```chart\n"
        '{"type":"bar","title":"Jobs","labels":["A"],"data":[1]}\n```',
        [],
        revenue_reader=lambda: [],
    )
    assert packed["spoken"].startswith("Hi there.")
    assert "Third" not in packed["spoken"]
    assert "```" not in packed["spoken"]
    assert packed["artifacts"][0]["kind"] == "chart"
    assert packed["artifacts"][0]["payload"]["title"] == "Jobs"


def test_present_builds_slides_and_revenue_uses_real_rows_only():
    packed = package_turn(
        "present this week's numbers",
        "Here is the week.",
        [],
        revenue_reader=lambda: [{"label": "2026-09", "value": 120.0}],
    )
    assert packed["slides"]
    assert packed["slides"][0]["artifact"]["kind"] == "chart"
    assert packed["slides"][0]["artifact"]["payload"]["data"] == [120.0]
    assert packed["spoken"].startswith("I'll walk through")

    empty = package_turn(
        "show me last month's revenue",
        "Nothing on file.",
        [],
        revenue_reader=lambda: [],
    )
    assert empty["artifacts"][0]["payload"]["empty"] is True
    assert empty["artifacts"][0]["payload"]["data"] == []
    assert "invent" in empty["artifacts"][0]["narration"]


def test_quote_draft_is_unsent_and_founder_name_is_scrubbed():
    packed = package_turn(
        "pull up quote 123",
        "Draft is ready.",
        [{
            "tool": "create_quick_quote",
            "success": True,
            "result": {
                "quote_number": "Q-123",
                "customer_name": "Rafael",
                "line_items": [{"description": "Cushion", "amount": 40}],
                "total": 40,
                "missing": [],
                "sent": True,
            },
        }],
        revenue_reader=lambda: [],
    )
    artifact = packed["artifacts"][0]
    assert artifact["kind"] == "quote_draft"
    assert artifact["payload"]["sent"] is False
    assert artifact["payload"]["customer_name"] == ""
    assert artifact["brand"] == CLIENT_BRAND
    assert "Rafael" not in str(artifact)


def test_live_voice_stage_event_carries_the_same_artifact():
    event = stage_event(
        "get_quote",
        {"success": True, "result": {"quote_number": "Q-9", "total": 10, "line_items": []}},
        "pull up quote 9",
    )
    assert event["artifacts"][0]["kind"] == "quote"
    assert event["artifacts"][0]["payload"]["quote_number"] == "Q-9"


def test_avatar_chat_uses_the_tool_path_and_listen_passes_request():
    src = (Path(__file__).resolve().parents[1] / "app" / "routers" / "avatar.py").read_text(encoding="utf-8")
    chat = src.split("async def avatar_chat", 1)[1].split("async def avatar_listen", 1)[0]
    assert "package_turn" in chat
    assert 'presentation=True' in chat
    assert 'canonical_channel="web_cc"' in src
    listen = src.split("async def avatar_listen", 1)[1].split("async def avatar_status", 1)[0]
    assert "avatar_chat(chat_req, request)" in listen
