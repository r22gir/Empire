"""Live screen-path map: 'where is X' from nav/quick-switch, never from stale .next greps."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load ui_map.py without importing app.services.max (that package pulls httpx / telegram).
_UI_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "ui_map.py"
_spec = importlib.util.spec_from_file_location("max_ui_map_under_test", _UI_PATH)
ui_map = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["max_ui_map_under_test"] = ui_map
_spec.loader.exec_module(ui_map)

build_ui_map = ui_map.build_ui_map
feature_markdown_link = ui_map.feature_markdown_link
find_in_app_reply = ui_map.find_in_app_reply
format_feature_reply = ui_map.format_feature_reply
is_find_in_app_request = ui_map.is_find_in_app_request
live_source_ids = ui_map.live_source_ids
lookup_feature = ui_map.lookup_feature
parse_left_nav = ui_map.parse_left_nav
parse_quick_switch = ui_map.parse_quick_switch
refuse_shell_search = ui_map.refuse_shell_search
render_ui_map_section = ui_map.render_ui_map_section
set_current_user_message = ui_map.set_current_user_message


BANNED_STALE = (
    "lower-left",
    "lower left",
    "fixed gold button",
    "no verified",
    "not verified",
)

PROMPT_PY = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "system_prompt.py"
EXECUTOR_PY = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "tool_executor.py"
ROUTER_PY = Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py"
PAGE_TSX = Path(__file__).resolve().parents[2] / "empire-command-center" / "app" / "page.tsx"


def test_left_nav_and_quick_switch_are_in_the_map():
    sources = live_source_ids()
    assert "workroom" in sources["nav"]
    assert "vision" in sources["nav"]
    assert "owner" in sources["nav"]
    assert "presentation" in sources["quick"]
    assert "quote" in sources["quick"]
    assert "presentation" in sources["screens"]

    mapped = {f.id for f in build_ui_map()}
    for nid in sources["nav"]:
        assert nid in mapped, f"nav id {nid} missing from UI map"
    assert "presentation-mode" in mapped
    assert "organizer" in mapped
    assert "quotes" in mapped


def test_where_is_presentation_mode_has_tappable_link():
    assert is_find_in_app_request("Where is presentation mode")
    feat = lookup_feature("Where is presentation mode")
    assert feat is not None
    assert feat.id == "presentation-mode"
    text = find_in_app_reply("Where is presentation mode", family=False, channel="web")
    assert text and "Presentation" in text
    assert "[Open Presentation](/?screen=presentation" in text
    assert "mode=presentation" in text or "/?screen=presentation" in text
    for banned in BANNED_STALE:
        assert banned not in text.lower()
    # Truthful for this checkout: Quick Switch MAX Avatar, not a stale gold button.
    assert "quick switch" in text.lower() or "max avatar" in text.lower()


def test_where_is_organizer_has_tappable_link():
    assert is_find_in_app_request("where is the Organizer")
    feat = lookup_feature("where is the Organizer")
    assert feat is not None
    assert feat.id == "organizer"
    text = find_in_app_reply("where is Organizer", family=False, channel="web")
    assert text
    assert "[Open Organizer](/?product=vision" in text
    assert "photo" in text.lower() or "vision" in text.lower()
    assert lookup_feature("organizador").id == "organizer"
    assert lookup_feature("photo organizer").id == "organizer"


def test_where_are_quotes_has_tappable_link():
    assert is_find_in_app_request("where are quotes")
    assert is_find_in_app_request("where is the quote builder")
    feat = lookup_feature("where are quotes")
    assert feat is not None
    assert feat.id == "quotes"
    text = find_in_app_reply("where are quotes", family=False, channel="web")
    assert text
    assert "[Open Quotes](/?product=workroom&section=quotes)" in text
    assert "workroom" in text.lower()
    review = find_in_app_reply("where is quote review", family=False, channel="web")
    assert review and "[Open Quote Review](/?screen=quote)" in review
    # Named quote records are NOT screen questions.
    assert not is_find_in_app_request("where is the last Marley's quote")
    assert not is_find_in_app_request("where is EST-2026-027")


def test_spanish_presentation_alias():
    feat = lookup_feature("dónde está el modo presentación")
    assert feat is not None
    assert feat.id == "presentation-mode"


def test_where_is_replies_always_include_clickable_deep_link(monkeypatch):
    monkeypatch.delenv("EMPIRE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    for question, label_part, href_part in (
        ("where is presentation mode", "Open Presentation", "/?screen=presentation"),
        ("where is Organizer", "Open Organizer", "/?product=vision"),
        ("where are quotes", "Open Quotes", "/?product=workroom&section=quotes"),
    ):
        web = find_in_app_reply(question, family=False, channel="web")
        assert web and f"[{label_part}]({href_part}" in web
        spoken = find_in_app_reply(question, family=False, channel="voice")
        assert spoken and "[" not in spoken and "http" not in spoken.lower()
        assert "/?" not in spoken


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


def test_prompt_executor_and_router_are_wired_to_the_map():
    prompt_src = PROMPT_PY.read_text(encoding="utf-8")
    assert "render_ui_map_section" in prompt_src
    assert "set_current_user_message" in prompt_src

    exec_src = EXECUTOR_PY.read_text(encoding="utf-8")
    assert "refuse_shell_search" in exec_src
    assert "tools_ui_map" in exec_src
    assert '"where_is": "find_in_app"' in exec_src

    router_src = ROUTER_PY.read_text(encoding="utf-8")
    assert "find_in_app_reply" in router_src
    assert "ui-map" in router_src or "find_in_app" in router_src

    section = render_ui_map_section(family=False)
    assert "LIVE SCREEN-PATH MAP" in section or "LIVE UI MAP" in section
    assert ".next.prev" in section
    assert "Presentation mode" in section
    assert "Organizer" in section
    assert "Quotes" in section


def test_page_deep_links_cover_presentation_organizer_quotes():
    src = PAGE_TSX.read_text(encoding="utf-8")
    assert "presentation" in src
    assert "product" in src and "section" in src
    # Deep-link handler must honor the tappable hrefs the map emits.
    assert "params.get('product')" in src or 'params.get("product")' in src
    assert "params.get('section')" in src or 'params.get("section")' in src


def test_family_edition_hides_workroom_quotes(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    assert lookup_feature("where are quotes", family=True) is None
    assert lookup_feature("where is presentation mode", family=True) is not None
    assert lookup_feature("where is Organizer", family=True) is not None


def test_nav_parse_matches_left_nav_file():
    nav = {i.id for i in parse_left_nav()}
    assert {"owner", "workroom", "vision", "tokens"} <= nav
    quick = {q["screen"] for q in parse_quick_switch()}
    assert {"presentation", "quote"} <= quick


def test_markdown_link_helpers():
    pres = lookup_feature("presentation mode")
    link = feature_markdown_link(pres, channel="web", family=False)
    assert link.startswith("[Open Presentation](/?screen=presentation")
    formatted = format_feature_reply(pres, channel="web", family=False)
    assert "[Open Presentation](/?screen=presentation" in formatted


def test_chat_helper_answers_common_where_is_questions():
    """Same contract the router helper uses: map reply + tappable link, no model."""
    cases = (
        ("Where is presentation mode", "Open Presentation", "/?screen=presentation"),
        ("where is Organizer", "Open Organizer", "/?product=vision"),
        ("where are quotes", "Open Quotes", "/?product=workroom&section=quotes"),
    )
    for message, label, href in cases:
        assert is_find_in_app_request(message), message
        text = find_in_app_reply(message, family=False, channel="web")
        assert text, message
        assert f"[{label}]({href}" in text
        for banned in BANNED_STALE:
            assert banned not in text.lower()
    assert not is_find_in_app_request("where is the last Marley's quote")
    assert find_in_app_reply("where is the last Marley's quote", channel="web") is None
