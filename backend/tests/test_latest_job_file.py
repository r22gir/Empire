"""Newest file for a job — never first-match / chat-memory / canned hijack.

No live data, no real sends, no real contacts.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date
from pathlib import Path

import pytest

from app.services.max import latest_job_file as ljf
from app.services.max import file_finder as ff
from app.services.max import send_me_link as sml
from app.services.max import quick_replies as qr
from app.services.max import ui_map


def _touch(p: Path, data: bytes = b"%PDF-1.4 drawing", age_hours: float = 0.0) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    if age_hours:
        t = time.time() - age_hours * 3600
        os.utime(p, (t, t))
    return p


@pytest.fixture()
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    drawings = h / "empire-data" / "drawings"
    old = _touch(drawings / "mockup_marley_s_u_bench_f904d55bb684.pdf", age_hours=10)
    new = _touch(drawings / "mockup_marley_s_u_bench_c84dc1c774c6.pdf", age_hours=0.1)
    aliases = tmp_path / "aliases.json"
    aliases.write_text(json.dumps({"clients": [
        {"name": "Marley", "aliases": ["Marleys", "Marley's"], "address": "Hyattsville"}
    ]}))
    monkeypatch.setenv("MAX_CLIENT_ALIASES_PATH", str(aliases))
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(h))
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(drawings))
    monkeypatch.setenv("MAX_CLOUD_FILES_DISABLED", "1")
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    ff.INDEX.clear()
    yield {"home": h, "drawings": drawings, "old": old, "new": new}
    ff.INDEX.clear()


def test_show_link_phrases():
    for t in (
        "Send me a link",
        "give me link",
        "done? show it",
        "show it",
        "show me the drawing",
        "studio link",
    ):
        assert ljf.is_show_link_request(t), t
        assert ljf.wants_studio_share(t), t
        assert not ljf.wants_external_send(t), t
    assert ljf.wants_external_send("email me the drawing")
    assert ljf.wants_external_send("send it on WhatsApp")
    assert not ljf.wants_studio_share("email me the drawing")


def test_pick_newest_ignores_list_order(home):
    old = {
        "name": home["old"].name, "path": str(home["old"]),
        "mtime": home["old"].stat().st_mtime,
    }
    new = {
        "name": home["new"].name, "path": str(home["new"]),
        "mtime": home["new"].stat().st_mtime,
    }
    picked = ljf.pick_newest_file([old, new])
    assert picked["name"] == home["new"].name
    picked2 = ljf.pick_newest_file([new, old])
    assert picked2["name"] == home["new"].name
    assert sml.pick_latest_match([old, new])["name"] == home["new"].name


def test_send_me_a_link_returns_newest_studio_url(home, monkeypatch):
    history = [
        {"role": "user", "content": "revise the marleys job drawing"},
        {"role": "assistant", "content": (
            "here is the old one https://studio.empirebox.store/api/v1/files/found?t=OLDTOKEN "
            f"{home['old'].name}"
        )},
    ]
    out = ljf.show_link_reply("Send me a link", history, channel="web", drawings_dir=home["drawings"])
    assert out and out["found"]
    assert out["name"] == home["new"].name
    assert home["old"].name not in (out.get("text") or "")
    assert out["url"].startswith("https://studio.empirebox.store/api/v1/files/found?t=")
    assert os.path.isfile(out["path"])
    assert out["mtime"] >= home["new"].stat().st_mtime - 1


def test_recorded_revision_beats_older_index_hit(home):
    rec = ljf.record_generated_drawing(
        job_key="marley",
        path=str(home["new"]),
        drawings_dir=home["drawings"],
    )
    assert rec["name"] == home["new"].name
    looked = ljf.find_newest_job_document("Send me a link", [
        {"role": "user", "content": "drawing of the marleys job"},
    ], drawings_dir=home["drawings"])
    assert looked["found"]
    assert looked["match"]["name"] == home["new"].name


def test_canned_shortcuts_do_not_hijack_show_link(home, monkeypatch):
    monkeypatch.setattr(qr, "docs_location_reply", lambda *a, **k: "FINAL DOCS LIST")
    monkeypatch.setattr(ui_map, "find_in_app_reply", lambda *a, **k: "WHERE IS SCREEN MAP")
    history = [{"role": "user", "content": "give me a drawing of the marleys job"}]
    for msg in ("done? show it", "give me link", "Send me a link"):
        hit = qr.direct_reply(msg, channel="web", history=history)
        assert hit, msg
        assert hit["skill"] == "latest_job_file", msg
        assert "FINAL DOCS" not in hit["text"]
        assert "SCREEN MAP" not in hit["text"]
        assert home["new"].name in hit["text"]
    assert not ui_map.is_find_in_app_request("where is the drawing")
    assert not ui_map.is_find_in_app_request("Send me a link")
    assert not qr.is_docs_location_request("give me link")
    assert not qr.is_docs_location_request("done? show it")


def test_find_files_ranks_newest_same_stem_first(home):
    res = ff.find_files("marley drawing")
    assert res["found"]
    assert res["matches"][0]["name"] == home["new"].name
    assert res["matches"][0]["mtime"] >= res["matches"][1]["mtime"]


def test_voice_studio_link_does_not_send(home, monkeypatch):
    from app.services.max import voice_live as vl

    def boom(*a, **k):
        raise AssertionError("must not send WhatsApp or email")

    monkeypatch.setattr(sml, "_deliver_email", boom)
    monkeypatch.setattr(sml, "_deliver_whatsapp", boom)
    out = vl.run_voice_tool(
        "send_me_this_link",
        {"query": "send me a link", "via": "studio"},
        user_text="send me a link",
    )
    assert out["success"], out
    assert (out.get("result") or {}).get("via") == "studio"
    assert "whatsapp" not in json.dumps(out).lower()
    share = vl.run_voice_tool(
        "share_file",
        {"via": "link"},
        user_text="studio link",
    )
    assert share["success"], share
    assert (share.get("result") or {}).get("via") == "studio"


def test_voice_can_you_link_is_studio_not_whatsapp():
    from app.services.max.voice_can_do import matching_action_tool, can_you_do
    assert matching_action_tool("can you send me a link") == "share_file"
    assert matching_action_tool("can you send me the 3D drawing on WhatsApp?") == "send_me_this_link"
    res = can_you_do({"question": "can you send me a link"})
    assert res["result"]["action_tool"] == "share_file"
