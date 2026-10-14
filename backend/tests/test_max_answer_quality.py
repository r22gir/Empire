"""Tests for intent-based freshness, completeness recovery signals, and score flags."""
from pathlib import Path

from app.services.max.answer_quality import (
    detect_quality_flags,
    file_quality_miss,
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


def test_founder_cut_off_sets_truncated_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("MAX_IMPROVE_SPEC_DIR", str(tmp_path / "specs"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    flags = detect_quality_flags(
        "A full stored reply that the phone never showed.",
        user_message="Message cut off",
    )
    assert flags["truncated"] is True


def test_founder_dude_and_read_article_set_user_repeat(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("MAX_IMPROVE_SPEC_DIR", str(tmp_path / "specs"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    dude = detect_quality_flags("same summary again", user_message="Dude")
    no_read = detect_quality_flags("same summary again", user_message="No... read the article")
    assert dude["user_repeat"] is True
    assert no_read["user_repeat"] is True
    wrong = detect_quality_flags("ok", user_message="wrong")
    assert wrong["user_repeat"] is True
    assert wrong["pushback"] is True
    # Mid-sentence "no" is not a founder correction.
    casual = detect_quality_flags("ok", user_message="I have no extra fabric for Lopez")
    assert casual["user_repeat"] is False
    assert casual["truncated"] is False


def _quality_db(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("MAX_IMPROVE_SPEC_DIR", str(tmp_path / "specs"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    from app.db import database, init_db
    import importlib
    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()
    from app.services.max import improvements as imp
    importlib.reload(imp)
    return imp


def test_quality_miss_weak_phrases_file_nothing(monkeypatch, tmp_path):
    imp = _quality_db(monkeypatch, tmp_path)
    for msg in ("send it again", "no thanks", "Can you send the invoice again"):
        flags = detect_quality_flags("ok", user_message=msg, founder=True)
        filed = file_quality_miss(flags, user_message=msg, founder=True)
        assert filed is None, msg
    assert (imp.list_requests("proposed").get("items") or []) == []
    # Non-founder Dude must not file either.
    assert file_quality_miss({"user_repeat": True}, user_message="Dude", founder=False) is None
    detect_quality_flags("ok", user_message="Dude", founder=False)
    assert (imp.list_requests("proposed").get("items") or []) == []


def test_quality_miss_files_proposed_improvement_deduped(monkeypatch, tmp_path):
    imp = _quality_db(monkeypatch, tmp_path)

    first = file_quality_miss({"truncated": True}, user_message="Message cut off", founder=True)
    assert first and first["status"] == "proposed"
    assert first["kind"] == "fix"
    assert first["requested_via"] == "answer_quality"
    spec = Path(first["spec_path"])
    assert spec.is_file()
    # Same flag set + day, different wording — one row.
    again = file_quality_miss({"truncated": True}, user_message="got cut off on the phone", founder=True)
    assert again["id"] == first["id"]

    dude = detect_quality_flags("same summary", user_message="Dude", founder=True)
    assert dude["user_repeat"] is True
    items = imp.list_requests("proposed").get("items") or []
    repeat_rows = [r for r in items if "user_repeat" in (r.get("title") or "")]
    assert len(repeat_rows) == 1
    detect_quality_flags("same summary", user_message="Dude", founder=True)
    items2 = imp.list_requests("proposed").get("items") or []
    repeat_rows2 = [r for r in items2 if "user_repeat" in (r.get("title") or "")]
    assert len(repeat_rows2) == 1
    assert repeat_rows2[0]["id"] == repeat_rows[0]["id"]
    # At most one per day per flag set (truncated + user_repeat).
    assert len(items2) == 2


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


def test_snippet_only_empty_section_and_lookup_offer_force_continuation():
    from app.services.max.answer_quality import validate_reply_structure

    draft = (
        "I am not able to confirm from these snippets alone:\n\n"
        "Want me to open the articles?"
    )
    issues = validate_reply_structure(draft)
    assert "dangling_colon" in issues
    assert "lookup_offer" in issues
    assert needs_continuation(draft)


def test_colon_intro_without_list_is_incomplete_but_colon_with_list_is_complete():
    from app.services.max.answer_quality import needs_continuation, strip_empty_sections

    assert needs_continuation("Max's inference:\nThe practical tradeoff is function vs. statement:")
    complete = "Max's inference:\nThe practical tradeoff is function vs. statement:\n- French for function\n- Goblet for statement"
    assert not needs_continuation(complete)
    assert "statement:" not in strip_empty_sections("The practical tradeoff is function vs. statement:")


def test_tool_failure_placeholder_is_incomplete_when_verified_data_exists():
    from app.services.max.answer_quality import needs_continuation

    assert needs_continuation(
        "I have not run that yet. web_read: HTTP 403",
        tool_results=[{"tool": "web_search", "success": True}, {"tool": "web_read", "success": False}],
    )


def test_phase_heading_with_goal_only_triggers_continuation():
    draft = (
        "### Phase 0 — Inventory\n"
        "Goal: Baseline counts and totals.\n\n"
        "### Phase 1 — Workflows\n"
        "Goal: Replace invoicing.\n"
    )
    assert needs_continuation(draft, user_message="Finance readiness report with phased plan")


def test_phase_with_steps_is_complete():
    complete = (
        "### Phase 0 — Inventory\n"
        "Goal: Baseline counts.\n"
        "- Export chart of accounts\n"
        "- Reconcile AR\n"
    )
    assert not needs_continuation(complete, user_message="Phased plan")
