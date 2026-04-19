"""MAX operating truth registry.

This is intentionally small and prompt-safe: the JSON file is the structured
source, and this module emits short summaries for MAX prompts.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REGISTRY_PATH = Path(__file__).with_name("operating_registry.json")


@lru_cache(maxsize=1)
def load_operating_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def clear_operating_registry_cache() -> None:
    load_operating_registry.cache_clear()


def _find_by_key(items: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("key") == key), None)


def get_surface_truth(surface_key: str) -> dict[str, Any] | None:
    return _find_by_key(load_operating_registry().get("surfaces", []), surface_key)


def get_product_truth(product_key: str) -> dict[str, Any] | None:
    return _find_by_key(load_operating_registry().get("ecosystem_products", []), product_key)


def get_skill_truth(skill_key: str) -> dict[str, Any] | None:
    return _find_by_key(load_operating_registry().get("skills", []), skill_key)


def _normalize_prompt_channel(channel: str | None) -> str:
    ch = (channel or "web").lower()
    if ch in {"web", "web_cc", "dashboard", "command_center", "mobile_browser"}:
        return "web_chat"
    if ch == "telegram":
        return "telegram"
    if ch == "email":
        return "email"
    return ch


def generate_operating_context(channel: str = "web", compact: bool = False) -> str:
    """Generate a bounded MAX operating-truth section for prompts."""
    registry = load_operating_registry()
    prompt_channel = _normalize_prompt_channel(channel)

    surfaces = registry.get("surfaces", [])
    products = registry.get("ecosystem_products", [])
    skills = registry.get("skills", [])
    policy = registry.get("delegation_policy", {})

    surface_lines = []
    for key in ["founder_web", "web_browser_other_device", "telegram", "email", "phone"]:
        surface = _find_by_key(surfaces, key)
        if not surface:
            continue
        surface_lines.append(
            f"- {surface['name']}: {surface['status']} | channel={surface.get('canonical_channel') or 'none'} | "
            f"{surface['continuity_real_today']}"
        )
        if key in {"web_browser_other_device", "phone"}:
            surface_lines.append(f"  Limitation: {'; '.join(surface.get('limitations', [])[:2])}")

    product_lines = []
    for key in ["relistapp", "finance", "openclaw", "email", "workroom_creations", "supportforge"]:
        product = _find_by_key(products, key)
        if not product:
            continue
        product_lines.append(
            f"- {key}: {product['status']} | MAX query={product['max_can_query']} act={product['max_can_act']} | "
            f"limits: {'; '.join(product.get('limitations', [])[:2])}"
        )

    if compact:
        return "\n".join([
            "## MAX Operating Truth (registry)",
            f"- Current prompt channel normalizes to: {prompt_channel}.",
            "- Web/Founder and mobile browser are Web MAX (`web_chat`); Telegram is `telegram`; Email is partial; Phone MAX is not implemented.",
            "- Compact continuity uses recent unified_messages from other channels, but the History UI is still split by surface.",
            "- Before route/service/payment/email/OpenClaw claims, run a runtime truth check or say it is repo-truth only.",
            "- Never claim Phone MAX exists, email is fully unified, or a partial/stubbed product is live.",
        ])

    tier1 = [s["key"] for s in skills if s.get("tier") == 1]
    tier2 = [s["key"] for s in skills if s.get("tier") == 2]
    tier3 = [s["key"] for s in skills if s.get("tier") == 3]

    return "\n".join([
        "## MAX Operating Truth Registry",
        f"Registry version: {registry.get('schema_version')} ({registry.get('updated_at')}). Current prompt channel: {prompt_channel}.",
        "",
        "### Surface Truth",
        *surface_lines,
        "",
        "### Product Truth Hotlist",
        *product_lines,
        "",
        "### Skill / Policy Inventory",
        f"- Tier 1 implemented/policy skills: {', '.join(tier1)}",
        f"- Tier 2 ecosystem trust skills: {', '.join(tier2)}",
        f"- Tier 3 scaffolded/planned only: {', '.join(tier3)}",
        "- Existing Codex skills are inventoried for policy only. Do not claim MAX can invoke Skill Creator, Skill Installer, OpenAI Docs, Image Gen, or Plugin Creator directly.",
        "",
        "### Delegation Rules",
        f"- Runtime truth check required for: {', '.join(policy.get('runtime_truth_check_required', []))}",
        f"- Regression review required for: {', '.join(policy.get('regression_review_required', []))}",
        f"- Never claim: {', '.join(policy.get('never_claim', []))}",
    ])
