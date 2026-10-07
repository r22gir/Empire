"""Job visual asks must not web-presearch or look like Unsplash routes (2026-10-06 Marley's miss)."""
from app.services.max.factual_guard import is_factual_question
from app.services.max.answer_policy import should_pre_search, wants_research


TONIGHT = [
    "Show me mick up drwings or something for bisual reference",
    "Show me mockup drawings or something for visual reference",
    "Can you give me  the diagram or drawing of the pattern for illustration purposes only",
    "Give me proposed pattern v original 8 pnale nasket weave",
    "More like the requested design goes back to original request. Best possible solution is a 4 panel basket weave v 8 panel that we had. We can meet you half way at 65 sq ft.",
]


def test_tonight_messages_are_not_public_factual():
    for msg in TONIGHT:
        assert is_factual_question(msg) is False, msg


def test_tonight_messages_do_not_pre_search():
    for msg in TONIGHT:
        legacy = is_factual_question(msg) or wants_research(msg)
        assert should_pre_search(msg, legacy) is False, msg


def test_explicit_research_still_pre_searches():
    msg = "research the latest textile basket weave trends online"
    assert wants_research(msg) is True
    assert should_pre_search(msg, True) is True


def test_public_evergreen_still_pre_searches():
    msg = "How does a French pleat compare to a ripplefold?"
    assert is_factual_question(msg) is True
    assert should_pre_search(msg, True) is True
