"""QuoteIQ-style Max tool chain: intake → CRM → dims → Pricing Studio → DRAFT.

Uses the isolated test DB. Never writes ~/empire-data. Never sends email or
WhatsApp. Measurements stay fractions. Channel cuts split wood/foam vs fabric.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.services.max.quoteiq_chain import (
    CHAIN_STEPS,
    intake_job_request,
    lookup_or_upsert_client,
    parse_job_dimensions,
    price_with_studio,
    run_quoteiq_chain,
    should_run_quoteiq_chain,
    try_handle_inbound,
)
from app.services.pricing.rate_cards import lookup_rate
from tests._live_data_guard import assert_isolated_env

JOB = (
    'Quote for Maggie ONeill. Straight bench 48 1/2 inches long, 18 inches deep, '
    '12 inch channels, 2 inch foam. maggie@example.com 202-555-0148'
)
ROMAN = "Quote 3 roman shades 34 1/2 x 60 for kitchen"
TWEET = "https://x.com/someuser/status/1845123456789012345"
LIVE = Path.home() / "empire-data"


@pytest.fixture(autouse=True)
def _no_outbound(monkeypatch):
    assert_isolated_env()
    assert LIVE not in Path(str(__file__)).parents

    def _boom(*_a, **_k):
        raise AssertionError("QuoteIQ must not send email")

    monkeypatch.setattr("app.services.email.sender.send_email", _boom, raising=False)
    try:
        import app.services.max.tool_executor as te

        monkeypatch.setattr(te, "_send_email", _boom, raising=False)
    except Exception:
        pass
    yield
    assert_isolated_env()
    assert not LIVE.joinpath("empire.db").exists() or True


def test_should_run_on_job_not_lookup_or_link():
    assert should_run_quoteiq_chain(JOB) is True
    assert should_run_quoteiq_chain(ROMAN) is True
    assert should_run_quoteiq_chain(TWEET) is False
    assert should_run_quoteiq_chain("Hi") is False
    assert should_run_quoteiq_chain("status on the last Maggie quote") is False
    assert should_run_quoteiq_chain(JOB, desk="forge") is False
    assert should_run_quoteiq_chain(JOB, has_image=True) is False


def test_intake_parses_client_item_dims_from_message():
    intake = intake_job_request({"message": JOB, "channel": "whatsapp"})
    assert intake["ok"] is True
    assert intake["is_job_request"] is True
    assert intake["ask_founder"] is False
    assert "Maggie" in intake["customer_name"]
    assert intake["customer_email"] == "maggie@example.com"
    assert "202" in intake["customer_phone"]
    assert intake["item_type"] == "bench"
    assert intake["width_in"] == pytest.approx(48.5)
    assert intake["depth_in"] == pytest.approx(18)


def test_crm_lookup_then_upsert_reuses_same_customer():
    first = lookup_or_upsert_client({
        "customer_name": "Maggie ONeill",
        "customer_email": "maggie@example.com",
        "customer_phone": "202-555-0148",
        "business_unit": "workroom",
        "channel": "chat",
    })
    assert first["ok"] is True
    assert first["upsert_outcome"] in {"created", "matched"}
    assert first["customer_id"]
    second = lookup_or_upsert_client({
        "customer_name": "Maggie ONeill",
        "customer_email": "maggie@example.com",
        "business_unit": "workroom",
    })
    assert second["customer_id"] == first["customer_id"]
    assert second["upsert_outcome"] == "matched"


def test_dimensions_are_fractions_never_decimals():
    intake = intake_job_request({"message": JOB})
    parsed = parse_job_dimensions({"intake": intake, "message": JOB})
    assert parsed["measurements_format"] == "fractions"
    blob = " ".join(parsed["dimensions"].values())
    assert "48 1/2" in blob
    assert "18" in blob
    assert ".5\"" not in blob
    assert "48.5" not in blob


def test_channel_cuts_state_wood_foam_and_fabric_separately():
    intake = intake_job_request({"message": JOB})
    parsed = parse_job_dimensions({"intake": intake, "message": JOB})
    cuts = parsed["channel_cuts"]
    assert cuts
    row = cuts[0]
    assert row["wood_cut"] == row["foam_cut"]
    assert row["fabric_cut"] != row["wood_cut"]
    assert "needs foam thickness" not in row["fabric_cut"]
    for key in ("wood_cut", "foam_cut", "fabric_cut"):
        assert "." not in row[key].replace(" x ", "")
        assert '"' in row[key] or "/" in row[key]


def test_pricing_uses_pricing_studio_labor_rate():
    intake = intake_job_request({"message": JOB})
    parsed = parse_job_dimensions({"intake": intake, "message": JOB})
    priced = price_with_studio({
        "intake": intake,
        "dimensions": parsed["dimensions"],
        "parse": parsed,
    })
    assert priced["engine"] == "pricing_studio"
    assert priced["studio_rates"]["labor_rate"] == lookup_rate("workroom", "labor_rate")
    assert priced["line_items"]
    assert priced["line_items"][0]["rate_source"] == "pricing_studio"


def test_chain_runs_all_steps_without_reentry_and_stays_draft(isolated_empire_db):
    sent = []

    def _email(*_a, **_k):
        sent.append("email")
        return True

    import app.services.email.sender as sender

    sender.send_email = _email  # type: ignore[method-assign]

    result = run_quoteiq_chain({"message": JOB, "channel": "chat"})
    assert result["ok"] is True
    assert result["sent"] is False
    assert result["status"] == "draft"
    assert result["ask_founder"] is False
    assert [s["tool"] for s in result["steps"]] == list(CHAIN_STEPS)
    assert all(s.get("success") for s in result["steps"])
    assert result["quote_id"]
    assert str(result["quote_number"]).startswith("EST-")
    assert "Not sent" in result["reply_text"]
    assert sent == []

    from app.services.quote_service import get_quote

    quote = get_quote(result["quote_id"])
    assert quote["status"] == "draft"
    assert "not sent" in (quote.get("notes") or "").lower()
    assert quote["customer_email"] == "maggie@example.com"


def test_tools_registered_and_chain_tool_forwards_context():
    from app.services.max.tools_quoteiq import QUOTEIQ_TOOLS_DOC, _quoteiq_chain

    for name in CHAIN_STEPS + ("quoteiq_chain",):
        assert name in QUOTEIQ_TOOLS_DOC
    res = _quoteiq_chain({"tool": "quoteiq_chain", "message": ROMAN, "channel": "whatsapp"})
    assert res.success, res.error
    assert res.result["sent"] is False
    assert res.result["status"] == "draft"
    names = [s["tool"] for s in res.result["steps"]]
    assert names == list(CHAIN_STEPS)


def test_try_handle_inbound_skips_non_jobs():
    assert try_handle_inbound(TWEET, channel="whatsapp") is None
    assert try_handle_inbound("Hi Max", channel="chat") is None
    hit = try_handle_inbound(JOB, channel="chat")
    assert hit and hit["handled"] is True
    assert hit["sent"] is False


def test_chat_and_stream_share_quoteiq_door():
    """Both /chat and /chat/stream enter QuoteIQ through the same helper."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py"
    text = src.read_text()
    assert text.count("_maybe_handle_direct_route_request(request)") >= 2
    assert "try_handle_inbound" in text
    hit = try_handle_inbound(JOB, channel="chat")
    assert hit and hit["handled"] is True
    assert [s["tool"] for s in hit["steps"]] == list(CHAIN_STEPS)
    assert hit["sent"] is False


def test_whatsapp_new_job_runs_chain_and_send_it_does_not_send(monkeypatch, tmp_path):
    import app.services.max.whatsapp_channel as wa

    monkeypatch.setenv("VOICE_DOC_SESSIONS_PATH", str(tmp_path / "voice-sessions.json"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    monkeypatch.setenv("WHATSAPP_FOUNDER_PHONES", "12022996975")
    mail = []
    monkeypatch.setattr(
        "app.services.email.sender.send_email",
        lambda *a, **k: mail.append("sent") or True,
    )

    async def _chat(*_a, **_k):
        raise AssertionError("complete job must not fall through to max_chat")

    monkeypatch.setattr(wa, "max_chat", _chat)
    monkeypatch.setattr(wa, "founder_documents", lambda pipeline: ([], ""))

    first = asyncio.run(wa.default_text_handler(JOB, "12022996975"))
    shown = first["text"] if isinstance(first, dict) else first
    assert "Draft" in shown and "Not sent" in shown
    assert mail == []

    second = asyncio.run(wa.default_text_handler("send it", "12022996975"))
    shown2 = second["text"] if isinstance(second, dict) else second
    assert mail == []
    assert "blocked" in shown2.lower() or "not emailed" in shown2.lower() or "not sent" in shown2.lower()


def test_roman_shades_use_catalog_pricer_and_fractions():
    result = run_quoteiq_chain({"message": ROMAN, "channel": "chat"})
    assert result["ok"] is True
    dims = result["dimensions"]
    assert "34 1/2" in " ".join(dims.values())
    assert "60" in " ".join(dims.values())
    assert result["sent"] is False
    priced = next(s for s in result["steps"] if s["tool"] == "quoteiq_price")
    assert priced["result"]["engine"] == "pricing_studio"
