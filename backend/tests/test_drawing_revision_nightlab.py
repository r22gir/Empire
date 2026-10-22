"""Night Lab 2026-10-22 FP-2/3/4/5 — drawing revisions, letters, layout, codes.

Temp dirs and fixture layouts only. No live quotes, sends, or contacts.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.drawing.job_drawing import (
    generate_job_drawing,
    next_revision_letter,
    resolve_internal_fabric,
    run_job_drawing_turn,
)
from app.services.max.job_drawing_intent import (
    extract_spec_changes,
    should_route_to_drawing_desk,
)


HISTORY = [
    {"role": "user", "content": "make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black"},
    {"role": "assistant", "content": "New drawing for Marley's (REV A)"},
]

MOCK_QUOTE = {
    "customer_name": "Marley's",
    "quote_number": "EST-TEMP-NL",
    "project_name": "Marley's Hyattsville",
    "line_items": [],
    "total": 0,
}


def extract_pages(pdf_path: str) -> list[str]:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def _page_words(pdf_path: str, page_index: int) -> list[dict]:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        return page.extract_words() or []


def _no_clip(words: list[dict], page_w: float, page_h: float, margin: float = 18.0) -> None:
    for word in words:
        assert word["x0"] >= margin - 1, f"clipped left {word}"
        assert word["x1"] <= page_w - margin + 1, f"clipped right {word!r} x1={word['x1']} page_w={page_w}"
        assert word["top"] >= 4, f"clipped top {word}"
        assert word["bottom"] <= page_h - 4, f"clipped bottom {word}"


def _overlaps(words: list[dict], *, min_pt: float = 2.5) -> list[tuple[str, str]]:
    hits = []
    for i, a in enumerate(words):
        if len(a["text"]) < 2:
            continue
        for b in words[i + 1 :]:
            if len(b["text"]) < 2:
                continue
            if a["text"] == b["text"] and abs(a["x0"] - b["x0"]) < 1 and abs(a["top"] - b["top"]) < 1:
                continue
            ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            oy = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
            if ox > min_pt and oy > min_pt:
                hits.append((a["text"], b["text"]))
    return hits


@pytest.fixture
def drawings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setattr(
        "app.services.drawing.job_drawing.resolve_job_quote",
        lambda hint: dict(MOCK_QUOTE),
    )
    return tmp_path


def test_nightlab_phrases_parse_and_route():
    assert extract_spec_changes("channel width 10 inch")["channel_width_in"] == 10
    assert extract_spec_changes("change it to 10 inch channels")["channel_width_in"] == 10
    assert extract_spec_changes('change it: make the channels 10" wide and seats V008-Bittersweet')["channel_width_in"] == 10
    assert extract_spec_changes("make the channels 10 inches")["channel_width_in"] == 10
    for phrase in (
        "change it to 10 inch channels",
        'change it: make the channels 10" wide and seats V008-Bittersweet',
        "make the channels 10 inches",
        "use V008-Bittersweet for the seats",
        "seat cushions on Black",
        "redo the drawing with black seats",
        "can you change the drawing",
        "change the drawing to 10 inch channels",
        "revise the drawing: channel width 10 inch, seat cushions on V008-Bittersweet",
    ):
        assert should_route_to_drawing_desk(phrase, HISTORY), phrase
    # Spec-only follow-ups need a drawing already in the thread.
    for phrase in (
        "change it to 10 inch channels",
        "make the channels 10 inches",
        "use V008-Bittersweet for the seats",
        "redo the drawing with black seats",
        "can you change the drawing",
        "change the drawing to 10 inch channels",
    ):
        assert not should_route_to_drawing_desk(phrase, []), phrase


def test_black_and_cognac_resolve_to_workroom_codes():
    black = resolve_internal_fabric("Black")
    assert black["code"] == "V001-Raven"
    assert black["color"].lower() == "black"
    assert "spradling" not in (black["label"] or "").lower()
    cognac = resolve_internal_fabric("Cognac")
    assert cognac["code"] == "V003-Cognac"
    raven = resolve_internal_fabric("V001-Raven")
    assert raven["code"] == "V001-Raven"
    assert raven["color"].lower() == "black"


def test_revision_letters_are_sequential(drawings_dir):
    assert next_revision_letter(drawings_dir, "marleys") == "A"
    letters = []
    for msg in (
        "make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black",
        "change it",
        "change it to 10 inch channels",
    ):
        result = generate_job_drawing(
            message=msg,
            history=HISTORY,
            job_hint="marleys",
            quote=MOCK_QUOTE,
        )
        assert result["success"]
        letters.append(result["revision"])
        # Shop PDFs must not consume a letter.
        shop = Path(result.get("shop_pdf_path") or "")
        assert shop.exists()
    assert letters == ["A", "B", "C"]


def test_ten_inch_revision_via_chat_path(drawings_dir):
    first = generate_job_drawing(
        message="make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black",
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert first["success"]
    assert first["revision"] == "A"
    assert first["fabrics"]["seat"]["code"] == "V001-Raven"
    assert first["fabrics"]["back"]["code"] == "V003-Cognac"

    turn = run_job_drawing_turn(
        "revise the drawing: channel width 10 inch, seat cushions on V008-Bittersweet",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert turn["handled"] is True
    assert turn["success"] is True
    result = turn["result"]
    assert result["specs_honored"] is True
    assert result["revision"] == "B"
    assert result["dimensions"]["channel_width"] == '10"'
    assert result["fabrics"]["seat"]["code"] == "V008-Bittersweet"
    assert result["fabrics"]["back"]["code"] == "V003-Cognac"
    assert "New drawing" in turn["response"]
    assert "I will not call this a new drawing" not in turn["response"]
    channel_wood = [
        item for item in (result.get("cut_list") or {}).get("wood") or []
        if "channel" in str(item.get("part") or "").lower()
    ]
    assert any(abs(float(item.get("width") or 0) - 10) < 0.05 for item in channel_wood)
    pages = extract_pages(result["pdf_path"])
    blob = "\n".join(pages)
    assert "@ 10" in blob or '10"' in blob
    assert "V008-Bittersweet" in blob
    assert "V003-Cognac" in blob
    assert "Spradling" not in blob
    assert "Apex" not in blob
    assert re.findall(r"\d+\.\d+\"", blob) == []
    # Wood/foam vs fabric: fabric = wood + 2 x 5
    channels = [
        item for item in result["cut_list"]["wood"]
        if "channel" in str(item.get("part") or "").lower()
    ]
    assert channels
    wood = next(c for c in channels if abs(float(c["width"]) - 10) < 0.05)
    fabric = next(
        f for f in result["cut_list"]["fabric"]
        if f.get("part") == wood.get("part")
    )
    assert wood["size"] == next(
        f["size"] for f in result["cut_list"]["foam"] if f.get("part") == wood.get("part")
    )
    assert abs(float(fabric["width"]) - (10 + 2 * 5)) < 0.05


def test_change_it_to_ten_inch_channels_routes_and_applies(drawings_dir):
    generate_job_drawing(
        message="make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black",
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    turn = run_job_drawing_turn(
        "change it to 10 inch channels",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert turn["handled"] is True
    result = turn["result"]
    assert result["dimensions"]["channel_width"] == '10"'
    assert result["specs_honored"] is True
    assert result["revision"] == "B"
    assert "New drawing" in turn["response"]


def test_unapplied_spec_is_not_announced_as_new(drawings_dir, monkeypatch):
    from app.services.drawing import job_drawing as jd

    real = jd._requested_vs_applied

    def force_miss(requested, channel_in, fabrics):
        if requested.get("channel_width_in"):
            return [f"channel width {requested['channel_width_in']} was not applied (drawing has 12\")"]
        return real(requested, channel_in, fabrics)

    monkeypatch.setattr(jd, "_requested_vs_applied", force_miss)
    result = generate_job_drawing(
        message="revise the drawing: channel width 10 inch",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert result["success"]
    assert result["specs_honored"] is False
    assert "New drawing" not in result["message"]
    assert "was not applied" in result["message"]


def test_pages_do_not_clip_or_overlap(drawings_dir):
    import pdfplumber

    result = generate_job_drawing(
        message="revise the drawing: channel width 10 inch, seat cushions on Black",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert result["success"]
    path = result["pdf_path"]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 5
        page2 = pdf.pages[1]
        page3 = pdf.pages[2]
        w2 = page2.extract_words() or []
        w3 = page3.extract_words() or []
        _no_clip(w2, float(page2.width), float(page2.height))
        _no_clip(w3, float(page3.width), float(page3.height))
        page3_text = page3.extract_text() or ""
        assert len(re.findall(r"SIDE SECTION", page3_text)) <= 2
        note_words = [wd for wd in w2 if wd["x0"] > 850]
        for a, b in _overlaps(note_words, min_pt=3.0):
            pytest.fail(f"page 2 notes overlap {a!r} / {b!r}")
        captions = [wd for wd in w3 if "channel" in wd["text"].lower() or "ODD" in wd["text"]]
        for a, b in _overlaps(captions, min_pt=3.0):
            pytest.fail(f"page 3 caption overlap {a!r} / {b!r}")


def test_chat_path_returns_public_link(drawings_dir, monkeypatch):
    """Same entry the router uses: run_job_drawing_turn(message, history, job_id)."""
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")

    generate_job_drawing(
        message="make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black",
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    turn = run_job_drawing_turn(
        "change it to 10 inch channels",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert turn["handled"] is True
    assert turn["success"] is True
    assert "New drawing" in turn["response"]
    assert "10" in turn["response"]
    assert "https://studio.empirebox.store/api/v1/files/found?t=" in turn["response"]
    result = turn["result"]
    assert result["dimensions"]["channel_width"] == '10"'
    assert result["share_url"].startswith("https://studio.empirebox.store/api/v1/files/found?t=")
    assert Path(result["pdf_path"]).exists()
