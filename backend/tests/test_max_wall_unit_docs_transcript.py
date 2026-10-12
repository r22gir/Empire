"""Rafael studio Max transcript + review guards for PR #105.

show me wall unit led docs
  -> first web reply lists absolute public-base /files/found links
regenerate where / and / what do you mean / there are no links
  -> drawing router must NOT intercept
Spanish / pending dims / voice+Telegram stay correct
"""
from __future__ import annotations

import pytest

from app.services.max import file_finder as ff
from app.services.max.doc_links import (
    attach_studio_links_to_matches,
    ensure_absolute_doc_links,
    first_reply_link_instruction,
    is_document_lookup_request,
    is_family_edition,
    is_workroom_founder_edition,
    public_base,
    rewrite_relative_file_links,
    strip_spoken_urls,
    studio_found_url,
)
from app.services.max.drawing_intent import (
    build_drawing_handoff,
    is_drawing_intent,
    is_explicit_drawing_request,
    is_short_non_drawing_followup,
    looks_like_dimension_reply,
    pending_should_resume,
)


TRANSCRIPT_FOLLOWUPS = (
    "regenerate where",
    "and",
    "what do you mean",
    "there are no links",
    "relative links aren't rendering as buttons",
    "i need no drawing",
)

DOC_HISTORY = [
    {"role": "user", "content": "show me wall unit led docs"},
    {"role": "assistant", "content": "I found the LED spec. [Wall Unit LED](/jobs/wall-unit/led.pdf)"},
    {"role": "user", "content": "the links aren't buttons"},
    {"role": "assistant", "content": "Here are the files again."},
]

STUDIO = "https://studio.empirebox.store"
REAL_URL = f"{STUDIO}/api/v1/files/found?t=real.sig"
FOREIGN_URL = "https://evil.example/api/v1/files/found?t=abc.sig"


@pytest.fixture
def studio_env(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", STUDIO)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    yield STUDIO


def _found_tools(url: str = REAL_URL, name: str = "Wall-Unit-LED.pdf"):
    return [{"tool": "find_files", "success": True, "result": {
        "matches": [{"name": name, "viewer_url": url}],
    }}]


def test_show_me_docs_is_document_lookup_not_drawing():
    msg = "show me wall unit led docs"
    assert is_document_lookup_request(msg) is True
    assert is_drawing_intent(msg) is False
    handoff = build_drawing_handoff(msg)
    assert handoff.is_drawing_intent is False
    assert "I need drawing inputs" not in (handoff.response or "")


@pytest.mark.parametrize("msg", TRANSCRIPT_FOLLOWUPS)
def test_transcript_followups_do_not_route_to_drawing(msg):
    assert is_drawing_intent(msg) is False
    assert is_drawing_intent(msg, history=DOC_HISTORY) is False
    handoff = build_drawing_handoff(msg, history=DOC_HISTORY)
    assert handoff.is_drawing_intent is False
    assert "I need drawing inputs" not in (handoff.response or "")


def test_short_followups_are_classified():
    assert is_short_non_drawing_followup("and") is True
    assert is_short_non_drawing_followup("regenerate where") is True
    assert is_explicit_drawing_request("regenerate where") is False
    assert is_explicit_drawing_request("draw me a bench") is True


def test_weak_redraw_still_routes_when_drawing_companion_present():
    assert is_drawing_intent("regenerate as 4-view") is True
    assert is_drawing_intent("redo with the new dims") is True
    assert is_drawing_intent("make it 4-view") is True
    assert is_drawing_intent("redraw the Willard bench") is True
    assert is_drawing_intent("draw me a bench") is True


@pytest.mark.parametrize("msg", (
    "dibuja un banco",
    "dibújame un banquette",
    "rehaz el dibujo",
    "haz un dibujo del banco",
))
def test_spanish_drawing_requests_route(msg):
    assert is_explicit_drawing_request(msg) is True
    assert is_drawing_intent(msg) is True
    assert is_drawing_intent(msg, history=DOC_HISTORY) is True


def test_spanish_drawing_on_telegram_still_routes():
    assert is_drawing_intent("dibuja un banco") is True
    assert build_drawing_handoff("dibuja un banco").is_drawing_intent is True


def test_document_context_blocks_weak_regenerate_unless_pending():
    assert is_drawing_intent("regenerate where", history=DOC_HISTORY) is False
    assert is_drawing_intent("regenerate", history=DOC_HISTORY) is False
    # History guard does not suppress an explicit verb, even after docs.
    assert is_drawing_intent("draw me a bench", history=DOC_HISTORY) is True
    # Pending drawing + a dim reply is allowed despite doc history.
    assert is_drawing_intent("36 by 18", history=DOC_HISTORY, pending_drawing=True) is True


def test_pending_dimension_replies_resume_drawing():
    assert looks_like_dimension_reply("36 by 18") is True
    assert looks_like_dimension_reply("38 wide 64 long") is True
    assert is_drawing_intent("36 by 18") is False
    assert is_drawing_intent("36 by 18", pending_drawing=True) is True
    pending = {"missing": ["width", "height"]}
    assert pending_should_resume("36 by 18", pending) is True
    assert pending_should_resume("38 wide 64 long", pending) is True
    assert pending_should_resume("regenerate where", pending, history=DOC_HISTORY) is False
    handoff = build_drawing_handoff("36 by 18", pending_drawing=True)
    assert handoff.is_drawing_intent is True


def test_explicit_no_drawing_phrases():
    assert is_drawing_intent("i need no drawing") is False
    assert is_drawing_intent("no necesito dibujo") is False
    assert is_drawing_intent("no quiero un dibujo") is False
    assert is_drawing_intent("show me wall unit led docs") is False


def test_find_files_first_reply_has_absolute_studio_links(tmp_path, monkeypatch, studio_env):
    home = tmp_path / "home"
    led = home / "jobs" / "philipp-naomi" / "Wall-Unit-LED-Spec.pdf"
    led.parent.mkdir(parents=True)
    led.write_bytes(b"%PDF-1.4 wall unit led")
    (home / "jobs" / "philipp-naomi" / "Wall-Unit-LED-Layout.pdf").write_bytes(b"%PDF-1.4 layout")
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(home))
    monkeypatch.setenv("MAX_CLOUD_FILES_DISABLED", "1")
    ff.INDEX.clear()
    found = ff.find_files("wall unit led")
    assert found.get("found"), found
    matches = attach_studio_links_to_matches(found.get("matches") or [])
    assert matches
    for m in matches:
        url = m["viewer_url"]
        assert url.startswith(f"{studio_env}/api/v1/files/found?t=")
        assert m["markdown_link"] == f"[{m['name']}]({url})"
    r = {"tool": "find_files", "success": True, "result": {**found, "matches": matches}}
    filled = ensure_absolute_doc_links("I found the wall unit LED docs.", [r], channel="web")
    assert f"{studio_env}/api/v1/files/found?t=" in filled
    assert "Wall-Unit-LED" in filled
    relative = "See [LED spec](/api/v1/files/found?t=abc.sig)"
    assert rewrite_relative_file_links(relative) == (
        f"See [LED spec]({studio_env}/api/v1/files/found?t=abc.sig)"
    )
    ff.INDEX.clear()


def test_clean_reply_keeps_file_sources_block(studio_env):
    from app.services.max.answer_policy import clean_reply
    body = (
        "Here are the wall unit LED docs.\n\n"
        "Sources\n"
        f"1. [Wall-Unit-LED-Spec.pdf]({STUDIO}/api/v1/files/found?t=aaa.sig)\n"
        f"2. [Wall-Unit-LED-Layout.pdf]({STUDIO}/api/v1/files/found?t=bbb.sig)"
    )
    out = clean_reply(body, "show me wall unit led docs")
    assert f"{studio_env}/api/v1/files/found" in out
    assert "Wall-Unit-LED-Spec.pdf" in out


def test_foreign_host_found_link_does_not_count_as_present(studio_env):
    text = f"See [x]({FOREIGN_URL})"
    out = ensure_absolute_doc_links(text, _found_tools(), channel="web")
    assert REAL_URL in out
    assert "Wall-Unit-LED.pdf" in out
    assert FOREIGN_URL in out


def test_clean_reply_drops_foreign_host_sources(studio_env):
    from app.services.max.answer_policy import clean_reply
    body = (
        "Here are the docs.\n\n"
        "Sources\n"
        f"1. [x]({FOREIGN_URL})"
    )
    out = clean_reply(body, "show me wall unit led docs")
    assert FOREIGN_URL not in out
    assert not out.lstrip().startswith("Sources")


def test_family_edition_emits_no_studio_link(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.delenv("EMPIRE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    assert public_base() == ""
    relative = "See [x](/api/v1/files/found?t=abc.sig)"
    assert rewrite_relative_file_links(relative) == relative
    out = ensure_absolute_doc_links("I found the LED spec.", _found_tools(), channel="web")
    assert "studio.empirebox.store" not in out
    assert out == "I found the LED spec."
    p = tmp_path / "A.pdf"
    p.write_bytes(b"%PDF-1.4 x")
    monkeypatch.setattr(ff, "resolve_file", lambda ref: str(p))
    rows = attach_studio_links_to_matches([{"file_id": "x", "name": "A.pdf"}])
    assert not rows[0].get("viewer_url")
    assert "studio.empirebox.store" not in studio_found_url(str(p))
    assert "studio.empirebox.store" not in first_reply_link_instruction()
    from app.services.max.answer_policy import style_directive
    from app.services.max.chat_style import render_chat_style_section
    assert "studio.empirebox.store" not in style_directive()
    assert "studio.empirebox.store" not in render_chat_style_section()


def test_non_document_chat_unchanged(studio_env):
    text = "The Marley's quote is EST-2026-295, total $3,546.69."
    assert ensure_absolute_doc_links(text, [], channel="web") == text
    assert ensure_absolute_doc_links(
        text, [{"tool": "search_quotes", "success": True, "result": {}}], channel="web",
    ) == text


@pytest.mark.parametrize("channel", ("voice", "telegram", "phone", "sms"))
def test_voice_and_telegram_do_not_append_sources(channel, studio_env):
    text = "I found the wall unit LED spec."
    out = ensure_absolute_doc_links(text, _found_tools(), channel=channel)
    assert out == text
    assert "Sources" not in out
    assert "files/found" not in out


@pytest.mark.parametrize("channel", ("voice", "telegram", "phone", "sms"))
def test_spoken_channels_strip_urls_in_code(channel, studio_env):
    text = (
        "I found the LED spec. "
        f"[Wall-Unit-LED.pdf]({REAL_URL}) "
        f"also {REAL_URL} and /api/v1/files/found?t=rel.sig\n\n"
        "Sources\n"
        f"1. [Layout.pdf]({REAL_URL})"
    )
    out = ensure_absolute_doc_links(text, _found_tools(), channel=channel)
    assert "http" not in out.lower()
    assert "files/found" not in out
    assert "studio.empirebox.store" not in out
    assert "Wall-Unit-LED.pdf" in out
    assert "Layout.pdf" in out
    stripped = strip_spoken_urls(text)
    assert stripped == out
    assert "http" not in stripped.lower()


def test_unset_edition_never_falls_back_to_studio(monkeypatch):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("EMPIRE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    assert is_workroom_founder_edition() is False
    assert is_family_edition() is True
    assert public_base() == ""
    relative = "See [x](/api/v1/files/found?t=abc.sig)"
    assert rewrite_relative_file_links(relative) == relative
    out = ensure_absolute_doc_links("I found the LED spec.", _found_tools(), channel="web")
    assert out == "I found the LED spec."
    assert "studio.empirebox.store" not in out
    assert "studio.empirebox.store" not in first_reply_link_instruction()
    assert "studio.empirebox.store" not in studio_found_url("/tmp/A.pdf")


def test_unset_edition_rejects_studio_env_override(monkeypatch):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", STUDIO)
    monkeypatch.setenv("PUBLIC_BASE_URL", STUDIO)
    assert public_base() == ""
    assert rewrite_relative_file_links("See [x](/api/v1/files/found?t=abc.sig)") == (
        "See [x](/api/v1/files/found?t=abc.sig)"
    )


@pytest.mark.parametrize("edition", ("workroom", "founder"))
def test_explicit_workroom_founder_uses_studio_default(monkeypatch, edition):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.delenv("EMPIRE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    assert is_workroom_founder_edition() is True
    assert is_family_edition() is False
    assert public_base() == STUDIO


def test_unset_edition_allows_non_studio_public_base(monkeypatch):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://maxine.example")
    monkeypatch.delenv("EMPIRE_PUBLIC_BASE_URL", raising=False)
    assert public_base() == "https://maxine.example"


def test_attach_links_never_emits_relative_viewer(tmp_path, monkeypatch, studio_env):
    p = tmp_path / "Wall-Unit-LED.pdf"
    p.write_bytes(b"%PDF-1.4 x")
    monkeypatch.setattr(ff, "resolve_file", lambda ref: str(p))
    monkeypatch.setattr(ff, "share_token", lambda path, ttl_seconds=86400: "tok.sig")
    rows = attach_studio_links_to_matches([{"file_id": "x", "name": "Wall-Unit-LED.pdf"}])
    assert rows[0]["viewer_url"] == f"{studio_env}/api/v1/files/found?t=tok.sig"
    assert studio_found_url(str(p)).startswith(f"{studio_env}/")
