"""MAX quote PDF — skip verification for canonical line_items; propagate verifier errors."""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

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


def test_send_quote_email_json_quote_uses_mclean_not_weasy_verification(tmp_path, monkeypatch):
    """Email attachments render through McLean; WeasyPrint verification is not the gate."""
    from app.services.data_paths import quotes_data_dir
    from app.services.max import tool_executor as te
    from app.services.max.tool_executor import _send_quote_email

    legacy_id = f"leg{uuid.uuid4().hex[:6]}"
    quote_number = f"EST-LEG-{legacy_id}"
    legacy = {
        "id": legacy_id,
        "quote_number": quote_number,
        "customer_name": "Legacy Json Quote",
        "total": 100,
        "status": "draft",
        "line_items": [{
            "description": "Seat",
            "quantity": 1,
            "unit": "ea",
            "rate": 100,
            "amount": 100,
            "room": "Dining",
        }],
        "deposit_required": 50,
        "balance_due": 50,
        "deposit_percent": 50,
    }
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    monkeypatch.setattr(te.dp, "quote_pdf_dir", lambda: pdf_dir)
    monkeypatch.setattr("app.services.data_paths.quote_pdf_dir", lambda: pdf_dir)
    monkeypatch.setattr("app.services.quote_pdf_service.quote_pdf_dir", lambda: pdf_dir)

    sent = []

    class FakeSvc:
        is_configured = True
        last_message_id = "json-mclean"

        def send(self, **kwargs):
            sent.append(kwargs)
            return True

    monkeypatch.setattr("app.services.max.email_service.EmailService", FakeSvc)

    quotes_dir = quotes_data_dir()
    quotes_dir.mkdir(parents=True, exist_ok=True)
    legacy_path = quotes_dir / f"{legacy_id}.json"
    try:
        with open(legacy_path, "w") as f:
            json.dump(legacy, f)

        result = _send_quote_email({
            "quote_id": legacy_id,
            "to": "empirebox2026@gmail.com",
        })
        assert result.success, result.error
        assert sent and sent[0]["to"] == "empirebox2026@gmail.com"
        assert sent[0].get("cc") in (None, "", [])
        pdf_bytes = Path(sent[0]["attachments"][0]).read_bytes()
        assert pdf_bytes[:4] == b"%PDF"
        from pypdf import PdfReader
        text = "\n".join(
            (p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf_bytes)).pages
        )
        assert "MANUAL_LINE" not in text.upper()
        assert "Deposit" in text
        assert "Balance" in text
    finally:
        if legacy_path.exists():
            legacy_path.unlink()
