"""Invoices render through the estimate's design; sq ft shown as fractions."""
import json
import subprocess

from app.services.estimates.mclean_estimate_pdf import sqft_fraction
from app.services.estimates.invoice_mclean_pdf import render_invoice_bytes


def test_sqft_fraction():
    assert sqft_fraction(7.012) == "7"
    assert sqft_fraction(46.39) == "46 3/8"
    assert sqft_fraction(4.72) == "4 3/4"
    assert sqft_fraction(0.25) == "1/4"
    assert sqft_fraction(None) == ""


def _inv(**kw):
    inv = {
        "invoice_number": "INV-2026-999", "client_name": "Marley's Bar & Grill · Attn Davonne Austin",
        "client_email": "info@example.com", "client_address": "6450 America Blvd", "invoice_date": "2026-10-09",
        "subtotal": 300.0, "total": 300.0, "tax_rate": 0, "tax_amount": 0, "amount_paid": 0, "balance_due": 200.0,
        "invoice_stage": "final", "status": "draft", "payment_status": "link_ready",
        "stripe_checkout_url": "https://checkout.stripe.com/c/pay/cs_test_x",
        "pricing_snapshot_json": {"final_settlement": {"contract_total": 300}},
        "_ledger_credits": [{"label": "Deposit received", "invoice_number": "INV-2026-001", "amount": 100.0,
                              "payment_date": "2026-09-27"}],
        "_ledger_prior": [],
        "line_items": [
            {"room": "U banquette", "description": "Seat back\n37 3/4\" run", "quantity": 1, "unit": "ea",
             "unit_price": 65, "total": 150.0, "sq_ft": 46.39, "price_per_sqft": 65.0},
            {"room": "Material", "description": "Vinyl", "quantity": 1, "unit": "lot", "unit_price": 150, "total": 150.0},
        ],
    }
    inv.update(kw)
    return inv


def _text(pdf, tmp_path):
    p = tmp_path / "i.pdf"
    p.write_bytes(pdf)
    return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout


def test_invoice_uses_estimate_design_and_balance_only_link(tmp_path):
    pdf = render_invoice_bytes(_inv())
    t = " ".join(_text(pdf, tmp_path).split())
    assert "EMPIRE WORKROOM" in t and "Invoice INV-2026-999" in t and "Final invoice" in t
    assert "46 3/8" in t and "46.39" not in t
    assert "SUBTOTAL — U banquette" in t and "SUBTOTAL — Material" in t
    assert "PAYMENTS & CREDITS APPLIED" in t and "-$100.00" in t
    assert "Balance due" in t and "$200.00" in t
    assert "Pay balance online: $200.00" in t
    assert b"/URI" in pdf and b"checkout.stripe.com" in pdf
    assert "DRY RUN" not in t and "Nelma" not in t and "Bladensburg" not in t


def test_dry_run_banner_only_when_flagged(tmp_path):
    assert "DRY RUN" in _text(render_invoice_bytes(_inv(_dry_run=True)), tmp_path)
