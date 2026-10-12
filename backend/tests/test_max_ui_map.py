"""Live UI map: 'where is X' from nav/home ids, never from stale .next greps."""
from __future__ import annotations

from pathlib import Path

from app.services.max import ui_map
from app.services.max.ui_map import (
    WORKROOM_ONLY_IDS,
    build_ui_map,
    feature_markdown_link,
    find_in_app_reply,
    format_feature_reply,
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
    qr_src = (Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "quick_replies.py").read_text()
    assert "find_in_app_reply" in qr_src
    assert '"find_in_app"' in qr_src

    out = find_in_app_reply("Where is presentation mode", family=False, channel="web")
    assert out and "Presentation" in out
    assert "[Open Presentation](/?screen=presentation" in out
    for banned in BANNED_STALE:
        assert banned not in out.lower()

    face = find_in_app_reply("where is the AI face", family=False, channel="web")
    assert face and "simli" in face.lower()
    assert "[Open MAX Home](/)" in face


def test_where_is_replies_include_clickable_deep_link(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    monkeypatch.delenv("EMPIRE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    pres = lookup_feature("presentation mode")
    link = feature_markdown_link(pres, channel="web", family=False)
    assert link == "[Open Presentation](/?screen=presentation&mode=presentation)" or link.startswith("[Open Presentation](/?screen=presentation")
    web = format_feature_reply(pres, channel="web", family=False)
    assert "[Open Presentation](/?screen=presentation" in web
    spoken = format_feature_reply(pres, channel="voice", family=False)
    assert "[" not in spoken and "http" not in spoken.lower() and "/?" not in spoken
    tg = find_in_app_reply("where is presentation mode", family=False, channel="telegram")
    assert tg and "Presentation" in tg
    assert "http" not in tg.lower() and "](/" not in tg


def test_family_links_never_use_studio_host(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://studio.empirebox.store")
    text = find_in_app_reply("where is presentation mode", family=True, channel="web")
    assert text and "[Open Presentation](/?screen=presentation" in text
    assert "studio.empirebox.store" not in text
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://maxe.family.example")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    web = feature_markdown_link(lookup_feature("presentation mode", family=True), channel="web", family=True)
    assert web.startswith("[Open Presentation](/?screen=presentation")
    assert "studio.empirebox.store" not in web
    own = feature_markdown_link(lookup_feature("presentation mode", family=True), channel="whatsapp", family=True)
    assert own.startswith("[Open Presentation](https://maxe.family.example/?screen=presentation")
    assert "studio.empirebox.store" not in own


def test_header_search_is_on_the_map():
    bar = lookup_feature("where is the search bar")
    assert bar is not None and bar.id == "search"
    assert "quick switch" in bar.where.lower()
    assert "jobs/search" in bar.where.lower()
    assert lookup_feature("barra de búsqueda").id == "search"
    assert lookup_feature("command k").id == "search"
    assert lookup_feature("where is search").id == "search"
    assert lookup_feature("where is research").id == "research"
    family_where = find_in_app_reply("dónde está el buscador", family=True, channel="web") or ""
    for name in FAMILY_FORBIDDEN:
        assert name not in family_where.lower(), name
    assert "[Open Command Center](/?product=owner)" in family_where


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
