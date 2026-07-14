"""Sprint 1d Phase A — drawing standard golden bundle + routing fixes.

Run with: cd backend && pytest tests/test_drawing_phase_a.py -v
"""
import os
import re
from pathlib import Path

import pytest

# Adjust path so the test can import drawing_intent / drawing_pending /
# theater_detector regardless of cwd.
import sys
_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))


# ───────────────────────────────────────────────────────────────────
# Phase A — Diff 1: golden bundle present in repo (NO path outside repo)
# ───────────────────────────────────────────────────────────────────

GOLDEN_BUNDLE_FILES = [
    # The standard + reference impl
    "app/services/drawing/EMPIRE_DRAWING_STANDARD.md",
    "app/services/drawing/_legacy_willard_reference.py",
    "app/services/drawing/STANDARD_README.md",
    # Golden PDFs (Phase B + D acceptance)
    "app/services/drawing/golden_reference_willard.pdf",
    "app/services/drawing/golden_templates_10sheet.pdf",
    "app/services/drawing/golden_estimate.pdf",
    # Golden PNGs (Phase C tier-1 mockup acceptance)
    "app/services/drawing/golden_presentation_board.png",
    "app/services/drawing/golden_presentation_board_v1.png",
    "app/services/drawing/golden_presentation_board_proposed.png",
    "app/services/drawing/golden_drapery_composite.png",
    "app/services/drawing/golden_drapery_proposed.png",
]


def test_golden_bundle_committed_to_repo():
    """Phase A — Diff 1: standard + golden outputs are committed INTO the
    repo. After Phase A, NO path outside the repo may be referenced. This
    test enforces that."""
    repo_root = _BACKEND  # _BACKEND = backend/app; paths are backend/app/services/drawing/...
    missing = []
    for rel in GOLDEN_BUNDLE_FILES:
        path = repo_root / rel
        if not path.exists():
            missing.append(rel)
    assert not missing, (
        f"golden bundle missing files (Phase A requires these in the repo, "
        f"no path outside allowed): {missing}"
    )
    # The README must point at the canonical standard.
    readme = (repo_root / "app/services/drawing/STANDARD_README.md").read_text()
    assert "EMPIRE_DRAWING_STANDARD.md" in readme
    assert "_legacy_willard_reference.py" in readme
    assert "golden_presentation_board.png" in readme


# ───────────────────────────────────────────────────────────────────
# Phase A — Diff 2: drawing_intent has NO hardcoded dim defaults
# ───────────────────────────────────────────────────────────────────

def test_no_hardcoded_dim_defaults():
    """Regression guard for the leak the founder saw: a prior job's
    seat_height=18" persisted into a new job because drawing_intent.py
    used dimensions.get(key, "18\"") style defaults. Phase A forbids
    get_default_dims() in the drawing path — missing dims MUST become
    structured questions, never defaults.

    Excluded: the back_height -> height fallback (uses an existing
    founder-supplied value, not an invented default).
    """
    drawing_intent_path = _BACKEND / "app/services/max/drawing_intent.py"
    src = drawing_intent_path.read_text()
    # Forbidden: any default that is a literal digit string (an invented
    # measurement). The back_height pattern is allowed because it falls
    # back to a founder-supplied height value, never to an invented default.
    forbidden = [
        (r'dimensions\.get\(["\']width["\']\s*,\s*["\']\d', "width default"),
        (r'dimensions\.get\(["\']depth["\']\s*,\s*["\']\d', "depth default"),
        (r'dimensions\.get\(["\']seat_height["\']\s*,\s*["\']\d', "seat_height default"),
        (r'dimensions\.get\(["\']back_height["\']\s*,\s*["\']\d', "back_height digit default"),
    ]
    for pat, label in forbidden:
        assert not re.search(pat, src), (
            f"Phase A violation: drawing_intent.py contains a default-dim "
            f"pattern for {label} matching /{pat}/. Per Standard Hard Rule 1, "
            f"missing dims MUST be reported as structured questions, never defaulted."
        )


def test_redraw_keywords_trigger_drawing_intent():
    """Phase A Fix #2: founder re-ask keywords must re-route to drawing-router
    (otherwise the founder's reply falls through to plain chat and the
    drawing job is orphaned)."""
    from app.services.max.drawing_intent import is_drawing_intent
    for phrase in [
        "redraw the Willard bench",
        "regenerate as 4-view",
        "redo with the new dims",
        "new version of the bench",
        "same version of the panel",
        "draw the Willard again with seat height 17",
    ]:
        assert is_drawing_intent(phrase), (
            f"Phase A Fix #2: founder re-ask phrase {phrase!r} did NOT trigger "
            f"drawing-router. Add to DRAWING_KEYWORDS."
        )


# ───────────────────────────────────────────────────────────────────
# Phase A — Diff 3: pending drawing-job lifecycle
# ───────────────────────────────────────────────────────────────────

def _use_test_db(monkeypatch):
    """Redirect the pending jobs module to a tmp DB so we don't pollute
    the live empire.db. Returns the path."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("EMPIRE_TASK_DB", tmp.name)
    # Force module reload so DB_PATH is recomputed.
    import importlib
    if "app.services.max.drawing_pending" in sys.modules:
        importlib.reload(sys.modules["app.services.max.drawing_pending"])
    return tmp.name


def test_pending_job_lifecycle(monkeypatch):
    """Phase A Fix #2: persist pending drawing-job across chat turns.

    create → get → is_continuation_reply (synonym match) → merge
    (synonym-aware extraction) → clear → get returns None.
    """
    _use_test_db(monkeypatch)
    from app.services.max import drawing_pending
    drawing_pending.set_pending("conv-1", "web", {
        "dimensions": {"width": None, "seat_height": None},
        "missing": ["width", "seat_height"],
        "required_keys": ["width", "seat_height"],
        "name": "Bench",
    })
    snap = drawing_pending.get_pending("conv-1", "web")
    assert snap is not None
    assert snap["missing"] == ["width", "seat_height"]
    # Founder reply with synonyms ("wide" → width, "seat height" → seat_height).
    merged = drawing_pending.merge_founder_reply(
        snap, "make the bench 87 wide, seat height 17"
    )
    assert merged["dimensions"]["width"] == "87"
    assert merged["dimensions"]["seat_height"] == "17"
    assert merged["missing"] == []  # both required now present
    # Clear the job (job resolved).
    drawing_pending.clear_pending("conv-1", "web")
    assert drawing_pending.get_pending("conv-1", "web") is None


def test_pending_job_24h_ttl_expiry(monkeypatch):
    """Phase A Fix #2: TTL expiry — pending jobs older than 24h are swept
    on the next ensure_table() call so an abandoned job cannot hijack an
    unrelated founder message days later.
    """
    db_path = _use_test_db(monkeypatch)
    # Bootstrap table.
    from app.services.max.drawing_pending import ensure_table
    ensure_table()
    # Insert a row with created_at 25h ago.
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO pending_drawing_jobs "
        "(conversation_id, channel, handoff_json, missing_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "conv-old", "web",
            '{"dimensions":{},"missing":["x"]}',
            '["x"]',
            "2020-01-01T00:00:00",
            "2020-01-01T00:00:00",
        ),
    )
    conn.commit()
    conn.close()
    # Force-sweep.
    ensure_table()
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM pending_drawing_jobs").fetchone()[0]
    conn.close()
    assert n == 0, "Phase A violation: 25h-old pending job was NOT swept by ensure_table()"


def test_pending_job_cancel_keywords(monkeypatch):
    """Phase A Fix #2: founder cancel keywords must drop the pending job."""
    _use_test_db(monkeypatch)
    from app.services.max.drawing_pending import (
        is_cancel_message, set_pending, get_pending, clear_pending,
    )
    set_pending("c", "web", {"missing": ["x"]})
    # Cancel keywords
    for phrase in ["cancel the drawing", "nevermind", "stop drawing", "abort", "discard"]:
        assert is_cancel_message(phrase), f"cancel keyword {phrase!r} not detected"
        clear_pending("c", "web")
    # NOT cancel
    for phrase in ["continue", "draw more", "make taller", "send me the PDF"]:
        assert not is_cancel_message(phrase), (
            f"non-cancel phrase {phrase!r} was falsely flagged as cancel"
        )


def test_pending_job_continuation_match_scoped():
    """Phase A Fix #2: scoped resume-match — only treat a reply as a
    continuation if it contains a dim-keyword OR mentions one of the
    missing keys explicitly. Plain text should NOT match.
    """
    from app.services.max.drawing_pending import is_continuation_reply
    # Match: contains dim-keyword
    assert is_continuation_reply("make it 87 wide", ["width"])
    assert is_continuation_reply("seat height 17", ["seat_height"])
    # Match: mentions missing key directly
    assert is_continuation_reply("width=87", ["width"])
    assert is_continuation_reply("seat height: 17", ["seat_height"])
    # NO match: empty
    assert not is_continuation_reply("", ["width"])
    assert not is_continuation_reply(None, ["width"])
    # NO match: random text
    assert not is_continuation_reply("ok thanks", ["width"])
    assert not is_continuation_reply("have a nice day", ["width"])


# ───────────────────────────────────────────────────────────────────
# Phase A — Diff 4: theater detector is WARNING-only (never blocking)
# ───────────────────────────────────────────────────────────────────

def test_theater_detector_warning_only():
    """Phase A Fix #3: chat model emitted {"tool":"db_query",...} JSON as
    prose when no matching tool was actually executed. The detector must
    flag this as a WARNING (visible + logged) but NEVER as a fail.

    Regex scope: covers ONLY {"tool": ...} shape. Code fences and
    function-call text are explicitly future work (NOT Phase A).
    """
    from app.services.max.theater_detector import detect_fabricated_tool_text
    text = 'I queried the db: {"tool": "db_query", "table": "leads"}'
    # Fabrication detected
    warning = detect_fabricated_tool_text(text, executed_tool_names=[])
    assert warning is not None
    assert warning.startswith("WARNING (Sprint 1d Phase A theater-detector)")
    assert "'db_query'" in warning
    # Same text but db_query was actually executed → no warning
    assert detect_fabricated_tool_text(text, executed_tool_names=["db_query"]) is None
    # Plain text → no fabrication
    assert detect_fabricated_tool_text("Here is the answer.", []) is None
    # Empty / None → no crash
    assert detect_fabricated_tool_text("", []) is None
    assert detect_fabricated_tool_text(None, []) is None
    # Multiple fabrications deduped and joined
    multi = '{"tool":"db_query"} and {"tool":"send_email"} and {"tool":"db_query"}'
    warning2 = detect_fabricated_tool_text(multi, [])
    assert warning2 is not None
    assert "'db_query'" in warning2 and "'send_email'" in warning2
    # Regex scope is EXPLICITLY limited to {"tool": ...} shape. Code
    # fences and function-call text are EXPLICITLY future work (NOT
    # Phase A — documented in code + README). We do NOT assert
    # anything about them here.


# ───────────────────────────────────────────────────────────────────
# Phase A — Diff 2: clear_handoff_state is a safe no-op per turn
# ───────────────────────────────────────────────────────────────────

def test_clear_handoff_state_per_turn():
    """Phase A Fix #3: clear_handoff_state is called by chat_with_max at
    the start of every turn. It must be idempotent and never raise."""
    from app.services.max.drawing_intent import clear_handoff_state
    for _ in range(5):
        clear_handoff_state()  # safe no-op
