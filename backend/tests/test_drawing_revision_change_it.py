"""Night Lab RED — Max drawing revisions must apply new specs.

'change it' (e.g. seat cushions to Black V001-Raven, backs 12\" channel
V003-Cognac) carries the job + prior specs, applies the new specs, writes
a new REV letter PDF, and only claims success when the generated output
actually shows those changes.

Temp dirs / mock quotes only. No live quotes, sends, or contacts.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.drawing.job_drawing import (
    generate_job_drawing,
    run_job_drawing_turn,
    verify_specs_in_output,
)
from app.services.max.job_drawing_intent import (
    extract_spec_changes,
    merge_drawing_job_context,
    should_route_to_drawing_desk,
)


OLDER_LAYOUT_MSG = (
    "make a drawing for the Marley's job with 10 inch channels "
    "and seat cushions on V008-Bittersweet"
)
CHANGE_IT_MSG = (
    'change it: seat cushions to Black V001-Raven, '
    'backs 12" channel V003-Cognac'
)

HISTORY = [
    {"role": "user", "content": OLDER_LAYOUT_MSG},
    {"role": "assistant", "content": "New drawing for Marley's (REV A)"},
]

MOCK_QUOTE = {
    "customer_name": "Marley's",
    "quote_number": "EST-TEMP-REV",
    "project_name": "Marley's Hyattsville",
    "line_items": [],
    "total": 0,
}


def extract_pages(pdf_path: str) -> list[str]:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


@pytest.fixture
def drawings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setattr(
        "app.services.drawing.job_drawing.resolve_job_quote",
        lambda hint: dict(MOCK_QUOTE),
    )
    return tmp_path


def test_nightlab_change_it_phrase_parses_new_specs():
    changes = extract_spec_changes(CHANGE_IT_MSG)
    assert changes["channel_width_in"] == 12
    assert str(changes["seat_fabric"]).upper().startswith("V001")
    assert str(changes["back_fabric"]).upper().startswith("V003")
    ctx = merge_drawing_job_context("you change it", HISTORY)
    assert (ctx["job_hint"] or "").lower().startswith("marley")
    assert ctx["spec_changes"]["channel_width_in"] == 10
    assert "v008" in str(ctx["spec_changes"]["seat_fabric"]).lower()
    merged = merge_drawing_job_context(CHANGE_IT_MSG, HISTORY)
    assert merged["spec_changes"]["channel_width_in"] == 12
    assert str(merged["spec_changes"]["seat_fabric"]).upper().startswith("V001")
    assert str(merged["spec_changes"]["back_fabric"]).upper().startswith("V003")
    assert should_route_to_drawing_desk(CHANGE_IT_MSG, HISTORY)
    assert should_route_to_drawing_desk("you change it", HISTORY)


def test_spec_carry_over_and_change_application(drawings_dir):
    first = generate_job_drawing(
        message=OLDER_LAYOUT_MSG,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert first["success"] is True
    assert first["revision"] == "A"
    assert first["dimensions"]["channel_width"] == '10"'
    assert first["fabrics"]["seat"]["code"] == "V008-Bittersweet"
    before_pages = extract_pages(first["pdf_path"])
    before_blob = "\n".join(before_pages)
    assert "V008-Bittersweet" in before_blob
    assert '10"' in before_blob or "@ 10" in before_blob

    turn = run_job_drawing_turn(
        CHANGE_IT_MSG,
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert turn["handled"] is True
    assert turn["success"] is True
    result = turn["result"]
    assert (result.get("job_hint") or "").lower().startswith("marley")
    assert result["revision"] == "B"
    assert result["specs_honored"] is True
    assert result["dimensions"]["channel_width"] == '12"'
    assert result["fabrics"]["seat"]["code"] == "V001-Raven"
    assert result["fabrics"]["seat"]["color"].lower() == "black"
    assert result["fabrics"]["back"]["code"] == "V003-Cognac"
    assert Path(result["pdf_path"]).resolve() != Path(first["pdf_path"]).resolve()
    assert "REV B" in Path(result["pdf_path"]).name.upper().replace("REVB", "REV B") or "REVB" in Path(result["pdf_path"]).name.upper()
    assert "New drawing" in turn["response"]
    pages = extract_pages(result["pdf_path"])
    blob = "\n".join(pages)
    assert "V001-Raven" in blob
    assert "V003-Cognac" in blob
    assert "V008-Bittersweet" not in blob
    assert '12"' in blob or "@ 12" in blob
    assert "Spradling" not in blob
    assert "Apex" not in blob
    assert re.findall(r"\d+\.\d+\"", blob) == []
    wood = (result.get("cut_list") or {}).get("wood") or []
    fabric = (result.get("cut_list") or {}).get("fabric") or []
    channels = [w for w in wood if "channel" in str(w.get("part") or "").lower()]
    assert channels
    std = next(c for c in channels if abs(float(c.get("width") or 0) - 12) < 0.05)
    fab = next(f for f in fabric if f.get("part") == std.get("part"))
    assert abs(float(fab["width"]) - (12 + 2 * 5)) < 0.05
    assert std["size"] == next(
        f["size"] for f in result["cut_list"]["foam"] if f.get("part") == std.get("part")
    )


def test_false_success_guard_requires_pdf_to_show_specs(drawings_dir):
    """A generated file that does not show the new specs is not a new drawing."""
    stale = (
        "EMPIRE WORKROOM\nREV A\nChannel back 10\" — V008-Bittersweet\n"
        "Seat — V008-Bittersweet\n"
    )
    result = generate_job_drawing(
        message=CHANGE_IT_MSG,
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
        verify_pdf_text=stale,
    )
    assert result["success"] is False
    assert result["specs_honored"] is False
    assert result["spec_mismatches"]
    assert "New drawing" not in result["message"]
    assert "was not applied" in result["message"]
    turn = run_job_drawing_turn(
        CHANGE_IT_MSG,
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
        verify_pdf_text=stale,
    )
    assert turn["handled"] is True
    assert turn["success"] is False
    assert "New drawing" not in turn["response"]
    assert "I will not call this a new drawing" in turn["response"]


def test_verify_specs_in_output_reads_pdf_not_memory():
    misses = verify_specs_in_output(
        pdf_path=None,
        requested={"channel_width_in": 12, "seat_fabric": "V001-Raven", "back_fabric": "V003-Cognac"},
        channel_in=12.0,
        fabrics={
            "seat": {"code": "V001-Raven", "color": "Black", "label": "V001-Raven Black"},
            "back": {"code": "V003-Cognac", "color": "Cognac", "label": "V003-Cognac"},
        },
        pdf_text='Channel back 10" — V008-Bittersweet\nSeat — V008-Bittersweet',
    )
    assert any("12" in m for m in misses)
    assert any("v001" in m.lower() or "seat" in m.lower() for m in misses)


def test_max_chat_path_revision_before_after(drawings_dir, monkeypatch):
    """Same function both /chat doors call: run_job_drawing_turn."""
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")

    first = run_job_drawing_turn(
        OLDER_LAYOUT_MSG,
        history=[],
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert first["handled"] is True
    assert first["model_used"] == "drawing-desk"
    assert first["success"] is True
    before = first["result"]
    assert before["revision"] == "A"
    assert before["dimensions"]["channel_width"] == '10"'
    assert before["fabrics"]["seat"]["code"] == "V008-Bittersweet"
    before_path = Path(before["pdf_path"])
    assert before_path.exists()

    second = run_job_drawing_turn(
        CHANGE_IT_MSG,
        history=[
            {"role": "user", "content": OLDER_LAYOUT_MSG},
            {"role": "assistant", "content": first["response"]},
        ],
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert second["handled"] is True
    assert second["model_used"] == "drawing-desk"
    assert second["success"] is True
    after = second["result"]
    assert after["revision"] == "B"
    assert after["specs_honored"] is True
    assert after["dimensions"]["channel_width"] == '12"'
    assert after["fabrics"]["seat"]["code"] == "V001-Raven"
    assert after["fabrics"]["back"]["code"] == "V003-Cognac"
    assert "New drawing" in second["response"]
    after_path = Path(after["pdf_path"])
    assert after_path.exists()
    assert after_path.resolve() != before_path.resolve()
    blob = "\n".join(extract_pages(str(after_path)))
    assert "V001-Raven" in blob
    assert "V003-Cognac" in blob
    assert "V008-Bittersweet" not in blob


def test_chat_and_stream_share_drawing_desk_door():
    """Both Max chat doors must call the same drawing-desk helper."""
    src = Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py"
    text = src.read_text(encoding="utf-8")
    assert text.count("_maybe_job_drawing_desk_response") >= 3
    assert "run_job_drawing_turn(" in text


def test_opaque_job_id_does_not_drop_named_job(drawings_dir):
    result = generate_job_drawing(
        message=CHANGE_IT_MSG,
        history=HISTORY,
        job_hint="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        job_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        quote=MOCK_QUOTE,
    )
    assert (result.get("job_hint") or "").lower().startswith("marley")
    assert result["success"] is True
    assert result["fabrics"]["seat"]["code"] == "V001-Raven"
    assert result["dimensions"]["channel_width"] == '12"'
