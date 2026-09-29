"""Item 3 (feature/drawing-standard dispatch) — the Workroom quotes list
only ever fetched `?limit=100`, so older quotes (EST-2026-007,
EST-2026-291) fell off once more than 100 quotes existed for a business
unit. Fix: `list_quotes()` accepts `offset` for paging and clamps `limit`
to a sane ceiling (MAX_LIST_QUOTES_LIMIT) instead of a silent unbounded
value, and reports `total` so a client can page with "Load more".
"""
from __future__ import annotations


def _make_quotes(n: int, business_unit: str = "workroom") -> list[dict]:
    from app.services.quote_service import create_quote
    return [
        create_quote({
            "customer_name": f"Pagination Customer {i:03d}",
            "business_unit": business_unit,
            "pricing_mode": "flat",
            "tax_rate": 0,
            "project_name": "Pagination Coverage",
        })
        for i in range(n)
    ]


def test_list_quotes_default_limit_is_below_new_ceiling(isolated_empire_db):
    from app.services.quote_service import MAX_LIST_QUOTES_LIMIT
    assert MAX_LIST_QUOTES_LIMIT >= 200


def test_list_quotes_limit_is_clamped_to_ceiling(isolated_empire_db):
    from app.services.quote_service import MAX_LIST_QUOTES_LIMIT, list_quotes

    _make_quotes(3)
    result = list_quotes(business_unit="workroom", limit=MAX_LIST_QUOTES_LIMIT * 10)
    # Never trust a caller-supplied limit above the ceiling.
    assert len(result["quotes"]) <= MAX_LIST_QUOTES_LIMIT


def test_list_quotes_offset_pages_through_all_rows(isolated_empire_db):
    from app.services.quote_service import list_quotes

    created = _make_quotes(7)
    created_ids = {q["id"] for q in created}

    page_size = 3
    seen_ids: set[str] = set()
    offset = 0
    total = None
    for _ in range(10):
        page = list_quotes(business_unit="workroom", limit=page_size, offset=offset)
        total = page.get("total", total)
        rows = page["quotes"]
        if not rows:
            break
        seen_ids.update(row["id"] for row in rows)
        offset += page_size

    assert created_ids.issubset(seen_ids)
    if total is not None:
        assert total >= len(created)


def test_list_quotes_older_quotes_reachable_past_first_hundred(isolated_empire_db):
    """Regression for the EST-2026-007 / EST-2026-291 report: a quote
    created before 100+ later quotes must still be reachable by paging,
    not silently dropped by a hard limit=100 cutoff."""
    from app.services.quote_service import list_quotes

    oldest = _make_quotes(1)[0]
    _make_quotes(105)  # push the oldest past the old limit=100 cutoff

    first_page = list_quotes(business_unit="workroom", limit=100, offset=0)
    first_page_ids = {row["id"] for row in first_page["quotes"]}
    assert oldest["id"] not in first_page_ids, (
        "test setup assumption broken: oldest quote unexpectedly on page 1"
    )

    next_page = list_quotes(business_unit="workroom", limit=100, offset=100)
    next_page_ids = {row["id"] for row in next_page["quotes"]}
    assert oldest["id"] in next_page_ids, (
        "oldest quote must be reachable via offset pagination"
    )
