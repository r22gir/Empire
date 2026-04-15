from app.services.max.ai_router import AIRouter


def test_xai_config_uses_current_model_and_safe_payload(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")
    monkeypatch.setenv("XAI_BASE_URL", "https://api.x.ai/v1/")
    monkeypatch.setenv("XAI_MODEL", "grok-test-model")
    monkeypatch.setenv("XAI_MAX_TOKENS", "123")

    router = AIRouter()
    payload = router._xai_payload([{"role": "user", "content": "hello"}], stream=True)

    assert router.primary_model.value == "grok"
    assert router.xai_base_url == "https://api.x.ai/v1"
    assert payload == {
        "model": "grok-test-model",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 123,
        "stream": True,
    }
    assert "stop" not in payload
    assert "presencePenalty" not in payload
    assert "frequencyPenalty" not in payload
    assert "reasoning_effort" not in payload
    assert "logprobs" not in payload


def test_xai_provider_status_exposes_effective_config(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")
    monkeypatch.setenv("XAI_MODEL", "grok-visible-model")
    monkeypatch.setenv("XAI_BASE_URL", "https://api.x.ai/v1")

    router = AIRouter()
    grok = next(model for model in router.get_available_models() if model["id"] == "grok")

    assert grok["available"] is True
    assert grok["configured"] is True
    assert grok["primary"] is True
    assert grok["model"] == "grok-visible-model"
    assert grok["base_url"] == "https://api.x.ai/v1"
    assert grok["status_source"] == "env_configured"
