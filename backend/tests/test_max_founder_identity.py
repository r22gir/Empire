"""Founder identity + 'who am I' rule: Rafael's main edition only (2026-10-04)."""
import pytest

from app.services.max import chat_style, system_prompt


def _prompt(monkeypatch, edition):
    if edition is None:
        monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    else:
        monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setitem(system_prompt._prompt_cache, "prompt", None)
    monkeypatch.setitem(system_prompt._prompt_cache, "expires", 0)
    return system_prompt.get_system_prompt()


def test_main_edition_names_founder(monkeypatch):
    p = _prompt(monkeypatch, None)
    assert "The user is Rafael Giraldo, founder of Empire" in p
    assert "You're Rafael Giraldo, founder of Empire," in p
    assert "Quién soy" in chat_style.render_chat_style_section()


@pytest.mark.parametrize("edition", ["amp", "maxine"])
def test_family_editions_never_get_founder_identity(monkeypatch, edition):
    p = _prompt(monkeypatch, edition)
    assert "Rafael Giraldo, founder of Empire" not in p
    monkeypatch.setitem(system_prompt._prompt_cache, "prompt", None)


def test_founder_authority_main_only(monkeypatch):
    p = _prompt(monkeypatch, None)
    assert "FOUNDER AUTHORITY" in p and "permission is final" in p
    assert "no outbound sends" in p  # his own standing limits stay
    for ed in ("amp", "maxine"):
        assert "FOUNDER AUTHORITY" not in _prompt(monkeypatch, ed)


def test_no_own_code_refusal_wording(monkeypatch):
    p = _prompt(monkeypatch, None)
    assert "never edit your own code" not in p
    assert "Never answer \"I don't edit my own code\"" in p
