"""Rafael 2026-10-23 Willard / REV C estimate format. Mock data only."""
from __future__ import annotations

import io

from app.services.estimates.rafael_format import (
    CLIENT_FACTOR,
    FORMAT_ID,
    MOCK_BASE_TOTAL,
    MOCK_CLIENT_TOTAL,
    MOCK_DESIGNER_SHARE,
    MOCK_FINISHED_LENGTH_IN,
    MOCK_MAIN_WIDTH_IN,
    MOCK_SHEER_COVERAGE_IN,
    apply_designer,
    designer_name,
    format_item_list,
    format_rate_label,
    group_willard_areas,
    install_section_price,
    is_com_line,
    mock_drapery_spec,
    money_round,
    normalize_variant,
    scrub_brands,
    simple_area_blurb,
    simple_com_line,
    simple_includes_line,
    totals_from_areas,
    uses_willard_layout,
)
from app.services.estimates.workroom_packet import (
    build_packet,
    is_new_fabrication,
    price_opening,
)
from app.services.pricing.workroom_rules import (
    new_fab_widths,
    reset_rules,
    track_feet,
)


def _pdf_text(pdf: bytes) -> str:
    from pypdf import PdfReader
    raw = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    # Landscape chrome letter-spaces the header; collapse for assertions.
    return raw.replace("\n", "")


def _all_lines(packet: dict) -> list[dict]:
    lines = []
    for area in packet.get("areas") or []:
        for group in area.get("groups") or []:
            lines.extend(group.get("lines") or [])
    return lines


def test_new_fab_width_math_matches_rev_c_fixture():
    reset_rules()
    main = new_fab_widths(MOCK_MAIN_WIDTH_IN, fullness=2.5, goods_in=54, panels=2)
    assert main["total"] == 12
    assert main["per_panel"] == 6
    sheers = new_fab_widths(MOCK_SHEER_COVERAGE_IN, fullness=2.5, goods_in=110, panels=1)
    assert sheers["total"] == 5
    assert track_feet(MOCK_MAIN_WIDTH_IN) == 21
    assert track_feet(MOCK_SHEER_COVERAGE_IN) == 16


def test_new_fab_opening_reproduces_fixture_totals():
    reset_rules()
    spec = mock_drapery_spec()
    opening = spec["openings"][0]
    assert is_new_fabrication(opening)
    priced = price_opening(opening)
    assert priced["subtotal"] == MOCK_BASE_TOTAL
    items = [ln for a in priced["areas"] for g in a["groups"] for ln in g["lines"]]
    labels = [(ln["area"][:1], ln["group"], ln["item"]) for ln in items]
    assert ("A", "Labor", "Drapes") in [(a, g, i) for a, g, i in labels]
    assert any(ln["item"] == "Sheers" and ln["quantity"] == 5 for ln in items)
    assert any(ln["item"] == "Drapes" and ln["quantity"] == 12 for ln in items)
    tracks = [ln for ln in items if ln["item"] == "Track"]
    assert len(tracks) == 2
    assert {ln["quantity"] for ln in tracks} == {21, 16}
    assert all(ln["unit"] == "ft" for ln in tracks)
    installs = [ln for ln in items if ln["item"] == "Install"]
    assert len(installs) == 2
    assert {ln["quantity"] for ln in installs} == {21, 16}
    assert not any("hr" == (ln.get("unit") or "") for ln in items)
    assert not any("re-center" in str(ln.get("description") or "").lower() for ln in items)
    coms = [ln for ln in items if is_com_line(ln)]
    assert {ln["item"] for ln in coms} >= {"Fabric", "Hem"}
    assert all(ln.get("amount") in (None, 0) for ln in coms)
    packet = build_packet(spec)
    assert packet["base_total"] == MOCK_BASE_TOTAL
    assert packet["client_total"] == MOCK_CLIENT_TOTAL
    assert packet["designer_share_20pct"] == MOCK_DESIGNER_SHARE
    assert packet["estimate_format"] == FORMAT_ID
    assert abs(packet["client_total"] - packet["base_total"] * CLIENT_FACTOR) < 0.02


def test_willard_client_and_internal_pdf_columns():
    reset_rules()
    from app.services.estimates.willard_estimate import (
        render_willard_estimate,
        render_willard_pair,
    )
    from pypdf import PdfReader

    packet = build_packet(mock_drapery_spec())
    simple_pdf, internal_pdf = render_willard_pair(packet)
    detailed_pdf = render_willard_estimate(packet, variant="client")
    simple = _pdf_text(simple_pdf)
    detailed = _pdf_text(detailed_pdf)
    internal = _pdf_text(internal_pdf)
    assert "ITEM" in detailed and "DESCRIPTION" in detailed and "QTY" in detailed
    assert "TOTAL" in detailed
    assert "MARKUP 20%" not in detailed
    assert "MARKUP20%(DESIGNER)" not in detailed.replace(" ", "")
    assert "MARKUP" in internal and "AMOUNT" in internal and "RATE" in internal
    assert "$245/8 ft" in internal and "$325/8 ft" in internal
    assert "COM" in detailed and "COM" in internal
    assert "MARKUP 20% (DESIGNER)" in internal
    assert f"${MOCK_CLIENT_TOTAL:,.2f}" in detailed
    assert f"${MOCK_CLIENT_TOTAL:,.2f}" in simple
    assert f"${MOCK_BASE_TOTAL:,.2f}" in internal
    assert f"${MOCK_CLIENT_TOTAL:,.2f}" in internal
    assert "track re-center" not in detailed.lower()
    assert "Rafael" not in detailed and "Rafael" not in internal
    assert "Maggie O" not in detailed and "Le Midi" not in detailed
    assert len(PdfReader(io.BytesIO(simple_pdf)).pages) == 1
    assert "A. Main Drapery" in simple
    assert "lined ripplefold" in simple
    assert "249 5/16" in simple
    assert "fabrication, track and installation" in simple
    assert "Includes" in simple
    assert "Fabric provided by client" in simple
    assert "GRAND TOTAL" in simple
    assert "Deposit (50%)" in simple or "DEPOSIT" in simple.upper()
    assert "BALANCE" in simple.upper()
    assert "QTY" not in simple
    assert "RATE" not in simple
    assert "MARKUP" not in simple
    assert "LABOR" not in simple
    assert "widths" not in simple.lower()
    assert " yd" not in simple.lower()
    assert normalize_variant(None) == "client_simple"
    assert normalize_variant("client") == "client"


def test_draft_estimate_tool_is_the_max_path(isolated_empire_db):
    reset_rules()
    from app.services.max.tool_executor import _draft_estimate_and_presentation
    from app.services.quote_pdf_service import generate_quote_pdf
    from app.services.quote_service import get_quote

    spec = mock_drapery_spec()
    result = _draft_estimate_and_presentation({
        "billed_by": spec["billed_by"],
        "prepared_for": spec["prepared_for"],
        "project": spec["project"],
        "notes": spec["notes"],
        "date": spec["date"],
        "quote_number": spec["quote_number"],
        "openings": spec["openings"],
        "client_factor": spec["client_factor"],
        "designer_name": spec["designer_name"],
        "save_quote": True,
    })
    assert result.success, result.error
    assert result.result["sent"] is False
    assert result.result["base_total"] == MOCK_BASE_TOTAL
    assert result.result["client_total"] == MOCK_CLIENT_TOTAL
    assert result.result["designer_share_20pct"] == MOCK_DESIGNER_SHARE
    assert result.result["estimate_bytes"] > 1000
    assert result.result["estimate_internal_bytes"] > 1000
    quote = get_quote(result.result["quote_id"])
    assert uses_willard_layout(quote)
    assert (quote.get("metadata") or {}).get("estimate_format") == FORMAT_ID
    default = _pdf_text(generate_quote_pdf(quote["id"]))
    client = _pdf_text(generate_quote_pdf(quote["id"], variant="client"))
    internal = _pdf_text(generate_quote_pdf(quote["id"], variant="internal"))
    assert "Fabric provided by client" in default
    assert "QTY" not in default
    assert "LABOR" in client and "MATERIALS" in client and "INSTALLATION" in client
    assert "COM" in client
    assert f"${MOCK_CLIENT_TOTAL:,.2f}" in client
    assert f"${MOCK_CLIENT_TOTAL:,.2f}" in default
    assert "MARKUP 20% (DESIGNER)" in internal
    assert "$245/8 ft" in internal
    assert "Rafael" not in client
    assert "Rafael" not in default


def test_upholstery_stays_mclean():
    quote = {
        "line_items": [
            {"room": "U banquette", "description": "Seat", "sq_ft": 10, "price_per_sqft": 40},
        ]
    }
    assert uses_willard_layout(quote) is False


def test_scrub_brands_keeps_fabric_code():
    assert "Schumacher" not in scrub_brands("Schumacher V203-Ivory face")
    assert "V203-Ivory" in scrub_brands("Schumacher V203-Ivory face")


def test_email_item_list_one_per_line():
    text = format_item_list(["Main drapery", "Sheers, batons, track"])
    assert "\n" in text
    assert text.count("\n") >= 2


def test_rate_labels_are_section_rates():
    assert format_rate_label({
        "item": "Install", "unit": "ft", "base_rate": 30.625, "base_amount": 245,
    }) == "$245/8 ft"
    assert format_rate_label({
        "item": "Track", "unit": "ft", "base_rate": 40.625, "base_amount": 325,
    }) == "$325/8 ft"


def test_group_willard_areas_orders_labor_materials_installation():
    areas = group_willard_areas([
        {"area": "Main Drapery", "group": "Installation", "description": "Install", "amount": 10},
        {"area": "Main Drapery", "group": "Labor", "description": "Drapes", "amount": 20},
        {"area": "Sheers", "group": "Materials", "description": "Track", "amount": 5},
    ])
    assert [a["name"] for a in areas] == ["Main Drapery", "Sheers"]
    assert [g["name"] for g in areas[0]["groups"]] == ["Labor", "Installation"]


def test_money_round_is_half_up_everywhere():
    reset_rules()
    assert money_round(853.125) == 853.13
    assert money_round(643.125) == 643.13
    assert money_round(1.225) == 1.23
    assert apply_designer(4740.36) == 5688.43
    qty_rate = money_round(21 * 40.625)
    assert qty_rate == 853.13
    areas = group_willard_areas([
        {"area": "Main Drapery", "group": "Labor", "description": "Drapes",
         "quantity": 21, "rate": 40.625},
        {"area": "Main Drapery", "group": "Installation", "description": "Install",
         "quantity": 21, "rate": 30.625},
    ])
    assert areas[0]["groups"][0]["subtotal"] == 853.13
    assert areas[0]["groups"][1]["subtotal"] == 643.13
    assert areas[0]["subtotal"] == 1496.26
    totals = totals_from_areas(areas, {"deposit_percent": 50})
    assert totals["base"] == 1496.26
    assert totals["client"] == money_round(1496.26 * CLIENT_FACTOR)
    assert totals["deposit"] == money_round(totals["client"] * 0.5)
    assert totals["balance"] == money_round(totals["client"] - totals["deposit"])
    assert totals["designer"] == apply_designer(1496.26)
    flat = install_section_price(96, flat=245.125)
    assert flat["amount"] == 245.13
    hourly = install_section_price(96, hourly=1, override=True)
    assert hourly["method"] == "hourly_override"
    ignored = install_section_price(96, hourly=1, override=False)
    assert ignored["method"] == "section_prorate"
    packet = build_packet(mock_drapery_spec())
    assert packet["designer_share_20pct"] == MOCK_DESIGNER_SHARE
    from app.services.estimates.willard_estimate import render_willard_estimate
    from app.services.estimates.rafael_format import VARIANT_INTERNAL
    internal = _pdf_text(render_willard_estimate(packet, variant=VARIANT_INTERNAL))
    assert f"${MOCK_DESIGNER_SHARE:,.2f}" in internal


def test_designer_name_comes_from_metadata_only():
    assert designer_name({
        "customer_name": "Maggie O'Neil",
        "prepared_for": {"company": "Maggie O'Neil Interiors"},
    }) == "Designer"
    assert designer_name({
        "metadata": {"designer_name": "Ada"},
        "customer_name": "Maggie O'Neil",
    }) == "Ada"
    assert designer_name({
        "designer_name": "Ada",
        "designer_markup_factor": 1.1,
    }) == "Ada"


def test_default_tool_output_has_no_hourly_line(isolated_empire_db):
    reset_rules()
    from app.services.max.tool_executor import _draft_estimate_and_presentation

    spec = mock_drapery_spec()
    poisoned = dict(spec["openings"][0])
    poisoned["track_hours"] = 3
    poisoned["install_hours"] = 2
    result = _draft_estimate_and_presentation({
        "billed_by": spec["billed_by"],
        "prepared_for": spec["prepared_for"],
        "project": spec["project"],
        "notes": spec["notes"],
        "date": spec["date"],
        "quote_number": spec["quote_number"],
        "openings": [poisoned],
        "save_quote": True,
    })
    assert result.success, result.error
    from app.services.quote_service import get_quote
    quote = get_quote(result.result["quote_id"])
    blob = " ".join(
        str(it.get("description") or "") for it in (quote.get("line_items") or [])
    ).lower()
    assert "hr @" not in blob
    assert "hourly" not in blob
    assert "track re-center" not in blob
    packet = build_packet(mock_drapery_spec())
    lines = _all_lines(packet)
    assert not any((ln.get("unit") or "") in {"hr", "hour", "hours"} for ln in lines)
    assert not any("hr @" in str(ln.get("description") or "").lower() for ln in lines)


def test_client_simple_blurbs_and_default_variant():
    reset_rules()
    from app.services.estimates.willard_estimate import render_willard_estimate
    from pypdf import PdfReader

    packet = build_packet(mock_drapery_spec())
    areas = packet["areas"]
    main = simple_area_blurb(areas[0])
    sheers = simple_area_blurb(areas[1])
    assert main.startswith("A. Main Drapery: lined ripplefold")
    assert '249 5/16"' in main
    assert main.endswith("fabrication, track and installation")
    assert sheers.startswith("B. Sheers: ripplefold")
    assert '189 3/8"' in sheers
    assert "Includes track, installation and removal." == simple_includes_line(areas)
    assert simple_com_line(areas) == "Fabric provided by client"
    default_pdf = render_willard_estimate(packet)
    named = render_willard_estimate(packet, variant="client_simple")
    assert _pdf_text(default_pdf) == _pdf_text(named)
    assert len(PdfReader(io.BytesIO(default_pdf)).pages) == 1
    text = _pdf_text(default_pdf)
    assert "Labor" not in text
    assert "Materials" not in text
    assert "Installation subtotal" not in text
    assert "MARKUP" not in text
