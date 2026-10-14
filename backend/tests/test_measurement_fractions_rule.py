"""2026-10-08 (Rafael): measurements in fractions, channel cut allowance in Max's style rules."""
from app.services.max.answer_policy import STYLE_DIRECTIVE


def test_fraction_rule_in_style_directive():
    assert '26 3/4"' in STYLE_DIRECTIVE and "never decimals" in STYLE_DIRECTIVE
    assert "Wood/board cut is true size with no add-ons" in STYLE_DIRECTIVE
    assert "Foam cut equals the wood cut" in STYLE_DIRECTIVE
    assert "Fabric cut is a separate labeled size" in STYLE_DIRECTIVE
    assert "quoteiq_chain" in STYLE_DIRECTIVE
    # Old add-on rule must stay gone.
    assert '12" channel as needing 18"' in STYLE_DIRECTIVE
    assert "Never add 2 1/2" in STYLE_DIRECTIVE
    assert "add 2 1/2\" / 12\" channel needs 18\"" not in STYLE_DIRECTIVE.replace(
        "Never add 2 1/2\" or treat a 12\" channel as needing 18\".", ""
    )
