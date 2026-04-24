import importlib

from fastapi.testclient import TestClient

from app.main import app
from app.services.max.hermes_memory import get_hermes_memory_status, render_hermes_bridge_for_prompt
from app.services.max.hermes_phase2 import prepare_prefill_draft_from_message
from app.services.max.hermes_phase3 import get_phase3_status, read_browser_action_audit


client = TestClient(app)
system_prompt_module = importlib.import_module("app.services.max.system_prompt")


class _FakeResponse:
    def __init__(self, url: str, text: str, status_code: int = 200):
        self.url = url
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_max_chat_surfaces_planned_browser_action_and_requires_approval(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    system_prompt_module._prompt_cache.update({"prompt": None, "expires": 0})

    plan_res = client.post(
        "/api/v1/max/chat",
        json={
            "message": "plan Hermes browser action for LIFE magazine lookup assistance 1969-07-25 Apollo 11",
            "channel": "web",
        },
    )
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["model_used"] == "hermes-browser-plan"
    assert plan_data["metadata"]["skill_used"] == "hermes_browser_plan"
    action = plan_data["tool_results"][0]["result"]
    action_id = action["id"]
    assert action["workflow_key"] == "life_magazine_lookup_assist"
    assert action["state"] == "planned"
    assert action["browser_actions_enabled"] is False
    assert "Founder approval is required before execution." in plan_data["response"]

    blocked_res = client.post(
        "/api/v1/max/chat",
        json={"message": f"execute hermes browser action {action_id}", "channel": "web"},
    )
    assert blocked_res.status_code == 200
    blocked_data = blocked_res.json()
    assert blocked_data["model_used"] == "hermes-browser-execute"
    assert "blocked until explicit founder approval" in blocked_data["response"].lower()
    assert blocked_data["tool_results"][0]["result"]["blocked"] is True

    approval_res = client.post(
        "/api/v1/max/chat",
        json={"message": f"approve hermes browser action {action_id}", "channel": "web"},
    )
    assert approval_res.status_code == 200
    approval_data = approval_res.json()
    assert approval_data["model_used"] == "hermes-browser-approval"
    assert approval_data["tool_results"][0]["result"]["state"] == "approved"
    assert approval_data["tool_results"][0]["result"]["browser_actions_enabled"] is True

    def fake_get(url, timeout=15.0, follow_redirects=True, headers=None):
        html = """
        <html>
          <head>
            <title>LIFE Apollo 11 Lookup</title>
            <meta name="description" content="LIFE magazine Apollo 11 reference page" />
          </head>
          <body>
            <h1>Apollo 11</h1>
            <h2>LIFE magazine results</h2>
            <form action="/lookup" method="post">
              <input name="query" type="text" required />
              <input name="issue_date" type="date" />
            </form>
          </body>
        </html>
        """
        return _FakeResponse(url, html, 200)

    hermes_phase3 = importlib.import_module("app.services.max.hermes_phase3")
    monkeypatch.setattr(hermes_phase3.httpx, "get", fake_get)

    execute_res = client.post(
        "/api/v1/max/chat",
        json={"message": f"execute hermes browser action {action_id}", "channel": "web"},
    )
    assert execute_res.status_code == 200
    execute_data = execute_res.json()
    assert execute_data["model_used"] == "hermes-browser-execute"
    assert execute_data["tool_results"][0]["result"]["executed"] is True
    assert execute_data["tool_results"][0]["result"]["record"]["state"] == "completed"
    assert "No form submission or messaging was performed." in execute_data["response"]

    logs_res = client.post(
        "/api/v1/max/chat",
        json={"message": "show hermes browser logs", "channel": "web"},
    )
    assert logs_res.status_code == 200
    logs_data = logs_res.json()
    assert logs_data["model_used"] == "hermes-browser-logs"
    assert "plan_created" in logs_data["response"]
    assert "approval_granted" in logs_data["response"]
    assert "execution_completed" in logs_data["response"]

    audit = read_browser_action_audit(limit=10)
    events = [item["event"] for item in audit]
    assert "execution_blocked_missing_approval" in events
    assert "execution_completed" in events


def test_phase3_form_navigation_can_stage_phase2_fields(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    system_prompt_module._prompt_cache.update({"prompt": None, "expires": 0})

    draft = prepare_prefill_draft_from_message(
        "prepare VendorOps vendor entry draft for ShipStation category shipping purpose labels https://shipstation.com renewal 2026-05-01 monthly $29 starter",
        channel="web",
    )
    assert draft["workflow_key"] == "vendorops_vendor_entry"

    plan_res = client.post(
        "/api/v1/max/chat",
        json={
            "message": "plan Hermes browser action for vendorops form navigation prep https://vendor.example/form",
            "channel": "web",
        },
    )
    assert plan_res.status_code == 200
    data = plan_res.json()
    result = data["tool_results"][0]["result"]
    assert result["workflow_key"] == "repetitive_form_navigation_prep"
    assert result["phase2_draft_ref"] == draft["id"]
    assert result["staged_fields"]["vendor_name"] == "ShipStation"
    assert result["submission_allowed"] is False


def test_phase3_status_keeps_truth_hierarchy_and_channels_truthful(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    status = get_phase3_status()
    memory_status = get_hermes_memory_status()
    prompt = render_hermes_bridge_for_prompt(compact=False)

    assert status["browser_assist_mode"] == "gated"
    assert status["browser_actions_enabled"] == "gated_by_explicit_founder_approval"
    assert status["autonomous_submission_allowed"] is False
    assert status["autonomous_messaging_allowed"] is False
    assert status["production_services_in_docker"] is False
    assert status["extra_channels"]["whatsapp"]["enabled"] is False
    assert status["extra_channels"]["discord"]["enabled"] is False
    assert status["extra_channels"]["whatsapp"]["status"] in {"disabled", "partial_disabled_gateway"}
    assert memory_status["truth_hierarchy"] == ["runtime", "registry", "repo_truth", "hermes_memory", "skills"]
    assert memory_status["phase3"]["browser_assist_mode"] == "gated"
    assert "Phase 3 Browser Assist (gated only)" in prompt
