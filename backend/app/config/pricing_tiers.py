"""
Pricing tiers for Empire SaaS
Lite $29/mo, Pro $79/mo, Empire $199/mo, Founder unlimited
"""

PRICING_TIERS = {
    "lite": {
        "name": "Lite",
        "price_monthly": 29,
        "token_budget": 50_000,       # 50K tokens/mo
        "allowed_models": ["groq", "ollama", "openclaw"],
        "features": ["chat", "web_search"],
        "priority": "low",
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 79,
        "token_budget": 200_000,      # 200K tokens/mo
        "allowed_models": ["grok", "claude-haiku", "groq", "ollama", "openclaw"],
        "features": ["chat", "chat/stream", "vision", "tts", "web_search", "quote", "desk_task"],
        "priority": "normal",
    },
    "empire": {
        "name": "Empire",
        "price_monthly": 199,
        "token_budget": 1_000_000,    # 1M tokens/mo
        "allowed_models": ["grok", "claude-sonnet", "claude-haiku", "groq", "ollama", "openclaw"],
        "features": ["chat", "chat/stream", "vision", "tts", "stt", "web_search", "quote", "desk_task", "image_gen", "inpaint", "mockup", "email"],
        "priority": "high",
    },
    "founder": {
        "name": "Founder",
        "price_monthly": 0,
        "token_budget": -1,           # unlimited
        "allowed_models": ["*"],      # all models including opus
        "features": ["*"],            # all features
        "priority": "max",
    },
}


def get_tier(tier_id: str) -> dict:
    return PRICING_TIERS.get(tier_id, PRICING_TIERS["lite"])


def get_token_budget(tier_id: str) -> int:
    return get_tier(tier_id)["token_budget"]


def is_model_allowed(tier_id: str, model: str) -> bool:
    tier = get_tier(tier_id)
    if "*" in tier["allowed_models"]:
        return True
    return any(allowed in model for allowed in tier["allowed_models"])


def is_feature_allowed(tier_id: str, feature: str) -> bool:
    tier = get_tier(tier_id)
    if "*" in tier["features"]:
        return True
    return feature in tier["features"]
