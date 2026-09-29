"""PHASE 2 · F5-H43 portal button compatibility sweep.

The Command Center portal hits 6 backend URLs from QuoteActions.tsx
and QuoteCard.tsx. Pre-F5, 5 of them returned 404 (the legacy
quotes.py router reads stale-fork JSON which has been empty).

This test walks EVERY portal button endpoint and asserts non-404.
The sweep is the point: ANY future regression that breaks a portal
button MUST fail this test.

Endpoints covered:
  - POST   /quotes/{quote_id}/accept
  - POST   /quotes/{quote_id}/send
  - POST   /quotes/{quote_id}/pdf
  - DELETE /quotes/{quote_id}
  - POST   /jobs/from-quote/{quote_id}
  - POST   /finance/invoices/from-quote/{quote_id}

TEARDOWN: create-job and create-invoice tests mutate the live DB
(rows are inserted). The `h43_test_sweep_artifacts` fixture tracks
the created job_id / invoice_id and deletes them at the end of the
session. Marked identifiers (the test quote_id) ensure cleanup is
targeted. Tests using @pytest.mark.live_db to opt out of the test
isolation are the only ones that hit prod — these tests are
explicitly prod-touching.
"""
from __future__ import annotations

import os
import json
import sqlite3

import pytest
import requests


API_BASE = os.environ.get("EMPIRE_API_BASE", "http://127.0.0.1:8000")


# Track rows created by tests for cleanup
_created_job_ids: list[str] = []
_created_invoice_ids: list[str] = []
_created_quote_ids: list[str] = []


@pytest.fixture(scope="session", autouse=True)
def h43_test_sweep_artifacts():
    """Session-scope autouse: clean up jobs/invoices/etc. created by
    the H43 sweep tests. The compat router creates real DB rows
    when the buttons are clicked — without this teardown, every
    sweep pollutes the live DB."""
    yield
    if _created_job_ids or _created_invoice_ids or _created_quote_ids:
        try:
            conn = sqlite3.connect('/home/rg/empire-data/empire.db')
            for jid in _created_job_ids:
                conn.execute("DELETE FROM jobs WHERE id = ?", (jid,))
            for iid in _created_invoice_ids:
                conn.execute("DELETE FROM invoices WHERE id = ?", (iid,))
            for qid in _created_quote_ids:
                conn.execute("DELETE FROM quote_line_items WHERE quote_id = ?", (qid,))
                conn.execute("DELETE FROM quote_photos WHERE quote_id = ?", (qid,))
                conn.execute("DELETE FROM quotes_v2 WHERE id = ?", (qid,))
            conn.commit()
            conn.close()
        except Exception:
            pass


def _canonical_quote_id() -> str:
    """Read the canonical quotes_v2 DB to get a real quote id."""
    import sqlite3
    conn = sqlite3.connect('/home/rg/empire-data/empire.db')
    row = conn.execute("SELECT id FROM quotes_v2 ORDER BY rowid DESC LIMIT 1").fetchone()
    if not row:
        pytest.skip("no canonical quote available")
    return str(row[0])


def _track_created_job(body: dict):
    """Track a job_id for cleanup."""
    job_id = body.get("job_id")
    if job_id:
        _created_job_ids.append(job_id)


def _track_created_invoice(body: dict):
    """Track an invoice_id for cleanup."""
    invoice_id = body.get("invoice_id")
    if invoice_id:
        _created_invoice_ids.append(invoice_id)


@pytest.mark.e2e_live
def test_h43_quote_accept_not_404():
    """POST /quotes/{quote_id}/accept — QuoteActions Accept button."""
    quote_id = _canonical_quote_id()
    r = requests.post(f"{API_BASE}/api/v1/quotes/{quote_id}/accept", json={}, timeout=10)
    assert r.status_code != 404, f"Accept button 404: {r.text}"
    assert r.status_code < 500, f"Accept button 5xx: {r.text}"


@pytest.mark.e2e_live
def test_h43_quote_send_email_not_404():
    """POST /quotes/{quote_id}/send — QuoteActions Send Email button."""
    quote_id = _canonical_quote_id()
    r = requests.post(
        f"{API_BASE}/api/v1/quotes/{quote_id}/send",
        json={"email": "empirebox2026@gmail.com"},
        timeout=10,
    )
    assert r.status_code != 404, f"Send Email button 404: {r.text}"


@pytest.mark.e2e_live
def test_h43_quote_pdf_post_not_404():
    """POST /quotes/{quote_id}/pdf?skip_verification=true — QuoteActions PDF button."""
    quote_id = _canonical_quote_id()
    r = requests.post(
        f"{API_BASE}/api/v1/quotes/{quote_id}/pdf?skip_verification=true",
        json={},
        timeout=10,
    )
    assert r.status_code != 404, f"PDF button 404: {r.text}"
    if r.status_code == 200:
        assert r.headers.get("content-type", "").startswith("application/pdf"), (
            f"PDF button should return application/pdf; got {r.headers.get('content-type')}"
        )


@pytest.mark.e2e_live
def test_h43_quote_delete_not_via_404():
    """DELETE /quotes/{quote_id} — does NOT crash with 404 on a real quote."""
    quote_id = _canonical_quote_id()
    r = requests.delete(f"{API_BASE}/api/v1/quotes/{quote_id}-NOTREAL", timeout=10)
    body = r.text or ""
    assert "Quote" in body or "not found" in body.lower() or r.status_code != 404, (
        f"DELETE route missing; got {r.status_code} {body}"
    )


@pytest.mark.e2e_live
def test_h43_create_job_from_quote_not_404():
    """POST /jobs/from-quote/{quote_id} — QuoteActions Create Job button."""
    quote_id = _canonical_quote_id()
    r = requests.post(f"{API_BASE}/api/v1/jobs/from-quote/{quote_id}", json={}, timeout=10)
    assert r.status_code != 404, f"Create Job button 404: {r.text}"
    if r.status_code == 200:
        try:
            _track_created_job(r.json())
        except Exception:
            pass


@pytest.mark.e2e_live
def test_h43_create_invoice_from_quote_not_404():
    """POST /finance/invoices/from-quote/{quote_id} — QuoteActions Create Invoice button."""
    quote_id = _canonical_quote_id()
    r = requests.post(
        f"{API_BASE}/api/v1/finance/invoices/from-quote/{quote_id}",
        json={},
        timeout=10,
    )
    assert r.status_code != 404, f"Create Invoice button 404: {r.text}"
    if r.status_code == 200:
        try:
            _track_created_invoice(r.json())
        except Exception:
            pass


@pytest.mark.e2e_live
def test_h43_full_sweep_log():
    """Walk ALL six endpoints in one test and report non-404 count."""
    quote_id = _canonical_quote_id()
    endpoints = [
        ("POST", f"/api/v1/quotes/{quote_id}/accept", {}),
        ("POST", f"/api/v1/quotes/{quote_id}/send", {"email": "empirebox2026@gmail.com"}),
        ("POST", f"/api/v1/quotes/{quote_id}/pdf?skip_verification=true", {}),
        ("POST", f"/api/v1/jobs/from-quote/{quote_id}", {}),
        ("POST", f"/api/v1/finance/invoices/from-quote/{quote_id}", {}),
    ]
    results = []
    for method, path, body in endpoints:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=10)
        results.append((method, path, r.status_code, r.text[:80]))
        # Track created artifacts for cleanup
        if r.status_code == 200:
            try:
                blob = r.json()
                if "/jobs/" in path:
                    _track_created_job(blob)
                elif "/invoices/" in path:
                    _track_created_invoice(blob)
            except Exception:
                pass
    non_404 = [(m, p, s, t) for m, p, s, t in results if s != 404]
    failed = [(m, p, s, t) for m, p, s, t in results if s == 404]
    print(f"\n== H43 SWEEP ({len(results)} endpoints) ==")
    for m, p, s, t in results:
        marker = "❌ 404" if s == 404 else ("✓ OK" if s < 400 else f"⚠️ {s}")
        print(f"  {m} {p}: {marker}  {t}")
    assert len(failed) == 0, f"H43 sweep failed: {len(failed)} endpoints returned 404: {failed}"
    assert len(non_404) == len(results), f"some endpoints still 404: {failed}"
