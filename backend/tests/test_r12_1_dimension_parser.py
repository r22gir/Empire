"""PHASE 2 · R12.1 — dimension parser fix + plausibility gate.

The founder reproduced a live bug at 4:49 PM today: typing
`69 1/2" wide x 55" High` produced `width='2"'` in the spec
because the value_first regex took the "2" from the "1/2"
fraction. The sheet rendered silently as a 2" shade.

The fix:
  1. Add `_parse_dimension_value(token)` — a pure helper that
     accepts the founder's required formats (69, 69.5, 69 1/2,
     69-1/2, 5/8, 5' 9", 5' 9-1/2", 5 feet 9 inches) and
     returns the float inches or None. Reuses the proven
     feet/inches/fraction logic from b2_qc.py:1868.
  2. Refactor `_extract_dimensions` in
     app/services/max/drawing_intent.py to route every captured
     value through `_parse_dimension_value`. Unparseable
     tokens drop with a logged warning (dimension surfaces as
     missing, NOT as a partial number).
  3. Add a plausibility gate — values outside `[3.0, 600.0]`
     inches are dropped with a logged warning. Bounds picked
     from the templates' own required dims; the 3" floor
     catches the 2" parse bug, the 600" ceiling (50 feet)
     catches foot/inch typos.
  4. Fix `_match_dim` in app/services/max/drawing_pending.py —
     same fraction gap, currently dead per the Phase 2 finding
     but the founder's directive: "it will not stay dead."
"""
from __future__ import annotations

import pytest

from app.services.max.drawing_intent import (
    _parse_dimension_value,
    _extract_dimensions,
    _DIMENSION_BOUNDS,
)


# ──────────────────────────────────────────────────────────────────────
# _parse_dimension_value — the central pure helper
# ──────────────────────────────────────────────────────────────────────


class TestParseDimensionValueValid:
    """Every format the founder listed. Each must parse to the
    expected float inches."""

    @pytest.mark.parametrize("token, expected_inches", [
        # Bare integer
        ("69",           69.0),
        ("12",           12.0),
        # Decimal
        ("69.5",         69.5),
        ("0.25",         0.25),
        # Whole + fraction, hyphen-joined
        ("69-1/2",       69.5),
        ("12-3/4",       12.75),
        # Whole + fraction, space-separated
        ("69 1/2",       69.5),
        ("12 3/4",       12.75),
        # Standalone fraction
        ("5/8",          0.625),
        ("7/16",         7.0 / 16.0),
        ("1/2",          0.5),
        # Feet + inches
        ("5' 9\"",       69.0),
        ("10' 0\"",      120.0),
        # Feet + inches + fraction (hyphen-joined)
        ("5' 9-1/2\"",   69.5),
        ("5' 3-3/8\"",   63.375),
        # Word form (feet / inches)
        ("5 feet 9 inches",     69.0),
        ("5 feet 9-1/2 inches", 69.5),
        # Whitespace tolerant
        ("  69.5  ",     69.5),
    ])
    def test_valid_token(self, token, expected_inches):
        got = _parse_dimension_value(token)
        assert got is not None, (
            f"expected {expected_inches!r}, got None for token {token!r}"
        )
        assert got == pytest.approx(expected_inches), (
            f"expected {expected_inches!r}, got {got!r} for token {token!r}"
        )


class TestParseDimensionValueInvalid:
    """Tokens the parser must reject. Returning None (not a partial
    number) is the only acceptable failure mode per the dispatch."""

    @pytest.mark.parametrize("token", [
        "",                # empty
        "   ",             # whitespace only
        "abc",             # garbage
        "feet",            # keyword without value
        "inches",          # keyword without value
        "5'",              # feet marker without inches
        "1/0",             # division by zero — explicit fail
        "0/0",             # division by zero — explicit fail
        "-5",              # negative — doesn't match \d+
        "abc 5 wide",      # letters before digit — value-first rejects
        "69 1/2 wide",     # label attached — value parser doesn't strip label
    ])
    def test_invalid_token_returns_none(self, token):
        assert _parse_dimension_value(token) is None, (
            f"expected None for token {token!r}, got a non-None value"
        )


# ──────────────────────────────────────────────────────────────────────
# _extract_dimensions — the live bug + regression
# ──────────────────────────────────────────────────────────────────────


class TestExtractDimensionsRegression:
    """The live founder-reported case MUST produce width=69.5",
    NOT width=2"."""

    def test_founder_live_bug_69_and_a_half_wide(self):
        """The exact string the founder typed at 4:49 PM today.
        Pre-fix this returned {'width': '2"', 'height': '55"'}.
        Post-fix this returns {'width': '69.5"', 'height': '55"'}.
        """
        result = _extract_dimensions(
            '69 1/2" wide x 55" High',
            item_type='flat_fold',
        )
        assert result == {'width': '69.5"', 'height': '55"'}, (
            f"live regression: expected width=69.5\", got {result!r}"
        )

    def test_hyphen_fraction_69_and_a_half_wide(self):
        result = _extract_dimensions(
            '69-1/2" wide 55" high',
            item_type='flat_fold',
        )
        assert result == {'width': '69.5"', 'height': '55"'}


class TestExtractDimensionsAllFormats:
    """Table-driven: every accepted dimension format must parse
    via _extract_dimensions."""

    @pytest.mark.parametrize("text, item_type, expected", [
        # Decimal (control — worked pre-fix)
        ('38 wide 64 long', 'flat_fold',
         {'width': '38"', 'length': '64"'}),
        ('69.5 wide 55 high', 'flat_fold',
         {'width': '69.5"', 'height': '55"'}),
        # Bare fraction (regression — broke pre-fix). Values above
        # the gate floor (3"); the gate-fraction case is in
        # TestPlausibilityGate.
        ('13 3/4 wide 24-1/2 deep', 'bench',
         {'width': '13.75"', 'depth': '24.5"'}),
        # Space-separated whole + fraction
        ('69 1/2 wide 38 1/2 high', 'flat_fold',
         {'width': '69.5"', 'height': '38.5"'}),
        # Hyphen-joined whole + fraction
        ('12-3/4 wide 18 deep 36-1/2 high', 'bench',
         {'width': '12.75"', 'depth': '18"', 'height': '36.5"'}),
        # Feet + inches
        ('5\' 9" wide 4\' 0" high', 'flat_fold',
         {'width': '69"', 'height': '48"'}),
        # Feet + inches + fraction
        ('5\' 9-1/2" wide', 'flat_fold',
         {'width': '69.5"'}),
        # Word form
        ('5 feet 9 inches wide 8 feet 0 inches high', 'flat_fold',
         {'width': '69"', 'height': '96"'}),
    ])
    def test_format(self, text, item_type, expected):
        result = _extract_dimensions(text, item_type=item_type)
        assert result == expected, (
            f"text={text!r}: expected {expected!r}, got {result!r}"
        )


# ──────────────────────────────────────────────────────────────────────
# Plausibility gate
# ──────────────────────────────────────────────────────────────────────


class TestPlausibilityGate:
    """The gate's lower bound catches the 2" bug. The upper bound
    catches foot/inch typos (600" = 50 feet is a sensible cap)."""

    LOWER, UPPER = _DIMENSION_BOUNDS

    def test_bounds_constants(self):
        assert _DIMENSION_BOUNDS == (3.0, 600.0)

    def test_2_inch_width_dropped(self):
        """The exact live-bug outcome must be impossible post-fix."""
        # Even direct injection of "2 wide" must not produce
        # width=2 — the gate drops it.
        result = _extract_dimensions('2" wide', item_type='flat_fold')
        assert result == {}, (
            f"2\" wide should be dropped, got {result!r}"
        )

    def test_3_inch_width_kept_at_boundary(self):
        """3" is the floor. width=3 is the smallest accepted."""
        result = _extract_dimensions('3" wide', item_type='flat_fold')
        assert result == {'width': '3"'}

    def test_2_and_7_8_inch_width_dropped(self):
        """A 2-7/8" width is below the 3" floor."""
        result = _extract_dimensions('2-7/8" wide', item_type='flat_fold')
        assert result == {}

    def test_600_inch_height_kept_at_boundary(self):
        """600" = 50 feet is the ceiling. height=600 is the largest accepted."""
        result = _extract_dimensions('600" high', item_type='flat_fold')
        assert result == {'height': '600"'}

    def test_601_inch_height_dropped(self):
        result = _extract_dimensions('601" high', item_type='flat_fold')
        assert result == {}

    def test_fifty_feet_dropped(self):
        """50'0" = 600.0" — at the boundary, kept. 50'1" = 601" — dropped."""
        result_50ft = _extract_dimensions(
            "50' 0\" wide", item_type='flat_fold'
        )
        assert result_50ft == {'width': '600"'}
        result_50ft1 = _extract_dimensions(
            "50' 1\" wide", item_type='flat_fold'
        )
        assert result_50ft1 == {}

    def test_partial_parse_with_out_of_bounds_label_dropped(self):
        """If a label is parsed but its value is out of bounds,
        the other labels still parse."""
        result = _extract_dimensions(
            '2" wide 38 high 64 long', item_type='flat_fold'
        )
        # width=2 dropped (below 3); height=38 kept; length=64 kept.
        assert result == {'height': '38"', 'length': '64"'}

    def test_mixed_format_under_floor_dropped(self):
        """Fraction form also hits the gate. 5/8 = 0.625" is below
        the 3" floor and must be dropped."""
        result = _extract_dimensions('5/8 wide 38 high', item_type='flat_fold')
        assert result == {'height': '38"'}

    def test_zero_value_dropped(self):
        """0 is below the 3" floor."""
        result = _extract_dimensions('0" wide', item_type='flat_fold')
        assert result == {}

    def test_negative_value_rejected_by_parser(self):
        """Negative numbers don't match \\d+ — parser returns None."""
        assert _parse_dimension_value("-5") is None


# ──────────────────────────────────────────────────────────────────────
# _match_dim — same gap, currently dead, fixed per directive
# ──────────────────────────────────────────────────────────────────────


class TestMatchDimFixed:
    """The same fraction gap that produced width=2 from "69 1/2"
    in _extract_dimensions also existed in _match_dim (used by
    the continuation reply merger). Fixed in R12.1 even though
    the path is dead per the Phase 2 finding."""

    def test_fraction_via_match_dim(self):
        from app.services.max.drawing_pending import _match_dim
        assert _match_dim("69 1/2 wide", "width") == '69.5"'

    def test_hyphen_fraction_via_match_dim(self):
        from app.services.max.drawing_pending import _match_dim
        assert _match_dim("69-1/2 wide", "width") == '69.5"'

    def test_standalone_fraction_via_match_dim(self):
        from app.services.max.drawing_pending import _match_dim
        assert _match_dim("5/8 wide", "width") == '0.625"'

    def test_pre_fix_bug_does_not_recur(self):
        """The exact bug shape from drawing_intent — `69 1/2 wide`
        producing width=2 — must not happen in _match_dim either."""
        from app.services.max.drawing_pending import _match_dim
        result = _match_dim("69 1/2 wide", "width")
        assert result is not None
        assert result != '2.0"', (
            f"pre-fix bug recurred: _match_dim returned {result!r}"
        )