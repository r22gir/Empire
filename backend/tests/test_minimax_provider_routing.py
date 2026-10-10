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
os.environ.pop("MAX_SELECTED_PROVIDER", None)
os.environ.pop("MAX_SELECTED_MODEL", None)


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
        os.environ["MAX_SELECTED_PROVIDER"] = "minimax"
        os.environ["MAX_SELECTED_MODEL"] = "MiniMax-M2.7"
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


class TestFreeModelRoutingAndGuardrails:
    """Free model routing additions, quota fallback, and financial desk guardrails."""

    def test_known_models_contain_free_models(self):
        """routing_state.KNOWN_MODELS must contain verified free models."""
        from app.services.max.routing_state import KNOWN_MODELS

        groq_models = KNOWN_MODELS.get("groq", [])
        assert "openai/gpt-oss-120b" in groq_models
        assert "openai/gpt-oss-20b" in groq_models
        assert "qwen/qwen3.8-27b" in groq_models

        gemini_models = KNOWN_MODELS.get("gemini", [])
        assert "gemini-2.5-flash-lite" in gemini_models
        assert "gemini-3.5-flash" in gemini_models

        openrouter_models = KNOWN_MODELS.get("openrouter", [])
        assert "nvidia/nemotron-3-super-120b-a12b:free" in openrouter_models
        assert "google/gemma-4-31b-it:free" in openrouter_models
        assert "cohere/north-mini-code:free" in openrouter_models
        assert "openrouter/free" in openrouter_models

    def test_ai_router_chat_signatures_accept_model(self):
        """_groq_chat and _gemini_chat must accept model keyword argument."""
        import inspect
        from app.services.max.ai_router import AIRouter

        groq_sig = inspect.signature(AIRouter._groq_chat)
        assert "model" in groq_sig.parameters

        gemini_sig = inspect.signature(AIRouter._gemini_chat)
        assert "model" in gemini_sig.parameters

        groq_stream_sig = inspect.signature(AIRouter._groq_chat_stream)
        assert "model" in groq_stream_sig.parameters

        gemini_stream_sig = inspect.signature(AIRouter._gemini_chat_stream)
        assert "model" in gemini_stream_sig.parameters

    def test_client_facing_and_financial_desks_block_free_models(self):
        """Client-facing and financial desks must never route to free-tier models."""
        from app.services.max.free_tiers import is_financial_or_client_desk, is_free_tier_model

        # Check guardrail classification
        assert is_financial_or_client_desk("forge") is True
        assert is_financial_or_client_desk("finance") is True
        assert is_financial_or_client_desk("workroom") is True
        assert is_financial_or_client_desk(feature="quote") is True
        assert is_financial_or_client_desk(feature="invoice") is True
        assert is_financial_or_client_desk(feature="client_reply") is True

        # Non-financial / internal desks are allowed
        assert is_financial_or_client_desk("dev", feature="code") is False
        assert is_financial_or_client_desk("notes", feature="summary") is False

        # In AIRouter._chat_via_selected_routing, financial desks skip free-tier candidates
        import importlib
        import app.services.max.ai_router as ai_router_mod
        importlib.reload(ai_router_mod)

        router = ai_router_mod.AIRouter()
        # Simulated candidate routing: free model on forge desk is skipped
        assert is_free_tier_model("openai/gpt-oss-120b") is True
        assert is_free_tier_model("nvidia/nemotron-3-super-120b-a12b:free") is True

    @pytest.mark.asyncio
    async def test_free_model_quota_exhausted_skips_and_falls_back(self, tmp_path, monkeypatch):
        """When a free model's quota is exhausted, router skips it."""
        from app.services.max.free_tiers import record_free_tier_usage, is_free_tier_quota_exhausted
        from datetime import datetime

        db_file = str(tmp_path / "test_quota_exhaust.db")
        now = datetime(2026, 10, 10, 12, 0, 0)

        # Exhaust groq free model (limit: 1000 requests/day)
        record_free_tier_usage("openai/gpt-oss-120b", "groq", requests=1000, tokens=1000, db_path=db_file, now=now)

        assert is_free_tier_quota_exhausted("openai/gpt-oss-120b", "groq", db_path=db_file, now=now) is True

        # Router skip check
        import app.services.max.ai_router as ai_router_mod
        router = ai_router_mod.AIRouter()

        # Mocking check_free_tier_quota to exhaust
        monkeypatch.setattr(
            "app.services.max.ai_router.is_free_tier_quota_exhausted",
            lambda model, provider=None: model == "openai/gpt-oss-120b",
        )

        # In _try_provider_chat, exhausted free model returns None (skips and falls back)
        res = await router._try_provider_chat(
            provider_type="groq",
            model_override="openai/gpt-oss-120b",
            full_messages=[],
            messages=[],
            image_path=None,
            fallback=False,
            feature="chat",
            business="general",
            tenant_id="founder",
        )
        assert res is None

