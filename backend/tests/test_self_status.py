"""'What are you building / what's next' -> internal state, never web research (stubbed state, no live data)."""
from __future__ import annotations

import pytest

from app.services.max import self_status as ss
from app.services.max.factual_guard import is_factual_question

FAKE = {
    "improvements": [
        {"id": 7, "status": "building", "title": "Deposit link on invoices"},
        {"id": 5, "status": "proposed", "title": "File finder: add Gmail attachments + Google Drive search"},
        {"id": 2, "status": "merge_approved", "title": "Old thing"},
    ],
    "commits": [
        {"hash": "aaa", "date": "2099-01-01", "text": "File finder also searches Gmail attachments + Google Drive"},
    ],
    "approvals_pending": 3,
    "tasks": [{"id": "t1", "title": "[Voice request - needs founder approval] Send quotes EST-2026-297 to Rafael",
               "status": "waiting", "created_at": "2099-01-01"}],
}


@pytest.fixture()
def fake_state(monkeypatch):
    monkeypatch.setattr(ss, "gather", lambda: FAKE)
    return FAKE


@pytest.mark.parametrize("msg", [
    "What are you building now?", "And what is empirebox next step with you", "what are you working on",
    "what's next", "what's in progress", "status", "what's the status of empirebox",
])
def test_self_questions_detected_and_never_research(msg):
    assert ss.is_self_status_question(msg)
    assert not is_factual_question(msg)


@pytest.mark.parametrize("msg", [
    "Research what's new in solar for the Travelers claim house and give me 3 things worth my time",
    "what's the status of Nehal's quote", "what is the next step for the Dahlia job",
    "look up what other contractors are building", "what are the best blackout drapery linings",
])
def test_non_self_questions_not_shortcut(msg):
    assert not ss.is_self_status_question(msg)


def test_real_research_question_still_researches():
    assert is_factual_question("Research the best blackout lining fabrics for drapery and cite sources")
    assert is_factual_question("How does a French pleat compare to a ripplefold drapery?")
    from app.services.max.runtime_truth_check import _is_performative_web_search_request as perf
    msg = "look up what you would need for a solar permit in Maryland, with sources"
    assert is_factual_question(msg) or perf(msg)  # the router's pre-search condition


def test_building_reply_is_short_plain_and_grounded(fake_state):
    text = ss.answer("What are you building now?")["text"]
    assert 1 <= len(text.splitlines()) <= 6
    assert "Building now: #7 Deposit link on invoices." in text
    assert "#5 File finder" in text and "Old thing" not in text
    for bad in ("Sources", "Verified", "inference", "###", "Phase", "http", "[1]"):
        assert bad not in text


def test_next_step_names_real_pending_items(fake_state):
    text = ss.answer("And what is empirebox next step with you")["text"]
    assert "In progress: #7" in text and "Waiting on your tap" in text and "#5 File finder" in text
    assert "Send quotes EST-2026-297 to Rafael" in text and "3 outreach drafts" in text
    assert "Voice request" not in text and "Sources" not in text and len(text.splitlines()) <= 5


def test_empty_categories_skipped(monkeypatch):
    monkeypatch.setattr(ss, "gather", lambda: {"improvements": [], "commits": [], "approvals_pending": 0, "tasks": []})
    assert ss.answer("what's next")["text"].startswith("Nothing is queued right now")
    assert ss.answer("what are you building now")["text"] == "Nothing is building right this minute."


def test_commit_subjects_in_plain_words():
    assert ss._plain_commit("feat(max): search all of Rafael's files, share to Rafael only") == \
        "Search all of your files, share to you only"
    assert ss._plain_commit("Max (main edition): founder authority — long tail") == "Founder authority"


def test_chat_endpoint_answers_from_state_without_web(fake_state, monkeypatch):
    import asyncio
    import importlib
    r = importlib.import_module("app.routers.max.router")
    from app.services.max import tool_executor as te
    called = []
    monkeypatch.setattr(te, "execute_tool", lambda *a, **k: called.append(a))
    resp = asyncio.run(r._chat_with_max_service_impl(
        r.ChatRequest(message="What are you building now?", channel="web"),
        canonical_channel="web", canonical_chat_id=None, canonical_founder=True))
    assert resp.model_used == "max-status"
    assert "Building now: #7" in resp.response and "Sources" not in resp.response
    assert not called


def test_voice_has_max_status_tool(fake_state):
    from app.services.max import voice_live as vl
    assert "max_status" in vl.VOICE_TOOL_ALLOWLIST
    out = vl.run_voice_tool("max_status", {"question": "what are you building now"})
    assert out["success"] and "Building now: #7" in out["result"]["text"]


def test_truth_guard_counts_max_status_as_proof():
    from app.services.max import runtime_truth_enforcer as rte
    assert "max_status" in rte.PROOF_TOOL_EXACT
