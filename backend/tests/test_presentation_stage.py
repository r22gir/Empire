"""Presentation stage artifacts. No network, no send."""
from pathlib import Path

import pytest

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


def test_chart_uses_the_same_rows_as_the_spoken_answer():
    packed = package_turn(
        "show me last month's revenue",
        "**$4,576.31** collected for Alice. See [the ledger](https://example.com).",
        [{
            "tool": "db_query",
            "success": True,
            "result": {
                "rows": [{"month": "2026-09", "total": "4,576.31", "customer_name": "Alice"}],
            },
        }],
        revenue_reader=lambda: [],
    )
    chart = packed["artifacts"][0]
    assert chart["kind"] == "chart"
    assert chart["payload"]["empty"] is False
    assert chart["payload"]["data"] == [4576.31]
    assert chart["payload"]["labels"] == ["2026-09"]
    assert "*" not in packed["spoken"]
    assert "Alice" not in packed["spoken"]
    assert "the client" in packed["spoken"]
    assert "https://" not in packed["spoken"]
    assert "4,576.31" in packed["spoken"]

    asked = package_turn(
        "who is the client",
        "The client is Alice.",
        [{
            "tool": "db_query",
            "success": True,
            "result": {"rows": [{"customer_name": "Alice", "total": 1}]},
        }],
        revenue_reader=lambda: [],
    )
    assert "Alice" in asked["spoken"]

    named = package_turn(
        "what did Alice pay",
        "Alice paid **$10**.",
        [{
            "tool": "db_query",
            "success": True,
            "result": {"rows": [{"customer_name": "Alice", "amount": 10}]},
        }],
        revenue_reader=lambda: [],
    )
    assert "Alice" in named["spoken"]
    assert "*" not in named["spoken"]

    founder = package_turn(
        "hello",
        "Rafael, the total is **$4**.",
        [],
        revenue_reader=lambda: [],
    )
    assert "Rafael" not in founder["spoken"]
    assert "rafael" not in founder["spoken"].lower()
    assert "the founder" in founder["spoken"]
    assert "*" not in founder["spoken"]

    summed = package_turn(
        "show me last month's revenue",
        "Collected **$4,576.31** for Alice.",
        [{
            "tool": "db_query",
            "success": True,
            "result": {"rows": [{"SUM(amount)": 4576.31, "customer_name": "Alice"}]},
        }],
        revenue_reader=lambda: [],
    )
    assert summed["artifacts"][0]["payload"]["data"] == [4576.31]
    assert summed["artifacts"][0]["payload"]["labels"] == ["Revenue"]
    assert "Alice" not in summed["spoken"]

    quotes = package_turn(
        "show revenue",
        "Line items only.",
        [{
            "tool": "db_query",
            "success": True,
            "result": {"rows": [{"description": "Cushion", "amount": 40}]},
        }],
        revenue_reader=lambda: [],
    )
    assert quotes["artifacts"][0]["payload"]["empty"] is True


def test_revenue_reader_prefers_payments_v2(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager

    from app.services.max.presentation_stage import read_revenue_rows

    db = tmp_path / "rev.db"
    setup = sqlite3.connect(db)
    setup.execute("CREATE TABLE payments (amount REAL, paid_at TEXT, created_at TEXT)")
    setup.execute("INSERT INTO payments VALUES (1, '2026-09-01', '2026-09-01')")
    setup.execute(
        """CREATE TABLE payments_v2 (
            amount REAL, payment_date TEXT, created_at TEXT, payment_type TEXT, status TEXT
        )"""
    )
    setup.execute(
        "INSERT INTO payments_v2 VALUES (4576.31, '2026-09-15', '2026-09-15', 'payment', 'completed')"
    )
    setup.execute(
        "INSERT INTO payments_v2 VALUES (100, '2026-09-15', '2026-09-15', 'refund', 'completed')"
    )
    setup.commit()
    setup.close()

    @contextmanager
    def fake_db():
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr("app.db.database.get_db", fake_db)
    rows = read_revenue_rows()
    assert len(rows) == 1
    assert rows[0]["label"] == "2026-09"
    assert rows[0]["value"] == pytest.approx(4576.31)


def test_avatar_chat_uses_the_tool_path_and_listen_passes_request():
    src = (Path(__file__).resolve().parents[1] / "app" / "routers" / "avatar.py").read_text(encoding="utf-8")
    chat = src.split("async def avatar_chat", 1)[1].split("async def avatar_listen", 1)[0]
    assert "package_turn" in chat
    assert 'presentation=True' in chat
    assert 'canonical_channel="web_cc"' in src
    listen = src.split("async def avatar_listen", 1)[1].split("async def avatar_status", 1)[0]
    assert "avatar_chat(chat_req, request)" in listen
