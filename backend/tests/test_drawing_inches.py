"""Fraction-only inch formatting for Drawing Studio."""
from app.services.vision.inches import (
    format_inches,
    format_size,
    has_decimal_dimension,
    parse_inches,
)


def test_format_inches_never_emits_a_decimal_point():
    samples = [0, 1, 4.25, 4.5, 4.75, 18, 22.5, 29.125, 72, 96.375, 120.0625]
    for value in samples:
        label = format_inches(value)
        assert "." not in label, label
        assert label.endswith('"')
        assert has_decimal_dimension(label) is False


def test_format_inches_common_woodworking_fractions():
    assert format_inches(72) == '72"'
    assert format_inches(22.5) == '22 1/2"'
    assert format_inches(4.75) == '4 3/4"'
    assert format_inches(0.375) == '3/8"'
    assert format_inches(0.0625) == '1/16"'
    assert format_inches(-1.25) == '-1 1/4"'
    assert format_inches(18, mark=False) == "18"


def test_format_size_is_true_size_label():
    assert format_size(72, 20) == '72" × 20"'
    assert format_size(72, 20, 0.75) == '72" × 20" × 3/4"'


def test_parse_inches_reads_fractions_and_legacy_decimals():
    assert parse_inches('4 1/2"') == 4.5
    assert parse_inches("3/4") == 0.75
    assert parse_inches(72) == 72
    assert parse_inches('22.5"') == 22.5
    assert parse_inches("bogus", default=18) == 18
