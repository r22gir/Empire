from app.services.quote_service import _area_grouped_financials


def test_area_grouped_financials_include_original_and_addons():
    metadata = {
        "area_grouping": {
            "original_total": 4580.99,
            "addons_total": 4175.30,
            "grand_total": 8756.29,
        },
        "optional_hardware": {"total": 531.91},
    }
    assert _area_grouped_financials(metadata) == {
        "original_subtotal": 4580.99,
        "addons_subtotal": 4175.30,
        "grand_total": 8756.29,
        "optional_hardware_total": 531.91,
    }
