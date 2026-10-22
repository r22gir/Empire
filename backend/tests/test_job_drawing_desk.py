"""Job drawing desk — routing, revision PDF, review sanitize, pipeline filter.

Temp data only. No live quotes, no real sends.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.max.desks.delegate_first import classify_request
from app.services.max.desks.desk_chat_report import (
    brief_review_failure,
    founder_facing_desk_result,
    is_raw_desk_dump,
)
from app.services.max.desks.desk_router import DeskRouter
from app.services.max.job_drawing_intent import (
    DRAWING_DESK_ID,
    extract_job_hint,
    is_drawing_change_followup,
    is_job_drawing_request,
    is_layout_revision_request,
    merge_drawing_job_context,
    should_route_to_drawing_desk,
)
from app.services.max.brief_filters import is_noise_client


TEMP_LAYOUT = {
    "width_in": 96,
    "depth_in": 16,
    "back_height_in": 26.75,
    "channel_width_in": 10,
    "foam_thickness_in": 2.0,
    "seat_height_in": 18,
    "shape": "straight",
}

MARLEY_HISTORY = [
    {"role": "user", "content": "can you give me a drawing of the marleys job"},
    {"role": "assistant", "content": "here is an older PDF"},
    {
        "role": "user",
        "content": (
            'this layout was the older one, we need the one with channel back '
            'at 12" wide for all seat backs on cognac and seat cushion on black'
        ),
    },
]


def test_job_drawing_request_is_not_a_file_lookup():
    assert is_job_drawing_request("can you give me a drawing of the marleys job")
    assert is_job_drawing_request("give me a drawing of the TempBanquette job")
    assert not is_job_drawing_request("can you show me the Marley docs")
    assert not is_job_drawing_request("give me a drawing of a bench 96 wide 22 deep")
    assert not is_job_drawing_request("drawing")


def test_layout_revision_and_change_it_followup():
    spec_msg = (
        'this layout was the older one, we need the one with channel back '
        'at 12" wide for all seat backs on cognac and seat cushion on black'
    )
    assert is_layout_revision_request(spec_msg)
    assert is_drawing_change_followup("you change it")
    assert is_drawing_change_followup("change it")
    assert should_route_to_drawing_desk(spec_msg)
    assert should_route_to_drawing_desk("you change it", MARLEY_HISTORY)
    assert not should_route_to_drawing_desk("you change it", [])
    assert not should_route_to_drawing_desk("can you show me the Marley docs")


def test_followup_carries_job_and_spec_context():
    ctx = merge_drawing_job_context("you change it", MARLEY_HISTORY)
    assert (ctx["job_hint"] or "").lower().startswith("marley")
    assert ctx["spec_changes"]["channel_width_in"] == 12
    assert ctx["spec_changes"]["back_fabric"].lower() == "cognac"
    assert ctx["spec_changes"]["seat_fabric"].lower() == "black"
    assert extract_job_hint("drawing of the TempBanquette job") == "TempBanquette"


def test_classify_routes_drawing_to_forge_never_sales():
    d = classify_request("can you give me a drawing of the marleys job")
    assert d.action == "delegate"
    assert d.desk_id == DRAWING_DESK_ID
    d2 = classify_request(
        'this layout was the older one, we need the one with channel back at 12" wide',
    )
    assert d2.desk_id == DRAWING_DESK_ID
    d3 = classify_request("you change it", history=MARLEY_HISTORY)
    assert d3.desk_id == DRAWING_DESK_ID
    docs = classify_request("can you show me the Marley docs")
    assert docs.answers_directly


def test_desk_router_drawing_beats_pipeline_keywords():
    from app.services.max.desks.base_desk import DeskTask
    from app.services.max.desks.forge_desk import ForgeDesk
    from app.services.max.desks.sales_desk import SalesDesk

    router = DeskRouter()
    router.register_desk(ForgeDesk())
    router.register_desk(SalesDesk())
    task = DeskTask(
        id="t1",
        title="you change it",
        description=(
            "Marleys job quote EST-TEMP-1 — this layout was the older one, "
            "we need channel back at 12 wide. you change it"
        ),
    )
    desk_id, reason = router._route_with_keywords(task)
    assert desk_id == "forge"
    assert "drawing" in reason.lower() or "layout" in reason.lower() or "forge" in reason.lower()


def test_prelookup_does_not_search_files_for_new_job_drawing():
    from app.services.max.answer_policy import prelookup_calls

    with patch("app.services.max.answer_policy.model_first", return_value=True):
        calls = prelookup_calls("can you give me a drawing of the marleys job")
    tools = [c.get("tool") for c in calls]
    assert "find_files" not in tools


def test_generate_uses_layout_when_estimate_lacks_dims(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    csv_path = tmp_path / "FABRIC_CODES.csv"
    csv_path.write_text(
        "code,color,material_type,width_inches,pattern_repeat_v,pattern_repeat_h,"
        "backing,specs,brand,supplier,supplier_sku,notes\n"
        "V100-Cognac,Cognac,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU1,\n"
        "V101-Black,Black,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU2,\n"
    )
    monkeypatch.setenv("EMPIRE_FABRIC_CODES_CSV", str(csv_path))

    quote = {
        "customer_name": "TempBanquette Client",
        "quote_number": "EST-TEMP-1",
        "project_name": "TempBanquette booth",
        "line_items": [{"description": "banquette", "inputs": {}}],  # no dims
        "total": 1000,
    }
    result = generate_job_drawing(
        message=(
            'this layout was the older one, we need the one with channel back '
            'at 12" wide for all seat backs on cognac and seat cushion on black'
        ),
        job_hint="TempBanquette",
        quote=quote,
        layout_data=TEMP_LAYOUT,
        takeoff=TEMP_LAYOUT,
    )
    assert result["success"] is True
    assert result["internal_only"] is True
    assert result["never_send_to_clients"] is True
    assert result["desk"] == "forge"
    assert result["dimensions"]["channel_width"] == '12"'
    assert "." not in result["dimensions"]["channel_width"]
    assert "." not in result["dimensions"]["back_height"]
    pdf = Path(result["pdf_path"])
    assert pdf.exists() and pdf.stat().st_size > 80
    raw = pdf.read_bytes()
    shop = Path(result.get("shop_pdf_path") or result["pdf_path"])
    shop_raw = shop.read_bytes() if shop.exists() else raw
    blob = raw + shop_raw
    assert b"EMPIRE WORKROOM" in blob
    assert b"INTERNAL ONLY" in blob
    assert b"SecretBrand" not in blob
    assert b"HiddenSupplier" not in blob
    assert b"Spradling" not in blob
    assert b"Apex" not in blob
    cuts = result["cut_list"]
    wood = cuts["wood"][0]
    foam = cuts["foam"][0]
    fabric = cuts["fabric"][0]
    assert wood["size"] == foam["size"]
    assert "WOOD" in wood["label"]
    assert "FOAM" in foam["label"]
    assert "FABRIC" in fabric["label"]
    assert wood["size"] != fabric["size"]
    assert "." not in fabric["size"]
    assert fabric["width"] == 12 + 2 * 5
    assert fabric["length"] == 26.75 + 2 * 5
    assert result["fabrics"]["back"]["code"] == "V100-Cognac"
    assert result["fabrics"]["seat"]["code"] == "V101-Black"


def test_estimate_conflict_flagged_not_repriced(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    quote = {
        "customer_name": "TempBanquette Client",
        "quote_number": "EST-TEMP-2",
        "line_items": [{"description": '10" channel back', "inputs": {"channel_width_in": 10}}],
        "total": 2400,
    }
    result = generate_job_drawing(
        message='revise the drawing, channel back at 12" wide',
        job_hint="TempBanquette",
        quote=quote,
        layout_data=TEMP_LAYOUT,
        spec_changes={"channel_width_in": 12},
    )
    assert result["success"]
    blob = " ".join(result["estimate_conflicts"]).lower()
    assert "12" in blob and "10" in blob
    assert "not changed" in blob or "unchanged" in blob
    assert quote["total"] == 2400


def test_refuses_only_when_no_layout_or_takeoff():
    from app.services.drawing.job_drawing import generate_job_drawing

    result = generate_job_drawing(
        message="give me a drawing of the UnknownTemp job",
        job_hint="UnknownTemp-NoLayout",
        quote={"customer_name": "UnknownTemp", "line_items": [{"description": "banquette"}]},
        layout_data={},
        takeoff={},
    )
    assert result["success"] is False
    assert "invent" in result["error"].lower() or "layout" in result["error"].lower()


def test_review_failure_is_brief_not_pipeline_dump():
    dump = (
        "FAILED (review): output does not match the request\n"
        "Today's Pipeline Summary — 230 open quotes, 0 active jobs, 0 events today\n"
        "Open quotes:\n"
    ) + "\n".join(f"  - EST-{i} — TrustTest, $1.00, draft" for i in range(230))
    assert is_raw_desk_dump(dump)
    brief = founder_facing_desk_result(
        dump, verdict="failed", reason="output does not match the request", desk_id="sales",
    )
    assert "230" not in brief
    assert "TrustTest" not in brief
    assert "review failed" in brief.lower()
    assert len(brief) < 280
    assert "raw desk output" in brief.lower()
    assert "FAILED (review)" not in brief or "230" not in brief
    line = brief_review_failure("wrong desk work", desk_id="sales")
    assert "sales desk review failed" in line.lower()


def test_pipeline_summary_excludes_test_quotes(isolated_empire_db):
    from app.db.database import get_db
    from app.services.max.desks.job_runner import job_forge_pipeline
    from app.services.max.desks.live_data import query_open_quotes, snapshot

    with get_db() as conn:
        rows = [
            ("real-1", "EST-REAL-1", "Nelma Rivera", "sent", 900, 0),
            ("tt-1", "EST-TT", "TrustTest", "sent", 10, 0),
            ("hf-1", "EST-HF", "HOTFIX5 Probe", "draft", 10, 0),
            ("cc-1", "EST-CC", "Canonical Customer", "draft", 10, 0),
            ("rc-1", "EST-RC", "Routed Customer", "proposal", 10, 0),
            ("mk-1", "EST-MK", "MOCK fixture", "draft", 10, 0),
            ("tg-1", "EST-TG", "TruthGuard lane", "draft", 10, 0),
            ("sm-1", "EST-SM", "SMOKE", "draft", 10, 0),
            ("dp-1", "EST-DP", "diag-probe-alpha", "draft", 10, 0),
            ("flag-1", "EST-FLAG", "Looks Real", "sent", 50, 1),
        ]
        for qid, number, customer, status, total, flag in rows:
            conn.execute(
                """INSERT INTO quotes_v2
                   (id, quote_number, customer_name, status, total, created_at, is_test)
                   VALUES (?, ?, ?, ?, ?, datetime('now'), ?)""",
                (qid, number, customer, status, total, flag),
            )
        found = query_open_quotes(conn)
    names = {q["name"] for q in found}
    customers = {q["customer"] for q in found}
    assert "EST-REAL-1" in names
    assert "Nelma Rivera" in customers
    for bad in (
        "EST-TT", "EST-HF", "EST-CC", "EST-RC", "EST-MK",
        "EST-TG", "EST-SM", "EST-DP", "EST-FLAG",
    ):
        assert bad not in names
    for name in (
        "TrustTest", "HOTFIX5 Probe", "Canonical Customer", "Routed Customer",
        "MOCK fixture", "TruthGuard lane", "SMOKE", "diag-probe-alpha",
    ):
        assert is_noise_client(name)
        assert name not in customers
    body, _ = job_forge_pipeline({"open_quotes": found, "jobs_active": [], "schedule_today": []})
    assert "TrustTest" not in body
    assert "230 open quotes" not in body
    assert "EST-REAL-1" in body


def test_forge_drawing_handler_does_not_call_pipeline(tmp_path, monkeypatch):
    from app.services.max.desks.base_desk import DeskTask
    from app.services.max.desks.forge_desk import ForgeDesk

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))

    async def _run():
        desk = ForgeDesk()
        task = DeskTask(
            id="d1",
            title="you change it",
            description=(
                'TempBanquette job — this layout was the older one, '
                'channel back at 12" wide, seat backs on cognac'
            ),
            customer_name="TempBanquette",
        )
        with patch(
            "app.services.drawing.job_drawing.generate_job_drawing",
            return_value={
                "success": True,
                "pdf_filename": "job_drawing_temp.pdf",
                "message": "New internal shop drawing for TempBanquette: job_drawing_temp.pdf. INTERNAL ONLY — never send to clients",
            },
        ) as gen, patch(
            "app.services.max.desks.job_runner.job_forge_pipeline",
            side_effect=AssertionError("pipeline must not run for a drawing task"),
        ):
            done = await desk._handle_task(task)
            gen.assert_called()
        return done

    done = asyncio.run(_run())
    assert done.result
    assert "INTERNAL ONLY" in done.result
    assert "Pipeline Summary" not in (done.result or "")
    assert "230" not in (done.result or "")


def test_job_drawing_turn_returns_desk_payload(monkeypatch, tmp_path):
    from app.services.drawing.job_drawing import run_job_drawing_turn

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    turn = run_job_drawing_turn(
        "can you give me a drawing of the TempBanquette job",
        job_hint="TempBanquette",
        layout_data=TEMP_LAYOUT,
    )
    assert turn["handled"] is True
    assert turn["success"] is True
    assert turn["model_used"] == "drawing-desk"
    assert turn["desk"] == "forge"
    assert "INTERNAL ONLY" in turn["response"]
    assert "Pipeline" not in turn["response"]
    skipped = run_job_drawing_turn("can you show me the Marley docs")
    assert skipped["handled"] is False


def test_change_it_turn_keeps_job_and_spec(monkeypatch, tmp_path):
    from app.services.drawing.job_drawing import generate_job_drawing

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    result = generate_job_drawing(
        message="you change it",
        history=MARLEY_HISTORY,
        layout_data=TEMP_LAYOUT,
    )
    assert result["success"]
    assert (result.get("job_hint") or "").lower().startswith("marley")
    assert result["dimensions"]["channel_width"] == '12"'
    assert result["fabrics"]["back"]["color"].lower() == "cognac"
    assert result["fabrics"]["seat"]["color"].lower() == "black"


def test_run_desk_task_forces_forge_for_drawing():
    from app.services.max.job_drawing_intent import force_drawing_desk

    assert force_drawing_desk(
        "you change it",
        "Marleys job drawing — channel back 12 wide, you change it",
        chosen="sales",
    ) == "forge"
    assert force_drawing_desk("pipeline report", "open quotes status", chosen="sales") == "sales"


def test_seventeen_desks_unchanged():
    from app.services.max.desks.desk_registry import DESK_ROSTER, live_desk_count
    assert len(DESK_ROSTER) == 17
    assert live_desk_count() == 17
    forge = next(d for d in DESK_ROSTER if d["id"] == "forge")
    assert "Drawing Studio" in forge["scope"]
    assert forge["agent"] == "Kai"
