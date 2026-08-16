"""PHASE 2 · F5.2 — shared canonical-first resolver test.

The dual-source quote problem (H44) was that the router side had
canonical-first fallback but the tool layer had THREE independent
JSON direct-reads (send_quote_telegram, send_quote_email,
_generate_pdf_for_quote, sketch_to_drawing). F5.2 fixed this by
introducing ONE shared resolver `quote_service.resolve_quote` used
by both routers and tools.

This test seed the isolated test DB with a canonical quote and
proves the shared resolver behavior end-to-end.
"""
from __future__ import annotations

import os
import pytest
import sqlite3


@pytest.fixture
def canonical_quote_in_db(isolated_empire_db):
    """Seed the isolated test DB with a canonical quote for testing."""
    conn = sqlite3.connect(isolated_empire_db)
    try:
        conn.execute("""
            INSERT INTO quotes_v2
                (id, quote_number, customer_name, business_unit, status, total, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, ("f52-test-id", "EST-2026-F52", "f52-test-customer", "workroom", "sent", 241.80))
        conn.execute("""
            INSERT INTO quote_line_items
                (quote_id, line_number, description, quantity, unit_price, subtotal, category, business_unit, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, ("f52-test-id", 1, "f52-test line", 1.0, 241.80, 241.80, "fabric_only", "workroom"))
        conn.commit()
    finally:
        conn.close()
    yield "f52-test-id"
    # Cleanup is automatic via _truncate_test_db_between_tests


def test_resolve_quote_canonical_first(canonical_quote_in_db):
    """resolve_quote returns canonical quotes from quotes_v2."""
    from app.services.quote_service import resolve_quote
    q = resolve_quote(canonical_quote_in_db)
    assert q is not None
    assert q.get("quote_number") == "EST-2026-F52"
    assert "line_items" in q, "canonical quote must have line_items"
    assert q.get("business_unit") == "workroom"


def test_resolve_quote_returns_none_for_missing():
    """resolve_quote returns None for missing quote IDs."""
    from app.services.quote_service import resolve_quote
    assert resolve_quote("nonexistent-id-12345") is None
    assert resolve_quote("") is None
    assert resolve_quote(None) is None  # type: ignore


def test_resolve_quote_falls_back_to_legacy_json():
    """When canonical misses, the resolver falls back to legacy JSON."""
    from app.services.quote_service import resolve_quote
    import json
    from app.services.data_paths import quotes_data_dir
    legacy_path = quotes_data_dir() / "f52-test-legacy-id.json"
    fake_data = {
        "id": "f52-test-legacy-id",
        "quote_number": "EST-2026-F52L",
        "customer_name": "f52-test-legacy",
        "total": 0.0,
    }
    try:
        with open(legacy_path, "w") as f:
            json.dump(fake_data, f)
        q = resolve_quote("f52-test-legacy-id")
        assert q is not None
        assert q.get("quote_number") == "EST-2026-F52L"
        assert q.get("customer_name") == "f52-test-legacy"
    finally:
        if legacy_path.exists():
            legacy_path.unlink()


def test_router_uses_shared_resolver(canonical_quote_in_db):
    """The router's _load_quote delegates to the shared resolver."""
    from app.routers.quotes import _load_quote
    from app.services.quote_service import resolve_quote
    q_from_router = _load_quote(canonical_quote_in_db)
    q_from_resolver = resolve_quote(canonical_quote_in_db)
    assert q_from_router.get("quote_number") == q_from_resolver.get("quote_number")
    assert q_from_router.get("id") == q_from_resolver.get("id")


def test_tool_layer_uses_shared_resolver():
    """The tool layer must use the shared resolver — not a second copy."""
    from app.services.max import tool_executor
    src = open(tool_executor.__file__).read()
    # The router's _load_quote must NOT be imported by the tool layer
    # (would bypass the shared resolver).
    assert "from app.routers.quotes import _load_quote" not in src, (
        "tool layer must not import _load_quote from router — "
        "would bypass the shared resolver"
    )
    # The shared resolver IS used
    assert "from app.services.quote_service import resolve_quote" in src, (
        "tool layer must use the shared resolve_quote"
    )


def test_send_quote_email_uses_shared_resolver(canonical_quote_in_db):
    """The send_quote_email tool must use the shared resolver."""
    from app.services.max.tool_executor import _send_quote_email
    # The tool will fail at the email send step (no SMTP configured), but
    # should NOT fail at the quote lookup step (the bug pre-F5.2).
    result = _send_quote_email({
        "quote_id": canonical_quote_in_db,
        "to": "empirebox2026@gmail.com",
        "subject": "f52-test",
        "body": "f52-test body",
    })
    # If the quote lookup failed, error would be "Quote ... not found".
    # We expect either success or SMTP/email error (not quote error).
    if not result.success:
        assert "Quote" not in (result.error or ""), (
            f"send_quote_email failed at QUOTE LOOKUP step: {result.error}"
        )


def test_send_quote_telegram_uses_shared_resolver(canonical_quote_in_db):
    """The send_quote_telegram tool must use the shared resolver."""
    from app.services.max.tool_executor import _send_quote_telegram
    result = _send_quote_telegram({"quote_id": canonical_quote_in_db})
    # If the quote lookup failed, error would be "Quote ... not found".
    if not result.success:
        assert "Quote" not in (result.error or ""), (
            f"send_quote_telegram failed at QUOTE LOOKUP step: {result.error}"
        )
