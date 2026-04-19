import json

import app.services.max.operating_registry as operating_registry
from app.services.max.operating_registry import (
    generate_operating_context,
    get_registry_load_info,
    get_product_truth,
    get_surface_truth,
    get_skill_truth,
    load_operating_registry,
)
from app.services.max.system_prompt import get_compact_system_prompt, get_system_prompt


def test_operating_registry_loads_required_truth():
    registry = load_operating_registry()

    assert registry["schema_version"] == 1
    assert registry["registry_version"] == "operating-registry-v2"
    assert get_surface_truth("founder_web")["canonical_channel"] == "web_chat"
    assert get_surface_truth("web_browser_other_device")["canonical_channel"] == "web_chat"
    assert get_surface_truth("telegram")["status"] == "active"
    assert get_surface_truth("email")["status"] == "partial"
    assert get_surface_truth("phone")["status"] == "dead"
    assert get_product_truth("relistapp")["status"] == "active_partial"
    assert get_product_truth("finance")["status"] == "active_partial"
    assert get_skill_truth("empire-capability-registry")["status"] == "implemented"
    assert get_skill_truth("external-memory-mem0-zep")["status"] == "planned"


def test_operating_context_is_prompt_safe_and_truthful():
    compact = generate_operating_context(channel="mobile_browser", compact=True)
    full = generate_operating_context(channel="web_cc", compact=False)

    assert "Current prompt channel normalizes to: web_chat" in compact
    assert "Phone MAX is not implemented" in compact
    assert "Email is partial" in compact
    assert "Tier 1 implemented/policy skills" in full
    assert "empire-runtime-truth-check" in full
    assert "Do not claim MAX can invoke Skill Creator" in full


def test_system_prompts_include_operating_truth_without_phone_overclaim():
    compact_prompt = get_compact_system_prompt(channel="mobile_browser")
    full_prompt = get_system_prompt()

    assert "mobile browser access is Web MAX" in compact_prompt
    assert "Phone MAX is not implemented" in compact_prompt
    assert "MAX Operating Truth Registry" in full_prompt
    assert "Email MAX: partial" in full_prompt
    assert "a dedicated Phone MAX does not exist" in full_prompt
    assert "All channels share the same MAX brain and memory" not in full_prompt


def test_operating_registry_hot_reloads_and_keeps_last_known_good(monkeypatch, tmp_path):
    registry_path = tmp_path / "operating_registry.json"
    good = {
        "schema_version": 99,
        "registry_version": "test-registry-v99",
        "updated_at": "2026-04-19",
        "surfaces": [],
        "ecosystem_products": [],
        "skills": [],
        "delegation_policy": {},
    }
    registry_path.write_text(json.dumps(good), encoding="utf-8")

    monkeypatch.setattr(operating_registry, "REGISTRY_PATH", registry_path)
    operating_registry.clear_operating_registry_cache()

    loaded = operating_registry.load_operating_registry()
    assert loaded["registry_version"] == "test-registry-v99"
    assert operating_registry.get_registry_load_info()["last_error"] is None

    updated = {**good, "registry_version": "test-registry-v100"}
    registry_path.write_text(json.dumps(updated), encoding="utf-8")
    operating_registry._registry_state["last_checked"] = 0
    reloaded = operating_registry.load_operating_registry()
    assert reloaded["registry_version"] == "test-registry-v100"

    registry_path.write_text("{not valid json", encoding="utf-8")
    operating_registry._registry_state["last_checked"] = 0
    fallback = operating_registry.load_operating_registry()

    assert fallback["registry_version"] == "test-registry-v100"
    assert operating_registry.get_registry_load_info()["last_error"]

    registry_path.unlink()
    operating_registry._registry_state["last_checked"] = 0
    missing_fallback = operating_registry.load_operating_registry()
    assert missing_fallback["registry_version"] == "test-registry-v100"

    registry_path.write_text(json.dumps({"schema_version": 100}), encoding="utf-8")
    operating_registry._registry_state["last_checked"] = 0
    schema_fallback = operating_registry.load_operating_registry()
    assert schema_fallback["registry_version"] == "test-registry-v100"
    operating_registry.clear_operating_registry_cache()
