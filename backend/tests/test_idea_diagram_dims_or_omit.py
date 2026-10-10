"""2026-10-08: quote lines carry dimensions so the idea diagram renders; otherwise the section is omitted."""
from app.services.drawing import idea_drawing as idd


def test_dims_from_description_render():
    d = idd.build_idea_diagram({"category": "manual_line",
                                "description": 'U bench channel back (left) 37.75" x 26.75"'})
    assert d["status"] == "attached", d.get("note")
    assert d["svg"] and "<svg" in d["svg"]


def test_sq_ft_and_prices_are_not_dimensions():
    assert idd.dimensions_from_text("U bench channel back (left) 7.01 sq ft x $65") == {}
    assert idd.dimensions_from_text('29.5 yd @ 54" x $54.95/yd') in ({}, {"width": 54.0})


def test_undrawable_line_is_omitted_from_client_html():
    quote = {"line_items": [{"category": "manual_line", "description": "U bench seat cushion (left) 4.72 sq ft x $45"}]}
    html = idd.quote_idea_html(idd.annotate_quote(quote))
    assert html == ""
    assert "needs at least one dimension" not in html and "unavailable" not in html.lower()


def test_legacy_pdf_omits_section_without_drawable_sheets():
    from app.services import quote_pdf_service as qps
    story = []
    styles = qps._get_styles()
    items = [{"description": "x", "idea_diagram": {"status": "degraded", "note": "Bench needs at least one dimension"},
              "drawing_svg": "<svg>notice</svg>"}]
    qps._append_idea_diagrams(story, styles, items)
    assert story == []
