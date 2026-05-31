"""Canonical MAX AI routing state and provider registry helpers."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.data_paths import data_root

CANONICAL_PROVIDERS: tuple[str, ...] = (
    "minimax",
    "deepseek",
    "qwen",
    "openrouter",
    "groq",
    "claude",
    "openai",
    "gemini",
    "xai",
    "ollama",
    "openclaw",
)

PROVIDER_ALIASES: dict[str, str] = {
    "grok": "xai",
    "x-ai": "xai",
    "anthropic": "claude",
    "anthropic-claude": "claude",
    "google": "gemini",
    "google-gemini": "gemini",
    "chatgpt": "openai",
    "open-ai": "openai",
    "local": "ollama",
}

PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "minimax": "MiniMax",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "claude": "Claude",
    "openai": "OpenAI",
    "gemini": "Gemini",
    "xai": "xAI / Grok",
    "ollama": "Ollama",
    "openclaw": "OpenClaw",
}

PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "minimax": "MiniMax-M2.7",
    "deepseek": "deepseek-v4-flash",
    "qwen": "qwen-plus",
    "openrouter": "openai/gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "claude": "claude-sonnet-4-6",
    "openai": "gpt-4.1-nano",
    "gemini": "gemini-2.5-flash",
    "xai": "grok-4-fast-non-reasoning",
    "ollama": "llama3.1:8b",
    "openclaw": "openclaw",
}

PROVIDER_MODEL_ENV: dict[str, str] = {
    "minimax": "MINIMAX_MODEL",
    "deepseek": "DEEPSEEK_MODEL",
    "qwen": "QWEN_MODEL",
    "openrouter": "OPENROUTER_MODEL",
    "groq": "GROQ_MODEL",
    "claude": "CLAUDE_MODEL",
    "openai": "OPENAI_MODEL",
    "gemini": "GEMINI_MODEL",
    "xai": "XAI_MODEL",
    "ollama": "OLLAMA_MODEL",
    "openclaw": "OPENCLAW_MODEL",
}

PROVIDER_KEY_ENV: dict[str, str] = {
    "minimax": "MINIMAX_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "QWEN_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_GEMINI_API_KEY",
    "xai": "XAI_API_KEY",
    "ollama": "",
    "openclaw": "",
}

PROVIDER_DISABLE_ENV: dict[str, str] = {
    "minimax": "MAX_DISABLE_MINIMAX",
    "deepseek": "MAX_DISABLE_DEEPSEEK",
    "qwen": "MAX_DISABLE_QWEN",
    "openrouter": "MAX_DISABLE_OPENROUTER",
    "groq": "MAX_DISABLE_GROQ",
    "claude": "MAX_DISABLE_CLAUDE",
    "openai": "MAX_DISABLE_OPENAI",
    "gemini": "MAX_DISABLE_GEMINI",
    "xai": "MAX_DISABLE_XAI",
    "ollama": "MAX_DISABLE_OLLAMA",
    "openclaw": "MAX_DISABLE_OPENCLAW",
}

CLOUD_PROVIDERS: set[str] = {
    "minimax",
    "deepseek",
    "qwen",
    "openrouter",
    "groq",
    "claude",
    "openai",
    "gemini",
    "xai",
}

KNOWN_MODELS: dict[str, list[str]] = {
    "minimax": ["MiniMax-M2.7"],
    "deepseek": ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"],
    "qwen": ["qwen-plus", "qwen-max", "qwen-turbo"],
    "openrouter": ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    "claude": ["claude-sonnet-4-6", "claude-opus-4-6"],
    "openai": ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4o"],
    "gemini": ["gemini-2.5-flash"],
    "xai": ["grok-4-fast-non-reasoning"],
    "ollama": ["llama3.1:8b"],
    "openclaw": ["openclaw"],
}


def _state_path() -> Path:
    return data_root() / "max" / "ai_routing_state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def canonical_provider(provider: str | None) -> str:
    key = (provider or "").strip().lower()
    if not key:
        return ""
    if key in CANONICAL_PROVIDERS:
        return key
    return PROVIDER_ALIASES.get(key, key)


def provider_is_cloud(provider: str) -> bool:
    return canonical_provider(provider) in CLOUD_PROVIDERS


def provider_disable_env(provider: str) -> str:
    canonical = canonical_provider(provider)
    return PROVIDER_DISABLE_ENV.get(canonical, "")


def provider_disabled(provider: str) -> bool:
    env_name = provider_disable_env(provider)
    if not env_name:
        return False
    return env_flag(env_name, False)


def provider_key_env(provider: str) -> str:
    canonical = canonical_provider(provider)
    return PROVIDER_KEY_ENV.get(canonical, "")


def provider_model_env(provider: str) -> str:
    canonical = canonical_provider(provider)
    return PROVIDER_MODEL_ENV.get(canonical, "")


def provider_default_model(provider: str) -> str:
    canonical = canonical_provider(provider)
    return PROVIDER_DEFAULT_MODELS.get(canonical, "unknown-model")


def provider_model_choices(provider: str) -> list[str]:
    canonical = canonical_provider(provider)
    choices = list(KNOWN_MODELS.get(canonical, []))
    env_model = (os.getenv(provider_model_env(canonical), "") or "").strip()
    if env_model and env_model not in choices:
        choices.insert(0, env_model)
    env_models = os.getenv(f"MAX_MODELS_{canonical.upper()}", "").strip()
    if env_models:
        for model in [item.strip() for item in env_models.split(",") if item.strip()]:
            if model not in choices:
                choices.append(model)
    if not choices:
        choices = [provider_default_model(canonical)]
    return choices


def provider_configured(provider: str) -> bool:
    canonical = canonical_provider(provider)
    key_env = provider_key_env(canonical)
    if not key_env:
        return True
    return bool((os.getenv(key_env, "") or "").strip())


def _preferred_provider_order() -> list[str]:
    order = [canonical_provider(os.getenv("MAX_PRIMARY_PROVIDER", ""))]
    order.extend(list(CANONICAL_PROVIDERS))
    normalized: list[str] = []
    for provider in order:
        if provider and provider in CANONICAL_PROVIDERS and provider not in normalized:
            normalized.append(provider)
    return normalized


def _default_selected_provider() -> str:
    for provider in _preferred_provider_order():
        if provider_disabled(provider):
            continue
        if provider_configured(provider):
            return provider
    return "ollama"


@dataclass
class RoutingState:
    selected_provider: str
    selected_model: str
    fallback_enabled: bool
    ai_calls_disabled: bool
    lane: str
    updated_at: str
    updated_by: str
    last_switch_reason: str
    manual_disabled: dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _default_state() -> RoutingState:
    provider = _default_selected_provider()
    model = provider_default_model(provider)
    env_model = (os.getenv(provider_model_env(provider), "") or "").strip()
    if env_model:
        model = env_model
    return RoutingState(
        selected_provider=provider,
        selected_model=model,
        fallback_enabled=env_flag("MAX_ALLOW_FALLBACK", False),
        ai_calls_disabled=env_flag("AI_CALLS_DISABLED", False),
        lane=os.getenv("EMPIRE_LANE", "stable/main"),
        updated_at=_now_iso(),
        updated_by="system",
        last_switch_reason="bootstrap_default",
        manual_disabled={},
    )


def _normalize_loaded_state(raw: dict[str, Any], fallback: RoutingState) -> RoutingState:
    provider = canonical_provider(str(raw.get("selected_provider", fallback.selected_provider)))
    if provider not in CANONICAL_PROVIDERS:
        provider = fallback.selected_provider

    model = str(raw.get("selected_model", fallback.selected_model) or "").strip()
    if not model:
        model = provider_default_model(provider)

    manual_disabled_raw = raw.get("manual_disabled", {}) if isinstance(raw, dict) else {}
    manual_disabled: dict[str, bool] = {}
    if isinstance(manual_disabled_raw, dict):
        for provider_name, disabled in manual_disabled_raw.items():
            canonical = canonical_provider(str(provider_name))
            if canonical in CANONICAL_PROVIDERS:
                manual_disabled[canonical] = bool(disabled)

    return RoutingState(
        selected_provider=provider,
        selected_model=model,
        fallback_enabled=bool(raw.get("fallback_enabled", fallback.fallback_enabled)),
        ai_calls_disabled=bool(raw.get("ai_calls_disabled", fallback.ai_calls_disabled)),
        lane=str(raw.get("lane", fallback.lane) or fallback.lane),
        updated_at=str(raw.get("updated_at", fallback.updated_at) or fallback.updated_at),
        updated_by=str(raw.get("updated_by", fallback.updated_by) or fallback.updated_by),
        last_switch_reason=str(raw.get("last_switch_reason", fallback.last_switch_reason) or fallback.last_switch_reason),
        manual_disabled=manual_disabled,
    )


def _apply_env_overrides(state: RoutingState) -> RoutingState:
    selected_provider_env = canonical_provider(os.getenv("MAX_SELECTED_PROVIDER", ""))
    if selected_provider_env in CANONICAL_PROVIDERS:
        state.selected_provider = selected_provider_env
        state.selected_model = (os.getenv("MAX_SELECTED_MODEL", "") or "").strip() or provider_default_model(selected_provider_env)
        state.last_switch_reason = "env_override(MAX_SELECTED_PROVIDER)"
        state.updated_by = "system_env"
        state.updated_at = _now_iso()
    elif os.getenv("MAX_SELECTED_MODEL"):
        state.selected_model = (os.getenv("MAX_SELECTED_MODEL", "") or "").strip() or state.selected_model
        state.last_switch_reason = "env_override(MAX_SELECTED_MODEL)"
        state.updated_by = "system_env"
        state.updated_at = _now_iso()

    if os.getenv("MAX_ALLOW_FALLBACK") is not None:
        state.fallback_enabled = env_flag("MAX_ALLOW_FALLBACK", state.fallback_enabled)

    if os.getenv("AI_CALLS_DISABLED") is not None:
        state.ai_calls_disabled = env_flag("AI_CALLS_DISABLED", state.ai_calls_disabled)

    if os.getenv("EMPIRE_LANE"):
        state.lane = os.getenv("EMPIRE_LANE", state.lane) or state.lane

    return state


def load_routing_state() -> RoutingState:
    path = _state_path()
    default = _default_state()
    if not path.exists():
        return _apply_env_overrides(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _apply_env_overrides(default)
    return _apply_env_overrides(_normalize_loaded_state(payload, default))


def save_routing_state(state: RoutingState) -> RoutingState:
    state.selected_provider = canonical_provider(state.selected_provider) or _default_selected_provider()
    if state.selected_provider not in CANONICAL_PROVIDERS:
        state.selected_provider = _default_selected_provider()
    if not state.selected_model:
        state.selected_model = provider_default_model(state.selected_provider)
    normalized_manual: dict[str, bool] = {}
    for provider_name, disabled in (state.manual_disabled or {}).items():
        canonical = canonical_provider(provider_name)
        if canonical in CANONICAL_PROVIDERS and bool(disabled):
            normalized_manual[canonical] = True
    state.manual_disabled = normalized_manual
    state.updated_at = _now_iso()
    state.lane = state.lane or os.getenv("EMPIRE_LANE", "stable/main")

    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)
    return state


def update_routing_state(
    *,
    selected_provider: str | None = None,
    selected_model: str | None = None,
    fallback_enabled: bool | None = None,
    ai_calls_disabled: bool | None = None,
    manual_disabled: dict[str, bool] | None = None,
    updated_by: str = "system",
    last_switch_reason: str = "manual_update",
) -> RoutingState:
    state = load_routing_state()
    if selected_provider is not None:
        provider = canonical_provider(selected_provider)
        if provider in CANONICAL_PROVIDERS:
            state.selected_provider = provider
            if selected_model is None:
                state.selected_model = provider_default_model(provider)
    if selected_model is not None:
        state.selected_model = (selected_model or "").strip() or provider_default_model(state.selected_provider)
    if fallback_enabled is not None:
        state.fallback_enabled = bool(fallback_enabled)
    if ai_calls_disabled is not None:
        state.ai_calls_disabled = bool(ai_calls_disabled)
    if manual_disabled is not None:
        state.manual_disabled = dict(manual_disabled)
    state.updated_by = updated_by
    state.last_switch_reason = last_switch_reason
    return save_routing_state(state)


def provider_label(provider: str) -> str:
    canonical = canonical_provider(provider)
    return PROVIDER_DISPLAY_NAMES.get(canonical, canonical.title() if canonical else "Unknown")


def provider_manually_disabled(state: RoutingState, provider: str) -> bool:
    canonical = canonical_provider(provider)
    if not canonical:
        return False
    return bool((state.manual_disabled or {}).get(canonical, False))


def provider_effectively_disabled(state: RoutingState, provider: str) -> bool:
    return provider_disabled(provider) or provider_manually_disabled(state, provider)
