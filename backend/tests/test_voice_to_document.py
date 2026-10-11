"""Voice notes become one draft quote and drawing. Nothing is sent."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.services.quote_engine.pricing_tables import get_labor_cost
from app.services.vision.bench_svg_dim_layout import (
    validate_bench_raked_bh_parallel_to_back,
    validate_bench_seat_cushion_consistency,
    validate_bench_seat_overhang_dim,
    validate_bench_side_depth_inside_frame,
)
from app.services.voice_documents.edition import (
    DOCUMENT_KINDS,
    PORTABLE_CORE,
    get_edition,
)
from app.services.voice_documents.extract import extract_transcript
from app.services.voice_documents.kinds import ensure_handlers_loaded, registered_kinds
from app.services.voice_documents.pipeline import (
    dispatch_confirmed_send,
    ingest_telegram_voice_transcript,
    ingest_transcript,
)
from app.services.voice_documents.send_gate import DraftSendBlocked, deliver_client_email

FIXTURE = Path(__file__).parent / "fixtures" / "voice_quote_transcript.txt"
NOTE = FIXTURE.read_text().strip()
KEY = "test-voice-quote"


@pytest.fixture(autouse=True)
def _isolate_voice_store(tmp_path, monkeypatch):
    monkeypatch.setenv("VOICE_DOC_SESSIONS_PATH", str(tmp_path / "sessions.json"))
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path / "drawings"))


def test_transcript_fixture_extracts_items():
    got = extract_transcript(NOTE)
    assert got.client_name == "Maggie"
    assert got.document_kind == "quote"
    assert got.items
    item = got.items[0]
    assert item.item_type == "banquette"
    assert item.width_in == 72
    assert item.depth_in == 20
    assert item.seat_height_in == 18
    assert item.back_height_in == 16
    assert item.fabric_mode == "com"
    assert item.welt == "none"
    assert item.seat_sections == 3
    assert item.back_sections == 2
    assert got.bill_as_nelmas is False


def test_quote_total_uses_saved_rates_and_drawing_rules(monkeypatch):
    monkeypatch.setattr(
        "app.services.voice_documents.pipeline._remember",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.voice_documents.send_gate.deliver_client_email",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("send called")),
    )
    result = ingest_transcript(NOTE, channel="cc", session_key=KEY)
    assert result["handled"] is True
    assert result["sent"] is False
    assert result["quote_status"] == "draft"
    assert result["status"] == "accumulating"
    expected = get_labor_cost("banquette", {"width": 72, "linear_ft": 6})
    assert result["total"] == pytest.approx(expected)
    descriptions = [row["description"] for row in result["line_items"]]
    assert "Supplied fabric, plain seats/backs" in descriptions
    fabric = next(row for row in result["line_items"] if "Supplied fabric" in row["description"])
    assert fabric["amount"] == pytest.approx(0)
    assert "%" not in fabric["description"]
    assert any(str(row.get("rate_source") or "").startswith("pricing_tables.LABOR_RATES:") for row in result["line_items"])

    fab = result["drawing"]["fabrication"]
    assert fab["usable_seat_in"] == pytest.approx(18)
    assert fab["overall_depth_in"] == pytest.approx(20)
    assert fab["back_thickness_in"] == pytest.approx(2)
    assert fab["seat_cushion_thickness_in"] == pytest.approx(2)
    assert fab["seat_deck_height_in"] == pytest.approx(16)
    assert fab["overhang_in"] >= 1
    assert fab["back_angle_deg"] == pytest.approx(0)
    assert fab["vertical_back"] is True
    assert fab["seat_sections"] == 3
    assert fab["back_sections"] == 2

    svg = result["drawing"]["svg"]
    assert svg
    assert "EMPIRE WORKROOM" in svg
    assert "NELMA" not in svg.upper()
    assert "Rafael" not in svg
    validate_bench_seat_cushion_consistency(svg, cushion_in=2.0, deck_in=16.0, seat_h_in=18.0)
    validate_bench_seat_overhang_dim(svg, 1.0)
    validate_bench_side_depth_inside_frame(
        svg, overall_depth_in=20, back_thickness_in=2, usable_seat_in=18,
    )

    plain = result["email_preview"]["plain_text"]
    assert result["email_preview"]["sent"] is False
    assert "Supplied fabric, plain seats/backs: $0.00" in plain
    assert "Rafael" not in plain
    banquette_at = plain.find("Banquette")
    fabric_at = plain.find("Supplied fabric")
    assert banquette_at != -1 and fabric_at != -1
    assert "\n" in plain[banquette_at:fabric_at]
    assert result["client_brand"] == "Empire Workroom"


def test_notes_accumulate_until_done_and_never_auto_send(monkeypatch):
    monkeypatch.setattr(
        "app.services.voice_documents.pipeline._remember",
        lambda *args, **kwargs: None,
    )
    calls = []

    def _spy(*args, **kwargs):
        calls.append(args)
        return True

    monkeypatch.setattr("app.services.email.sender.send_email", _spy)
    first = ingest_transcript(
        "I'm Rafael. " + NOTE,
        channel="cc",
        session_key=KEY,
    )
    assert first["customer_name"] == "Maggie"
    assert "Rafael" not in (first["customer_name"] or "")
    quote_id = first["quote_id"]
    second = ingest_transcript(
        "Make the back raked 10 degrees. Bill as Nelma's.",
        channel="cc",
        session_key=KEY,
    )
    assert second["quote_id"] == quote_id
    assert second["sent"] is False
    assert second["billed_by"] == "nelmas_workroom"
    assert second["client_brand"] == "Nelma's Workroom"
    fab = second["drawing"]["fabrication"]
    assert fab["back_angle_deg"] == pytest.approx(10)
    assert fab["vertical_back"] is False
    svg = second["drawing"]["svg"]
    assert "NELMA" in svg.upper()
    assert "Rafael" not in svg
    validate_bench_raked_bh_parallel_to_back(svg)

    asked = ingest_transcript("send it", channel="cc", session_key=KEY)
    assert asked["sent"] is False
    assert asked["send_requested"] is True
    assert calls == []

    done = ingest_transcript("done", channel="cc", session_key=KEY)
    assert done["status"] == "finalized"
    assert done["sent"] is False
    assert done["quote_status"] == "draft"
    assert calls == []

    with pytest.raises(DraftSendBlocked):
        asyncio.run(dispatch_confirmed_send(done["session_id"], confirmed=False))
    assert calls == []

    async def _fake_send(to, subject, html):
        calls.append(to)
        return True

    monkeypatch.setattr("app.services.email.sender.send_email", _fake_send)
    sent = asyncio.run(dispatch_confirmed_send(
        done["session_id"], confirmed=True, to_email="maggie@example.com",
    ))
    assert sent["sent"] is True
    assert calls == ["maggie@example.com"]


def test_telegram_voice_uses_the_same_pipeline(monkeypatch):
    monkeypatch.setattr(
        "app.services.voice_documents.pipeline._remember",
        lambda *args, **kwargs: None,
    )
    result = ingest_telegram_voice_transcript(NOTE, "chat-9")
    assert result["handled"] is True
    assert result["sent"] is False
    assert result["quote_status"] == "draft"
    assert "Not sent" in result["reply_text"] or "not emailed" in result["reply_text"].lower()


def test_unported_edition_does_not_invent_a_price(monkeypatch):
    monkeypatch.setattr(
        "app.services.voice_documents.pipeline._remember",
        lambda *args, **kwargs: None,
    )
    result = ingest_transcript(NOTE, channel="cc", session_key="max-e", edition_id="max_e")
    assert result["edition"] == "max_e"
    assert result["stub"] is True
    assert result["sent"] is False
    assert result["persisted"] is False
    assert get_edition("max_e").auto_send is False
    assert get_edition("maxine").auto_send is False
    ensure_handlers_loaded()
    for kind in DOCUMENT_KINDS:
        assert kind in registered_kinds()
    assert PORTABLE_CORE


def test_deliver_blocks_without_confirmation():
    with pytest.raises(DraftSendBlocked):
        deliver_client_email(
            to="a@example.com",
            subject="quote",
            html_body="<p>hi</p>",
            confirmed=False,
            sender=lambda *a, **k: True,
        )


def test_choices_when_fabric_and_welt_are_open(monkeypatch):
    monkeypatch.setattr(
        "app.services.voice_documents.pipeline._remember",
        lambda *args, **kwargs: None,
    )
    result = ingest_transcript(
        "Quote for Bea. Straight bench 60 inches long, 22 inches deep, 19 inches high, back 15 inches.",
        channel="cc",
        session_key="choices",
    )
    prompts = [opt["prompt"] for opt in result["options"]]
    assert "Fabric" in prompts
    assert "Welt" in prompts
    assert 2 <= len(result["options"]) <= 3
    assert result["sent"] is False
    assert any(row["id"] == "client" for row in result["missing"]) is False
