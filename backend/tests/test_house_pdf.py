"""House-format PDF unity: one cream/ink/gold sheet, inch fractions."""
from app.services.house_pdf import (
    CREAM,
    GOLD,
    INK,
    format_inches,
    render_estimate,
    render_idea_sheet,
    render_measurements,
    render_shop_ticket,
    size_label,
)
from app.services.vision.parametric_templates import render_template_instance


def test_format_inches_uses_fractions_not_decimals():
    assert format_inches(48) == '48"'
    assert format_inches(48.5) == '48 1/2"'
    assert format_inches(4.75) == '4 3/4"'
    assert format_inches(36.125) == '36 1/8"'
    assert format_inches(0.375) == '3/8"'
    assert format_inches(4.5) == '4 1/2"'
    assert format_inches("48.25") == '48 1/4"'
    assert format_inches("") == "—"
    assert format_inches(None) == "—"
    assert "." not in format_inches(48.5)


def test_size_label_skips_blanks():
    assert size_label(48.5, 84, None) == '48 1/2" W × 84" H'
    assert size_label(0, 0, 0) == "—"


def test_estimate_shop_and_idea_share_house_colors():
    quote = {
        "quote_number": "EST-DRAFT",
        "customer_name": "Ada Lovelace",
        "rooms": [{
            "name": "Library",
            "windows": [{
                "name": "Bay",
                "width": 48.5,
                "height": 84,
                "treatmentType": "pinch-pleat",
                "quantity": 2,
            }],
        }],
        "line_items": [{
            "description": "Pinch pleat panels",
            "quantity": 2,
            "unit_price": 400,
            "subtotal": 800,
            "width": 48.5,
            "height": 84,
        }],
        "subtotal": 800,
        "total": 800,
    }
    estimate = render_estimate(quote)
    shop = render_shop_ticket(quote)
    idea = render_idea_sheet({"title": "Silk idea", "notes": "Try a 48.5 inch return."})
    measure = render_measurements("Scan", [{"id": 1, "distance_in": 48.5, "distance_ft": 4.04, "distance_m": 1.23}])

    for html in (estimate, shop, idea, measure):
        assert CREAM in html
        assert INK in html
        assert GOLD in html
        assert "#e94560" not in html
        assert "#8B5CF6" not in html

    assert "ESTIMATE" in estimate
    assert "SHOP" in shop
    assert "IDEA" in idea
    assert "MEASURE" in measure
    assert "48 1/2" in estimate
    assert "48 1/2" in shop
    assert "48 1/2" in measure
    assert "48.5" not in shop


def test_workroom_shop_sheet_is_cream_with_fractions():
    sheet = render_template_instance("pinch_pleat", {
        "name": "Library bay",
        "drawing_mode": "shop",
        "width": 108,
        "drop": 96,
        "return": 4.5,
        "hem": 4,
    })
    assert sheet is not None
    svg = sheet["svg"]
    assert 'fill="#f5f3ef"' in svg
    assert "#b8960c" in svg
    assert "EMPIRE WORKROOM" in svg
    assert "4 1/2" in svg
    assert "Return: 4.5" not in svg
