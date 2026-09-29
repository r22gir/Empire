"""Item 4 (feature/drawing-standard dispatch) — stop stray JSON quotes.

`POST /api/v1/quotes/analyze-photo` used to unconditionally create AND
PERSIST a brand-new JSON-store quote (burning the next EST number) on
every call, even when the Quote Review "Analyze" button already had a
real quotes-v2 quote open. Two independent fixes are covered here:

  1. `_attach_photo_analysis_to_quote` attaches analysis to an EXISTING
     quote (quotes-v2 first, legacy JSON fallback) instead of creating one.
  2. `_next_quote_number` (legacy JSON store) takes quotes_v2's highest
     issued number into account so the two stores can never collide.
"""
from __future__ import annotations

import json
import os


def test_attach_photo_analysis_updates_existing_v2_quote(isolated_empire_db):
    from app.routers.quotes import _attach_photo_analysis_to_quote
    from app.services.quote_service import create_quote, get_quote

    quote = create_quote({
        "customer_name": "Analyze Button Customer",
        "business_unit": "workroom",
        "pricing_mode": "flat",
        "tax_rate": 0,
        "project_name": "Analyze Photo Attach Coverage",
    })

    ok = _attach_photo_analysis_to_quote(
        quote["id"], {"items": [{"name": "Left Wall Window", "type": "drapery_panel"}]},
    )
    assert ok is True

    reloaded = get_quote(quote["id"])
    assert reloaded["ai_outlines"] == [{"name": "Left Wall Window", "type": "drapery_panel"}]


def test_attach_photo_analysis_falls_back_to_legacy_json_quote(isolated_empire_db, tmp_path, monkeypatch):
    from app.routers import quotes as quotes_router

    quotes_dir = tmp_path / "quotes_json"
    quotes_dir.mkdir()
    monkeypatch.setattr(quotes_router, "QUOTES_DIR", str(quotes_dir))
    monkeypatch.setattr(quotes_router, "COUNTER_FILE", str(quotes_dir / "_counter.json"))

    legacy_quote = {
        "id": "legacy-quote-1",
        "quote_number": "EST-2026-999",
        "customer_name": "Legacy JSON Customer",
        "line_items": [],
    }
    quotes_router._save_quote(legacy_quote)

    ok = quotes_router._attach_photo_analysis_to_quote(
        "legacy-quote-1", {"items": [{"name": "Bay Window"}]},
    )
    assert ok is True

    with open(quotes_dir / "legacy-quote-1.json") as f:
        reloaded = json.load(f)
    assert reloaded["ai_outlines"] == [{"name": "Bay Window"}]


def test_attach_photo_analysis_unknown_quote_id_returns_false(isolated_empire_db, tmp_path, monkeypatch):
    from app.routers import quotes as quotes_router

    quotes_dir = tmp_path / "quotes_json_empty"
    quotes_dir.mkdir()
    monkeypatch.setattr(quotes_router, "QUOTES_DIR", str(quotes_dir))

    assert quotes_router._attach_photo_analysis_to_quote("does-not-exist", {"items": []}) is False


def test_next_quote_number_never_collides_with_quotes_v2(isolated_empire_db, tmp_path, monkeypatch):
    """quotes_v2 already at EST-<year>-292; the legacy JSON store only has
    files up to EST-<year>-005. _next_quote_number must return a number
    ABOVE the quotes_v2 max, not reuse an already-issued v2 number."""
    from datetime import datetime

    from app.routers import quotes as quotes_router
    from app.services.quote_service import create_quote

    year = datetime.utcnow().year

    quotes_dir = tmp_path / "quotes_json"
    quotes_dir.mkdir()
    monkeypatch.setattr(quotes_router, "QUOTES_DIR", str(quotes_dir))
    monkeypatch.setattr(quotes_router, "COUNTER_FILE", str(quotes_dir / "_counter.json"))

    # A handful of low-numbered legacy JSON quotes.
    for seq in range(1, 6):
        quotes_router._save_quote({
            "id": f"legacy-{seq}",
            "quote_number": f"EST-{year}-{seq:03d}",
            "line_items": [],
        })

    # quotes_v2 already issued a much higher number.
    high_quote = None
    for _ in range(292):
        high_quote = create_quote({
            "customer_name": "Bulk V2 Customer",
            "business_unit": "workroom",
            "pricing_mode": "flat",
            "tax_rate": 0,
        })
    assert high_quote["quote_number"] == f"EST-{year}-292"

    next_number = quotes_router._next_quote_number()
    assert next_number == f"EST-{year}-293"


def test_analyze_photo_response_documents_ephemeral_quote(isolated_empire_db):
    """assemble_quote's result is an in-memory preview only — it must not
    be persisted as a side effect of building it."""
    from app.services.quote_engine.quote_assembler import assemble_quote

    before = None
    quotes_dir = os.environ.get("EMPIRE_QUOTES_DIR")
    if quotes_dir and os.path.isdir(quotes_dir):
        before = set(os.listdir(quotes_dir))

    assemble_quote(
        analyzed_items=[{"name": "Left Wall Window", "type": "drapery_panel", "selected": True}],
        customer_name="Ephemeral Preview Customer",
        location="DC",
        lining="standard",
    )

    if before is not None:
        after = set(os.listdir(quotes_dir))
        assert after == before, "assemble_quote must not write a quote file as a side effect"
