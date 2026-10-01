"""Tests for intent-based freshness, completeness recovery signals, and score flags."""
from app.services.max.answer_quality import (
    detect_quality_flags,
    freshness_directive,
    freshness_intent,
    needs_continuation,
    strip_empty_sections,
)


def test_freshness_is_intent_based_without_universal_date_cap():
    assert freshness_intent("What's the best news this week on AI agent orchestration?") == "fresh"
    directive = freshness_directive("What's the best news this week on AI agent orchestration?")
    assert "no universal 14-day cutoff" in directive
    assert "publication date" in directive


def test_historical_question_is_not_forced_to_recent_filter():
    assert freshness_intent("How did agent orchestration evolve in 2021?") == "historical"
    assert freshness_directive("How did agent orchestration evolve in 2021?") == ""


def test_completeness_guard_catches_heading_only_and_dangling_sections():
    assert needs_continuation("## Best options", user_message="Explain the best options for me")
    text = "## Sources\n\n## Answer\nUseful answer."
    assert "## Sources" not in strip_empty_sections(text)
    flags = detect_quality_flags("## Sources", user_message="Give me sources")
    assert flags["truncated"] and flags["empty_section"]


def test_web_answer_without_date_or_url_is_stale_source_flag():
    flags = detect_quality_flags(
        "The leading story is important.",
        tool_results=[{"tool": "web_search", "success": True}],
    )
    assert flags["stale_source"]


def test_complete_drapery_answer_has_no_truncation_flag():
    flags = detect_quality_flags(
        "A French pleat is a tailored three-fold heading; a goblet pleat has rounded cups and a more formal look.",
        user_message="How does a French pleat compare to a goblet pleat for drapery?",
    )
    assert not flags["truncated"]


def test_evergreen_public_facts_require_web_grounding_and_citations():
    from app.services.max.factual_guard import (
        grounding_directive,
        is_factual_question,
    )

    assert is_factual_question("How does a French pleat compare to a goblet pleat for drapery?")
    policy = grounding_directive("How does a French pleat compare to a goblet pleat for drapery?")
    assert "numbered inline markdown citation" in policy
    assert "Sources list" in policy
    assert "Max's inference" in policy
    assert "do not impose a date limit" in policy


def test_factual_guard_exempts_chitchat_and_internal_data():
    from app.services.max.factual_guard import is_factual_question

    assert not is_factual_question("How are you today?")
    assert not is_factual_question("What is the status of quote # EST-2026-293?")
    assert not is_factual_question("What is our founder pricing rule for goblet pleats?")


def test_colon_intro_without_list_is_incomplete_but_colon_with_list_is_complete():
    from app.services.max.answer_quality import needs_continuation, strip_empty_sections

    assert needs_continuation("Max's inference:\nThe practical tradeoff is function vs. statement:")
    complete = "Max's inference:\nThe practical tradeoff is function vs. statement:\n- French for function\n- Goblet for statement"
    assert not needs_continuation(complete)
    assert "statement:" not in strip_empty_sections("The practical tradeoff is function vs. statement:")
