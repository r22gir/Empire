"""2026-10-08 (Rafael): measurements in fractions, channel cut allowance in Max's style rules."""
from app.services.max.answer_policy import STYLE_DIRECTIVE


def test_fraction_rule_in_style_directive():
    assert '26 3/4"' in STYLE_DIRECTIVE and "never decimals" in STYLE_DIRECTIVE
    assert "wood/foam cut" in STYLE_DIRECTIVE and "fabric cut" in STYLE_DIRECTIVE
    assert "quoteiq_chain" in STYLE_DIRECTIVE
