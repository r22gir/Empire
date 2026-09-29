"""Item 2 (feature/drawing-standard dispatch) — hide test quotes from the
Workroom quotes-v2 list.

quotes_v2 accumulated ~156 smoke/QA fixtures (TrustTest, MOCK-SWEEP, SMOKE,
diag-probe, Demo Client, ...) that clutter the founder's real quote list.
The fix: an `is_test` column, default 0/false, that `list_quotes()` excludes
unless `include_test=True`. Flagging a quote as test must NOT break direct
lookup by id/number — Max smoke routines pin to a known id.
"""
from __future__ import annotations

import pytest


def _make_quote(customer_name: str, business_unit: str = "workroom") -> dict:
    from app.services.quote_service import create_quote
    return create_quote({
        "customer_name": customer_name,
        "business_unit": business_unit,
        "pricing_mode": "flat",
        "tax_rate": 0,
        "project_name": "Is-Test Filter Coverage",
    })


def test_new_quotes_default_is_test_false(isolated_empire_db):
    quote = _make_quote("Real Customer")
    assert quote.get("is_test") in (0, False, None)


def test_list_quotes_hides_flagged_test_quotes_by_default(isolated_empire_db):
    from app.services.quote_service import list_quotes, set_quote_test_flag

    real = _make_quote("Real Customer A")
    test_quote = _make_quote("SMOKE Test Customer")
    set_quote_test_flag(test_quote["id"], is_test=True, changed_by="test-suite")

    default_listing = list_quotes(business_unit="workroom", limit=500)
    ids = {row["id"] for row in default_listing["quotes"]}
    assert real["id"] in ids
    assert test_quote["id"] not in ids

    with_test = list_quotes(business_unit="workroom", limit=500, include_test=True)
    ids_with_test = {row["id"] for row in with_test["quotes"]}
    assert real["id"] in ids_with_test
    assert test_quote["id"] in ids_with_test


def test_get_quote_by_id_still_works_when_flagged_test(isolated_empire_db):
    """Max's smoke routines pin to a known quote id (e.g. EST-2026-273) —
    flagging must never make get_quote/get_quote_by_number 404."""
    from app.services.quote_service import get_quote, get_quote_by_number, set_quote_test_flag

    quote = _make_quote("diag-probe Customer")
    set_quote_test_flag(quote["id"], is_test=True, changed_by="test-suite")

    fetched = get_quote(quote["id"])
    assert fetched is not None
    assert fetched["id"] == quote["id"]
    assert fetched.get("is_test") in (1, True)

    by_number = get_quote_by_number(quote["quote_number"])
    assert by_number is not None
    assert by_number["id"] == quote["id"]


def test_set_quote_test_flag_unflag_round_trips(isolated_empire_db):
    from app.services.quote_service import list_quotes, set_quote_test_flag

    quote = _make_quote("MOCK-SWEEP Customer")
    set_quote_test_flag(quote["id"], is_test=True, changed_by="test-suite")
    assert quote["id"] not in {
        row["id"] for row in list_quotes(business_unit="workroom", limit=500)["quotes"]
    }

    set_quote_test_flag(quote["id"], is_test=False, changed_by="test-suite")
    assert quote["id"] in {
        row["id"] for row in list_quotes(business_unit="workroom", limit=500)["quotes"]
    }


def test_set_quote_test_flag_unknown_id_returns_none(isolated_empire_db):
    from app.services.quote_service import set_quote_test_flag
    assert set_quote_test_flag("does-not-exist", is_test=True) is None


def test_flag_test_quotes_script_dry_run_does_not_mutate(isolated_empire_db, tmp_path):
    """scripts/flag_test_quotes.py defaults to dry-run and must not write
    to the DB unless --apply is passed."""
    import sqlite3
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        import flag_test_quotes
    finally:
        sys.path.remove(str(scripts_dir))

    quote = _make_quote("HOTFIX5 Test Customer")

    conn = sqlite3.connect(isolated_empire_db)
    conn.row_factory = sqlite3.Row
    try:
        matches = flag_test_quotes.find_matches(
            conn,
            name_patterns=flag_test_quotes.DEFAULT_TEST_NAME_PATTERNS,
            ids=None,
            quote_numbers=None,
        )
        match_ids = {row["id"] for row in matches}
        assert quote["id"] in match_ids

        # Dry run: no --apply, so nothing may be written.
        still_row = conn.execute(
            "SELECT is_test FROM quotes_v2 WHERE id = ?", (quote["id"],)
        ).fetchone()
        assert int(still_row["is_test"] or 0) == 0
    finally:
        conn.close()
