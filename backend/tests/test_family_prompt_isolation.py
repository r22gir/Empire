"""Family editions must not pull Workroom live context into prompts."""
from __future__ import annotations

from pathlib import Path

from app.edition import AMP_COACH_NAME, MAXINE_OWNER_NAME


WORKROOM_PROMPT_LEAKS = (
    "Empire Workroom",
    "Hyattsville",
    "5124 Frolich",
    "workroom@empirebox.store",
    "woodcraft@empirebox.store",
    "Nelma's Workroom",
    "~/empire-repo",
    ".claude-context",
    "RG's Drapery",
    "empire-box-memory",
    "Dahlia = Nehal Elrefai",
    "Nehal Elrefai",
    "The Willard Hotel",
    "McLean Whittington",
)


def _family_env(monkeypatch, tmp_path, edition: str):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.delenv("EMPIRE_BOX_MEMORY_DIR", raising=False)
    monkeypatch.delenv("EMPIRE_BRAIN_DIR", raising=False)
    name = "Max-e" if edition == "amp" else "Maxine"
    monkeypatch.setenv("ASSISTANT_NAME", name)
    from app.edition import apply_amp_process_paths
    apply_amp_process_paths()
    from app.services.max.system_prompt import _prompt_cache
    _prompt_cache.update({
        "prompt": None,
        "expires": 0,
        "edition": None,
        "_brain_ctx": None,
        "_brain_expires": 0,
        "_brain_edition": None,
    })


def test_prompt_context_paths_stay_in_data_root_for_amp_and_maxine(monkeypatch, tmp_path):
    from app.edition import (
        assert_under_root,
        edition_service_ports,
        family_forbidden_prompt_roots,
        family_prompt_context_paths,
        last_chat_summary_path,
    )

    expected_ports = {
        "amp": {"Backend API": 8011, "Command Center": 3011},
        "maxine": {"Backend API": 8012, "Command Center": 3012},
    }
    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        _family_env(monkeypatch, root, edition)
        paths = family_prompt_context_paths()
        assert paths
        forbidden = family_forbidden_prompt_roots()
        for name, path in paths.items():
            resolved = path.expanduser().resolve()
            assert_under_root(resolved, root)
            assert "empire-repo" not in str(resolved)
            assert ".claude-context" not in str(resolved)
            for banned in forbidden:
                banned_res = banned.expanduser().resolve()
                assert resolved != banned_res
                assert banned_res not in resolved.parents
        assert last_chat_summary_path() is None
        ports = edition_service_ports()
        assert ports == expected_ports[edition]
        assert 8000 not in ports.values()
        assert 3005 not in ports.values()
        assert 7878 not in ports.values()


def test_family_system_prompt_has_no_workroom_text(monkeypatch, tmp_path):
    from app.edition import brain_sync_storage_paths
    from app.services.max.hermes_memory import memory_root, render_hermes_bridge_for_prompt
    from app.services.max.supermemory_recall import store_path
    from app.services.max.continuity_compaction import default_handoff_path
    from app.services.max.system_prompt import get_max_brain_context, get_system_prompt

    for edition, assistant in (("amp", "Max-e"), ("maxine", "Maxine")):
        root = tmp_path / f"prompt-{edition}"
        _family_env(monkeypatch, root, edition)
        assert memory_root().resolve() == (root / "assistant" / "hermes").resolve()
        assert store_path().resolve() == (root / "assistant" / "brain" / "supermemory_scaffold.jsonl").resolve()
        assert default_handoff_path().resolve() == (root / "assistant" / "brain" / "session_handoff.json").resolve()
        storage = brain_sync_storage_paths()
        assert storage["quotes"].resolve() == (root / "quotes").resolve()
        assert storage["inbox"].resolve() == (root / "inbox").resolve()
        assert root.resolve() in Path(storage["brain_db"]).resolve().parents

        prompt = get_system_prompt()
        live = get_max_brain_context()
        hermes = render_hermes_bridge_for_prompt(compact=False)
        blob = "\n".join([prompt, live, hermes])
        assert assistant in prompt
        for leak in WORKROOM_PROMPT_LEAKS:
            assert leak not in blob, f"{edition} leaked {leak!r}"
        assert ":8000" not in live
        assert ":3005" not in live
        assert ":7878" not in live


def test_founder_profile_is_owner_name_only(monkeypatch, tmp_path):
    from app.edition import ensure_founder_profile

    _family_env(monkeypatch, tmp_path / "amp", "amp")
    profile = ensure_founder_profile()
    assert profile["role"] == "founder"
    assert profile["owner_name"] == AMP_COACH_NAME
    assert profile["workroom"] is None
    assert profile["preferences"] == {}
    assert profile["notes"] == ""
    dumped = str(profile).lower()
    assert "hyattsville" not in dumped
    assert "quote" not in dumped
    stub = tmp_path / "amp" / "assistant" / "brain" / "founder_profile.md"
    assert stub.is_file()
    text = stub.read_text(encoding="utf-8")
    assert AMP_COACH_NAME in text
    assert "Workroom" in text  # the "Sin datos del Workroom" disclaimer
    assert "Hyattsville" not in text

    _family_env(monkeypatch, tmp_path / "maxine", "maxine")
    maxine = ensure_founder_profile()
    assert maxine["owner_name"] == MAXINE_OWNER_NAME
    assert maxine["workroom"] is None


def test_family_extraction_prompts_are_spanish(monkeypatch, tmp_path):
    from app.services.max.brain.local_llm import extraction_prompts

    _family_env(monkeypatch, tmp_path / "amp", "amp")
    user, system = extraction_prompts("summarize", "hola")
    assert "español" in system.lower() or "español" in user.lower()
    assert "Responde solo en JSON" in user
    classify_user, classify_system = extraction_prompts("classify", "necesito una cotización")
    assert "español" in classify_system.lower() or "español" in classify_user.lower()
    facts_user, facts_system = extraction_prompts("facts", "Juan es el dueño")
    assert "español" in facts_system.lower() or "español" in facts_user.lower()

    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("ASSISTANT_NAME", raising=False)
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    en_user, en_system = extraction_prompts("summarize", "hello")
    assert "español" not in en_system.lower()
    assert "Summarize this conversation" in en_user
