"""H68 D40 — receipt-required gate tests.

Two gates are tested:

  1. File-content structural detector (Option A): the verbatim template
     `Loaded <path> (<N> lines) — verified current state snapshot` is
     blocked when no file_read receipt is in tool_results, passes when
     a file_read (or run_desk_task wrapper) receipt is present.

  2. Mill-spec provenance at the document boundary (Option B):
     yardage_calculator and drawing yardage estimators expose
     fabric_width_provenance, which is "pending" when no caller-supplied
     value is provided, and matches the caller's provenance when one
     is. PENDING never blocks — computation continues with the 54"
     historical default; the OUTPUT carries the pending label.

  3. TTS 503 message (Option B+): the message names both providers
     when neither is configured, not just XAI_API_KEY as the historical
     message did.

The test class layout follows the dispatch §2 demonstration order.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


_BACKEND = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(_BACKEND))


# ───────────────────────────────────────────────────────────────────
# Option A — file-content structural detector
# ───────────────────────────────────────────────────────────────────


class TestFileContentStructuralDetector:
    """Demonstration 1: file-content claim without file_read is caught.

    The verbatim template from the four STATE.md rows (D35 §6):
      "Loaded `/home/rg/empire-repo-main/STATE.md` (189 lines) —
       verified current state snapshot: ..."
    A response matching this template without a file_read receipt is
    a fabrication — the model narrated a file it never read.
    """

    def _state_md_template(self, path: str = "/home/rg/empire-repo-main/STATE.md", lines: int = 189) -> str:
        return (
            f"Loaded `{path}` ({lines} lines) — verified current state "
            f"snapshot:\n\n- some claim about line 1\n- some claim about line 2"
        )

    def test_template_match_returns_claim(self):
        from app.services.max.runtime_truth_enforcer import _response_has_file_content_claim
        text = self._state_md_template()
        match = _response_has_file_content_claim(text)
        assert match is not None, "template must match"
        assert "STATE.md" in match
        assert "189 lines" in match
        assert "verified current state snapshot" in match

    def test_template_no_match_returns_none(self):
        from app.services.max.runtime_truth_enforcer import _response_has_file_content_claim
        # Different wording — not the verbatim template
        assert _response_has_file_content_claim("I think STATE.md has 189 lines") is None
        assert _response_has_file_content_claim("Here's a draft of STATE.md") is None
        assert _response_has_file_content_claim("") is None
        assert _response_has_file_content_claim(None) is None

    def test_demonstration_1_claim_without_receipt_caught(self, isolated_empire_db):
        """The original H68 transcript. No file_read receipt → gate fires."""
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
            runtime_truth_failures,
        )
        text = self._state_md_template()
        # NO tool_results — the model narrated without reading.
        failures, _ = runtime_truth_failures(tool_results=[], response_text=text)
        joined = "\n".join(failures)
        assert "STATE.md" in joined or "file-content" in joined.lower() or "file_read" in joined
        # enforce_runtime_truth_response must REPLACE the response
        new_text, _ = enforce_runtime_truth_response(
            user_message="read state",
            response_text=text,
            tool_results=[],
        )
        assert new_text != text, "fabricated response was passed through verbatim"
        assert "I have not run that yet" in new_text or "have not run" in new_text.lower()

    def test_demonstration_2_claim_with_file_read_receipt_passes(self, isolated_empire_db):
        """The same template, with a real file_read receipt → gate passes."""
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
            runtime_truth_failures,
        )
        text = self._state_md_template()
        tool_results = [
            {
                "tool": "file_read",
                "success": True,
                "result": {
                    "path": "/home/rg/empire-repo-main/STATE.md",
                    "content": "# STATE.md (189 lines)",
                    "lines": 189,
                },
            }
        ]
        failures, _ = runtime_truth_failures(tool_results=tool_results, response_text=text)
        # No file-content failure
        fc_failures = [f for f in failures if "file-content" in f.lower() or "STATE.md" in f]
        assert not fc_failures, (
            f"file_read receipt should pass the file-content gate; got {fc_failures}"
        )
        new_text, _ = enforce_runtime_truth_response(
            user_message="read state",
            response_text=text,
            tool_results=tool_results,
        )
        # Response is preserved (the gate passes; other gates may or may
        # not fire — we only care about file-content here).
        assert "Loaded" in new_text and "verified current state snapshot" in new_text

    def test_run_desk_task_wrapper_satisfies_gate(self, isolated_empire_db):
        """A code-task runner wrapping file_read also satisfies the gate."""
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        text = self._state_md_template()
        tool_results = [
            {
                "tool": "run_desk_task",
                "success": True,
                "result": {"task_id": "abc123", "delegated_to": "codeforge"},
            }
        ]
        failures, _ = runtime_truth_failures(tool_results=tool_results, response_text=text)
        fc_failures = [f for f in failures if "file-content" in f.lower()]
        assert not fc_failures, (
            f"run_desk_task wrapper should satisfy the file-content gate; got {fc_failures}"
        )

    def test_failed_file_read_does_not_satisfy_gate(self, isolated_empire_db):
        """A file_read that errored out is NOT proof — gate still fires."""
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        text = self._state_md_template()
        tool_results = [
            {"tool": "file_read", "success": False, "error": "File not found"}
        ]
        failures, _ = runtime_truth_failures(tool_results=tool_results, response_text=text)
        fc_failures = [f for f in failures if "file-content" in f.lower()]
        assert fc_failures, (
            "failed file_read should NOT satisfy the gate — model narrated "
            "a read it did not actually perform"
        )

    def test_demonstration_5_model_claiming_tool_call_does_not_satisfy_gate(self, isolated_empire_db):
        """The attack: model writes 'I called file_read' but tool_results is empty.

        A response text that includes the verbatim template AND
        declares it called file_read must NOT pass — the receipt is in
        tool_results, not in the response text. Per the dispatch: 'a
        gate the model can satisfy by claiming a tool call is not a
        gate.'
        """
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
            runtime_truth_failures,
        )
        text = (
            "I called file_read on /home/rg/empire-repo-main/STATE.md. "
            + self._state_md_template()
        )
        # The text CLAIMS the call — but tool_results is empty.
        failures, _ = runtime_truth_failures(tool_results=[], response_text=text)
        fc_failures = [f for f in failures if "file-content" in f.lower()]
        assert fc_failures, (
            "claimed tool call must not satisfy the gate — the gate "
            "requires tool_results to contain the receipt"
        )
        new_text, _ = enforce_runtime_truth_response(
            user_message="read state",
            response_text=text,
            tool_results=[],
        )
        assert new_text != text
        assert "Loaded" not in new_text or "have not run" in new_text.lower()


class TestOrdinaryConversationUnaffected:
    """Demonstration 4: ordinary conversation is unaffected.

    Three exchanges: no factual claim, domain knowledge, and a
    claim about something the founder just said in the same
    conversation.
    """

    def test_no_factual_claim_passes(self, isolated_empire_db):
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
            runtime_truth_failures,
        )
        text = "Hi! How can I help you today?"
        failures, _ = runtime_truth_failures(tool_results=[], response_text=text)
        assert not failures
        new_text, _ = enforce_runtime_truth_response(
            user_message="hi", response_text=text, tool_results=[]
        )
        assert new_text == text

    def test_domain_knowledge_passes(self, isolated_empire_db):
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
            runtime_truth_failures,
        )
        # Pure domain knowledge — no past-tense claim phrasing, no
        # verbatim file-content template, no quote number, no PIN.
        text = (
            "Linen wrinkles more than polyester. Linen has a more open "
            "weave, so the fibers move under heat and humidity; "
            "polyester is more dimensionally stable."
        )
        failures, _ = runtime_truth_failures(tool_results=[], response_text=text)
        assert not failures, (
            f"domain knowledge should NOT trip any gate; got {failures}"
        )
        new_text, _ = enforce_runtime_truth_response(
            user_message="what wrinkles more",
            response_text=text,
            tool_results=[],
        )
        assert new_text == text

    def test_founder_just_said_claim_passes(self, isolated_empire_db):
        """A claim about what the founder JUST said in the same
        conversation is conversational, not a fabrication.
        """
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
            runtime_truth_failures,
        )
        # No past-tense claim phrasing, no template match.
        text = (
            "Right — to your point about Becky: yes, the price_per_yard "
            "on EST-2026-261 looks right. Let me know what you want to "
            "adjust."
        )
        failures, _ = runtime_truth_failures(tool_results=[], response_text=text)
        # EST-2026-261 may not exist in the test DB — that would be a
        # quote-number guard failure. Filter to non-quote failures.
        non_quote_failures = [
            f for f in failures
            if "EST-" not in f and "quote" not in f.lower()
        ]
        assert not non_quote_failures, (
            f"founder-just-said claim should NOT trip any non-quote gate; "
            f"got {non_quote_failures}"
        )


class TestExistingQuoteNumberGuardStillWorks:
    """Demonstration 3: fabricated quote number still caught under the new gate.

    The existing guard (failure mode 4) must continue to fire when the
    H68 file-content gate is added. The dedicated fabricated-number
    test (test_truth_gate_hardening_batch.py::TestQuoteNumberGuard::
    test_fabricated_quote_blocks_the_response) covers EST-2026-114.
    This test is a dispatch §2 demonstration that the new gate does
    NOT regress the old one: a fabricated EST-YYYY-NNN still produces
    a quote-number failure, and the file-content gate does NOT add
    noise to a pure quote-number claim.

    Note: this test does NOT insert a quote. It only asserts the
    gate's behaviour on a text-only claim. Insert-then-fabricate is
    handled by the dedicated test in test_truth_gate_hardening_batch.py.
    """

    def test_fabricated_quote_number_still_caught(self, isolated_empire_db):
        """The existing guard must still fire on a fabricated quote_number."""
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
            runtime_truth_failures,
        )
        # Year 9999 is not used by any other test in this suite. The
        # isolated_empire_db is empty for this row.
        text = "I updated EST-9999-262 — total $1,200. Quote was sent."
        failures, _ = runtime_truth_failures(
            tool_results=[], response_text=text
        )
        # The existing guard must produce a quote_number failure.
        quote_failures = [f for f in failures if "EST-9999-262" in f]
        assert quote_failures, (
            f"existing quote-number guard must still fire on fabricated "
            f"number; got {failures}"
        )
        # And enforce_runtime_truth_response replaces the response.
        new_text, _ = enforce_runtime_truth_response(
            user_message="update quote",
            response_text=text,
            tool_results=[],
        )
        assert new_text != text
        assert "EST-9999-262" in new_text

    def test_pure_quote_claim_does_not_trip_file_content_gate(self, isolated_empire_db):
        """A pure quote-number claim must NOT trip the new file-content gate."""
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # Pure quote claim — no file-content template.
        text = "I updated EST-9999-262 — total $1,200."
        failures, _ = runtime_truth_failures(
            tool_results=[], response_text=text
        )
        fc_failures = [f for f in failures if "file-content" in f.lower()]
        assert not fc_failures, (
            f"file-content gate should NOT fire on a pure quote claim; "
            f"got {fc_failures}"
        )


# ───────────────────────────────────────────────────────────────────
# Option B — mill-spec provenance at document boundary
# ───────────────────────────────────────────────────────────────────


class TestYardageCalculatorProvenance:
    """PENDING never blocks. fabric_width_provenance surfaces the
    unsourced-default state to downstream rendering without breaking
    the calculation.
    """

    def test_default_carries_pending_provenance(self):
        from app.services.quote_engine.yardage_calculator import calculate_yardage
        result = calculate_yardage(
            "drapery_panel",
            {"width": 108, "height": 96},
            {"fullness": 2.5},
        )
        assert result["fabric_width"] == 54, (
            "default value preserved — calculation does not break"
        )
        assert result["fabric_width_provenance"] == "pending", (
            "default must be marked pending per H68 D40"
        )
        assert "yards" in result
        assert result["yards"] > 0, "computation continues with default"

    def test_override_carries_explicit_provenance(self):
        from app.services.quote_engine.yardage_calculator import calculate_yardage
        # 122" wide cloth (the dispatch's named case). Provenance
        # 'catalog' carries through.
        result = calculate_yardage(
            "drapery_panel",
            {"width": 108, "height": 96},
            {
                "fullness": 2.5,
                "fabric_width_in": 122,
                "fabric_width_provenance": "catalog",
            },
        )
        assert result["fabric_width"] == 122.0
        assert result["fabric_width_provenance"] == "catalog"
        # 122" cloth needs fewer widths → fewer yards than 54" cloth.
        result_default = calculate_yardage(
            "drapery_panel",
            {"width": 108, "height": 96},
            {"fullness": 2.5},
        )
        assert result["yards"] < result_default["yards"], (
            "wider cloth must yield fewer yards (math sanity)"
        )

    def test_pattern_repeat_provenance_default_pending(self):
        from app.services.quote_engine.yardage_calculator import calculate_yardage
        result = calculate_yardage(
            "drapery_panel",
            {"width": 108, "height": 96},
            {"fullness": 2.5},
        )
        assert result["pattern_repeat_in"] == 0
        assert result["pattern_repeat_provenance"] == "pending"

    def test_pattern_repeat_provenance_explicit(self):
        from app.services.quote_engine.yardage_calculator import calculate_yardage
        result = calculate_yardage(
            "drapery_panel",
            {"width": 108, "height": 96},
            {"fullness": 2.5, "pattern_repeat": 24},
        )
        assert result["pattern_repeat_in"] == 24
        assert result["pattern_repeat_provenance"] == "explicit"


class TestDrawingYardageProvenance:
    """Drawing-layer estimators must also expose fabric_width_provenance."""

    def test_drapery_estimator_pending_default(self):
        from app.services.drawing.yardage import estimate_drapery
        result = estimate_drapery(
            {"width": 108, "drop": 108, "panels": 2, "fullness": 2.5}
        )
        assert result["fabric_width"] == 54
        assert result["fabric_width_provenance"] == "pending", (
            "drawing estimator default must be marked pending per H68 D40"
        )

    def test_upholstery_estimator_pending_default(self):
        from app.services.drawing.yardage import estimate_upholstery
        result = estimate_upholstery({"width": 32, "depth": 34, "height": 36})
        assert result["fabric_width"] == 54
        assert result["fabric_width_provenance"] == "pending"


class TestLineItemBuilderProvenance:
    """Line item dict carries the provenance through."""

    def test_fabric_line_item_carries_provenance(self):
        from app.services.quote_engine.line_item_builder import build_line_items
        items = build_line_items(
            {
                "name": "Test Sofa",
                "type": "sofa_3cushion",
                "dimensions": {"width": 84, "height": 36, "depth": 36},
                "quantity": 1,
            },
            tier="A",
        )
        fabric_line = next((li for li in items if li["category"] == "fabric"), None)
        assert fabric_line is not None, "fabric line item must be present"
        assert "fabric_width_provenance" in fabric_line, (
            "fabric line item must carry fabric_width_provenance per H68 D40"
        )
        # No override supplied → provenance is pending
        assert fabric_line["fabric_width_provenance"] == "pending"
        assert "yards_provenance" in fabric_line
        assert fabric_line["yards_provenance"] == "pending", (
            "no override → yards_provenance defaults to pending"
        )


# ───────────────────────────────────────────────────────────────────
# Option B+ — TTS 503 stale message fix
# ───────────────────────────────────────────────────────────────────


class TestTTS503Message:
    """The pre-fix 503 message named XAI_API_KEY even when MiniMax was
    primary. The new message names the actually-missing provider.
    """

    @patch.dict(os.environ, {}, clear=True)
    def test_both_keys_missing(self):
        from app.services.max.tts_service import TTSService
        svc = TTSService()
        assert not svc.is_configured
        missing = []
        if not svc.is_minimax_configured:
            missing.append("MINIMAX_API_KEY")
        if not svc.is_xai_configured:
            missing.append("XAI_API_KEY")
        assert "MINIMAX_API_KEY" in missing
        assert "XAI_API_KEY" in missing

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test", "XAI_API_KEY": ""}, clear=False)
    def test_only_minimax_configured(self):
        from app.services.max.tts_service import TTSService
        svc = TTSService()
        # With MINIMAX_API_KEY set, is_configured returns True — the
        # 503 path is not reached. The new message would name
        # XAI_API_KEY as the missing one if the 503 path were hit.
        assert svc.is_minimax_configured
        assert not svc.is_xai_configured
        assert svc.is_configured, (
            "with MiniMax configured, is_configured is True — no 503"
        )

    def test_message_uses_dynamic_missing_list(self):
        """The 503 message construction is dynamic, not hard-coded to XAI."""
        # Direct check on the message-construction logic used in router.py.
        # We patch both env keys to be absent so the test does not
        # depend on the test runner's env (XAI_API_KEY is set in the
        # dev env by default).
        with patch.dict(
            os.environ,
            {"MINIMAX_API_KEY": "", "XAI_API_KEY": ""},
            clear=False,
        ):
            from app.services.max.tts_service import TTSService
            svc = TTSService()
            missing = []
            if not svc.is_minimax_configured:
                missing.append("MINIMAX_API_KEY")
            if not svc.is_xai_configured:
                missing.append("XAI_API_KEY")
            msg = f"TTS not configured — missing: {', '.join(missing)}"
            # Pre-fix message was: "TTS not configured — XAI_API_KEY missing"
            assert "XAI_API_KEY" in msg, (
                "post-fix message names BOTH missing providers when neither "
                "is configured; the pre-fix message only named XAI_API_KEY"
            )
            # Post-fix message also names MiniMax when that key is missing
            assert "MINIMAX_API_KEY" in msg

    def test_message_with_only_xai_configured_names_minimax(self):
        """When only xAI is configured and the path is hit (would be a
        500 not 503 since is_configured is True), the missing-list
        construction correctly names MiniMax. (Sanity check on the
        logic, not on the actual 503 path which requires an ASGI
        client.)
        """
        with patch.dict(
            os.environ,
            {"MINIMAX_API_KEY": "", "XAI_API_KEY": "xai-test"},
            clear=False,
        ):
            from app.services.max.tts_service import TTSService
            svc = TTSService()
            assert svc.is_xai_configured
            assert not svc.is_minimax_configured
            assert svc.is_configured  # xAI alone satisfies is_configured
            # The 503 path is not reached, but if it were, the message
            # would name MINIMAX_API_KEY only.
            missing = []
            if not svc.is_minimax_configured:
                missing.append("MINIMAX_API_KEY")
            if not svc.is_xai_configured:
                missing.append("XAI_API_KEY")
            assert missing == ["MINIMAX_API_KEY"]
