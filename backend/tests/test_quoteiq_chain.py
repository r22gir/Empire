"""QuoteIQ-style Max tool chain: intake → dims → Pricing Studio → CRM → DRAFT.

Uses the isolated test DB. Never writes ~/empire-data. Never sends email or
WhatsApp. Measurements stay fractions. Channel cuts split wood/foam vs fabric.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.config.fabric_cut_allowance import lookup_fabric_allowance
from app.config.workroom_billing import BILLED_BY_EMPIRE, normalize_billed_by
from app.db.database import get_db
from app.services.max.quoteiq_chain import (
    CHAIN_STEPS,
    intake_job_request,
    looks_like_quote_request,
    lookup_or_upsert_client,
    parse_job_dimensions,
    price_with_studio,
    quoteiq_founder_allowed,
    run_quoteiq_chain,
    should_run_quoteiq_chain,
    try_handle_inbound,
)
from tests._live_data_guard import assert_isolated_env

JOB = (
    "Quote for Maggie ONeill. Straight bench 48 1/2 inches long, 18 inches deep, "
    "12 inch channels, 2 inch foam. maggie@example.com 15555550148"
)
ROMAN = "Quote 3 roman shades 34 1/2 x 60 for kitchen"
CASUAL_DIMS = "the roman shades are 34 1/2 x 60, looks good"
BARE_WXH = "34 1/2 x 60"
TWEET = "https://x.com/someuser/status/1845123456789012345"
FOUNDER_WA = "12022996975"
CLIENT_WA = "15555550100"
LIVE = Path.home() / "empire-data"


@pytest.fixture(autouse=True)
def _no_outbound(monkeypatch):
    assert_isolated_env()
    assert LIVE not in Path(str(__file__)).parents

    def _boom(*_a, **_k):
        raise AssertionError("QuoteIQ must not send email")

    monkeypatch.setattr("app.services.email.sender.send_email", _boom, raising=False)
    yield
    assert_isolated_env()
    assert not LIVE.joinpath("empire.db").exists()


def _quote_count() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT count(*) AS n FROM quotes_v2").fetchone()
    return int(row["n"] if row["n"] is not None else row[0])


def _customer_by_email(email: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM customers WHERE lower(trim(email)) = lower(?)",
            (email,),
        ).fetchall()
    return [dict(r) for r in rows]


def test_should_run_requires_phrase_and_item_and_dim():
    assert should_run_quoteiq_chain(JOB) is True
    assert should_run_quoteiq_chain(ROMAN) is True
    assert should_run_quoteiq_chain(TWEET) is False
    assert should_run_quoteiq_chain("Hi") is False
    assert should_run_quoteiq_chain("status on the last Maggie quote") is False
    assert should_run_quoteiq_chain(JOB, desk="forge") is False
    assert should_run_quoteiq_chain(JOB, has_image=True) is False
    assert should_run_quoteiq_chain(BARE_WXH) is False
    assert should_run_quoteiq_chain(CASUAL_DIMS) is False
    assert looks_like_quote_request(BARE_WXH) is False
    assert looks_like_quote_request(CASUAL_DIMS) is False
    assert looks_like_quote_request(ROMAN) is True


def test_casual_chat_with_dims_does_not_trigger():
    assert try_handle_inbound(CASUAL_DIMS, channel="web_cc", founder=True) is None
    assert try_handle_inbound(BARE_WXH, channel="web_cc", founder=True) is None
    assert try_handle_inbound("Maggie wants a bench 48 x 18", channel="web_cc", founder=True) is None


def test_client_and_unknown_senders_are_gated():
    assert quoteiq_founder_allowed(channel="client", founder=False) is False
    assert quoteiq_founder_allowed(channel="unknown") is False
    assert quoteiq_founder_allowed(channel="storefront") is False
    assert quoteiq_founder_allowed(channel="whatsapp", sender=CLIENT_WA, founder=False) is False
    assert quoteiq_founder_allowed(channel="web_cc", founder=True) is True
    assert try_handle_inbound(ROMAN, channel="client", founder=False) is None
    assert try_handle_inbound(ROMAN, channel="unknown") is None
    assert try_handle_inbound(ROMAN, channel="whatsapp", sender=CLIENT_WA, founder=False) is None


def test_intake_parses_client_item_dims_from_message():
    intake = intake_job_request({"message": JOB, "channel": "whatsapp"})
    assert intake["ok"] is True
    assert intake["is_job_request"] is True
    assert intake["ask_founder"] is False
    assert "Maggie" in intake["customer_name"]
    assert intake["customer_email"] == "maggie@example.com"
    assert "1555" in intake["customer_phone"]
    assert intake["item_type"] == "bench"
    assert intake["width_in"] == pytest.approx(48.5)
    assert intake["depth_in"] == pytest.approx(18)


def test_crm_lookup_then_upsert_reuses_same_customer(isolated_empire_db):
    first = lookup_or_upsert_client({
        "customer_name": "Maggie ONeill",
        "customer_email": "maggie@example.com",
        "customer_phone": "15555550148",
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


def test_crm_does_not_overwrite_filled_fields(isolated_empire_db):
    first = lookup_or_upsert_client({
        "customer_name": "Maggie ONeill",
        "customer_email": "maggie@example.com",
        "customer_phone": "15555550148",
        "customer_address": "1 Oak St",
        "business_unit": "workroom",
    })
    assert first["upsert_outcome"] == "created"
    second = lookup_or_upsert_client({
        "customer_name": "Someone Else",
        "customer_email": "maggie@example.com",
        "customer_phone": "15555550999",
        "customer_address": "99 Pine Ave",
        "business_unit": "workroom",
    })
    assert second["customer_id"] == first["customer_id"]
    assert second["customer_name"] == "Maggie ONeill"
    assert "15555550148" in (second["customer_phone"] or "").replace("-", "").replace(" ", "")
    assert second["customer_address"] == "1 Oak St"
    assert second["mismatches"]
    rows = _customer_by_email("maggie@example.com")
    assert len(rows) == 1
    assert rows[0]["name"] == "Maggie ONeill"
    assert "0148" in (rows[0]["phone"] or "")


def test_no_customer_from_email_only(isolated_empire_db):
    result = lookup_or_upsert_client({
        "customer_email": "only@example.com",
        "business_unit": "workroom",
    })
    assert result["upsert_outcome"] == "skipped"
    assert result["customer_id"] is None
    assert _customer_by_email("only@example.com") == []


def test_crm_never_matches_name_only(isolated_empire_db):
    lookup_or_upsert_client({
        "customer_name": "Maggie ONeill",
        "customer_email": "maggie@example.com",
        "customer_phone": "15555550148",
    })
    name_only = lookup_or_upsert_client({
        "customer_name": "Maggie ONeill",
        "business_unit": "workroom",
    })
    assert name_only["upsert_outcome"] == "skipped"
    assert name_only["customer_id"] is None


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
    assert "18\"" not in row["wood_cut"] or "12" in row["wood_cut"]
    assert parsed["channel_remainder"]
    assert "leftover" in (parsed["channel_remainder_note"] or "").lower()
    for key in ("wood_cut", "foam_cut", "fabric_cut"):
        assert "." not in row[key].replace(" x ", "")
        assert '"' in row[key] or "/" in row[key]
    # Current rule: 12" channel stays 12", not the old 18" add-on.
    assert "12" in row["wood_cut"]
    assert "18\"" not in row["wood_cut"].split(" x ")[0]


def test_allowance_table_is_total_per_dimension_not_per_side():
    """allowance_in is total extra on EACH wood dim (wrap both faces + sew)."""
    row = lookup_fabric_allowance(2.0)
    assert row["allowance_in"] == 5.0  # 2×2" foam + 1" sew, not 2.5 per side
    intake = intake_job_request({"message": JOB})
    parsed = parse_job_dimensions({"intake": intake, "message": JOB})
    assert "total extra added to each wood dimension" in parsed["allowance_semantics"]
    fabric = parsed["channel_cuts"][0]["fabric_cut"]
    # 12" channel + 5" total = 17"; 18" deep + 5" = 23"
    assert "17" in fabric
    assert "23" in fabric


def test_pricing_bench_has_no_invented_line():
    intake = intake_job_request({"message": JOB})
    parsed = parse_job_dimensions({"intake": intake, "message": JOB})
    priced = price_with_studio({
        "intake": intake,
        "dimensions": parsed["dimensions"],
        "parse": parsed,
    })
    assert priced["engine"] == "pricing_studio"
    assert priced["has_real_price"] is False
    assert priced["line_items"] == []
    assert priced["need"] == "a Pricing Studio price"


def test_incomplete_bench_replies_need_and_creates_nothing(isolated_empire_db):
    before = _quote_count()
    customers_before = _customer_by_email("maggie@example.com")
    result = run_quoteiq_chain({"message": JOB, "channel": "web_cc"})
    assert result["handled"] is True
    assert result["sent"] is False
    assert result["created"] is False
    assert result["quote_id"] is None
    assert result["reply_text"].startswith("need ")
    assert "Pricing Studio" in result["reply_text"]
    assert "quoteiq_crm_upsert" not in [s["tool"] for s in result["steps"]]
    assert "quoteiq_draft_quote" not in [s["tool"] for s in result["steps"]]
    assert _quote_count() == before
    assert _customer_by_email("maggie@example.com") == customers_before


def test_chain_runs_all_steps_without_reentry_and_stays_draft(isolated_empire_db, monkeypatch):
    sent = []

    def _email(*_a, **_k):
        sent.append("email")
        return True

    monkeypatch.setattr("app.services.email.sender.send_email", _email, raising=False)

    result = run_quoteiq_chain({"message": ROMAN, "channel": "web_cc"})
    assert result["ok"] is True
    assert result["sent"] is False
    assert result["status"] == "draft"
    assert result["ask_founder"] is False
    assert [s["tool"] for s in result["steps"]] == list(CHAIN_STEPS)
    assert all(s.get("success") for s in result["steps"])
    assert result["quote_id"]
    assert str(result["quote_number"]).startswith("EST-")
    assert "Not sent" in result["reply_text"]
    assert result["brand"] == "Empire Workroom"
    assert result["billed_by"] == BILLED_BY_EMPIRE
    assert sent == []

    from app.services.quote_service import get_quote

    quote = get_quote(result["quote_id"])
    assert quote["status"] == "draft"
    assert "not sent" in (quote.get("notes") or "").lower()
    assert "Empire Workroom" in (quote.get("notes") or "")
    assert normalize_billed_by(quote.get("billed_by")) == BILLED_BY_EMPIRE
    assert "Customer" not in (quote.get("customer_name") or "")
    assert "Item" not in (quote.get("project_name") or "")


def test_dedupe_returns_same_quote_id_within_24h(isolated_empire_db):
    first = run_quoteiq_chain({"message": ROMAN, "channel": "web_cc"})
    second = run_quoteiq_chain({"message": ROMAN, "channel": "web_cc"})
    assert first["quote_id"]
    assert second["quote_id"] == first["quote_id"]
    assert second.get("deduped") is True
    assert _quote_count() == 1


def test_tools_registered_and_chain_forwards_context(isolated_empire_db):
    src = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "tools_quoteiq.py"
    text = src.read_text()
    for name in CHAIN_STEPS + ("quoteiq_chain",):
        assert f'@tool("{name}")' in text
    result = run_quoteiq_chain({"message": ROMAN, "channel": "whatsapp"})
    assert result["ok"] is True
    assert result["sent"] is False
    assert result["status"] == "draft"
    names = [s["tool"] for s in result["steps"]]
    assert names == list(CHAIN_STEPS)


def test_try_handle_inbound_skips_non_jobs():
    assert try_handle_inbound(TWEET, channel="web_cc", founder=True) is None
    assert try_handle_inbound("Hi Max", channel="web_cc", founder=True) is None


def test_try_handle_inbound_founder_roman(isolated_empire_db):
    hit = try_handle_inbound(ROMAN, channel="web_cc", founder=True)
    assert hit and hit["handled"] is True
    assert hit["sent"] is False
    assert hit["quote_id"]


def test_chat_and_stream_share_quoteiq_door():
    """/chat and /chat/stream enter QuoteIQ after runtime-truth via the same helper."""
    src = Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py"
    text = src.read_text()
    assert text.count("_maybe_handle_quoteiq_request") >= 3
    assert "run_in_threadpool(_maybe_handle_quoteiq_request" in text
    assert "looks_like_quote_request" in text
    rt_chat = text.find("should_force_runtime_truth_check(request.message)")
    qiq_chat = text.find("quoteiq = _maybe_handle_quoteiq_request(request, founder=founder)")
    assert rt_chat != -1 and qiq_chat != -1 and qiq_chat > rt_chat
    assert "logger.warning(\"quoteiq chain failed" in text


def test_whatsapp_new_job_runs_chain_and_send_it_does_not_send(
    monkeypatch, tmp_path, isolated_empire_db,
):
    import app.services.max.whatsapp_channel as wa

    monkeypatch.setenv("VOICE_DOC_SESSIONS_PATH", str(tmp_path / "voice-sessions.json"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    monkeypatch.setenv("WHATSAPP_FOUNDER_PHONES", FOUNDER_WA)
    mail = []
    monkeypatch.setattr(
        "app.services.email.sender.send_email",
        lambda *a, **k: mail.append("sent") or (_ for _ in ()).throw(AssertionError("email")),
    )

    async def _chat(*_a, **_k):
        raise AssertionError("complete job must not fall through to max_chat")

    monkeypatch.setattr(wa, "max_chat", _chat)
    monkeypatch.setattr(wa, "founder_documents", lambda pipeline: ([], ""))

    first = asyncio.run(wa.default_text_handler(ROMAN, FOUNDER_WA))
    shown = first["text"] if isinstance(first, dict) else first
    assert "Draft" in shown and "Not sent" in shown
    assert mail == []

    second = asyncio.run(wa.default_text_handler("send it", FOUNDER_WA))
    shown2 = second["text"] if isinstance(second, dict) else second
    assert mail == []
    assert "blocked" in shown2.lower() or "not emailed" in shown2.lower() or "not sent" in shown2.lower()


def test_whatsapp_client_sender_does_not_run_chain(monkeypatch, tmp_path, isolated_empire_db):
    import app.services.max.whatsapp_channel as wa

    monkeypatch.setenv("VOICE_DOC_SESSIONS_PATH", str(tmp_path / "voice-sessions.json"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    monkeypatch.setenv("WHATSAPP_FOUNDER_PHONES", FOUNDER_WA)
    fell_through = []

    async def _chat(*_a, **_k):
        fell_through.append("max_chat")
        return "ok"

    monkeypatch.setattr(wa, "max_chat", _chat)
    monkeypatch.setattr(wa, "founder_documents", lambda pipeline: ([], ""))

    before = _quote_count()
    shown = asyncio.run(wa.default_text_handler(ROMAN, CLIENT_WA))
    text = shown["text"] if isinstance(shown, dict) else shown
    assert "Draft" not in str(text)
    assert _quote_count() == before
    assert fell_through == ["max_chat"]


def test_roman_shades_use_catalog_pricer_and_fractions(isolated_empire_db):
    result = run_quoteiq_chain({"message": ROMAN, "channel": "web_cc"})
    assert result["ok"] is True
    dims = result["dimensions"]
    assert "34 1/2" in " ".join(dims.values())
    assert "60" in " ".join(dims.values())
    assert result["sent"] is False
    priced = next(s for s in result["steps"] if s["tool"] == "quoteiq_price")
    assert priced["result"]["engine"] == "pricing_studio"
    assert priced["result"]["has_real_price"] is True
    assert priced["result"]["line_items"]
    assert priced["result"]["line_items"][0]["rate_source"] == "pricing_studio"
