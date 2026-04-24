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
