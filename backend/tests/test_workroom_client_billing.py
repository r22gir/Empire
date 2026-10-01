"""Nelma's Workroom client billing PDFs, email signatures, and invoice rules."""
from __future__ import annotations

import io

from app.config.workroom_billing import get_workroom_billing
from app.services.invoice_pdf_service import (
    JOB_DEPOSIT_SCHEDULE_NOTE,
    client_visible_line_description,
    client_visible_notes,
    render_client_invoice_html,
    uses_job_deposit_schedule,
)
from app.services.max.email_template import render_house_email
from app.services.quote_pdf_service import (
    COMPANY_NAME,
    generate_quote_pdf_legacy_portrait,
)


def test_workroom_billing_defaults():
    b = get_workroom_billing()
    assert b.name == "Nelma's Workroom"
    assert "5124 Frolich" in b.address
    assert "Rafael" not in b.name


def test_house_email_signature_uses_billing_name_only():
    rendered = render_house_email("Please see attached.", recipient_name="Client")
    assert "Nelma's Workroom" in rendered.plain_text
    assert "Rafael Giraldo" not in rendered.plain_text
    assert "Rafael Giraldo" not in rendered.html


def test_client_visible_line_strips_allocation_math():
    item = {
        "description": "Supplied fabric, plain backs\nU share, 62.4% of 17 yd",
    }
    assert client_visible_line_description(item) == "Supplied fabric, plain backs"


def test_client_visible_notes_hides_split_reference():
    notes = "Thank you.\nSplit from INV-2026-123"
    assert client_visible_notes(notes) == "Thank you."


def test_invoice_html_title_and_deposit_schedule():
    inv = {
        "invoice_number": "INV-2026-99",
        "invoice_date": "2026-10-01",
        "due_date": "2026-10-31",
        "terms": "Net 30",
        "subtotal": 1000.0,
        "tax_rate": 0.06,
        "tax_amount": 60.0,
        "total": 1060.0,
        "client_name": "Test Client",
        "line_items": [
            {
                "description": "Bench upholstery",
                "quantity": 1,
                "unit": "ea",
                "unit_price": 1000,
                "total": 1000,
            }
        ],
        "client_job_deposit_schedule": 1,
        "notes": "Split from INV-2026-001",
    }
    html = render_client_invoice_html(inv)
    assert "<title>INVOICE</title>" in html
    assert "DRAFT INVOICE" not in html.upper()
    assert "<h1>INVOICE</h1>" in html
    assert "50% Deposit Due" in html
    assert "Balance Due" in html
    assert JOB_DEPOSIT_SCHEDULE_NOTE in html
    assert "Split from INV" not in html
    assert uses_job_deposit_schedule(inv)


def test_legacy_quote_pdf_header_is_nelmas_workroom(monkeypatch, tmp_path):
    from app.services import quote_pdf_service

    quote = {
        "id": "q-bill",
        "quote_number": "EST-BILL",
        "customer_name": "Test",
        "status": "draft",
        "created_at": "2026-10-01",
        "line_items": [{
            "description": "Panel",
            "quantity": 1,
            "unit_price": 100,
            "subtotal": 100,
        }],
        "subtotal": 100,
        "tax_rate": 0,
        "tax_amount": 0,
        "total": 100,
    }
    monkeypatch.setattr(quote_pdf_service, "get_quote", lambda _id: quote)
    monkeypatch.setattr(quote_pdf_service, "quote_pdf_dir", lambda: tmp_path)

    assert COMPANY_NAME == "Nelma's Workroom"
    pdf_bytes = generate_quote_pdf_legacy_portrait("q-bill")
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages
    )
    assert "Nelma's Workroom" in text
    assert "Rafael Giraldo" not in text
    assert "Empire Workroom" not in text
