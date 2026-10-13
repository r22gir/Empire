"""Canonical AI desk registry — single source of truth for desk count and IDs.

The live AIDeskManager.initialize() list MUST match REGISTERED_DESKS.
UI labels, MAX prompts, and /desks/registry all read from here.
Do not hardcode 12 or 18 in founder-facing surfaces.
"""
from __future__ import annotations

from typing import Iterable

# Order matches AIDeskManager.initialize() registration order.
REGISTERED_DESKS: tuple[dict[str, str], ...] = (
    {"id": "forge", "name": "ForgeDesk", "agent": "Kai"},
    {"id": "market", "name": "MarketDesk", "agent": "Sofia"},
    {"id": "marketing", "name": "MarketingDesk", "agent": "Nova"},
    {"id": "support", "name": "SupportDesk", "agent": "Luna"},
    {"id": "sales", "name": "SalesDesk", "agent": "Aria"},
    {"id": "finance", "name": "FinanceDesk", "agent": "Sage"},
    {"id": "clients", "name": "ClientsDesk", "agent": "Elena"},
    {"id": "contractors", "name": "ContractorsDesk", "agent": "Marcus"},
    {"id": "it", "name": "ITDesk", "agent": "Orion"},
    {"id": "website", "name": "WebsiteDesk", "agent": "Zara"},
    {"id": "legal", "name": "LegalDesk", "agent": "Raven"},
    {"id": "lab", "name": "LabDesk", "agent": "Phoenix"},
    {"id": "innovation", "name": "InnovationDesk", "agent": "Spark"},
    {"id": "intake", "name": "IntakeDesk", "agent": "Zara"},
    {"id": "analytics", "name": "AnalyticsDesk", "agent": "Raven"},
    {"id": "quality", "name": "QualityDesk", "agent": "Phoenix"},
    {"id": "codeforge", "name": "CodeForgeDesk", "agent": "Atlas"},
)

CANONICAL_DESK_COUNT = len(REGISTERED_DESKS)  # 17


def registered_desk_ids() -> list[str]:
    return [d["id"] for d in REGISTERED_DESKS]


def registry_payload() -> dict:
    return {
        "source": "desk_registry",
        "count": CANONICAL_DESK_COUNT,
        "desks": [dict(d) for d in REGISTERED_DESKS],
    }


def assert_matches_live(live_ids: Iterable[str]) -> None:
    """Raise if the running manager drifted from the registry."""
    live = list(live_ids)
    expected = registered_desk_ids()
    if len(live) != CANONICAL_DESK_COUNT or set(live) != set(expected):
        raise RuntimeError(
            f"Desk registry mismatch: live={live} expected={expected} "
            f"(canonical_count={CANONICAL_DESK_COUNT})"
        )
