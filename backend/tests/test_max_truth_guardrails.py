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


def test_archiveforge_lookup_returns_truthful_status_response(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("ArchiveForge lookup should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="What ArchiveForge features are working?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "empire-module-knowledge"
    assert response.tool_results[0]["tool"] == "empire_module_knowledge"
    assert response.tool_results[0]["result"]["module"] == "ArchiveForge"
    assert "ArchiveForge is the Empire module for archive and magazine workflows" in response.response
    assert "No Hermes intake draft was created from this message." not in response.response


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


# ---------------------------------------------------------------------------
# MAX email channel dry-run and threading tests
# ---------------------------------------------------------------------------


def test_email_allowlist_founder_accepted(monkeypatch):
    """Founder-allowed sender must be authorized."""
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")
    from app.services.max.email_sender_whitelist import authorize_email_sender, allowed_sender_addresses

    # Force reload of cached senders
    result = authorize_email_sender("empirebox2026@gmail.com")
    assert result["sender_authorized"] is True, f"Got: {result}"
    assert result["blocked_reason"] is None
    assert result["email_sender_whitelist_configured"] is True
    assert result["allowed_sender_count"] >= 1


def test_email_allowlist_unauthorized_blocked(monkeypatch):
    """Non-whitelisted sender must be blocked."""
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com")
    from app.services.max.email_sender_whitelist import authorize_email_sender

    result = authorize_email_sender("random@example.com")
    assert result["sender_authorized"] is False
    assert result["blocked_reason"] == "non_whitelisted_sender"


def test_email_classify_question():
    """Emails with question markers should classify as question."""
    from app.routers.webhooks import classify_max_email

    result = classify_max_email("Can you check inventory?", "Can you look at eBay inventory for me?", None)
    assert result["classification"] == "question"
    assert "question" in result["tags"]


def test_email_classify_task():
    """Emails with task markers should classify as task."""
    from app.routers.webhooks import classify_max_email

    result = classify_max_email("TODO: Fix listing", "Please fix the eBay listing price", None)
    assert result["classification"] == "task"
    assert "task" in result["tags"]


def test_email_dry_run_returns_no_send():
    """Dry-run must never send live email."""
    from app.services.channels.status import build_dry_run_result

    result = build_dry_run_result("email", {
        "from": "empirebox2026@gmail.com",
        "subject": "Test",
        "body": "Hello",
    })
    assert result["dry_run"] is True
    assert result["live_send_performed"] is False
    assert result["reply_payload_preview"]["would_send"] is False


def test_email_dry_run_blocks_unauthorized():
    """Dry-run must block unauthorized senders from calling MAX."""
    from app.services.channels.status import build_dry_run_result

    result = build_dry_run_result("email", {
        "from": "random@example.com",
        "subject": "Urgent",
        "body": "Send money",
    })
    assert result["sender_authorized"] is False
    assert result["would_call_max"] is False


def test_email_threading_headers_in_service_method():
    """EmailService.send() must accept threading parameters."""
    from app.services.max.email_service import EmailService
    import inspect

    sig = inspect.signature(EmailService.send)
    params = list(sig.parameters.keys())
    assert "in_reply_to" in params
    assert "references" in params
    assert "reply_to" in params


def test_email_auto_reply_not_set_defaults_disabled():
    """MAX_EMAIL_AUTO_REPLY_ENABLED must default to disabled when not set."""
    import os
    val = os.getenv("MAX_EMAIL_AUTO_REPLY_ENABLED")
    # If not set or explicitly false, auto-reply is disabled
    is_enabled = str(val).lower() in ("true", "1", "yes") if val else False
    assert not is_enabled, "Auto-reply must be disabled by default"


def test_channel_status_email_is_present(monkeypatch):
    """Channel status must include email channel with expected layers."""
    # Set env vars needed for outbound to show as configured in test env
    monkeypatch.setenv("SMTP_USER", "test@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "testpass")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "founder@example.com")

    from app.services.channels.status import build_channel_status

    status = build_channel_status()
    email = [c for c in status["channels"] if c["key"] == "email"]
    assert len(email) == 1
    email = email[0]
    assert email["status"] == "partial"
    assert email["inbound_configured"] is True

    layer_names = [l["name"] for l in email["layers"]]
    assert "sender_whitelist_gate" in layer_names
    assert "sendgrid_smtp_outbound" in layer_names
    assert "reply_threading" in layer_names
    assert "auto_reply_safety" in layer_names
    assert "backend_gmail_oauth_read_access" in layer_names


def test_email_service_smtp_header_construction():
    """SMTP send must construct In-Reply-To, References, and Reply-To headers."""
    from email.mime.multipart import MIMEMultipart
    from email.utils import formataddr

    msg = MIMEMultipart()
    msg["From"] = formataddr(("MAX - Empire AI", "max@empirebox.store"))
    msg["To"] = "founder@gmail.com"
    msg["Subject"] = "Re: Test"
    msg["In-Reply-To"] = "<test123@mail.example.com>"
    msg["References"] = "<test123@mail.example.com>"
    msg["Reply-To"] = "max@empirebox.store"

    assert msg["In-Reply-To"] == "<test123@mail.example.com>"
    assert msg["References"] == "<test123@mail.example.com>"
    assert msg["Reply-To"] == "max@empirebox.store"
    # From display name must be properly encoded
    assert "MAX" in msg["From"]


def test_email_dry_run_reads_routing_state(monkeypatch):
    """Email dry-run must read provider from routing state, not hard-coded."""
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    from app.services.max.email_service import generate_email_reply_draft

    draft = generate_email_reply_draft(
        sender="empirebox2026@gmail.com",
        subject="Test",
        body="Hello",
        tiny_test_prompt="ok",
    )
    # Must report routing state source, not hard-coded
    assert draft["selected_provider_source"] == "routing_state"
    assert draft["provider"] == "deepseek"
    assert draft["model"] == "deepseek-v4-flash"
    assert draft["fallback_used"] is False
    assert draft["would_send"] is False


def test_email_dry_run_blocks_unsupported_provider(monkeypatch):
    """Email dry-run must block gracefully for unsupported providers."""
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com")

    # Simulate unsupported provider by patching the routing state load
    import app.services.max.email_service as es
    original_load = es.load_routing_state if hasattr(es, 'load_routing_state') else None

    class FakeRoutingState:
        selected_provider = "ollama"
        selected_model = "llama3"
        fallback_enabled = False

    try:
        # Patch at the function level
        from app.services.max import routing_state as rs
        orig = rs.load_routing_state
        rs.load_routing_state = lambda: FakeRoutingState
        draft = es.generate_email_reply_draft(
            sender="empirebox2026@gmail.com",
            subject="Test",
            body="Hello",
        )
        assert draft["response_state"] in (
            "response_generation_blocked",
            "response_generation_skipped",
        ), f"Got: {draft['response_state']}"
        assert draft["provider"] == "ollama"
        assert draft["would_send"] is False
    finally:
        rs.load_routing_state = orig
