"""HOTFIX 5 (2026-07-15): founder-facing money-display regression tests.

PRODUCTION DEFECT — observed on the live Maggie O'Neil EST-2026-110 quote:

  A line item had:
    unit_price     = 2400     (original, inherited from a draft estimate)
    final_price    = 1933.33  (founder override, 2-line discount)
    price_overridden = 1

  QuoteReviewScreen rendered:
    per-line rate     = $2,400.00 (from item.rate alias of unit_price)
    per-line amount   = $2,400.00 (from item.amount alias of subtotal)
    displayed total   = $3,600.00 (client-recomputed from line items)
  Canonical quote totals (DB):
    quotes_v2.total   = $2,900.00 (server _recalculate_totals honored
                                    final_price correctly)

  Result: the screen displayed $3,600 — off by $700 — for a quote the
  founder already sent to the client.

ROOT CAUSE — three layers:

  1. _item_to_dict in quote_service aliased rate=unit_price and
     amount=subtotal unconditionally, ignoring price_overridden. Every
     downstream display path (QuoteReviewScreen, PDF, etc.) inherited
     the wrong values.
  2. quote_pdf_service.py read unit_price directly when rendering the
     line-item price columns of the customer-facing PDF.
  3. The QuoteReviewScreen's Total cell showed a client-side
     computedTotal (sum of item.amount) instead of quote.total.

FIX:

  1. _item_to_dict now emits rate/amount from final_price when
     price_overridden=1.
  2. quote_pdf_service.py renders final_price in the line-item rate +
     amount columns when price_overridden=1.
  3. QuoteReviewScreen renders `quote.total` (canonical) by default;
     falls back to computedTotal only while the user has unsaved edits
     (dirty=true). Per-row "Founder override" badge makes the override
     state explicit.

SAVE PATH AUDIT (verified safe — fix only needed for display):

  - update_quote (PATCH handler) only accepts a fixed `updatable`
    whitelist that EXCLUDES subtotal/tax_amount/total/deposit_required.
    line_items is also not in the whitelist. So the PATCH body cannot
    overwrite quote totals — server always recomputes from DB line
    items via _recalculate_totals, which honors final_price when
    price_overridden=1. The override is therefore preserved on save.
  - The frontend still sends subtotal/tax_amount/total in the PATCH
    body for backwards compat with any older clients. They are
    silently dropped (HTTP 200, no error) because they are not in the
    whitelist. Defense-in-depth is preserved.

These tests pin the new contract end-to-end.
"""
from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def two_line_quote():
    """Insert a quote with two catalog-priced line items. Returns
    (quote_id, item_a_id, item_b_id, original_prices)."""
    from app.services.quote_service import create_quote
    result = create_quote({
        "customer_name": "HOTFIX5 Test",
        "business_unit": "workroom",
        "line_items": [
            {
                "category": "pinch_pleat",
                "description": "Pinched pleat drapery (12 ft rod)",
                "quantity": 1,
                "unit_price": 2400.00,
                "subtotal": 2400.00,
            },
            {
                "category": "pinch_pleat",
                "description": "Pinched pleat drapery (6 ft rod)",
                "quantity": 1,
                "unit_price": 1200.00,
                "subtotal": 1200.00,
            },
        ],
        "tax_rate": 0.0,
        "project_name": "HOTFIX-5 baseline",
    })
    qid = result["id"]
    # Item ids were assigned by create_quote. Pull them back so we can
    # target the override.
    from app.services.quote_service import get_quote
    full = get_quote(qid)
    item_a = full["line_items"][0]
    item_b = full["line_items"][1]
    yield (
        qid,
        item_a["id"],
        item_a["unit_price"],
        item_b["id"],
        item_b["unit_price"],
    )
    # Best-effort cleanup so the isolated DB stays tidy for other tests.
    import sqlite3, os
    conn = sqlite3.connect(os.environ.get("EMPIRE_TASK_DB", ""))
    try:
        conn.execute("DELETE FROM quote_line_items WHERE quote_id = ?", (qid,))
        conn.execute("DELETE FROM quotes_v2 WHERE id = ?", (qid,))
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# (1) Server alias: rate/amount come from final_price when overridden
# ──────────────────────────────────────────────────────────────

def test_item_to_dict_alias_honors_price_overridden(isolated_empire_db,
                                                     two_line_quote):
    """When price_overridden=1, the row's rate and amount aliases MUST
    point at final_price, not the original unit_price / subtotal."""
    from app.services.quote_service import (
        get_quote, update_final_price,
    )
    qid, item_a_id, item_a_unit, _item_b_id, _item_b_unit = two_line_quote

    # Override item_a: 2400 -> 1933.33 (proportional 2-line discount)
    updated = update_final_price(qid, item_a_id, 1933.33,
                                 changed_by="hotfix5-test")
    assert updated is not None
    assert updated["price_overridden"] == 1
    assert updated["final_price"] == pytest.approx(1933.33, abs=0.01)

    # The API response must surface final_price as the alias.
    full = get_quote(qid)
    item = next(li for li in full["line_items"] if li["id"] == item_a_id)
    assert item["rate"] == pytest.approx(1933.33, abs=0.01), (
        f"alias `rate` MUST be final_price when overridden; got {item['rate']}"
    )
    assert item["amount"] == pytest.approx(1933.33, abs=0.01), (
        f"alias `amount` MUST be final_price when overridden; got {item['amount']}"
    )
    # Original unit_price is still preserved on the row for audit.
    assert item["unit_price"] == pytest.approx(2400.00, abs=0.01)


def test_item_to_dict_alias_falls_back_when_not_overridden(isolated_empire_db,
                                                            two_line_quote):
    """Without an override, the alias falls back to unit_price /
    subtotal as it always did."""
    from app.services.quote_service import get_quote
    qid, _ia, _aiup, item_b_id, item_b_unit = two_line_quote
    full = get_quote(qid)
    item = next(li for li in full["line_items"] if li["id"] == item_b_id)
    assert item["price_overridden"] == 0
    assert item["rate"] == pytest.approx(item_b_unit, abs=0.01)
    assert item["amount"] == pytest.approx(item_b_unit, abs=0.01)


# ──────────────────────────────────────────────────────────────
# (2) Server totals: client-side recompute must not be able to
# overwrite canonical quotes_v2.total
# ──────────────────────────────────────────────────────────────

def test_save_does_not_overwrite_canonical_total_from_client(
        isolated_empire_db, two_line_quote):
    """Founder edits/saves a quote through PATCH. The PATCH body may
    carry subtotal/total/tax_amount but the server must ignore those
    and keep its canonical total. This pins the SAVE PATH AUDIT
    conclusion from HOTFIX 5."""
    from app.services.quote_service import (
        create_quote, get_quote, update_final_price,
    )
    qid, item_a_id, _a_up, item_b_id, _b_up = two_line_quote
    # Apply BOTH overrides to mirror the Maggie O'Neil EST-2026-110 case
    # from the bug report: $2,400 -> $1,933.33 and $1,200 -> $966.67.
    update_final_price(qid, item_a_id, 1933.33, changed_by="hotfix5-test")
    update_final_price(qid, item_b_id, 966.67, changed_by="hotfix5-test")

    # Sanity: canonical total is $2,900 (sum of both final_prices).
    full_before = get_quote(qid)
    assert full_before["total"] == pytest.approx(2900.00, abs=0.01), (
        f"baseline total must be $2,900; got {full_before['total']}"
    )

    # PATCH with WRONG totals (what a buggy frontend would do).
    from app.services.quote_service import update_quote
    update_quote(qid, {
        "subtotal": 99999.99,
        "tax_amount": 99999.99,
        "total": 99999.99,
        "tax_rate": 0.0,
        "discount_amount": 0,
        "deposit_percent": 50,
    })

    # After the PATCH, the server's canonical total must be unchanged.
    full_after = get_quote(qid)
    assert full_after["total"] == pytest.approx(2900.00, abs=0.01), (
        f"server must recompute total from line items (using final_price "
        f"when overridden); PATCH attempted to inject 99999.99 but the "
        f"canonical total is now {full_after['total']}"
    )
    assert full_after["subtotal"] == pytest.approx(2900.00, abs=0.01)
    # The override must still be in place after the PATCH.
    item_a = next(li for li in full_after["line_items"] if li["id"] == item_a_id)
    item_b = next(li for li in full_after["line_items"] if li["id"] == item_b_id)
    assert item_a["price_overridden"] == 1
    assert item_a["final_price"] == pytest.approx(1933.33, abs=0.01)
    assert item_b["price_overridden"] == 1
    assert item_b["final_price"] == pytest.approx(966.67, abs=0.01)


# ──────────────────────────────────────────────────────────────
# (3) PDF rendering: customer-facing PDF reflects the override
# ──────────────────────────────────────────────────────────────

def test_pdf_uses_final_price_when_overridden(isolated_empire_db,
                                                two_line_quote):
    """The PDF service must render final_price (not unit_price) for a
    line item with price_overridden=1.

    The 'Founder override' badge is a QuoteReviewScreen-only surface
    (not in the PDF). The PDF contract is: customer-facing numbers MUST
    equal the canonical quote total, which they do once the
    price_overridden=1 case routes unit_price/subtotal through
    final_price in the PDF service."""
    from app.services.quote_service import (
        get_quote, update_final_price,
    )
    qid, item_a_id, _a_up, item_b_id, _b_up = two_line_quote
    # Override only item_a (matches the canonical single-override case
    # for the line-item price column — the multi-override case is
    # exercised by the canonical-total test above).
    update_final_price(qid, item_a_id, 1933.33, changed_by="hotfix5-test")

    # Generate the PDF and parse it.
    pdf_bytes = None
    try:
        from app.services.quote_pdf_service import generate_quote_pdf
        pdf_bytes = generate_quote_pdf(qid)
    except Exception as e:
        pytest.fail(f"generate_quote_pdf raised {type(e).__name__}: {e}")
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 1024, "PDF must be a non-trivial size"

    # pdfplumber is a TEST-ONLY dep per Phase B plan; skip if absent.
    pytest.importorskip("pdfplumber", reason="pdfplumber is a TEST-ONLY dep")

    import io
    import pdfplumber
    text_pages: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text_pages.append(page.extract_text() or "")
    full_text = "\n".join(text_pages)

    # Override value must appear in the PDF for the overridden row.
    assert "1,933" in full_text, (
        f"PDF must show the founder-set $1,933.33 for the overridden row; "
        f"snippet: {full_text[:400]!r}"
    )
    # Non-overridden row keeps its unit_price.
    assert "1,200" in full_text, (
        f"PDF must show the non-overridden row at its $1,200 rate"
    )
    # Canonical subtotal of the two lines ($3,133.33) MUST be the PDF
    # Subtotal row — confirming the renderer respects final_price when
    # overridden. The earlier Phase-A bug was: subtotal used unit_price,
    # summing $3,600 instead of $3,133.33.
    assert "3,133" in full_text, (
        f"PDF subtotal/TOTAL must reflect the founder override "
        f"($1,933.33 + $1,200.00 = $3,133.33); snippet: {full_text[:400]!r}"
    )


# ──────────────────────────────────────────────────────────────
# (4) Display contract: total visible to the founder matches the
# canonical server total — the regression that produced the bug report
# ──────────────────────────────────────────────────────────────

def test_get_quote_returns_canonical_total_for_overridden_quote(
        isolated_empire_db, two_line_quote):
    """The exact shape the frontend renders: the total field must be
    $2,900.00, NOT $3,600.00."""
    from app.services.quote_service import (
        get_quote, update_final_price,
    )
    qid, item_a_id, _a_up, item_b_id, _b_up = two_line_quote
    # Apply BOTH overrides to mirror the Maggie O'Neil EST-2026-110 case.
    update_final_price(qid, item_a_id, 1933.33, changed_by="hotfix5-test")
    update_final_price(qid, item_b_id, 966.67, changed_by="hotfix5-test")

    full = get_quote(qid)
    assert full["total"] == pytest.approx(2900.00, abs=0.01), (
        f"canonical total must be $2,900; got {full['total']}. "
        f"Line items: {[(li.get('unit_price'), li.get('final_price'), li.get('price_overridden')) for li in full['line_items']]}"
    )
    # Cross-check: the line-item aliases (rate/amount) already reflect
    # the override — so a client-side recompute would now produce the
    # same $2,900 total. The fix protects both server-truth and display.
    alias_sum = sum(li["amount"] for li in full["line_items"])
    assert alias_sum == pytest.approx(2900.00, abs=0.01), (
        f"line-item amount aliases must sum to canonical total $2,900; "
        f"got {alias_sum}. Items: "
        f"{[(li.get('unit_price'), li.get('final_price'), li.get('price_overridden'), li.get('amount')) for li in full['line_items']]}"
    )
