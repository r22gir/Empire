"""Tests for drawing-intent router fix.

The router previously classified ANY message containing the word "plan" as
a drawing intent, which caused MAX to route "plan mode, propose Telegram
voice pipeline" to the drawing handler. These tests pin the new behavior:
    - "plan mode", "make a plan for ...", "Telegram voice pipeline plan" must NOT
      route to drawing.
    - "make a plan for backend/db/grok/claude/ollama/tg" must NOT route to drawing.
    - "draw a floor plan with dimensions" must still route to drawing.
    - Bare "draw me a floor plan" must still route to drawing.
"""
from app.services.max.drawing_intent import is_drawing_intent


# ── Plan-mode / proposal-mode negatives ──────────────────────────────────

PLAN_MODE_NEGATIVES = [
    "plan mode, propose Telegram voice pipeline",
    "Plan mode — give me a plan for backend",
    "make a plan for the backend integration",
    "make a plan for db schema",
    "make a plan for grok routing",
    "make a plan for claude fallback",
    "make a plan for ollama local",
    "make a plan for tg bot",
    "propose a plan for voice pipeline",
    "write a plan for the migration",
    "draft a plan to ship the integration",
    "planning the rollout of the new webhooks",
    "Telegram voice pipeline plan: STT, TTS, queue",
    "voice pipeline plan: start with whisper",
    "what about a roadmap for the next 30 days",
    "can you make a plan for our quarterly review",
]


# ── These MUST still route to drawing ───────────────────────────────────

DRAWING_POSITIVES = [
    "draw a floor plan with dimensions",
    "draw a bench 96 wide, 22 deep, 36 high",
    "draw me a chair 24 wide 24 deep 36 high",
    "draw the dining room layout",
    "draw this image as a plan",
    "show me the floor plan of the kitchen",
    "isometric view of the bench",
    "elevation drawing for the west wall",
    "section drawing of the stairs",
    "CAD file for the banquette",
    "4-view of the dining table",
    "section view of the cabinet",
]


def test_plan_mode_messages_do_not_route_to_drawing():
    for msg in PLAN_MODE_NEGATIVES:
        assert is_drawing_intent(msg) is False, (
            f"plan-mode message should NOT route to drawing: {msg!r}"
        )


def test_drawing_messages_still_route_to_drawing():
    for msg in DRAWING_POSITIVES:
        assert is_drawing_intent(msg) is True, (
            f"drawing message should still route to drawing: {msg!r}"
        )


def test_explicit_negation_suppresses_drawing():
    """If user explicitly says don't draw, suppress even strong patterns."""
    assert is_drawing_intent("don't draw a bench, just describe it") is False
    assert is_drawing_intent("not a drawing, just an estimate") is False


def test_drawing_negation_specific_phrases():
    assert is_drawing_intent("do not use drawing-router for this") is False
    assert is_drawing_intent("don't use drawing-router") is False
    assert is_drawing_intent("no drawing-router please") is False


def test_empty_string_does_not_route():
    assert is_drawing_intent("") is False
    # The router is defensive: even None should not raise.
    assert is_drawing_intent(None) is False  # type: ignore[arg-type]
