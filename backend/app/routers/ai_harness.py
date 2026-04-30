"""
AI Harness Profiles Router

Read-only profile registry + profile selection endpoints.
Does NOT call external AI providers — routing/selection layer only.

GET /api/v1/ai-harness/profiles
GET /api/v1/ai-harness/profiles/{profile_id}
GET /api/v1/ai-harness/recommend?task_type=...
POST /api/v1/ai-harness/select
GET /api/v1/ai-harness/status
GET /api/v1/ai-harness/telemetry
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.ai_harness_profiles import (
    registry,
    ALL_TASK_TYPES,
    log_routing_decision,
    get_recent_routing_decisions,
    RoutingExplanation,
)

router = APIRouter(prefix="/api/v1/ai-harness", tags=["ai-harness"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class SelectRequest(BaseModel):
    task_type: str
    requested_provider: Optional[str] = None
    requested_model: Optional[str] = None
    emergency_override: bool = False
    budget_mode: bool = False
    provider_availability: Optional[dict] = None


class ProfileResponse(BaseModel):
    id: str
    display_name: str
    provider: str
    model: str
    task_types: list[str]
    description: str
    default_for_tasks: list[str]
    priority: int
    enabled: bool
    local_only: bool
    cloud_required: bool
    emergency_only: bool
    budget_mode: bool
    recommended_for: list[str]
    not_recommended_for: list[str]
    prompt_style: str
    tool_policy: str
    file_access_policy: str
    approval_policy: str
    testing_policy: str
    retry_policy: str
    timeout_seconds: int
    max_context_strategy: str
    cost_tier: str
    speed_tier: str
    quality_tier: str
    reliability_tier: str
    fallback_profile_ids: list[str]
    telemetry_enabled: bool
    ui_badge: str
    risk_level: str
    notes: str


class RoutingExplanationResponse(BaseModel):
    selected_profile_id: str
    selected_provider: str
    selected_model: str
    task_type: str
    reason: str
    fallback_used: bool
    fallback_reason: str
    emergency_override: bool
    policy_summary: str


class SelectResponse(BaseModel):
    selected_profile: Optional[ProfileResponse]
    routing: RoutingExplanationResponse
    policy_summary: str


class StatusResponse(BaseModel):
    total_profiles: int
    enabled_profiles: int
    default_profiles_by_task: dict
    emergency_capable: bool
    fallback_chains: dict
    registry_only_warning: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _profile_to_response(profile) -> ProfileResponse:
    d = profile.to_dict()
    return ProfileResponse(**d)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles(enabled_only: bool = True):
    """
    List all AI harness profiles.

    Query params:
    - enabled_only: bool = True (only show enabled profiles)
    """
    profiles = registry.list_profiles(enabled_only=enabled_only)
    return [_profile_to_response(p) for p in profiles]


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    """Get a single profile by ID."""
    profile = registry.get_profile(profile_id)
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    return _profile_to_response(profile)


@router.get("/recommend", response_model=list[ProfileResponse])
async def recommend_profiles(
    task_type: str = Query(..., description="Task type to get recommendations for"),
    requested_provider: Optional[str] = Query(None, description="Filter by provider"),
    budget_mode: bool = Query(False, description="Prefer budget/local profiles"),
):
    """
    Get recommended profiles for a task type.

    - task_type: one of the valid task types
    - requested_provider: optional provider filter
    - budget_mode: prefer local/budget profiles
    """
    if task_type not in ALL_TASK_TYPES:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task_type '{task_type}'. Valid: {ALL_TASK_TYPES}",
        )

    profiles = registry.recommend_profiles(
        task_type=task_type,
        requested_provider=requested_provider,
        budget_mode=budget_mode,
    )
    return [_profile_to_response(p) for p in profiles]


@router.post("/select", response_model=SelectResponse)
async def select_profile(req: SelectRequest):
    """
    Select the best profile for a task.

    Returns the selected profile, routing explanation, and policy summary.

    Request body:
    - task_type: str (required)
    - requested_provider: str | None
    - requested_model: str | None
    - emergency_override: bool = False
    - budget_mode: bool = False
    - provider_availability: dict | None
    """
    if req.task_type not in ALL_TASK_TYPES:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task_type '{req.task_type}'. Valid: {ALL_TASK_TYPES}",
        )

    profile, routing = registry.select_profile(
        task_type=req.task_type,
        requested_provider=req.requested_provider,
        requested_model=req.requested_model,
        emergency_override=req.emergency_override,
        budget_mode=req.budget_mode,
        provider_availability=req.provider_availability,
    )

    policy_summary = registry.build_policy_summary(routing.selected_profile_id) if routing.selected_profile_id else ""

    return SelectResponse(
        selected_profile=_profile_to_response(profile) if profile else None,
        routing=RoutingExplanationResponse(
            selected_profile_id=routing.selected_profile_id,
            selected_provider=routing.selected_provider,
            selected_model=routing.selected_model,
            task_type=routing.task_type,
            reason=routing.reason,
            fallback_used=routing.fallback_used,
            fallback_reason=routing.fallback_reason,
            emergency_override=routing.emergency_override,
            policy_summary=policy_summary,
        ),
        policy_summary=policy_summary,
    )


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get harness profile registry status.

    Returns:
    - total/enabled profile counts
    - default profiles by task type
    - emergency capability status
    - fallback chains
    - registry-only warning (this is not yet wired into live MAX routing)
    """
    all_profiles = registry.list_profiles(enabled_only=False)
    enabled_profiles = registry.list_profiles(enabled_only=True)

    # Build default-by-task map
    default_by_task = {}
    for task in ALL_TASK_TYPES:
        default = registry.get_default_for_task(task)
        if default:
            default_by_task[task] = default.id

    # Fallback chains
    fallback_chains = {}
    for p in enabled_profiles:
        if p.fallback_profile_ids:
            fallback_chains[p.id] = p.fallback_profile_ids

    # Emergency capable
    emergency_profile = registry.get_profile("grok_emergency_repair_profile")
    emergency_capable = emergency_profile is not None and emergency_profile.enabled

    return StatusResponse(
        total_profiles=len(all_profiles),
        enabled_profiles=len(enabled_profiles),
        default_profiles_by_task=default_by_task,
        emergency_capable=emergency_capable,
        fallback_chains=fallback_chains,
        registry_only_warning=(
            "Profile registry is available. Full live MAX provider routing integration is Phase 2. "
            "Currently ai_router.py does NOT call ai_harness_profiles.py. "
            "This endpoint is for audit/selection only."
        ),
    )


@router.get("/telemetry")
async def get_telemetry(limit: int = Query(20, ge=1, le=100)):
    """
    Get recent routing decisions from the telemetry log.

    Returns sanitized entries — no API keys, no full prompts, no uploaded content.
    """
    entries = get_recent_routing_decisions(limit=limit)
    return {
        "entries": entries,
        "count": len(entries),
        "log_path": str(log_routing_decision.__doc__),
        "note": "API keys, secrets, and full prompts are never logged",
    }
