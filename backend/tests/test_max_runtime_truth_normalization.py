import asyncio
import importlib
from dataclasses import dataclass

from fastapi import BackgroundTasks, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import app
from app.services.max.ai_router import AIResponse
from app.services.max.runtime_truth_enforcer import (
    enforce_runtime_truth_response,
    should_halt_after_tool_failure,
)
from app.services.max.tool_executor import ToolResult, execute_tool
from app.services.max.tool_result_normalizer import normalize_runtime_result, normalize_tool_result_entry
from app.services.max.evaluation_service import EvaluationService


max_router = importlib.import_module("app.routers.max.router")
client = TestClient(app)


@dataclass
class DataclassResult:
    success: bool
    result: dict
    provider: str = "unit-test"


class PydanticResult(BaseModel):
    success: bool
    data: dict
    provider: str


class SdkStyleResult:
    def __init__(self):
        self.success = True
        self.result = {"accepted": True}
        self.provider = "sdk"


def test_tool_result_object_without_get_normalizes_and_does_not_crash(tmp_path):
    result = ToolResult(tool="send_email", success=False, error="SMTP rejected")

    normalized = normalize_tool_result_entry(result)

    assert normalized["tool"] == "send_email"
    assert normalized["success"] is False
    assert normalized["error"] == "SMTP rejected"

    service = EvaluationService()
    original_db_path = service.db_path
    service.db_path = str(tmp_path / "eval.db")
    service._ensure_schema()
    service.log_response(
        response_id="tool-result-object",
        channel="web",
        conversation_id="conv",
        message="send the analysis",
        model_used="unit-test",
        tools_used=["send_email"],
        tool_results=[result],
        latency_ms=1,
        response_length=10,
        fallback_used=False,
    )
    service.db_path = original_db_path


def test_normalizer_handles_typed_objects_and_exceptions():
    assert normalize_runtime_result({"success": True, "data": {"ok": 1}})["data"] == {"ok": 1}
    assert normalize_runtime_result(DataclassResult(True, {"ok": 2}))["provider"] == "unit-test"
    assert normalize_runtime_result(PydanticResult(success=True, data={"ok": 3}, provider="pydantic"))["data"] == {"ok": 3}
    assert normalize_runtime_result(SdkStyleResult())["data"] == {"accepted": True}
    failed = normalize_runtime_result(RuntimeError("provider down"))
    assert failed["success"] is False
    assert failed["error"] == "provider down"
    assert normalize_runtime_result(None)["success"] is False


def test_send_email_failure_cannot_produce_success_message():
    response = enforce_runtime_truth_response(
        "email the analysis to me",
        "Done, I sent it with the PDF attached.",
        [ToolResult(tool="send_email", success=False, error="Email body is empty")],
    )

    assert response.startswith("I attempted this, but verification failed:")
    assert "Email body is empty" in response
    assert "Done" not in response


def test_missing_attachment_request_is_marked_incomplete():
    response = enforce_runtime_truth_response(
        "send the PDF attachment",
        "Sent with the PDF attached.",
        [ToolResult(tool="send_email", success=True, result={"sent_to": "founder@example.com", "attachments_sent": 0})],
    )

    assert "requested attachment was not verified" in response


def test_pdf_generation_works_without_ollama(monkeypatch, tmp_path):
    monkeypatch.setenv("MAX_DISABLE_OLLAMA", "true")
    output_path = tmp_path / "proof.pdf"
    result = execute_tool(
        {
            "tool": "svg_to_pdf",
            "svg_content": "<svg xmlns='http://www.w3.org/2000/svg' width='100' height='50'><text x='5' y='25'>Proof</text></svg>",
            "output_path": str(output_path),
        },
        founder=True,
    )

    assert result.success is True
    assert result.result["pdf_path"] == str(output_path)
    assert result.result["size_bytes"] > 0
    assert output_path.exists()


def test_provider_unavailable_message_is_user_facing_not_raw(monkeypatch):
    monkeypatch.setattr(max_router.ai_router, "last_provider_errors", {"ollama": "connection refused"})

    message = max_router.ai_router._provider_unavailable_message()

    assert "Ollama not available" not in message
    assert "connection refused" not in message
    assert "no configured text provider returned a verified response" in message


def test_present_tool_documentation_does_not_claim_external_send():
    from app.services.max.tool_executor import TOOLS_DOC

    assert "Generate a professional presentation/report on a topic and send PDF via Telegram" not in TOOLS_DOC
    assert "It does not send externally" in TOOLS_DOC


def test_runtime_truth_halts_after_verification_failure():
    assert should_halt_after_tool_failure(
        [ToolResult(tool="send_email", success=False, error="missing attachment")],
        user_message="send the attached analysis",
    )


def test_max_response_replaces_false_success_after_tool_failure(monkeypatch):
    calls = {"count": 0}

    async def fake_chat(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] > 1:
            raise AssertionError("MAX should halt after the failed send_email tool")
        return AIResponse(
            content='```tool\n{"tool":"send_email","to":"founder@example.com","subject":"Analysis","body":"Report"}\n```',
            model_used="unit-test",
        )

    def fake_execute_tool(*args, **kwargs):
        return ToolResult(tool="send_email", success=False, error="SMTP rejected")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)

    request = max_router.ChatRequest(
        message="Handle this analysis delivery through the appropriate tool.",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert calls["count"] == 1
    assert response.tool_results[0]["success"] is False
    assert response.response == "I attempted this, but verification failed: send_email: SMTP rejected"
    assert "sent" not in response.response.lower()


def test_presentation_telegram_route_fails_when_send_unverified(monkeypatch, tmp_path):
    pdf_path = tmp_path / "presentation.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%proof\n")

    monkeypatch.setattr("app.services.max.tool_executor._render_presentation_pdf", lambda data: str(pdf_path))

    class FakeTelegramBot:
        is_configured = True

        async def send_document(self, *args, **kwargs):
            return False

    monkeypatch.setattr("app.services.max.telegram_bot.TelegramBot", FakeTelegramBot)

    res = client.post(
        "/api/v1/max/present/telegram",
        json={"title": "Runtime Truth", "sections": [{"title": "One"}], "model_used": "unit-test"},
    )

    assert res.status_code == 502
    assert "send was not verified" in res.json()["detail"]


def test_auto_email_pdf_failure_does_not_report_emailed(monkeypatch, tmp_path):
    import app.services.max.email_service as email_service_module
    from app.services.max.tool_executor import _auto_email_pdf

    pdf_path = tmp_path / "drawing.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%proof\n")

    class FakeEmailService:
        is_configured = True

        def send(self, *args, **kwargs):
            return False

    monkeypatch.setattr(email_service_module, "EmailService", FakeEmailService)

    result = _auto_email_pdf(str(pdf_path), "founder@example.com", "Runtime Truth")

    assert result["emailed"] is False
    assert "did not verify send acceptance" in result["error"]
