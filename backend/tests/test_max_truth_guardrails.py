import asyncio
import importlib

from fastapi import BackgroundTasks, Response
from fastapi.testclient import TestClient

from app.main import app
from app.services.max.ai_router import AIResponse


client = TestClient(app)


def test_queen_elizabeth_life_prompt_routes_to_hermes_prefill_not_drawing(monkeypatch, tmp_path):
    max_router = importlib.import_module("app.routers.max.router")
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("LIFE intake should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    response = client.post(
        "/api/v1/max/chat",
        json={
            "message": "Prepare a LIFE magazine intake draft for Queen Elizabeth. Use Hermes form-prep and browser assist only.",
            "channel": "web",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "hermes-form-prep"
    assert data["tool_results"][0]["result"]["workflow_key"] == "life_magazine_intake"
    assert data["tool_results"][0]["result"]["fields"]["cover_subject"] == "Queen Elizabeth"
    assert "No Hermes browser action was created from this request." in data["response"]
    assert "drawing-router" not in data["response"]


def test_queen_elizabeth_life_prompt_honors_plain_key_output_shape(monkeypatch, tmp_path):
    max_router = importlib.import_module("app.routers.max.router")
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("LIFE intake should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    response = client.post(
        "/api/v1/max/chat",
        json={
            "message": (
                "Prepare a LIFE magazine intake draft for Queen Elizabeth.\n"
                "Use Hermes form-prep only.\n"
                "Do not submit anything.\n\n"
                "Return only these exact keys as plain lines:\n"
                "draft_id:\n"
                "publication_title:\n"
                "cover_subject:\n"
                "real_cover_candidate_found:\n"
                "missing_required_fields:\n"
                "planned_browser_action_ids:"
            ),
            "channel": "web",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "hermes-form-prep"
    assert data["tool_results"][0]["result"]["fields"]["cover_subject"] == "Queen Elizabeth"
    assert data["tool_results"][0]["result"]["real_cover_candidate_found"] is True
    assert data["tool_results"][0]["result"]["planned_browser_action_ids"] == []
    assert data["response"].splitlines() == [
        f"draft_id: {data['tool_results'][0]['result']['id']}",
        "publication_title: LIFE",
        "cover_subject: Queen Elizabeth",
        "real_cover_candidate_found: yes",
        "missing_required_fields: issue_date, condition, source_box",
        "planned_browser_action_ids: none",
    ]


def test_archiveforge_lookup_returns_truthful_no_draft(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("ArchiveForge lookup should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="ArchiveForge cover search issue lookup for Queen Elizabeth",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "hermes-form-prep"
    assert response.tool_results[0]["result"]["draft_created"] is False
    assert "No Hermes intake draft was created from this message." in response.response


def test_browser_assist_guardrail_blocks_fabricated_ids(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fake_ai_router(*args, **kwargs):
        return AIResponse(
            content="Simulated browser assist prepared. Action id: hermes_browser_id_001",
            model_used="test-model",
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fake_ai_router)

    request = max_router.ChatRequest(
        message="The browser assist answer sounded simulated.",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "test-model"
    assert "No Hermes browser action was created from this request." in response.response
    assert "simulated" not in response.response.lower()
    assert "hermes_browser_id_001" not in response.response


def test_email_send_request_cannot_claim_sent_without_real_result(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Unverified email send request should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(message="Send to my email", history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "email-truth-guardrail"
    assert "I have not sent anything" in response.response
    assert "cannot claim an email or attachment was delivered" in response.response
    assert response.tool_results[0]["result"]["verified_send_result"] is False


def test_email_reply_read_request_labels_partial_threading(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Partial email threading guardrail should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(message="Can you read my reply?", history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "email-truth-guardrail"
    assert "Email MAX is partial." in response.response
    assert "I have not fetched the exact email thread/message" in response.response
    assert "Reply threading continuity is partial" in response.response
    assert response.tool_results[0]["result"]["thread_continuity"] == "partial"


def test_check_openclaw_routes_to_gate_specific_response(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    openclaw_gate = importlib.import_module("app.services.max.openclaw_gate")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("OpenClaw gate check should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    monkeypatch.setattr(
        openclaw_gate,
        "check_openclaw_gate",
        lambda force=False, timeout=2.0: openclaw_gate.OpenClawGateResult(
            state="healthy",
            allowed=True,
            reason="health endpoint, local queue, and worker heartbeat ready",
            checked_at="2026-04-24T14:40:00+00:00",
            cache_ttl_seconds=20,
            cache_age_seconds=0.0,
            health_endpoint="http://localhost:7878/health",
            founder_message="OpenClaw healthy - delegating task now.",
        ),
    )

    request = max_router.ChatRequest(message="check OpenClaw", history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "openclaw-gate-check"
    assert "State: healthy" in response.response
    assert "Reason: health endpoint, local queue, and worker heartbeat ready" in response.response
    assert response.tool_results[0]["tool"] == "openclaw_gate_check"
    assert response.tool_results[0]["result"]["state"] == "healthy"


def test_gmail_inbox_invalid_grant_returns_reauth_boundary(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Gmail inbox guardrail should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    monkeypatch.setattr(
        max_router,
        "execute_tool",
        lambda *args, **kwargs: max_router.ToolResult(
            tool="check_email",
            success=False,
            error="('invalid_grant: Token has been expired or revoked.', {'error': 'invalid_grant'})",
        ),
    )

    request = max_router.ChatRequest(message="check my Gmail inbox", history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "gmail-inbox-boundary"
    assert "reauth required" in response.response.lower()
    assert "I did not read any inbox messages." in response.response
    assert response.tool_results[0]["tool"] == "check_email"
    assert response.tool_results[0]["success"] is False


# ── EmpireDell GPU Stability Lock ─────────────────────────────────────

def test_gpu_safety_apt_autoremove_blocked(monkeypatch):
    """apt autoremove on EmpireDell is blocked by GPU stability lock."""
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("GPU safety guardrail should block before AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="run sudo apt autoremove",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "gpu-safety-guardrail"
    assert "EmpireDell GPU stability lock is active" in response.response
    assert "apt autoremove" in response.response
    assert response.tool_results[0]["tool"] == "gpu_safety_check"
    assert response.tool_results[0]["result"]["risky"] is True


def test_gpu_safety_nvidia_upgrade_warns(monkeypatch):
    """NVIDIA driver upgrade on EmpireDell triggers GPU stability lock."""
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("GPU safety guardrail should block before AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="upgrade NVIDIA driver",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "gpu-safety-guardrail"
    assert "EmpireDell GPU stability lock is active" in response.response
    assert "470.239.06" in response.response
    assert response.tool_results[0]["result"]["risky"] is True


def test_gpu_safety_resolution_broken_shows_verification(monkeypatch):
    """Resolution broken query triggers GPU safety + verification commands."""
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("GPU safety guardrail should block before AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="why is my resolution broken?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "gpu-safety-guardrail"
    assert "EmpireDell GPU stability lock is active" in response.response
    assert "uname -r" in response.response
    assert "nvidia-smi" in response.response
    assert "6.8.0-31-generic" in response.response
    assert "470.239.06" in response.response


def test_gpu_safety_update_ubuntu_requires_simulation(monkeypatch):
    """Updating Ubuntu triggers GPU safety lock + simulation requirement."""
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("GPU safety guardrail should block before AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="can I update Ubuntu?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "gpu-safety-guardrail"
    assert "EmpireDell GPU stability lock is active" in response.response
    assert "simulation" in response.response
    assert "apt-get -s upgrade" in response.response


def test_gpu_safety_nvidia_driver_470_install_blocked(monkeypatch):
    """Installing nvidia-driver-470 is blocked because DKMS path caused crash."""
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("GPU safety guardrail should block before AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="install nvidia-driver-470",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "gpu-safety-guardrail"
    assert "DKMS" in response.response
    assert "crash loop" in response.response
    assert "prebuilt" in response.response
    assert "470.239.06" in response.response


def test_gpu_safety_safe_message_passes_through(monkeypatch):
    """Ordinary non-GPU messages should not trigger GPU safety guardrail."""
    max_router = importlib.import_module("app.routers.max.router")

    async def no_call(*args, **kwargs):
        # This should be called (not blocked by GPU guardrail)
        return AIResponse(content="Hello, how can I help?", model_used="test")

    call_count = {"n": 0}

    async def counting_ai_router(*args, **kwargs):
        call_count["n"] += 1
        return await no_call(*args, **kwargs)

    monkeypatch.setattr(max_router.ai_router, "chat", counting_ai_router)

    request = max_router.ChatRequest(
        message="what is the status of my quotes?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    # Should NOT be a gpu-safety-guardrail response
    assert response.model_used != "gpu-safety-guardrail"
    # And it should have gone to the AI router
    assert call_count["n"] > 0
