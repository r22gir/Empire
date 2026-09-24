"""Regression: create_engine_quote must map Becky-shape top-level fields
into inputs for manual_line so PricingInputError is not raised when the
model omits a nested inputs dict.
"""
import sys
import uuid
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))


def test_normalize_manual_line_copies_toplevel_into_inputs():
    from app.services.max.tool_executor import _normalize_manual_line_inputs

    inputs = _normalize_manual_line_inputs({
        "category": "manual_line",
        "description": "Pinch pleat, 4 widths @ $95",
        "unit_price": 95.0,
        "quantity": 4,
        "inputs": {},
    })
    assert inputs["description"].startswith("Pinch pleat")
    assert inputs["unit_price"] == 95.0
    assert inputs["quantity"] == 4


def test_normalize_manual_line_preserves_existing_inputs():
    from app.services.max.tool_executor import _normalize_manual_line_inputs

    inputs = _normalize_manual_line_inputs({
        "category": "manual_line",
        "description": "ignored top-level",
        "unit_price": 1,
        "inputs": {
            "description": "nested wins",
            "unit_price": 50.0,
            "quantity": 2,
        },
    })
    assert inputs["description"] == "nested wins"
    assert inputs["unit_price"] == 50.0
    assert inputs["quantity"] == 2


def test_normalize_leaves_other_engines_alone():
    from app.services.max.tool_executor import _normalize_manual_line_inputs

    inputs = _normalize_manual_line_inputs({
        "category": "drapery",
        "description": "should not be copied",
        "unit_price": 999,
        "inputs": {"window_width_in": 84},
    })
    assert inputs == {"window_width_in": 84}
    assert "description" not in inputs
    assert "unit_price" not in inputs


def test_create_engine_quote_accepts_becky_shape_manual_line(isolated_empire_db):
    """Live tool path: top-level description/unit_price/quantity, empty inputs."""
    from app.services.max.tool_executor import execute_tool

    marker = uuid.uuid4().hex[:8]
    res = execute_tool({
        "tool": "create_engine_quote",
        "customer_name": f"ManualLine Map Test {marker}",
        "business_unit": "workroom",
        "line_items": [
            {
                "category": "manual_line",
                "description": f"Test labor line {marker}",
                "unit_price": 95.0,
                "quantity": 4,
                # Model forgot to nest — previously PricingInputError.
                "inputs": {},
            }
        ],
    })
    assert res.success, f"create_engine_quote failed: {res.error}"
    assert res.result["status"] == "draft"
    assert res.result["store"] == "quotes_v2"
    assert res.result["total"] == 380.0
    assert res.result["quote_id"]
    assert res.result["quote_number"]
