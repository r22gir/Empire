"""PHASE 2 · R12.2 — cross-site dimension-formatter consistency guard.

The founder spotted a real defect on the live sheet
(flat_fold_ba55b30d.pdf, rendered 2026-08-23): three different
sites printed the SAME dimension with three different values:

  Site                                            | Formatter             | 69.5" rendered
  ------------------------------------------------+-----------------------+---------------
  Header band       b2_renderers.py:554           | int(round())          | "70""  (half-in)
  Title DIMENSIONS b2_renderers.py:743           | :.2f (2 decimals)    | "69.50"
  Layout math      b2_renderers.py:819-830        | _fmt_in (1/16 frac)   | "69-1/2""

For a shop sheet that's a defect. Half an inch decides fit.

Fix (R12.2): every site uses _fmt_in. Single source of truth.

This test renders a non-integer-dimensioned flat_fold, extracts
the PDF text, and asserts that for each of {width, height} the
set of distinct values printed on the sheet is exactly one. If a
future change re-introduces a different formatter at any site,
this test FAILS — guarding the class, not just the call.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from app.services.drawing.templates import render_spec


def _pdf_to_text(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF using pdftotext."""
    out_path = Path("/tmp/_r12_2_extract.pdf")
    out_path.write_bytes(pdf_bytes)
    result = subprocess.run(
        ["pdftotext", str(out_path), "-"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout


# Numbers that must agree across sites:
#   * width  (the W axis of the shade, geo_w)
#   * height (the H axis of the shade, geo_h)
#
# A "value" here means a numeric token that names the dimension:
# 69, 69.5, "69-1/2", etc. The guard collects every occurrence
# of each dimension key on the sheet and asserts a single value.


def _extract_dimension_values(pdf_text: str, dimension_key: str) -> list[str]:
    """Find every numeric value paired with `dimension_key` in
    the PDF text. Returns raw match strings (the printed tokens).

    The sheet prints dimensions three ways:
      1. Header band:        `38" W × 55-1/2" H`
      2. Title DIMENSIONS:   `DIMENSIONS: 38" W × 55-1/2" H`
      3. Front elevation:    `38"` (just the value, drawn below the box)
      4. Side section:       `55-1/2" SHADE` (value + side context)
      5. Layout math:        `1 × 38" = 38" (target 38")`
                           and `8 × 6-15/16" = 55-1/2" (target 55-1/2")`

    The dimension KEY labels printed on the sheet are "W" (width)
    and "H" (height). "SHADE" appears only on height's side section.
    "DIMENSIONS:" is a row header (always followed by the value).

    This function returns every numeric value printed adjacent to
    the given dimension key on the sheet.
    """
    fraction = r"\d+(?:\.\d+)?(?:-\d+/\d+)?"

    values = []

    # Patterns where the value precedes the key:
    #   "55-1/2\" H"
    #   "55\" SHADE"
    #   "55\" (target ...)"
    pre = re.compile(
        rf"({fraction})\"\s*{re.escape(dimension_key)}\b",
        re.IGNORECASE,
    )
    values.extend(pre.findall(pdf_text))

    # Patterns where the key precedes the value:
    #   "DIMENSIONS: 38\" W × 55-1/2\" H"
    #   "W: 38\""
    #   "H: 55\""
    # But for "W" and "H" the prefix match above already catches
    # everything. Skip the prefix form for these single-letter keys
    # (it would match too much) and only enable it for multi-char
    # keys like "height".
    if len(dimension_key) > 2:
        pre2 = re.compile(
            rf"\b{re.escape(dimension_key)}\s*[:=×]?\s*({fraction})\"",
            re.IGNORECASE,
        )
        values.extend(pre2.findall(pdf_text))

    return values


# ──────────────────────────────────────────────────────────────────────
# The guard
# ──────────────────────────────────────────────────────────────────────


class TestDimensionFormatterConsistency:
    """Every site that prints a width or a height on a single sheet
    must agree. Half an inch decides fit; the dispatch calls this
    a defect when sites diverge."""

    @pytest.fixture(scope="class")
    def flat_fold_pdf_with_fractional_dim(self):
        """Render a 69-1/2" W × 55" H flat-fold shade. The non-integer
        width is the critical case — 69.5 rounds to 70 with
        int(round())."""
        spec = {
            "product_type": "flat_fold",
            "dims": {"width": 69.5, "height": 55.0},
            "client_name": "",
            "site_address": "",
            "material": "",
            "date": "",
        }
        return render_spec(spec)

    @pytest.fixture(scope="class")
    def flat_fold_pdf_with_half_inch_height(self):
        spec = {
            "product_type": "flat_fold",
            "dims": {"width": 38.0, "height": 55.5},
            "client_name": "",
            "site_address": "",
            "material": "",
            "date": "",
        }
        return render_spec(spec)

    @pytest.fixture(scope="class")
    def flat_fold_pdf_with_integer_dim(self):
        """Control: integer dims must also be consistent across sites
        (the bug pre-fix would have produced 70 vs 69 vs 70; we want
        all to agree on 69 or 69-1/2 — never on a rounded-up whole)."""
        spec = {
            "product_type": "flat_fold",
            "dims": {"width": 69.0, "height": 55.0},
            "client_name": "",
            "site_address": "",
            "material": "",
            "date": "",
        }
        return render_spec(spec)

    def _value_set(self, pdf_text: str, key: str) -> set:
        return set(_extract_dimension_values(pdf_text, key))

    def test_width_value_single_across_sites_fractional(
        self, flat_fold_pdf_with_fractional_dim
    ):
        """The live bug. With width=69.5, every site on the sheet
        that names the width must agree."""
        text = _pdf_to_text(flat_fold_pdf_with_fractional_dim)
        widths = self._value_set(text, "W")
        assert len(widths) == 1, (
            f"width printed with multiple values on one sheet: "
            f"{sorted(widths)!r}. The founder-reported bug: header "
            f"rounded to 70\" while title block printed 69.50\"."
        )

    def test_height_value_single_across_sites_fractional(
        self, flat_fold_pdf_with_fractional_dim
    ):
        text = _pdf_to_text(flat_fold_pdf_with_fractional_dim)
        heights = self._value_set(text, "H")
        heights |= self._value_set(text, "SHADE")
        assert len(heights) == 1, (
            f"height printed with multiple values on one sheet: "
            f"{sorted(heights)!r}"
        )

    def test_height_value_single_across_sites_half_inch_height(
        self, flat_fold_pdf_with_half_inch_height
    ):
        text = _pdf_to_text(flat_fold_pdf_with_half_inch_height)
        heights = self._value_set(text, "H")
        heights |= self._value_set(text, "SHADE")
        assert len(heights) == 1, (
            f"height printed with multiple values on one sheet "
            f"(height=55.5): {sorted(heights)!r}"
        )

    def test_width_value_single_across_sites_integer(
        self, flat_fold_pdf_with_integer_dim
    ):
        text = _pdf_to_text(flat_fold_pdf_with_integer_dim)
        widths = self._value_set(text, "W")
        assert len(widths) == 1, (
            f"integer width printed with multiple values on one "
            f"sheet (width=69): {sorted(widths)!r}"
        )

    def test_no_rounded_up_half_inch_in_header(
        self, flat_fold_pdf_with_fractional_dim
    ):
        """Regression: the founder's exact case was width=69.5
        producing "70" W" in the header (rounding up half an inch).
        Post-fix, no site on the sheet may print 70 for the width
        when the spec says 69.5."""
        text = _pdf_to_text(flat_fold_pdf_with_fractional_dim)
        # Look for "70" near the width key (defensive against
        # coincidental "70" elsewhere).
        for line in text.splitlines():
            if " W " in line and "×" in line:
                # Header / title / front-elevation label
                assert "70\"" not in line, (
                    f"sheet printed 70\" for width when spec was "
                    f"69.5\": {line!r}"
                )
                # The only allowed width value is 69-1/2
                assert "69-1/2\"" in line, (
                    f"sheet did not print 69-1/2\" for width: {line!r}"
                )

    def test_format_inch_marker_consistent(self, flat_fold_pdf_with_fractional_dim):
        """Every printed dimension value must end with a single "
        inch marker (not 55""  SHADE double-quote bug)."""
        text = _pdf_to_text(flat_fold_pdf_with_fractional_dim)
        # Find lines containing numeric values followed by ".
        for line in text.splitlines():
            if re.search(r'\d+""', line):  # two consecutive quotes
                pytest.fail(
                    f"double-quote bug on line: {line!r}"
                )


# ──────────────────────────────────────────────────────────────────────
# Unit tests for the fix (the helper itself)
# ──────────────────────────────────────────────────────────────────────


class TestFmtInUsedEverywhere:
    """The fix replaces int(round()) and :.2f with _fmt_in. These
    tests pin the helper output so future formatters can't drift."""

    def test_fmt_in_integer(self):
        from app.services.drawing.templates.b2_renderers import _fmt_in
        assert _fmt_in(69) == '69"'
        assert _fmt_in(55) == '55"'

    def test_fmt_in_decimal_rounds_to_half_inch(self):
        from app.services.drawing.templates.b2_renderers import _fmt_in
        # _fmt_in rounds to nearest 1/16" via round(value * 16).
        # 0.5 rounds to 8/16 = 1/2.
        assert _fmt_in(69.5) == '69-1/2"'
        assert _fmt_in(55.5) == '55-1/2"'

    def test_fmt_in_quarter_inch(self):
        from app.services.drawing.templates.b2_renderers import _fmt_in
        assert _fmt_in(69.25) == '69-1/4"'
        assert _fmt_in(55.75) == '55-3/4"'

    def test_fmt_in_eighth_inch(self):
        from app.services.drawing.templates.b2_renderers import _fmt_in
        assert _fmt_in(69.125) == '69-1/8"'

    def test_fmt_in_zero(self):
        from app.services.drawing.templates.b2_renderers import _fmt_in
        assert _fmt_in(0) == '0"'

    def test_fmt_in_regression_no_int_round_remainder(self):
        """int(round(69.5)) = 70 (banker's rounding may give 70 here
        on CPython, or 69 on some implementations). _fmt_in must
        always return 69-1/2 for 69.5. This pins that."""
        from app.services.drawing.templates.b2_renderers import _fmt_in
        assert _fmt_in(69.5) == '69-1/2"', (
            f"formatting drift: 69.5 → {_fmt_in(69.5)!r}, "
            f"expected '69-1/2\"'"
        )


# ──────────────────────────────────────────────────────────────────────
# R12.3.1 — fold-count and slat-pitch cross-site guard
# ──────────────────────────────────────────────────────────────────────


def _extract_fold_count(pdf_text: str) -> list[int]:
    """Pull every integer N that names a fold/slat count on the sheet.

    Matches patterns like:
      "9 folds @ ..."           (header band)
      "9 @ 7-1/8\""            (FOLDS row + front-elevation witness)
      "8 × 6-7/8\" = 55\"" (layout math segment count)
      "8 total"                 (notes "ASSUMED 6-7/8" (8 total)")

    Filters: the layout math has TWO `N ×` lines — one for the
    width ("1 × 69-1/2\"" — single-panel roman) and one for the
    slats ("8 × 6-7/8\""). Only the slat-side count is a fold
    count. The width-panel count is 1 by convention and is
    excluded.
    """
    found = []
    # "N folds @" (header)
    for m in re.finditer(r"\b(\d+)\s+folds\s+@", pdf_text):
        found.append(int(m.group(1)))
    # "N @ pitch" (FOLDS row + front-elevation witness)
    for m in re.finditer(r"\b(\d+)\s+@\s+\d", pdf_text):
        found.append(int(m.group(1)))
    # "N × pitch" (layout math segment counts) — exclude the
    # width-panel count (which is 1 by convention for roman).
    for m in re.finditer(r"\b(\d+)\s+×\s+\d+(?:-\d+/\d+)?\"", pdf_text):
        n = int(m.group(1))
        if n >= 2:  # exclude the single-panel width entry
            found.append(n)
    # "(N total)" (notes assumption block)
    for m in re.finditer(r"\((\d+)\s+total\)", pdf_text):
        found.append(int(m.group(1)))
    return found


def _extract_slat_pitches(pdf_text: str) -> list[str]:
    """Pull every slat-pitch string printed on the sheet.

    Matches `N-X/Y"` (the format _fmt_in uses). Restricts to
    pitches that appear adjacent to "× " (the layout math
    segment) or "@ " (the descriptor / FOLDS row), excluding
    other fractional measurements on the sheet like the mount
    depth (2-1/2"), the cover depth (7-9/16"), and the W/H
    dimensions themselves.

    Specifically excludes the width-row "1 × 69-1/2\"" (single-
    panel roman) — the operand there is the width, not a pitch.
    """
    pitches = set()
    # From "N × pitch" segments (layout math). Exclude the
    # single-panel width entry (count=1 by convention for roman).
    for m in re.finditer(r"\b(\d+)\s+×\s+(\d+-\d+/\d+\")", pdf_text):
        if int(m.group(1)) >= 2:
            pitches.add(m.group(2))
    # From "N folds @ pitch" and "N @ pitch" (header + FOLDS row).
    for m in re.finditer(r"@\s+(\d+-\d+/\d+\")", pdf_text):
        pitches.add(m.group(1))
    # From the notes "Slat: ASSUMED X-Y/Z" (8 total)".
    for m in re.finditer(r"Slat:\s+ASSUMED\s+(\d+-\d+/\d+\")", pdf_text):
        pitches.add(m.group(1))
    return sorted(pitches)


class TestFoldCountSlatsConsistency:
    """R12.3.1 — every fold-count and slat-pitch value printed on
    one sheet must agree. The founder's live bug:
    flat_fold_148b13ff.pdf printed `9 folds @ 7-1/8"` in the
    header but `8 × 6-7/8"` in the layout math for a 55"-tall
    shade. Wrong fold count is the same defect class as wrong
    dimensions — half an inch decides fit, but so does "is this
    a 9-fold or an 8-fold stack?".

    The guard renders flat_fold at three heights and asserts
    that the SET of distinct fold counts and slat pitches
    printed on each sheet is exactly one each.
    """

    @pytest.fixture(scope="class")
    def flat_fold_height_55_pdf(self):
        """Founder's live case: 55" produces 8 folds @ 6-7/8\"
        (round(55/7) = round(7.857) = 8)."""
        spec = {
            "product_type": "flat_fold",
            "dims": {"width": 69.5, "height": 55.0},
            "client_name": "", "site_address": "", "material": "",
            "date": "",
        }
        return render_spec(spec)

    @pytest.fixture(scope="class")
    def flat_fold_height_64_pdf(self):
        """The golden-reference case: 64" produces 9 folds @ 7-1/8"
        (round(64/7) = round(9.143) = 9). This is what the
        hard-coded '9 folds @ 7-1/8"' was originally written for."""
        spec = {
            "product_type": "flat_fold",
            "dims": {"width": 38.0, "height": 64.0},
            "client_name": "", "site_address": "", "material": "",
            "date": "",
        }
        return render_spec(spec)

    @pytest.fixture(scope="class")
    def flat_fold_height_30_pdf(self):
        """Short shade: 30" produces 4 folds @ 7-1/2"
        (round(30/7) = round(4.286) = 4)."""
        spec = {
            "product_type": "flat_fold",
            "dims": {"width": 36.0, "height": 30.0},
            "client_name": "", "site_address": "", "material": "",
            "date": "",
        }
        return render_spec(spec)

    def test_fold_count_single_value_height_55(self, flat_fold_height_55_pdf):
        text = _pdf_to_text(flat_fold_height_55_pdf)
        counts = _extract_fold_count(text)
        assert len(counts) >= 3, (
            f"expected at least 3 fold-count sites on a flat-fold "
            f"sheet, found {counts!r}"
        )
        assert len(set(counts)) == 1, (
            f"fold count disagrees across sites on one sheet "
            f"(height=55): {counts!r}. The live bug: header said "
            f"'9 folds' while layout math said '8 ×'."
        )
        assert counts[0] == 8, (
            f"round(55/7) should yield 8 folds; sheet says "
            f"{counts[0]}"
        )

    def test_fold_count_single_value_height_64(self, flat_fold_height_64_pdf):
        text = _pdf_to_text(flat_fold_height_64_pdf)
        counts = _extract_fold_count(text)
        assert len(set(counts)) == 1, (
            f"fold count disagrees on golden-reference sheet "
            f"(height=64): {counts!r}"
        )
        assert counts[0] == 9

    def test_fold_count_single_value_height_30(self, flat_fold_height_30_pdf):
        text = _pdf_to_text(flat_fold_height_30_pdf)
        counts = _extract_fold_count(text)
        assert len(set(counts)) == 1, (
            f"fold count disagrees on short sheet (height=30): "
            f"{counts!r}"
        )
        assert counts[0] == 4

    def test_slat_pitch_single_value_height_55(self, flat_fold_height_55_pdf):
        text = _pdf_to_text(flat_fold_height_55_pdf)
        pitches = _extract_slat_pitches(text)
        # The set is collapsed by dedup; a correct sheet has
        # exactly one pitch value printed (layout math, header
        # descriptor, notes all agree).
        assert pitches, (
            f"expected at least one slat pitch on a flat-fold "
            f"sheet, found {pitches!r}"
        )
        assert len(set(pitches)) == 1, (
            f"slat pitch disagrees across sites on one sheet "
            f"(height=55): {pitches!r}. Layout math says '6-7/8\"'; "
            f"the pre-fix header said '7-1/8\"' (rounded-up golden-"
            f"reference pitch)."
        )
        assert pitches == ['6-7/8"'], (
            f"expected exactly 6-7/8\" for height=55 (round(55/7)=8 "
            f"slats @ 6.875\"), got {pitches!r}"
        )

    def test_slat_pitch_single_value_height_64(self, flat_fold_height_64_pdf):
        text = _pdf_to_text(flat_fold_height_64_pdf)
        pitches = _extract_slat_pitches(text)
        assert len(set(pitches)) == 1, (
            f"slat pitch disagrees on golden-reference sheet "
            f"(height=64): {pitches!r}"
        )
        assert pitches == ['7-1/8"']

    def test_slat_pitch_single_value_height_30(self, flat_fold_height_30_pdf):
        text = _pdf_to_text(flat_fold_height_30_pdf)
        pitches = _extract_slat_pitches(text)
        assert len(set(pitches)) == 1, (
            f"slat pitch disagrees on short sheet (height=30): "
            f"{pitches!r}"
        )
        # round(30/7) = round(4.286) = 4; 30/4 = 7.5 → 7-1/2"
        assert pitches == ['7-1/2"']


class TestFoldDescriptorHelper:
    """Unit tests for the fold_descriptor helper in roman.py.
    Pins the single source of truth."""

    def test_height_55_yields_8_folds(self):
        from app.services.drawing.templates.roman import fold_descriptor
        assert fold_descriptor("flat_fold", 55.0) == '8 folds @ 6-7/8"'

    def test_height_64_yields_9_folds(self):
        from app.services.drawing.templates.roman import fold_descriptor
        assert fold_descriptor("flat_fold", 64.0) == '9 folds @ 7-1/8"'

    def test_height_30_yields_4_folds(self):
        from app.services.drawing.templates.roman import fold_descriptor
        # round(30/7) = round(4.286) = 4; 30/4 = 7.5 → 7-1/2
        assert fold_descriptor("flat_fold", 30.0) == '4 folds @ 7-1/2"'

    def test_height_100_yields_14_folds(self):
        from app.services.drawing.templates.roman import fold_descriptor
        # round(100/7) = round(14.286) = 14; 100/14 ≈ 7.143 → 7-1/8
        assert fold_descriptor("flat_fold", 100.0) == '14 folds @ 7-1/8"'

    def test_unknown_product_type_returns_empty(self):
        from app.services.drawing.templates.roman import fold_descriptor
        assert fold_descriptor("nonexistent_style", 64.0) == ""

    def test_zero_height_returns_empty(self):
        from app.services.drawing.templates.roman import fold_descriptor
        assert fold_descriptor("flat_fold", 0.0) == ""