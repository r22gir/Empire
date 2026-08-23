"""R9 regression guards for the openclaw model-name leak (R8 defect #2).

Three structural guards so the bug class — "provider id leaked into the model
field" — cannot recur silently:

1. `test_no_self_id_in_provider_defaults` — iterates `PROVIDER_DEFAULT_MODELS`
   and `KNOWN_MODELS`; asserts no provider's default model or known-model list
   contains the provider id. The structural assertion catches the class of bug
   for any provider, present or future, not just openclaw.

2. `test_no_openclaw_model_literal_in_codepaths` — scans the four files that
   emitted the leak (ai_router.py, code_task_runner.py, evaluation_service.py,
   token_tracker.py) for the literal "openclaw" used as a MODEL value (regex
   around model_used=, startswith("openclaw"), "openclaw" in model,
   MODEL_PROVIDER_HINTS["openclaw"]). Fails on any hit.

3. `test_wrapper_delegate_present_in_pricing_tiers` — for each wrapper
   provider, resolve the inner delegate and assert it appears in at least one
   tier's `allowed_models`. Surfaces the entitlement break in the suite, not in
   production. Skips (not fails) when the wrapper's env is unconfigured in CI.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from app.config.pricing_tiers import PRICING_TIERS
from app.services.max.routing_state import (
    KNOWN_MODELS,
    PROVIDER_DEFAULT_MODELS,
    openclaw_inner_model,
)

# Files that previously emitted the "openclaw" model-value leak. The scan
# guards the four known sites; new files MUST be added here if they ever emit
# the same pattern.
LEAK_SCAN_FILES = (
    "app/services/max/ai_router.py",
    "app/services/max/code_task_runner.py",
    "app/services/max/evaluation_service.py",
    "app/services/max/token_tracker.py",
)

# Regex matches the literal "openclaw" used as a MODEL value, not as a
# service identifier. The patterns are deliberately narrow — service-name
# uses (e.g. `provider == "openclaw"`, `AIModel.OPENCLAW`, log tags, allowed
# process names) are correct and must NOT trigger the guard. The fix uses
# `openclaw_inner_model()` and returns `"unknown"` instead of `"openclaw"`
# from any inference branch — the patterns below catch ONLY the leak shape.
MODEL_VALUE_PATTERNS = (
    re.compile(r'model_used\s*=\s*"openclaw"'),                       # ai_router hardcoded emit
    re.compile(r'model_used\s*=\s*\'openclaw\''),                      # ai_router hardcoded emit (single quotes)
    re.compile(r'startswith\(\s*"openclaw"\s*\)'),                     # code_task_runner prefix branch (the leak)
    re.compile(r'return\s+"openclaw"\s*$'),                            # any function returning the wrapper id
    re.compile(r'MODEL_PROVIDER_HINTS.*"openclaw"\s*:\s*"openclaw"'), # token_tracker round-trip
    re.compile(r'KNOWN_MODELS\s*\[.*"openclaw".*\]\s*=\s*\[\s*"openclaw"\s*\]'),  # registry self-id
    re.compile(r'PROVIDER_DEFAULT_MODELS\s*\[.*"openclaw".*\]\s*=\s*"openclaw"'), # registry self-id
)


# ────────────────────────────────────────────────────────────────────────────
# Guard 1 — structural: no provider's default model equals its provider id
# ────────────────────────────────────────────────────────────────────────────


class TestNoSelfIdInProviderRegistry:
    """The defect class: PROVIDER_DEFAULT_MODELS[k] == k, or
    KNOWN_MODELS[k] containing k. Catches the leak at the registry level for
    any provider, present or future."""

    def test_no_provider_default_equals_provider_id(self):
        violations = [
            (provider, default)
            for provider, default in PROVIDER_DEFAULT_MODELS.items()
            if default == provider
        ]
        assert not violations, (
            f"PROVIDER_DEFAULT_MODELS round-trips the provider id (the leak): "
            f"{violations}. Use `provider_default_model(provider)` with a "
            f"resolver for wrapper providers; never put the provider id in "
            f"the dict."
        )

    def test_no_known_model_equals_provider_id(self):
        violations = [
            (provider, model)
            for provider, models in KNOWN_MODELS.items()
            for model in models
            if model == provider
        ]
        assert not violations, (
            f"KNOWN_MODELS contains the provider id (the leak): {violations}."
        )


# ────────────────────────────────────────────────────────────────────────────
# Guard 2 — literal scan: no file emits "openclaw" as a MODEL value
# ────────────────────────────────────────────────────────────────────────────


class TestNoOpenclawModelLiteralInCodePaths:
    """Static check that the four leak-emitting files no longer hardcode
    "openclaw" as a model value. The check is deliberately narrow — service
    identifier uses (provider comparisons, AIModel.OPENCLAW enum membership,
    process names, log tags) are correct."""

    @pytest.mark.parametrize("relpath", LEAK_SCAN_FILES)
    def test_file_has_no_openclaw_model_literal(self, relpath):
        path = Path(__file__).resolve().parents[1] / relpath
        assert path.exists(), f"Cannot scan non-existent file: {relpath}"
        text = path.read_text(encoding="utf-8")

        hits = []
        for pattern in MODEL_VALUE_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                hits.append((line_no, match.group(0)))

        assert not hits, (
            f"{relpath} contains \"openclaw\" used as a MODEL value (the leak): "
            f"{hits}. Use `openclaw_inner_model()` to resolve the inner "
            f"delegate from DEEPSEEK_MODEL at call time."
        )


# ────────────────────────────────────────────────────────────────────────────
# Guard 3 — entitlement: wrapper delegate must appear in some tier
# ────────────────────────────────────────────────────────────────────────────

# Wrapper providers — currently just openclaw. Add new wrappers here so the
# guard applies to them too.
WRAPPER_PROVIDERS = ("openclaw",)


class TestWrapperDelegatePresentInPricingTiers:
    """The pricing_tiers substring check at `app/config/pricing_tiers.py:94`
    keys on the model string returned by the AIResponse. If a wrapper
    provider's inner delegate is absent from every tier's `allowed_models`,
    requests routed through that wrapper stop being entitled in production.

    This test catches that breakage in CI: when the wrapper's delegate env is
    configured (DEEPSEEK_MODEL for openclaw), the resolved delegate string
    MUST appear in at least one tier's `allowed_models`. If the test env has
    no DEEPSEEK_MODEL, the test SKIPS — we are not asserting env presence,
    only entitlement consistency."""

    @pytest.mark.parametrize("wrapper", WRAPPER_PROVIDERS)
    def test_wrapper_delegate_in_some_tier(self, wrapper):
        if wrapper == "openclaw":
            delegate = openclaw_inner_model()
        else:
            pytest.skip(f"Wrapper '{wrapper}' has no resolver registered.")

        if not delegate:
            pytest.skip(
                f"DEEPSEEK_MODEL is unset in the test environment — cannot "
                f"resolve '{wrapper}' delegate for entitlement check. "
                f"Set DEEPSEEK_MODEL=<model> to exercise this guard."
            )

        present_in = [
            tier_name
            for tier_name, tier in PRICING_TIERS.items()
            if "*" in tier["allowed_models"]
            or any(delegate.lower() in allowed.lower() for allowed in tier["allowed_models"])
        ]

        assert present_in, (
            f"Wrapper provider '{wrapper}' delegates to '{delegate}', but "
            f"that delegate is absent from EVERY tier's allowed_models in "
            f"`app/config/pricing_tiers.py:PRICING_TIERS`. Openclaw-routed "
            f"requests would silently fail the entitlement check at line 94. "
            f"Add '{delegate}' to at least one tier's allowed_models."
        )

    def test_openclaw_inner_model_returns_none_when_env_missing(self, monkeypatch):
        """Sanity: `openclaw_inner_model()` returns None (not a fallback string,
        not the provider id) when DEEPSEEK_MODEL is unset or empty. This is
        the explicitly-unknown contract the dispatch requires."""
        for key in ("DEEPSEEK_MODEL",):
            monkeypatch.delenv(key, raising=False)

        from app.services.max import routing_state
        routing_state.openclaw_inner_model.__defaults__  # noqa: B018 — touch to force import
        result = routing_state.openclaw_inner_model()
        assert result is None, (
            f"openclaw_inner_model() must return None when env is absent "
            f"(explicitly unknown); got {result!r}."
        )


# ────────────────────────────────────────────────────────────────────────────
# Guard 4 — drift: backend and openclaw service drop-ins must agree
# ────────────────────────────────────────────────────────────────────────────


class TestBackendOpenclawDeepseekModelAgreement:
    """Backend (`empire-backend.service`) and OpenClaw (`empire-openclaw.service`)
    are separate systemd user units with separate `EnvironmentFile=` drop-ins.
    They both carry `DEEPSEEK_MODEL`. They have already drifted once:
    backend had `deepseek-chat`, openclaw had `deepseek-v4-flash`. The R9
    resolver surfaces the BACKEND's value as `model_used`; the wrapper
    actually delegates via the OPENCLAW service's value. When the two drop-ins
    disagree, the surfaced model name is honest about the backend's view but
    a lie about what answered the prompt.

    This guard reads BOTH source-of-truth drop-in files and asserts the
    DEEPSEEK_MODEL values agree. Catches the next drift in CI before it ships.
    Skips (not fails) when a drop-in is absent — the test environment may not
    have both unit drop-ins installed."""

    BACKEND_DROPIN = Path("/home/rg/.config/empirebox/empire-backend.env")
    OPENCLAW_DROPIN = Path("/home/rg/.config/empirebox/openclaw-deepseek.env")

    @staticmethod
    def _read_deepseek_model(path: Path) -> str | None:
        if not path.exists():
            return None
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "DEEPSEEK_MODEL":
                v = value.strip()
                return v or None
        return None

    def test_backend_and_openclaw_dropins_agree_on_deepseek_model(self):
        backend_value = self._read_deepseek_model(self.BACKEND_DROPIN)
        openclaw_value = self._read_deepseek_model(self.OPENCLAW_DROPIN)

        if backend_value is None or openclaw_value is None:
            pytest.skip(
                f"Cannot run drift guard: one or both drop-ins missing "
                f"or DEEPSEEK_MODEL unset. backend_dropin={self.BACKEND_DROPIN} "
                f"value={backend_value!r}, openclaw_dropin={self.OPENCLAW_DROPIN} "
                f"value={openclaw_value!r}. The guard is environment-specific "
                f"and skips on hosts without the full EmpireBox drop-ins."
            )

        assert backend_value == openclaw_value, (
            f"DEEPSEEK_MODEL drift between backend and openclaw drop-ins: "
            f"backend={backend_value!r} (from {self.BACKEND_DROPIN}), "
            f"openclaw={openclaw_value!r} (from {self.OPENCLAW_DROPIN}). "
            f"The R9 resolver returns the backend's value; the openclaw "
            f"wrapper actually delegates via the openclaw service's value. "
            f"When they disagree, model_used lies about what answered. "
            f"Edit one drop-in to match the other and restart the backend "
            f"to pick up the change."
        )
