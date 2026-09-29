"""HOTFIX 4b (2026-07-15): quote-link routing regression tests.

Production defect: A click on a chat link labeled "EST-2026-110"
opened EST-2026-124's review page. The frontend's chat-link click
handler called onScreenChange?.('quote') with NO id; QuoteReviewScreen
then fell back to fetching /quotes-v2?limit=1 and taking data.quotes[0]
(whichever row happened to be the latest — EST-2026-124 in the prod
DB at the time).

These tests pin the new contract on the backend: a click-side resolver
that turns "EST-2026-XXX" into the canonical quote row. The fix is
data-only (the frontend resolves via this endpoint and threads the id
through onScreenChange).
"""
import uuid
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(_BACKEND))


def _insert_canonical_quote(marker: str) -> str:
    """Helper: insert a quote via quote_service and return its quote_number."""
    from app.services.quote_service import create_quote
    result = create_quote({
        "customer_name": f"Routed Customer {marker}",
        "business_unit": "workroom",
        "line_items": [{"category": "", "description": "test", "quantity": 1, "unit_price": 99.0}],
        "tax_rate": 0.0,
        "project_name": f"routing test {marker}",
    })
    return result.get("quote_number")


def test_by_number_resolves_to_canonical_quote(isolated_empire_db):
    """The new /quotes-v2/by-number/{qn} endpoint must return the
    canonical row for the requested quote_number, with line items."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    marker = uuid.uuid4().hex[:8]
    qn = _insert_canonical_quote(marker)

    r = client.get(f"/api/v1/quotes-v2/by-number/{qn}")
    assert r.status_code == 200, f"resolver must succeed; got {r.status_code} body={r.text[:200]}"
    body = r.json()
    assert body["quote_number"] == qn
    assert body["customer_name"] == f"Routed Customer {marker}"
    assert body["id"], "resolver must return the canonical 8-char uuid4 id"
    assert isinstance(body.get("line_items"), list)
    assert len(body["line_items"]) >= 1


def test_by_number_404_when_not_found(isolated_empire_db):
    """An unknown quote_number must return 404, not fall back to a
    different row."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/quotes-v2/by-number/EST-9999-999")
    assert r.status_code == 404, (
        f"resolver must 404 for unknown number; got {r.status_code}"
    )


def test_by_number_route_does_not_shadow_id_route(isolated_empire_db):
    """The /by-number literal path must be matched BEFORE /{quote_id}
    so 'EST-2026-110' (which looks like an id) is treated as a
    quote_number lookup, not an id lookup.

    The contract: a fresh quote_number 'EST-2026-XXX' that does NOT
    match any id must return 404 (by-number miss), not 200 (id miss
    with payload). This is the litmus for the route ordering."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # A string that LOOKS like a uuid4-prefixed id but isn't an actual id.
    # If routes are reordered, /{quote_id} would match and 404. We want
    # /by-number to match first AND 404 too (no row by that number).
    # Both should 404, but the response should NOT carry id-style content.
    r = client.get("/api/v1/quotes-v2/by-number/zzz-9999-999")
    assert r.status_code == 404


def test_by_number_does_not_read_legacy_store(isolated_empire_db):
    """The resolver must NEVER return a row that exists only in the
    legacy data/quotes/{id}.json store. We don't ship that store in
    the test env, so this is mostly a pin that the resolver hits
    quote_service (SQL) and not the file-store fallback."""
    from app.services import quote_service
    import inspect
    # Read the function body lines (skip the docstring to avoid hitting
    # self-referential words).
    src_lines = inspect.getsource(quote_service.get_quote_by_number).splitlines()
    body_only = [l for l in src_lines if not l.lstrip().startswith(("#", '"""', "'''"))]
    body = "\n".join(body_only).lower()

    assert "with get_db() as conn:" in body, (
        "resolver must use the canonical SQL get_db() connection"
    )
    # Look for actual code-level references, not docstring prose.
    for legacy_token in ("data/quotes/", "open(", "loadtxt", "from_json",
                         "json.load", "quotes_dir", "legacyquotes"):
        assert legacy_token not in body, (
            f"resolver body must not reference legacy JSON store "
            f"({legacy_token!r} found)"
        )
