"""Shop sheets print whole inches or fractions, never decimal inches.

Founder rule (2026-09-27): 72" not 72.00", 14-1/2" not 14.5" or 14.50".
Geometry stays float. Only the display strings change.
"""
from __future__ import annotations

import html
import io
import re

import pytest

from app.services.drawing.inches import format_inches
from app.services.drawing.templates import get_template, render_spec
from app.services.vision.bench_renderer import render_straight
from app.services.vision.diagram_generator import DiagramGenerator

# A decimal glued to an inch mark: 72.00" or 14.5" or 14.50 ".
_DECIMAL_INCH = re.compile(r"\d+\.\d+\s*\"")


def _no_decimal_inches(text: str) -> None:
    hit = _DECIMAL_INCH.search(text or "")
    assert hit is None, f"decimal inch form {hit.group(0)!r} in {text!r}"


def _svg_text(svg: str) -> str:
    """Visible text only. Coordinate attributes also end in a quote."""
    raw = "\n".join(re.findall(r">([^<]*)</text>", svg))
    return html.unescape(raw)


class TestFormatInches:
    def test_whole_inches_drop_trailing_zeros(self):
        assert format_inches(72) == '72"'
        assert format_inches(72.0) == '72"'
        assert format_inches(72.00) == '72"'
        assert format_inches(14) == '14"'
        assert format_inches(6) == '6"'
        assert format_inches(0) == '0"'

    def test_halves_and_quarters_are_fractions(self):
        assert format_inches(14.5) == '14-1/2"'
        assert format_inches(14.50) == '14-1/2"'
        assert format_inches(6.25) == '6-1/4"'
        assert format_inches(6.75) == '6-3/4"'
        assert format_inches(0.5) == '1/2"'
        assert "14.5" not in format_inches(14.5)
        assert "14.50" not in format_inches(14.50)

    def test_sixteenths_match_the_b1_sheet_contract(self):
        assert format_inches(69.5) == '69-1/2"'
        assert format_inches(69.125) == '69-1/8"'
        assert format_inches(35.46) == '35-7/16"'


class TestQuoteIdeaSheetDimensions:
    def test_kingston_valance_dimensions_line(self):
        block = get_template("kingston").title_block({
            "product_type": "kingston",
            "dims": {"width": 72, "drop": 14},
        })
        assert block["DIMENSIONS"] == '72" W × 14" drop'
        _no_decimal_inches(block["DIMENSIONS"])
        assert "72.00" not in block["DIMENSIONS"]
        assert "14.00" not in block["DIMENSIONS"]

    def test_straight_cornice_dimensions_line(self):
        block = get_template("straight").title_block({
            "product_type": "straight",
            "dims": {"width": 72, "depth": 6, "drop": 14},
        })
        assert block["DIMENSIONS"] == '72" W × 6" D × 14" drop'
        _no_decimal_inches(block["DIMENSIONS"])
        assert "72.00" not in block["DIMENSIONS"]
        assert "6.00" not in block["DIMENSIONS"]
        assert "14.00" not in block["DIMENSIONS"]

    def test_half_inch_drop_is_a_fraction_on_the_title_block(self):
        block = get_template("kingston").title_block({
            "product_type": "kingston",
            "dims": {"width": 72.0, "drop": 14.5, "returns": 3.5},
        })
        assert block["DIMENSIONS"] == '72" W × 14-1/2" drop'
        assert block["RETURNS"] == '3-1/2"'
        _no_decimal_inches(block["DIMENSIONS"])
        _no_decimal_inches(block["RETURNS"])
        assert "14.50" not in block["DIMENSIONS"]
        assert "14.5" not in block["DIMENSIONS"]

    def test_rendered_idea_sheets_have_no_decimal_inch_callouts(self):
        pytest.importorskip("pdfplumber")
        import pdfplumber

        samples = [
            {
                "product_type": "kingston",
                "dims": {"width": 72, "drop": 14},
                "expect": '72" W',
            },
            {
                "product_type": "straight",
                "dims": {"width": 72, "depth": 6, "drop": 14},
                "expect": '6" D',
            },
            {
                "product_type": "kingston",
                "dims": {"width": 72, "drop": 14.5},
                "expect": '14-1/2"',
            },
        ]
        for spec in samples:
            pdf = render_spec({k: spec[k] for k in ("product_type", "dims")})
            with pdfplumber.open(io.BytesIO(pdf)) as doc:
                text = doc.pages[0].extract_text() or ""
            assert spec["expect"] in text
            _no_decimal_inches(text)
            assert "72.00" not in text
            assert "14.00" not in text
            assert "14.50" not in text


class TestBenchAndDiagramCallouts:
    def test_bench_dimensions_stay_whole_and_halves_are_fractions(self):
        whole = _svg_text(render_straight(
            "KINGSTON BENCH", 66, depth_in=20, seat_h_in=18, back_h_in=18,
        ))
        assert '66" W' in whole
        assert '20" D' in whole
        _no_decimal_inches(whole)
        assert "66.00" not in whole

        half = _svg_text(render_straight(
            "HALF BENCH", 72.5, depth_in=20, seat_h_in=18.5, back_h_in=14,
            cushion_width=20.5,
        ))
        assert '72-1/2"' in half
        assert '18-1/2"' in half
        assert '20-1/2"' in half
        _no_decimal_inches(half)
        assert "72.50" not in half
        assert "14.50" not in half
        assert "20.5" not in half

    def test_quote_diagram_labels_are_not_decimal_inches(self):
        labels = _svg_text(DiagramGenerator().generate_window_diagram({
            "measurements": {"width_inches": 72.0, "height_inches": 14.5},
        }))
        assert '72"' in labels
        assert '14-1/2"' in labels
        _no_decimal_inches(labels)
        assert "72.0" not in labels
        assert "14.5" not in labels
