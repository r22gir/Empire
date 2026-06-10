"""D3 — MAX drawing routing tests.

Pins the 6-way intent_mode classification (per D1 + D1 Addendum) and the
integration with the existing DrawingHandoff dataclass.

Tests:
1. shop drawing request routes to shop_drawing
2. sketch analysis request routes to sketch_analysis
3. concept image request routes to concept_image
4. planning request routes to planning_help
5. animated diagram request routes to animated_diagram
6. visual explainer request routes to visual_explainer
7. is_drawing_intent correctly fires on animated / explainer phrases
   (regression: previously this returned False)
8. DrawingHandoff carries the new intent_mode field with the right value
9. Priority: animation wins over generic "drawing" keywords
10. Negation preservation: existing negation patterns still return False
"""
from __future__ import annotations

import pytest

from app.services.max.drawing_intent import (
    DrawingHandoff,
    build_drawing_handoff,
    classify_intent_mode,
    is_drawing_intent,
)


# ── T1: shop drawing → shop_drawing ──────────────────────────────────
def test_t1_shop_drawing_routes_to_shop_drawing():
    h = build_drawing_handoff(
        "Make a shop drawing for this banquette with dimensions"
    )
    assert h.is_drawing_intent is True
    assert h.intent_mode == "shop_drawing"


# ── T2: sketch analysis → sketch_analysis ────────────────────────────
def test_t2_sketch_analysis_routes_to_sketch_analysis():
    h = build_drawing_handoff(
        "Analyze this sketch and tell me what dimensions are missing"
    )
    assert h.is_drawing_intent is True
    assert h.intent_mode == "sketch_analysis"


# ── T3: concept image → concept_image ────────────────────────────────
def test_t3_concept_image_routes_to_concept_image():
    """A 'concept image' request is classified to concept_image regardless
    of whether the existing is_drawing_intent gate fires. D3 is additive
    and orthogonal to the existing gate.
    """
    h = build_drawing_handoff("Make a concept image of this bench idea")
    assert h.intent_mode == "concept_image"


# ── T4: planning help → planning_help ────────────────────────────────
def test_t4_planning_routes_to_planning_help():
    """Per Founder spec: 'Help me plan how to build this' must route
    to planning_help (not visual_explainer, even though 'how to' is
    a substring of 'how to build').
    """
    h = build_drawing_handoff("Help me plan how to build this")
    # planning_help is NOT a drawing intent; is_drawing_intent may be
    # False here. The intent_mode is the routed intent, regardless.
    assert h.intent_mode == "planning_help"


# ── T5: animated diagram → animated_diagram ──────────────────────────
def test_t5_animated_diagram_routes_to_animated_diagram():
    h = build_drawing_handoff(
        "Make an animated diagram showing the cushion construction sequence"
    )
    assert h.is_drawing_intent is True
    assert h.intent_mode == "animated_diagram"


# ── T6: visual explainer → visual_explainer ──────────────────────────
def test_t6_visual_explainer_routes_to_visual_explainer():
    h = build_drawing_handoff(
        "Create a visual explainer for how this Murphy bed mechanism works"
    )
    assert h.is_drawing_intent is True
    assert h.intent_mode == "visual_explainer"


# ── T7: is_drawing_intent fires on animated / explainer phrases ───────
def test_t7_is_drawing_intent_fires_on_animated_explainer():
    """D3 regression: previously is_drawing_intent returned False for
    'animated diagram' / 'visual explainer' because those phrases
    weren't in DRAWING_KEYWORDS. Now they are.
    """
    assert is_drawing_intent(
        "Make an animated diagram showing the cushion construction sequence"
    ) is True
    assert is_drawing_intent(
        "Create a visual explainer for how this Murphy bed mechanism works"
    ) is True
    assert is_drawing_intent("Show me an installation diagram") is True


# ── T8: DrawingHandoff carries intent_mode ───────────────────────────
def test_t8_drawing_handoff_has_intent_mode_field():
    h = DrawingHandoff(is_drawing_intent=True)
    assert h.intent_mode == "unknown"  # default for backward compatibility
    h2 = DrawingHandoff(
        is_drawing_intent=True, intent_mode="animated_diagram"
    )
    assert h2.intent_mode == "animated_diagram"


# ── T9: priority — animation wins over generic "drawing" ─────────────
def test_t9_priority_animation_wins_over_drawing():
    """A message containing BOTH 'animation' and 'drawing' keywords
    must route to animated_diagram, not shop_drawing.
    """
    assert (
        classify_intent_mode("Make an animation showing the drawing assembly")
        == "animated_diagram"
    )
    assert (
        classify_intent_mode("Generate an animation of the drawing sequence")
        == "animated_diagram"
    )


# ── T10: existing negation patterns still return False ───────────────
def test_t10_existing_negation_patterns_preserved():
    """The pre-existing negation patterns (not asking you to draw, etc.)
    must still suppress drawing intent. D3 is additive.
    """
    negation_phrases = [
        "I am not asking you to draw",
        "do not draw",
        "I don't need a drawing",
        "I'm not asking for a drawing",
        "no drawing-router",
    ]
    for phrase in negation_phrases:
        assert is_drawing_intent(phrase) is False, (
            f"Negation phrase {phrase!r} should suppress drawing intent"
        )


# ── Bonus: pure classify_intent_mode with no drawing signal → unknown ─
def test_bonus_no_drawing_signal_returns_unknown():
    assert classify_intent_mode("What is the weather like today?") == "unknown"
    assert classify_intent_mode("") == "unknown"
    assert classify_intent_mode(None or "") == "unknown"


# ── Bonus: 17-case exhaustive classifier sweep ───────────────────────
@pytest.mark.parametrize(
    "text,expected_mode",
    [
        ("Make a shop drawing for this banquette with dimensions", "shop_drawing"),
        ("Analyze this sketch and tell me what dimensions are missing", "sketch_analysis"),
        ("Make a concept image of this bench idea", "concept_image"),
        ("Help me plan how to build this", "planning_help"),
        ("Make an animated diagram showing the cushion construction sequence", "animated_diagram"),
        ("Create a visual explainer for how this Murphy bed mechanism works", "visual_explainer"),
        ("What is the weather like today?", "unknown"),
        ("Draw a bench", "shop_drawing"),
        ("Make me an animation showing the assembly steps", "animated_diagram"),
        ("I do not need a drawing", "unknown"),
        ("Animation of cushion layers", "animated_diagram"),
        ("Explainer video for headboard mounting", "visual_explainer"),
        ("What dimensions are missing from this sketch?", "sketch_analysis"),
        ("", "unknown"),
        ("How to plan a window treatment", "planning_help"),
        ("Show me a concept of a wood-grain finish", "concept_image"),
        ("Make an installation diagram for the headboard", "visual_explainer"),
    ],
)
def test_bonus_classify_intent_mode_exhaustive(text, expected_mode):
    assert classify_intent_mode(text) == expected_mode
