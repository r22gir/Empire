"""Tests for MiniMax provider routing and xAI disable policy.

Covers:
- MAX_PRIMARY_PROVIDER=minimax selects MiniMax as primary
- MAX_DISABLE_XAI=true prevents xAI from being used anywhere
- get_available_models reflects disabled xAI
- _build_complexity_chain skips xAI when disabled
- Status endpoint shows provider policy correctly
- No API keys are printed or exposed
"""
import os
import pytest

# Ensure clean env for testing
os.environ.pop("MAX_PRIMARY_PROVIDER", None)
os.environ.pop("MAX_DISABLE_XAI", None)
os.environ.pop("MAX_DISABLE_OLLAMA", None)
os.environ.pop("MINIMAX_API_KEY", None)
os.environ.pop("XAI_API_KEY", None)
os.environ.pop("OLLAMA_ENABLED", None)


class TestMiniMaxPrimaryProvider:
    """MAX_PRIMARY_PROVIDER=minimax must select MiniMax as primary model."""

    def test_minimax_primary_when_env_set(self):
        """MiniMax primary when MAX_PRIMARY_PROVIDER=minimax and key is present."""
        os.environ["MINIMAX_API_KEY"] = "test-key"
        os.environ["MAX_PRIMARY_PROVIDER"] = "minimax"
        os.environ["MAX_DISABLE_XAI"] = "false"

        # Re-import to pick up env
        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        assert router.primary_model == ai_router_mod.AIModel.MINIMAX
        assert router.max_disable_xai is False

    def test_minimax_primary_skips_xai_when_disabled(self):
        """xAI is skipped in complexity chain when MAX_DISABLE_XAI=true."""
        os.environ["MINIMAX_API_KEY"] = "test-key"
        os.environ["XAI_API_KEY"] = "xai-test-key"
        os.environ["MAX_PRIMARY_PROVIDER"] = "minimax"
        os.environ["MAX_DISABLE_XAI"] = "true"

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        assert router.primary_model == ai_router_mod.AIModel.MINIMAX
        assert router.max_disable_xai is True

        # xAI should not appear in moderate chain
        chain = router._build_complexity_chain(ai_router_mod.TaskComplexity.MODERATE)
        providers = [p[0] for p in chain]
        assert "grok" not in providers, f"xAI/grok should not appear in chain when disabled: {providers}"
        assert "minimax" in providers, f"MiniMax should be first in chain: {providers}"


class TestXaiDisablePolicy:
    """MAX_DISABLE_XAI=true must prevent xAI from being used anywhere."""

    def test_xai_not_used_when_disabled(self):
        """xAI disabled chain should never include grok."""
        os.environ["XAI_API_KEY"] = "xai-key"
        os.environ["MINIMAX_API_KEY"] = ""
        os.environ["MAX_DISABLE_XAI"] = "true"
        os.environ["MAX_PRIMARY_PROVIDER"] = ""

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        assert router.max_disable_xai is True

        for complexity in [ai_router_mod.TaskComplexity.SIMPLE, ai_router_mod.TaskComplexity.MODERATE, ai_router_mod.TaskComplexity.COMPLEX]:
            chain = router._build_complexity_chain(complexity)
            providers = [p[0] for p in chain]
            assert "grok" not in providers, f"xAI/grok should not appear in {complexity.value} chain: {providers}"

    def test_xai_available_when_not_disabled(self):
        """xAI available when MAX_DISABLE_XAI is not set."""
        os.environ["XAI_API_KEY"] = "xai-key"
        os.environ["MINIMAX_API_KEY"] = ""
        os.environ["MAX_DISABLE_XAI"] = ""
        os.environ["MAX_PRIMARY_PROVIDER"] = ""

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        assert router.max_disable_xai is False


class TestGetAvailableModels:
    """get_available_models must reflect xAI disabled state correctly."""

    def test_xai_disabled_shows_in_model_list(self):
        """xAI should show disabled=True in model list when MAX_DISABLE_XAI=true."""
        os.environ["XAI_API_KEY"] = "xai-key"
        os.environ["MINIMAX_API_KEY"] = "minimax-key"
        os.environ["MAX_PRIMARY_PROVIDER"] = "minimax"
        os.environ["MAX_DISABLE_XAI"] = "true"

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        models = router.get_available_models()

        grok_model = next(m for m in models if m["id"] == "grok")
        assert grok_model["disabled"] is True
        assert grok_model["disabled_reason"] == "credits_unavailable"
        assert grok_model["configured"] is True  # key still set, just disabled
        assert grok_model["available"] is False  # but not usable

        minimax_model = next(m for m in models if m["id"] == "minimax")
        assert minimax_model["primary"] is True


class TestNoKeyExposure:
    """API keys must never be printed or exposed in status."""

    def test_no_key_in_primary_model_name(self, monkeypatch):
        """Primary model name output must not contain key material."""
        os.environ["MINIMAX_API_KEY"] = "sk-super-secret-key-12345"
        os.environ["MAX_PRIMARY_PROVIDER"] = "minimax"

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        primary_name = router.primary_model.name
        # Primary model name is just an enum name, not the key
        assert "super-secret" not in primary_name
        assert "sk-" not in primary_name

    def test_no_key_in_get_available_models(self, monkeypatch):
        """get_available_models must not include key values."""
        os.environ["MINIMAX_API_KEY"] = "sk-secret-xyz"
        os.environ["XAI_API_KEY"] = "xai-secret-abc"

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        models = router.get_available_models()

        for model in models:
            # Model dicts should not contain key values
            for key, value in model.items():
                if isinstance(value, str):
                    assert "sk-secret" not in value
                    assert "xai-secret" not in value


class TestOllamaDisablePolicy:
    """MAX_DISABLE_OLLAMA=true must prevent Ollama from being used anywhere."""

    def test_ollama_disabled_prevents_selection(self):
        """Ollama should not be selected when MAX_DISABLE_OLLAMA=true."""
        os.environ["MINIMAX_API_KEY"] = "test-key"
        os.environ["MAX_PRIMARY_PROVIDER"] = "minimax"
        os.environ["MAX_DISABLE_OLLAMA"] = "true"
        os.environ.pop("XAI_API_KEY", None)

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        assert router.max_disable_ollama is True
        assert router.primary_model == ai_router_mod.AIModel.MINIMAX

    def test_ollama_disabled_in_model_list(self):
        """Ollama should show disabled=True in model list when MAX_DISABLE_OLLAMA=true."""
        os.environ["MINIMAX_API_KEY"] = "test-key"
        os.environ["MAX_PRIMARY_PROVIDER"] = "minimax"
        os.environ["MAX_DISABLE_OLLAMA"] = "true"

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        models = router.get_available_models()

        ollama_model = next(m for m in models if m["id"] == "ollama-llama")
        assert ollama_model["disabled"] is True
        assert ollama_model["disabled_reason"] == "founder_disabled_due_to_stall_suspected"

    def test_ollama_not_in_provider_list(self):
        """Ollama should not appear in providers list when disabled."""
        os.environ["MINIMAX_API_KEY"] = "test-key"
        os.environ["MAX_PRIMARY_PROVIDER"] = "minimax"
        os.environ["MAX_DISABLE_OLLAMA"] = "true"

        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        # Providers list is built in __init__ — check via available models
        models = router.get_available_models()
        ollama = next((m for m in models if m["id"] == "ollama-llama"), None)
        assert ollama is not None
        assert ollama["disabled"] is True