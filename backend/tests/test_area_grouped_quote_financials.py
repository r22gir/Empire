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


def test_quote_search_matches_metadata_and_ranks_updated_quote(isolated_empire_db):
    import json
    from app.db.database import get_db
    from app.services.quote_service import create_quote, list_quotes

    older = create_quote({
        "customer_name": "Maggie O'Neill",
        "project_name": "Willard Est 838 Addendum v2 Final",
        "business_unit": "workroom",
    })
    newer = create_quote({
        "customer_name": "Maggie O'Neill",
        "project_name": "Addendum 293",
        "business_unit": "workroom",
    })
    with get_db() as conn:
        conn.execute(
            "UPDATE quotes_v2 SET metadata_json=?, updated_at=? WHERE id=?",
            (json.dumps({"project": "Willard InterContinental – Lobby"}),
             "2026-09-30T13:42:00", newer["id"]),
        )
        conn.execute(
            "UPDATE quotes_v2 SET updated_at=? WHERE id=?",
            ("2026-09-30T11:20:00", older["id"]),
        )

    rows = list_quotes(search="Willard", limit=10)["quotes"]
    assert rows[0]["id"] == newer["id"]
    assert rows[0]["metadata"]["project"] == "Willard InterContinental – Lobby"
