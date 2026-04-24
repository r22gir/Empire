import importlib

from fastapi.testclient import TestClient

from app.main import app
from app.services.max.hermes_memory import get_hermes_memory_status, render_hermes_bridge_for_prompt
from app.services.max.hermes_phase2 import (
    get_phase2_status,
    ingest_scheduled_result,
    list_scheduled_results,
    prepare_prefill_draft_from_message,
)


client = TestClient(app)
system_prompt_module = importlib.import_module("app.services.max.system_prompt")


def test_phase2_prefill_supports_life_and_vendorops(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    life = prepare_prefill_draft_from_message(
        "prepare LIFE magazine intake draft for 1969-07-25 Apollo 11 from Box 12 condition VG tier A comp $150-$600",
        channel="web",
    )
    vendor = prepare_prefill_draft_from_message(
        "prepare VendorOps vendor entry draft for ShipStation category shipping purpose labels https://shipstation.com renewal 2026-05-01 monthly $29 starter",
        channel="web",
    )

    assert life["workflow_key"] == "life_magazine_intake"
    assert life["fields"]["publication_title"] == "LIFE"
    assert life["fields"]["issue_date"] == "1969-07-25"
    assert life["fields"]["cover_subject"] == "Apollo 11"
    assert life["fields"]["source_box"] == "Box 12"
    assert life["fields"]["condition"] == "VG"
    assert life["confirmation_required"] is True
    assert life["submission_allowed"] is False
    assert life["browser_actions_enabled"] is False

    assert vendor["workflow_key"] == "vendorops_vendor_entry"
    assert vendor["fields"]["vendor_name"] == "ShipStation"
    assert vendor["fields"]["category"] == "shipping"
    assert vendor["fields"]["vendor_url"] == "https://shipstation.com"
    assert vendor["fields"]["renewal_date"] == "2026-05-01"
    assert vendor["fields"]["monthly_cost_usd"] == 29.0
    assert vendor["confirmation_required"] is True
    assert vendor["submission_allowed"] is False


def test_phase2_scheduled_results_are_stored_beneath_memory_bridge(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    ingest_scheduled_result(
        result_type="daily_summary",
        title="Daily source roundup",
        summary="3 source products flagged for review.",
        payload={"flagged_count": 3},
        schedule="daily 8am",
    )
    ingest_scheduled_result(
        result_type="renewal_reminder",
        title="VendorOps renewals due",
        summary="Adobe and ShipStation renew within 7 days.",
        payload={"vendors": ["Adobe", "ShipStation"]},
        schedule="monday 9am",
    )

    status = get_phase2_status()
    bridge_status = get_hermes_memory_status()
    prompt = render_hermes_bridge_for_prompt(compact=False)

    assert status["scheduled_result_count"] == 2
    assert status["supported_workflows"][0]["key"] == "life_magazine_intake"
    assert bridge_status["truth_hierarchy"][:2] == ["runtime", "registry"]
    assert bridge_status["phase2"]["scheduled_result_count"] == 2
    assert "Phase 2 Assist" in prompt
    assert "Browser actions: disabled. Form submission: disabled." in prompt


def test_max_chat_surfaces_hermes_drafts_and_scheduled_results(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    system_prompt_module._prompt_cache.update({"prompt": None, "expires": 0})

    life_res = client.post(
        "/api/v1/max/chat",
        json={
            "message": "prepare LIFE magazine intake draft for 1969-07-25 Apollo 11 from Box 12 condition VG tier A",
            "channel": "web",
        },
    )
    assert life_res.status_code == 200
    life_data = life_res.json()
    assert life_data["model_used"] == "hermes-form-prep"
    assert life_data["metadata"]["skill_used"] == "hermes_form_prep"
    assert life_data["tool_results"][0]["result"]["workflow_key"] == "life_magazine_intake"
    assert "Founder confirmation is required" in life_data["response"]
    assert "Submission: disabled" in life_data["response"]

    vendor_res = client.post(
        "/api/v1/max/chat",
        json={
            "message": "prepare VendorOps vendor entry draft for ShipStation category shipping https://shipstation.com monthly $29 renewal 2026-05-01",
            "channel": "web",
        },
    )
    assert vendor_res.status_code == 200
    vendor_data = vendor_res.json()
    assert vendor_data["model_used"] == "hermes-form-prep"
    assert vendor_data["tool_results"][0]["result"]["workflow_key"] == "vendorops_vendor_entry"
    assert "VendorOps vendor entry" in vendor_data["response"]

    ingest_scheduled_result(
        result_type="weekly_summary",
        title="Weekly workflow summary",
        summary="2 renewal reminders and 1 repetitive task prep are ready.",
        payload={"renewals": 2, "task_preps": 1},
        schedule="weekly monday 9am",
    )

    scheduled_res = client.post(
        "/api/v1/max/chat",
        json={"message": "show Hermes scheduled results", "channel": "web"},
    )
    assert scheduled_res.status_code == 200
    scheduled_data = scheduled_res.json()
    assert scheduled_data["model_used"] == "hermes-scheduled-intake"
    assert scheduled_data["metadata"]["skill_used"] == "hermes_scheduled_intake"
    assert "Weekly summary" in scheduled_data["response"]
    assert "Nothing was submitted or executed" in scheduled_data["response"]

    stored_results = list_scheduled_results(limit=5)
    assert stored_results[0]["review_state"] == "presented_by_max"
