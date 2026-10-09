"""2026-10-08 (Rafael): change-order invoice — grouped by area with Sq ft / Price columns,
plain fractions, earlier deposit applied: deposit due now and balance on completion."""
from app.services.invoice_pdf_service import credit_schedule, render_client_invoice_html


def _inv():
    return {
        "invoice_number": "INV-TEST-1", "total": 1000.0, "subtotal": 1000.0, "tax_rate": 0, "tax_amount": 0,
        "deposit_required": 500.0, "deposit_received": 300.0, "deposit_date": "2026-09-27",
        "pricing_snapshot_json": {"change_order": {"number": 1, "credit_ref": "INV-OLD"}},
        "line_items": [
            {"room": "U banquette", "description": "Seat back — main\n249 3/4\" run · back 26¾\"", "quantity": 1,
             "unit": "ea", "unit_price": 650.0, "total": 650.0, "sq_ft": 10, "price_per_sqft": 65},
            {"room": "Material", "description": "Vinyl", "quantity": 1, "unit": "lot", "unit_price": 350.0, "total": 350.0},
        ],
    }


def test_credit_schedule_amounts():
    c = credit_schedule(_inv())
    assert c["due_now"] == 200.0 and c["balance_on_completion"] == 500.0 and c["received_date"] == "09/27/2026"


def test_change_order_html():
    html = render_client_invoice_html(_inv())
    assert "Sq ft" in html and "Subtotal &mdash; U banquette" in html and "Subtotal &mdash; Material" in html
    assert "Deposit due now" in html and "$200.00" in html and "Balance on completion" in html
    assert "-$300.00" in html and "INV-OLD" in html and "Change Order 1" in html
    assert '26 3/4"' in html and "¾" not in html


def test_plain_invoice_unchanged_columns():
    inv = {"invoice_number": "X", "total": 10, "subtotal": 10,
           "line_items": [{"description": "Item", "quantity": 1, "unit_price": 10, "total": 10}]}
    html = render_client_invoice_html(inv)
    assert "Unit Price" in html and "Sq ft" not in html and "Deposit due now" not in html
