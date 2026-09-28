"""Idea diagrams on Workroom quotes: category + any dims, fractional inches, no hard failure."""
import importlib

import pytest


def test_format_inches_uses_reduced_fractions():
    from app.services.drawing.idea_drawing import format_inches, parse_length

    assert format_inches(54.5) == '54 1/2"'
    assert format_inches(0.75) == '3/4"'
    assert format_inches(0.125) == '1/8"'
    assert format_inches(34.5) == '34 1/2"'
    assert format_inches(48) == '48"'
    assert format_inches(0.0625) == '1/16"'
    assert parse_length('54 1/2') == 54.5
    assert parse_length('54-1/2"') == 54.5
    assert parse_length("3/4") == 0.75
    assert parse_length(137.125) == 137.125


def test_catalog_drapery_lands_in_window_treatment_with_any_dims():
    from app.services.drawing.idea_drawing import build_idea_diagram

    diagram = build_idea_diagram({
        "category": "drapery",
        "description": "Living room pinch pleat",
        "inputs": {
            "window_width_in": 54.5,
            "length_in": 96.25,
            "style": "regular",
            "fullness": 2.5,
        },
    })
    assert diagram["status"] == "attached"
    assert diagram["category"] == "window_treatment"
    assert diagram["fidelity"] == "idea"
    assert diagram["final_design"] == "later"
    assert diagram["dimensions"]["width"] == 54.5
    assert diagram["dimensions"]["height"] == 96.25
    assert '54 1/2"' in diagram["svg"]
    assert '96 1/4"' in diagram["svg"]
    assert "IDEA ONLY" in diagram["svg"]
    assert "WINDOW TREATMENT" in diagram["svg"]
    from app.services.drawing.idea_drawing import idea_png_bytes
    png = idea_png_bytes(diagram)
    assert png is not None and png.startswith(b"\x89PNG")


def test_odd_dimensions_scale_on_the_sheet():
    from app.services.drawing.idea_drawing import build_idea_diagram

    diagram = build_idea_diagram({
        "item_type": "chair",
        "width": "32 1/8",
        "depth": 19.5,
        "height": 41.75,
        "seat_height": 18.25,
    })
    assert diagram["status"] == "attached"
    assert diagram["category"] == "chair"
    assert '32 1/8"' in diagram["svg"]
    assert '41 3/4"' in diagram["svg"]
    assert '19 1/2"' in diagram["svg"]
    assert "<svg" in diagram["svg"]
    assert 'viewBox="0 0 720 480"' in diagram["svg"]


def test_missing_dims_degrade_without_raising():
    from app.services.drawing.idea_drawing import build_idea_diagram

    diagram = build_idea_diagram({"category": "roman_shade", "description": "Kitchen roman"})
    assert diagram["status"] == "degraded"
    assert diagram["category"] == "window_treatment"
    assert "needs at least one dimension" in diagram["note"]
    assert "unavailable" in diagram["svg"].lower() or "needs at least one dimension" in diagram["svg"]


def test_unknown_category_and_fees_are_honest():
    from app.services.drawing.idea_drawing import build_idea_diagram

    unknown = build_idea_diagram({"category": "mystery_widget", "description": "custom widget", "width": 12})
    assert unknown["status"] == "degraded"
    assert unknown["category"] is None
    assert "No Max diagram category" in unknown["note"]

    labor = build_idea_diagram({"category": "labor", "description": "Installation labor", "quantity": 2})
    assert labor["status"] == "not_applicable"
    assert labor["svg"] is None

    hardware = build_idea_diagram({"category": "hardware_rings", "description": "Rings", "width": 48})
    assert hardware["status"] == "not_applicable"


def test_renderer_crash_is_degraded():
    from app.services.drawing import idea_drawing

    original = idea_drawing._build_idea_diagram

    def explode(_item):
        raise RuntimeError("renderer exploded")

    idea_drawing._build_idea_diagram = explode
    try:
        diagram = idea_drawing.build_idea_diagram({"item_type": "sofa", "width": 90, "height": 34, "depth": 36})
    finally:
        idea_drawing._build_idea_diagram = original
    assert diagram["status"] == "degraded"
    assert "renderer exploded" in diagram["note"]


def test_quote_html_includes_idea_sheet_and_survives_bad_input():
    from app.services.drawing.idea_drawing import quote_idea_html

    html = quote_idea_html({
        "rooms": [{
            "name": "Living",
            "items": [{
                "type": "cushion_box_edge",
                "description": "Window seat cushion",
                "dimensions": {"width": 48.5, "depth": 18.25, "thickness": 4},
            }],
        }],
    })
    assert "Idea diagrams" in html
    assert "window_treatment" not in html or "Cushion" in html or "cushion" in html.lower()
    assert '48 1/2"' in html
    assert "not the final design" in html.lower() or "later process" in html.lower()

    assert quote_idea_html({"line_items": [{"category": "labor", "description": "Labor"}]}) == ""
    assert "unavailable" in quote_idea_html(None).lower() or quote_idea_html("nope") == ""


def _fresh_quote_service(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    monkeypatch.setenv("EMPIRE_TASK_DB", str(db_path))
    import app.db.database as database
    importlib.reload(database)
    import app.db.unified_business_migration as migration
    importlib.reload(migration)
    conn = migration.get_conn()
    migration.create_all_tables(conn)
    conn.close()
    import app.services.quote_service as quote_service
    importlib.reload(quote_service)
    return quote_service


def test_v2_quote_attaches_idea_diagram_and_pdf(monkeypatch, tmp_path):
    quote_service = _fresh_quote_service(monkeypatch, tmp_path)
    created = quote_service.create_quote({
        "customer_name": "Ada Lovelace",
        "business_unit": "workroom",
        "line_items": [
            {
                "category": "drapery",
                "description": "Parlor drapery",
                "inputs": {
                    "window_width_in": 54.5,
                    "length_in": 84,
                    "style": "regular",
                    "fullness": 2.5,
                },
            },
            {
                "category": "labor",
                "description": "Install",
                "inputs": {"hours": 2},
            },
        ],
    })
    assert created["quote_number"]
    drapery = created["line_items"][0]
    labor = created["line_items"][1]
    assert drapery["proposed_price"] > 0
    assert drapery["idea_diagram"]["status"] == "attached"
    assert drapery["idea_diagram"]["category"] == "window_treatment"
    assert '54 1/2"' in drapery["drawing_svg"]
    assert labor["idea_diagram"]["status"] == "not_applicable"
    assert not labor.get("drawing_svg")

    import app.services.quote_pdf_service as pdf_service
    importlib.reload(pdf_service)
    pdf_bytes = pdf_service.generate_quote_pdf(created["id"])
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 1000


def test_v2_quote_survives_drawing_failure(monkeypatch, tmp_path):
    quote_service = _fresh_quote_service(monkeypatch, tmp_path)

    def explode(_line):
        raise RuntimeError("drawing backend down")

    monkeypatch.setattr(
        "app.services.drawing.idea_drawing.build_idea_diagram",
        explode,
    )
    created = quote_service.create_quote({
        "customer_name": "Grace Hopper",
        "business_unit": "workroom",
        "line_items": [{
            "category": "pillow",
            "description": "Euro sham",
            "width": 26,
            "height": 26,
            "quantity": 2,
            "inputs": {"unit_price": 30, "quantity": 2},  # founder price; drawing still must not block
        }],
    })
    assert created["id"]
    item = created["line_items"][0]
    assert item["idea_diagram"]["status"] == "degraded"
    assert "drawing backend down" in item["idea_diagram"]["note"]
    assert item["final_price"] >= 0
