"""Revision drawings: separate seat/back, no brand, current date, U+L set, fractions.

Temp data only. No live quotes or sends.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from app.services.drawing.client_material import (
    apply_seat_back_materials,
    client_facing_label,
    color_hex_for,
    strip_supplier_names,
)
from app.services.drawing.job_drawing import generate_job_drawing
from app.services.drawing.shop_date import shop_today
from app.services.drawing.mockup_engine import (
    marleys_u_and_l_preset,
    render_job_set_pdf,
    render_piece_mockup_pdf,
)
from app.services.drawing.mockup_engine.canvas_helpers import format_in


def extract_pdf_text(pdf_path: str) -> str:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_seat_and_back_are_separate_inputs():
    presets = marleys_u_and_l_preset()
    spec = presets["u_bench"].model_copy(deep=True)
    apply_seat_back_materials(
        spec.material,
        back={"code": "V100-Cognac", "color": "Cognac"},
        seat={"code": "V101-Black", "color": "Black"},
    )
    assert spec.material.back_color_label().lower() == "cognac"
    assert spec.material.seat_color_label().lower() == "black"
    assert spec.material.color_hex != spec.material.seat_color_hex
    assert spec.material.seat_color_hex == color_hex_for("black")
    assert spec.material.back_client_label() == "V100-Cognac"
    assert spec.material.seat_client_label() == "V101-Black"
    assert "apex" not in spec.material.name.lower()
    assert "spradling" not in spec.material.name.lower()


def test_client_label_never_prints_supplier():
    assert strip_supplier_names("Apex (Spradling Softside) vinyl") == ""
    assert "Spradling" not in client_facing_label("Apex (Spradling Softside) vinyl", material_type="vinyl")
    assert client_facing_label("cognac", color="Cognac", material_type="vinyl")


def test_revision_pdf_has_separate_labels_and_today(tmp_path):
    today = shop_today()
    presets = marleys_u_and_l_preset()
    u = presets["u_bench"].model_copy(deep=True)
    l = presets["l_bench"].model_copy(deep=True)
    for spec in (u, l):
        apply_seat_back_materials(
            spec.material,
            back={"code": "V100-Cognac", "color": "Cognac"},
            seat={"code": "V101-Black", "color": "Black"},
        )
        spec.revision = "B"
        spec.drawn_date = today
    path = tmp_path / "job_set_marley_REVB.pdf"
    render_job_set_pdf([u, l], str(path), revision="B", date_str=today)
    assert path.exists() and path.stat().st_size > 80
    text = extract_pdf_text(str(path))
    assert today in text
    assert "REV B" in text
    assert "V100-Cognac" in text
    assert "V101-Black" in text
    assert "Apex" not in text
    assert "Spradling" not in text
    assert "Softside" not in text
    assert "seat cushion, V101-Black" in text or "seat cushion: V101-Black" in text
    assert "channel back, V100-Cognac" in text
    assert "Marley's U Bench" in text or "MARLEY'S U BENCH" in text
    assert "Marley's L Bench" in text or "MARLEY'S L BENCH" in text
    assert re.findall(r"\d+\.\d+\"", text) == []
    assert format_in(249.75) == '249 3/4"'
    assert "249 3/4" in text
    assert "PAGE 1 / 4" in text or "PAGE 1 / 4" in text.replace("  ", " ")


def test_generate_job_drawing_revision_is_new_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    csv_path = tmp_path / "FABRIC_CODES.csv"
    csv_path.write_text(
        "code,color,material_type,width_inches,pattern_repeat_v,pattern_repeat_h,"
        "backing,specs,brand,supplier,supplier_sku,notes\n"
        "V100-Cognac,Cognac,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU1,\n"
        "V101-Black,Black,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU2,\n"
    )
    monkeypatch.setenv("EMPIRE_FABRIC_CODES_CSV", str(csv_path))
    first = generate_job_drawing(
        message=(
            'this layout was the older one, we need the one with channel back '
            'at 12" wide for all seat backs on cognac and seat cushion on black'
        ),
        job_hint="marleys",
    )
    assert first["success"]
    first_path = Path(first["pdf_path"])
    assert first_path.exists()
    assert first["drawn_date"] == shop_today()
    assert first["revision"]
    assert first_path.name != "mockup_marley_s_u_bench_f904d55bb684.pdf"
    assert "REV" in first_path.name
    text = extract_pdf_text(str(first_path))
    assert shop_today() in text
    assert "V100-Cognac" in text
    assert "V101-Black" in text
    assert "SecretBrand" not in text
    assert "Spradling" not in text
    assert first["fabrics"]["seat"]["color"].lower() == "black"
    assert first["fabrics"]["back"]["color"].lower() == "cognac"
    assert first.get("job_set") is True
    assert len(first.get("pieces") or []) == 2

    second = generate_job_drawing(
        message="you change it",
        history=[{"role": "user", "content": "drawing of the marleys job, seat cushion on black"}],
        job_hint="marleys",
    )
    assert second["success"]
    assert Path(second["pdf_path"]).resolve() != first_path.resolve()
    assert Path(second["pdf_path"]).stat().st_mtime >= first_path.stat().st_mtime


def test_single_piece_still_uses_today_not_oct8(tmp_path):
    spec = marleys_u_and_l_preset()["u_bench"].model_copy(deep=True)
    apply_seat_back_materials(
        spec.material,
        back={"color": "Cognac"},
        seat={"color": "Black"},
    )
    path = tmp_path / "u_only.pdf"
    render_piece_mockup_pdf(spec, str(path))
    text = extract_pdf_text(str(path))
    assert shop_today() in text
    assert "2026-10-08" not in text
    assert "Apex" not in text
    assert "Spradling" not in text
    assert "Black" in text
    assert "Cognac" in text or "cognac" in text
