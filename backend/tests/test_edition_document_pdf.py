"""Max-e / Maxine quote and invoice PDFs use each company's config.

Tests write only under tmp_path (EMPIRE_DATA_DIR). They never open or
change repo business.json, client_aliases.json, or .env.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

REPO_BUSINESS = Path(__file__).resolve().parents[1] / "app" / "config" / "business.json"
REPO_ALIASES = Path(__file__).resolve().parents[1] / "app" / "config" / "client_aliases.json"

# 1x1 PNG — fixture only, not a client logo.
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _env(monkeypatch, tmp_path, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


def _write_company(tmp_path: Path, slug: str, **fields) -> Path:
    root = tmp_path / "businesses" / slug
    root.mkdir(parents=True, exist_ok=True)
    name = fields.pop("name", "Taller Norte")
    profile = {
        "slug": slug,
        "name": name,
        "legal_name": fields.pop("legal_name", f"{name} S.A.S." if name == "Taller Norte" else ""),
        "trade_name": fields.pop("trade_name", name),
        "tax_id": fields.pop("tax_id", "901.234.567-8"),
        "iva_rate": fields.pop("iva_rate", 0.19),
        "currency": "COP",
        "country": "Colombia",
        "city": fields.pop("city", "Cartago"),
        "contact_email": "hola@tallernorte.test",
        "contact_phone": "3100000000",
        "website": "tallernorte.test",
    }
    profile.update(fields)
    (root / "business.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    index = tmp_path / "businesses" / "index.json"
    businesses = []
    if index.is_file():
        businesses = json.loads(index.read_text(encoding="utf-8")).get("businesses") or []
    businesses = [row for row in businesses if row.get("slug") != slug]
    businesses.append({"slug": slug, "name": profile["name"]})
    index.write_text(json.dumps({"businesses": businesses}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root


def _quote(slug="taller-norte"):
    return {
        "id": "q-ed-1",
        "quote_number": "COT-2026-010",
        "business_slug": slug,
        "customer_name": "Cliente Demo",
        "customer_nit": "800.111.222-3",
        "customer_email": "cliente@demo.test",
        "status": "draft",
        "created_at": "2026-10-13",
        "valid_days": 15,
        "line_items": [{
            "description": "Panel de cortina",
            "width": 14.5,
            "height": 72.00,
            "quantity": 1,
            "unit_price": 1234567,
            "subtotal": 1234567,
        }],
        "subtotal": 1234567,
        "total": 0,
    }


def _invoice(slug="taller-norte"):
    return {
        "id": "inv-ed-1",
        "invoice_number": "FAC-2026-003",
        "business_slug": slug,
        "client_name": "Cliente Demo",
        "client_nit": "800.111.222-3",
        "invoice_date": "2026-10-13",
        "due_date": "2026-11-13",
        "line_items": [{
            "description": "Instalación",
            "quantity": 1,
            "unit_price": 200000,
            "total": 200000,
        }],
        "subtotal": 200000,
    }


def _pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_format_cop_has_dots_and_no_decimals():
    from app.services.edition_pdf_branding import format_document_cop, normalize_iva_rate

    assert format_document_cop(1234567) == "$1.234.567"
    assert format_document_cop(1234567.8) == "$1.234.568"
    assert "." in format_document_cop(1000)
    assert "," not in format_document_cop(1000)
    assert normalize_iva_rate(None) == 0.19
    assert normalize_iva_rate(19) == 0.19
    assert normalize_iva_rate("19%") == 0.19
    assert normalize_iva_rate(0.16) == 0.16


@pytest.mark.parametrize("edition", ["amp", "maxine"])
def test_quote_pdf_uses_company_name_spanish_cop(monkeypatch, tmp_path, edition):
    _env(monkeypatch, tmp_path, edition)
    root = _write_company(tmp_path, "taller-norte")
    (root / "logo.png").write_bytes(_TINY_PNG)
    repo_before = REPO_BUSINESS.read_bytes() if REPO_BUSINESS.is_file() else None

    from app.edition import set_active_business
    from app.services.edition_document_pdf import render_edition_document_pdf
    from app.services.edition_pdf_branding import resolve_edition_pdf_brand

    set_active_business("taller-norte")
    brand = resolve_edition_pdf_brand({"business_slug": "taller-norte"})
    assert brand.name == "Taller Norte"
    assert brand.nit == "901.234.567-8"
    assert brand.iva_rate == 0.19
    assert brand.logo_path is not None
    assert brand.logo_path.is_file()
    assert "Empire" not in brand.name

    pdf = render_edition_document_pdf(_quote(), kind="cotizacion")
    assert pdf[:4] == b"%PDF"
    text = _pdf_text(pdf)
    folded = text.casefold()
    assert "Taller Norte" in text
    assert "cotizaci" in folded
    assert "cliente" in folded
    assert "fecha" in folded
    assert "validez" in folded
    assert "Subtotal" in text
    assert "IVA" in text
    assert "Total" in text
    assert "NIT" in text
    assert "901.234.567-8" in text
    assert "800.111.222-3" in text
    assert "$1.234.567" in text
    assert "19%" in text
    assert '14½"' in text or "14½" in text
    assert "72.00" not in text
    assert "14.5" not in text
    assert "Empire Workroom" not in text
    assert "ESTIMATE" not in text
    assert "INVOICE" not in text
    if repo_before is not None:
        assert REPO_BUSINESS.read_bytes() == repo_before


@pytest.mark.parametrize("edition", ["amp", "maxine"])
def test_invoice_pdf_uses_factura_and_company_logo_config(monkeypatch, tmp_path, edition):
    _env(monkeypatch, tmp_path, edition)
    _write_company(
        tmp_path,
        "cibernettic",
        name="Cibernettic",
        legal_name="Cibernettic S.A.S.",
        trade_name="Cibernettic",
        tax_id="900.555.666-1",
        iva_rate=0.19,
        city="Bogotá",
    )
    from app.services.edition_document_pdf import generate_edition_invoice_pdf_bytes

    pdf = generate_edition_invoice_pdf_bytes(_invoice("cibernettic"), save=False)
    text = _pdf_text(pdf)
    folded = text.casefold()
    assert "Cibernettic" in text
    assert "factura" in folded
    assert "NIT" in text
    assert "900.555.666-1" in text
    assert "800.111.222-3" in text
    assert "$200.000" in text
    assert "IVA" in text
    assert "Taller Norte" not in text
    assert "Empire Workroom" not in text


def test_generate_quote_pdf_routes_family_not_mclean(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    _write_company(tmp_path, "taller-norte")
    quote = _quote()

    from app.edition import is_family_edition
    from app.services.edition_document_pdf import generate_edition_quote_pdf

    source = Path(__file__).resolve().parents[1] / "app" / "services" / "quote_pdf_service.py"
    hook = source.read_text(encoding="utf-8")
    assert "is_family_edition()" in hook
    assert "generate_edition_quote_pdf" in hook
    assert is_family_edition() is True

    pdf = generate_edition_quote_pdf("q-ed-1", quote=quote, save=True)
    text = _pdf_text(pdf)
    assert "cotizaci" in text.casefold()
    assert "Taller Norte" in text
    assert "Empire Workroom" not in text
    saved = list((tmp_path / "quotes" / "pdf").glob("*.pdf"))
    assert saved
    assert all(str(tmp_path) in str(path) for path in saved)
    assert not (Path("/data/amp") / "quotes").exists() or not any(
        (Path("/data/amp") / "quotes").rglob("COT-2026-010.pdf")
    )


def test_generate_invoice_pdf_routes_family(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    _write_company(
        tmp_path,
        "portal-campestre-2",
        name="Portal Campestre 2",
        legal_name="",
        trade_name="Portal Campestre 2",
        tax_id="800.999.000-4",
    )
    from app.services.invoice_pdf_service import generate_client_invoice_pdf_bytes

    pdf = generate_client_invoice_pdf_bytes(_invoice("portal-campestre-2"))
    text = _pdf_text(pdf)
    assert "Portal Campestre 2" in text
    assert "factura" in text.casefold()
    assert "Empire Workroom" not in text


def test_two_companies_keep_their_own_letterhead(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    _write_company(tmp_path, "taller-norte")
    _write_company(
        tmp_path,
        "cibernettic",
        name="Cibernettic",
        legal_name="Cibernettic S.A.S.",
        trade_name="Cibernettic",
        tax_id="900.555.666-1",
    )
    from app.services.edition_document_pdf import render_edition_document_pdf

    taller = _pdf_text(render_edition_document_pdf(_quote("taller-norte"), kind="cotizacion"))
    cyber = _pdf_text(render_edition_document_pdf(_quote("cibernettic"), kind="cotizacion"))
    assert "Taller Norte" in taller
    assert "Cibernettic" not in taller
    assert "Cibernettic" in cyber
    assert "Taller Norte" not in cyber


def test_does_not_read_or_write_repo_identity_files(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    _write_company(tmp_path, "taller-norte", name="Empresa Prueba")
    aliases_before = REPO_ALIASES.read_bytes() if REPO_ALIASES.is_file() else None
    biz_before = REPO_BUSINESS.read_bytes() if REPO_BUSINESS.is_file() else None
    from app.services.edition_pdf_branding import resolve_edition_pdf_brand

    brand = resolve_edition_pdf_brand({"business_slug": "taller-norte"})
    assert brand.name == "Empresa Prueba"
    if biz_before is not None:
        assert REPO_BUSINESS.read_bytes() == biz_before
    if aliases_before is not None:
        assert REPO_ALIASES.read_bytes() == aliases_before
    assert not (tmp_path / "client_aliases.json").exists()
