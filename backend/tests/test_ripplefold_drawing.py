"""Ripplefold sheet: Kirsch chart, partial coverage, no guessed mount."""
from __future__ import annotations

import io

import pytest


def _case(**overrides):
    dims = {
        "width": 160,
        "height": 84,
        "coverage_width": 96,
        "fullness_pct": 100,
        "carrier": "92141",
        "masters": "butt",
        "control": "center",
        "coverage_align": "center",
        "layer": "sheer",
    }
    dims.update(overrides)
    return {"product_type": "ripplefold", "dims": dims}


def _pdf_text(pdf: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages
    )


def test_center_draw_chart_is_24_snaps_per_panel():
    from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold

    job = resolve_ripplefold(_case())
    assert job.coverage_width == 96
    assert job.track_length == 96
    assert job.track_equals_coverage is True
    assert job.offset == 32
    assert job.align == "center"
    assert job.fullness == 100
    assert job.carrier == "92141"
    assert job.carrier_spacing == 2.125
    assert job.masters == "butt"
    assert job.control == "center"
    assert job.carriers_per_panel == 24
    assert job.carrier_count == 48
    assert job.full_spaces_per_panel == 23
    assert job.stack == 16.25
    assert job.stack_source == "kirsch chart"
    assert job.layer == "sheer"
    assert job.mount is None
    assert job.ceiling_height is None
    assert job.mount_height is None


def test_one_way_same_coverage_is_48_snaps_on_one_panel():
    from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold

    job = resolve_ripplefold(_case(control="one-way"))
    assert job.carriers_per_panel == 48
    assert job.carrier_count == 48


def test_partial_coverage_is_not_centered_unless_asked():
    from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold

    job = resolve_ripplefold(_case(coverage_align=None))
    assert job.align is None
    assert job.offset is None


def test_missing_masters_does_not_invent_a_carrier_count():
    from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold

    job = resolve_ripplefold(_case(masters=None))
    assert job.carrier_count is None
    assert job.stack is None


def test_catalog_override_is_kept():
    from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold

    job = resolve_ripplefold(_case(fullness_pct=80))
    assert job.fullness == 80
    assert job.carrier_spacing == 2.125
    assert any("override" in note for note in job.notes)


def test_template_does_not_assume_returns_or_pinch_panels():
    from app.services.drawing.templates import get_template

    template = get_template("ripplefold")
    spec = _case()
    missing = template.validate_spec(spec)
    assert missing.is_complete
    assert "returns" not in missing.missing_optional
    assert "carrier" not in missing.extra_dims
    result = template.compute(spec)
    assumptions = " ".join(result.assumptions).lower()
    assert "returns" not in assumptions
    assert "assumed 3" not in assumptions
    assert result.title_block["ITEM"] == "RIPPLEFOLD"
    assert result.title_block["MOUNT"] == "NOT GIVEN"
    assert result.title_block["CEILING"] == "NOT GIVEN"
    assert result.title_block["CARRIERS"] == "48"
    offenders = [
        line for line in result.layout_math
        if line.closing_tolerance_in >= (1 / 64)
    ]
    assert not offenders


def test_sheet_labels_ripplefold_and_skips_pinch_guesses():
    from app.services.drawing.templates.drapery_render import render_drapery
    from app.services.drawing.templates.printer import render_spec

    direct = render_drapery(_case())
    via_printer = render_spec(_case())
    for pdf in (direct, via_printer):
        text = _pdf_text(pdf)
        for needle in (
            "RIPPLEFOLD", "ELEVATION", "TOP VIEW", "160", "96", "84",
            "100%", "92141", "2-1/8", "48", "BUTT", "CENTER", "32",
            "SHEER", "NOT GIVEN",
        ):
            assert needle in text, needle
        assert "PINCH" not in text.upper()
        assert "108" not in text
        assert "2-1/2" not in text
        assert "EACH SIDE" in text


def test_layered_sheet_names_both_fabrics():
    from app.services.drawing.templates.drapery_render import render_drapery

    pdf = render_drapery(_case(layer="sheer behind drapery"))
    text = _pdf_text(pdf).upper()
    assert "SHEER BEHIND DRAPERY" in text
    assert "PINCH" not in text


def test_quote_card_uses_ripplefold_not_a_pinch_pair():
    from app.routers.quotes import _build_window_drawing

    svg = _build_window_drawing({
        "name": "Sheers",
        "treatmentType": "ripplefold",
        "width": 160,
        "height": 84,
        "coverageWidth": 96,
        "fullnessPct": 100,
        "carrier": "92141",
        "masters": "butt",
        "drawDirection": "center",
        "coverageAlign": "center",
        "layer": "sheer",
    })
    assert "RIPPLEFOLD" in svg
    assert "TOP VIEW" in svg
    assert "92141" in svg
    assert "2-1/8" in svg
    assert "NOT GIVEN" in svg
    assert "48" in svg
    assert "window view" not in svg
    assert "Wall Mount" not in svg
    assert "2.5" not in svg
    assert "PINCH" not in svg.upper()
    assert '108"' not in svg
    assert "CEILING" in svg


def test_chat_handoff_reads_the_sheer_sentence():
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff(
        "draw a ripplefold shop drawing, 160 wide 84 high, "
        "sheers covering 96, 100% fullness, carrier 92141, "
        "butt masters, center draw, re-centered track"
    )
    dims = handoff.translated_dims
    assert handoff.b1_product_type == "ripplefold"
    assert str(dims.get("coverage_width")) == "96"
    assert dims.get("carrier") == "92141"
    assert dims.get("masters") == "butt"
    assert dims.get("control") == "center"
    assert dims.get("coverage_align") == "center"
    assert dims.get("layer") == "sheer"
    assert "ceiling_height" not in dims
    assert "mount" not in dims
    assert handoff.missing_template_keys == []


def test_chat_router_passes_ripplefold_words_into_the_sheet():
    from app.routers.max.router import _dims_for_render_shop
    from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff(
        "draw a ripplefold shop drawing, 160 wide 84 high, "
        "sheers covering 96, 100% fullness, carrier 92141, "
        "butt masters, center draw, re-centered track"
    )
    dims, _shape, _construction = _dims_for_render_shop(handoff)
    assert dims["carrier"] == "92141"
    assert dims["masters"] == "butt"
    assert dims["control"] == "center"
    assert dims["coverage_align"] == "center"
    assert dims["layer"] == "sheer"
    job = resolve_ripplefold({"product_type": "ripplefold", "dims": dims})
    assert job.carrier_count == 48
    assert job.carriers_per_panel == 24
    assert job.offset == 32
    assert job.ceiling_height is None
    assert job.mount is None


def test_carrier_float_text_stays_the_kirsch_number():
    from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold

    job = resolve_ripplefold(_case(carrier="92141.0"))
    assert job.carrier == "92141"
    assert job.carrier_count == 48


def test_shop_tool_keeps_carrier_text(monkeypatch, tmp_path):
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    from app.services.max.tool_executor import _render_shop_drawing

    result = _render_shop_drawing({
        "product_type": "ripplefold",
        "dims": {
            "width": 160,
            "height": 84,
            "coverage_width": 96,
            "fullness_pct": 100,
            "carrier": "92141",
            "masters": "butt",
            "control": "center",
            "coverage_align": "re-centered",
            "layer": "sheer",
        },
    })
    assert result.success, result.error
    assert result.result["dims"]["carrier"] == "92141"
    assert result.result["dims"]["masters"] == "butt"
    assert result.result["dims"]["control"] == "center"
