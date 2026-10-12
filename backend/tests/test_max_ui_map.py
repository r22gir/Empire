"""Live UI map: 'where is X' from nav/home ids, never from stale .next greps."""
from __future__ import annotations

from pathlib import Path

from app.services.max import quick_replies, ui_map
from app.services.max.ui_map import (
    WORKROOM_ONLY_IDS,
    build_ui_map,
    find_in_app_reply,
    is_find_in_app_request,
    live_source_ids,
    lookup_feature,
    parse_left_nav,
    parse_max_home,
    refuse_shell_search,
    render_ui_map_section,
    set_current_user_message,
)


BANNED_STALE = (
    "lower-left",
    "lower left",
    "fixed gold button",
    "no verified",
    "not verified",
)

FAMILY_FORBIDDEN = (
    "empire workroom",
    "woodcraft",
    "schedule control",
    "pricing studio",
    "drawing studio",
    "leadforge",
    "final docs",
    "luxeforge",
    "forgecrm",
)

PROMPT_PY = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "system_prompt.py"
EXECUTOR_PY = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "tool_executor.py"


def test_left_nav_and_home_ids_are_in_the_map():
    sources = live_source_ids()
    assert "max-avatar" in sources["nav"]
    assert "improvements" in sources["nav"]
    assert "tokens" in sources["nav"]
    assert "schedule" in sources["nav"]
    assert "presentation" in sources["screens"]
    assert {"talk", "presentation-mode", "ai-face"} <= sources["home"]

    mapped = {f.id for f in build_ui_map()}
    for nid in sources["nav"]:
        assert nid in mapped, f"nav id {nid} missing from UI map"
    for hid in ("talk", "presentation-mode", "ai-face"):
        assert hid in mapped


def test_presentation_and_face_and_talk_are_on_max_home():
    pres = lookup_feature("Where is presentation mode")
    assert pres is not None
    text = f"{pres.name} {pres.where} {pres.href}".lower()
    assert "max home" in text
    assert "talk" in text
    assert "presentation" in pres.href
    for banned in BANNED_STALE:
        assert banned not in text

    face = lookup_feature("where is the AI face")
    assert face is not None
    face_txt = face.where.lower()
    assert "simli" in face_txt and "max home" in face_txt
    for banned in BANNED_STALE:
        assert banned not in face_txt

    simli = lookup_feature("dónde está Simli")
    assert simli is not None and simli.id == "ai-face"

    talk = lookup_feature("how do I open Talk")
    assert talk is not None
    assert "talk" in talk.where.lower()
    assert talk.href == "/"


def test_spanish_aliases_and_named_features():
    assert lookup_feature("dónde está el modo presentación").id == "presentation-mode"
    assert lookup_feature("como abro hablar").id == "talk"
    assert lookup_feature("donde esta mejoras").id == "improvements"
    assert lookup_feature("MiniMax usage").id == "minimax-usage"
    assert lookup_feature("uso de minimax").id == "minimax-usage"
    assert lookup_feature("Family help").id == "family-help"
    assert lookup_feature("ayuda familiar").id == "family-help"
    assert lookup_feature("Organizer").id == "organizer"
    assert lookup_feature("organizador").id == "organizer"
    sched = lookup_feature("where is the scheduler")
    assert sched is not None
    assert sched.id in {"scheduler", "schedule"}
    assert "max home" in sched.where.lower() or sched.id == "schedule"


def test_direct_reply_uses_ui_map_not_the_model():
    out = quick_replies.direct_reply("Where is presentation mode")
    assert out and out["skill"] == "find_in_app"
    assert "Presentation" in out["text"]
    assert "/?screen=presentation" in out["text"]
    for banned in BANNED_STALE:
        assert banned not in out["text"].lower()

    face = quick_replies.direct_reply("where is the AI face")
    assert face and face["skill"] == "find_in_app"
    assert "simli" in face["text"].lower()

    assert quick_replies.direct_reply("Hi")["skill"] == "greeting"
    assert quick_replies.is_docs_location_request("where are my docs")


def test_family_edition_hides_workroom_only_screens(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    family_ids = {f.id for f in ui_map.features_for_edition(True)}
    assert "presentation-mode" in family_ids
    assert "talk" in family_ids
    assert "ai-face" in family_ids
    assert "family-help" in family_ids
    assert "workroom" not in family_ids
    assert "schedule" not in family_ids
    assert "drawings" not in family_ids
    assert "pricing-studio" not in family_ids
    assert lookup_feature("where is presentation mode", family=True) is not None
    assert lookup_feature("Empire Workroom", family=True) is None
    assert lookup_feature("Schedule Control", family=True) is None

    section = render_ui_map_section(family=True).lower()
    for name in FAMILY_FORBIDDEN:
        assert name not in section, name
    assert "presentation mode" in section
    assert "simli" in section

    reply = find_in_app_reply("where is Schedule Control", family=True) or ""
    low = reply.lower()
    assert "schedule control" not in low
    assert "workroom" not in low


def test_prompt_and_executor_are_wired_to_the_map():
    prompt_src = PROMPT_PY.read_text(encoding="utf-8")
    assert "render_ui_map_section" in prompt_src
    assert "set_current_user_message" in prompt_src
    assert "is_find_in_app_request" in prompt_src

    exec_src = EXECUTOR_PY.read_text(encoding="utf-8")
    assert "refuse_shell_search" in exec_src
    assert "tools_ui_map" in exec_src
    assert '"where_is": "find_in_app"' in exec_src

    studio = render_ui_map_section(family=False)
    assert "LIVE UI MAP" in studio
    assert "find_in_app" in studio
    assert ".next.prev" in studio
    assert "Presentation mode" in studio
    assert "Simli" in studio


def test_find_it_detector():
    assert is_find_in_app_request("Where is presentation mode")
    assert is_find_in_app_request("how do I open the AI face")
    assert is_find_in_app_request("dónde está el modo presentación")
    assert not is_find_in_app_request("where is the last Marley's quote")
    assert not is_find_in_app_request("Hi")


def test_shell_guard_blocks_build_dirs_and_find_it_greps():
    set_current_user_message("Where is presentation mode")
    assert refuse_shell_search("rg -n Presentation empire-command-center/.next.prev")
    assert refuse_shell_search("grep -R talkinghead empire-command-center/.next/")
    assert refuse_shell_search("rg Simli node_modules/")
    assert refuse_shell_search("rg -n 'presentation mode' empire-command-center/app")
    assert refuse_shell_search("pwd") is None
    assert refuse_shell_search("echo hello") is None
    set_current_user_message("")
    assert refuse_shell_search("rg foo empire-command-center/.next.prev")


def test_find_in_app_lookup_function():
    hit = find_in_app_reply("where is presentation mode", family=False)
    assert hit and "Presentation" in hit and "/?screen=presentation" in hit
    assert "find_in_app" in EXECUTOR_PY.read_text(encoding="utf-8")
    assert "refuse_shell_search" in EXECUTOR_PY.read_text(encoding="utf-8")


def test_workroom_only_set_covers_operator_nav():
    nav = {i.id for i in parse_left_nav()}
    for wid in ("workroom", "craft", "schedule", "drawings", "pricing-studio", "lead"):
        assert wid in nav
        assert wid in WORKROOM_ONLY_IDS
    home = parse_max_home()
    assert any(h["id"] == "talk" for h in home)
    assert any("resentation" in h["label"] for h in home)
