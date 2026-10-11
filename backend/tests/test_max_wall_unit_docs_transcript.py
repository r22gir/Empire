"""Rafael studio Max transcript: wall-unit LED docs + drawing-router hijack.

show me wall unit led docs
  -> first reply must list absolute https://studio.empirebox.store/api/v1/files/found?t=... links
regenerate where / and / what do you mean / there are no links
  -> drawing router must NOT intercept
i need no drawing
  -> stays in chat (no drawing handoff)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.max import file_finder as ff
from app.services.max.doc_links import (
    attach_studio_links_to_matches,
    ensure_absolute_doc_links,
    is_document_lookup_request,
    rewrite_relative_file_links,
    studio_found_url,
)
from app.services.max.drawing_intent import (
    build_drawing_handoff,
    is_drawing_intent,
    is_explicit_drawing_request,
    is_short_non_drawing_followup,
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
    assert "drawing handoff" not in (handoff.response or "").lower()


def test_short_followups_are_classified():
    assert is_short_non_drawing_followup("and") is True
    assert is_short_non_drawing_followup("regenerate where") is True
    assert is_short_non_drawing_followup("what do you mean") is True
    assert is_short_non_drawing_followup("there are no links") is True
    assert is_explicit_drawing_request("regenerate where") is False
    assert is_explicit_drawing_request("draw me a bench") is True


def test_weak_redraw_still_routes_when_drawing_companion_present():
    assert is_drawing_intent("regenerate as 4-view") is True
    assert is_drawing_intent("redo with the new dims") is True
    assert is_drawing_intent("new version of the bench") is True
    assert is_drawing_intent("same version of the panel") is True
    assert is_drawing_intent("redraw the Willard bench") is True
    assert is_drawing_intent("draw me a bench") is True


def test_document_context_blocks_weak_regenerate(monkeypatch):
    assert is_drawing_intent("regenerate where", history=DOC_HISTORY) is False
    # Even a weak 'regenerate' alone stays in chat after a docs thread.
    assert is_drawing_intent("regenerate", history=DOC_HISTORY) is False


def test_explicit_no_drawing_router_phrase():
    router = Path(__file__).resolve().parents[1] / "app/routers/max/router.py"
    src = router.read_text()
    assert "i need no drawing" in src
    assert "need no drawing" in src


def test_find_files_first_reply_has_absolute_studio_links(tmp_path, monkeypatch):
    home = tmp_path / "home"
    led = home / "jobs" / "philipp-naomi" / "Wall-Unit-LED-Spec.pdf"
    led.parent.mkdir(parents=True)
    led.write_bytes(b"%PDF-1.4 wall unit led")
    other = home / "jobs" / "philipp-naomi" / "Wall-Unit-LED-Layout.pdf"
    other.write_bytes(b"%PDF-1.4 layout")
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(home))
    monkeypatch.setenv("MAX_CLOUD_FILES_DISABLED", "1")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    ff.INDEX.clear()
    found = ff.find_files("wall unit led")
    assert found.get("found"), found
    matches = attach_studio_links_to_matches(found.get("matches") or [])
    assert matches
    for m in matches:
        url = m["viewer_url"]
        assert url.startswith("https://studio.empirebox.store/api/v1/files/found?t=")
        assert m["markdown_link"] == f"[{m['name']}]({url})"
        assert not url.startswith("/api/")
    r = {"tool": "find_files", "success": True, "result": {**found, "matches": matches}}
    # First-reply assembler: model forgot the links / used a relative path.
    forgotten = "I found the wall unit LED docs."
    filled = ensure_absolute_doc_links(forgotten, [r])
    assert "https://studio.empirebox.store/api/v1/files/found?t=" in filled
    assert "Wall-Unit-LED" in filled
    assert "](/api/" not in filled
    relative = "See [LED spec](/api/v1/files/found?t=abc.sig)"
    assert rewrite_relative_file_links(relative) == (
        "See [LED spec](https://studio.empirebox.store/api/v1/files/found?t=abc.sig)"
    )
    ff.INDEX.clear()


def test_clean_reply_keeps_file_sources_block():
    from app.services.max.answer_policy import clean_reply
    body = (
        "Here are the wall unit LED docs.\n\n"
        "Sources\n"
        "1. [Wall-Unit-LED-Spec.pdf](https://studio.empirebox.store/api/v1/files/found?t=aaa.sig)\n"
        "2. [Wall-Unit-LED-Layout.pdf](https://studio.empirebox.store/api/v1/files/found?t=bbb.sig)"
    )
    out = clean_reply(body, "show me wall unit led docs")
    assert "studio.empirebox.store/api/v1/files/found" in out
    assert "Wall-Unit-LED-Spec.pdf" in out
    assert "Wall-Unit-LED-Layout.pdf" in out


def test_chat_markdown_safe_url_contract():
    """Mirrors empire-command-center/app/components/chat/safeUrl.ts."""
    import re

    def safe_url(u: str) -> str:
        if re.match(r"^https?://", u, re.I):
            return u
        if re.match(r"^/api/v1/files/found\?", u, re.I):
            return u
        if re.match(r"^/docs/view\?", u, re.I):
            return u
        return ""

    abs_u = "https://studio.empirebox.store/api/v1/files/found?t=abc.sig"
    rel_found = "/api/v1/files/found?t=abc.sig"
    relative_path = "/jobs/wall-unit/led.pdf"
    assert safe_url(abs_u) == abs_u
    assert safe_url(rel_found) == rel_found
    assert safe_url(relative_path) == ""
    md = f"[Wall Unit LED]({abs_u})"
    assert re.search(r"\]\(https?://", md)


def test_attach_links_never_emits_relative_viewer(tmp_path, monkeypatch):
    p = tmp_path / "Wall-Unit-LED.pdf"
    p.write_bytes(b"%PDF-1.4 x")
    monkeypatch.setattr(ff, "resolve_file", lambda ref: str(p))
    monkeypatch.setattr(ff, "share_token", lambda path, ttl_seconds=86400: "tok.sig")
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    rows = attach_studio_links_to_matches([{"file_id": "x", "name": "Wall-Unit-LED.pdf"}])
    assert rows[0]["viewer_url"] == "https://studio.empirebox.store/api/v1/files/found?t=tok.sig"
    assert rows[0]["markdown_link"] == (
        "[Wall-Unit-LED.pdf](https://studio.empirebox.store/api/v1/files/found?t=tok.sig)"
    )
    assert studio_found_url(str(p)).startswith("https://studio.empirebox.store/")
