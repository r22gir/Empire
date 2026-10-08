"""2026-10-08 (Rafael): upholstery estimate format.

Grouped by area (U banquette, L banquette, material); columns Description | Qty | Unit |
Sq ft | Price | Total; subtotal per area, then grand total, deposit, balance; measurements in
the sub-text in fractions. Runs on the isolated test DB (never live data).
"""
import subprocess
import tempfile

from app.services.estimates.mclean_estimate_pdf import inches_to_fractions, render_mclean_estimate_bytes
from app.services.max.tool_executor import execute_tool
from app.services.quote_service import get_quote


def _lines():
    back = '12" channels'
    return [
        {"room": "U banquette", "description": f'Seat back — main\n249.75" run · back 26.75" · {back}',
         "sq_ft": 46.39, "price_per_sqft": 65},
        {"room": "U banquette", "description": 'Seat cushion — main\n249 3/4" run · depth 18" · plain cognac',
         "sq_ft": 31.22, "price_per_sqft": 45},
        {"room": "L banquette", "description": f'Seat back — long leg\n107 3/4" run · back 26 3/4" · {back}',
         "sq_ft": 20.02, "price_per_sqft": 65},
        {"room": "Material", "category": "manual_line", "description": "Cognac commercial vinyl\nBacks and seats",
         "quantity": 1, "unit": "lot", "unit_price": 1785.88},
    ]


def _pdf_text(pdf: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
        fh.write(pdf)
        fh.flush()
        return subprocess.run(["pdftotext", "-layout", fh.name, "-"], capture_output=True, text=True).stdout


def test_fractions_helper():
    assert inches_to_fractions('back 26.75" · run 249.75 in') == 'back 26 3/4" · run 249 3/4 in'
    assert inches_to_fractions('12.1875"') == '12 3/16"'
    assert inches_to_fractions("29.5 yd") == "29.5 yd"  # yards are not inches


def test_create_and_render_grouped_sqft_estimate(isolated_empire_db):
    res = execute_tool({"tool": "create_engine_quote", "customer_name": "Test Banquette Co",
                        "line_items": _lines()})
    assert res.success, res.error
    q = get_quote(res.result["quote_id"])
    items = q["line_items"]
    assert [i.get("room") for i in items] == ["U banquette", "U banquette", "L banquette", "Material"]
    assert round(items[0]["subtotal"], 2) == round(46.39 * 65, 2)
    assert round(items[1]["subtotal"], 2) == round(31.22 * 45, 2)
    text = _pdf_text(render_mclean_estimate_bytes(q))
    for col in ("Description", "Qty", "Unit", "Sq ft", "Price", "Total"):
        assert col in text
    for area in ("U BANQUETTE", "L BANQUETTE", "MATERIAL"):
        assert area in text.upper()
    assert "46.39" in text and "65.00" in text and "$3,015.35" in text
    u_sub = round(46.39 * 65 + 31.22 * 45, 2)
    assert f"${u_sub:,.2f}" in text  # U banquette subtotal
    assert "SUBTOTAL" in text.upper() and "TOTAL" in text.upper()
    assert "Deposit" in text and "Balance" in text
    assert '249 3/4"' in text and '26 3/4"' in text  # decimals turned into plain fractions in the sub-text
    assert "249.75" not in text and "26.75" not in text
    assert not any(g in text for g in "¼½¾⅛⅜⅝⅞")
    # totals: area subtotals in the table, then Grand total / Deposit / Balance (no "Quoted / already given")
    assert "Grand total" in text and "Deposit (50%)" in text and "Balance" in text
    assert "already given" not in text and "priced / quoted only" not in text


def test_plain_fractions_in_replies():
    from app.services.max.answer_policy import clean_reply
    from app.services.pricing.dimensions import plain_fractions, format_inches
    assert plain_fractions('26¾" back, ½" ply') == '26 3/4" back, 1/2" ply'
    assert format_inches(14.1875) == '14 3/16"'
    assert '32 3/4"' in clean_reply('Cut each channel at 32¾" minimum.')
