"""2026-10-08: empty billed_by reads as Empire Workroom; Nelma's only when explicitly set."""
from app.services.max import tool_executor as te


def test_billed_as():
    assert te._billed_as(None) == "Empire Workroom"
    assert te._billed_as("") == "Empire Workroom"
    assert te._billed_as("empire_workroom") == "Empire Workroom"
    assert te._billed_as("nelmas_workroom") == "Nelma's Workroom"
