"""MAX quote PDF — skip verification for canonical line_items; propagate verifier errors."""
from __future__ import annotations

import json
import uuid

import pytest


@pytest.fixture
def draft_manual_line_quote(isolated_empire_db):
    """Draft canonical quote with manual_line items (no tiers / dimensions)."""
    from app.services.quote_service import create_quote

    marker = uuid.uuid4().hex[:8]
    return create_quote({
        "customer_name": f"PDF manual-line {marker}",
        "business_unit": "workroom",
        "status": "draft",
        "pricing_mode": "flat",
        "tax_rate": 0,
        "line_items": [
            {
                "category": "manual_line",
                "description": "LR drapery",
                "quantity": 1,
                "unit": "ea",
                "unit_price": 485,
            },
            {
                "category": "manual_line",
                "description": "BR Roman",
                "quantity": 2,
                "unit": "ea",
                "unit_price": 590,
            },
        ],
    })


@pytest.mark.asyncio
async def test_generate_pdf_for_quote_canonical_manual_lines(draft_manual_line_quote):
    """Draft canonical manual-line quotes must generate PDF without tier verification."""
    from app.services.max.tool_executor import _generate_pdf_for_quote

    qid = draft_manual_line_quote["id"]
    pdf_path = await _generate_pdf_for_quote(qid)
    assert pdf_path.endswith(f"{draft_manual_line_quote['quote_number']}.pdf")
    assert __import__("os").path.exists(pdf_path)
    assert __import__("os").path.getsize(pdf_path) > 0


def test_send_quote_email_surfaces_verifier_reasons_for_legacy_quote(tmp_path, monkeypatch):
    """Legacy tier quotes that fail verification return specific reasons, not a generic error."""
    import os

    from app.services.data_paths import quotes_data_dir
    from app.services.max.tool_executor import _send_quote_email

    legacy_id = f"leg{uuid.uuid4().hex[:6]}"
    quote_number = f"EST-LEG-{legacy_id}"
    legacy = {
        "id": legacy_id,
        "quote_number": quote_number,
        "customer_name": "Legacy Tier Fail",
        "total": 100,
        "status": "draft",
        "rooms": [{
            "name": "LR",
            "windows": [{"name": "W1", "treatmentType": "ripplefold"}],
        }],
    }
    legacy_path = quotes_data_dir() / f"{legacy_id}.json"
    try:
        with open(legacy_path, "w") as f:
            json.dump(legacy, f)

        monkeypatch.setenv("FOUNDER_EMAIL", "empirebox2026@gmail.com")
        result = _send_quote_email({
            "quote_id": legacy_id,
            "to": "empirebox2026@gmail.com",
        })
        assert not result.success
        err = result.error or ""
        assert "PDF generation failed" in err
        assert "No pricing tiers found in quote" in err
        assert err != "PDF generation failed"
    finally:
        if legacy_path.exists():
            legacy_path.unlink()
