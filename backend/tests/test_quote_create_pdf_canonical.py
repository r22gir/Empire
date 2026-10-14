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
    """JSON utcnow (no zone) can look 4h newer than a local quotes_v2 edit.

    A JSON snapshot that is actually older must not overwrite that edit.
    row_rev is the source of truth; naive clock strings are not compared.
    """
    _quotes(monkeypatch, tmp_path)
    from app.db.database import get_db
    from app.services.quote_service import ensure_row_rev_schema
    first = upsert_legacy_quote({
        "id": "newer-1",
        "quote_number": "EST-2026-815",
        "customer_name": "Canonical Name",
        "updated_at": "2026-10-14T12:00:00Z",
        "line_items": [{"description": "Seat", "quantity": 1, "rate": 10, "amount": 10}],
        "total": 10,
    })
    assert first["customer_name"] == "Canonical Name"
    with get_db() as conn:
        ensure_row_rev_schema(conn)
        # v2 edit at 18:00 UTC stored the way datetime.now() used to
        # (local EDT 14:00, no zone). JSON snapshot below is 16:00 UTC
        # naive — numerically later, actually two hours older.
        conn.execute(
            "UPDATE quotes_v2 SET customer_name = ?, updated_at = ?, row_rev = ? WHERE id = ?",
            ("Newer V2 Name", "2026-10-14T14:00:00", 5, "newer-1"),
        )
    again = upsert_legacy_quote({
        "id": "newer-1",
        "quote_number": "EST-2026-815",
        "customer_name": "Stale JSON Name",
        "updated_at": "2026-10-14T16:00:00",  # utcnow-style, no zone
        "row_rev": 1,
        "line_items": [{"description": "Other", "quantity": 2, "rate": 5, "amount": 10}],
        "total": 10,
    })
    assert again["customer_name"] == "Newer V2 Name"
    assert [i.get("description") for i in (again.get("line_items") or [])] == ["Seat"]
    assert int(again.get("row_rev") or 0) == 5


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


def test_line_sqft_always_divides_inches_by_144():
    from app.services.estimates.mclean_estimate_pdf import _line_sqft
    sq, _pps = _line_sqft({"width": 300, "height": 96})
    assert sq == 200.0
    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-2026-817",
        "customer_name": "Long Panel",
        "status": "sent",
        "line_items": [{
            "description": "Wide panel",
            "quantity": 1,
            "rate": 200,
            "amount": 200,
            "width": 300,
            "height": 96,
        }],
        "total": 200,
        "deposit_percent": 50,
    })
    from pypdf import PdfReader
    text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "200" in text
    assert "Sq ft" in text or "SQ FT" in text.upper() or "SQFT" in "".join(text.split()).upper()


def test_sqft_column_hidden_when_no_line_has_dimensions():
    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-2026-818",
        "customer_name": "No Dims",
        "status": "sent",
        "line_items": [{
            "description": "Labor only",
            "quantity": 2,
            "unit": "ea",
            "rate": 50,
            "amount": 100,
        }],
        "total": 100,
        "deposit_percent": 50,
    })
    from pypdf import PdfReader
    text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "Sq ft" not in text
    assert "SQFT" not in "".join(text.split()).upper()


def test_footer_omits_empty_parts_and_separators():
    from app.services.drawing.max_sheet_chrome import brand_footer
    assert brand_footer("ACME DRAPERY CO", "", "") == "ACME DRAPERY CO"
    assert "·" not in brand_footer("ACME DRAPERY CO", "", "")
    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-2026-819",
        "customer_name": "Atelier Client",
        "status": "sent",
        "business_name": "ACME DRAPERY CO",
        "edition": "acme",
        "line_items": [{"description": "Seat", "quantity": 1, "rate": 10, "amount": 10}],
        "total": 10,
        "deposit_percent": 50,
    })
    from pypdf import PdfReader
    text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "ACME DRAPERY CO · ·" not in text
    assert "ACMEDRAPERYCO··" not in "".join(text.split()).upper()


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


def _json_snapshot(quote_id, quote_number, status, row_rev, name="JSON Client"):
    return {
        "id": quote_id,
        "quote_number": quote_number,
        "customer_name": name,
        "status": status,
        "row_rev": row_rev,
        "updated_at": "2026-10-14T23:00:00Z",
        "line_items": [{"description": "Seat", "quantity": 1, "rate": 10, "amount": 10}],
        "total": 10,
    }


def test_portal_approve_then_json_keeps_approved(monkeypatch, tmp_path):
    """Portal SQL approval must survive a later JSON save of an earlier status."""
    _quotes(monkeypatch, tmp_path)
    from app.db.database import get_db
    from app.services.client_portal_service import (
        approve_quote_via_portal,
        generate_portal_link,
        init_portal_tables,
    )

    synced = upsert_legacy_quote(_json_snapshot(
        "portal-keep-1", "EST-2026-821", "sent", 1, "Portal Client",
    ))
    assert synced["status"] == "sent"
    prior_rev = int(synced.get("row_rev") or 0)

    init_portal_tables()
    link = generate_portal_link("cust-portal-1", quote_id="portal-keep-1")
    result = approve_quote_via_portal(link["token"])
    assert result["success"] is True

    approved = get_quote("portal-keep-1")
    assert approved["status"] == "approved"
    assert int(approved.get("row_rev") or 0) == prior_rev + 1
    assert str(approved.get("updated_at") or "").endswith("Z")

    again = upsert_legacy_quote(_json_snapshot(
        "portal-keep-1", "EST-2026-821", "draft", prior_rev + 50, "Stale JSON",
    ))
    assert again["status"] == "approved"
    assert again["customer_name"] == "Stale JSON"
    with get_db() as conn:
        row = conn.execute(
            "SELECT status, row_rev, updated_at FROM quotes_v2 WHERE id = ?",
            ("portal-keep-1",),
        ).fetchone()
        assert row["status"] == "approved"
        assert str(row["updated_at"]).endswith("Z")


def test_ordered_then_json_keeps_ordered(monkeypatch, tmp_path):
    """Lifecycle SQL 'ordered' must survive a later JSON save of an earlier status."""
    _quotes(monkeypatch, tmp_path)
    from app.services.lifecycle_service import _cascade_update_quote_to_ordered

    synced = upsert_legacy_quote(_json_snapshot(
        "ordered-keep-1", "EST-2026-822", "approved", 1, "Ordered Client",
    ))
    assert synced["status"] == "approved"
    prior_rev = int(synced.get("row_rev") or 0)

    assert _cascade_update_quote_to_ordered("ordered-keep-1") == "quote → ordered"
    ordered = get_quote("ordered-keep-1")
    assert ordered["status"] == "ordered"
    assert int(ordered.get("row_rev") or 0) == prior_rev + 1
    assert str(ordered.get("updated_at") or "").endswith("Z")

    again = upsert_legacy_quote(_json_snapshot(
        "ordered-keep-1", "EST-2026-822", "sent", prior_rev + 50, "Stale JSON",
    ))
    assert again["status"] == "ordered"
    assert again["customer_name"] == "Stale JSON"


def test_work_order_ordered_then_json_keeps_ordered(monkeypatch, tmp_path):
    """Work-order SQL 'ordered' must survive a later JSON save of draft."""
    _quotes(monkeypatch, tmp_path)
    from app.services.work_order_service import create_work_order_from_quote

    synced = upsert_legacy_quote(_json_snapshot(
        "wo-keep-1", "EST-2026-823", "approved", 1, "WO Client",
    ))
    assert synced["status"] == "approved"
    create_work_order_from_quote("wo-keep-1")
    assert get_quote("wo-keep-1")["status"] == "ordered"

    again = upsert_legacy_quote(_json_snapshot(
        "wo-keep-1", "EST-2026-823", "draft", 99, "Stale JSON",
    ))
    assert again["status"] == "ordered"


def test_apply_quote_v2_update_stamps_utc_and_bumps_rev(monkeypatch, tmp_path):
    _quotes(monkeypatch, tmp_path)
    from app.db.database import get_db
    from app.services.quote_service import apply_quote_v2_update

    first = upsert_legacy_quote(_json_snapshot(
        "helper-1", "EST-2026-824", "draft", 1,
    ))
    prior = int(first.get("row_rev") or 0)
    with get_db() as conn:
        stamp = apply_quote_v2_update(conn, "helper-1", {"notes": "helper"})
    row = get_quote("helper-1")
    assert stamp.endswith("Z")
    assert str(row.get("updated_at") or "").endswith("Z")
    assert int(row.get("row_rev") or 0) == prior + 1
    assert row["notes"] == "helper"


def test_naive_local_updated_at_converts_to_utc(monkeypatch, tmp_path):
    _quotes(monkeypatch, tmp_path)
    from app.db.database import get_db
    from app.services.quote_service import convert_naive_quote_timestamps_to_utc

    upsert_legacy_quote(_json_snapshot("naive-ts-1", "EST-2026-825", "draft", 1))
    with get_db() as conn:
        conn.execute(
            "UPDATE quotes_v2 SET updated_at = ?, created_at = ? WHERE id = ?",
            ("2026-10-14T14:00:00", "2026-10-14T14:00:00", "naive-ts-1"),
        )
        result = convert_naive_quote_timestamps_to_utc(conn)
    assert result["converted"] >= 1
    row = get_quote("naive-ts-1")
    # 14:00 America/New_York on 2026-10-14 is EDT (UTC-4) → 18:00Z
    assert row["updated_at"] == "2026-10-14T18:00:00Z"
    assert row["created_at"] == "2026-10-14T18:00:00Z"
