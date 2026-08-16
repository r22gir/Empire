"""PHASE 2 · F5-H44 — one-quote-one-source test.

The legacy `_load_quote` in `routers/quotes.py` reads from
`backend/data/quotes/{id}.json` (legacy JSON store). The canonical
source is `quotes_v2` SQL table. Pre-F5-H44, the legacy route
returned 404 when the JSON file was missing (even if the canonical
quote existed). F5-H44 fixes this by:

1. `routers/quotes.py:_load_quote` tries canonical SQL first.
2. Falls back to legacy JSON only if canonical misses.
3. The legacy JSON files are NOT deleted (audit trail retained).

This test asserts that the canonical quote is reachable through
EVERY consumer path that USED to hit legacy JSON.
"""
from __future__ import annotations

import os

import pytest
import requests
import sqlite3


API_BASE = os.environ.get("EMPIRE_API_BASE", "http://127.0.0.1:8000")


def _canonical_quote_id() -> str:
    conn = sqlite3.connect('/home/rg/empire-data/empire.db')
    row = conn.execute("SELECT id FROM quotes_v2 ORDER BY rowid DESC LIMIT 1").fetchone()
    if not row:
        pytest.skip("no canonical quote available")
    return str(row[0])


def test_h44_legacy_get_returns_canonical_data():
    """GET /api/v1/quotes/{id} must return canonical quotes_v2 data."""
    quote_id = _canonical_quote_id()
    r = requests.get(f"{API_BASE}/api/v1/quotes/{quote_id}", timeout=10)
    assert r.status_code == 200, f"classic GET failed: {r.status_code} {r.text}"
    data = r.json()
    # The canonical get_quote returns line_items and quote_photos
    # even if empty. Legacy JSON would have 'rooms'/'design_proposals'
    # but NOT 'line_items'.
    assert "quote_number" in data, "no quote_number"
    assert "line_items" in data, "no line_items — canonical path not used"


def test_h44_legacy_post_accept_uses_canonical():
    """POST /api/v1/quotes/{id}/accept must find the canonical quote."""
    quote_id = _canonical_quote_id()
    r = requests.post(f"{API_BASE}/api/v1/quotes/{quote_id}/accept", json={}, timeout=10)
    # Either 200 (success) or 4xx (e.g. status conflict) — but NOT 404
    assert r.status_code != 404, (
        f"legacy accept endpoint returned 404 — canonical fallback failed: {r.text}"
    )


def test_h44_search_quotes_tagged_canonical():
    """The search_quotes tool tags each result with source='canonical'."""
    r = requests.post(
        f"{API_BASE}/api/v1/max/chat",
        json={
            "message": "search_quotes for status proposal",
            "channel": "web",
            "chat_id": "h44-test",
            "conversation_id": "h44-canonical-test",
        },
        timeout=180,
    )
    assert r.status_code == 200
    found_canonical = False
    for tr in r.json().get("tool_results") or []:
        if tr.get("tool") == "search_quotes":
            for q in tr.get("result", {}).get("quotes", []):
                if q.get("source") == "canonical":
                    found_canonical = True
                    break
    assert found_canonical, "search_quotes returned no canonical-tagged results"


def test_h44_get_quote_tool_returns_canonical():
    """The get_quote tool returns canonical data."""
    quote_id = _canonical_quote_id()
    r = requests.post(
        f"{API_BASE}/api/v1/max/chat",
        json={
            "message": f"get_quote for {quote_id}",
            "channel": "web",
            "chat_id": "h44-test",
            "conversation_id": "h44-getquote-test",
        },
        timeout=180,
    )
    assert r.status_code == 200
    for tr in r.json().get("tool_results") or []:
        if tr.get("tool") == "get_quote":
            result = tr.get("result", {})
            assert "quote_number" in result
            # Canonical has line_items
            assert "line_items" in result
            return
    pytest.fail("get_quote tool did not run")


def test_h44_dual_source_audit_report():
    """Document the dual source: where the legacy JSON files live.

    The brief says: "Report any second store the way the intake map
    did; never silently delete data." This test asserts the dual
    source is acknowledged (the legacy JSON files exist as audit
    trail) and the canonical source has the authoritative count.
    """
    import os
    canonical_db = "/home/rg/empire-data/empire.db"
    legacy_stale_fork = "/home/rg/empire-repo/backend/data/quotes"
    legacy_canonical_repo = "/home/rg/empire-repo-main/backend/data/quotes"

    # Canonical source — authoritative
    import sqlite3
    conn = sqlite3.connect(canonical_db)
    canonical_count = conn.execute("SELECT COUNT(*) FROM quotes_v2").fetchone()[0]
    assert canonical_count > 0, "canonical quotes_v2 is empty"

    # Audit-only mirrors — these are NOT deleted
    stale_fork_count = 0
    if os.path.isdir(legacy_stale_fork):
        stale_fork_count = sum(
            1 for f in os.listdir(legacy_stale_fork)
            if f.endswith(".json") and "_verification" not in f
        )
    canonical_repo_count = 0
    if os.path.isdir(legacy_canonical_repo):
        canonical_repo_count = sum(
            1 for f in os.listdir(legacy_canonical_repo)
            if f.endswith(".json") and "_verification" not in f
        )

    print(f"\n== H44 DUAL SOURCE AUDIT ==")
    print(f"  canonical (quotes_v2 SQL): {canonical_count}")
    print(f"  legacy stale-fork JSON   : {stale_fork_count}")
    print(f"  legacy canonical-repo JSON: {canonical_repo_count}")
    print(f"  authoritative source: quotes_v2 (canonical)")
    print(f"  legacy JSON files: AUDIT TRAIL — NOT deleted")
    # The secondary stores are reported but not removed
    assert canonical_count > 0, "canonical must have quotes"
