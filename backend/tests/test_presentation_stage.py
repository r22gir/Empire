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


def test_chart_and_speech_use_the_same_revenue_rows():
    packed = package_turn(
        "show me last month's revenue",
        'September was **$1.00**.\nchart {"type":"bar","title":"Revenue","labels":["2026-09"],"data":[1]}\n✅ Verified',
        [{
            "tool": "db_query",
            "success": True,
            "result": {"rows": [{"month": "2026-09", "total": 1, "customer_name": "Alice"}]},
        }],
        revenue_reader=lambda: [{"label": "2026-09", "value": 4576.31}],
    )
    chart = packed["artifacts"][0]
    assert chart["kind"] == "chart"
    assert chart["payload"]["data"] == [4576.31]
    assert chart["payload"]["labels"] == ["2026-09"]
    assert packed["spoken"] == "Revenue is $4,576.31."
    assert "chart" not in packed["spoken"].lower()
    assert "{" not in packed["spoken"]
    assert "Verified" not in packed["spoken"]
    assert "Alice" not in packed["spoken"]

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
            "result": {"rows": [{"SUM(amount)": 1, "customer_name": "Alice"}]},
        }],
        revenue_reader=lambda: [],
    )
    assert summed["artifacts"][0]["payload"]["empty"] is True
    assert summed["spoken"] == "I don't have payment rows for that window, so I won't invent a total."
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


def test_spoken_line_drops_inline_chart_json_emoji_and_badges():
    from app.services.max.presentation_stage import spoken_text

    model = (
        "September revenue is $4,576.31.\n"
        'chart {"type":"bar","title":"Revenue","labels":["2026-09"],"data":[4576.31]}\n'
        "✅ Verified"
    )
    spoken = spoken_text(model)
    assert spoken == "September revenue is $4,576.31."
    assert "{" not in spoken
    assert "type" not in spoken
    assert "Verified" not in spoken
    assert "✅" not in spoken

    fenced = (
        "Last month came in at $4,576.31.\n"
        "```chart\n"
        '{"type":"bar","title":"Revenue","labels":["2026-09"],"data":[1]}\n'
        "```\n"
        "⚠️ Unverified\n"
        "```mermaid\n"
        "graph TD\n  A-->B\n"
        "```"
    )
    spoken = spoken_text(fenced)
    assert spoken == "Last month came in at $4,576.31."
    assert "graph" not in spoken
    assert "Unverified" not in spoken
    assert "```" not in spoken


def test_revenue_reader_includes_stripe_deposits_once(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager

    from app.services.max.presentation_stage import read_revenue_rows

    db = tmp_path / "rev.db"
    setup = sqlite3.connect(db)
    setup.execute(
        "CREATE TABLE payments (amount REAL, payment_date TEXT, created_at TEXT, invoice_id TEXT)"
    )
    setup.execute("INSERT INTO payments VALUES (50, '2026-08-02', '2026-08-02', 'legacy-only')")
    setup.execute("INSERT INTO payments VALUES (5, '2026-09-02', '2026-09-02', 'stripe-inv')")
    setup.execute(
        """CREATE TABLE payments_v2 (
            amount REAL, payment_date TEXT, created_at TEXT, payment_type TEXT, status TEXT,
            invoice_id TEXT, stripe_session_id TEXT
        )"""
    )
    setup.execute(
        "INSERT INTO payments_v2 VALUES (1, '2026-09-01', '2026-09-01', 'payment', 'completed', 'tiny', NULL)"
    )
    setup.execute(
        "INSERT INTO payments_v2 VALUES (4576.31, '2026-09-15', '2026-09-15', 'payment', 'completed', 'stripe-inv', 'cs_test')"
    )
    setup.execute(
        "INSERT INTO payments_v2 VALUES (100, '2026-09-15', '2026-09-15', 'refund', 'completed', 'refund-inv', NULL)"
    )
    setup.execute(
        """CREATE TABLE invoices (
            id TEXT, amount_paid REAL, total REAL, status TEXT, payment_status TEXT,
            paid_at TEXT, created_at TEXT, stripe_checkout_session_id TEXT
        )"""
    )
    setup.execute(
        "INSERT INTO invoices VALUES ('stripe-inv', 4576.31, 4576.31, 'paid', 'paid', '2026-09-15', '2026-09-15', 'cs_test')"
    )
    setup.execute(
        "INSERT INTO invoices VALUES ('missed', 4576.31, 4576.31, 'paid', 'paid', '2026-09-20', '2026-09-20', 'cs_missed')"
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
    rows = {row["label"]: row["value"] for row in read_revenue_rows()}
    # Sept: $1 tiny payment + $4,576.31 already in payments_v2 + the same Stripe
    # invoice is not added again + a Stripe deposit the ledger missed.
    assert rows["2026-09"] == pytest.approx(1 + 4576.31 + 4576.31)
    assert rows["2026-08"] == pytest.approx(50)


def test_sql_error_retries_once_without_the_missing_column(tmp_path, monkeypatch):
    import sqlite3

    from app.services.max.presentation_stage import REVENUE_SCHEMA_HINT, sql_retry_without_missing_column
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response
    from app.services.max.tool_executor import _db_query

    query = "SELECT SUM(amount) AS total FROM payments WHERE status = 'completed'"
    rewritten = sql_retry_without_missing_column(query, "no such column: status")
    assert rewritten is not None
    assert "status" not in rewritten.lower()
    assert "payments" in rewritten.lower()

    db = tmp_path / "empire.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE payments (amount REAL, payment_date TEXT)")
    conn.execute("INSERT INTO payments VALUES (4576.31, '2026-09-15')")
    conn.commit()
    conn.close()
    monkeypatch.setattr("app.services.max.tool_executor.dp.db_path", lambda name="empire.db": db)
    result = _db_query({"query": query})
    from app.services.max.tool_executor import TOOLS_DOC
    assert "NO status column" in TOOLS_DOC
    assert "payments_v2" in TOOLS_DOC

    assert result.success is True
    assert result.result["rows"][0]["total"] == pytest.approx(4576.31)

    hinted = _db_query({"query": "SELECT status FROM payments"})
    assert hinted.success is False
    assert "no such column: status" in hinted.error
    assert "NO status column" in hinted.error
    assert REVENUE_SCHEMA_HINT.split(".")[0] in hinted.error

    recovered, _warnings = enforce_runtime_truth_response(
        "show revenue",
        "Revenue is on the books.",
        [
            {"tool": "db_query", "success": False, "error": "no such column: status"},
            {"tool": "db_query", "success": True, "result": {"rows": [{"total": 4576.31}]}},
        ],
    )
    assert "I have not run that yet" not in recovered
    blocked, _warnings = enforce_runtime_truth_response(
        "show revenue",
        "Revenue is on the books.",
        [{"tool": "db_query", "success": False, "error": "no such column: status"}],
    )
    assert blocked.startswith("I have not run that yet.")


def test_avatar_chat_uses_the_tool_path_and_listen_passes_request():
    src = (Path(__file__).resolve().parents[1] / "app" / "routers" / "avatar.py").read_text(encoding="utf-8")
    chat = src.split("async def avatar_chat", 1)[1].split("async def avatar_listen", 1)[0]
    assert "package_turn" in chat
    assert 'presentation=True' in chat
    assert 'canonical_channel="web_cc"' in src
    listen = src.split("async def avatar_listen", 1)[1].split("async def avatar_status", 1)[0]
    assert "avatar_chat(chat_req, request)" in listen
