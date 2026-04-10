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
        "relist": {
            "source_products_limit": 25,
            "listings_limit": 50,
            "ai_analysis_limit": 10,
            "crosslist_limit": 20,
            "orders_limit": 30,
            "ai_deal_finder": False,
            "auto_relist": False,
            "price_alerts": 5,
        },
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 79,
        "token_budget": 200_000,      # 200K tokens/mo
        "allowed_models": ["grok", "claude-haiku", "groq", "ollama", "openclaw"],
        "features": ["chat", "chat/stream", "vision", "tts", "web_search", "quote", "desk_task"],
        "priority": "normal",
        "relist": {
            "source_products_limit": 200,
            "listings_limit": 500,
            "ai_analysis_limit": 100,
            "crosslist_limit": 200,
            "orders_limit": 200,
            "ai_deal_finder": True,
            "auto_relist": True,
            "price_alerts": 50,
        },
    },
    "empire": {
        "name": "Empire",
        "price_monthly": 199,
        "token_budget": 1_000_000,    # 1M tokens/mo
        "allowed_models": ["grok", "claude-sonnet", "claude-haiku", "groq", "ollama", "openclaw"],
        "features": ["chat", "chat/stream", "vision", "tts", "stt", "web_search", "quote", "desk_task", "image_gen", "inpaint", "mockup", "email"],
        "priority": "high",
        "relist": {
            "source_products_limit": -1,    # unlimited
            "listings_limit": -1,
            "ai_analysis_limit": -1,
            "crosslist_limit": -1,
            "orders_limit": -1,
            "ai_deal_finder": True,
            "auto_relist": True,
            "price_alerts": -1,
        },
    },
    "founder": {
        "name": "Founder",
        "price_monthly": 0,
        "token_budget": -1,           # unlimited
        "allowed_models": ["*"],      # all models including opus
        "features": ["*"],            # all features
        "priority": "max",
        "relist": {
            "source_products_limit": -1,
            "listings_limit": -1,
            "ai_analysis_limit": -1,
            "crosslist_limit": -1,
            "orders_limit": -1,
            "ai_deal_finder": True,
            "auto_relist": True,
            "price_alerts": -1,
        },
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


def get_relist_limit(tier_id: str, limit_name: str):
    tier = get_tier(tier_id)
    relist = tier.get("relist", {})
    limit = relist.get(limit_name, 0)
    return limit


def is_relist_unlimited(tier_id: str, limit_name: str) -> bool:
    limit = get_relist_limit(tier_id, limit_name)
    return limit == -1


def check_relist_within_limit(tier_id: str, limit_name: str, current_count: int) -> dict:
    limit = get_relist_limit(tier_id, limit_name)
    if limit == -1:
        return {"allowed": True, "limit": "unlimited", "remaining": "unlimited"}
    remaining = max(0, limit - current_count)
    return {
        "allowed": remaining > 0,
        "limit": limit,
        "used": current_count,
        "remaining": remaining,
    }
