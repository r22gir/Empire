"""
Empire AI Harness Profiles — Profile Registry & Selection Service

Provides typed model/provider-specific routing profiles that define:
- prompt style and system instructions
- task type support and provider/model preference
- tool policy, file access policy, approval policy
- fallback chain, emergency behavior, telemetry settings
- cost/speed/quality/reliability tiers

This is a routing/profile selection layer ONLY.
It does NOT call external AI providers.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ai_harness_profiles")

# ── Task Type Constants ───────────────────────────────────────────────────────

TASK_TYPE_CODE_PATCH = "code_patch"
TASK_TYPE_REPO_AUDIT = "repo_audit"
TASK_TYPE_DOCUMENTATION = "documentation"
TASK_TYPE_UI_UX_REVIEW = "ui_ux_review"
TASK_TYPE_VISUAL_ANALYSIS = "visual_analysis"
TASK_TYPE_QUOTE_GENERATION = "quote_generation"
TASK_TYPE_PRICING_REVIEW = "pricing_review"
TASK_TYPE_IMAGE_TO_QUOTE = "image_to_quote"
TASK_TYPE_CUSTOMER_SUPPORT = "customer_support"
TASK_TYPE_FINANCE_ANALYSIS = "finance_analysis"
TASK_TYPE_MARKETING = "marketing"
TASK_TYPE_EMERGENCY_REPAIR = "emergency_repair"
TASK_TYPE_MODEL_BENCHMARK = "model_benchmark"
TASK_TYPE_MAX_CHAT = "max_chat"
TASK_TYPE_OPENCLAW_TASK = "openclaw_task"
TASK_TYPE_OPENCODE_TASK = "opencode_task"
TASK_TYPE_TRANSCRIPTION = "transcription"
TASK_TYPE_VOICE_TTS = "voice_tts"
TASK_TYPE_VISION = "vision"
TASK_TYPE_DRAWING_STUDIO = "drawing_studio"
TASK_TYPE_RECOVERY_ARCHIVE_ANALYSIS = "recovery_archive_analysis"
TASK_TYPE_SUMMARIZATION = "summarization"
TASK_TYPE_RESEARCH = "research"

ALL_TASK_TYPES = [
    TASK_TYPE_CODE_PATCH,
    TASK_TYPE_REPO_AUDIT,
    TASK_TYPE_DOCUMENTATION,
    TASK_TYPE_UI_UX_REVIEW,
    TASK_TYPE_VISUAL_ANALYSIS,
    TASK_TYPE_QUOTE_GENERATION,
    TASK_TYPE_PRICING_REVIEW,
    TASK_TYPE_IMAGE_TO_QUOTE,
    TASK_TYPE_CUSTOMER_SUPPORT,
    TASK_TYPE_FINANCE_ANALYSIS,
    TASK_TYPE_MARKETING,
    TASK_TYPE_EMERGENCY_REPAIR,
    TASK_TYPE_MODEL_BENCHMARK,
    TASK_TYPE_MAX_CHAT,
    TASK_TYPE_OPENCLAW_TASK,
    TASK_TYPE_OPENCODE_TASK,
    TASK_TYPE_TRANSCRIPTION,
    TASK_TYPE_VOICE_TTS,
    TASK_TYPE_VISION,
    TASK_TYPE_DRAWING_STUDIO,
    TASK_TYPE_RECOVERY_ARCHIVE_ANALYSIS,
    TASK_TYPE_SUMMARIZATION,
    TASK_TYPE_RESEARCH,
]

# ── Profile Dataclass ─────────────────────────────────────────────────────────

@dataclass
class AIHarnessProfile:
    id: str
    display_name: str
    provider: str          # e.g. "anthropic", "xai", "openai", "ollama", "openclaw"
    model: str            # e.g. "claude-sonnet-4-6", "grok-4-fast-non-reasoning"
    task_types: list[str]  # supported task types
    description: str
    default_for_tasks: list[str] = field(default_factory=list)  # tasks this is the DEFAULT for
    priority: int = 50    # 0=highest, 100=lowest; used when no explicit provider requested
    enabled: bool = True
    local_only: bool = False
    cloud_required: bool = False
    emergency_only: bool = False
    budget_mode: bool = False
    recommended_for: list[str] = field(default_factory=list)
    not_recommended_for: list[str] = field(default_factory=list)
    prompt_style: str = "concise"  # "concise" | "detailed" | "conversational" | "technical"
    system_instructions: str = ""
    tool_policy: str = "default"  # "default" | "strict" | "permissive" | "disabled"
    file_access_policy: str = "read_only"  # "read_only" | "read_write" | "none"
    approval_policy: str = "none"  # "none" | "founder" | "review"
    testing_policy: str = "none"  # "none" | "verify" | "required"
    retry_policy: str = "standard"  # "standard" | "aggressive" | "conservative"
    timeout_seconds: int = 120
    max_context_strategy: str = "standard"  # "standard" | "compact" | "expand"
    cost_tier: str = "medium"  # "free" | "low" | "medium" | "high"
    speed_tier: str = "medium"  # "fast" | "medium" | "slow"
    quality_tier: str = "medium"  # "standard" | "high" | "maximum"
    reliability_tier: str = "medium"  # "experimental" | "standard" | "high"
    fallback_profile_ids: list[str] = field(default_factory=list)
    benchmark_tags: list[str] = field(default_factory=list)
    telemetry_enabled: bool = True
    ui_badge: str = ""
    risk_level: str = "low"  # "safe" | "low" | "medium" | "high" | "critical"
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "provider": self.provider,
            "model": self.model,
            "task_types": self.task_types,
            "description": self.description,
            "default_for_tasks": self.default_for_tasks,
            "priority": self.priority,
            "enabled": self.enabled,
            "local_only": self.local_only,
            "cloud_required": self.cloud_required,
            "emergency_only": self.emergency_only,
            "budget_mode": self.budget_mode,
            "recommended_for": self.recommended_for,
            "not_recommended_for": self.not_recommended_for,
            "prompt_style": self.prompt_style,
            "system_instructions": self.system_instructions,
            "tool_policy": self.tool_policy,
            "file_access_policy": self.file_access_policy,
            "approval_policy": self.approval_policy,
            "testing_policy": self.testing_policy,
            "retry_policy": self.retry_policy,
            "timeout_seconds": self.timeout_seconds,
            "max_context_strategy": self.max_context_strategy,
            "cost_tier": self.cost_tier,
            "speed_tier": self.speed_tier,
            "quality_tier": self.quality_tier,
            "reliability_tier": self.reliability_tier,
            "fallback_profile_ids": self.fallback_profile_ids,
            "benchmark_tags": self.benchmark_tags,
            "telemetry_enabled": self.telemetry_enabled,
            "ui_badge": self.ui_badge,
            "risk_level": self.risk_level,
            "notes": self.notes,
        }


# ── Routing Explanation ─────────────────────────────────────────────────────────

@dataclass
class RoutingExplanation:
    selected_profile_id: str
    selected_provider: str
    selected_model: str
    task_type: str
    reason: str
    fallback_used: bool = False
    fallback_reason: str = ""
    emergency_override: bool = False
    policy_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "selected_profile_id": self.selected_profile_id,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "task_type": self.task_type,
            "reason": self.reason,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "emergency_override": self.emergency_override,
            "policy_summary": self.policy_summary,
        }


# ── Starter Profiles ──────────────────────────────────────────────────────────

def _default_profiles() -> list[AIHarnessProfile]:
    return [
        AIHarnessProfile(
            id="claude_repo_audit_profile",
            display_name="Claude — Repo Audit",
            provider="anthropic",
            model="claude-sonnet-4-6",
            task_types=[TASK_TYPE_REPO_AUDIT, TASK_TYPE_DOCUMENTATION, TASK_TYPE_UI_UX_REVIEW],
            description="Best for architecture review, repo-wide audits, careful planning, and documentation. Inspects before editing, cites files, avoids broad refactors.",
            default_for_tasks=[TASK_TYPE_REPO_AUDIT, TASK_TYPE_DOCUMENTATION],
            priority=20,
            recommended_for=[TASK_TYPE_REPO_AUDIT, TASK_TYPE_DOCUMENTATION],
            not_recommended_for=[TASK_TYPE_CODE_PATCH, TASK_TYPE_EMERGENCY_REPAIR],
            prompt_style="detailed",
            system_instructions="You are a careful architecture reviewer. Always inspect existing code before making recommendations. Cite specific files and line numbers. Avoid broad refactors without explicit approval.",
            tool_policy="strict",
            file_access_policy="read_only",
            approval_policy="founder",
            testing_policy="verify",
            retry_policy="standard",
            timeout_seconds=180,
            quality_tier="maximum",
            reliability_tier="high",
            fallback_profile_ids=["openai_codex_patch_profile", "grok_emergency_repair_profile"],
            telemetry_enabled=True,
            ui_badge="Claude",
            risk_level="low",
        ),
        AIHarnessProfile(
            id="openai_codex_patch_profile",
            display_name="OpenAI Codex — Code Patch",
            provider="openai",
            model="gpt-4o",
            task_types=[TASK_TYPE_CODE_PATCH, TASK_TYPE_OPENCODE_TASK],
            description="Best for code edits, patching, and test generation. Patch-style changes, runs tests, reports exact files modified.",
            default_for_tasks=[TASK_TYPE_CODE_PATCH],
            priority=30,
            recommended_for=[TASK_TYPE_CODE_PATCH],
            not_recommended_for=[TASK_TYPE_REPO_AUDIT, TASK_TYPE_MAX_CHAT],
            prompt_style="technical",
            system_instructions="You are a precise code patch agent. Make minimal targeted changes. Run tests before claiming success. Report exact files changed and line counts.",
            tool_policy="default",
            file_access_policy="read_write",
            approval_policy="founder",
            testing_policy="required",
            retry_policy="aggressive",
            timeout_seconds=300,
            cost_tier="high",
            speed_tier="fast",
            quality_tier="high",
            reliability_tier="standard",
            fallback_profile_ids=["claude_repo_audit_profile", "ollama_budget_fallback_profile"],
            telemetry_enabled=True,
            ui_badge="OpenAI",
            risk_level="medium",
        ),
        AIHarnessProfile(
            id="grok_emergency_repair_profile",
            display_name="xAI Grok — Emergency Repair",
            provider="xai",
            model="grok-4-fast-non-reasoning",
            task_types=[TASK_TYPE_EMERGENCY_REPAIR, TASK_TYPE_MAX_CHAT],
            description="Emergency fallback for quick diagnosis, low-credit mode, and rapid response. Concise, inspect-first, minimal edits, strong safety gates, logs everything.",
            default_for_tasks=[TASK_TYPE_EMERGENCY_REPAIR],
            priority=5,  # Highest priority — used when emergency override is triggered
            emergency_only=True,
            recommended_for=[TASK_TYPE_EMERGENCY_REPAIR],
            not_recommended_for=[TASK_TYPE_REPO_AUDIT, TASK_TYPE_DOCUMENTATION],
            prompt_style="concise",
            system_instructions="You are in emergency mode. Respond concisely. Inspect before acting. Minimize edits. Log every action. If unsure, say so and defer to founder.",
            tool_policy="strict",
            file_access_policy="read_only",
            approval_policy="founder",
            testing_policy="none",
            retry_policy="conservative",
            timeout_seconds=60,
            cost_tier="low",
            speed_tier="fast",
            quality_tier="standard",
            reliability_tier="high",
            fallback_profile_ids=["ollama_budget_fallback_profile"],
            telemetry_enabled=True,
            ui_badge="🛟 Grok",
            risk_level="medium",
        ),
        AIHarnessProfile(
            id="gemini_research_visual_profile",
            display_name="Google Gemini — Research & Visual",
            provider="google",
            model="gemini-2.5-flash",
            task_types=[TASK_TYPE_VISUAL_ANALYSIS, TASK_TYPE_RESEARCH, TASK_TYPE_DOCUMENTATION],
            description="Best for research, multimodal/visual analysis, and long-context tasks. Summarizes sources, avoids repo edits unless explicitly assigned.",
            default_for_tasks=[TASK_TYPE_VISUAL_ANALYSIS],
            priority=40,
            recommended_for=[TASK_TYPE_VISUAL_ANALYSIS, TASK_TYPE_IMAGE_TO_QUOTE],
            not_recommended_for=[TASK_TYPE_CODE_PATCH, TASK_TYPE_OPENCLAW_TASK],
            prompt_style="detailed",
            system_instructions="You are a research and visual analysis agent. Summarize sources clearly. Avoid making changes to the codebase unless explicitly asked. Label confidence levels on visual observations.",
            tool_policy="default",
            file_access_policy="read_only",
            approval_policy="none",
            testing_policy="none",
            retry_policy="standard",
            timeout_seconds=120,
            cost_tier="medium",
            speed_tier="fast",
            quality_tier="high",
            reliability_tier="standard",
            fallback_profile_ids=["ollama_budget_fallback_profile"],
            telemetry_enabled=True,
            ui_badge="Gemini",
            risk_level="low",
        ),
        AIHarnessProfile(
            id="qwen_local_coding_profile",
            display_name="Qwen — Local Coding",
            provider="ollama/local",
            model="qwen",
            task_types=[TASK_TYPE_CODE_PATCH, TASK_TYPE_OPENCODE_TASK],
            description="Local coding via Ollama Qwen. Best for budget coding, agentic coding tests, and small patches. Tests required, conservative claims.",
            priority=60,
            local_only=True,
            budget_mode=True,
            recommended_for=[TASK_TYPE_CODE_PATCH],
            not_recommended_for=[TASK_TYPE_REPO_AUDIT, TASK_TYPE_EMERGENCY_REPAIR],
            prompt_style="concise",
            system_instructions="You are a local coding agent. Make small targeted patches. Require tests for all changes. Be conservative — if local compute is limited, prefer simplicity over sophistication.",
            tool_policy="default",
            file_access_policy="read_write",
            approval_policy="founder",
            testing_policy="required",
            retry_policy="standard",
            timeout_seconds=180,
            cost_tier="free",
            speed_tier="medium",
            quality_tier="standard",
            reliability_tier="experimental",
            fallback_profile_ids=["ollama_budget_fallback_profile"],
            telemetry_enabled=True,
            ui_badge="Qwen",
            risk_level="medium",
        ),
        AIHarnessProfile(
            id="minimax_visual_quote_profile",
            display_name="MiniMax — Visual Quote",
            provider="minimax",
            model="MiniMax-M1",
            task_types=[TASK_TYPE_IMAGE_TO_QUOTE, TASK_TYPE_VISUAL_ANALYSIS, TASK_TYPE_QUOTE_GENERATION],
            description="Visual quote/render support, image-assisted workflows, and concept drafting. Never invents measurements or prices without source; labels confidence; visual concepts only.",
            default_for_tasks=[TASK_TYPE_IMAGE_TO_QUOTE],
            priority=35,
            recommended_for=[TASK_TYPE_IMAGE_TO_QUOTE, TASK_TYPE_VISUAL_ANALYSIS],
            not_recommended_for=[TASK_TYPE_CODE_PATCH, TASK_TYPE_REPO_AUDIT],
            prompt_style="conversational",
            system_instructions="You are a visual concept assistant. Provide image-assisted analysis and concept drafts. Never invent specific measurements, prices, or quantities without a verified source. Always label your confidence level. Separate factual observations from speculative concepts.",
            tool_policy="default",
            file_access_policy="read_only",
            approval_policy="founder",
            testing_policy="none",
            retry_policy="standard",
            timeout_seconds=90,
            cost_tier="low",
            speed_tier="fast",
            quality_tier="standard",
            reliability_tier="standard",
            fallback_profile_ids=["gemini_research_visual_profile"],
            telemetry_enabled=True,
            ui_badge="MiniMax",
            risk_level="low",
        ),
        AIHarnessProfile(
            id="ollama_budget_fallback_profile",
            display_name="Ollama — Budget Fallback",
            provider="ollama/local",
            model="llama3.1",
            task_types=[TASK_TYPE_MAX_CHAT, TASK_TYPE_TRANSCRIPTION, TASK_TYPE_SUMMARIZATION],
            description="Free local fallback for summarization, classification, drafts, and low-priority chat. No high-risk code changes without verification.",
            priority=80,
            local_only=True,
            budget_mode=True,
            recommended_for=[TASK_TYPE_MAX_CHAT, TASK_TYPE_SUMMARIZATION],
            not_recommended_for=[TASK_TYPE_CODE_PATCH, TASK_TYPE_EMERGENCY_REPAIR, TASK_TYPE_REPO_AUDIT],
            prompt_style="concise",
            system_instructions="You are a lightweight local assistant. Provide summaries, classifications, and drafts. Do not make high-risk code changes. Be concise.",
            tool_policy="disabled",
            file_access_policy="read_only",
            approval_policy="none",
            testing_policy="none",
            retry_policy="standard",
            timeout_seconds=60,
            cost_tier="free",
            speed_tier="medium",
            quality_tier="standard",
            reliability_tier="standard",
            fallback_profile_ids=[],
            telemetry_enabled=True,
            ui_badge="Ollama",
            risk_level="safe",
        ),
        AIHarnessProfile(
            id="opencode_repo_execution_profile",
            display_name="OpenCode — Repo Execution",
            provider="openclaw/local",
            model="openclaw",
            task_types=[TASK_TYPE_OPENCLAW_TASK, TASK_TYPE_OPENCODE_TASK, TASK_TYPE_CODE_PATCH],
            description="Repo execution via OpenClaw/terminal-based implementation. Read AGENTS/CLAUDE/progress first, inspect before edit, avoid unrelated refactors, test before claiming done, commit only after successful verified block when explicitly required.",
            default_for_tasks=[TASK_TYPE_OPENCLAW_TASK],
            priority=25,
            recommended_for=[TASK_TYPE_OPENCLAW_TASK, TASK_TYPE_CODE_PATCH],
            not_recommended_for=[TASK_TYPE_MAX_CHAT, TASK_TYPE_VISUAL_ANALYSIS],
            prompt_style="technical",
            system_instructions="You are an autonomous repo execution agent. Before touching any file: read AGENTS.md, CLAUDE.md, and any relevant progress files. Inspect thoroughly before editing. Avoid unrelated refactors. Test every change before claiming done. Commit only when the task explicitly requires it and after all tests pass.",
            tool_policy="permissive",
            file_access_policy="read_write",
            approval_policy="founder",
            testing_policy="required",
            retry_policy="aggressive",
            timeout_seconds=600,
            cost_tier="free",
            speed_tier="medium",
            quality_tier="high",
            reliability_tier="high",
            fallback_profile_ids=["claude_repo_audit_profile"],
            telemetry_enabled=True,
            ui_badge="OpenCode",
            risk_level="high",
            notes="Branch targeting not yet enforced. All tasks run against whatever branch is currently active in OpenClaw.",
        ),
        AIHarnessProfile(
            id="max_default_chat_profile",
            display_name="MAX — Default Chat",
            provider="xai",
            model="grok-4-fast-non-reasoning",
            task_types=[TASK_TYPE_MAX_CHAT, TASK_TYPE_CUSTOMER_SUPPORT, TASK_TYPE_MARKETING],
            description="MAX default chat profile. For general conversation, customer support, and marketing. Concise, friendly, action-oriented.",
            default_for_tasks=[TASK_TYPE_MAX_CHAT],
            priority=50,
            recommended_for=[TASK_TYPE_MAX_CHAT, TASK_TYPE_CUSTOMER_SUPPORT, TASK_TYPE_MARKETING],
            not_recommended_for=[TASK_TYPE_CODE_PATCH, TASK_TYPE_REPO_AUDIT, TASK_TYPE_EMERGENCY_REPAIR],
            prompt_style="conversational",
            system_instructions="You are MAX, Empire's AI assistant. Be concise, friendly, and action-oriented. Provide practical help. When uncertain, say so rather than guessing.",
            tool_policy="default",
            file_access_policy="read_only",
            approval_policy="none",
            testing_policy="none",
            retry_policy="standard",
            timeout_seconds=120,
            cost_tier="medium",
            speed_tier="fast",
            quality_tier="standard",
            reliability_tier="high",
            fallback_profile_ids=["ollama_budget_fallback_profile", "grok_emergency_repair_profile"],
            telemetry_enabled=True,
            ui_badge="MAX",
            risk_level="safe",
        ),
        AIHarnessProfile(
            id="claude_opus_critical_profile",
            display_name="Claude Opus — Critical Code",
            provider="anthropic",
            model="claude-opus-4-6",
            task_types=[TASK_TYPE_CODE_PATCH, TASK_TYPE_REPO_AUDIT],
            description="For critical code quality when maximum reasoning is required. Most expensive tier. Use only whenOpus-level analysis is explicitly needed.",
            priority=10,
            recommended_for=[TASK_TYPE_CODE_PATCH],
            not_recommended_for=[TASK_TYPE_MAX_CHAT, TASK_TYPE_CUSTOMER_SUPPORT],
            prompt_style="technical",
            system_instructions="You are operating at maximum reasoning capacity. Provide thorough, precise code analysis and changes. Cite files and line numbers. No hand-waving.",
            tool_policy="strict",
            file_access_policy="read_write",
            approval_policy="founder",
            testing_policy="required",
            retry_policy="standard",
            timeout_seconds=300,
            cost_tier="high",
            speed_tier="slow",
            quality_tier="maximum",
            reliability_tier="high",
            fallback_profile_ids=["claude_repo_audit_profile", "openai_codex_patch_profile"],
            telemetry_enabled=True,
            ui_badge="Claude Opus",
            risk_level="medium",
        ),
    ]


# ── Profile Registry ──────────────────────────────────────────────────────────

class AIHarnessProfileRegistry:
    def __init__(self):
        self._profiles: dict[str, AIHarnessProfile] = {}
        for profile in _default_profiles():
            self._profiles[profile.id] = profile

    def list_profiles(self, enabled_only: bool = True) -> list[AIHarnessProfile]:
        if enabled_only:
            return [p for p in self._profiles.values() if p.enabled]
        return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[AIHarnessProfile]:
        return self._profiles.get(profile_id)

    def get_default_for_task(self, task_type: str) -> Optional[AIHarnessProfile]:
        candidates = [
            p for p in self._profiles.values()
            if p.enabled and task_type in p.default_for_tasks
        ]
        if not candidates:
            return None
        # Return highest priority (lowest number)
        return min(candidates, key=lambda p: p.priority)

    def recommend_profiles(
        self,
        task_type: str,
        requested_provider: Optional[str] = None,
        budget_mode: bool = False,
    ) -> list[AIHarnessProfile]:
        candidates = [p for p in self._profiles.values() if p.enabled and task_type in p.task_types]

        if requested_provider:
            candidates = [p for p in candidates if p.provider == requested_provider]

        if budget_mode:
            # Prefer local/budget profiles
            candidates = sorted(candidates, key=lambda p: (0 if p.local_only else 1, p.priority))
        else:
            candidates = sorted(candidates, key=lambda p: p.priority)

        return candidates

    def select_profile(
        self,
        task_type: str,
        requested_provider: Optional[str] = None,
        requested_model: Optional[str] = None,
        emergency_override: bool = False,
        budget_mode: bool = False,
        provider_availability: Optional[dict] = None,
    ) -> tuple[Optional[AIHarnessProfile], RoutingExplanation]:
        """Select the best profile for a task. Returns (profile, routing_explanation)."""
        avail = provider_availability or {}

        # Emergency override: Grok emergency profile
        if emergency_override:
            profile = self.get_profile("grok_emergency_repair_profile")
            if profile and profile.enabled:
                reason = "Emergency override triggered — using Grok emergency profile"
                routing = RoutingExplanation(
                    selected_profile_id=profile.id,
                    selected_provider=profile.provider,
                    selected_model=profile.model,
                    task_type=task_type,
                    reason=reason,
                    fallback_used=False,
                    emergency_override=True,
                )
                _record_routing(profile.id, profile.provider, profile.model, task_type,
                               reason, False, "", True)
                return profile, routing

        # Explicit provider + model request
        if requested_provider or requested_model:
            candidates = self.list_profiles(enabled_only=True)
            # Exclude emergency_only profiles for explicit provider requests
            candidates = [c for c in candidates if not c.emergency_only]
            # Must support the requested task type
            candidates = [c for c in candidates if task_type in c.task_types]
            if requested_provider:
                candidates = [c for c in candidates if c.provider == requested_provider]
            if requested_model:
                candidates = [c for c in candidates if c.model == requested_model]
            if candidates:
                # Pick highest priority
                profile = min(candidates, key=lambda p: p.priority)
                routing = RoutingExplanation(
                    selected_profile_id=profile.id,
                    selected_provider=profile.provider,
                    selected_model=profile.model,
                    task_type=task_type,
                    reason=f"Explicit provider/model request: provider={requested_provider}, model={requested_model}",
                )
                _record_routing(profile.id, profile.provider, profile.model, task_type,
                              routing.reason, False, "", False)
                return profile, routing
            else:
                # Explicit provider requested but no matching task type — warn and fall through
                routing = RoutingExplanation(
                    selected_profile_id="",
                    selected_provider=requested_provider or "",
                    selected_model=requested_model or "",
                    task_type=task_type,
                    reason=f"Provider '{requested_provider}' has no profile for task '{task_type}' — no fallback selected",
                    fallback_used=True,
                    fallback_reason=f"No {requested_provider} profile supports task type '{task_type}'",
                )
                _record_routing("", "", "", task_type, routing.reason,
                               True, routing.fallback_reason, False)
                return None, routing

        # Default for task type
        profile = self.get_default_for_task(task_type)
        if profile:
            routing = RoutingExplanation(
                selected_profile_id=profile.id,
                selected_provider=profile.provider,
                selected_model=profile.model,
                task_type=task_type,
                reason=f"Default profile for task type '{task_type}'",
            )
            _record_routing(profile.id, profile.provider, profile.model, task_type,
                          routing.reason, False, "", False)
            return profile, routing

        # Fallback to max_default_chat_profile
        profile = self.get_profile("max_default_chat_profile")
        if profile and profile.enabled:
            routing = RoutingExplanation(
                selected_profile_id=profile.id,
                selected_provider=profile.provider,
                selected_model=profile.model,
                task_type=task_type,
                reason=f"No default profile for '{task_type}' — fell back to MAX default chat",
                fallback_used=True,
                fallback_reason=f"Task type '{task_type}' has no assigned default profile",
            )
            _record_routing(profile.id, profile.provider, profile.model, task_type,
                          routing.reason, True, routing.fallback_reason, False)
            return profile, routing

        # Final fallback: ollama_budget_fallback_profile
        profile = self.get_profile("ollama_budget_fallback_profile")
        if profile and profile.enabled:
            routing = RoutingExplanation(
                selected_profile_id=profile.id,
                selected_provider=profile.provider,
                selected_model=profile.model,
                task_type=task_type,
                reason="All profiles exhausted — using Ollama budget fallback",
                fallback_used=True,
                fallback_reason="No enabled profiles available",
            )
            _record_routing(profile.id, profile.provider, profile.model, task_type,
                          routing.reason, True, routing.fallback_reason, False)
            return profile, routing

        # Nothing available
        routing = RoutingExplanation(
            selected_profile_id="",
            selected_provider="",
            selected_model="",
            task_type=task_type,
            reason="No available profiles",
        )
        _record_routing("", "", "", task_type, routing.reason, False, "", False)
        return None, routing

    def build_policy_summary(self, profile_id: str) -> str:
        profile = self.get_profile(profile_id)
        if not profile:
            return "Unknown profile"

        lines = [
            f"Profile: {profile.display_name}",
            f"Provider: {profile.provider}/{profile.model}",
            f"Task types: {', '.join(profile.task_types)}",
            f"Risk level: {profile.risk_level}",
            f"Tool policy: {profile.tool_policy}",
            f"File access: {profile.file_access_policy}",
            f"Approval required: {profile.approval_policy}",
            f"Testing: {profile.testing_policy}",
            f"Cost tier: {profile.cost_tier}",
            f"Speed: {profile.speed_tier}",
        ]
        if profile.fallback_profile_ids:
            lines.append(f"Fallbacks: {', '.join(profile.fallback_profile_ids)}")
        if profile.notes:
            lines.append(f"Notes: {profile.notes}")

        return "\n".join(lines)

    def build_system_instruction_block(
        self, profile_id: str, task_type: str
    ) -> str:
        profile = self.get_profile(profile_id)
        if not profile:
            return ""

        block = f"[Harness Profile: {profile.display_name}]\n"
        block += f"[Task: {task_type}]\n"
        if profile.system_instructions:
            block += f"[System Instructions]\n{profile.system_instructions}\n"
        block += f"[Tool Policy: {profile.tool_policy}]\n"
        block += f"[File Access: {profile.file_access_policy}]\n"
        block += f"[Approval: {profile.approval_policy}]\n"
        return block


# ── Module-level last routing decision (updated on every select_profile call) ──
_last_routing: dict = {}


def _record_routing(profile_id: str, provider: str, model: str, task_type: str,
                    reason: str, fallback_used: bool, fallback_reason: str,
                    emergency_override: bool) -> None:
    _last_routing.update({
        "selected_profile_id": profile_id,
        "selected_provider": provider,
        "selected_model": model,
        "task_type": task_type,
        "reason": reason,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "emergency_override": emergency_override,
        "timestamp": datetime.now().isoformat(),
    })


# ── Telemetry ──────────────────────────────────────────────────────────────────

# Write to the backend data/logs directory that this code is running from.
# Resolves relative to THIS module's location, so ~/empire-repo-v10/backend when
# running from v10 worktree, ~/empire-repo/backend when running from stable.
_logs_dir = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
_logs_dir.mkdir(parents=True, exist_ok=True)
_ROUTING_LOG = _logs_dir / "ai_harness_routing.jsonl"


def log_routing_decision(
    channel: Optional[str],
    task_type: str,
    selected_provider: str,
    selected_model: str,
    selected_harness_profile: str,
    fallback_used: bool,
    fallback_reason: str,
    emergency_override: bool,
    success: Optional[bool] = None,
    error: Optional[str] = None,
) -> None:
    """Log a routing decision to JSONL. Never logs secrets, API keys, or full prompts."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "channel": channel or "",
        "task_type": task_type,
        "selected_provider": selected_provider,
        "selected_model": selected_model,
        "selected_harness_profile": selected_harness_profile,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "emergency_override": emergency_override,
        "success": success,
        "error": error or "",
    }
    try:
        with open(_ROUTING_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning(f"Failed to log routing decision: {e}")


def get_recent_routing_decisions(limit: int = 20) -> list[dict]:
    """Read recent sanitized routing decisions from JSONL log."""
    entries = []
    if not _ROUTING_LOG.exists():
        return entries
    try:
        with open(_ROUTING_LOG) as f:
            lines = f.readlines()
        for line in reversed(lines[-limit:]):
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Failed to read routing log: {e}")
    return list(reversed(entries))


def get_last_routing_decision() -> dict:
    """Return the most recent routing decision dict (metadata-only, not from log)."""
    return dict(_last_routing)


# ── Module-level singleton ─────────────────────────────────────────────────────

registry = AIHarnessProfileRegistry()
