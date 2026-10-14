"""Standard create-path quotes must be readable by the PDF / canonical store."""

from __future__ import annotations

import asyncio
import io
import json

from app.config.workroom_billing import resolve_quote_billing
from app.services.estimates.mclean_estimate_pdf import (
    group_estimate_sections,
    inches_to_fractions,
    render_mclean_estimate_bytes,
)
from app.services.quote_pdf_service import generate_quote_pdf
from app.services.quote_service import (
    get_quote,
    get_quote_by_number,
    migrate_legacy_json_quotes,
    upsert_legacy_quote,
)


def _quotes(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    import app.routers.quotes as quotes
    quotes.QUOTES_DIR = str(tmp_path / "quotes")
    (tmp_path / "quotes").mkdir(parents=True, exist_ok=True)
    return quotes


class _OpenQuality:
    blocked = False
    issues = []
    severity = None
    fixed_count = 0


def test_standard_create_is_in_canonical_store_and_pdf(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    monkeypatch.setattr(quotes, "_sync_quote_customer_to_crm", lambda q: None)
    monkeypatch.setattr(quotes.quality_engine, "validate", lambda *a, **k: _OpenQuality())
    created = asyncio.run(quotes.create_quote(quotes.QuoteCreate(
        customer_name="Client House",
        customer_email="client@example.com",
        customer_address="100 Main Street",
        project_name="Living room",
        billed_by="nelmas_workroom",
        line_items=[
            quotes.LineItem(
                description='U banquette — 26.75" wide',
                quantity=1,
                unit="ea",
                rate=1800,
                room="U banquette",
                width=26.75,
                height=18.5,
            ),
            quotes.LineItem(
                description="L banquette seat",
                quantity=1,
                unit="ea",
                rate=1400,
                area="L banquette",
            ),
        ],
    )))
    quote = created["quote"]
    qid = quote["id"]
    qn = quote["quote_number"]

    canonical = get_quote(qid)
    assert canonical is not None
    assert canonical["id"] == qid
    assert get_quote_by_number(qn)["id"] == qid

    from app.routers.portal_button_compat import _existing_or_404
    portal = _existing_or_404(qid)
    assert portal["id"] == qid

    pdf = generate_quote_pdf(qid)
    assert pdf[:4] == b"%PDF"
    from pypdf import PdfReader
    text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    squashed = "".join(text.split()).upper()
    assert "NELMA" in squashed
    assert "EMPIREWORKROOM" not in squashed
    assert "DESCRIPTION" in squashed
    assert "QTY" in squashed
    assert "SQFT" in squashed or "SQ FT" in text.upper()
    assert "GRANDTOTAL" in squashed or "GRAND TOTAL" in text.upper()
    assert "DEPOSIT" in squashed
    assert "BALANCE" in squashed
    assert "26 3/4" in text or "26 3/4\"" in text
    assert "26.75" not in text


def test_json_only_quote_migrates_for_pdf(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    payload = {
        "id": "json-only-1",
        "quote_number": "EST-2026-811",
        "customer_name": "Imported Client",
        "status": "draft",
        "billed_by": "nelmas_workroom",
        "line_items": [
            {"description": 'Panel 36.5" high', "quantity": 2, "unit": "ea", "rate": 400, "room": "Living"},
        ],
        "total": 800,
        "deposit_percent": 50,
    }
    path = tmp_path / "quotes" / "json-only-1.json"
    path.write_text(json.dumps(payload))
    # Do not call _save_quote — this is the pre-fix create-path file.
    migrated = migrate_legacy_json_quotes(apply=True)
    assert "json-only-1" in migrated["imported"]
    assert get_quote("json-only-1")["quote_number"] == "EST-2026-811"
    pdf = generate_quote_pdf("json-only-1")
    assert pdf[:4] == b"%PDF"


def test_upsert_is_idempotent(monkeypatch, tmp_path):
    _quotes(monkeypatch, tmp_path)
    quote = {
        "id": "idem-1",
        "quote_number": "EST-2026-812",
        "customer_name": "Same",
        "line_items": [{"description": "Seat", "quantity": 1, "rate": 10, "amount": 10}],
        "total": 10,
    }
    first = upsert_legacy_quote({**quote, "updated_at": "2026-10-14T12:00:00"})
    second = upsert_legacy_quote({**quote, "updated_at": "2026-10-14T13:00:00"})
    assert first["id"] == second["id"] == "idem-1"
    assert len(second.get("line_items") or []) == 1


def test_upsert_does_not_overwrite_newer_v2(monkeypatch, tmp_path):
    _quotes(monkeypatch, tmp_path)
    from app.db.database import get_db
    first = upsert_legacy_quote({
        "id": "newer-1",
        "quote_number": "EST-2026-815",
        "customer_name": "Canonical Name",
        "updated_at": "2026-10-14T12:00:00",
        "line_items": [{"description": "Seat", "quantity": 1, "rate": 10, "amount": 10}],
        "total": 10,
    })
    assert first["customer_name"] == "Canonical Name"
    with get_db() as conn:
        conn.execute(
            "UPDATE quotes_v2 SET customer_name = ?, updated_at = ? WHERE id = ?",
            ("Newer V2 Name", "2026-10-14T18:00:00", "newer-1"),
        )
    again = upsert_legacy_quote({
        "id": "newer-1",
        "quote_number": "EST-2026-815",
        "customer_name": "Stale JSON Name",
        "updated_at": "2026-10-14T10:00:00",
        "line_items": [{"description": "Other", "quantity": 2, "rate": 5, "amount": 10}],
        "total": 10,
    })
    assert again["customer_name"] == "Newer V2 Name"
    assert [i.get("description") for i in (again.get("line_items") or [])] == ["Seat"]


def test_migrate_is_dry_run_by_default(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    payload = {
        "id": "dry-1",
        "quote_number": "EST-2026-816",
        "customer_name": "Dry Run",
        "line_items": [],
        "total": 0,
    }
    (tmp_path / "quotes" / "dry-1.json").write_text(json.dumps(payload))
    result = migrate_legacy_json_quotes()
    assert result["dry_run"] is True
    assert result["apply"] is False
    assert "dry-1" in result["planned"]
    assert get_quote("dry-1") is None


def test_quote_branding_follows_business_and_edition():
    nelma = resolve_quote_billing({"billed_by": "nelmas_workroom"})
    assert nelma.name == "Nelma's Workroom"
    custom = resolve_quote_billing({"business_name": "McLean Atelier", "edition": "mclean"})
    assert custom.name == "McLean Atelier"
    assert "Empire" not in custom.name
    assert custom.address == ""
    assert custom.phone == ""
    assert custom.email == ""
    assert custom.website == ""
    assert custom.tagline == ""
    empire = resolve_quote_billing({"billed_by": "empire_workroom"})
    assert empire.name == "Empire Workroom"


def test_non_empire_pdf_never_shows_empire_contact(monkeypatch, tmp_path):
    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-2026-814",
        "customer_name": "Atelier Client",
        "status": "sent",
        "business_name": "McLean Atelier",
        "edition": "mclean",
        "line_items": [{"description": "Seat", "quantity": 1, "rate": 100, "amount": 100}],
        "total": 100,
        "deposit_percent": 50,
    })
    from pypdf import PdfReader
    text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    squashed = "".join(text.split()).upper()
    assert "MCLEANATELIER" in squashed or "MCLEAN ATELIER" in text.upper()
    assert "5124" not in text
    assert "Frolich" not in text
    assert "213-6484" not in text
    assert "workroom@empirebox.store" not in text.lower()
    assert "workroom.empirebox.store" not in text.lower()
    assert "Custom Window Treatments" not in text
    assert "EMPIREWORKROOM" not in squashed


def test_estimate_groups_by_area_and_uses_fractions():
    items = [
        {"description": 'U banquette — 46.5" long', "room": "U banquette", "quantity": 1, "rate": 2200, "amount": 2200, "sq_ft": 46.5, "price_per_sqft": 47.31},
        {"description": "Seat foam", "area": "U banquette", "quantity": 1, "rate": 180, "amount": 180},
        {"description": 'L banquette — 26.75"', "room": "L banquette", "quantity": 1, "rate": 1600, "amount": 1600},
    ]
    sections = group_estimate_sections(items)
    names = [n for n, _ in sections]
    assert "U banquette" in names
    assert "L banquette" in names
    assert inches_to_fractions('26.75" wide') == '26 3/4" wide'

    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-2026-813",
        "customer_name": "Client House",
        "status": "sent",
        "billed_by": "nelmas_workroom",
        "line_items": items,
        "total": 3980,
        "deposit_percent": 50,
    })
    from pypdf import PdfReader
    text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    flat = " ".join(text.split())
    assert "U BANQUETTE" in text.upper() or "U banquette" in flat
    assert "SUBTOTAL" in text.upper()
    assert "26 3/4" in text
    assert "46 1/2" in text or "46 4/8" in text
    assert "Grand total" in flat or "GRAND TOTAL" in text.upper()
    assert "Deposit" in flat
    assert "Balance" in flat
    squashed = "".join(text.split()).upper()
    assert "NELMA" in squashed
    assert "EMPIREWORKROOM" not in squashed
