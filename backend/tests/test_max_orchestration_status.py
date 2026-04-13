import asyncio


def test_local_vision_triage_is_prepended_to_image_context(tmp_path, monkeypatch):
    from app.services.max.ai_router import AIRouter, AIMessage
    import app.services.ollama_vision_router as vision_router

    image_path = tmp_path / "proof.png"
    image_path.write_bytes(b"not-a-real-png-but-valid-for-base64")

    async def fake_generate_vision_response(*, prompt, image_b64, preferred_model=None, timeout=120.0):
        assert "local lightweight vision triage" in prompt
        assert image_b64
        assert timeout == 60.0
        return "local image summary", "moondream"

    monkeypatch.setattr(vision_router, "generate_vision_response", fake_generate_vision_response)

    router = AIRouter()
    messages = [AIMessage(role="user", content="Analyze this for MAX.")]
    updated = asyncio.run(router._prepend_local_vision_triage(messages, image_path))

    assert updated[-1].content.startswith("[Local Ollama vision triage via moondream")
    assert "route moondream -> llava" in updated[-1].content
    assert "local image summary" in updated[-1].content
    assert updated[-1].content.endswith("Analyze this for MAX.")


def test_orchestration_status_reports_max_hierarchy_and_live_local_routes(monkeypatch):
    import importlib
    import httpx

    max_router = importlib.import_module("app.routers.max.router")

    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            if "/api/tags" in url:
                return FakeResponse({"models": [{"name": "moondream:latest"}, {"name": "llava:latest"}]})
            if url.endswith("/health"):
                return FakeResponse({"status": "online"})
            return FakeResponse({})

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(max_router.desk_manager, "get_all_desks", lambda: [{"id": "forge"}, {"id": "it"}])

    async def fake_statuses():
        return [{"desk_id": "forge", "status": "idle"}]

    monkeypatch.setattr(max_router.ai_desk_manager, "get_all_statuses", fake_statuses)

    status = asyncio.run(max_router.orchestration_status())

    assert status["role"]["founder"] == "top"
    assert status["role"]["max"] == "primary_command_center_brain"
    assert status["role"]["ai_desks"] == "subordinate_specialists"
    assert status["role"]["openclaw"] == "execution_delegation_layer"
    assert status["entrypoints"]["web_chat"] == "/api/v1/max/chat/stream"
    assert status["capabilities"]["text_chat"] is True
    assert status["capabilities"]["image_upload_analysis"] is True
    assert status["capabilities"]["openclaw_delegation"] is True
    assert status["local_vision"]["primary"] == "moondream"
    assert status["local_vision"]["fallback"] == "llava"
    assert status["local_vision"]["ready"] is True
    assert status["desks"]["count"] == 2
    assert status["code_mode"]["mode"] == "subordinate_to_max"
    assert status["code_mode"]["executor"] == "CodeForge / Atlas"
    assert status["self_heal"]["mode"] == "guided_self_heal"
    assert status["self_heal"]["full_autonomous_repair_verified"] is False
    assert status["voice"]["stt"]["configured"] is not None
    assert status["voice"]["tts"]["last_status"] in {"not_checked", "ok", "failed", "unconfigured"}


def test_compact_prompt_is_used_only_for_ordinary_text():
    from app.services.max.system_prompt import (
        get_compact_system_prompt,
        get_system_prompt,
        is_ordinary_text_request,
    )

    assert len(get_compact_system_prompt()) < 1500
    assert len(get_system_prompt()) > len(get_compact_system_prompt()) * 10
    assert is_ordinary_text_request("MAX text routing proof. Reply briefly.") is True
    assert is_ordinary_text_request("create a task for the forge desk") is False
    assert is_ordinary_text_request("show my invoices") is False
    assert is_ordinary_text_request("analyze this quote") is False


def test_code_mode_service_manager_uses_actual_portal_unit():
    from app.services.max.tool_executor import (
        SERVICE_MAP,
        SYSTEMD_SERVICES,
        _should_retry_systemctl_with_sudo,
        _systemctl_cmd,
    )

    assert SERVICE_MAP["cc"]["systemd"] == "empire-portal"
    assert "empire-portal" in SYSTEMD_SERVICES
    assert "empire-cc" not in SYSTEMD_SERVICES
    assert _systemctl_cmd("empire-portal", "is-active", "--quiet") == [
        "systemctl",
        "--user",
        "is-active",
        "--quiet",
        "empire-portal",
    ]
    assert _systemctl_cmd("ollama", "is-active", "--quiet") == [
        "systemctl",
        "is-active",
        "--quiet",
        "ollama",
    ]
    assert _should_retry_systemctl_with_sudo("empire-portal", "Access denied") is False
    assert _should_retry_systemctl_with_sudo("ollama", "Access denied") is True
