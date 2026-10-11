"""Maxine refuses company legal-detail asks. Category words only; no stored values."""
from __future__ import annotations

from pathlib import Path

from app.routers.max.router import ChatRequest, _maybe_handle_direct_route_request
from app.services.max.family_answer_policy import (
    REFUSAL_EN,
    REFUSAL_ES,
    family_answer_policy_reply,
    is_save_offer_reply,
    looks_like_company_legal_query,
    maxine_legal_prompt_rule,
    reply_locale,
    should_skip_public_lookup,
)
from app.services.max.family_memory import extract_user_stated_facts


LEGAL_ASKS_ES = (
    "¿Cuál es la razón social, el NIT y los datos legales de Argos Campestre o Grupo Argos Campestre?",
    "¿Cuál es la razón social de la compañía?",
    "¿Me das el NIT y el registro mercantil?",
    "¿Quiénes son los accionistas y el representante legal?",
    "¿Cuál es la composición accionaria y el capital social?",
    "Pásame las escrituras de constitución y los abogados de la sociedad",
)

LEGAL_ASKS_EN = (
    "What is the legal name and tax ID of the company?",
    "Who are the shareholders and company officers?",
    "Tell me the company registration and ownership split",
    "What are the company deeds and the lawyers?",
)

PUBLIC_PROJECT_ASKS = (
    "¿Cuántos lotes tiene el proyecto?",
    "¿Dónde queda Portal Campestre 2?",
    "Recuerda que mi empresa se llama Norte Solar",
    "How many lots are available?",
    "hola, ¿qué hay de nuevo?",
)

SAVE_OFFERS = (
    "Compárteme los datos y te los guardo",
    "Pásame la información y la guardo",
    "Share the data and I'll save it",
    "Send me the data and I will save it",
)


def _family(monkeypatch, tmp_path, edition: str):
    root = tmp_path / edition
    root.mkdir()
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    from app.edition import apply_amp_process_paths
    from app.services.max.system_prompt import _prompt_cache

    apply_amp_process_paths()
    _prompt_cache.update({"prompt": None, "expires": 0, "edition": None})
    return root


def test_detector_matches_spanish_and_english_category_asks():
    for question in LEGAL_ASKS_ES + LEGAL_ASKS_EN:
        assert looks_like_company_legal_query(question), question
    for question in PUBLIC_PROJECT_ASKS:
        assert not looks_like_company_legal_query(question), question


def test_locale_defaults_to_spanish():
    assert reply_locale(LEGAL_ASKS_ES[0]) == "es"
    assert reply_locale(LEGAL_ASKS_EN[0]) == "en"
    assert reply_locale("NIT y razón social") == "es"


def test_maxine_refuses_in_user_language(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    es = family_answer_policy_reply(LEGAL_ASKS_ES[0])
    en = family_answer_policy_reply(LEGAL_ASKS_EN[0])
    assert es == REFUSAL_ES
    assert en == REFUSAL_EN
    assert "no tengo" in es.lower()
    assert "no comparto" in es.lower()
    assert "información pública" in es.lower()
    assert "don't hold" in en.lower()
    assert "legal details" in en.lower()
    assert "public project" in en.lower()
    assert not is_save_offer_reply(es)
    assert not is_save_offer_reply(en)
    for offer in SAVE_OFFERS:
        assert is_save_offer_reply(offer), offer


def test_amp_and_workroom_do_not_use_this_refusal(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    assert family_answer_policy_reply(LEGAL_ASKS_ES[0]) is None
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    monkeypatch.delenv("ASSISTANT_NAME", raising=False)
    assert family_answer_policy_reply(LEGAL_ASKS_ES[0]) is None


def test_fail_closed_when_edition_lookup_breaks(monkeypatch):
    import app.services.max.family_answer_policy as policy

    def boom():
        raise RuntimeError("edition unavailable")

    monkeypatch.setattr(policy, "_edition_is_maxine", boom)
    reply = policy.family_answer_policy_reply(LEGAL_ASKS_ES[0])
    assert reply == REFUSAL_ES
    assert policy.family_answer_policy_reply("hola, ¿cuántos lotes hay?") is None


def test_direct_route_returns_policy_on_maxine(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    req = ChatRequest(message=LEGAL_ASKS_ES[0], history=[], channel="web")
    routed = _maybe_handle_direct_route_request(req)
    assert routed is not None
    assert routed.model_used == "family-answer-policy"
    assert routed.response == REFUSAL_ES
    public = ChatRequest(message="¿Cuántos lotes tiene el proyecto?", history=[], channel="web")
    assert _maybe_handle_direct_route_request(public) is None or (
        _maybe_handle_direct_route_request(public).model_used != "family-answer-policy"
    )


def test_memory_does_not_store_legal_category_asks(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    assert extract_user_stated_facts(LEGAL_ASKS_ES[0]) == []
    assert extract_user_stated_facts("Recuerda el NIT y la razón social de la empresa") == []
    kept = extract_user_stated_facts("Recuerda que mi empresa se llama Norte Solar")
    assert kept and kept[0]["value"] == "Norte Solar"


def test_maxine_prompt_has_category_rule_without_stored_values(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    from app.edition import edition_prompt_suffix
    from app.services.max.system_prompt import get_system_prompt

    prompt = get_system_prompt()
    suffix = edition_prompt_suffix()
    rule = maxine_legal_prompt_rule()
    assert rule in prompt
    assert rule in suffix
    blob = "\n".join([prompt, suffix, rule, REFUSAL_ES, REFUSAL_EN])
    assert not any(ch.isdigit() and "NIT" in blob[max(0, i - 8) : i + 8] for i, ch in enumerate(blob))
    for leak in ("900", "S.A.S.", "representante: ", "% de"):
        assert leak not in blob


def test_amp_prompt_omits_maxine_legal_block(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    from app.services.max.system_prompt import get_system_prompt

    prompt = get_system_prompt()
    assert "COMPANY LEGAL DETAILS" not in prompt
    assert maxine_legal_prompt_rule() not in prompt


def test_factual_guard_skips_lookup_on_maxine_legal_ask(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    from app.services.max.factual_guard import is_factual_question

    assert should_skip_public_lookup(LEGAL_ASKS_ES[0]) is True
    assert is_factual_question(LEGAL_ASKS_ES[0]) is False
    assert is_factual_question("¿Cuántos lotes tiene el proyecto?") is False


def test_policy_sources_use_category_words_only():
    root = Path(__file__).resolve().parents[2]
    paths = [
        root / "backend" / "app" / "services" / "max" / "family_answer_policy.py",
        Path(__file__),
    ]
    banned = ("S.A.S.", "S.A ", "900111", "cedula", "cédula")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for needle in banned:
            assert needle not in text, f"{path} contains {needle!r}"
        assert "razón social" in text or "razon social" in text.lower() or "legal name" in text.lower()
