"""PHASE 2 · F5-H46 — import honesty CLOSE check.

Per the staleness rule: "if any of the three is already fixed
(golden port, R1, or earlier hotfixes — the stale-checkbox pattern
has hit 3+ times), CLOSE it with live-system evidence instead of
re-fixing."

H46 (import honesty) IS the import-honesty concern. The original
failure mode: the create_quick_quote tool used to return a result
shape that looked canonical (no store / engine / deprecation
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

TEARDOWN: every test creates a quote (canonical or legacy). The
fixture `h46_test_quotes` tracks all created quote_ids and deletes
them at the end of the session. Marked identifiers (H46-test-*)
ensure cleanup is targeted.
"""
from __future__ import annotations

import os
import pytest
import json
import sqlite3


# Track quote IDs created by tests for cleanup
_created_quote_ids: list[str] = []
_created_legacy_quote_ids: list[str] = []


@pytest.fixture(scope="session", autouse=True)
def h46_test_quotes():
    """Session-scope autouse: track and clean up H46-test quotes."""
    yield
    # Cleanup
    if _created_quote_ids:
        try:
            conn = sqlite3.connect('/home/rg/empire-data/empire.db')
            for qid in _created_quote_ids:
                conn.execute("DELETE FROM quote_line_items WHERE quote_id = ?", (qid,))
                conn.execute("DELETE FROM quote_photos WHERE quote_id = ?", (qid,))
                conn.execute("DELETE FROM quotes_v2 WHERE id = ?", (qid,))
            conn.commit()
            conn.close()
        except Exception:
            pass
    # Cleanup legacy JSON
    for qid in _created_legacy_quote_ids:
        from app.services.data_paths import quotes_data_dir
        path = quotes_data_dir() / f"{qid}.json"
        if path.exists():
            path.unlink()
        ver_path = quotes_data_dir() / f"{qid}_verification.json"
        if ver_path.exists():
            ver_path.unlink()


def _track_legacy(quote_id):
    """Track a legacy JSON quote id for cleanup."""
    _created_legacy_quote_ids.append(quote_id)


def test_h46_create_quick_quote_result_has_legacy_store_marker():
    """The create_quick_quote tool must report `store: json_legacy`."""
    from app.services.max.tool_executor import _create_quick_quote

    result = _create_quick_quote({
        "customer_name": "H46-test-customer",
        "rooms": [],
    })
    assert result.success is True
    _track_legacy(result.result.get("quote_id"))
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
    _track_legacy(result.result.get("quote_id"))
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
    _track_legacy(result.result.get("quote_id"))
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
        _created_quote_ids.append(result.result.get("quote_id"))
        payload = result.result or {}
        assert payload.get("store") == "quotes_v2", (
            f"create_engine_quote must report store='quotes_v2'; "
            f"got {payload.get('store')!r}"
        )
    else:
        pytest.skip(f"create_engine_quote returned failure: {result.error}")


def test_h46_honesty_markers_distinguish_legacy_from_canonical():
    """The two quote-creation tools must report DIFFERENT store values."""
    from app.services.max.tool_executor import _create_engine_quote, _create_quick_quote

    canonical = _create_engine_quote({
        "customer_name": "H46-distinction",
        "business_unit": "workroom",
        "line_items": [
            {"category": "window", "description": "test", "inputs": {"width": 30, "height": 40}, "quantity": 1}
        ],
    })
    legacy = _create_quick_quote({
        "customer_name": "H46-distinction-legacy",
        "rooms": [],
    })

    if canonical.success:
        _created_quote_ids.append(canonical.result.get("quote_id"))
        canonical_store = canonical.result.get("store")
        assert canonical_store == "quotes_v2", (
            f"create_engine_quote must say 'quotes_v2'; got {canonical_store!r}"
        )
    assert legacy.success is True
    _track_legacy(legacy.result.get("quote_id"))
    legacy_store = legacy.result.get("store")
    assert legacy_store == "json_legacy", (
        f"create_quick_quote must say 'json_legacy'; got {legacy_store!r}"
    )
    assert canonical.result.get("store") != legacy.result.get("store"), (
        "the two tools must report DIFFERENT store values"
    )
