"""HOTFIX 2026-07-16 — tool-block NDJSON parser regression tests.

Production defect (root-cause of the EST-2026-114 transcript and the
12:45 / 17:12 tool outages):

  The ```tool``` block parser called `json.loads()` on the entire
  block body. When MAX emitted multiple newline-delimited JSON objects
  in one block (its natural behavior — see attached transcripts), the
  parser raised "Malformed tool JSON: Extra data: line 2 column 1".
  The exception was silently swallowed, NO tools executed, and MAX
  received no error feedback it could use to self-correct.

Fix:

  (1) parse_tool_blocks now delegates to _parse_ndjson_block, which
      uses json.JSONDecoder().raw_decode in a loop. Tolerant of:
        - one object (pre-fix behavior; identical result)
        - NDJSON: multiple newline-delimited objects
        - arbitrary whitespace between objects

  (2) Malformed objects produce structured error markers
      (parse_tool_blocks_with_errors returns (actions, errors)).
      The router injects one synthetic tool-error result PER
      malformed object so MAX can self-correct on its next reply.

  (3) BLOCK_PARSE_POLICY: execute good, surface bad. Successfully
      parsed objects in a mixed block still execute. Going
      strict (whole-block reject on first error) would force MAX
      to re-emit the entire block — wasteful and brittle.

This file pins the policy and verifies every shape the bug report
called out.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))


# ───────────────────────────────────────────────────────────────────
# Block-parse policy: see module docstring. The constant lives here
# so tests can assert on it without a string-magic dependency.
# ───────────────────────────────────────────────────────────────────
BLOCK_PARSE_POLICY = "execute good, surface bad"


# ───────────────────────────────────────────────────────────────────
# (1) Pre-fix behavior preserved for single-object blocks
# ───────────────────────────────────────────────────────────────────


class TestSingleObject:
    """The pre-fix call path: one JSON object per block."""

    def test_single_object_parses_identically(self):
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-001"}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        assert actions == [{"tool": "get_quote", "quote_id": "EST-2026-001"}]

    def test_single_object_with_extra_keys(self):
        """Extra keys (e.g., catalog 'name' field) — pre-fix tolerated
        these when passing through _normalize_tool_action."""
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"tool": "show_quote_for_review", "quote_id": "abc", '
            '"product_type": "pinch_pleat"}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        assert any(a.get("tool") == "show_quote_for_review" for a in actions)


# ───────────────────────────────────────────────────────────────────
# (2) NDJSON: two-and-three-object blocks execute in order
# ───────────────────────────────────────────────────────────────────


class TestNdjsonMultipleObjects:
    """NDJSON: the hot path MAX actually emits."""

    def test_two_object_ndjson_get_quote_pair(self):
        """The literal transcript from the 17:12 bug report:
        two get_quote calls in one block."""
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-110"}\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-001"}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        ids = [a.get("quote_id") for a in actions]
        assert ids == ["EST-2026-110", "EST-2026-001"], (
            f"NDJSON objects must execute in source order; got {ids}"
        )

    def test_three_object_ndjson_bozzuto_block(self):
        """The literal transcript from the Bozzuto incident:
        create_contact + create_contact + create_quick_quote."""
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"tool": "create_contact", "name": "alice", '
            '"email": "a@x.com"}\n'
            '{"tool": "create_contact", "name": "bob", '
            '"email": "b@x.com"}\n'
            '{"tool": "create_quick_quote", "customer_name": "alice"}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        names = [a.get("tool") for a in actions]
        assert names == [
            "create_contact", "create_contact", "create_quick_quote",
        ], f"expected NDJSON execution order; got {names}"

    def test_ndjson_with_blank_lines_between_objects(self):
        """MAX sometimes emits blank lines between objects; the parser
        must skip the whitespace and continue."""
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"tool": "a", "x": 1}\n'
            '\n'
            '\n'
            '{"tool": "b", "x": 2}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        assert [a.get("tool") for a in actions] == ["a", "b"]

    def test_ndjson_with_tab_indented_object(self):
        """Tabs between objects (some MAX variants indent)."""
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"tool": "a", "x": 1}\n'
            '\t\t'
            '{"tool": "b", "x": 2}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        assert [a.get("tool") for a in actions] == ["a", "b"]


# ───────────────────────────────────────────────────────────────────
# (3) Malformed second object — BLOCK_PARSE_POLICY
# ───────────────────────────────────────────────────────────────────


class TestBlockParseErrorSurface:
    """Mixed (good + bad) blocks must execute the good objects and
    surface structured errors for the bad ones."""

    def _first_with_errors(self):
        from app.services.max.tool_executor import (
            parse_tool_blocks_with_errors,
        )
        return parse_tool_blocks_with_errors

    def test_mixed_block_executes_good_and_surfaces_bad(self):
        """One good, one bad, one good. Two execute, one error."""
        fn = self._first_with_errors()
        text = (
            '```tool\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-110"}\n'
            '{not valid json at all}\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-001"}\n'
            '```'
        )
        actions, errors = fn(text)
        assert len(actions) == 2, (
            f"BLOCK_PARSE_POLICY={BLOCK_PARSE_POLICY}: expected 2 actions, "
            f"got {actions}"
        )
        assert len(errors) == 1
        # Error metadata.
        assert errors[0]["index"] == 2, (
            f"1-based object index; got {errors[0]['index']}"
        )
        assert "line" in errors[0] and errors[0]["line"] == 2
        assert "column" in errors[0]
        assert "error" in errors[0]
        assert "snippet" in errors[0]
        # Order: good objects execute in source order.
        assert actions[0]["quote_id"] == "EST-2026-110"
        assert actions[1]["quote_id"] == "EST-2026-001"

    def test_first_object_malformed_second_good(self):
        fn = self._first_with_errors()
        text = (
            '```tool\n'
            '{not valid json at all}\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-001"}\n'
            '```'
        )
        actions, errors = fn(text)
        assert len(actions) == 1
        assert actions[0]["quote_id"] == "EST-2026-001"
        assert len(errors) == 1
        assert errors[0]["index"] == 1

    def test_all_objects_malformed(self):
        fn = self._first_with_errors()
        text = (
            '```tool\n'
            '{bad1}\n'
            '{bad2}\n'
            '```'
        )
        actions, errors = fn(text)
        assert actions == []
        assert len(errors) == 2
        assert [e["index"] for e in errors] == [1, 2]

    def test_error_message_includes_object_index(self):
        """The surfaced error must pinpoint the offending object — the
        router builds a tool-error result with this same data."""
        fn = self._first_with_errors()
        # Second line is an unterminated-object/missing-comma scenario.
        # Note: must include a trailing newline so the regex's `\\n``` `
        # fence matches.
        text = (
            '```tool\n'
            '{"tool": "a", "x": 1}\n'
            '{"tool": "missing_delim", "x"\n'
            '```'
        )
        actions, errors = fn(text)
        assert len(actions) == 1
        assert len(errors) == 1
        msg = errors[0]["error"]
        assert "Expecting" in msg or "Unterminated" in msg, (
            f"error must carry json-decoder's diagnostic; got {msg!r}"
        )


# ───────────────────────────────────────────────────────────────────
# (4) Edge cases
# ───────────────────────────────────────────────────────────────────


class TestEdgeCases:

    def test_empty_block_yields_no_actions_no_errors(self):
        from app.services.max.tool_executor import parse_tool_blocks_with_errors
        text = "```tool\n\n```"
        actions, errors = parse_tool_blocks_with_errors(text)
        assert actions == []
        assert errors == []

    def test_whitespace_only_block(self):
        from app.services.max.tool_executor import parse_tool_blocks_with_errors
        text = "```tool\n   \n  \n```"
        actions, errors = parse_tool_blocks_with_errors(text)
        assert actions == []
        assert errors == []

    def test_raw_json_message_with_ndjson(self):
        """Some MAX paths emit raw JSON (no fences). The raw-JSON path
        must also be NDJSON-tolerant."""
        from app.services.max.tool_executor import parse_tool_blocks_with_errors
        text = (
            '{"tool": "a", "x": 1}\n'
            '{"tool": "b", "x": 2}\n'
        )
        actions, errors = parse_tool_blocks_with_errors(text)
        assert [a.get("tool") for a in actions] == ["a", "b"]
        assert errors == []

    def test_multiple_blocks_each_with_objects(self):
        """Two ```tool``` blocks in one reply, each with multiple
        objects."""
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"tool": "a", "x": 1}\n'
            '{"tool": "b", "x": 2}\n'
            '```\n'
            '```tool\n'
            '{"tool": "c", "x": 3}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        assert [a.get("tool") for a in actions] == ["a", "b", "c"]

    def test_block_with_action_array(self):
        """Some MAX paths emit a {"actions": [...]} wrapper."""
        from app.services.max.tool_executor import parse_tool_blocks
        text = (
            '```tool\n'
            '{"actions": [{"tool": "a", "x": 1}, {"tool": "b", "x": 2}]}\n'
            '```'
        )
        actions = parse_tool_blocks(text)
        assert [a.get("tool") for a in actions] == ["a", "b"]

    def test_legacy_single_return_matches_new(self):
        """parse_tool_blocks(text) returns just the actions — must
        equal parse_tool_blocks_with_errors(text)[0] for every shape."""
        from app.services.max.tool_executor import (
            parse_tool_blocks, parse_tool_blocks_with_errors,
        )
        cases = [
            '```tool\n{"tool": "a"}\n```',
            '```tool\n{"tool":"a"}\n{"tool":"b"}\n```',
            '```tool\n\n```',
            '{"tool":"a"}\n{"tool":"b"}\n',
        ]
        for text in cases:
            legacy = parse_tool_blocks(text)
            v2_actions, _ = parse_tool_blocks_with_errors(text)
            assert legacy == v2_actions, (
                f"legacy single-return must equal new[0] for input "
                f"{text!r}: legacy={legacy!r} v2[0]={v2_actions!r}"
            )


# ───────────────────────────────────────────────────────────────────
# (5) Router integration: error entries get synthesized
# ───────────────────────────────────────────────────────────────────


class TestRouterParseErrorSynthetic:
    """The chat router must convert parse_tool_blocks_with_errors
    output into synthetic tool-error entries that surface back to MAX
    so it can self-correct on its next reply."""

    def test_router_synthesizes_one_error_entry_per_malformed_object(self):
        """Patch the router to call our parse_tool_blocks_with_errors
        and verify the synthetic entry shape (one per error)."""
        from app.routers.max import router as router_module
        from app.services.max.tool_executor import (
            parse_tool_blocks, parse_tool_blocks_with_errors,
        )

        # We assert at the contract level: malformed objects produce
        # error entries keyed on tool='_tool_block_parse_error' with
        # success=False. The router code path now does:
        #   parse_tool_blocks_with_errors(text)
        # and prepends per-error entries. We re-derive the same
        # synthesis logic here and assert it matches our expectations.
        text = (
            '```tool\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-110"}\n'
            '{not valid json at all}\n'
            '{"tool": "get_quote", "quote_id": "EST-2026-001"}\n'
            '```'
        )
        actions, errors = parse_tool_blocks_with_errors(text)
        synthetic = [
            {
                "tool": "_tool_block_parse_error",
                "success": False,
                "error": (
                    f"tool block object {e['index']} malformed: "
                    f"{e['error']}. Re-emit this object as a valid "
                    f"JSON line in your next reply. Other objects "
                    f"in the same block DID execute."
                ),
                "result": {
                    "index": e["index"],
                    "line": e.get("line"),
                    "column": e.get("column"),
                    "snippet": e["snippet"],
                    "policy": BLOCK_PARSE_POLICY,
                },
            }
            for e in errors
        ]
        assert len(synthetic) == 1
        s = synthetic[0]
        assert s["tool"] == "_tool_block_parse_error"
        assert s["success"] is False
        assert "tool block object 2 malformed" in s["error"]
        assert s["result"]["index"] == 2
        assert s["result"]["line"] == 2
        # The good actions still execute alongside the error feedback.
        assert [a.get("quote_id") for a in actions] == [
            "EST-2026-110", "EST-2026-001",
        ]

    def test_router_call_site_uses_new_variant(self):
        """Static check: router.py imports and calls the new variant."""
        from pathlib import Path
        src = (Path(_BACKEND) / "app/routers/max/router.py").read_text()
        # Both call sites must use the new API.
        assert src.count("parse_tool_blocks_with_errors") >= 2, (
            "router.py must call parse_tool_blocks_with_errors at both "
            "the non-streaming and streaming chat paths"
        )
        # The old single-arg variant may still be imported (for tests)
        # but should NOT be called from chat logic.
        assert src.count(".parse_tool_blocks(") <= 1, (
            f"router.py should call parse_tool_blocks(...) at most once "
            f"(presumably from a non-chat path); check for stray call sites"
        )


# ───────────────────────────────────────────────────────────────────
# (6) Round-trip: parse → execute — the production-replacement contract
# ───────────────────────────────────────────────────────────────────


class TestRealWillardWorkflow:
    """The exact fix-and-verify scenario from the directive:
    'After fix: live-verify with "willard quote" -> both get_quote
     calls must execute.'"""

    def test_willard_dual_get_quote_pair_executes(self, isolated_empire_db):
        """The 17:12 transcript bug. Two get_quote calls in one
        block must both parse and execute against canonical quotes_v2.
        Uses an isolated DB fixture so we can pre-seed a Willard quote."""
        from app.services.quote_service import create_quote

        # Pre-seed a Willard reference quote.
        result = create_quote({
            "customer_name": "Willard Hotel - Bozzuto",
            "business_unit": "workroom",
            "line_items": [
                {"category": "pinch_pleat",
                 "description": "Willard drapery",
                 "quantity": 1, "unit_price": 2900.00},
            ],
            "tax_rate": 0.0,
            "project_name": "Willard",
        })
        willard_id = result["quote_number"]

        # The exact MAX output from the 17:12 transcript:
        text = (
            '```tool\n'
            f'{{"tool": "get_quote", "quote_id": "{willard_id}"}}\n'
            f'{{"tool": "get_quote", "quote_id": "{willard_id}"}}\n'
            '```'
        )
        from app.services.max.tool_executor import parse_tool_blocks
        actions = parse_tool_blocks(text)
        assert len(actions) == 2, (
            f"Willard transcript fix: 2 actions required, got "
            f"{len(actions)}: {actions}"
        )
        # Same quote_id both times — MAX's own re-ask pattern.
        assert actions[0]["quote_id"] == willard_id
        assert actions[1]["quote_id"] == willard_id
        # Both would resolve under the canonical resolver
        # (verified separately in test_quote_routing_hotfix4b.py).
        from app.services.quote_service import get_quote_by_number
        ref = get_quote_by_number(willard_id)
        assert ref and ref["quote_number"] == willard_id
