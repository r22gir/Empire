"""Tests for the Customer Journey Review Queue.

The review-queue service is **read-only** by construction. The
proposals it returns are for founder review; the apply-approval
endpoint is RESERVED with live writes disabled.

Tests verify:
    - proposed quote→customer matches (with confidence scoring)
    - proposed invoice→quote matches
    - confidence scoring math
    - low-confidence matches are correctly marked
    - no live DB writes (the review-queue service is read-only)
    - no legacy tables touched
    - the apply-approval endpoint returns 'reserved' status
    - proposal IDs are stable (same input → same id)
    - normalization helpers behave as expected
    - end-to-end shape of the review queue endpoint
"""
import os
import re
import sys
import json
import sqlite3
import tempfile
import pytest

LIVE_VENV = "/home/rg/empire-repo/backend/venv/lib/python3.12/site-packages"
if LIVE_VENV not in sys.path:
    sys.path.insert(0, LIVE_VENV)

APP_ROOT = "/home/rg/empire-repo-main/backend"
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

LIVE_DB = "/home/rg/empire-repo/backend/data/empire.db"
if not os.path.exists(LIVE_DB):
    pytest.skip(f"Live empire.db not found at {LIVE_DB}", allow_module_level=True)

from app.services.max.journey_review_queue import (
    generate_review_queue,
    write_review_queue_snapshot,
    apply_approval_enabled,
    _norm_email,
    _norm_phone,
    _norm_name,
    _name_tokens,
    _jaccard,
    _date_diff_days,
    _amount_close,
    _score_quote_to_customer,
    _score_invoice_to_quote,
    _score_payment_to_invoice,
    _band,
    _proposal_id,
    REVIEW_QUEUE_PATH,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
    Proposal,
)
from app.services.max.journey_linkage import _open_db


# ── 1. Normalization helpers ───────────────────────────────────────────


def test_norm_email_lowercases_and_trims():
    assert _norm_email("  Foo@Bar.COM  ") == "foo@bar.com"
    assert _norm_email(None) == ""
    assert _norm_email("") == ""


def test_norm_phone_strips_formatting():
    assert _norm_phone("(703) 555-1234") == "7035551234"
    assert _norm_phone("703.555.1234") == "7035551234"
    assert _norm_phone(None) == ""
    assert _norm_phone("") == ""


def test_norm_name_collapses_whitespace_and_lowercases():
    assert _norm_name("  Maggie   O'Neil  ") == "maggie o'neil"
    assert _norm_name(None) == ""
    assert _norm_name("   ") == ""


def test_name_tokens_filters_short():
    assert _name_tokens("Bob A Smith") == {"bob", "smith"}
    # 'A' is too short (< 2 chars) — filtered out
    assert _name_tokens(None) == set()


def test_jaccard_basics():
    assert _jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5
    assert _jaccard(set(), set()) == 0.0
    assert _jaccard({"x"}, {"x"}) == 1.0


def test_date_diff_days():
    assert _date_diff_days("2026-01-01", "2026-01-08") == 7
    assert _date_diff_days("2026-01-08", "2026-01-01") == 7
    assert _date_diff_days("2026-01-01T10:00:00", "2026-01-08T05:00:00") == 7
    assert _date_diff_days(None, "2026-01-01") is None
    assert _date_diff_days("not-a-date", "2026-01-01") is None


def test_amount_close():
    assert _amount_close(100.0, 100.0, 0.01) is True
    assert _amount_close(100.0, 100.5, 0.01) is False  # 0.5% > 0.01%
    assert _amount_close(100.0, 100.5, 1.0) is True   # within 1%
    assert _amount_close(0, 0, 1.0) is True
    assert _amount_close(0, 100, 100) is False  # 0 amount is special-cased
    assert _amount_close(100, 0, 100) is False


# ── 2. Confidence scoring ──────────────────────────────────────────────


def test_band_thresholds():
    assert _band(THRESHOLD_HIGH) == "high"
    assert _band(THRESHOLD_HIGH + 1) == "high"
    assert _band(THRESHOLD_MEDIUM) == "medium"
    assert _band(THRESHOLD_MEDIUM + 1) == "medium"
    assert _band(THRESHOLD_MEDIUM - 1) == "low"
    assert _band(0) == "low"


def test_score_quote_to_customer_perfect_match():
    """Email + phone + name all match → score = 130, confidence = high."""
    q = {
        "customer_email": "ramiro@comcast.net",
        "customer_phone": "(301) 919-6580",
        "customer_name": "Ramiro Paez",
    }
    c = {
        "email": "ramiro@comcast.net",
        "phone": "3019196580",
        "name": "Ramiro Paez",
    }
    s, reasons, risks = _score_quote_to_customer(q, c)
    assert s == 130
    assert _band(s) == "high"
    assert any("email" in r for r in reasons)
    assert any("phone" in r for r in reasons)
    assert any("name exact match" in r for r in reasons)
    assert risks == []


def test_score_quote_to_customer_email_only():
    """Only email matches → score = 50, confidence = medium."""
    q = {"customer_email": "a@b.com", "customer_name": "Z", "customer_phone": "111"}
    c = {"email": "A@B.com", "name": "Different", "phone": "999"}
    s, _, _ = _score_quote_to_customer(q, c)
    assert s == 50
    assert _band(s) == "medium"


def test_score_quote_to_customer_no_match():
    q = {"customer_email": "x@y.com", "customer_name": "Bob", "customer_phone": "111"}
    c = {"email": "a@b.com", "name": "Alice", "phone": "999"}
    s, reasons, risks = _score_quote_to_customer(q, c)
    assert s == 0
    assert reasons == [] or all("match" not in r.lower() for r in reasons)
    # Should have risks for each mismatch
    assert any("email" in r for r in risks)
    assert any("name" in r.lower() or "phone" in r for r in risks)


def test_score_quote_to_customer_name_partial_overlap():
    """Names share some tokens but aren't exact → +10 (jaccard 0.5).

    Last-name anchor is the LAST WORD of each name, not a token
    from a set. The test data has 'paez' as middle in one name
    and last in the other, so the last-word check does NOT fire
    (q_last='smith', c_last='johnson'). That's a +0 for the anchor.
    """
    q = {"customer_name": "Ramiro Paez Smith", "customer_email": "", "customer_phone": ""}
    c = {"name": "ramiro paez johnson"}
    s, reasons, _ = _score_quote_to_customer(q, c)
    # Tokens: q={ramiro,paez,smith}, c={ramiro,paez,johnson}, jaccard=2/4=0.5
    # +10 (moderate overlap, 0.5). No last-name anchor.
    assert s == 10
    assert any("moderate overlap" in r for r in reasons)
    assert not any("last-name anchor" in r for r in reasons)


def test_score_quote_to_customer_phone_last7():
    """Phones match in the last 7 digits but not full → +20."""
    q = {"customer_phone": "+1 (800) 555-1234"}
    c = {"phone": "5551234"}  # 7 digits, matches the last 7 of the 11-digit phone
    s, reasons, _ = _score_quote_to_customer(q, c)
    assert s == 20
    assert any("last-7-digits" in r for r in reasons)


# ── 3. Invoice→quote scoring ─────────────────────────────────────────


def test_score_invoice_to_quote_email_and_amount_match():
    inv = {
        "client_email": "ramiro@comcast.net",
        "client_name": "Ramiro Paez",
        "total": 53275.75,
        "created_at": "2026-03-26",
    }
    q = {
        "customer_email": "ramiro@comcast.net",
        "customer_name": "Ramiro Paez",
        "total": 53275.75,
        "created_at": "2026-03-25",
    }
    s, reasons, risks = _score_invoice_to_quote(inv, q)
    # +50 email +30 name +20 amount+date = 100
    assert s == 100
    assert _band(s) == "high"
    assert any("email" in r for r in reasons)
    assert any("name" in r for r in reasons)
    assert any("amount" in r for r in reasons)
    assert risks == [] or all("mismatch" not in r for r in risks)


def test_score_invoice_to_quote_no_email_no_match():
    """No client_email on invoice, no client_name match → very low score."""
    inv = {
        "client_email": None,
        "client_name": "X",
        "total": 100.0,
        "created_at": "2026-04-01",
    }
    q = {
        "customer_email": "someone@else.com",
        "customer_name": "Y",
        "total": 999.0,
        "created_at": "2026-01-01",
    }
    s, _, _ = _score_invoice_to_quote(inv, q)
    assert s == 0


def test_score_invoice_to_quote_amount_only_within_window():
    """Amount match within 7 days → +20 (no email, no name)."""
    inv = {"client_email": "", "client_name": "", "total": 100.0, "created_at": "2026-03-15"}
    q = {"customer_email": "", "customer_name": "", "total": 100.0, "created_at": "2026-03-18"}
    s, reasons, _ = _score_invoice_to_quote(inv, q)
    assert s == 20
    assert any("amount match" in r for r in reasons)


# ── 4. Payment→invoice scoring ────────────────────────────────────────


def test_score_payment_to_invoice_amount_match():
    pay = {"amount": 100.0, "customer_id": "c-1", "payment_date": "2026-04-01"}
    inv = {"total": 100.0, "amount_paid": 0.0, "customer_id": "c-1", "created_at": "2026-03-25"}
    s, reasons, _ = _score_payment_to_invoice(pay, inv)
    # +50 amount match within 7d +10 customer_id = 60 (medium)
    assert s == 60
    assert _band(s) == "medium"


def test_score_payment_to_invoice_no_match():
    pay = {"amount": 1.0, "customer_id": "c-1", "payment_date": "2026-04-01"}
    inv = {"total": 9999.0, "amount_paid": 0.0, "customer_id": "c-9", "created_at": "2026-01-01"}
    s, _, risks = _score_payment_to_invoice(pay, inv)
    assert s == 0
    assert any("risk" in r.lower() or "mismatch" in r.lower() or "differs" in r for r in risks)


# ── 5. Stable proposal IDs ────────────────────────────────────────────


def test_proposal_id_stable():
    """Same (source, target, score) → same id across runs."""
    id1 = _proposal_id("quote", "q-1", "customer", "c-1", 130)
    id2 = _proposal_id("quote", "q-1", "customer", "c-1", 130)
    assert id1 == id2
    assert id1.startswith("p_")
    assert len(id1) == 2 + 16  # 'p_' + 16 hex chars


def test_proposal_id_differs_with_different_inputs():
    a = _proposal_id("quote", "q-1", "customer", "c-1", 130)
    b = _proposal_id("quote", "q-1", "customer", "c-2", 130)
    c = _proposal_id("quote", "q-2", "customer", "c-1", 130)
    d = _proposal_id("quote", "q-1", "customer", "c-1", 100)
    assert len({a, b, c, d}) == 4


# ── 6. Live integration: at least one high-confidence quote proposal ──


def test_live_review_queue_has_high_confidence_quote_proposals():
    """The live DB has 8 quotes with email-matching customers and 8 with
    phone-matching customers; the queue should find at least one
    high-confidence match (the Ramiro Paez / Kate Whittington cases
    that the scout analysis surfaced).
    """
    proposals = generate_review_queue()
    high_quote = [p for p in proposals
                  if p.confidence == "high" and p.source_type == "quote"]
    assert len(high_quote) >= 1, "expected at least one high-confidence quote proposal"
    # The top one should be a triple-match (email+phone+name)
    top = high_quote[0]
    assert top.confidence_score >= 70
    assert any("email" in r for r in top.match_reasons)
    assert any("phone" in r for r in top.match_reasons)


def test_live_review_queue_has_invoice_proposals():
    """The live DB has 14+ dangling invoices; at least some should have
    name-based proposals to real quotes.
    """
    proposals = generate_review_queue()
    inv = [p for p in proposals if p.source_type == "invoice"]
    assert len(inv) >= 1, "expected at least one invoice→quote proposal"


# ── 7. No live DB writes ───────────────────────────────────────────────


def test_review_queue_does_not_modify_live_db():
    """The review queue must be read-only."""
    size_before = os.path.getsize(LIVE_DB)
    mtime_before = os.path.getmtime(LIVE_DB)
    generate_review_queue()
    size_after = os.path.getsize(LIVE_DB)
    mtime_after = os.path.getmtime(LIVE_DB)
    assert size_before == size_after
    assert mtime_before == mtime_after


def test_review_queue_does_not_touch_legacy_tables():
    """The review queue reads customers, quotes_v2, invoices, payments
    only. Legacy tables (sf_customers, sf2_customers, assist_clients,
    payments_v2, cf_payments, invoice_payments) must be unchanged.
    """
    legacy_tables = ["sf_customers", "sf2_customers", "assist_clients",
                     "payments_v2", "cf_payments", "invoice_payments"]
    with _open_db() as conn:
        before = {}
        for t in legacy_tables:
            try:
                before[t] = conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            except sqlite3.OperationalError:
                before[t] = -1

    generate_review_queue()

    with _open_db() as conn:
        for t, n in before.items():
            if n < 0:
                continue
            after = conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            assert after == n, f"legacy table {t} changed: {n} -> {after}"


def test_apply_approval_disabled_by_default():
    """The apply path must be disabled unless the env var is set."""
    os.environ.pop("JOURNEY_REVIEW_APPLY_ENABLED", None)
    assert apply_approval_enabled() is False


def test_apply_approval_can_be_opted_in():
    os.environ["JOURNEY_REVIEW_APPLY_ENABLED"] = "1"
    try:
        assert apply_approval_enabled() is True
    finally:
        os.environ.pop("JOURNEY_REVIEW_APPLY_ENABLED", None)
        assert apply_approval_enabled() is False


# ── 8. Snapshot persistence is gitignored-equivalent ──────────────────


def test_write_review_queue_snapshot_writes_to_gitignored_path():
    """The snapshot path is gitignored; the snapshot is regenerable."""
    proposals = generate_review_queue(min_confidence="high")
    path = write_review_queue_snapshot(proposals)
    assert path == REVIEW_QUEUE_PATH
    assert os.path.exists(path)
    with open(path) as f:
        data = json.load(f)
    assert "proposals" in data
    assert "by_confidence" in data
    assert "by_source_type" in data
    assert data["proposal_count"] == len(proposals)


# ── 9. Min-confidence filter ──────────────────────────────────────────


def test_min_confidence_filter_excludes_low():
    """min_confidence='high' must exclude medium and low proposals."""
    all_p = generate_review_queue(min_confidence="low")
    high_p = generate_review_queue(min_confidence="high")
    assert len(high_p) < len(all_p)
    for p in high_p:
        assert p.confidence == "high"


def test_min_confidence_medium_includes_medium_and_high():
    med = generate_review_queue(min_confidence="medium")
    high = generate_review_queue(min_confidence="high")
    assert len(med) >= len(high)
    for p in med:
        assert p.confidence in ("medium", "high")


# ── 10. Proposal shape ─────────────────────────────────────────────────


def test_proposal_dataclass_shape():
    """Each Proposal has the required fields and the safety defaults."""
    p = Proposal(
        proposal_id="p_test",
        source_type="quote",
        source_id="q-1",
        target_type="customer",
        target_id="c-1",
        confidence="high",
        confidence_score=130,
    )
    assert p.action == "proposed_only"
    assert p.requires_founder_approval is True
    d = p.to_dict()
    assert d["proposal_id"] == "p_test"
    assert d["confidence"] == "high"
    assert d["confidence_score"] == 130
    assert d["requires_founder_approval"] is True
    assert d["action"] == "proposed_only"


# ── 11. End-to-end: only the live routes' read paths ──────────────────


def test_router_approval_endpoint_reserved_by_default():
    """Directly import the route handler to verify the reserved path."""
    from app.routers.journey import journey_review_queue_approve
    # The default env state is JOURNEY_REVIEW_APPLY_ENABLED unset
    os.environ.pop("JOURNEY_REVIEW_APPLY_ENABLED", None)
    import asyncio
    class _FakeReq: pass
    result = asyncio.run(journey_review_queue_approve("p_anything", _FakeReq()))
    assert result["status"] == "reserved"
    assert result["apply_enabled"] is False
    assert "disabled" in result["detail"]


def test_router_approval_endpoint_reserved_even_with_opt_in():
    """Even if the env var is set, the apply path is still 'reserved'
    in this pass — it just reports apply_enabled=True so the founder
    can see the opt-in took effect.
    """
    from app.routers.journey import journey_review_queue_approve
    os.environ["JOURNEY_REVIEW_APPLY_ENABLED"] = "1"
    try:
        import asyncio
        class _FakeReq: pass
        result = asyncio.run(journey_review_queue_approve("p_anything", _FakeReq()))
        assert result["status"] == "reserved"
        assert result["apply_enabled"] is True
        assert "not implemented" in result["detail"]
    finally:
        os.environ.pop("JOURNEY_REVIEW_APPLY_ENABLED", None)
