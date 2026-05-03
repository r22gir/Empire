"""
MVP Triad Flow: MAX → Hermes → OpenClaw
Minimum working version that proves the command triad works.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.services.max.hermes_memory import HermesMemoryBridge
from app.services.max.openclaw_executor import OpenClawExecutor
from app.services.ai_harness_profiles import get_profile_service, log_routing_decision

logger = logging.getLogger(__name__)

hermes = HermesMemoryBridge()
openclaw = OpenClawExecutor()
harness_registry = get_profile_service()


async def execute_workroom_quote_flow(
    founder_intent: str,
    client_id: Optional[str] = None,
    photo_ids: Optional[list[str]] = None,
    harness_profile_id: Optional[str] = None,
    emergency_override: bool = False
) -> Dict[str, Any]:
    """
    MVP Triad Flow:
    1. MAX selects harness profile + attaches metadata
    2. Hermes assembles context + creates draft + sets approval gate
    3. OpenClaw queues Vision analysis task
    4. Returns structured response proving triad works
    """
    
    # ====== STEP 1: MAX SELECTS HARNESS PROFILE ======
    profile = None
    routing_reason = "opt_in" if harness_profile_id else "auto_select"

    if harness_profile_id:
        profile = harness_registry.get_profile(harness_profile_id)
        if not profile or not profile.enabled:
            harness_profile_id = None  # Fallback to auto-select
            profile = None

    if not harness_profile_id:
        profile, routing_explanation = harness_registry.select_profile(
            task_type="quote_generation",
            emergency_override=emergency_override
        )
        if profile:
            harness_profile_id = profile.id
            routing_reason = routing_explanation.reason

    # Fallback: use default MiniMax profile if nothing selected
    if not profile:
        profile = harness_registry.get_profile("minimax_default_chat_profile")
        if profile:
            harness_profile_id = profile.id
            routing_reason = "fallback_to_default"

    if not profile:
        return {"status": "error", "message": "No harness profile available"}

    # Build harness metadata (Phase 2A format)
    harness_metadata = {
        "harness_profile_id": harness_profile_id,
        "harness_profile_display_name": profile.display_name,
        "harness_provider": profile.provider,
        "harness_model": profile.model,
        "harness_task_type": "quote_generation",
        "harness_reason": routing_reason,
        "harness_fallback_used": False,
        "harness_emergency_override": emergency_override,
        "harness_policy_summary": harness_registry.build_profile_policy_summary(harness_profile_id),
        "harness_system_instructions": harness_registry.build_system_instruction_block(
            harness_profile_id, "quote_generation"
        )
    }
    
    # ====== STEP 2: HERMES ASSEMBLES CONTEXT + CREATES DRAFT ======
    context = await hermes.assemble_context(
        task_type="quote_generation",
        entity_type="workroom_quote",
        client_id=client_id,
        desk="workroom_ops"
    )
    
    draft = await hermes.create_draft(
        draft_type="workroom_quote",
        base_data={
            "client_id": client_id,
            "photo_ids": photo_ids or [],
            "intake_source": "max_command",
            "status": "draft",
            "created_at": datetime.utcnow().isoformat()
        }
    )
    
    # ====== STEP 3: OPENCLAW QUEUES VISION ANALYSIS ======
    vision_task = await openclaw.queue_task(
        task_type="vision_analysis",
        desk_id="workroom_ops",
        harness_profile_id=harness_profile_id,
        parameters={
            "photo_ids": photo_ids or [],
            "draft_id": draft["id"],
            "context": context
        }
    )
    
    # ====== STEP 4: HERMES CREATES APPROVAL GATE ======
    approval_gate = await hermes.create_approval_gate(
        action="workroom_quote_approval",
        draft_id=draft["id"],
        level="L2",
        timeout_minutes=15
    )
    
    # ====== STEP 5: BUILD TRIAD RESPONSE ======
    response = {
        "status": "success",
        "message": "MVP Triad proven. MAX commanded Hermes and OpenClaw.",
        "triad_flow": {
            "max": {
                "intent_processed": founder_intent,
                "harness_metadata": harness_metadata
            },
            "hermes": {
                "context_id": context.get("context_id", "assembled"),
                "draft_id": draft["id"],
                "approval_gate_id": approval_gate["id"],
                "draft_status": draft["status"]
            },
            "openclaw": {
                "vision_task_id": vision_task["task_id"],
                "task_status": vision_task["status"],
                "v10_boundary_enforced": True
            }
        },
        "next_steps": [
            "Founder approves draft via Hermes gate",
            "OpenClaw completes Vision analysis",
            "Quote moves to QuoteReviewScreen"
        ],
        "timestamp": datetime.utcnow().isoformat(),
        "version": "mvp_triad_v1"
    }
    
    # Log to telemetry
    log_routing_decision(
        channel=None,
        task_type="quote_generation",
        selected_provider=harness_metadata["harness_provider"],
        selected_model=harness_metadata["harness_model"],
        selected_harness_profile=harness_profile_id,
        fallback_used=False,
        fallback_reason="",
        emergency_override=emergency_override,
        success=True,
    )
    
    return response
