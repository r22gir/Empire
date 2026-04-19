from app.services.max.operating_registry import (
    generate_operating_context,
    get_product_truth,
    get_surface_truth,
    get_skill_truth,
    load_operating_registry,
)
from app.services.max.system_prompt import get_compact_system_prompt, get_system_prompt


def test_operating_registry_loads_required_truth():
    registry = load_operating_registry()

    assert registry["schema_version"] == 1
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
