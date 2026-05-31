"""MAX AI Router - Multi-provider tiered routing: xAI Grok, Claude, Gemini, OpenAI, Groq, OpenClaw, Ollama with streaming & vision."""
import os
import json
import httpx
import base64
import subprocess
import re
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, AsyncGenerator, Tuple, Any
from pathlib import Path
import logging
from dotenv import load_dotenv
from app.services.data_paths import data_root
from .routing_state import (
    CANONICAL_PROVIDERS,
    RoutingState,
    canonical_provider,
    env_flag,
    load_routing_state,
    provider_effectively_disabled,
    provider_label,
    provider_manually_disabled,
    provider_configured,
    provider_default_model,
    provider_disabled,
    provider_is_cloud,
    provider_key_env,
    provider_model_choices,
    provider_model_env,
    save_routing_state,
    update_routing_state,
)

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger("max.ai_router")

class AIModel(Enum):
    GROK = "grok"
    CLAUDE = "claude"
    CLAUDE_OPUS = "claude-opus-4-6"
    CLAUDE_SONNET = "claude-sonnet-4-6"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    QWEN = "qwen"
    OPENCLAW = "openclaw"
    OLLAMA = "ollama-llama"
    GEMINI = "gemini"
    OPENAI_NANO = "gpt-4.1-nano"
    OPENAI_MINI = "gpt-4o-mini"
    OPENAI_4O = "gpt-4o"
    MINIMAX = "minimax"


class TaskComplexity(Enum):
    SIMPLE = "simple"      # hi, status, lookup, greeting, thanks, ok, yes, no
    MODERATE = "moderate"   # summary, report, list, CRM, show, recent, brief
    COMPLEX = "complex"    # analyze, calculate, quote, why, explain, compare, strategy
    CRITICAL = "critical"  # fix, edit, code, file, git, build, deploy, read ~/

# ── Conversation model floor ────────────────────────────────────────
# Once a conversation escalates to a tier, it stays at least that tier
# for the rest of the session.  Maps conversation_id → highest complexity.
_COMPLEXITY_ORDER = {TaskComplexity.SIMPLE: 0, TaskComplexity.MODERATE: 1,
                     TaskComplexity.COMPLEX: 2, TaskComplexity.CRITICAL: 3}
_conversation_floors: dict[str, TaskComplexity] = {}


def apply_conversation_floor(conversation_id: str | None, complexity: TaskComplexity) -> TaskComplexity:
    """Enforce model floor: never downgrade within a conversation."""
    if not conversation_id:
        return complexity
    prev = _conversation_floors.get(conversation_id)
    if prev and _COMPLEXITY_ORDER.get(prev, 0) > _COMPLEXITY_ORDER.get(complexity, 0):
        logger.info(f"[floor] Holding {conversation_id[:8]} at {prev.value} (would have been {complexity.value})")
        return prev
    _conversation_floors[conversation_id] = complexity
    return complexity


def classify_complexity(message: str, *, source: str = "", turn_count: int = 0) -> TaskComplexity:
    """Instant complexity classification — keyword matching + message length. No AI call.

    Parameters
    ----------
    source : str
        Where the message came from (e.g. "voice", "web", "telegram").
        Voice input gets escalated to MODERATE minimum.
    turn_count : int
        Number of back-and-forth messages in current session on same topic.
        3+ turns without resolution → escalate to MODERATE.
    """
    msg = message.lower().strip()
    words = msg.split()

    # Greetings set — used by both voice and standard classification
    simple_greetings = {'hi', 'hello', 'hey', 'thanks', 'thank you', 'bye',
                        'good morning', 'good night', 'good evening',
                        "what's up", 'whats up', 'sup', 'yo'}

    # CRITICAL — code/file operations
    critical_keywords = ['fix', 'edit', 'code', 'file', 'git', 'build', 'deploy', 'commit', 'push', 'pull', 'merge', 'rebase', 'scaffold', 'refactor']
    if any(kw in words for kw in critical_keywords) or msg.startswith('read ~/') or msg.startswith('cat ') or '```' in msg:
        return TaskComplexity.CRITICAL

    # ── Escalation checks (floor = MODERATE) ──

    # Memory/search queries need contextual reasoning
    memory_patterns = ['what did i', 'my request', 'find my', 'remember when',
                       'search for', 'look up', 'what was', 'did i ask',
                       'last time', 'previous conversation', 'earlier today',
                       'search our', 'search conversation', 'find conversation']
    if any(p in msg for p in memory_patterns):
        return TaskComplexity.COMPLEX

    # Tool-triggering messages — Gemini Flash can't handle tool results well
    tool_trigger_patterns = [
        'create a task', 'create task', 'add a task', 'new task',
        'create quote', 'create a quote', 'new quote',
        'create invoice', 'send invoice', 'send email',
        'search memory', 'search memories', 'check my',
        'look up customer', 'find customer', 'customer list',
        'schedule', 'set reminder', 'remind me',
        'run report', 'generate report', 'show report',
        'post to', 'send to telegram', 'send message',
        'check my email', 'check email', 'check inbox', 'read my email',
        'any new email', 'unread email', 'new emails', 'check mail',
    ]
    if any(p in msg for p in tool_trigger_patterns):
        return TaskComplexity.MODERATE

    # Voice transcriptions are less structured — need smarter model
    if source == "voice":
        # Only exact greetings stay SIMPLE for voice
        if msg.rstrip('!., ') in simple_greetings:
            return TaskComplexity.SIMPLE
        return TaskComplexity.MODERATE  # everything else from voice → MODERATE min

    # Multi-turn without resolution → escalate
    if turn_count >= 3:
        return TaskComplexity.MODERATE

    # ── Standard classification ──

    # SIMPLE — ONLY exact greetings (Gemini Flash territory)
    # Must be an EXACT match after stripping punctuation — no questions, no requests
    stripped = msg.rstrip('!., ')
    if stripped in simple_greetings:
        return TaskComplexity.SIMPLE

    # COMPLEX — analytical tasks
    complex_keywords = ['analyze', 'analysis', 'calculate', 'quote', 'why', 'explain', 'compare', 'strategy', 'optimize', 'recommend', 'evaluate', 'financial', 'pricing', 'revenue', 'profit']
    if any(kw in msg for kw in complex_keywords):
        return TaskComplexity.COMPLEX

    # MODERATE — everything else (Grok territory)
    return TaskComplexity.MODERATE


@dataclass
class AIMessage:
    role: str
    content: str
    image_path: Optional[str] = None

@dataclass
class AIResponse:
    content: str
    model_used: str
    fallback_used: bool = False
    function_calls: Optional[list] = None  # xAI /v1/responses function calls


PROVIDER_LABELS: dict[str, str] = {
    "minimax": "MiniMax",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "claude": "Claude",
    "openai": "OpenAI",
    "gemini": "Gemini",
    "xai": "xAI Grok",
    "ollama": "Ollama",
    "openclaw": "OpenClaw",
}

from .system_prompt import get_system_prompt
from .desk_prompt import get_desk_system_prompt
from .token_tracker import token_tracker

# Per-desk model routing — overrides primary model when desk is specified
DESK_MODEL_ROUTING = {
    "codeforge": AIModel.CLAUDE_OPUS,     # Atlas — code quality critical
    "analytics": AIModel.CLAUDE_SONNET,   # Raven — data analysis
    "quality": AIModel.CLAUDE_SONNET,     # Phoenix — accuracy critical
    "innovation": AIModel.CLAUDE_SONNET,  # Spark — creative reasoning
    "forge": AIModel.MINIMAX,             # Kai — routine ops, speed
    "sales": AIModel.GROQ,              # Aria — needs reasoning, not just lookups
    "costtracker": AIModel.OPENAI_NANO,  # Cipher — basic expense math
    "it": AIModel.MINIMAX,               # Orion — health checks routine
    "marketing": AIModel.MINIMAX,         # Nova — content needs reasoning
    "support": AIModel.MINIMAX,          # Fast responses
    # All others fall through to complexity-based routing
}


class AIRouter:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY", "")
        self.xai_base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        self.xai_model = os.getenv("XAI_MODEL", "grok-4-fast-non-reasoning")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        self.qwen_key = os.getenv("QWEN_API_KEY", "")
        self.qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1").rstrip("/")
        self.qwen_model = os.getenv("QWEN_MODEL", "qwen-plus")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        try:
            self.xai_max_tokens = int(os.getenv("XAI_MAX_TOKENS", "8192"))
        except ValueError:
            self.xai_max_tokens = 8192
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.minimax_key = os.getenv("MINIMAX_API_KEY", "")
        self.minimax_base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
        self.minimax_model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
        # Empire-wide provider policy — set via MAX_PRIMARY_PROVIDER and MAX_DISABLE_XAI env vars
        self.max_primary_provider = os.getenv("MAX_PRIMARY_PROVIDER", "").lower()
        self.max_disable_xai = os.getenv("MAX_DISABLE_XAI", "").lower() in ("true", "1", "yes")
        self.max_disable_ollama = os.getenv("MAX_DISABLE_OLLAMA", "").lower() in ("true", "1", "yes")
        self.last_provider_errors: dict[str, str] = {}
        self.last_provider_successes: dict[str, str] = {}
        self.routing_state: RoutingState = load_routing_state()
        # Primary model is largely legacy/diagnostic now that selector state is authoritative.
        # Keep xAI first when available to avoid stale env cross-test contamination.
        if self.xai_key and not self.max_disable_xai:
            self.primary_model = AIModel.GROK
        elif self.max_primary_provider == "minimax" and self.minimax_key:
            self.primary_model = AIModel.MINIMAX
        elif self.max_primary_provider == "claude" and self.anthropic_key:
            self.primary_model = AIModel.CLAUDE
        elif self.max_primary_provider == "groq" and self.groq_key:
            self.primary_model = AIModel.GROQ
        elif self.anthropic_key:
            self.primary_model = AIModel.CLAUDE
        elif self.groq_key:
            self.primary_model = AIModel.GROQ
        elif self.minimax_key:
            self.primary_model = AIModel.MINIMAX
        else:
            self.primary_model = AIModel.OLLAMA
        self.system_prompt = get_system_prompt()
        self.upload_dirs = [
            data_root() / "uploads",
            Path.home() / "empire-repo" / "backend" / "data" / "uploads",
            Path.home() / "empire-repo" / "uploads",
        ]
        self.upload_dir = self.upload_dirs[0]
        providers = []
        if self.xai_key: providers.append("xAI")
        if self.anthropic_key: providers.append("Claude")
        if self.groq_key: providers.append("Groq")
        if self.gemini_key: providers.append("Gemini")
        if self.openai_key: providers.append("OpenAI")
        if self.deepseek_key: providers.append("DeepSeek")
        if self.qwen_key: providers.append("Qwen")
        if self.openrouter_key: providers.append("OpenRouter")
        if self.minimax_key: providers.append("MiniMax")
        providers += ["OpenClaw"]
        if not self.max_disable_ollama:
            providers.append("Ollama")
        model_names = {AIModel.GROK: "xAI Grok", AIModel.CLAUDE: "Claude 4.6 Sonnet", AIModel.GROQ: "Groq Llama", AIModel.OLLAMA: "Ollama", AIModel.MINIMAX: "MiniMax"}
        xai_label = "ON" if self.xai_key and not self.max_disable_xai else ("disabled" if self.max_disable_xai else "no_key")
        ollama_label = "disabled" if self.max_disable_ollama else "enabled"
        logger.info(
            "[MAX] Primary=%s | Providers=%s | xAI=%s | Ollama=%s",
            model_names.get(self.primary_model, str(self.primary_model)),
            ", ".join(providers),
            xai_label,
            ollama_label,
        )

    def _refresh_runtime_keys(self) -> None:
        """Reload key env values so runtime updates are reflected without restart."""
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.minimax_key = os.getenv("MINIMAX_API_KEY", "")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.qwen_key = os.getenv("QWEN_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.minimax_model = os.getenv("MINIMAX_MODEL", self.minimax_model or "MiniMax-M2.7")
        self.xai_model = os.getenv("XAI_MODEL", self.xai_model or "grok-4-fast-non-reasoning")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", self.deepseek_model or "deepseek-chat")
        self.qwen_model = os.getenv("QWEN_MODEL", self.qwen_model or "qwen-plus")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", self.openrouter_model or "openai/gpt-4o-mini")

    def _refresh_routing_state(self) -> RoutingState:
        self.routing_state = load_routing_state()
        self._refresh_runtime_keys()
        return self.routing_state

    def _provider_key_present(self, provider: str) -> bool:
        canonical = canonical_provider(provider)
        if canonical == "xai":
            return bool(self.xai_key)
        if canonical == "claude":
            return bool(self.anthropic_key)
        if canonical == "groq":
            return bool(self.groq_key)
        if canonical == "gemini":
            return bool(self.gemini_key)
        if canonical == "openai":
            return bool(self.openai_key)
        if canonical == "minimax":
            return bool(self.minimax_key)
        if canonical == "deepseek":
            return bool(self.deepseek_key)
        if canonical == "qwen":
            return bool(self.qwen_key)
        if canonical == "openrouter":
            return bool(self.openrouter_key)
        return True

    def _provider_disabled_reason(self, provider: str, state: RoutingState | None = None) -> str | None:
        state = state or self.routing_state
        canonical = canonical_provider(provider)
        if not canonical:
            return "unknown_provider"
        if provider_manually_disabled(state, canonical):
            return "disabled_by_platformforge"
        if provider_disabled(canonical):
            if canonical == "xai":
                return "credits_unavailable"
            if canonical == "ollama":
                return "founder_disabled_due_to_stall_suspected"
            return "disabled_by_kill_switch"
        if state.ai_calls_disabled and provider_is_cloud(canonical):
            return "ai_calls_disabled"
        if not self._provider_key_present(canonical) and canonical not in {"ollama", "openclaw"}:
            return "missing_key"
        return None

    def _local_provider_online(self, provider: str) -> bool | None:
        provider = canonical_provider(provider)
        try:
            if provider == "openclaw":
                resp = httpx.get("http://localhost:7878/health", timeout=2.0)
                return resp.status_code < 500
            if provider == "ollama":
                resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
                return resp.status_code < 500
        except Exception:
            return False
        return None

    def get_available_models(self):
        state = self._refresh_routing_state()
        legacy_id_map = {"xai": "grok", "ollama": "ollama-llama"}
        rows: list[dict[str, Any]] = []
        for provider in CANONICAL_PROVIDERS:
            configured = provider_configured(provider) and self._provider_key_present(provider)
            disabled_reason = self._provider_disabled_reason(provider, state)
            local_online = self._local_provider_online(provider)
            if local_online is False and disabled_reason is None and provider in {"openclaw", "ollama"}:
                disabled_reason = "local_service_unavailable"
            disabled = disabled_reason is not None
            models = provider_model_choices(provider)
            active_model = state.selected_model if state.selected_provider == provider else models[0]
            base_url = None
            if provider == "xai":
                base_url = self.xai_base_url
            elif provider == "minimax":
                base_url = self.minimax_base_url
            elif provider == "deepseek":
                base_url = self.deepseek_base_url
            elif provider == "qwen":
                base_url = self.qwen_base_url
            elif provider == "openrouter":
                base_url = self.openrouter_base_url
            last_error = self.last_provider_errors.get(provider) or self.last_provider_errors.get("grok" if provider == "xai" else provider)
            last_success = self.last_provider_successes.get(provider) or self.last_provider_successes.get("grok" if provider == "xai" else provider)
            rows.append(
                {
                    "id": legacy_id_map.get(provider, provider),
                    "name": provider_label(provider),
                    "provider_canonical": provider,
                    "models": models,
                    "model": active_model,
                    "configured": bool(configured),
                    "available": bool(configured) and not disabled,
                    "disabled": disabled,
                    "disabled_reason": disabled_reason,
                    "primary": provider == state.selected_provider,
                    "selected": provider == state.selected_provider,
                    "type": "cloud" if provider_is_cloud(provider) else "local",
                    "fallback_eligible": bool(configured) and not disabled,
                    "status_source": "env_configured",
                    "last_error": last_error,
                    "last_success": last_success,
                    "manual_disabled": provider_manually_disabled(state, provider),
                    "credential_env": provider_key_env(provider) or None,
                    "local_online": local_online,
                    "base_url": base_url,
                }
            )
        return rows

    def _record_provider_error(self, provider: str, exc: Exception) -> None:
        key = canonical_provider(provider) or provider
        self.last_provider_errors[key] = f"{type(exc).__name__}: {str(exc)[:300]}"
        if key == "xai":
            self.last_provider_errors["grok"] = self.last_provider_errors[key]

    def _record_provider_success(self, provider: str) -> None:
        key = canonical_provider(provider) or provider
        self.last_provider_successes[key] = "ok"
        self.last_provider_errors.pop(key, None)
        if key == "xai":
            self.last_provider_successes["grok"] = "ok"
            self.last_provider_errors.pop("grok", None)

    def _provider_unavailable_message(self) -> str:
        return (
            "I could not complete the AI text-generation step because no configured text provider "
            "returned a verified response. Provider diagnostics are available in /api/v1/max/status."
        )

    def get_routing_state_payload(self) -> dict[str, Any]:
        state = self._refresh_routing_state()
        return {
            **state.as_dict(),
            "selected_provider_label": provider_label(state.selected_provider),
            "provider_registry": self.get_available_models(),
        }

    def set_active_provider_model(
        self,
        *,
        provider: str,
        model: str | None,
        updated_by: str = "founder_or_system",
        reason: str = "manual_selector_switch",
    ) -> RoutingState:
        canonical = canonical_provider(provider)
        if canonical not in CANONICAL_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        current = self._refresh_routing_state()
        disabled_reason = self._provider_disabled_reason(canonical, current)
        if disabled_reason:
            raise ValueError(f"Provider '{canonical}' is unavailable: {disabled_reason}")

        selected_model = (model or "").strip()
        if not selected_model:
            selected_model = provider_default_model(canonical)
        if selected_model not in provider_model_choices(canonical):
            raise ValueError(f"Model '{selected_model}' is not in configured choices for '{canonical}'")

        state = update_routing_state(
            selected_provider=canonical,
            selected_model=selected_model,
            updated_by=updated_by,
            last_switch_reason=reason,
        )
        self.routing_state = state
        return state

    def set_provider_enabled(
        self,
        provider: str,
        enabled: bool,
        *,
        updated_by: str = "founder_or_system",
        reason: str = "platformforge_toggle",
    ) -> RoutingState:
        canonical = canonical_provider(provider)
        if canonical not in CANONICAL_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        state = self._refresh_routing_state()
        manual = dict(state.manual_disabled or {})
        if enabled:
            manual.pop(canonical, None)
        else:
            manual[canonical] = True
        state = update_routing_state(
            manual_disabled=manual,
            updated_by=updated_by,
            last_switch_reason=f"{reason}:{canonical}:{'enable' if enabled else 'disable'}",
        )
        self.routing_state = state
        return state

    def set_routing_policy(
        self,
        *,
        fallback_enabled: bool | None = None,
        ai_calls_disabled: bool | None = None,
        updated_by: str = "founder_or_system",
        reason: str = "routing_policy_update",
    ) -> RoutingState:
        state = update_routing_state(
            fallback_enabled=fallback_enabled,
            ai_calls_disabled=ai_calls_disabled,
            updated_by=updated_by,
            last_switch_reason=reason,
        )
        self.routing_state = state
        return state

    async def provider_smoke_test(
        self,
        *,
        provider: str,
        model: str | None = None,
        prompt: str = "Reply only: deepseek ok",
        tenant_id: str = "founder",
    ) -> AIResponse:
        state = self._refresh_routing_state()
        canonical = canonical_provider(provider)
        if canonical not in CANONICAL_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        reason = self._provider_disabled_reason(canonical, state)
        if reason:
            raise ValueError(f"Provider '{canonical}' unavailable: {reason}")
        selected_model = (model or "").strip() or provider_default_model(canonical)
        messages = [AIMessage(role="system", content=self.system_prompt), AIMessage(role="user", content=prompt)]
        result = await self._try_provider_chat(
            canonical,
            selected_model,
            messages,
            [AIMessage(role="user", content=prompt)],
            None,
            False,
            "chat",
            "platform",
            tenant_id,
            tools=None,
        )
        if result is None:
            error_text = self.last_provider_errors.get(canonical) or self.last_provider_errors.get("grok" if canonical == "xai" else canonical)
            raise RuntimeError(error_text or "provider_smoke_test_failed")
        return result

    def _sanitize_minimax_content(self, text: str) -> str:
        cleaned = (text or "").strip()
        cleaned = re.sub(r"<think>[\s\S]*?</think>\s*", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"<thinking>[\s\S]*?</thinking>\s*", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"</?think(?:ing)?>", "", cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            return ""

        reasoning_markers = (
            "i should respond",
            "i need to respond",
            "the user",
            "simple greeting",
            "founder",
        )
        self_talk_patterns = (
            r"^\s*wait\b\s*[-—:,.].*",
            r"^\s*actually\b\s*,?.*",
            r"^\s*let me\b.*",
            r"^\s*i(?:'ll| will)\s+(?:write|make|answer|respond|summarize|condense|describe)\b.*",
            r"^\s*key elements from (?:the )?description\s*:?\s*",
        )

        def _is_self_talk_line(line: str) -> bool:
            return any(re.match(pattern, line, flags=re.IGNORECASE) for pattern in self_talk_patterns)

        if "\n\n" in cleaned:
            prefix, visible = cleaned.split("\n\n", 1)
            prefix_l = prefix.lower()
            prefix_lines = [line.strip() for line in prefix.splitlines() if line.strip()]
            if any(marker in prefix_l for marker in reasoning_markers) or (
                prefix_lines and all(_is_self_talk_line(line) or line.startswith("-") for line in prefix_lines)
            ):
                cleaned = visible.lstrip()

        lines = cleaned.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        while len([line for line in lines if line.strip()]) > 1 and _is_self_talk_line(lines[0]):
            lines.pop(0)
            while lines and not lines[0].strip():
                lines.pop(0)
        cleaned = "\n".join(lines).strip()

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
        if len(paragraphs) > 1:
            filtered = []
            for paragraph in paragraphs:
                para_lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
                if para_lines and all(_is_self_talk_line(line) or line.startswith("-") for line in para_lines):
                    continue
                filtered.append(paragraph)
            if filtered:
                cleaned = "\n\n".join(filtered).strip()
        return cleaned

    AUDIO_EXTS = {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.wma', '.aac'}
    TEXT_EXTS = {'.txt', '.md', '.csv', '.json'}
    CODE_EXTS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.sh', '.yaml', '.yml'}

    def _find_file(self, filename: str) -> Optional[Path]:
        safe = Path(filename).name
        for root in self.upload_dirs:
            for cat in ['images', 'documents', 'audio', 'other', 'code']:
                path = root / cat / safe
                if path.exists() and path.is_file():
                    return path
        return None

    def _find_image(self, filename: str) -> Optional[Path]:
        return self._find_file(filename)

    def _is_image(self, path: Path) -> bool:
        return path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

    def _is_audio(self, path: Path) -> bool:
        return path.suffix.lower() in self.AUDIO_EXTS

    def _is_readable_text(self, path: Path) -> bool:
        return path.suffix.lower() in (self.TEXT_EXTS | self.CODE_EXTS)

    def _is_pdf(self, path: Path) -> bool:
        return path.suffix.lower() == '.pdf'

    def _transcribe_audio(self, path: Path) -> str:
        """Transcribe audio using Groq Whisper API."""
        from app.services.max.stt_service import stt_service
        return stt_service.transcribe_sync(path)

    def _read_text_file(self, path: Path, max_chars: int = 50000) -> str:
        """Read text content from a file, truncating if too large."""
        try:
            text = path.read_text(errors='replace')
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n[Truncated — file is {len(text)} chars, showing first {max_chars}]"
            return text
        except Exception as e:
            return f"[Could not read file: {e}]"

    def _read_pdf(self, path: Path, max_chars: int = 50000) -> str:
        """Extract text from a PDF file."""
        try:
            from subprocess import run
            result = run(['pdftotext', str(path), '-'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                if len(text) > max_chars:
                    text = text[:max_chars] + f"\n\n[Truncated — showing first {max_chars} chars]"
                return text
        except Exception:
            pass
        return "[Could not extract PDF text — pdftotext not available]"

    def _process_attachment(self, filename: str) -> Tuple[Optional[Path], Optional[str]]:
        """Process an attached file. Returns (image_path, attachment_text).
        For images: returns the path for vision API.
        For audio/docs/code: returns extracted text content."""
        path = self._find_file(filename)
        if not path:
            return None, None

        if self._is_image(path):
            return path, None
        elif self._is_audio(path):
            transcript = self._transcribe_audio(path)
            return None, f"[Audio transcription of {filename}]\n{transcript}"
        elif self._is_pdf(path):
            text = self._read_pdf(path)
            return None, f"[Contents of {filename}]\n{text}"
        elif self._is_readable_text(path):
            text = self._read_text_file(path)
            return None, f"[Contents of {filename}]\n{text}"
        else:
            return None, f"[Unsupported file type: {path.suffix}]"

    async def _prepend_local_vision_triage(self, messages: List[AIMessage], image_path: Optional[Path]) -> List[AIMessage]:
        """Run lightweight local Ollama vision triage before cloud escalation."""
        if not image_path or not self._is_image(image_path) or not messages:
            return messages

        try:
            from app.services.ollama_vision_router import generate_vision_response, vision_model_order

            _, image_b64 = self._encode_image(image_path)
            prompt = (
                "You are MAX's local lightweight vision triage. Describe the image, "
                "list visible objects/text, call out business-relevant details, and say "
                "what a cloud model should inspect next. Keep it concise and factual."
            )
            analysis, model_used = await generate_vision_response(
                prompt=prompt,
                image_b64=image_b64,
                timeout=60.0,
            )
            if not analysis:
                return messages

            last = messages[-1]
            routing = " -> ".join(vision_model_order())
            local_context = (
                f"[Local Ollama vision triage via {model_used}; route {routing}]\n"
                f"{analysis.strip()}\n\n"
            )
            updated = list(messages)
            updated[-1] = AIMessage(role=last.role, content=local_context + last.content, image_path=last.image_path)
            return updated
        except Exception as e:
            logger.warning(f"Local Ollama vision triage skipped: {e}")
            return messages

    def _safe_vision_error(self, error: str | None) -> str:
        text = (error or "MiniMax image understanding failed").strip()
        text = text.replace(os.getenv("MINIMAX_API_KEY", "") or "\0", "[KEY_REDACTED]")
        text = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[KEY_REDACTED]", text)
        text = re.sub(r"[A-Za-z0-9+/]{40,}={0,2}", "[TOKEN_REDACTED]", text)
        text = text[:300]
        return text or "MiniMax image understanding failed"

    async def _prepend_mmx_vision_context(
        self,
        messages: List[AIMessage],
        image_path: Optional[Path],
        image_filename: str | None = None,
    ) -> Tuple[List[AIMessage], Optional[str], Optional[dict]]:
        """Analyze attached images through MiniMax mmx_cli and inject grounded text context.

        MiniMax text/chat remains a text provider. Image understanding belongs to
        the mmx CLI transport, so downstream chat providers receive a verified
        description instead of the raw image payload.
        """
        if not image_path or not self._is_image(image_path) or not messages:
            return messages, None, None

        try:
            from app.services.max.minimax_tools import minimax_understand_image

            result = await minimax_understand_image(
                str(image_path),
                prompt=(
                    "Describe this image for MAX in factual operational terms. "
                    "Mention visible objects, text, layout, materials, colors, and any business-relevant details. "
                    "Do not generate a new image."
                ),
            )
        except Exception as exc:
            return messages, self._safe_vision_error(str(exc)), None

        if not isinstance(result, dict) or not result.get("success"):
            return messages, self._safe_vision_error((result or {}).get("error") if isinstance(result, dict) else str(result)), result if isinstance(result, dict) else None

        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        description = (
            data.get("summary")
            or data.get("full_response")
            or data.get("text")
            or ""
        )
        description = str(description).strip()
        if not description:
            return messages, "MiniMax image understanding returned no verified description", result

        last = messages[-1]
        vision_context = (
            "[Image understanding via MiniMax mmx_cli]\n"
            f"File: {Path(image_filename or image_path.name).name}\n"
            "Transport: mmx_cli\n"
            "Quota bucket: mcp_understand_image\n"
            "Image generation used: false\n"
            "Instruction: Answer the user directly from the description. Do not narrate your thought process or use self-talk such as Wait, Actually, or Let me.\n"
            f"Description:\n{description}\n\n"
        )
        updated = list(messages)
        updated[-1] = AIMessage(role=last.role, content=vision_context + last.content, image_path=None)
        return updated, None, result

    def _encode_image(self, path: Path) -> tuple:
        ext = path.suffix.lower()
        media_types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp'}
        media_type = media_types.get(ext, 'image/png')
        with open(path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode('utf-8')
        return media_type, data

    def _prepare_messages(self, messages: List[AIMessage], image_path: Optional[Path] = None):
        """Prepare system message and API messages for Claude."""
        system_msg = ""
        api_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})
        if image_path and api_messages:
            media_type, image_data = self._encode_image(image_path)
            last_msg = api_messages[-1]
            api_messages[-1] = {
                "role": last_msg["role"],
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                    {"type": "text", "text": last_msg["content"]}
                ]
            }
        return system_msg, api_messages

    def _prepare_openai_messages(self, messages: List[AIMessage], image_path: Optional[Path] = None):
        """Prepare messages in OpenAI-compatible format (used by xAI Grok, OpenAI, Groq)."""
        api_messages = []
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        if image_path and api_messages:
            media_type, image_data = self._encode_image(image_path)
            last_msg = api_messages[-1]
            api_messages[-1] = {
                "role": last_msg["role"],
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                    {"type": "text", "text": last_msg["content"]}
                ]
            }
        return api_messages

    def _build_complexity_chain(self, complexity: TaskComplexity) -> list:
        """Build provider chain based on task complexity. Returns list of (provider_type, model_override) tuples.

        Routing policy (owner-defined):
        - MiniMax: PRIMARY when MAX_PRIMARY_PROVIDER=minimax and key is present
        - xAI Grok: SKIPPED when MAX_DISABLE_XAI=true (credits unavailable)
        - Gemini Flash: ONLY single-word greetings and vision tasks (SIMPLE)
        - Claude Sonnet: Analysis, quality writing, memory/search (COMPLEX)
        - Claude Opus: Code Mode only (CRITICAL)
        """
        providers_chain = []

        if complexity == TaskComplexity.SIMPLE:
            # SIMPLE: MiniMax -> Gemini FREE (greetings only) -> Grok -> Groq -> Sonnet
            if self.minimax_key:
                providers_chain.append(("minimax", None))
            if self.gemini_key:
                providers_chain.append(("gemini", None))
            if self.xai_key and not self.max_disable_xai:
                providers_chain.append(("grok", None))
            if self.groq_key:
                providers_chain.append(("groq", None))
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))

        elif complexity == TaskComplexity.MODERATE:
            # MODERATE: MiniMax PRIMARY -> Grok (if allowed) -> Groq -> Sonnet -> Gemini (last resort)
            if self.minimax_key:
                providers_chain.append(("minimax", None))
            if self.xai_key and not self.max_disable_xai:
                providers_chain.append(("grok", None))
            if self.groq_key:
                providers_chain.append(("groq", None))
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))
            if self.gemini_key:
                providers_chain.append(("gemini", None))

        elif complexity == TaskComplexity.COMPLEX:
            # COMPLEX: MiniMax PRIMARY -> Claude Sonnet -> Grok (if allowed) -> GPT-4o -> Groq
            if self.minimax_key:
                providers_chain.append(("minimax", None))
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))
            if self.xai_key and not self.max_disable_xai:
                providers_chain.append(("grok", None))
            if self.openai_key:
                providers_chain.append(("openai", "gpt-4o"))
            if self.groq_key:
                providers_chain.append(("groq", None))

        else:  # CRITICAL
            # CRITICAL: Claude Opus -> Sonnet -> stop
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-opus-4-6"))
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))

        return providers_chain

    # ── Non-streaming chat ──────────────────────────────────────────────

    def _log_chat_cost(self, messages: List[AIMessage], response: str, model: str, feature: str = "chat", business: str = "general", tenant_id: str = "founder"):
        """Log cost for a chat completion."""
        try:
            input_text = " ".join(m.content for m in messages if m.content)
            token_tracker.log_chat(model, input_text, response, feature=feature, business=business, source="ai_router", tenant_id=tenant_id)
        except Exception as e:
            logger.debug(f"Cost logging failed: {e}")

    async def _try_provider_chat(self, provider_type: str, model_override: Optional[str], full_messages: List[AIMessage], messages: List[AIMessage], image_path: Optional[Path], fallback: bool, feature: str, business: str, tenant_id: str, tools: Optional[list] = None) -> Optional[AIResponse]:
        """Try a single provider for non-streaming chat. Returns AIResponse on success, None on failure."""
        canonical = canonical_provider(provider_type)
        if canonical == "xai":
            provider_type = "grok"
        else:
            provider_type = canonical or provider_type
        try:
            if provider_type == "grok":
                logger.info(f"[MAX] Chat via xAI Grok ({self.xai_model}){' (fallback)' if fallback else ''}")
                resp = await self._grok_chat(full_messages, image_path, tools=tools)
                self._log_chat_cost(full_messages, resp.content, self.xai_model, feature, business, tenant_id)
                resp.fallback_used = fallback
                return resp

            elif provider_type == "claude":
                model_id = model_override or "claude-sonnet-4-6"
                logger.info(f"[MAX] Chat via Claude ({model_id}){' (fallback)' if fallback else ''}")
                resp = await self._claude_chat(full_messages, image_path, model_id=model_id)
                self._log_chat_cost(full_messages, resp, model_id, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=model_id, fallback_used=fallback)

            elif provider_type == "groq":
                logger.info(f"[MAX] Chat via Groq{' (fallback)' if fallback else ''}")
                resp = await self._groq_chat(full_messages)
                self._log_chat_cost(full_messages, resp, "groq-llama-3.3-70b", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="groq-llama-3.3-70b", fallback_used=fallback)

            elif provider_type == "gemini":
                logger.info(f"[MAX] Chat via Gemini 2.5 Flash{' (fallback)' if fallback else ''}")
                resp = await self._gemini_chat(full_messages, image_path)
                self._log_chat_cost(full_messages, resp, "gemini-2.5-flash", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gemini-2.5-flash", fallback_used=fallback)

            elif provider_type == "openai":
                oai_model = model_override or "gpt-4.1-nano"
                logger.info(f"[MAX] Chat via OpenAI ({oai_model}){' (fallback)' if fallback else ''}")
                resp = await self._openai_chat(full_messages, model=oai_model, image_path=image_path)
                self._log_chat_cost(full_messages, resp, oai_model, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=oai_model, fallback_used=fallback)

            elif provider_type == "deepseek":
                ds_model = model_override or self.deepseek_model
                logger.info(f"[MAX] Chat via DeepSeek ({ds_model}){' (fallback)' if fallback else ''}")
                resp = await self._deepseek_chat(full_messages, model=ds_model, image_path=image_path)
                self._log_chat_cost(full_messages, resp, ds_model, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=ds_model, fallback_used=fallback)

            elif provider_type == "qwen":
                q_model = model_override or self.qwen_model
                logger.info(f"[MAX] Chat via Qwen ({q_model}){' (fallback)' if fallback else ''}")
                resp = await self._qwen_chat(full_messages, model=q_model, image_path=image_path)
                self._log_chat_cost(full_messages, resp, q_model, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=q_model, fallback_used=fallback)

            elif provider_type == "openrouter":
                or_model = model_override or self.openrouter_model
                logger.info(f"[MAX] Chat via OpenRouter ({or_model}){' (fallback)' if fallback else ''}")
                resp = await self._openrouter_chat(full_messages, model=or_model, image_path=image_path)
                self._log_chat_cost(full_messages, resp, or_model, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=or_model, fallback_used=fallback)

            elif provider_type == "openclaw":
                logger.info(f"[MAX] Chat via OpenClaw{' (fallback)' if fallback else ''}")
                resp = await self._openclaw_chat(messages)
                self._log_chat_cost(messages, resp, "openclaw", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="openclaw", fallback_used=fallback)

            elif provider_type == "ollama":
                logger.info(f"[MAX] Chat via Ollama{' (fallback)' if fallback else ''}")
                resp = await self._ollama_chat(full_messages)
                self._log_chat_cost(full_messages, resp, "ollama-llama3.1", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="ollama-llama3.1", fallback_used=fallback)

            elif provider_type == "minimax":
                logger.info(f"[MAX] Chat via MiniMax ({self.minimax_model}){' (fallback)' if fallback else ''}")
                resp = await self._minimax_chat(full_messages, image_path=image_path)
                self._log_chat_cost(full_messages, resp, self.minimax_model, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=f"minimax-{self.minimax_model}", fallback_used=fallback)

        except Exception as e:
            logger.warning(f"{provider_type} failed: {type(e).__name__}: {e}")
            self._record_provider_error(canonical or provider_type, e)
        return None

    @staticmethod
    def _is_circuit_break_error(error_text: str | None) -> bool:
        text = (error_text or "").lower()
        return any(marker in text for marker in (" 401", "http 401", " 403", "http 403", " 429", "http 429", "quota"))

    def _selected_provider_candidates(self, state: RoutingState) -> list[tuple[str, str, bool]]:
        selected = canonical_provider(state.selected_provider)
        if selected not in CANONICAL_PROVIDERS:
            selected = "ollama"
        selected_model = (state.selected_model or "").strip() or provider_default_model(selected)

        chain: list[tuple[str, str, bool]] = [(selected, selected_model, False)]
        if not state.fallback_enabled:
            return chain

        for provider in CANONICAL_PROVIDERS:
            if provider == selected:
                continue
            chain.append((provider, provider_default_model(provider), True))
        return chain

    async def _chat_via_selected_routing(
        self,
        *,
        full_messages: List[AIMessage],
        messages: List[AIMessage],
        image_path: Optional[Path],
        feature: str,
        business: str,
        tenant_id: str,
        tools: Optional[list] = None,
    ) -> AIResponse:
        state = self._refresh_routing_state()
        candidates = self._selected_provider_candidates(state)
        attempted: list[str] = []
        blocked: list[str] = []

        for provider, model_name, fallback in candidates:
            reason = self._provider_disabled_reason(provider, state)
            if reason:
                blocked.append(f"{provider}:{reason}")
                continue

            attempted.append(provider)
            result = await self._try_provider_chat(
                provider,
                model_name,
                full_messages,
                messages,
                image_path,
                fallback,
                feature,
                business,
                tenant_id,
                tools=tools,
            )
            if result:
                self._record_provider_success(provider)
                return result

            error_text = self.last_provider_errors.get(provider) or self.last_provider_errors.get("grok" if provider == "xai" else provider)
            if self._is_circuit_break_error(error_text):
                return AIResponse(
                    content=(
                        f"Selected provider '{provider}' failed with a circuit-break error ({error_text or 'auth/quota'}) "
                        "so routing stopped without fallback. Fix provider auth/quota or switch provider."
                    ),
                    model_used=provider,
                    fallback_used=fallback,
                )
            if not state.fallback_enabled:
                return AIResponse(
                    content=(
                        f"Selected provider '{provider}' failed and fallback is disabled. "
                        "No other provider was called."
                    ),
                    model_used=provider,
                    fallback_used=False,
                )

        details = ", ".join(blocked) if blocked else "none"
        return AIResponse(
            content=(
                "No available provider could satisfy this request under current routing policy. "
                f"Attempted: {', '.join(attempted) if attempted else 'none'}. "
                f"Blocked: {details}."
            ),
            model_used="none",
            fallback_used=bool(state.fallback_enabled and len(attempted) > 1),
        )

    async def chat(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None, system_prompt: Optional[str] = None, tenant_id: str = "founder", source: str = "", conversation_id: str = "", tools: Optional[list] = None) -> AIResponse:
        # Per-desk model routing: if no explicit model requested and desk has a preferred model, use it
        if model is None and desk and desk in DESK_MODEL_ROUTING:
            use_model = DESK_MODEL_ROUTING[desk]
        else:
            use_model = model or self.primary_model
        prompt = system_prompt or (get_desk_system_prompt(desk) if desk else self.system_prompt)
        feature = "vision" if image_filename else ("chat" if not desk else "desk_task")
        business = desk or "general"

        image_path = None
        local_attachment_answer = None
        if image_filename:
            image_path, attachment_text = self._process_attachment(image_filename)
            if attachment_text and messages:
                last = messages[-1]
                messages = list(messages)
                messages[-1] = AIMessage(role=last.role, content=attachment_text + "\n\n" + last.content)
                local_attachment_answer = f"MAX read the attached file. Extracted context:\n{attachment_text[:1500]}"
            if image_path:
                messages, vision_error, _vision_result = await self._prepend_mmx_vision_context(messages, image_path, image_filename)
                if vision_error:
                    return AIResponse(
                        content=f"I could not analyze the image because MiniMax vision verification failed: {vision_error}",
                        model_used="mmx-vision",
                        fallback_used=False,
                    )
                image_path = None
            if local_attachment_answer and model is None and not desk:
                model_used = "attachment-reader"
                return AIResponse(content=local_attachment_answer, model_used=model_used, fallback_used=False)

        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        # Canonical selector authority: when no explicit model enum is requested,
        # route through persisted selected provider/model state.
        if model is None:
            return await self._chat_via_selected_routing(
                full_messages=full_messages,
                messages=messages,
                image_path=image_path,
                feature=feature,
                business=business,
                tenant_id=tenant_id,
                tools=tools,
            )

        # Complexity-based routing (only when no desk override and no explicit model)
        if model is None and not desk:
            complexity = classify_complexity(messages[-1].content if messages else "", source=source)
            complexity = apply_conversation_floor(conversation_id, complexity)
            logger.info(f"[MAX] Classified as {complexity.value}, using tiered chain")
            providers_chain = self._build_complexity_chain(complexity)

            is_first = True
            for provider_type, model_override in providers_chain:
                result = await self._try_provider_chat(provider_type, model_override, full_messages, messages, image_path, not is_first, feature, business, tenant_id, tools=tools)
                is_first = False
                if result:
                    return result

            # If tiered chain exhausted, fall through to legacy chain below
            logger.warning("[MAX] Tiered chain exhausted, falling through to legacy chain")
            if local_attachment_answer:
                model_used = "ollama-vision" if image_path else "attachment-reader"
                return AIResponse(content=local_attachment_answer, model_used=model_used, fallback_used=True)

        # Legacy fallback chain for desk routing / explicit model requests
        # Resolve Claude variants to the base CLAUDE provider for fallback chain
        # but track the specific model requested
        claude_model_id = "claude-sonnet-4-6"  # default Claude model
        if use_model == AIModel.CLAUDE_OPUS:
            claude_model_id = "claude-opus-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.CLAUDE_SONNET:
            claude_model_id = "claude-sonnet-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.GEMINI:
            # Desk requested Gemini
            try:
                logger.info("[MAX] Chat via Gemini 2.5 Flash (desk)")
                resp = await self._gemini_chat(full_messages, image_path)
                self._log_chat_cost(full_messages, resp, "gemini-2.5-flash", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gemini-2.5-flash", fallback_used=False)
            except Exception as e:
                logger.warning(f"Gemini failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ  # fallback
        elif use_model == AIModel.OPENAI_NANO:
            try:
                logger.info("[MAX] Chat via OpenAI (gpt-4.1-nano) (desk)")
                resp = await self._openai_chat(full_messages, model="gpt-4.1-nano", image_path=image_path)
                self._log_chat_cost(full_messages, resp, "gpt-4.1-nano", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gpt-4.1-nano", fallback_used=False)
            except Exception as e:
                logger.warning(f"OpenAI nano failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ
        elif use_model == AIModel.OPENAI_MINI:
            try:
                logger.info("[MAX] Chat via OpenAI (gpt-4o-mini) (desk)")
                resp = await self._openai_chat(full_messages, model="gpt-4o-mini", image_path=image_path)
                self._log_chat_cost(full_messages, resp, "gpt-4o-mini", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gpt-4o-mini", fallback_used=False)
            except Exception as e:
                logger.warning(f"OpenAI mini failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ
        elif use_model == AIModel.OPENAI_4O:
            try:
                logger.info("[MAX] Chat via OpenAI (gpt-4o) (desk)")
                resp = await self._openai_chat(full_messages, model="gpt-4o", image_path=image_path)
                self._log_chat_cost(full_messages, resp, "gpt-4o", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gpt-4o", fallback_used=False)
            except Exception as e:
                logger.warning(f"OpenAI 4o failed: {type(e).__name__}: {e}")
                use_model = AIModel.CLAUDE
        elif use_model == AIModel.MINIMAX:
            try:
                logger.info(f"[MAX] Chat via MiniMax ({self.minimax_model}) (desk)")
                resp = await self._minimax_chat(full_messages, image_path=image_path)
                self._log_chat_cost(full_messages, resp, self.minimax_model, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=f"minimax-{self.minimax_model}", fallback_used=False)
            except Exception as e:
                logger.warning(f"MiniMax failed: {type(e).__name__}: {e}")
                self._record_provider_error("minimax", e)
                use_model = AIModel.GROK  # fallback to Grok

        # Build ordered provider chain: requested model first, then full fallback
        # Chain: Grok -> Claude -> Groq -> OpenClaw -> Ollama
        all_providers = [AIModel.GROK, AIModel.CLAUDE, AIModel.GROQ, AIModel.OPENCLAW, AIModel.OLLAMA]
        providers = []
        for candidate in [use_model] + all_providers:
            if candidate in providers:
                continue
            if candidate == AIModel.GROK and (self.max_disable_xai or not self.xai_key):
                continue
            if candidate == AIModel.OLLAMA and self.max_disable_ollama:
                continue
            providers.append(candidate)

        is_first = True
        for provider in providers:
            fallback = not is_first
            is_first = False

            if provider == AIModel.GROK and self.xai_key:
                try:
                    logger.info(f"[MAX] Chat via xAI Grok ({self.xai_model}){' (fallback)' if fallback else ''}")
                    resp = await self._grok_chat(full_messages, image_path, tools=tools)
                    self._log_chat_cost(full_messages, resp.content, self.xai_model, feature, business, tenant_id)
                    resp.fallback_used = fallback
                    return resp
                except Exception as e:
                    logger.warning(f"Grok failed: {type(e).__name__}: {e}")
                    self._record_provider_error("grok", e)

            elif provider == AIModel.CLAUDE and self.anthropic_key:
                try:
                    logger.info(f"[MAX] Chat via Claude ({claude_model_id}){' (fallback)' if fallback else ''}")
                    resp = await self._claude_chat(full_messages, image_path, model_id=claude_model_id)
                    self._log_chat_cost(full_messages, resp, claude_model_id, feature, business, tenant_id)
                    return AIResponse(content=resp, model_used=claude_model_id, fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Claude failed: {type(e).__name__}: {e}")
                    self._record_provider_error("claude", e)

            elif provider == AIModel.GROQ and self.groq_key:
                try:
                    logger.info(f"[MAX] Chat via Groq{' (fallback)' if fallback else ''}")
                    resp = await self._groq_chat(full_messages)
                    self._log_chat_cost(full_messages, resp, "groq-llama-3.3-70b", feature, business, tenant_id)
                    return AIResponse(content=resp, model_used="groq-llama-3.3-70b", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Groq failed: {type(e).__name__}: {e}")
                    self._record_provider_error("groq", e)

            elif provider == AIModel.OPENCLAW:
                try:
                    logger.info(f"[MAX] Chat via OpenClaw{' (fallback)' if fallback else ''}")
                    resp = await self._openclaw_chat(messages)
                    self._log_chat_cost(messages, resp, "openclaw", feature, business, tenant_id)
                    return AIResponse(content=resp, model_used="openclaw", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"OpenClaw failed: {e}")
                    self._record_provider_error("openclaw", e)

            elif provider == AIModel.OLLAMA:
                try:
                    logger.info(f"[MAX] Chat via Ollama{' (fallback)' if fallback else ''}")
                    resp = await self._ollama_chat(full_messages)
                    self._log_chat_cost(full_messages, resp, "ollama-llama3.1", feature, business, tenant_id)
                    return AIResponse(content=resp, model_used="ollama-llama3.1", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Ollama failed: {e}")
                    self._record_provider_error("ollama", e)

        return AIResponse(content=self._provider_unavailable_message(), model_used="none", fallback_used=True)

    # ── Streaming chat ──────────────────────────────────────────────────

    async def chat_stream(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None, system_prompt: Optional[str] = None, tenant_id: str = "founder", source: str = "", conversation_id: str = "") -> AsyncGenerator[tuple[str, str], None]:
        # Per-desk model routing
        if model is None and desk and desk in DESK_MODEL_ROUTING:
            use_model = DESK_MODEL_ROUTING[desk]
        else:
            use_model = model or self.primary_model
        prompt = system_prompt or (get_desk_system_prompt(desk) if desk else self.system_prompt)
        feature = "vision" if image_filename else ("chat/stream" if not desk else "desk_task")
        business = desk or "general"

        image_path = None
        local_attachment_answer = None
        if image_filename:
            image_path, attachment_text = self._process_attachment(image_filename)
            if attachment_text and messages:
                last = messages[-1]
                messages = list(messages)
                messages[-1] = AIMessage(role=last.role, content=attachment_text + "\n\n" + last.content)
                local_attachment_answer = f"MAX read the attached file. Extracted context:\n{attachment_text[:1500]}"
            if image_path:
                messages, vision_error, _vision_result = await self._prepend_mmx_vision_context(messages, image_path, image_filename)
                if vision_error:
                    yield f"I could not analyze the image because MiniMax vision verification failed: {vision_error}", "mmx-vision"
                    return
                image_path = None
            if local_attachment_answer and model is None and not desk:
                yield local_attachment_answer, "attachment-reader"
                return

        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        # Keep stream route under the same authoritative selector policy by
        # resolving the response through canonical non-stream routing first.
        if model is None:
            selected = await self._chat_via_selected_routing(
                full_messages=full_messages,
                messages=messages,
                image_path=image_path,
                feature=feature,
                business=business,
                tenant_id=tenant_id,
                tools=None,
            )
            yield selected.content, selected.model_used
            return

        # Complexity-based routing (only when no desk override and no explicit model)
        if model is None and not desk:
            complexity = classify_complexity(messages[-1].content if messages else "", source=source)
            complexity = apply_conversation_floor(conversation_id, complexity)
            logger.info(f"[MAX] Stream classified as {complexity.value}, using tiered chain")
            providers_chain = self._build_complexity_chain(complexity)

            chain_exhausted = True
            is_first = True
            for provider_type, model_override in providers_chain:
                fallback = not is_first
                is_first = False
                try:
                    if provider_type == "grok":
                        logger.info(f"[MAX] Streaming via xAI Grok ({self.xai_model}){' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._grok_chat_stream(full_messages, image_path):
                            collected.append(chunk)
                            yield chunk, self.xai_model
                        self._log_chat_cost(full_messages, "".join(collected), self.xai_model, feature, business, tenant_id)
                        return

                    elif provider_type == "claude":
                        m_id = model_override or "claude-sonnet-4-6"
                        logger.info(f"[MAX] Streaming via Claude ({m_id}){' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._claude_chat_stream(full_messages, image_path, model_id=m_id):
                            collected.append(chunk)
                            yield chunk, m_id
                        self._log_chat_cost(full_messages, "".join(collected), m_id, feature, business, tenant_id)
                        return

                    elif provider_type == "groq":
                        logger.info(f"[MAX] Streaming via Groq{' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._groq_chat_stream(full_messages):
                            collected.append(chunk)
                            yield chunk, "groq-llama-3.3-70b"
                        self._log_chat_cost(full_messages, "".join(collected), "groq-llama-3.3-70b", feature, business, tenant_id)
                        return

                    elif provider_type == "gemini":
                        logger.info(f"[MAX] Streaming via Gemini 2.5 Flash{' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._gemini_chat_stream(full_messages, image_path):
                            collected.append(chunk)
                            yield chunk, "gemini-2.5-flash"
                        self._log_chat_cost(full_messages, "".join(collected), "gemini-2.5-flash", feature, business, tenant_id)
                        return

                    elif provider_type == "openai":
                        oai_model = model_override or "gpt-4.1-nano"
                        logger.info(f"[MAX] Streaming via OpenAI ({oai_model}){' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._openai_chat_stream(full_messages, model=oai_model, image_path=image_path):
                            collected.append(chunk)
                            yield chunk, oai_model
                        self._log_chat_cost(full_messages, "".join(collected), oai_model, feature, business, tenant_id)
                        return

                    elif provider_type == "minimax":
                        if image_path:
                            logger.info("[MAX] Skipping MiniMax for vision task (image not supported)")
                            raise Exception("MiniMax vision not supported")
                        logger.info(f"[MAX] Streaming via MiniMax ({self.minimax_model}){' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._minimax_chat_stream(full_messages, image_path=None):
                            collected.append(chunk)
                            yield chunk, self.minimax_model
                        self._log_chat_cost(full_messages, "".join(collected), self.minimax_model, feature, business, tenant_id)
                        return

                except Exception as e:
                    logger.warning(f"{provider_type} stream failed: {type(e).__name__}: {e}")
                    self._record_provider_error(provider_type, e)

            # If tiered chain exhausted, fall through to legacy chain
            logger.warning("[MAX] Tiered stream chain exhausted, falling through to legacy chain")
            if local_attachment_answer:
                yield local_attachment_answer, "attachment-reader"
                return

        # Legacy fallback chain for desk routing / explicit model requests
        # Resolve Claude variants
        claude_model_id = "claude-sonnet-4-6"
        if use_model == AIModel.CLAUDE_OPUS:
            claude_model_id = "claude-opus-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.CLAUDE_SONNET:
            claude_model_id = "claude-sonnet-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.GEMINI:
            try:
                logger.info("[MAX] Streaming via Gemini 2.5 Flash (desk)")
                collected = []
                async for chunk in self._gemini_chat_stream(full_messages, image_path):
                    collected.append(chunk)
                    yield chunk, "gemini-2.5-flash"
                self._log_chat_cost(full_messages, "".join(collected), "gemini-2.5-flash", feature, business, tenant_id)
                return
            except Exception as e:
                logger.warning(f"Gemini stream failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ
        elif use_model in (AIModel.OPENAI_NANO, AIModel.OPENAI_MINI, AIModel.OPENAI_4O):
            oai_model = use_model.value
            try:
                logger.info(f"[MAX] Streaming via OpenAI ({oai_model}) (desk)")
                collected = []
                async for chunk in self._openai_chat_stream(full_messages, model=oai_model, image_path=image_path):
                    collected.append(chunk)
                    yield chunk, oai_model
                self._log_chat_cost(full_messages, "".join(collected), oai_model, feature, business, tenant_id)
                return
            except Exception as e:
                logger.warning(f"OpenAI stream failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ
        elif use_model == AIModel.MINIMAX:
            try:
                logger.info(f"[MAX] Streaming via MiniMax ({self.minimax_model})")
                collected = []
                async for chunk in self._minimax_chat_stream(full_messages, image_path=image_path):
                    collected.append(chunk)
                    yield chunk, self.minimax_model
                self._log_chat_cost(full_messages, "".join(collected), self.minimax_model, feature, business, tenant_id)
                return
            except Exception as e:
                logger.warning(f"MiniMax stream failed: {type(e).__name__}: {e}")
                self._record_provider_error("minimax", e)
                use_model = AIModel.GROK

        # Build ordered provider chain: requested model first, then full fallback
        all_providers = [AIModel.GROK, AIModel.CLAUDE, AIModel.GROQ, AIModel.OPENCLAW, AIModel.OLLAMA]
        providers = []
        for candidate in [use_model] + all_providers:
            if candidate in providers:
                continue
            if candidate == AIModel.GROK and (self.max_disable_xai or not self.xai_key):
                continue
            if candidate == AIModel.OLLAMA and self.max_disable_ollama:
                continue
            providers.append(candidate)

        for provider in providers:
            if provider == AIModel.GROK and self.xai_key:
                try:
                    logger.info(f"[MAX] Streaming via xAI Grok ({self.xai_model})")
                    collected = []
                    async for chunk in self._grok_chat_stream(full_messages, image_path):
                        collected.append(chunk)
                        yield chunk, self.xai_model
                    self._log_chat_cost(full_messages, "".join(collected), self.xai_model, feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Grok stream failed: {e}")
                    self._record_provider_error("grok", e)

            elif provider == AIModel.CLAUDE and self.anthropic_key:
                try:
                    logger.info(f"[MAX] Streaming via Claude ({claude_model_id})")
                    collected = []
                    async for chunk in self._claude_chat_stream(full_messages, image_path, model_id=claude_model_id):
                        collected.append(chunk)
                        yield chunk, claude_model_id
                    self._log_chat_cost(full_messages, "".join(collected), claude_model_id, feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Claude stream failed: {e}")
                    self._record_provider_error("claude", e)

            elif provider == AIModel.GROQ and self.groq_key:
                try:
                    logger.info("[MAX] Streaming via Groq")
                    collected = []
                    async for chunk in self._groq_chat_stream(full_messages):
                        collected.append(chunk)
                        yield chunk, "groq-llama-3.3-70b"
                    self._log_chat_cost(full_messages, "".join(collected), "groq-llama-3.3-70b", feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Groq stream failed: {e}")
                    self._record_provider_error("groq", e)

            elif provider == AIModel.OPENCLAW:
                try:
                    logger.info("[MAX] Streaming via OpenClaw")
                    resp = await self._openclaw_chat(messages)
                    self._log_chat_cost(messages, resp, "openclaw", feature, business, tenant_id)
                    yield resp, "openclaw"
                    return
                except Exception as e:
                    logger.warning(f"OpenClaw stream failed: {e}")
                    self._record_provider_error("openclaw", e)

            elif provider == AIModel.OLLAMA:
                try:
                    logger.info("[MAX] Streaming via Ollama")
                    collected = []
                    async for chunk in self._ollama_chat_stream(full_messages):
                        collected.append(chunk)
                        yield chunk, "ollama-llama3.1"
                    self._log_chat_cost(full_messages, "".join(collected), "ollama-llama3.1", feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Ollama stream failed: {e}")
                    self._record_provider_error("ollama", e)

        yield self._provider_unavailable_message(), "error"

    # ── xAI Grok (OpenAI-compatible API) ──────────────────────────────

    def _xai_payload(self, api_messages: list, *, stream: bool = False) -> dict:
        """Build the minimal xAI-compatible chat payload for /v1/chat/completions.

        Keep provider-specific fields out of this path. xAI rejects several
        common OpenAI/Anthropic-style extras on reasoning models, including
        stop, presencePenalty, frequencyPenalty, reasoning_effort, and logprobs.
        """
        payload = {
            "model": self.xai_model,
            "messages": api_messages,
            "max_tokens": self.xai_max_tokens,
        }
        if stream:
            payload["stream"] = True
        return payload

    def _xai_responses_payload(self, api_messages: list, tools: list) -> dict:
        """Build xAI /v1/responses payload (native function calling endpoint).

        xAI /v1/responses uses input[] array (not messages[]) and a flat tool
        structure: {type, name, description, parameters} (not nested under 'function').
        """
        # Build input array from api_messages
        input_array = []
        for msg in api_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Multimodal content — handle text parts
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                content = " ".join(text_parts)
            input_array.append({"role": role, "content": content})

        payload = {
            "model": self.xai_model,
            "input": input_array,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": self.xai_max_tokens,
        }
        return payload

    async def _grok_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None, tools: Optional[list] = None) -> AIResponse:
        """Call xAI. When tools are provided, uses /v1/responses endpoint (which supports
        function calling) and returns AIResponse with function_calls populated.
        Otherwise uses /v1/chat/completions and returns AIResponse with content only."""
        from .tool_executor import parse_xai_function_calls

        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tools:
                # /v1/responses — xAI-native function calling
                resp = await client.post(
                    f"{self.xai_base_url}/responses",
                    headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                    json=self._xai_responses_payload(api_messages, tools)
                )
                if resp.status_code != 200:
                    raise Exception(f"xAI responses HTTP {resp.status_code} model={self.xai_model}: {resp.text}")
                data = resp.json()
                function_calls = parse_xai_function_calls(data)

                # Extract text output
                text_output = ""
                for item in data.get("output", []):
                    if item.get("type") == "message":
                        text_output = "".join(
                            p.get("text", "") for p in item.get("content", [])
                            if isinstance(p, dict)
                        )
                        break

                return AIResponse(content=text_output, model_used=self.xai_model, function_calls=function_calls if function_calls else None)
            else:
                # /v1/chat/completions — plain text
                resp = await client.post(
                    f"{self.xai_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                    json=self._xai_payload(api_messages)
                )
                if resp.status_code != 200:
                    raise Exception(f"xAI HTTP {resp.status_code} model={self.xai_model} base_url={self.xai_base_url}: {resp.text}")
                return AIResponse(content=resp.json()["choices"][0]["message"]["content"], model_used=self.xai_model)

    async def _grok_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.xai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                json=self._xai_payload(api_messages, stream=True)
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"xAI HTTP {response.status_code} model={self.xai_model} base_url={self.xai_base_url}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    # ── Claude (Anthropic API) ────────────────────────────────────────

    async def _claude_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None, model_id: str = "claude-sonnet-4-6") -> str:
        system_msg, api_messages = self._prepare_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": model_id, "max_tokens": 8192, "system": system_msg, "messages": api_messages}
            )
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json().get("content", [{}])[0].get("text", "No response")

    async def _claude_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None, model_id: str = "claude-sonnet-4-6") -> AsyncGenerator[str, None]:
        system_msg, api_messages = self._prepare_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": model_id, "max_tokens": 8192, "stream": True, "system": system_msg, "messages": api_messages}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"HTTP {response.status_code}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "content_block_delta":
                        text = data.get("delta", {}).get("text", "")
                        if text:
                            yield text
                    elif data.get("type") == "message_stop":
                        return

    # ── Groq (OpenAI-compatible, Llama 3.3 70B) ──────────────────────

    async def _groq_chat(self, messages: List[AIMessage]) -> str:
        api_messages = self._prepare_openai_messages(messages)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": api_messages, "max_tokens": 2048}
            )
            if resp.status_code != 200:
                raise Exception(f"Groq HTTP {resp.status_code}: {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _groq_chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        api_messages = self._prepare_openai_messages(messages)
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": api_messages, "max_tokens": 2048, "stream": True}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"Groq HTTP {response.status_code}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    # ── Google Gemini (REST API, 2.5 Flash) ───────────────────────────

    async def _gemini_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        """Chat via Google Gemini 2.5 Flash (free tier)."""
        contents = []
        for msg in messages:
            role = "user" if msg.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        # Add image if present
        if image_path and contents:
            media_type, image_data = self._encode_image(image_path)
            contents[-1]["parts"].insert(0, {
                "inline_data": {"mime_type": media_type, "data": image_data}
            })

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}",
                json={"contents": contents, "generationConfig": {"maxOutputTokens": 4096}}
            )
            if resp.status_code == 429:
                raise Exception("Gemini rate limited (429)")
            if resp.status_code != 200:
                raise Exception(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return "No response from Gemini"

    async def _gemini_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        """Stream chat via Google Gemini 2.5 Flash."""
        contents = []
        for msg in messages:
            role = "user" if msg.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        if image_path and contents:
            media_type, image_data = self._encode_image(image_path)
            contents[-1]["parts"].insert(0, {
                "inline_data": {"mime_type": media_type, "data": image_data}
            })

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={self.gemini_key}",
                json={"contents": contents, "generationConfig": {"maxOutputTokens": 4096}}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"Gemini HTTP {response.status_code}: {error_body.decode()[:200]}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        if text:
                            yield text

    # ── Generic OpenAI-compatible providers ──────────────────────────

    async def _openai_compatible_chat(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[AIMessage],
        image_path: Optional[Path] = None,
        timeout: float = 45.0,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> str:
        api_messages = self._prepare_openai_messages(messages, image_path)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={"model": model, "messages": api_messages, "max_tokens": 4096},
            )
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _openai_compatible_chat_stream(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[AIMessage],
        image_path: Optional[Path] = None,
        timeout: float = 45.0,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        api_messages = self._prepare_openai_messages(messages, image_path)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json={"model": model, "messages": api_messages, "max_tokens": 4096, "stream": True},
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"HTTP {response.status_code}: {error_body.decode()[:300]}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    async def _deepseek_chat(self, messages: List[AIMessage], model: str, image_path: Optional[Path] = None) -> str:
        return await self._openai_compatible_chat(
            base_url=self.deepseek_base_url,
            api_key=self.deepseek_key,
            model=model,
            messages=messages,
            image_path=image_path,
            timeout=60.0,
        )

    async def _deepseek_chat_stream(self, messages: List[AIMessage], model: str, image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        async for chunk in self._openai_compatible_chat_stream(
            base_url=self.deepseek_base_url,
            api_key=self.deepseek_key,
            model=model,
            messages=messages,
            image_path=image_path,
            timeout=60.0,
        ):
            yield chunk

    async def _qwen_chat(self, messages: List[AIMessage], model: str, image_path: Optional[Path] = None) -> str:
        return await self._openai_compatible_chat(
            base_url=self.qwen_base_url,
            api_key=self.qwen_key,
            model=model,
            messages=messages,
            image_path=image_path,
            timeout=60.0,
        )

    async def _qwen_chat_stream(self, messages: List[AIMessage], model: str, image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        async for chunk in self._openai_compatible_chat_stream(
            base_url=self.qwen_base_url,
            api_key=self.qwen_key,
            model=model,
            messages=messages,
            image_path=image_path,
            timeout=60.0,
        ):
            yield chunk

    async def _openrouter_chat(self, messages: List[AIMessage], model: str, image_path: Optional[Path] = None) -> str:
        extra_headers = {
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://empirebox.local"),
            "X-Title": os.getenv("OPENROUTER_TITLE", "EmpireBox MAX"),
        }
        return await self._openai_compatible_chat(
            base_url=self.openrouter_base_url,
            api_key=self.openrouter_key,
            model=model,
            messages=messages,
            image_path=image_path,
            timeout=60.0,
            extra_headers=extra_headers,
        )

    async def _openrouter_chat_stream(self, messages: List[AIMessage], model: str, image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        extra_headers = {
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://empirebox.local"),
            "X-Title": os.getenv("OPENROUTER_TITLE", "EmpireBox MAX"),
        }
        async for chunk in self._openai_compatible_chat_stream(
            base_url=self.openrouter_base_url,
            api_key=self.openrouter_key,
            model=model,
            messages=messages,
            image_path=image_path,
            timeout=60.0,
            extra_headers=extra_headers,
        ):
            yield chunk

    # ── OpenAI API ────────────────────────────────────────────────────

    async def _openai_chat(self, messages: List[AIMessage], model: str = "gpt-4.1-nano", image_path: Optional[Path] = None) -> str:
        """Chat via OpenAI API."""
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": api_messages, "max_tokens": 4096}
            )
            if resp.status_code != 200:
                raise Exception(f"OpenAI HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _openai_chat_stream(self, messages: List[AIMessage], model: str = "gpt-4.1-nano", image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        """Stream chat via OpenAI API."""
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": api_messages, "max_tokens": 4096, "stream": True}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"OpenAI HTTP {response.status_code}: {error_body.decode()[:200]}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    # ── MiniMax ───────────────────────────────────────────────────────

    async def _minimax_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        """Chat via MiniMax M1 API."""
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{self.minimax_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.minimax_key}", "Content-Type": "application/json"},
                json={"model": self.minimax_model, "messages": api_messages, "max_tokens": 4096}
            )
            if resp.status_code != 200:
                raise Exception(f"MiniMax HTTP {resp.status_code}: {resp.text[:200]}")
            self._record_provider_success("minimax")
            return self._sanitize_minimax_content(resp.json()["choices"][0]["message"]["content"])

    async def _minimax_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        """Stream chat via MiniMax M1 API."""
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream(
                "POST",
                f"{self.minimax_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.minimax_key}", "Content-Type": "application/json"},
                json={"model": self.minimax_model, "messages": api_messages, "max_tokens": 4096, "stream": True}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"MiniMax HTTP {response.status_code}: {error_body.decode()[:200]}")
                self._record_provider_success("minimax")
                collected = []
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        collected.append(text)
                cleaned = self._sanitize_minimax_content("".join(collected))
                if cleaned:
                    yield cleaned

    # ── OpenClaw ──────────────────────────────────────────────────────

    async def _openclaw_chat(self, messages: List[AIMessage]) -> str:
        last_user_msg = ""
        history = []
        for msg in messages:
            if msg.role == "user":
                last_user_msg = msg.content
            history.append({"role": msg.role, "content": msg.content})

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "http://localhost:7878/chat",
                json={"message": last_user_msg, "history": history[:-1], "system_prompt": self.system_prompt},
            )
            if resp.status_code != 200:
                raise Exception(f"OpenClaw HTTP {resp.status_code}: {resp.text}")
            return resp.json().get("response", "No response from OpenClaw")

    # ── Ollama ────────────────────────────────────────────────────────

    async def _ollama_chat(self, messages: List[AIMessage]) -> str:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
            return resp.json().get("response", "No response")

    async def _ollama_chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = data.get("response", "")
                    if text:
                        yield text
                    if data.get("done", False):
                        return

ai_router = AIRouter()
