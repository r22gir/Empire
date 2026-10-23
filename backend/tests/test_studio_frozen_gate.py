"""Studio frozen suite — quotes, drawings, invoices.

Small, strict, fast. Mock data only. Never talks to live empire.db.
Never sends email / WhatsApp / SMS / Telegram.

These assertions are the Studio contract. Night Lab / self-improvement /
auto-fix must pass this file TWICE before a change is kept.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.services.invoice_pdf_service import (
    client_visible_line_description,
    subtotal_from_line_items,
)
from app.services.max.quoteiq_chain import (
    draft_quote_only,
    looks_like_quote_request,
    parse_job_dimensions,
)
from app.services.max.studio_frozen_gate import frozen_mutation_ok
from app.services.drawing.job_drawing import resolve_internal_fabric
from app.services.vision.bench_cut_list import (
    FABRIC_LABEL,
    FOAM_LABEL,
    WOOD_LABEL,
    format_cut_inches,
    generate_cut_list,
)
from app.services.workroom_quote_commerce import compute_estimate_totals


JOB = (
    "Quote for Frozen Client. Straight bench 48 1/2 inches long, "
    "18 inches deep, 12 inch channels, 2 inch foam."
)

REGISTRY = [
    {"code": "V001-Raven", "color": "Black"},
    {"code": "V003-Cognac", "color": "Cognac"},
    {"code": "V008-Bittersweet", "color": "Bittersweet"},
]


def test_mutation_hook_stays_clean():
    assert frozen_mutation_ok() is True


# ── Quotes ──────────────────────────────────────────────────────────


def test_quote_request_needs_phrase_and_dimension():
    assert looks_like_quote_request(JOB) is True
    assert looks_like_quote_request("the roman shades are 34 1/2 x 60") is False
    assert looks_like_quote_request("please quote this job") is False


def test_quote_totals_from_mock_lines_are_exact():
    totals = compute_estimate_totals(
        line_items=[
            {"description": "Seat run", "quantity": 2, "rate": 65, "amount": 130},
            {"description": "Back run", "quantity": "1", "rate": 80, "amount": 80},
        ],
        tax_rate=0,
        discount_amount=10,
        discount_type="dollar",
        deposit_percent=50,
        deposit_paid=0,
    )
    assert totals["items_subtotal"] == 210.0
    assert totals["subtotal"] == 210.0
    assert totals["discount_amount"] == 10.0
    assert totals["total"] == 200.0
    assert totals["deposit_amount"] == 100.0
    assert totals["balance_due"] == 200.0


def test_quote_dimensions_are_fractions_never_decimals():
    parsed = parse_job_dimensions({
        "intake": {
            "message": JOB,
            "item_type": "bench",
            "width_in": 48.5,
            "depth_in": 18,
            "channel_width_in": 12,
            "foam_thickness_in": 2,
            "panel_style": "channel",
        },
        "message": JOB,
    })
    blob = " ".join(parsed["dimensions"].values())
    assert parsed["measurements_format"] == "fractions"
    assert "48 1/2" in blob
    assert "48.5" not in blob
    assert ".5\"" not in blob


def test_quote_channel_cuts_label_wood_foam_and_fabric_separately():
    parsed = parse_job_dimensions({
        "intake": {
            "message": JOB,
            "item_type": "bench",
            "width_in": 48.5,
            "depth_in": 18,
            "channel_width_in": 12,
            "foam_thickness_in": 2,
            "panel_style": "channel",
        },
        "message": JOB,
    })
    cuts = parsed["channel_cuts"]
    assert cuts
    row = cuts[0]
    assert row["wood_cut"] == row["foam_cut"]
    assert row["fabric_cut"] != row["wood_cut"]
    assert '"' in row["wood_cut"]
    assert "." not in row["wood_cut"].replace(" x ", "")
    assert "." not in row["fabric_cut"].split("(")[0].replace(" x ", "")
    assert "12" in row["wood_cut"]


def test_quote_draft_never_sends():
    out = draft_quote_only({
        "message": JOB,
        "intake": {"message": JOB, "customer_name": "Frozen Client"},
        "dimensions": {},
        "pricing": {},
    })
    assert out["sent"] is False
    assert out.get("created") is False
    assert out.get("status") == "incomplete"


# ── Drawings ────────────────────────────────────────────────────────


def test_drawing_inches_are_fractions_only():
    assert format_cut_inches(22.5) == '22 1/2"'
    assert format_cut_inches(18) == '18"'
    assert format_cut_inches(0.5) == '1/2"'
    assert format_cut_inches(6.25) == '6 1/4"'
    for value in (22.5, 18, 0.5, 6.25, 48.5):
        text = format_cut_inches(value)
        assert "." not in text
        assert "-" not in text
        assert text.endswith('"')


def test_drawing_wood_foam_and_fabric_are_separately_labeled():
    model = SimpleNamespace(
        name="Frozen bench",
        width=96,
        depth=22.5,
        seat_h=18,
        back_h=18,
        bench_type="straight",
        foam_thickness_in=2.0,
    )
    cuts = generate_cut_list(model)
    assert cuts["wood"] and cuts["foam"] and cuts["fabric"]
    wood, foam, fabric = cuts["wood"][0], cuts["foam"][0], cuts["fabric"][0]
    assert wood["label"] == WOOD_LABEL == "WOOD CUT — TRUE SIZE"
    assert foam["label"] == FOAM_LABEL == "FOAM CUT — MATCHES WOOD"
    assert fabric["label"] == FABRIC_LABEL == "FABRIC CUT — LABELED SEPARATELY"
    assert wood["size"] == foam["size"] == '22 1/2" × 96"'
    assert fabric["size"] != wood["size"]
    assert "." not in wood["size"]
    assert "." not in fabric["size"]
    assert "-" not in wood["size"]
    assert "-" not in fabric["size"]


def test_drawing_uses_fabric_codes_not_brands():
    raven = resolve_internal_fabric("Black", registry_rows=REGISTRY)
    assert raven["code"] == "V001-Raven"
    assert "kravet" not in (raven["label"] or "").lower()
    assert "spradling" not in (raven["label"] or "").lower()
    assert "fabricut" not in (raven["label"] or "").lower()
    cognac = resolve_internal_fabric("V003-Cognac", registry_rows=REGISTRY)
    assert cognac["code"] == "V003-Cognac"
    branded = resolve_internal_fabric("Kravet V639 Navy Velvet", registry_rows=REGISTRY)
    blob = " ".join(str(v or "") for v in branded.values()).lower()
    assert "kravet" not in blob
    assert branded.get("code") != "Kravet V639 Navy Velvet"


# ── Invoices ────────────────────────────────────────────────────────


def test_invoice_subtotal_from_mock_lines():
    lines = [
        {"description": "U banquette seat", "quantity": 1, "unit_price": 150, "total": 150},
        {"description": "Material lot", "quantity": 1, "unit_price": 150, "amount": 150},
    ]
    assert subtotal_from_line_items(lines) == 300.0


def test_invoice_hides_internal_allocation_math():
    visible = client_visible_line_description({
        "description": "Seat back\nU share, 40% of 12 yd",
    })
    assert "Seat back" in visible
    assert "40%" not in visible
    assert "share" not in visible.lower()


def test_invoice_deposit_and_balance_from_mock_totals():
    totals = compute_estimate_totals(
        line_items=[{"quantity": 1, "rate": 400, "amount": 400}],
        tax_rate=0,
        deposit_percent=50,
        deposit_paid=100,
    )
    assert totals["total"] == 400.0
    assert totals["deposit_amount"] == 200.0
    assert totals["deposit_paid"] == 100.0
    assert totals["balance_due"] == 300.0
    assert "sent" not in totals
