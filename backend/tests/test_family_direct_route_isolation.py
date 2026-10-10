"""Family editions must not get Rafael's canned Workroom / CraftForge blurbs."""
from __future__ import annotations

import importlib

from app.routers.max.router import ChatRequest, _empire_module_response, _maybe_handle_direct_route_request
from app.services.max.empire_module_knowledge import resolve_empire_module_question


SHOP_LEAKS = (
    "Frolich",
    "Hyattsville",
    "workroom@",
    "WoodCraft",
    "woodcraft@",
    "5124",
)

WORKROOM_QUESTIONS = (
    "what is the Workroom?",
    "¿qué es el Workroom?",
    "¿qué sabes del Workroom?",
    "What is Empire Workroom?",
)

CRAFT_LUXE_QUESTIONS = (
    "what is craftforge",
    "¿qué es CraftForge?",
    "what is luxeforge",
    "¿qué es LuxeForge?",
)


def _family(monkeypatch, tmp_path, edition: str):
    root = tmp_path / edition
    root.mkdir()
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    return root


def _assert_clean(text: str, edition: str, question: str) -> None:
    for leak in SHOP_LEAKS:
        assert leak not in text, f"{edition} {question!r} leaked {leak!r}: {text}"


def test_family_direct_route_skips_workroom_craft_and_luxe(monkeypatch, tmp_path):
    importlib.reload(importlib.import_module("app.services.max.empire_module_knowledge"))
    for edition in ("amp", "maxine"):
        _family(monkeypatch, tmp_path, edition)
        for question in WORKROOM_QUESTIONS:
            hit = resolve_empire_module_question(question)
            assert hit is not None, question
            assert hit.get("family_unknown") is True
            assert hit["module"] == "Workroom"
            _assert_clean(hit["response"], edition, question)
            lowered = hit["response"].lower()
            assert "no conozco" in lowered or "no tiene sus datos" in lowered
            req = ChatRequest(message=question, history=[], channel="web")
            routed = _empire_module_response(req)
            assert routed is not None
            _assert_clean(routed.response, edition, question)
            assert "Hyattsville" not in routed.response
            direct = _maybe_handle_direct_route_request(req)
            assert direct is not None
            _assert_clean(direct.response, edition, question)

        for question in CRAFT_LUXE_QUESTIONS:
            hit = resolve_empire_module_question(question)
            assert hit is not None, question
            assert hit.get("family_unknown") is True
            _assert_clean(hit["response"], edition, question)
            req = ChatRequest(message=question, history=[], channel="web")
            routed = _empire_module_response(req)
            assert routed is not None
            _assert_clean(routed.response, edition, question)


def test_family_catalog_and_voice_schema_have_no_nelma_or_willard(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    from app.services.max.ecosystem_catalog import get_catalog_summary
    from app.services.max.voice_live import _FALLBACK_TOOL_SCHEMAS

    assert get_catalog_summary() == ""
    query = str(_FALLBACK_TOOL_SCHEMAS["search_quotes"])
    assert "Willard" not in query
    assert "Nelma" not in query
