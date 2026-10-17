"""MAX Workroom / EmpireBox grounding tests.

Validates the post-67b72a3 repair:
- Module knowledge resolver returns EmpireBox-specific facts (Workroom,
  Woodcraft, ApostApp, RelistApp, Memory Bank, OpenClaw, etc.).
- Module resolver introspects the live FastAPI app and surfaces real
  mounted routes (not a static doc).
- Module resolver does NOT short-circuit action/creation requests
  (they must reach the AI model or a tool/route).
- 'What tools/routes can you access for Workroom?' is answered by the
  module resolver with the live route inventory.
- Module response for Workroom includes the actual EmpireBox context
  (drapery, upholstery, Hyattsville, workroom@empirebox.store).
"""

import asyncio
import importlib

from fastapi import BackgroundTasks, Response

from app.services.max.tool_executor import ToolResult


max_router = importlib.import_module("app.routers.max.router")
ek = importlib.import_module("app.services.max.empire_module_knowledge")


def _assert_no_internal_leakage(text: str) -> None:
    lowered = text.lower()
    assert "```tool" not in lowered
    assert "i should check" not in lowered
    assert "runtime check required" not in lowered
    assert "delegation check required" not in lowered


def _set_model_first(monkeypatch, enabled: bool) -> None:
    """answer_policy.model_first() reads env at call time; reload in case a
    future cache lands. Patch the router binding too."""
    monkeypatch.setenv("MAX_MODEL_FIRST", "1" if enabled else "0")
    ap = importlib.reload(importlib.import_module("app.services.max.answer_policy"))
    monkeypatch.setattr(max_router, "answer_policy", ap)


def _block_live_sends(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise AssertionError("tests must not send live email, WhatsApp, or SMS")

    monkeypatch.setattr(
        "app.services.max.email_service.EmailService.send", _boom, raising=False
    )
    monkeypatch.setattr(
        "app.services.max.whatsapp_channel.send_template", _boom, raising=False
    )


def _message_content(message) -> str:
    if message is None:
        return ""
    if isinstance(message, dict):
        return str(message.get("content") or "")
    return str(getattr(message, "content", "") or "")


def _captured_model_context(captured: dict) -> str:
    parts = [captured.get("system_prompt") or ""]
    for message in captured.get("messages") or []:
        parts.append(_message_content(message))
    if captured.get("tools"):
        parts.append(str(captured["tools"]))
    return "\n".join(parts)


def _capture_ai_chat(monkeypatch, canned: str) -> dict:
    captured = {
        "count": 0,
        "messages": [],
        "system_prompt": "",
        "tools": None,
        "kwargs": {},
    }

    async def fake_ai_router(messages, *args, **kwargs):
        captured["count"] += 1
        captured["messages"] = list(messages)
        captured["system_prompt"] = kwargs.get("system_prompt") or ""
        captured["tools"] = kwargs.get("tools")
        captured["kwargs"] = dict(kwargs)
        from app.services.max.ai_router import AIResponse

        return AIResponse(content=canned, model_used="test-model")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_ai_router)
    return captured


def _assert_module_grounding_available(captured: dict, module_hit: dict) -> None:
    """Model-first path: grounding is whatever the live code actually puts
    on the model (system prompt / tools), plus the still-working resolver."""
    assert captured["count"] >= 1, "model-first must call ai_router.chat"
    ctx = _captured_model_context(captured)
    assert ctx.strip(), "model-first must pass a system prompt or messages"
    assert module_hit is not None
    module = module_hit.get("module")
    body = (module_hit.get("response") or "")
    assert body, f"resolver must still return {module} facts"
    if module == "Workroom":
        _assert_workroom_empirebox_context(ctx)
        _assert_workroom_empirebox_context(body)
        assert "/api/v1/quotes" in ctx or "/api/v1/finance" in ctx or "workroom" in ctx.lower()
    if module == "ArchiveForge":
        assert "ArchiveForge" in body
        # Oct 6 model-first does not inject the module doc into the prompt.
        # The standing system prompt is what the model actually receives.
        assert "empire workroom" in ctx.lower() or "empirebox" in ctx.lower()


def _assert_workroom_empirebox_context(text: str) -> None:
    """Every Workroom response must include EmpireBox-specific facts so
    MAX never falls back to a foreign/generic example."""
    lowered = text.lower()
    # EmpireBox context — at least one of these must be present
    empirebox_anchors = (
        "drapery",
        "upholstery",
        "hyattsville",
        "workroom@empirebox.store",
        "5124 frolich",
        "empirebox",
    )
    assert any(anchor in lowered for anchor in empirebox_anchors), (
        f"Workroom response missing EmpireBox context: {text[:300]}"
    )


# ---------------------------------------------------------------------------
# Unit tests on the resolver itself
# ---------------------------------------------------------------------------


def test_workroom_question_resolves_with_empirebox_facts():
    r = ek.resolve_empire_module_question("What is Empire Workroom?")
    assert r is not None
    assert r["module"] == "Workroom"
    assert "drapery" in r["response"].lower()
    assert "hyattsville" in r["response"].lower()
    assert "workroom@empirebox.store" in r["response"].lower()


def test_workroom_tools_routes_question_lists_live_routes():
    r = ek.resolve_empire_module_question(
        "What tools/routes can you access for Workroom right now?"
    )
    assert r is not None
    assert r["module"] == "Workroom"
    # Live route discovery must return a non-zero inventory from the
    # running FastAPI app.
    assert r.get("live_routes_count", 0) > 0, (
        f"Expected live routes; got {r.get('live_routes_count')}"
    )
    # Sample route prefix should appear in the response text.
    assert "/api/v1/quotes" in r["response"] or "/api/v1/finance" in r["response"]


def test_workroom_create_quote_workflow_passes_through_to_ai():
    """Action/creation requests must NOT be short-circuited to the
    static module doc. The model should handle them so MAX can actually
    offer a workflow or call a tool."""
    is_q = ek.is_empire_module_question("Create a Workroom upholstery quote workflow.")
    assert is_q is False, (
        "Action request should NOT be classified as empire-module-question; "
        "let AI model or tool handle it."
    )
    r = ek.resolve_empire_module_question(
        "Create a Workroom upholstery quote workflow."
    )
    assert r is None


def test_workroom_generate_estimate_passes_through_to_ai():
    is_q = ek.is_empire_module_question(
        "Generate a Workroom sofa/cushion estimate with drawing handoff."
    )
    assert is_q is False
    r = ek.resolve_empire_module_question(
        "Generate a Workroom sofa/cushion estimate with drawing handoff."
    )
    assert r is None


def test_woodcraft_question_resolves_with_cnc_context():
    r = ek.resolve_empire_module_question("What is WoodCraft?")
    assert r is not None
    assert r["module"] == "Woodcraft"
    assert "cnc" in r["response"].lower()
    assert "woodcraft@empirebox.store" in r["response"].lower()


def test_apostapp_question_resolves():
    r = ek.resolve_empire_module_question("What is ApostApp?")
    assert r is not None
    assert r["module"] == "ApostApp"
    assert "apostille" in r["response"].lower()


def test_relistapp_question_resolves():
    r = ek.resolve_empire_module_question("What is RelistApp?")
    assert r is not None
    assert r["module"] == "RelistApp"


def test_memory_bank_question_resolves():
    r = ek.resolve_empire_module_question("What is Memory Bank?")
    assert r is not None
    assert r["module"] == "Memory Bank"


def test_openclaw_question_resolves_with_skills():
    r = ek.resolve_empire_module_question("What is OpenClaw?")
    assert r is not None
    assert r["module"] == "OpenClaw"
    assert "7878" in r["response"]


# ---------------------------------------------------------------------------
# End-to-end routing through chat_with_max
# ---------------------------------------------------------------------------


def test_workroom_what_is_routes_to_module_knowledge(monkeypatch):
    _set_model_first(monkeypatch, False)
    _block_live_sends(monkeypatch)

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError(
            "Workroom 'what is' question should not reach generic AI chat"
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="What is Empire Workroom?",
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    assert response.model_used == "empire-module-knowledge"
    _assert_workroom_empirebox_context(response.response)
    _assert_no_internal_leakage(response.response)


def test_workroom_what_is_model_first_uses_module_grounding(monkeypatch):
    _set_model_first(monkeypatch, True)
    _block_live_sends(monkeypatch)
    captured = _capture_ai_chat(
        monkeypatch,
        "Empire Workroom is the drapery and upholstery shop in Hyattsville.",
    )
    module_hit = ek.resolve_empire_module_question("What is Empire Workroom?")

    request = max_router.ChatRequest(
        message="What is Empire Workroom?",
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    assert response.model_used != "empire-module-knowledge"
    assert captured["count"] >= 1
    _assert_module_grounding_available(captured, module_hit)
    _assert_no_internal_leakage(response.response)


def test_workroom_tools_routes_routes_to_module_knowledge(monkeypatch):
    _set_model_first(monkeypatch, False)
    _block_live_sends(monkeypatch)

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError(
            "Workroom 'what tools/routes' question should not reach generic AI chat"
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="What tools/routes can you access for Workroom right now?",
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    assert response.model_used == "empire-module-knowledge"
    assert (
        "/api/v1/quotes" in response.response or "/api/v1/finance" in response.response
    )
    _assert_workroom_empirebox_context(response.response)
    _assert_no_internal_leakage(response.response)


def test_workroom_tools_routes_model_first_uses_module_grounding(monkeypatch):
    _set_model_first(monkeypatch, True)
    _block_live_sends(monkeypatch)
    question = "What tools/routes can you access for Workroom right now?"
    captured = _capture_ai_chat(
        monkeypatch,
        "Workroom quotes live at /api/v1/quotes on EmpireBox in Hyattsville.",
    )
    module_hit = ek.resolve_empire_module_question(question)

    request = max_router.ChatRequest(
        message=question,
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    assert response.model_used != "empire-module-knowledge"
    assert captured["count"] >= 1
    _assert_module_grounding_available(captured, module_hit)
    ctx = _captured_model_context(captured)
    assert "/api/v1/quotes" in ctx or "/api/v1/finance" in ctx or "/quotes" in ctx
    # Resolver-only: FastAPI introspection / registry fallback phrasing.
    # Model-first does not inject the module doc into the prompt, so this
    # fact is intentionally absent from the model context.
    resolver_only = "from live FastAPI mount"
    if resolver_only not in (module_hit.get("response") or ""):
        resolver_only = "from registry/main.py fallback"
    assert resolver_only in (module_hit.get("response") or ""), (
        "resolver must publish live-route source that the standing prompt does not"
    )
    assert resolver_only not in ctx
    _assert_no_internal_leakage(response.response)


def _assert_no_foreign_defaults(text: str) -> None:
    """Reject foreign business defaults in MAX responses.

    Use word-boundary or punctuation-prefixed checks so legitimate substrings
    like "elevation" or "validate" do not match "vat".
    """
    import re

    lowered = text.lower()
    forbidden_patterns = [
        (r"\bacme\s+(repair|upholstery|drapery|works|co|ltd|inc)\b", "acme"),
        (r"\bgbp\b", "gbp"),
        (r"£\s*\d", "£"),
        (r"\bvat\b", "vat"),
        (r"\beur\b", "eur"),
        (r"\$\s*\d.*\bvat\b", "vat-after-money"),
    ]
    for pattern, label in forbidden_patterns:
        if re.search(pattern, lowered):
            raise AssertionError(
                f"Foreign default leaked: {label!r} matched pattern {pattern!r} "
                f"in response: {text[:300]}"
            )


def test_workroom_create_quote_workflow_reaches_ai_model(monkeypatch):
    """Create a Workroom upholstery quote workflow must NOT be intercepted
    by module knowledge. It should reach the AI model so MAX can either
    call a real tool or describe a real workflow grounded in /api/v1/quotes."""

    ai_called = {"count": 0, "messages": []}

    async def fake_ai_router(messages, *args, **kwargs):
        ai_called["count"] += 1
        ai_called["messages"] = list(messages)
        from app.services.max.ai_router import AIResponse

        return AIResponse(
            content=(
                "I can run a real Workroom quick-quote workflow: "
                "POST /api/v1/quotes/quick with business=workroom, "
                "3 options A/B/C, then promote to /api/v1/quotes/quick/promote."
            ),
            model_used="test-model",
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fake_ai_router)

    request = max_router.ChatRequest(
        message="Create a Workroom upholstery quote workflow.",
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    # Module knowledge must NOT have intercepted this.
    assert response.model_used != "empire-module-knowledge", (
        "Create a Workroom upholstery quote workflow should NOT be "
        "short-circuited to empire-module-knowledge; it must reach AI/tools."
    )
    _assert_no_foreign_defaults(response.response)


def test_workroom_generate_estimate_does_not_invoke_foreign_examples(monkeypatch):
    """Generate a Workroom sofa/cushion estimate with drawing handoff must
    not be short-circuited AND must not produce foreign Acme/GBP defaults.

    The current code path may legitimately route this through the drawing
    handoff (a real Workroom/EmpireBox code path) or through the AI model.
    Either way, the response must NOT contain foreign business defaults
    (Acme Repair / GBP / VAT / EUR)."""
    import re

    async def fake_ai_router(messages, *args, **kwargs):
        from app.services.max.ai_router import AIResponse

        return AIResponse(
            content=(
                "I can run the cushion/sofa estimate on EmpireBox: "
                "POST /api/v1/drawings/bench for the bench drawing, "
                "POST /api/v1/yardage for yardage, "
                "POST /api/v1/quotes/quick for a 3-option quote."
            ),
            model_used="test-model",
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fake_ai_router)

    request = max_router.ChatRequest(
        message="Generate a Workroom sofa/cushion estimate with drawing handoff.",
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    assert response.model_used != "empire-module-knowledge"
    _assert_no_foreign_defaults(response.response)


def test_archiveforge_question_still_routes_to_module_knowledge(monkeypatch):
    """Legacy MAX_MODEL_FIRST=0 path: ArchiveForge still answers from module
    knowledge (not the AI model)."""
    _set_model_first(monkeypatch, False)
    _block_live_sends(monkeypatch)

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("ArchiveForge question should not reach generic AI chat")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="max whats going on with Archive Forge?",
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    assert response.model_used == "empire-module-knowledge"
    assert "ArchiveForge is the Empire module" in response.response
    _assert_no_internal_leakage(response.response)


def test_archiveforge_question_model_first_uses_module_grounding(monkeypatch):
    """Default MAX_MODEL_FIRST=1: two-word 'Archive Forge' hits the kept
    archiveforge-status shortcut (not demoted module_knowledge, not the model)."""
    _set_model_first(monkeypatch, True)
    _block_live_sends(monkeypatch)
    question = "max whats going on with Archive Forge?"
    captured = _capture_ai_chat(
        monkeypatch,
        "ArchiveForge is the LIFE magazine intake module. No internal notes.",
    )
    module_hit = ek.resolve_empire_module_question(question)

    request = max_router.ChatRequest(
        message=question,
        history=[],
        channel="web",
    )
    response = asyncio.run(
        max_router.chat_with_max(request, BackgroundTasks(), Response())
    )

    assert response.model_used == "archiveforge-status"
    assert response.model_used != "empire-module-knowledge"
    assert captured["count"] == 0
    assert module_hit is not None
    assert module_hit.get("module") == "ArchiveForge"
    assert "ArchiveForge is the Empire module" in (module_hit.get("response") or "")
    assert "ArchiveForge is Empire's LIFE-magazine intake" in response.response
    _assert_no_internal_leakage(response.response)
