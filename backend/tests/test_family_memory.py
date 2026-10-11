"""Family editions persist owner facts under EMPIRE_DATA_DIR and recall them."""
from __future__ import annotations

from app.services.max.family_memory import (
    extract_user_stated_facts,
    family_memory_prompt_block,
    persist_user_stated_facts,
)


def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    from app.edition import apply_amp_process_paths, ensure_assistant_files
    apply_amp_process_paths()
    ensure_assistant_files()
    from app.services.max.system_prompt import _prompt_cache
    _prompt_cache.update({"prompt": None, "expires": 0, "edition": None})


def test_extracts_business_name_not_credential_code():
    facts = extract_user_stated_facts("Recuerda que mi empresa se llama Norte Solar")
    assert facts[0]["key"] == "trade_name"
    assert facts[0]["value"] == "Norte Solar"
    assert extract_user_stated_facts("remember this code ABC-991") == []
    assert extract_user_stated_facts("Nueva sesión. ¿Cómo se llama mi empresa?") == []


def test_persist_and_recall_across_prompt_rebuild(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    saved = persist_user_stated_facts("Recuerda que mi empresa se llama Norte Solar")
    assert saved
    from app.edition import assistant_memory_path
    from app.services.edition_facts import list_facts

    memory = assistant_memory_path().read_text(encoding="utf-8")
    assert "Norte Solar" in memory
    assert any(row.get("value") == "Norte Solar" for row in list_facts())

    block = family_memory_prompt_block()
    assert "Norte Solar" in block
    assert "todas las conversaciones" in block

    from app.services.max.system_prompt import get_system_prompt
    prompt = get_system_prompt()
    assert "Norte Solar" in prompt
    assert "solo para esta conversación" in prompt


def test_factual_guard_skips_remember_messages():
    from app.services.max.factual_guard import is_factual_question, is_memory_or_test_turn

    assert is_memory_or_test_turn("remember this code ABC123")
    assert is_memory_or_test_turn("Recuerda que mi empresa se llama Norte")
    assert is_memory_or_test_turn("Nueva sesión. ¿Cómo se llama mi empresa?")
    assert not is_factual_question("remember this code ABC123")
    assert not is_factual_question("Recuerda que mi empresa se llama Norte")
    assert not is_factual_question("Nueva sesión. ¿Cómo se llama mi empresa?")
