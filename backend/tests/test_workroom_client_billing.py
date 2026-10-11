"""Client billing: Empire Workroom default, optional Nelma's, no founder name."""
from __future__ import annotations

import io

from app.config.workroom_billing import (
    BILLED_BY_EMPIRE,
    BILLED_BY_NELMA,
    PUBLIC_CLIENT_HOST,
    billed_by_for_storage,
    client_facing_origin,
    client_facing_website,
    get_workroom_billing,
    normalize_billed_by,
    resolve_billing,
)
from app.services.invoice_pdf_service import (
    JOB_DEPOSIT_SCHEDULE_NOTE,
    client_visible_line_description,
    client_visible_notes,
    render_client_invoice_html,
)
from app.services.max.email_template import render_house_email
from app.services.quote_pdf_service import generate_quote_pdf_legacy_portrait


def test_default_billing_is_empire_workroom():
    b = get_workroom_billing()
    assert b.name == "Empire Workroom"
    assert b.website == PUBLIC_CLIENT_HOST
    assert "studio.empirebox.store" not in b.website
    assert normalize_billed_by(None) == BILLED_BY_EMPIRE
    assert billed_by_for_storage(None) is None


def test_client_docs_replace_internal_app_links():
    assert client_facing_website("https://studio.empirebox.store") == PUBLIC_CLIENT_HOST
    assert client_facing_website("https://api.empirebox.store/quotes/1") == PUBLIC_CLIENT_HOST
    assert client_facing_website("http://localhost:3005/presentation/abc") == PUBLIC_CLIENT_HOST
    assert client_facing_origin("https://studio.empirebox.store") == f"https://{PUBLIC_CLIENT_HOST}"
    assert client_facing_origin("https://woodcraft.example") == "https://woodcraft.example"


def test_nelmas_billing_option():
    b = get_workroom_billing(BILLED_BY_NELMA)
    assert b.name == "Nelma's Workroom"
    assert "Frolich" in b.address
    assert b.phone == "(703) 623-9203"
    assert b.email == "workroom@empirebox.store"
    assert b.website == PUBLIC_CLIENT_HOST
    assert billed_by_for_storage(BILLED_BY_NELMA) == BILLED_BY_NELMA


def test_house_email_empire_default_no_founder_name():
    rendered = render_house_email("Please see attached.", recipient_name="Client")
    assert "Empire Workroom" in rendered.plain_text
    assert "Rafael Giraldo" not in rendered.plain_text
    assert "Rafael Giraldo" not in rendered.html


def test_house_email_nelmas_entity_no_founder_name():
    rendered = render_house_email(
        "Please see attached.",
        recipient_name="Client",
        billed_by=BILLED_BY_NELMA,
    )
    assert "Nelma's Workroom" in rendered.plain_text
    assert "Rafael Giraldo" not in rendered.plain_text


def test_client_visible_line_strips_allocation_math():
    item = {
        "description": "Supplied fabric, plain backs\nU share, 62.4% of 17 yd",
    }
    assert client_visible_line_description(item) == "Supplied fabric, plain backs"


def test_invoice_html_empire_default_and_deposit_schedule():
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
    assert "Empire Workroom" in html
    assert PUBLIC_CLIENT_HOST in html
    assert "studio.empirebox.store" not in html
    assert "50% Deposit Due" in html
    assert JOB_DEPOSIT_SCHEDULE_NOTE in html
    assert "Split from INV" not in html
    assert client_visible_notes(inv["notes"]) is None


def test_woodcraft_invoice_uses_public_website():
    html = render_client_invoice_html(
        {
            "invoice_number": "INV-WC-1",
            "invoice_date": "2026-10-01",
            "due_date": "2026-10-31",
            "terms": "Due on receipt",
            "subtotal": 100.0,
            "tax_rate": 0.0,
            "tax_amount": 0.0,
            "total": 100.0,
            "client_name": "Test",
            "line_items": [{"description": "Shelf", "quantity": 1, "unit": "ea", "unit_price": 100, "total": 100}],
        },
        is_woodcraft=True,
    )
    assert PUBLIC_CLIENT_HOST in html
    assert "studio.empirebox.store" not in html
    assert "api.empirebox.store" not in html


def test_invoice_html_nelmas_when_billed_by_set():
    inv = {
        "invoice_number": "INV-2026-100",
        "invoice_date": "2026-10-01",
        "due_date": "2026-10-31",
        "terms": "Net 30",
        "subtotal": 500.0,
        "tax_rate": 0.0,
        "tax_amount": 0.0,
        "total": 500.0,
        "client_name": "Test",
        "billed_by": BILLED_BY_NELMA,
        "line_items": [{"description": "Labor", "quantity": 1, "unit": "ea", "unit_price": 500, "total": 500}],
    }
    html = render_client_invoice_html(inv)
    assert "Nelma's Workroom" in html
    assert "Empire Workroom" not in html


def test_legacy_quote_pdf_respects_billed_by(monkeypatch, tmp_path):
    from app.services import quote_pdf_service

    quote = {
        "id": "q-bill",
        "quote_number": "EST-BILL",
        "customer_name": "Test",
        "status": "draft",
        "created_at": "2026-10-01",
        "billed_by": BILLED_BY_NELMA,
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

    quote["billed_by"] = None
    pdf_empire = generate_quote_pdf_legacy_portrait("q-bill")
    text_empire = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(io.BytesIO(pdf_empire)).pages
    )
    assert "Empire Workroom" in text_empire
    assert PUBLIC_CLIENT_HOST in text_empire
    assert "studio.empirebox.store" not in text_empire
