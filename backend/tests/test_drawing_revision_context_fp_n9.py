"""FP-N9 / FP-N2 / FP-N3 regression (Night Lab 2026-10-31).

After several revision turns Max lost the job, reverted 10" channels to 12",
and accepted fabric code V999-Fake. MOCK quote + temp dirs only. No sends.
"""
from __future__ import annotations

import pytest

from app.services.drawing.job_drawing import run_job_drawing_turn
from app.services.max import job_drawing_intent as jdi
from app.services.max.job_drawing_intent import extract_spec_changes, merge_drawing_job_context

MOCK_QUOTE = {
    "customer_name": "Marley's",
    "quote_number": "EST-TEMP-N9",
    "project_name": "MOCK Marley's Hyattsville",
    "line_items": [],
    "total": 0,
}


@pytest.fixture
def drawings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setattr("app.services.drawing.job_drawing.resolve_job_quote", lambda hint: dict(MOCK_QUOTE))
    return tmp_path


def _u(t):
    return {"role": "user", "content": t}


def _a(t):
    return {"role": "assistant", "content": t}


LONG_HISTORY = [
    _u("make a drawing for the Marley's job with 12 inch channels, backs V003-Cognac, seats V001-Raven"),
    _a('New drawing for Marley\'s (REV A): channels 12"; seat V001-Raven; back V003-Cognac'),
    _u("change it to 10 inch channels"),
    _a('New drawing for Marley\'s (REV B): channels 10"; seat V001-Raven; back V003-Cognac'),
    _u("change it to seats V008-Bittersweet"),
    _a('New drawing for Marley\'s (REV C): channels 10"; seat V008-Bittersweet; back V003-Cognac'),
    _u("revise the drawing: move the wall note"),
    _a('New drawing (REV D): channels 10"'),
    _u("revise the layout labels please"),
    _a('New drawing (REV E): channels 10"'),
]


def test_latest_channel_width_wins_over_older_turns():
    ctx = merge_drawing_job_context("revise the drawing again", LONG_HISTORY)
    assert ctx["spec_changes"]["channel_width_in"] == 10
    assert ctx["spec_changes"]["seat_fabric"] == "V008-Bittersweet"


def test_job_hint_survives_many_turns():
    ctx = merge_drawing_job_context("change it", LONG_HISTORY)
    assert ctx["job_hint"] and "marley" in ctx["job_hint"].lower()


def test_unknown_fabric_code_is_flagged_and_not_carried():
    assert jdi.unknown_fabric_codes("seats V999-Fake") == ["V999-Fake"]
    assert jdi.unknown_fabric_codes("seats V008-Bittersweet") == []
    ctx = merge_drawing_job_context("change it to seats V999-Fake", LONG_HISTORY)
    assert ctx.get("unknown_fabric_codes") == ["V999-Fake"]
    assert ctx["spec_changes"].get("seat_fabric") == "V008-Bittersweet"
    later = merge_drawing_job_context("change it", LONG_HISTORY + [_u("change it to seats V999-Fake")])
    assert "V999-Fake" not in str(later["spec_changes"])


def test_bare_fraction_channel_width_parses():
    assert extract_spec_changes("change it to 3/4 inch channels")["channel_width_in"] == 0.75
    assert extract_spec_changes("channels at 10 1/2 inch")["channel_width_in"] == 10.5


def test_chat_path_rejects_fake_code(drawings_dir):
    turn = run_job_drawing_turn("change it to seats V999-Fake", history=LONG_HISTORY, quote=MOCK_QUOTE)
    assert turn["handled"] is True
    assert turn["success"] is False
    assert "V999-Fake" in turn["response"]
    assert not list(drawings_dir.glob("*.pdf"))


def test_chat_path_keeps_10in_and_job_after_many_turns(drawings_dir):
    turn = run_job_drawing_turn("revise the drawing: tighten the notes", history=LONG_HISTORY, quote=MOCK_QUOTE)
    assert turn["success"] is True, turn
    res = turn["result"]
    assert res["dimensions"]["channel_width"] == '10"'
    assert res["fabrics"]["seat"]["code"] == "V008-Bittersweet"
    assert "marley" in str(res["job_hint"]).lower()


def test_latest_revision_persists_when_history_is_truncated(drawings_dir):
    first = run_job_drawing_turn("change it to 10 inch channels", history=LONG_HISTORY[:2], quote=MOCK_QUOTE)
    assert first["success"] and first["result"]["dimensions"]["channel_width"] == '10"'
    # New session: history window only has the job name, not the 10" turn.
    nxt = run_job_drawing_turn(
        "revise the drawing for the Marley's job: tighten the notes", history=[], quote=MOCK_QUOTE,
    )
    assert nxt["success"] is True, nxt
    assert nxt["result"]["dimensions"]["channel_width"] == '10"'
