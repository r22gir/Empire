"""Revision drawings: separate seat/back colors, full job set, new file + studio URL.

No live quotes, no real sends, no real contacts.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.drawing.mockup_engine.finish import (
    apply_seat_back_finish,
    client_facing_label,
    color_hex_for_name,
    is_dark_hex,
    luminance,
    strip_supplier_brand,
)
from app.services.max.drawing_share import (
    clear_drawings,
    is_drawing_ready_followup,
    is_show_link_request,
    remember_drawing,
    verify_generated_file,
    wants_studio_share,
)


def _lum(hex_color: str) -> float:
    return luminance(hex_color)


def test_color_hex_black_is_dark_cognac_is_cognac():
    black = color_hex_for_name("black")
    cognac = color_hex_for_name("cognac")
    assert black.lower() == "#1a1a1a"
    assert cognac.lower() == "#9a5b2e"
    assert is_dark_hex(black)
    assert not is_dark_hex(cognac)
    assert _lum(black) < 0.22 < _lum(cognac)


def test_client_facing_label_uses_code_never_brand():
    assert client_facing_label(code="V100-Cognac", color="Cognac", material_type="vinyl") == "V100-Cognac"
    assert "vinyl" in client_facing_label(color="Black", material_type="vinyl").lower()
    assert "black" in client_facing_label(color="Black", material_type="vinyl").lower()
    assert strip_supplier_brand("Apex (Spradling Softside) vinyl") == ""
    assert "spradling" not in client_facing_label(
        code=None, color="Cognac", material_type="Apex (Spradling Softside) vinyl"
    ).lower()


def test_apply_seat_back_finish_keeps_inputs_separate():
    from app.services.drawing.mockup_engine.spec import MaterialFinishSpec

    mat = MaterialFinishSpec()
    apply_seat_back_finish(
        mat,
        back={"color": "cognac", "code": "V100-Cognac", "material_type": "vinyl"},
        seat={"color": "black", "code": "V101-Black", "material_type": "vinyl"},
    )
    assert mat.color_name.lower() == "cognac"
    assert mat.seat_color_name.lower() == "black"
    assert is_dark_hex(mat.seat_color_hex)
    assert not is_dark_hex(mat.color_hex)
    assert mat.color_hex.lower() != mat.seat_color_hex.lower()
    assert "apex" not in (mat.name or "").lower()
    assert "spradling" not in (mat.name or "").lower()


def test_revision_renders_black_seats_cognac_backs(tmp_path, monkeypatch):
    import pdfplumber
    from app.services.drawing.job_drawing import generate_job_drawing

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    csv_path = tmp_path / "FABRIC_CODES.csv"
    csv_path.write_text(
        "code,color,material_type,width_inches,pattern_repeat_v,pattern_repeat_h,"
        "backing,specs,brand,supplier,supplier_sku,notes\n"
        "V100-Cognac,Cognac,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU1,\n"
        "V101-Black,Black,vinyl,54,0,0,,,,SecretBrand,HiddenSupplier,SKU2,\n"
    )
    monkeypatch.setenv("EMPIRE_FABRIC_CODES_CSV", str(csv_path))
    clear_drawings()

    result = generate_job_drawing(
        message=(
            'Marleys job — this layout was the older one, we need channel back '
            'at 12" wide for all seat backs on cognac and seat cushion on black'
        ),
        job_hint="Marley's",
        conversation_id="conv-rev-1",
    )
    assert result["success"] is True
    assert result["piece_count"] == 2
    names = " ".join(result.get("piece_names") or []).lower()
    assert "u" in names and "l" in names
    assert result["sheet_date"] == date.today().isoformat()
    assert result["revision"] >= 1
    pdf = Path(result["pdf_path"])
    assert pdf.exists() and pdf.stat().st_size > 80
    assert pdf.name != "mockup_marley_s_u_bench_f904d55bb684.pdf"
    assert f"rev{result['revision']}" in pdf.name.lower()
    assert date.today().isoformat().replace("-", "") in pdf.name
    assert result["pdf_verified"] is True
    assert result["share_url"].startswith("https://studio.empirebox.store/api/v1/files/found?t=")
    assert result["share_url"] in (result.get("message") or "")

    fabrics = result["fabrics"]
    assert fabrics["back"]["code"] == "V100-Cognac"
    assert fabrics["seat"]["code"] == "V101-Black"
    assert is_dark_hex(fabrics["seat"]["hex"])
    assert not is_dark_hex(fabrics["back"]["hex"])

    with pdfplumber.open(str(pdf)) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
        assert len(doc.pages) >= 4
    low = text.lower()
    assert "marley's u" in low or "u bench" in low
    assert "marley's l" in low or "l bench" in low
    assert "apex" not in low
    assert "spradling" not in low
    assert "softside" not in low
    assert "secretbrand" not in low
    assert "hiddensupplier" not in low
    assert "v100-cognac" in low
    assert "v101-black" in low or "black" in low
    assert "plain cognac" not in low
    assert date.today().isoformat() in text
    assert not __import__("re").findall(r"\d+\.\d+\"", text)


def test_never_reuses_older_file(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    stale = tmp_path / "mockup_marley_s_u_bench_f904d55bb684.pdf"
    stale.write_bytes(b"%PDF-1.4 stale oct 8 drawing\n" + b"x" * 200)
    os.utime(stale, (1_000_000_000, 1_000_000_000))
    clear_drawings()

    result = generate_job_drawing(
        message='revise the Marleys job drawing, channel back at 12" wide, seats on black',
        job_hint="Marley's",
        conversation_id="conv-rev-2",
    )
    assert result["success"]
    assert Path(result["pdf_path"]).resolve() != stale.resolve()
    assert "f904d55bb684" not in result["pdf_filename"]
    assert result["pdf_mtime"] > stale.stat().st_mtime
    assert result["share_url"].startswith("https://studio.empirebox.store/")


def test_show_link_followup_returns_just_generated_url(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing, run_job_drawing_turn
    from app.services.max.quick_replies import direct_reply

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    clear_drawings()
    history = [
        {"role": "user", "content": "give me a drawing of the marleys job"},
        {"role": "assistant", "content": "working on the revision"},
        {
            "role": "user",
            "content": 'channel back at 12" wide, seat backs on cognac, seat cushion on black',
        },
    ]
    first = generate_job_drawing(
        message=history[-1]["content"],
        history=history,
        conversation_id="conv-link",
    )
    assert first["success"]
    url = first["share_url"]
    history = history + [
        {"role": "assistant", "content": first["message"]},
    ]
    assert is_show_link_request("done? show it")
    assert is_show_link_request("give me link")
    assert is_drawing_ready_followup("give me the link", history)

    hijack = direct_reply(
        "where is the drawing, give me the link",
        history=history,
        conversation_id="conv-link",
    )
    assert hijack is not None
    assert hijack["skill"] == "drawing_share"
    assert hijack["share_url"] == url
    assert "final-docs" not in hijack["text"].lower()
    assert "live UI map" not in hijack["text"]

    follow = run_job_drawing_turn(
        "done? show it",
        history=history,
        conversation_id="conv-link",
    )
    assert follow["handled"] is True
    assert url in follow["response"]
    assert follow["result"]["pdf_path"] == first["pdf_path"]


def test_canned_shortcuts_do_not_hijack_without_history():
    from app.services.max.quick_replies import direct_reply

    # Bare greeting still works.
    assert direct_reply("Hi")["skill"] == "greeting"
    # A docs-location ask with no drawing in the chat still lists Final Docs.
    out = direct_reply("where are my docs")
    assert out and out["skill"] == "docs_location"


def test_verify_generated_file_rejects_stale(tmp_path):
    stale = tmp_path / "old.pdf"
    stale.write_bytes(b"%PDF-1.4 " + b"x" * 100)
    os.utime(stale, (1_000_000, 1_000_000))
    proof = verify_generated_file(stale, min_mtime=1_700_000_000)
    assert proof["ok"] is False
    assert proof["error"] == "stale_mtime"
    fresh = tmp_path / "new.pdf"
    fresh.write_bytes(b"%PDF-1.4 " + b"y" * 100)
    assert verify_generated_file(fresh, min_mtime=fresh.stat().st_mtime - 0.1)["ok"] is True


def test_voice_studio_link_never_sends(monkeypatch, tmp_path):
    from app.services.max import send_me_link as sml
    from app.services.max import voice_live as vl

    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    pdf = tmp_path / "just_generated.pdf"
    pdf.write_bytes(b"%PDF-1.4 " + b"z" * 200)
    remember_drawing("cid:voice-1", {
        "success": True,
        "pdf_path": str(pdf),
        "pdf_filename": pdf.name,
        "pdf_mtime": pdf.stat().st_mtime,
        "share_url": "https://studio.empirebox.store/api/v1/files/found?t=test.sig",
    })
    monkeypatch.setattr(sml, "_deliver_email", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no email")))
    monkeypatch.setattr(sml, "_deliver_whatsapp", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no whatsapp")))

    assert wants_studio_share("give me the studio link")
    assert wants_studio_share("send me the link")
    assert not wants_studio_share("send it on WhatsApp")

    out = sml.send_me_this_link({
        "query": "the drawing",
        "via": "whatsapp",
        "user_text": "give me the studio link",
        "conversation_id": "voice-1",
    })
    assert out["success"]
    assert out["result"]["via"] == "studio"
    assert out["result"].get("sent") is False
    assert str(out["result"].get("share_url") or "").startswith("https://")

    voice = vl.run_voice_tool(
        "send_me_this_link",
        {"query": "the drawing", "via": "whatsapp"},
        conversation_id="voice-1",
        user_text="studio link please",
    )
    assert voice.get("success")
    via = (voice.get("result") or {}).get("via")
    assert via == "studio"


def test_fractions_only_on_revision_sheet(tmp_path, monkeypatch):
    import re
    import pdfplumber
    from app.services.drawing.job_drawing import generate_job_drawing

    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    result = generate_job_drawing(
        message='Marleys job revision, 12" channel backs',
        job_hint="Marley's",
    )
    assert result["success"]
    for value in result["dimensions"].values():
        assert "." not in value
        assert value.endswith('"')
    with pdfplumber.open(result["pdf_path"]) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
    assert re.findall(r"\d+\.\d+\"", text) == []
    assert "249 3/4" in text
    assert "26 3/4" in text
