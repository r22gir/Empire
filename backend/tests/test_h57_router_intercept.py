"""H57 — drawing-router keyword-substring intercept fix.

Tests for DISPATCH H57 (2026-08-19). After the Phase 2 fix:

  - Question forms NEVER route: "what is", "what's", "explain",
    "tell me about", "how does", "why ", "define ", etc.
  - Long pastes (>500 chars) NEVER route — likely a document
    submission, not a generation prompt.
  - Uncertainty → MAX (the router must never be the last word on an
    ambiguous turn).
  - Explicit user rejections + cancel keywords suppress routing.
  - Strong draw patterns + multi-token "plan" phrases + animation
    phrases + word-boundary matches against DRAWING_KEYWORDS all
    route normally.
  - Word-boundary substring matching — "drawing" matches "drawing"
    but NOT "withdrawing", "redrawing", or "drawings".

Fixtures per the dispatch (verbatim where possible):

  NEGATIVE (must reach MAX, not the router):
    1. "what is a drawing"
    2. "explain the difference between a drawing and a sketch"
    3. long dispatch paste (body >500 chars containing the word)

  POSITIVE (must still route):
    4. "draw me a roman shade, 68 high 70 wide"
    5. "generate the B1 sheet for the Willard bench"
    6. explicit drawing request with dimensions supplied
"""
from __future__ import annotations

import re

from app.services.max.drawing_intent import (
    DRAWING_KEYWORDS,
    is_drawing_intent,
)


# ══════════════════════ NEGATIVE FIXTURES (must NOT route) ═══════════════

class TestH57NegativeFixtures:
    """Per the dispatch: these must reach MAX, not drawing-router.
    Pre-fix, all three routed. Post-fix: question forms + long
    pastes + explicit rejections all return False."""

    def test_negative_1_what_is_a_drawing(self):
        """The founder's probe A. Returns False (no drawing intent)."""
        assert is_drawing_intent("what is a drawing") is False, (
            "question form 'what is' must suppress drawing intent — "
            "the founder's probe A must reach MAX, not the router"
        )

    def test_negative_2_explain_difference_drawing_sketch(self):
        """Funder probe B variant. Returns False."""
        assert is_drawing_intent(
            "explain the difference between a drawing and a sketch"
        ) is False

    def test_negative_3_long_paste_with_drawing(self):
        """Funder probe B variant — dispatch paste. Body >500 chars.
        Must NOT route: it's a document submission, not a request."""
        # Body >500 chars (padding to ensure the threshold trips).
        body = (
            "REPORT 2026-08-19 — drawing-router keyword intercept\n\n"
            "Per DISPATCH H57, the drawing router intercepts MAX on "
            "the word 'drawing'. Founder probes A and B demonstrated "
            "the failure. Probe A: 'what is a drawing' returns "
            "missing-dimensions. Probe B: long paste with 'drawing' "
            "vocabulary consumes the turn. Both must reach MAX. "
            "\n\n"
            "Fix: route on INTENT TO GENERATE, not vocabulary. "
            "Word-boundary substring. Question forms never route. "
            "Long pastes never route. Uncertainty goes to MAX."
            + " " * 50  # padding to clear 500-char threshold
        )
        assert len(body) > 500
        assert is_drawing_intent(body) is False, (
            "long paste (body >500 chars) with 'drawing' keyword "
            "must NOT route — it's a document, not a request"
        )

    def test_negative_word_boundary_substring(self):
        """'drawing' alone matches. 'withdrawing', 'redrawing',
        'drawings' do NOT (pre-fix they did — substring)."""
        assert is_drawing_intent("drawing") is False, (
            "bare 'drawing' (no intent context) must NOT route — "
            "the H57 dispatch fixes the keyword-substring trap. "
            "Bare keyword without a strong draw pattern or "
            "multi-token phrase must return False."
        )
        # Negative cases — substring of longer word:
        assert is_drawing_intent("I'm withdrawing the request") is False
        assert is_drawing_intent("redrawing the bench") is False
        assert is_drawing_intent("all my drawings are stored here") is False

    def test_negative_explicit_rejection(self):
        """User explicitly rejects drawing-router. Suppresses."""
        assert is_drawing_intent("do not use drawing-router please") is False
        assert is_drawing_intent("don't use drawing-router") is False

    def test_negative_trailing_question_mark(self):
        """Trailing '?' is a strong question signal. Must NOT route."""
        assert is_drawing_intent("what does a drawing look like?") is False
        assert is_drawing_intent("how does this drawing work?") is False


# ══════════════════════ POSITIVE FIXTURES (must still route) ═════════════

class TestH57PositiveFixtures:
    """Per the dispatch: these MUST still route after the fix."""

    def test_positive_4_draw_me_a_roman_shade(self):
        """Founder fixture 4. Strong 'draw me ' pattern → True."""
        assert is_drawing_intent(
            "draw me a roman shade, 68 high 70 wide"
        ) is True

    def test_positive_5_generate_b1_sheet(self):
        """Founder fixture 5. Strong 'generate' word-boundary → True."""
        assert is_drawing_intent(
            "generate the B1 sheet for the Willard bench"
        ) is True

    def test_positive_6_explicit_drawing_request(self):
        """Founder fixture 6. Explicit drawing request with dims → True."""
        assert is_drawing_intent(
            "Roman shade, width 68, drop 70"
        ) is True

    def test_positive_strong_draw_pattern_draw_a(self):
        """'draw a <thing>' is unambiguous → True."""
        assert is_drawing_intent("draw a 4-view of the bench") is True
        assert is_drawing_intent("draw an isometric for the window") is True

    def test_positive_floor_plan_phrase(self):
        """Multi-token 'floor plan' phrase → True."""
        assert is_drawing_intent(
            "I need a floor plan of the main level"
        ) is True

    def test_positive_animated_diagram(self):
        """Animation pattern routes through drawing-router with
        animated_diagram intent_mode (per D3 / D1 Addendum)."""
        assert is_drawing_intent("show me an animated diagram") is True


# ══════════════════════ WORD-BOUNDARY CHECK (C-fix) ════════════════════════

class TestH57WordBoundaryMatch:
    """H57 C-fix: trigger uses word-boundary regex, not substring.
    'drawing' alone is NOT enough (must be a strong draw pattern
    OR multi-token phrase OR animation phrase)."""

    def test_bare_drawing_does_not_route(self):
        """Bare 'drawing' must NOT route — the founder's probe A."""
        assert is_drawing_intent("drawing") is False

    def test_drawing_alone_in_sentence_does_not_route(self):
        """Mentioning drawing in a sentence (no intent) must NOT route."""
        assert is_drawing_intent("I read the drawing specification") is False
        assert is_drawing_intent("the drawing is on the wall") is False

    def test_withdrawing_does_not_match_drawing(self):
        """Substring of a longer word — must NOT match 'drawing'."""
        assert is_drawing_intent("I'm withdrawing my request") is False

    def test_redrawing_does_not_match_drawing(self):
        """Compound word — must NOT match the bare 'drawing' keyword."""
        assert is_drawing_intent("I'm redrawing the plan") is False

    def test_drawings_does_not_match_drawing(self):
        """Plural — must NOT match the bare 'drawing' keyword."""
        assert is_drawing_intent("all the drawings are stored") is False


# ══════════════════════ LONG-PASTE SUPPRESSION CHECK (H57) ════════════════

class TestH57LongPasteSuppression:
    """H57: long pastes (>500 chars) with a drawing keyword NEVER
    route — it's a document submission, not a generation request."""

    def test_long_paste_with_render_word_does_not_route(self):
        """Body >500 chars with 'render' anywhere — does NOT route."""
        text = "A" * 100 + " I want to render this thing " + "B" * 400
        assert len(text) > 500
        assert is_drawing_intent(text) is False

    def test_short_prompt_with_render_word_still_routes(self):
        """Body <=500 chars with 'render' + intent — still routes."""
        assert is_drawing_intent("render the bench, 96 wide") is True


# ══════════════════════ PENDING-TABLE FIX (H57 A-fix) ════════════════════════

class TestH57PendingRelease:
    """H57 A-fix: any turn that is NOT a continuation RELEASES
    the pending job. A user must never be trapped in a solicitation
    loop. The drawing_pending module's set_pending / get_pending /
    clear_pending are tested at the integration level (router
    handler). Unit-test the release semantics here."""

    def test_pending_release_on_non_continuation_turn(self):
        """A pending snapshot is abandoned if the next turn is NOT
        a continuation reply (and is a drawing intent)."""
        from app.services.max.drawing_pending import is_continuation_reply
        # pending-style snapshot dict (the real one in router.py
        # uses this shape): {"missing": [...], "subject": ...}.
        snap_missing = ["width", "depth"]
        # Non-continuation: "I'm just checking on something else"
        # is NOT a continuation reply for width/depth.
        assert is_continuation_reply(
            "I'm just checking on something else", snap_missing
        ) is False

    def test_pending_release_when_user_changes_topic(self):
        """Switching topics mid-solicitation releases the pending."""
        from app.services.max.drawing_pending import is_continuation_reply
        # Original pending: width/depth missing.
        # Next turn: unrelated question
        assert is_continuation_reply(
            "what time is the meeting", ["width", "depth"]
        ) is False


# ══════════════════════ KEYWORD LIST (informational) ═══════════════════════

def test_drawing_keywords_constant_includes_intent_words():
    """Sanity: the trigger list contains the intent-bearing words
    AND no longer contains the bare 'drawing' substring as the first
    hit (H57 C-fix removed it from the list)."""
    # Bare 'drawing' is GONE — multi-token phrases like
    # 'section drawing' still contain it as part of the phrase.
    assert "drawing" not in DRAWING_KEYWORDS
    assert "section drawing" in DRAWING_KEYWORDS
    assert "pdf drawing" in DRAWING_KEYWORDS
    assert "bench drawing" in DRAWING_KEYWORDS
    # Intent-bearing words remain:
    assert "render" in DRAWING_KEYWORDS
    assert "sketch" in DRAWING_KEYWORDS
    assert "elevation" in DRAWING_KEYWORDS
    assert "isometric" in DRAWING_KEYWORDS
    # H57 FIX: generate + make verbs added (positive fixture 5)
    assert "generate drawing" in DRAWING_KEYWORDS
    assert "generate the" in DRAWING_KEYWORDS
    assert "make a" in DRAWING_KEYWORDS
    assert "make me" in DRAWING_KEYWORDS
