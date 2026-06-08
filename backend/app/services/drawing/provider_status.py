"""Provider status checks for drawing routes.

The drawing subsystem has a small number of external AI dependencies:

  - XAI_API_KEY  — used by /drawings/analyze-sketch (xAI Grok vision)
  - ANTHROPIC_API_KEY — used by /drawings/ai/project-sheet (Claude Sonnet draftsman)
  - OPENAI_API_KEY  — fallback for /drawings/ai/project-sheet (GPT-4o draftsman)

These helpers give routers a single, truthful place to ask "is provider X
configured right now?" so the route can return a 503 with a clear reason
instead of crashing with 500 when the underlying HTTP call fails.

Important: these helpers are advisory. A non-empty env var does NOT mean the
key is valid or that the upstream service is healthy. The router still
performs the actual call and may surface provider-specific errors. The
helpers exist so the *first* failure mode is "no key configured" (503) and
not "KeyError: 'XAI_API_KEY'" or "HTTPException 500 from httpx".

This module is intentionally stdlib-only.
"""

from __future__ import annotations

import os
from typing import Optional


def _truthy_env(name: str) -> bool:
    """A provider is considered 'configured' if its env var is non-empty.

    We do not validate the key, hit the network, or open any file.
    """
    val = os.getenv(name, "")
    return bool(val and val.strip())


def xai_configured() -> bool:
    return _truthy_env("XAI_API_KEY")


def anthropic_configured() -> bool:
    return _truthy_env("ANTHROPIC_API_KEY")


def openai_configured() -> bool:
    return _truthy_env("OPENAI_API_KEY")


def draftsman_providers_configured() -> list[str]:
    """Return the list of provider names that have keys configured.

    Used by the AI draftsman routes to know which providers to try in order.
    Returns the configured subset of ["anthropic", "openai"] in the same
    priority order as app.services.drawing.ai_draftsman.call_draftsman.
    """
    providers = []
    if anthropic_configured():
        providers.append("anthropic")
    if openai_configured():
        providers.append("openai")
    return providers


def vision_providers_configured() -> list[str]:
    """Return the list of vision provider names that have keys configured.

    Used by the multi-item furniture analyzer to know which providers to try.
    Returns the configured subset of ["grok", "claude"].
    """
    providers = []
    if xai_configured():
        providers.append("grok")
    if anthropic_configured():
        providers.append("claude")
    return providers


def unavailable_reason(provider: str) -> str:
    """Return a human-readable reason a provider is unavailable.

    Always safe to expose — no secret values, just env-var names and
    a generic "not configured" message.
    """
    mapping = {
        "xai": ("XAI_API_KEY", "xAI Grok vision is not configured"),
        "grok": ("XAI_API_KEY", "xAI Grok vision is not configured"),
        "anthropic": ("ANTHROPIC_API_KEY", "Claude is not configured"),
        "claude": ("ANTHROPIC_API_KEY", "Claude vision is not configured"),
        "openai": ("OPENAI_API_KEY", "OpenAI is not configured"),
    }
    if provider not in mapping:
        return f"Provider {provider!r} is not configured"
    env_name, friendly = mapping[provider]
    return f"{friendly} (env: {env_name})"


def all_unavailable(providers: list[str]) -> Optional[str]:
    """If every provider in the list is unconfigured, return a 503 reason.

    Returns None if at least one provider is configured. The returned string
    joins the per-provider reasons with ' and '.
    """
    if not providers:
        return "no AI providers requested"
    unavailable = [p for p in providers if not _provider_configured(p)]
    if len(unavailable) != len(providers):
        return None
    return " and ".join(unavailable_reason(p) for p in providers)


def _provider_configured(provider: str) -> bool:
    if provider in ("xai", "grok"):
        return xai_configured()
    if provider in ("anthropic", "claude"):
        return anthropic_configured()
    if provider == "openai":
        return openai_configured()
    return False
