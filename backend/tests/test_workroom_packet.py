"""Header-B estimate, presentation, and workroom pricing rules."""
from __future__ import annotations

import io

from PIL import Image

from app.services.estimates.workroom_packet import (
    build_packet,
    draft_packet,
    render_packet_pdfs,
    sample_phase1,
    wants_packet,
)
from app.services.pricing.workroom_rules import (
    install_price,
    panel_widths,
    reload_rules,
    reset_rules,
    set_rule,
    sheer_widths,
)


def _text(pdf: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)


def test_width_math_matches_the_phase1_reference():
    reset_rules()
    living = panel_widths(160, 2)
    assert living["per_panel"] == 3.5
    assert living["total"] == 7
    office = panel_widths(143.75, 2)
    assert office["fabric_in"] == 299
    assert office["per_panel"] == 3.5
    sheer = sheer_widths(96)
    assert sheer["full"] == 4.5
    assert sheer["charged"] == 2.5
    assert install_price(96)["amount"] == 145
    assert install_price(160)["amount"] == 251.67
    assert install_price(160, flat=245)["amount"] == 245


def test_rules_are_editable_and_reset():
    reset_rules()
    try:
        set_rule("install_per_window", 160)
        assert install_price(72)["amount"] == 160
    finally:
        reset_rules()
    assert install_price(72)["amount"] == 145


def test_workroom_rules_persist_to_sqlite(isolated_empire_db):
    import sqlite3

    reset_rules()
    try:
        set_rule("install_per_window", 200.0)
        set_rule("baton_each", 40.0)
        reloaded = reload_rules()
        assert reloaded["install_per_window"] == 200.0
        assert reloaded["baton_each"] == 40.0
        assert install_price(72)["amount"] == 200.0

        conn = sqlite3.connect(isolated_empire_db)
        rows = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT rule_key, value FROM workroom_pricing_rules ORDER BY rule_key"
            ).fetchall()
        }
        conn.close()
        assert rows["install_per_window"] == 200.0
        assert rows["baton_each"] == 40.0
    finally:
        reset_rules()


def test_sample_packet_matches_reference_totals():
    reset_rules()
    packet = build_packet(sample_phase1())
    assert packet["total"] == 4759.96
    assert packet["deposit"] == 2379.98
    assert packet["payment_line"] == "Pay deposit online: [Square payment link]"
    assert packet["sent"] is False
    assert packet["status"] == "draft"
    living = packet["rooms"][0]
    assert living["subtotal"] == 2585.98
    assert [group["name"] for group in living["groups"]] == [
        "Installation", "Preparation", "Construction", "Materials",
    ]
    materials = " ".join(line["description"] for line in living["groups"][-1]["lines"])
    assert "carriers" in materials.lower()
    assert "Batons" in materials
    assert "Living Room" not in materials


def test_estimate_header_b_and_presentation(tmp_path):
    reset_rules()
    fabric = tmp_path / "fabric.png"
    Image.new("RGB", (80, 120), (180, 150, 110)).save(fabric)
    photo = tmp_path / "photo.png"
    Image.new("RGB", (240, 160), (90, 110, 140)).save(photo)
    spec = sample_phase1()
    spec["openings"][0]["photo"] = str(photo)
    spec["openings"][0]["fabric_crop"] = str(fabric)
    packet = build_packet(spec)
    estimate, presentation = render_packet_pdfs(packet)
    est = _text(estimate)
    pres = _text(presentation)
    assert "Nelma's Workroom" in est
    assert "by Empire" in est
    assert "(703) 623-9203" in est
    assert "workroom.empirebox.store" in est
    assert "PREPARED FOR" in est and "PROJECT" in est
    assert "9408 Old Courthouse Rd" in est
    assert "LIVING ROOM" in est and "OFFICE" in est
    assert "1. Installation" in est
    assert "4. Materials" in est
    assert "Subtotal" in est
    assert "$4,759.96" in est
    assert "$2,379.98" in est
    assert "[Square payment link]" in est
    assert "Rafael" not in est and "Rafael" not in pres
    assert "studio.empirebox.store" not in est
    assert "OPENING SCHEDULE" in pres
    assert "STATIONARY" in pres
    assert "RIPPLEFOLD" in pres
    assert "48" in pres
    from pypdf import PdfReader
    assert len(PdfReader(io.BytesIO(presentation)).pages) == 4


def test_empire_brand_uses_the_empire_phone():
    reset_rules()
    packet = build_packet(sample_phase1(billed_by="empire_workroom"))
    text = _text(render_packet_pdfs(packet)[0])
    assert "Empire Workroom" in text
    assert "(703) 213-6484" in text
    assert "(703) 623-9203" not in text


def test_chat_tool_drafts_and_does_not_send():
    reset_rules()
    from app.services.max.tool_executor import _draft_estimate_and_presentation
    spec = sample_phase1()
    result = _draft_estimate_and_presentation({
        "billed_by": spec["billed_by"],
        "prepared_for": spec["prepared_for"],
        "project": spec["project"],
        "notes": spec["notes"],
        "date": spec["date"],
        "openings": spec["openings"],
        "save_quote": True,
    })
    assert result.success, result.error
    assert result.result["sent"] is False
    assert result.result["status"] == "draft"
    assert result.result["project_address"] == "9408 Old Courthouse Rd, Tysons, VA"
    assert result.result["total"] == 4759.96
    from app.services.quote_service import get_quote
    quote = get_quote(result.result["quote_id"])
    assert quote["status"] == "draft"
    assert quote["project_address"] == "9408 Old Courthouse Rd, Tysons, VA"
    assert quote.get("sent_at") in (None, "")


def test_phrase_is_recognized():
    assert wants_packet("make the estimate and presentation for job 297")
    assert not wants_packet("draw a ripplefold shop drawing")


def test_reline_without_bump_option():
    """Rafael 10/4/2026: 'Re-line with lining (no bump)' at $125/width, lining only, same width count."""
    from app.services.estimates.workroom_packet import price_opening
    reset_rules()
    std = price_opening({"room": "Living Room", "width": 160, "height": 119.75, "panels": 2})
    nob = price_opening({"room": "Living Room", "width": 160, "height": 119.75, "panels": 2, "bump": False})
    alt = price_opening({"room": "Living Room", "width": 160, "height": 119.75, "panels": 2, "reline_type": "no bump"})

    def rows(op):
        return [r for g in op["groups"] for r in g["lines"]]

    std_reline = next(r for r in rows(std) if r["description"].startswith("Re-line"))
    nob_reline = next(r for r in rows(nob) if r["description"].startswith("Re-line"))
    assert std_reline["description"].startswith("Re-line with lining and bump")
    assert std_reline["rate"] == 150.0 and std_reline["quantity"] == 7
    assert nob_reline["description"].startswith("Re-line with lining (no bump)")
    assert nob_reline["rate"] == 125.0 and nob_reline["quantity"] == std_reline["quantity"] == 7
    assert nob_reline["amount"] == 875.0
    assert any(r["description"].startswith("Bump interlining") for r in rows(std))
    assert not any("Bump" in r["description"] for r in rows(nob))
    assert any(r["description"].startswith("Lining ·") for r in rows(nob))
    assert nob["bump"] is False and std["bump"] is True
    assert [r["description"] for r in rows(alt)] == [r["description"] for r in rows(nob)]
    assert round(std["subtotal"] - nob["subtotal"], 2) == round(25 * 7 + std["yards"] * 12.95, 2)
