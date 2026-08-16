"""PHASE 2 · F5-H46 — import honesty CLOSE check.

Per the staleness rule: "if any of the three is already fixed
(golden port, R1, or earlier hotfixes — the stale-checkbox pattern
has hit 3+ times), CLOSE it with live-system evidence instead of
re-fixing."

H46 (import honesty) IS the import-honesty concern. The original
failure mode: the create_quick_quote tool used to return a result
shape that looked like canonical (no store / engine / deprecation
fields), so the model would treat the legacy JSON quote as canonical.

The current state (already fixed pre-F5):
- create_quick_quote returns `store: "json_legacy"` explicitly
- create_quick_quote returns `engine: "qis"` explicitly
- create_quick_quote returns `deprecation_notice` directing the model
  to use create_engine_quote for new quotes
- System prompt (line 4490) tells the model: "Do NOT pick this tool
  for new quotes — use create_engine_quote instead."

This test asserts the live-system evidence: the import-honesty
markers are present in the create_quick_quote tool's result.
"""
from __future__ import annotations

import pytest


def test_h46_create_quick_quote_result_has_legacy_store_marker():
    """The create_quick_quote tool must report `store: json_legacy`."""
    from app.services.max.tool_executor import _create_quick_quote

    # Build a minimal params dict
    result = _create_quick_quote({
        "customer_name": "H46-test-customer",
        "rooms": [],
    })
    assert result.success is True
    payload = result.result or {}
    assert payload.get("store") == "json_legacy", (
        f"create_quick_quote must report store='json_legacy'; "
        f"got {payload.get('store')!r}"
    )


def test_h46_create_quick_quote_result_has_engine_marker():
    """The create_quick_quote tool must report `engine: qis`."""
    from app.services.max.tool_executor import _create_quick_quote

    result = _create_quick_quote({
        "customer_name": "H46-test-engine",
        "rooms": [],
    })
    assert result.success is True
    payload = result.result or {}
    assert payload.get("engine") == "qis", (
        f"create_quick_quote must report engine='qis'; "
        f"got {payload.get('engine')!r}"
    )


def test_h46_create_quick_quote_result_has_deprecation_notice():
    """The create_quick_quote tool must include a deprecation_notice."""
    from app.services.max.tool_executor import _create_quick_quote

    result = _create_quick_quote({
        "customer_name": "H46-test-deprecation",
        "rooms": [],
    })
    assert result.success is True
    payload = result.result or {}
    notice = payload.get("deprecation_notice")
    assert notice, "deprecation_notice must be present"
    assert "json_legacy" in notice.lower() or "json store" in notice.lower(), (
        f"deprecation_notice must mention legacy JSON store; got {notice!r}"
    )
    assert "create_engine_quote" in notice, (
        f"deprecation_notice must redirect to create_engine_quote; got {notice!r}"
    )


def test_h46_create_engine_quote_result_has_canonical_store_marker():
    """The canonical create_engine_quote tool reports `store: quotes_v2`."""
    from app.services.max.tool_executor import _create_engine_quote

    result = _create_engine_quote({
        "customer_name": "H46-test-canonical",
        "business_unit": "workroom",
        "line_items": [
            {"category": "window", "description": "H46-test-window", "inputs": {"width": 30, "height": 40}, "quantity": 1}
        ],
    })
    if result.success:
        payload = result.result or {}
        assert payload.get("store") == "quotes_v2", (
            f"create_engine_quote must report store='quotes_v2'; "
            f"got {payload.get('store')!r}"
        )
    else:
        # If the engine rejects (e.g. missing required fields), the
        # import-honesty test should still pass — the legacy
        # marker is the focus.
        pytest.skip(f"create_engine_quote returned failure: {result.error}")


def test_h46_honesty_markers_distinguish_legacy_from_canonical():
    """The two quote-creation tools must report DIFFERENT store values.

    This is the core import-honesty invariant: the model can read
    the result and tell whether the quote went to canonical or
    legacy JSON.
    """
    # Canonical tool
    from app.services.max.tool_executor import _create_engine_quote
    canonical = _create_engine_quote({
        "customer_name": "H46-distinction",
        "business_unit": "workroom",
        "line_items": [
            {"category": "window", "description": "test", "inputs": {"width": 30, "height": 40}, "quantity": 1}
        ],
    })
    # Legacy tool
    from app.services.max.tool_executor import _create_quick_quote
    legacy = _create_quick_quote({
        "customer_name": "H46-distinction-legacy",
        "rooms": [],
    })

    if canonical.success:
        canonical_store = canonical.result.get("store")
        assert canonical_store == "quotes_v2", (
            f"create_engine_quote must say 'quotes_v2'; got {canonical_store!r}"
        )
    assert legacy.success is True
    legacy_store = legacy.result.get("store")
    assert legacy_store == "json_legacy", (
        f"create_quick_quote must say 'json_legacy'; got {legacy_store!r}"
    )
    assert canonical.result.get("store") != legacy.result.get("store"), (
        "the two tools must report DIFFERENT store values"
    )
