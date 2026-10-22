"""Revision drawings: separate seat/back color, full U+L set, fresh share link.

No live quotes, no real sends, no real contacts.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.services.max.job_drawing_intent import (
    extract_spec_changes,
    is_drawing_link_followup,
    should_route_to_drawing_desk,
)
from app.services.max.quick_replies import direct_reply, is_docs_location_request
from app.services.max.ui_map import find_in_app_reply, is_find_in_app_request


TODAY = date.today().isoformat()

MARLEY_DRAWING_HISTORY = [
    {"role": "user", "content": "give me a drawing of the marleys job"},
    {"role": "assistant", "content": "Working on the Marley's U+L revision now."},
    {
        "role": "user",
        "content": (
            "Marley's Hyattsville U+L banquette revision: every back = 12\" wide "
            "vertical channel back in Cognac; every seat cushion = Black"
        ),
    },
    {"role": "assistant", "content": "Generating the revised set."},
]


def _fabric_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "FABRIC_CODES.csv"
    csv_path.write_text(
        "code,color,material_type,width_inches,pattern_repeat_v,pattern_repeat_h,"
        "backing,specs,brand,supplier,supplier_sku,notes\n"
        "V003-Cognac,Cognac,vinyl,54,0,0,,,,Apex,Spradling Softside,SKU-C,\n"
        "V010-Black,Black,vinyl,54,0,0,,,,Apex,Spradling Softside,SKU-B,\n"
    )
    return csv_path


def _studio_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_FABRIC_CODES_CSV", str(_fabric_csv(tmp_path)))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://studio.empirebox.store")


def test_spec_changes_parse_in_and_equals():
    msg = (
        'every back = 12" wide vertical channel back in Cognac; '
        "every seat cushion = Black"
    )
    spec = extract_spec_changes(msg)
    assert spec.get("channel_width_in") == 12
    assert spec.get("back_fabric", "").lower() == "cognac"
    assert spec.get("seat_fabric", "").lower() == "black"


def test_seat_and_back_are_independent_inputs(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing
    from app.services.drawing.mockup_engine.materials import color_hex_for

    _studio_env(monkeypatch, tmp_path)
    result = generate_job_drawing(
        message=(
            "Marley's Hyattsville U+L banquette revision: every back = 12\" wide "
            "vertical channel back in Cognac; every seat cushion = Black"
        ),
        job_hint="Marleys",
        conversation_id="conv-rev-1",
    )
    assert result["success"] is True
    back = result["fabrics"]["back"]
    seat = result["fabrics"]["seat"]
    assert back["code"] == "V003-Cognac"
    assert seat["code"] == "V010-Black"
    assert back["label"] == "V003-Cognac"
    assert seat["label"] == "V010-Black"
    assert color_hex_for("black", role="seat") == "#1A1A1A"
    assert color_hex_for("cognac", role="back") == "#9A5B2E"
    assert color_hex_for("black", role="seat") != color_hex_for("cognac", role="back")

    import pdfplumber
    text = ""
    with pdfplumber.open(result["pdf_path"]) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    low = text.lower()
    assert "v003-cognac" in low or "cognac" in low
    assert "v010-black" in low or "plain black" in low
    assert "plain cognac" not in low
    assert "apex" not in low
    assert "spradling" not in low
    assert "softside" not in low
    assert "secretbrand" not in low


def test_revision_is_full_ul_set_new_file_today(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing

    _studio_env(monkeypatch, tmp_path)
    stale = tmp_path / "mockup_marley_s_u_bench_f904d55bb684.pdf"
    stale.write_bytes(b"%PDF-1.4 stale oct 8 drawing")

    result = generate_job_drawing(
        message=(
            "Marley's Hyattsville U+L banquette revision: every back = 12\" wide "
            "vertical channel back in Cognac; every seat cushion = Black"
        ),
        job_hint="Marleys",
        conversation_id="conv-rev-2",
    )
    assert result["success"] is True
    pdf = Path(result["pdf_path"])
    assert pdf.exists()
    assert pdf.name != stale.name
    assert TODAY in pdf.name
    assert result["revision"] == f"REV {TODAY}"
    assert result["date"] == TODAY
    assert result["page_count"] >= 4
    names = " ".join(result.get("piece_names") or []).lower()
    assert "u" in names and "l" in names

    import pdfplumber
    with pdfplumber.open(pdf) as doc:
        assert len(doc.pages) >= 4
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
    assert "U MAIN" in text or "U BENCH" in text.upper()
    assert "L LONG" in text or "L BENCH" in text.upper()
    assert TODAY in text
    assert f"REV {TODAY}" in text or "REV" in text
    assert "Apex" not in text and "Spradling" not in text
    import re
    assert re.findall(r"\d+\.\d+\"", text) == []

    first = result["pdf_path"]
    first_mtime = result["mtime"]
    again = generate_job_drawing(
        message="revise the drawing, channel back at 12 wide",
        job_hint="Marleys",
        conversation_id="conv-rev-2b",
    )
    assert again["pdf_path"] != first
    assert Path(again["pdf_path"]).name != Path(first).name
    assert again["mtime"] >= first_mtime - 0.01
    assert Path(again["pdf_path"]).stat().st_mtime == pytest.approx(again["mtime"], abs=2)


def test_max_returns_verified_absolute_share_url(tmp_path, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing, run_job_drawing_turn

    _studio_env(monkeypatch, tmp_path)
    result = generate_job_drawing(
        message="give me a drawing of the marleys job",
        job_hint="Marleys",
        conversation_id="conv-share-1",
    )
    url = result["share_url"]
    assert url.startswith("https://studio.empirebox.store/api/v1/files/found?t=")
    assert Path(result["pdf_path"]).exists()
    assert result["mtime"] == Path(result["pdf_path"]).stat().st_mtime
    assert "mockup_marley_s_u_bench_f904d55bb684" not in result["pdf_path"]

    turn = run_job_drawing_turn(
        "done? show it / give me link",
        history=MARLEY_DRAWING_HISTORY + [
            {"role": "assistant", "content": result["message"]},
        ],
        conversation_id="conv-share-1",
        channel="web",
    )
    assert turn["handled"] is True
    assert turn["success"] is True
    assert url in turn["response"]
    assert "https://studio.empirebox.store/" in turn["response"]
    assert turn["result"]["pdf_path"] == result["pdf_path"]


def test_shortcuts_do_not_hijack_drawing_link_followup():
    assert is_drawing_link_followup("done?")
    assert is_drawing_link_followup("show it")
    assert is_drawing_link_followup("give me link")
    assert is_drawing_link_followup("give me the link")
    assert is_drawing_link_followup("where is it")
    assert is_find_in_app_request("where is it")
    assert is_docs_location_request("where are my docs")

    hijack = direct_reply("where is it", history=MARLEY_DRAWING_HISTORY)
    assert hijack is None
    hijack2 = direct_reply("give me link", history=MARLEY_DRAWING_HISTORY)
    assert hijack2 is None
    hijack3 = direct_reply("done? show it", history=MARLEY_DRAWING_HISTORY)
    assert hijack3 is None
    assert should_route_to_drawing_desk("give me link", MARLEY_DRAWING_HISTORY)
    assert should_route_to_drawing_desk("where is it", MARLEY_DRAWING_HISTORY)

    docs = direct_reply("where are my docs")
    assert docs is None or docs.get("skill") == "docs_location"
    assert find_in_app_reply("where is presentation mode")


def test_voice_studio_link_never_sends(monkeypatch, tmp_path):
    from app.services.max import send_me_link as sml
    from app.services.max import voice_live as vl
    from app.services.max import file_finder as ff

    pdf = tmp_path / "rev_drawing.pdf"
    pdf.write_bytes(b"%PDF-1.4 just generated")
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(tmp_path))
    monkeypatch.setenv("MAX_CLOUD_FILES_DISABLED", "1")
    ff.INDEX.clear()

    def boom(*_a, **_k):
        raise AssertionError("must not send WhatsApp or email")

    monkeypatch.setattr(sml, "_deliver_email", boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", boom)

    assert sml.wants_studio_share("give me the studio link", None)
    assert sml.wants_studio_share("link", "link")
    assert sml.resolve_voice_share_via("studio", None) == "studio"
    assert sml.resolve_voice_share_via("give me the link", None) == "studio"
    assert sml.resolve_voice_share_via("studio please", "email") == "studio"
    assert sml.resolve_voice_share_via("send it on whatsapp", "whatsapp") == "whatsapp"

    out = sml.send_me_this_link({
        "query": "the drawing",
        "via": "studio",
        "path": str(pdf),
    })
    assert out["success"] is True
    assert out["result"]["via"] == "studio"
    assert out["result"].get("sent") is False
    assert "studio.empirebox.store" in (out["result"].get("viewer_url") or "")

    link_via = sml.send_me_this_link({
        "query": "give me the link",
        "via": "link",
        "path": str(pdf),
        "user_text": "link",
    })
    assert link_via["success"] is True
    assert link_via["result"]["via"] == "studio"

    voice = vl.run_voice_tool(
        "send_me_this_link",
        {"query": "the drawing", "via": "studio", "path": str(pdf)},
        user_text="give me the studio link",
    )
    assert voice.get("success") is True
    assert (voice.get("result") or {}).get("via") == "studio"
    assert sml.resolve_voice_share_via("link", None) == "studio"
    ff.INDEX.clear()


def test_client_label_never_uses_supplier():
    from app.services.drawing.job_drawing import resolve_internal_fabric
    from app.services.drawing.mockup_engine.materials import (
        apply_seat_back_finish,
        client_facing_fabric_label,
        strip_supplier_text,
    )
    from app.services.drawing.mockup_engine.spec import MaterialFinishSpec

    assert strip_supplier_text("Apex (Spradling Softside) vinyl") == ""
    row = client_facing_fabric_label("black", material_type="vinyl", registry_rows=[])
    assert row["label"].lower() == "black vinyl"
    assert "apex" not in row["label"].lower()
    mat = MaterialFinishSpec(name="Apex (Spradling Softside) vinyl", color_name="cognac")
    apply_seat_back_finish(
        mat,
        back={"code": "V003-Cognac", "color": "Cognac", "label": "V003-Cognac"},
        seat={"code": "V010-Black", "color": "Black", "label": "V010-Black"},
    )
    assert mat.color_hex != mat.seat_color_hex
    assert mat.seat_color_hex == "#1A1A1A"
    assert "spradling" not in mat.name.lower()
    assert mat.client_seat_label == "V010-Black"
    resolved = resolve_internal_fabric("cognac", [
        {"code": "V003-Cognac", "color": "Cognac", "material_type": "vinyl"},
    ])
    assert resolved["label"] == "V003-Cognac"
