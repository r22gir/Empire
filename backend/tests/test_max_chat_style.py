"""Chat reply format + Chief e awareness (services/max/chat_style.py)."""
from app.services.max import chat_style


def test_main_edition_gets_style_and_chief_e(monkeypatch):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_DATA_DIR", "/tmp/empire-test-data")
    monkeypatch.setattr(chat_style.os, "getcwd", lambda: "/tmp")
    out = chat_style.render_chat_style_section()
    assert "Lead with the direct answer" in out
    assert "Own records first" in out
    assert "[Ask Chief e](chief-e:ask)" in out
    assert "doesn't exist" in out  # the rule forbidding that claim


def test_family_editions_never_see_chief_e(monkeypatch):
    for edition in ("amp", "maxine"):
        monkeypatch.setenv("EMPIRE_EDITION", edition)
        out = chat_style.render_chat_style_section()
        assert "Lead with the direct answer" in out
        assert "Chief e" not in out
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_DATA_DIR", "/data/amp")
    assert "Chief e" not in chat_style.render_chat_style_section()
