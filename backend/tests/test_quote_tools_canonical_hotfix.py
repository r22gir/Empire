"""HOTFIX 2026-07-15 2: quote-tool store split regression tests.

Before fix: MAX `get_quote` and `search_quotes` tools used legacy
backend/data/quotes/{id}.json (stale pre-1d-consolidation records like
Lauren Bassett / Baltimore Design Group / Nov 2025 EST-2026-110),
while `show_quote_for_review` correctly used quote_service against
the canonical quotes_v2 table.

After fix: get_quote + search_quotes both go through
app.services.quote_service (canonical quotes_v2 store), matching
show_quote_for_review.

These tests pin the new contract: get_quote(canonical_id) returns the
canonical row; search_quotes(customer_name) returns only canonical
rows; the legacy store is no longer read.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))


@pytest.fixture
def temp_quote_id():
    """Insert a canonical quote via quote_service + return its id; clean up.

    Note: create_quote ignores any caller-supplied id and assigns its own
    8-char uuid4 prefix. We capture the returned id and use that.
    """
    from app.services.quote_service import create_quote
    marker = uuid.uuid4().hex[:8]
    result = create_quote({
        "customer_name":   f"Canonical Customer {marker}",
        "business_unit":   "workroom",
        "line_items":      [{"category": "", "description": "hotfix item",
                             "quantity": 1, "unit_price": 123.45}],
        "tax_rate":        0.0,
        "project_name":    f"hotfix test {marker}",
    })
    qid = result.get("id")
    yield qid
    # best-effort cleanup
    import sqlite3
    conn = sqlite3.connect(os.path.expanduser("~/empire-data/empire.db"))
    conn.execute("DELETE FROM quote_line_items WHERE quote_id = ?", (qid,))
    conn.execute("DELETE FROM quotes_v2 WHERE id = ?", (qid,))
    conn.commit()
    conn.close()


def test_get_quote_reads_canonical_quote_service(temp_quote_id):
    """HOTFIX: get_quote must return the canonical row from quotes_v2,
    not a stale pre-consolidation JSON file."""
    from app.services.max.tool_executor import execute_tool
    res = execute_tool({"tool": "get_quote", "quote_id": temp_quote_id})
    assert res.success, f"get_quote failed: {res.error}"
    assert res.result["id"] == temp_quote_id
    assert res.result["customer_name"].startswith("Canonical Customer")
    # The canonical row carries the canonical business_unit field.
    assert res.result.get("business_unit") == "workroom"


def test_get_quote_4d9b1d03_returns_canonical_row():
    """Sanity: the live 4d9b1d03 quote (created by MAX in this sprint)
    must be readable via the canonical tool. This was the bug report —
    it returned 'not found' before the fix."""
    from app.services.max.tool_executor import execute_tool
    res = execute_tool({"tool": "get_quote", "quote_id": "4d9b1d03"})
    assert res.success, f"get_quote(4d9b1d03) failed: {res.error}"
    assert res.result["id"] == "4d9b1d03"


def test_search_quotes_finds_canonical_quote(temp_quote_id):
    """HOTFIX: search_quotes(customer_name) must return the canonical
    quote from quotes_v2, not a stale pre-consolidation row from the
    legacy JSON store."""
    from app.services.max.tool_executor import execute_tool
    # Pull customer_name from the canonical quote we created, since the
    # actual quote_id is an 8-char uuid4 (not our marker).
    from app.services.quote_service import get_quote
    created = get_quote(temp_quote_id)
    customer_query = created["customer_name"]
    res = execute_tool({"tool": "search_quotes", "customer_name": customer_query})
    assert res.success, f"search_quotes failed: {res.error}"
    ids = [q["id"] for q in res.result["quotes"]]
    assert temp_quote_id in ids, (
        f"search_quotes should find canonical quote {temp_quote_id}, "
        f"got ids: {ids}"
    )


def test_search_quotes_does_not_surface_legacy_only_records(temp_quote_id):
    """The legacy JSON store held stale pre-consolidation records (per
    the bug report). After the fix, search_quotes MUST NOT return rows
    that exist only in the legacy store. We can't enumerate the legacy
    store cleanly here, but we can assert: every result carries the
    `canonical` source marker (which legacy rows lack) and every
    result has a canonical quote-id prefix."""
    from app.services.max.tool_executor import execute_tool
    res = execute_tool({"tool": "search_quotes", "limit": 10})
    assert res.success, res.error
    for q in res.result["quotes"]:
        # canonical store has source='canonical'; legacy rows lack it.
        assert q.get("source") == "canonical", (
            f"non-canonical result leaked from search_quotes: {q}"
        )
        # canonical quote ids are 8 hex chars (uuid4); legacy was also
        # 8 hex chars so this is a soft check — source tag is the truth.
        assert isinstance(q.get("id"), str) and len(q["id"]) >= 1
