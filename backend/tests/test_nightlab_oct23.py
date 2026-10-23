"""Night Lab 2026-10-23 — Studio Max drawing / quote / WoodCraft fixes.

Mock data and temp dirs only. No live quotes, sends, or contacts.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services.drawing.job_drawing import (
    generate_job_drawing,
    resolve_internal_fabric,
    run_job_drawing_turn,
)
from app.services.max.job_drawing_intent import extract_spec_changes
from app.services.vision.bench_cut_list import format_cut_inches


HISTORY = [
    {"role": "user", "content": "make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black"},
    {"role": "assistant", "content": "New drawing for Marley's (REV A)"},
]

MOCK_QUOTE = {
    "customer_name": "Marley's",
    "quote_number": "EST-TEMP-NL23",
    "project_name": "Marley's Hyattsville",
    "line_items": [{"description": 'Seat back — 12" channels', "quantity": 1}],
    "total": 0,
}

LONG_PROJECT = (
    "The Very Long Banquette And Drapery Package For The Downtown "
    "Hotel Ballroom Renovation Phase Two With Extra Attn Notes"
)


@pytest.fixture
def drawings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setattr(
        "app.services.drawing.job_drawing.resolve_job_quote",
        lambda hint: dict(MOCK_QUOTE),
    )
    return tmp_path


def _pages(pdf_path: str) -> list[str]:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def test_fraction_parser_reads_three_quarters_not_four():
    assert extract_spec_changes("3/4 inch channels")["channel_width_in"] == pytest.approx(0.75)
    assert extract_spec_changes("change it to 3/4 inch channels")["channel_width_in"] == pytest.approx(0.75)
    assert extract_spec_changes("12 3/4 inch channels")["channel_width_in"] == pytest.approx(12.75)
    assert extract_spec_changes("12-3/4 inch channels")["channel_width_in"] == pytest.approx(12.75)
    assert extract_spec_changes("make the channels 10 inches")["channel_width_in"] == 10


def test_unknown_fabric_code_is_warned_not_silent(drawings_dir):
    fake = resolve_internal_fabric("V999-Fake")
    assert fake.get("unknown_code")
    assert fake.get("code") in (None, "")
    result = generate_job_drawing(
        message="revise the drawing: seat cushions on V999-Fake",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert result["success"]
    blob = " ".join(result.get("estimate_conflicts") or []).upper()
    assert "UNKNOWN FABRIC CODE" in blob
    assert "V999-FAKE" in blob
    assert "REGISTRY" in blob
    pages = _pages(result["pdf_path"])
    text = "\n".join(pages).upper()
    assert "UNKNOWN FABRIC CODE" in text
    assert "V999-FAKE" in text
    assert "None — drawing matches" not in "\n".join(pages)


def test_channel_revision_flags_conflicts_page(drawings_dir):
    first = generate_job_drawing(
        message="make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black",
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert first["success"]
    turn = run_job_drawing_turn(
        "change it to 10 inch channels",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert turn["handled"] is True
    result = turn["result"]
    assert result["dimensions"]["channel_width"] == '10"'
    flags = " ".join(result.get("estimate_conflicts") or [])
    assert "10" in flags and "12" in flags
    assert "revised" in flags.lower() or "conflicts" in flags.lower()
    pages = _pages(result["pdf_path"])
    conflicts_page = pages[-1] if pages else ""
    assert "CONFLICTS" in conflicts_page.upper()
    assert "None — drawing matches" not in conflicts_page
    assert re.search(r"10|12", conflicts_page)
    assert result["fabrics"]["seat"]["code"] == "V001-Raven"
    assert result["fabrics"]["back"]["code"] == "V003-Cognac"


def test_chat_and_drawings_use_space_fractions(drawings_dir):
    assert format_cut_inches(249.75) == '249 3/4"'
    assert format_cut_inches(26.75) == '26 3/4"'
    assert "-" not in format_cut_inches(249.75)
    result = generate_job_drawing(
        message="make a drawing for the Marley's job",
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert result["success"]
    dims = " ".join(str(v) for v in result["dimensions"].values())
    assert re.search(r"\d+-\d+/", dims) is None
    pages = _pages(result["pdf_path"])
    blob = "\n".join(pages)
    assert "249 3/4" in blob
    assert "249-3/4" not in blob
    assert result["fabrics"]["seat"]["code"] == "V001-Raven"


def test_quote_pdf_long_project_name_does_not_overlap_header(tmp_path):
    pytest.importorskip("pdfplumber")
    import pdfplumber
    from app.services.estimates.mclean_estimate_pdf import render_mclean_estimate_bytes

    quote = {
        "id": "q-long-nl23",
        "quote_number": "EST-TEMP-NL23",
        "customer_name": "Whittington Design Studio LLC",
        "project_name": LONG_PROJECT,
        "status": "draft",
        "created_at": "2026-10-23",
        "line_items": [
            {
                "room": "U banquette",
                "description": 'Seat back — main\n249 3/4" run · back 26 3/4" · 12" channels',
                "quantity": 1,
                "unit_price": 100,
                "total": 100,
            }
        ],
        "total": 100,
        "metadata": {"client_safe_pdf": True},
    }
    pdf_bytes = render_mclean_estimate_bytes(quote)
    assert pdf_bytes[:4] == b"%PDF"
    proof = tmp_path / "quote_long_project.pdf"
    proof.write_bytes(pdf_bytes)
    with pdfplumber.open(proof) as pdf:
        page = pdf.pages[0]
        words = page.extract_words() or []
        header = [w for w in words if w["top"] < 56]
        assert header, "header band should have words"
        # No two distinct header words should overlap in both x and y.
        hits = []
        for i, a in enumerate(header):
            for b in header[i + 1 :]:
                if a["text"] == b["text"] and abs(a["x0"] - b["x0"]) < 1:
                    continue
                ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
                oy = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
                if ox > 3 and oy > 3:
                    hits.append((a["text"], b["text"]))
        assert hits == [], f"header overlap {hits[:8]}"
        text = page.extract_text() or ""
        assert "ESTIMATE" in text.upper() or "EST-TEMP-NL23" in text
        # Tagline must stay a real phrase — mashed glyphs mean the project
        # line wrapped onto CUSTOM UPHOLSTERY & FABRICATION.
        assert "CUSTOM UPHOLSTERY" in text.upper()
        assert "CDOUWNSTTOWONM" not in text.upper()
        assert "OUTEPLH" not in text.upper()
        # Project words survive (shrunk/ellipsized, not dropped entirely).
        assert "BALLROOM" in text.upper() or "HOTEL" in text.upper() or "BANQUETTE" in text.upper()


def test_max_desk_returns_conflicts_and_fraction_pages(drawings_dir):
    """Real Max door: _maybe_job_drawing_desk_response returns the PDF pages."""
    import importlib

    max_router = importlib.import_module("app.routers.max.router")
    request = max_router.ChatRequest(
        message="change it to 10 inch channels; seat cushions on V999-Fake",
        history=HISTORY,
        channel="web",
        job_id="marleys",
    )
    response = asyncio.run(max_router._maybe_job_drawing_desk_response(request))
    assert response is not None
    assert response.model_used == "drawing-desk"
    blob = (response.response or "").upper()
    assert "UNKNOWN FABRIC CODE" in blob
    assert "V999-FAKE" in blob
    assert "249 3/4" in (response.response or "") or "10\"" in (response.response or "")
    tools = response.tool_results or []
    assert tools and tools[0].get("success")
    result = tools[0]["result"]
    pdf_path = result["pdf_path"]
    pages = _pages(pdf_path)
    text = "\n".join(pages)
    assert "CONFLICTS" in pages[-1].upper()
    assert "None — drawing matches" not in pages[-1]
    assert "UNKNOWN FABRIC CODE" in text.upper()
    assert "V999-FAKE" in text.upper()
    assert "249 3/4" in text
    assert "249-3/4" not in text
    assert result["fabrics"]["seat"].get("unknown_code")


def test_woodcraft_zero_invoice_and_job_link(monkeypatch, tmp_path):
    import importlib

    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    from app.db import database, init_db
    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()
    from app.routers import jobs_unified
    importlib.reload(jobs_unified)
    from app.routers import craftforge
    importlib.reload(craftforge)
    data_dir = tmp_path / "craftforge"
    designs_dir = data_dir / "designs"
    for path in (designs_dir, data_dir / "jobs", data_dir / "inventory", data_dir / "templates"):
        path.mkdir(parents=True)
    monkeypatch.setattr(craftforge, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(craftforge, "DESIGNS_DIR", str(designs_dir))
    monkeypatch.setattr(craftforge, "JOBS_DIR", str(data_dir / "jobs"))
    monkeypatch.setattr(craftforge, "INVENTORY_DIR", str(data_dir / "inventory"))
    monkeypatch.setattr(craftforge, "TEMPLATES_DIR", str(data_dir / "templates"))
    monkeypatch.setattr(craftforge, "COUNTER_FILE", str(data_dir / "_counter.json"))
    database.DB_PATH = str(tmp_path / "empire.db")
    paid = {
        "id": "design-link",
        "design_number": "CF-2026-NL",
        "customer_name": "Link Client",
        "name": "Walnut panel",
        "materials": [{"name": "Walnut", "quantity": 1, "cost_per_unit": 80}],
        "line_items": [{"description": "Finish", "quantity": 1, "unit_price": 20}],
        "material_cost": 80,
        "labor_cost": 20,
        "subtotal": 100,
        "tax_rate": 0,
        "tax_amount": 0,
        "total": 100,
        "status": "accepted",
    }
    (designs_dir / "design-link.json").write_text(json.dumps(paid))
    zero = dict(paid)
    zero.update({"id": "design-zero", "design_number": "CF-2026-ZERO", "total": 0, "subtotal": 0})
    (designs_dir / "design-zero.json").write_text(json.dumps(zero))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as caught:
        asyncio.run(craftforge.create_invoice_from_design("design-zero"))
    assert caught.value.status_code == 400
    assert "greater than zero" in str(caught.value.detail).lower()
    job = asyncio.run(craftforge.create_job_from_design("design-link"))["job"]
    invoice = asyncio.run(craftforge.create_invoice_from_design("design-link"))["invoice"]
    assert invoice["total"] == 100
    assert invoice.get("job_id") == job["id"]
    with database.get_db() as conn:
        job_row = conn.execute("SELECT invoice_id FROM jobs WHERE id = ?", (job["id"],)).fetchone()
        assert job_row["invoice_id"] == invoice["id"]
