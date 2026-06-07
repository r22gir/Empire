"""Tests for search-context carry-forward in MAX web_search.

The web_search tool previously used the raw user message as the query.
For short follow-up messages (e.g. "current elections" after "tell me about
Colombia"), this caused the search to return generic / US results instead
of the prior topic. The fix injects topic context from the conversation
history into the query.
"""
from app.services.max.search_context import build_search_query


def test_short_followup_keeps_anchor_from_history():
    history = [
        {"role": "user", "content": "tell me about Colombia"},
        {"role": "assistant", "content": "Colombia is a country in South America..."},
    ]
    out = build_search_query("current elections", history=history)
    assert out["context_injected"] is True
    assert "Colombia" in out["context_terms"]
    assert "Colombia" in out["query"]
    assert "current elections" in out["query"]


def test_topic_implicit_marker_injects_anchor():
    history = [
        {"role": "user", "content": "what's happening in France?"},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "and the latest?"},
    ]
    out = build_search_query("and the latest?", history=history)
    assert out["context_injected"] is True
    assert "France" in out["context_terms"]


def test_anchor_already_in_message_does_not_double_inject():
    history = [
        {"role": "user", "content": "tell me about Colombia"},
        {"role": "assistant", "content": "Colombia ..."},
    ]
    out = build_search_query("Colombia elections", history=history)
    assert out["context_injected"] is False  # already mentions Colombia


def test_long_specific_message_does_not_inject():
    history = [
        {"role": "user", "content": "tell me about Colombia"},
        {"role": "assistant", "content": "Colombia ..."},
    ]
    out = build_search_query(
        "what are the specific candidates in the upcoming Colombian presidential election 2026",
        history=history,
    )
    assert out["context_injected"] is False


def test_empty_history_does_not_inject():
    out = build_search_query("current elections", history=[])
    assert out["context_injected"] is False
    out = build_search_query("current elections", history=None)
    assert out["context_injected"] is False


def test_no_anchor_in_history_does_not_inject():
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    out = build_search_query("current elections", history=history)
    assert out["context_injected"] is False


def test_us_anchor_recognized():
    history = [
        {"role": "user", "content": "what about US politics?"},
        {"role": "assistant", "content": "US politics..."},
    ]
    out = build_search_query("current elections", history=history)
    assert out["context_injected"] is True
    # US maps to canonical "U.S."
    assert any("U.S." in t or "US" in t for t in out["context_terms"])


def test_mexico_anchor_recognized():
    history = [
        {"role": "user", "content": "I just moved to Mexico"},
        {"role": "assistant", "content": "Mexico is..."},
    ]
    out = build_search_query("what about the weather?", history=history)
    assert out["context_injected"] is True
    assert "Mexico" in out["context_terms"]
