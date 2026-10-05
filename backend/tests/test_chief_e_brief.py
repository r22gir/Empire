"""Chief e brief loader — main edition only, capped, mtime-cached.

Runs entirely on pytest tmp_path; never touches live data (the conftest
live-data firewall would fail the test if it did).
"""
from __future__ import annotations

import asyncio
import os
import sys
import types
from pathlib import Path

import pytest

from app.services.max import chief_e_brief as ceb


SAMPLE = """# Chief e brief — 2026-10-04

## Who Rafael is
- Founder of Empire Workroom.

## Active jobs and clients
{jobs}

## Hard rules
- Never send anything outbound without approval.

## Pricing and rates
- Re-line: sample rate.

## Doc and format rules
- Estimate numbering EST-YYYY-NNN.

## Recent changes
- 2026-10-04: brief created.
"""


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    data = tmp_path / "empire-data"
    (data / "brain").mkdir(parents=True)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data))
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("CHIEF_E_BRIEF_MAX_TOKENS", raising=False)
    ceb.clear_cache()
    yield data / "brain" / ceb.BRIEF_FILENAME
    ceb.clear_cache()


def _write(p: Path, text: str, mtime_ns: int | None = None) -> None:
    p.write_text(text, encoding="utf-8")
    if mtime_ns is not None:
        os.utime(p, ns=(mtime_ns, mtime_ns))


def test_brief_path_follows_data_dir(_isolated):
    assert ceb.brief_path() == _isolated
    assert "empire-data/brain/chief_e_brief.md" in str(_isolated)


def test_missing_file_is_noop(_isolated):
    assert not _isolated.exists()
    assert ceb.load_chief_e_brief() == ""
    assert ceb.render_chief_e_section() == ""


def test_loads_for_main_edition_with_pointer(_isolated):
    _write(_isolated, SAMPLE.format(jobs="- Job A"))
    out = ceb.render_chief_e_section()
    assert out.startswith("## Chief e Brief")
    assert "Chief e" in out and "cross-business decisions" in out
    assert "Re-line: sample rate." in out
    assert "Job A" in out


@pytest.mark.parametrize("edition", ["amp", "maxine", "max_e"])
def test_family_edition_env_never_loads(_isolated, monkeypatch, edition):
    _write(_isolated, SAMPLE.format(jobs="- Job A"))
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    assert ceb.load_chief_e_brief() == ""
    assert ceb.render_chief_e_section() == ""


def test_main_edition_env_value_loads(_isolated, monkeypatch):
    _write(_isolated, SAMPLE.format(jobs="- Job A"))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    assert "Job A" in ceb.load_chief_e_brief()


@pytest.mark.parametrize("marker", ["data/amp", "data/maxine", "empire-amp", "empire-maxine"])
def test_family_data_dir_never_loads(tmp_path, monkeypatch, marker):
    data = tmp_path / marker
    (data / "brain").mkdir(parents=True)
    p = data / "brain" / ceb.BRIEF_FILENAME
    _write(p, SAMPLE.format(jobs="- Job A"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data))
    assert ceb.load_chief_e_brief() == ""
    assert ceb.load_chief_e_brief(p) == ""


def test_cache_by_mtime(_isolated):
    _write(_isolated, SAMPLE.format(jobs="- Job A"), mtime_ns=1_700_000_000_000_000_000)
    assert "Job A" in ceb.load_chief_e_brief()
    # Same mtime and size: served from cache even though content changed.
    _write(_isolated, SAMPLE.format(jobs="- Job B"), mtime_ns=1_700_000_000_000_000_000)
    assert "Job A" in ceb.load_chief_e_brief()
    # New mtime: re-read.
    _write(_isolated, SAMPLE.format(jobs="- Job B"), mtime_ns=1_700_000_100_000_000_000)
    assert "Job B" in ceb.load_chief_e_brief()


def test_trim_keeps_rules_and_pricing_first(_isolated, monkeypatch):
    monkeypatch.setenv("CHIEF_E_BRIEF_MAX_TOKENS", "1000")  # ~4000 chars
    jobs = "\n".join(f"- Job {i}: " + "x" * 80 for i in range(200))  # ~17k chars
    _write(_isolated, SAMPLE.format(jobs=jobs))
    out = ceb.load_chief_e_brief()
    assert len(out) <= 4000
    assert "Never send anything outbound" in out
    assert "Re-line: sample rate." in out
    assert "EST-YYYY-NNN" in out
    assert "brief trimmed" in out or "section trimmed" in out
    # Original section order preserved for what survived.
    assert out.index("## Who Rafael is") < out.index("## Hard rules") < out.index("## Pricing")


def test_secret_like_tokens_scrubbed(_isolated):
    _write(_isolated, SAMPLE.format(jobs="- api_key: abc123def456\n- sk-" + "A" * 30))
    out = ceb.load_chief_e_brief()
    assert "abc123def456" not in out
    assert "sk-AAAA" not in out
    assert "[redacted]" in out


def test_assembled_prompt_includes_brief(_isolated, monkeypatch):
    """get_system_prompt_with_brain carries the brief (stubs keep it offline)."""
    _write(_isolated, SAMPLE.format(jobs="- Job Z"))
    from app.services.max import system_prompt as sp

    monkeypatch.setattr(sp, "get_system_prompt", lambda: "BASE PROMPT")
    monkeypatch.setattr(sp, "get_max_brain_context", lambda: "LIVE")

    class _StubBuilder:
        async def build_context(self, **_kw):
            return "MEM"

    stub_mod = types.ModuleType("app.services.max.brain.context_builder")
    stub_mod.ContextBuilder = _StubBuilder
    monkeypatch.setitem(sys.modules, "app.services.max.brain.context_builder", stub_mod)

    prompt = asyncio.run(sp.get_system_prompt_with_brain("hi"))
    assert prompt.startswith("BASE PROMPT")
    assert "## Chief e Brief" in prompt and "Job Z" in prompt
    assert prompt.index("## Live Brain Context") < prompt.index("## Chief e Brief") < prompt.index("## Brain Memory Context")

    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    ceb.clear_cache()
    family = asyncio.run(sp.get_system_prompt_with_brain("hi"))
    assert "Chief e Brief" not in family and "Job Z" not in family
