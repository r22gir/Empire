"""Standard upholstery / banquette shop-drawing template.

Fixture data only. No live quotes, sends, or contacts.
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

import pytest

from app.services.drawing.templates.banquette_fixtures import (
    marleys_job_layouts,
    marleys_standard_job,
)
from app.services.drawing.templates.banquette_job import (
    MAX_SEAT_LENGTH_IN,
    channel_option_a,
    inch_text,
    result_cut_list,
    return_seat_length_in,
    schedule_rows,
    split_equal_seats,
)
from app.services.drawing.templates.banquette_standard import (
    pages_for_job,
    render_banquette_job_pdf,
)


def extract_pdf_text(pdf_path: str) -> str:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_pages(pdf_path: str) -> list[str]:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def test_channel_option_a_matches_shop_rule():
    um = channel_option_a(249.75, 12.0, "UM", odd_at="left corner")
    assert len(um) == 21
    assert um[0].is_odd and um[0].width_in == pytest.approx(9.75)
    assert all(not c.is_odd and c.width_in == 12.0 for c in um[1:])
    assert sum(c.width_in for c in um) == pytest.approx(249.75)

    ul = channel_option_a(37.75, 12.0, "UL", odd_at="open end")
    assert [round(c.width_in, 4) for c in ul] == [12.0, 12.0, 13.75]
    assert ul[-1].is_odd

    ur = channel_option_a(48.5, 12.0, "UR", odd_at="open end")
    assert [round(c.width_in, 4) for c in ur] == [12.0, 12.0, 12.0, 12.5]

    ll = channel_option_a(107.75, 12.0, "LL", odd_at="open end")
    assert len(ll) == 9
    assert ll[-1].width_in == pytest.approx(11.75)

    ls = channel_option_a(95.375, 12.0, "LS", odd_at="open end")
    assert len(ls) == 8
    assert ls[-1].width_in == pytest.approx(11.375)


def test_seat_splits_and_u_l_joints():
    assert split_equal_seats(249.75) == pytest.approx([83.25, 83.25, 83.25])
    assert split_equal_seats(107.75) == pytest.approx([53.875, 53.875])
    assert all(x <= MAX_SEAT_LENGTH_IN for x in split_equal_seats(249.75))
    # open end = back stack + arm run; seat butts main front
    us4 = return_seat_length_in(2.5625, 37.75, 20.5625)
    us5 = return_seat_length_in(2.5625, 48.5, 20.5625)
    ls3 = return_seat_length_in(2.5625, 95.375, 20.5625)
    assert us4 == pytest.approx(19.75)
    assert us5 == pytest.approx(30.5)
    assert ls3 == pytest.approx(77.375)


def test_fractions_never_decimals():
    assert inch_text(20.5625) == '20 9/16"'
    assert inch_text(249.75) == '249 3/4"'
    assert inch_text(26.75) == '26 3/4"'
    assert "." not in inch_text(20.5625)
    assert "." not in inch_text(11.375)


def test_cut_sizes_wood_foam_fabric():
    job = marleys_standard_job()
    rows = schedule_rows(job)
    seats = [r for r in rows if r.part.startswith("Seat")]
    channels = [r for r in rows if "channel" in r.part.lower()]
    assert len(seats) == 8
    assert sum(r.qty for r in channels) == 45
    for row in rows:
        assert row.wood_size == f"{inch_text(row.wood_w)} x {inch_text(row.wood_l)}"
        assert row.foam_size.startswith(row.wood_size)
        assert '30 9/16"' in row.fabric_size or '22"' in row.fabric_size or "x" in row.fabric_size
        fw = row.wood_w + 2 * 5
        fl = row.wood_l + 2 * 5
        assert row.fabric_size.startswith(f"{inch_text(fw)} x {inch_text(fl)}")
        assert "." not in row.wood_size
        assert "." not in row.fabric_size
    cuts = result_cut_list(job)
    assert cuts["wood"][0]["size"] == cuts["foam"][0]["size"]
    assert "WOOD" in cuts["wood"][0]["label"]
    assert "FOAM" in cuts["foam"][0]["label"]
    assert "FABRIC" in cuts["fabric"][0]["label"]
    assert cuts["wood"][0]["size"] != cuts["fabric"][0]["size"]


def test_marleys_fixture_is_u_and_l_not_renderer_hardcode():
    layouts = marleys_job_layouts()
    assert len(layouts) == 2
    assert layouts[0]["shape"] == "u_shape"
    assert layouts[1]["shape"] == "l_shape"
    assert layouts[0]["depth_in"] == pytest.approx(20.5625)
    job = marleys_standard_job()
    assert job.seat_fabric.code == "V008-Bittersweet"
    assert job.back_fabric.code == "V003-Cognac"
    assert "Spradling" not in job.seat_fabric.sheet_label
    assert pages_for_job(job) == 5


def test_marleys_pdf_matches_reference_language(tmp_path):
    today = date.today().isoformat()
    job = marleys_standard_job(revision="C", drawn_date=today)
    path = tmp_path / "marleys_standard.pdf"
    render_banquette_job_pdf(job, path)
    assert path.exists() and path.stat().st_size > 2000
    pages = extract_pages(str(path))
    assert len(pages) == 5
    blob = "\n".join(pages)
    assert "EMPIRE WORKROOM" in blob
    assert "DRAFT / INTERNAL" in blob
    assert today in blob
    assert today in blob
    assert f"{today} · C" in blob
    assert "V003-Cognac" in blob
    assert "V008-Bittersweet" in blob
    assert "Spradling" not in blob
    assert "Apex" not in blob
    assert "Kravet" not in blob
    assert re.findall(r"\d+\.\d+\"", blob) == []
    # page-for-page content vs the 2026-10-21 reference
    assert "TOP VIEW PLAN — U booth" in pages[0]
    assert "249 3/4" in pages[0]
    assert "20 9/16" in pages[0]
    assert "US1" in pages[0] and "US4" in pages[0] and "US5" in pages[0]
    assert "OPEN END" in pages[0]
    assert "SCALE BAR" in pages[0]
    assert "Quoted runs" in pages[0]
    assert "TOP VIEW PLAN — L booth" in pages[1]
    assert "107 3/4" in pages[1]
    assert "LS1" in pages[1] and "LS3" in pages[1]
    assert "FRONT ELEVATIONS" in pages[2]
    assert "SIDE SECTION" in pages[2]
    assert "PART SCHEDULE" in pages[3]
    assert "WOOD cut" in pages[3]
    assert "FOAM cut" in pages[3]
    assert "FABRIC cut" in pages[3]
    assert "WOOD CUT — TRUE SIZE" in pages[3]
    assert "CONFLICTS" in pages[4]
    assert "OPEN ITEMS" in pages[4]
    assert "prices not updated" in pages[4] or "pricing not updated" in pages[4]


def test_straight_bench_job_from_layout(tmp_path):
    from app.services.drawing.templates.banquette_job import build_banquette_job

    job = build_banquette_job(
        layouts=[{
            "shape": "straight",
            "width_in": 96,
            "depth_in": 16,
            "back_height_in": 26.75,
            "channel_width_in": 12,
            "foam_thickness_in": 2.0,
            "piece_name": "Temp straight",
            "client_name": "TempBanquette Client",
            "project_name": "TempBanquette booth",
        }],
        fabrics={
            "back": {"code": "V100-Cognac", "color": "Cognac", "label": "V100-Cognac"},
            "seat": {"code": "V101-Black", "color": "Black", "label": "V101-Black"},
        },
        conflicts=["Channel width 12\" conflicts with estimate 10\" — flagged, prices not changed."],
        quote=None,
        revision="A",
        drawn_date=date.today().isoformat(),
        job_hint="TempBanquette",
    )
    assert job.benches[0].shape == "straight"
    assert len(job.benches[0].runs[0].channels) == 8
    assert all(not c.is_odd for c in job.benches[0].runs[0].channels)
    path = tmp_path / "straight.pdf"
    render_banquette_job_pdf(job, path)
    text = extract_pdf_text(str(path))
    assert "EMPIRE WORKROOM" in text
    assert "V100-Cognac" in text
    assert "V101-Black" in text
    assert "prices not changed" in text
    assert "TOP VIEW PLAN — straight" in text
    assert re.findall(r"\d+\.\d+\"", text) == []


def test_generate_job_drawing_uses_standard_template(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    csv_path = tmp_path / "FABRIC_CODES.csv"
    csv_path.write_text(
        "code,color,material_type,width_inches,pattern_repeat_v,pattern_repeat_h,"
        "backing,specs,brand,supplier,supplier_sku,notes\n"
        "V003-Cognac,Cognac,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU1,\n"
        "V008-Bittersweet,Bittersweet,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU2,\n"
    )
    monkeypatch.setenv("EMPIRE_FABRIC_CODES_CSV", str(csv_path))
    first = generate_job_drawing(
        message=(
            'this layout was the older one, we need the one with channel back '
            'at 12" wide for all seat backs on cognac and seat cushion on bittersweet'
        ),
        job_hint="marleys",
    )
    assert first["success"]
    assert first.get("job_set") is True
    assert len(first.get("pieces") or []) == 2
    pdf = Path(first["pdf_path"])
    assert pdf.exists()
    assert "REV" in pdf.name
    assert pdf.stat().st_size > 2000
    text = extract_pdf_text(str(pdf))
    assert date.today().isoformat() in text
    assert "EMPIRE WORKROOM" in text
    assert "V003-Cognac" in text
    assert "V008-Bittersweet" in text
    assert "SecretBrand" not in text
    assert "HiddenSupplier" not in text
    assert "20 9/16" in text
    assert "FRONT ELEVATIONS" in text
    assert "PART SCHEDULE" in text
    second = generate_job_drawing(
        message="you change it",
        history=[{"role": "user", "content": "drawing of the marleys job, seat cushion on bittersweet"}],
        job_hint="marleys",
    )
    assert second["success"]
    assert Path(second["pdf_path"]).resolve() != pdf.resolve()
    from app.services.max.latest_job_file import find_newest_job_document
    looked = find_newest_job_document(
        "Send me a link",
        [{"role": "user", "content": "drawing of the marleys job"}],
        drawings_dir=tmp_path,
    )
    assert looked["found"]
    assert looked["match"]["name"] == Path(second["pdf_path"]).name
