"""
Tier-based feature gating middleware.
Checks business tier from config and gates premium features accordingly.

Tiers: free → lite → pro → empire
"""
from functools import wraps
from fastapi import HTTPException

from app.config.business_config import biz

# ── Tier definitions ─────────────────────────────────────────────────

TIER_ORDER = ["free", "lite", "pro", "empire", "founder"]

TIER_LIMITS = {
    "free": {
        "max_desks": 0,
        "max_tools": 5,
        "tokens_per_month": 100,
        "ai_tokens_per_month": 0,
        "features": {"chat", "contacts", "tasks", "quotes_basic"},
    },
    "lite": {
        "max_desks": 3,
        "max_tools": 12,
        "tokens_per_month": 1_000,
        "ai_tokens_per_month": 50_000,
        "features": {"chat", "contacts", "tasks", "quotes_basic", "web_search", "telegram"},
    },
    "pro": {
        "max_desks": 12,
        "max_tools": 23,
        "tokens_per_month": 10_000,
        "ai_tokens_per_month": 200_000,
        "features": {
            "chat", "contacts", "tasks", "quotes_basic", "quotes_advanced",
            "web_search", "telegram", "presentations", "brain", "desks",
        },
    },
    "empire": {
        "max_desks": 999,
        "max_tools": 999,
        "tokens_per_month": 100_000,
        "ai_tokens_per_month": 1_000_000,
        "features": {
            "chat", "contacts", "tasks", "quotes_basic", "quotes_advanced",
            "web_search", "telegram", "presentations", "brain", "desks",
            "api_access", "custom_desks",
        },
    },
    "founder": {
        "max_desks": 999,
        "max_tools": 999,
        "tokens_per_month": 999_999_999,
        "ai_tokens_per_month": 999_999_999,
        "features": {
            "chat", "contacts", "tasks", "quotes_basic", "quotes_advanced",
            "web_search", "telegram", "presentations", "brain", "desks",
            "api_access", "custom_desks",
        },
    },
}

# Tools gated by tier (tool_name → minimum tier)
TOOL_TIERS = {
    # Free tools (available to all)
    "get_tasks": "free",
    "create_task": "free",
    "search_contacts": "free",
    "add_contact": "free",
    "create_quote": "free",
    # Lite tools
    "web_search": "lite",
    "send_telegram": "lite",
    "check_inbox": "lite",
    "search_quotes": "lite",
    "update_task": "lite",
    "get_calendar": "lite",
    "send_quote_telegram": "lite",
    # Pro tools
    "generate_presentation": "pro",
    "brain_search": "pro",
    "run_desk_task": "pro",
    "analyze_image": "pro",
    "generate_quote_pdf": "pro",
    "get_desk_status": "pro",
    # Empire only
    "execute_code": "empire",
    "manage_api_keys": "empire",
}


def get_tier_level(tier: str) -> int:
    """Return numeric tier level (0=free, 3=empire)."""
    try:
        return TIER_ORDER.index(tier.lower())
    except ValueError:
        return 0


def has_feature(feature: str) -> bool:
    """Check if current business tier has access to a feature."""
    tier = biz.tier.lower()
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    return feature in limits["features"]


def can_use_tool(tool_name: str) -> bool:
    """Check if current business tier can use a specific tool."""
    required_tier = TOOL_TIERS.get(tool_name, "free")
    return get_tier_level(biz.tier) >= get_tier_level(required_tier)


def get_limits() -> dict:
    """Return current tier limits."""
    tier = biz.tier.lower()
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    return {"tier": tier, **limits, "features": sorted(limits["features"])}


def require_feature(feature: str):
    """FastAPI dependency — raises 403 if feature is not available in current tier."""
    def checker():
        if not has_feature(feature):
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature}' requires a higher tier. Current: {biz.tier}",
            )
    return checker


def require_tool(tool_name: str):
    """Check tool access — returns error message or None if allowed."""
    if can_use_tool(tool_name):
        return None
    required = TOOL_TIERS.get(tool_name, "free")
    return f"Tool '{tool_name}' requires {required} tier (current: {biz.tier})"


def check_ai_token_budget(user_tier: str = None) -> dict:
    """Check if user is within their AI token budget for the month.

    Returns dict with allowed (bool), used, limit, and remaining.
    """
    tier = (user_tier or biz.tier).lower()
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    token_limit = limits["ai_tokens_per_month"]

    # Founder tier is unlimited
    if tier == "founder":
        return {"allowed": True, "used": 0, "limit": token_limit, "remaining": token_limit}

    # Check token usage from token_usage.db
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime

        db_path = Path(__file__).resolve().parent.parent.parent / "data" / "token_usage.db"
        if not db_path.exists():
            return {"allowed": True, "used": 0, "limit": token_limit, "remaining": token_limit}

        month_start = datetime.now().strftime("%Y-%m-01")
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) FROM token_log WHERE timestamp >= ?",
            (month_start,)
        ).fetchone()
        conn.close()

        used = row[0] if row else 0
        remaining = max(0, token_limit - used)

        return {
            "allowed": used < token_limit,
            "used": used,
            "limit": token_limit,
            "remaining": remaining,
        }
    except Exception:
        # If we can't check, allow the request
        return {"allowed": True, "used": 0, "limit": token_limit, "remaining": token_limit}


def enforce_ai_token_limit(user_tier: str = None):
    """FastAPI dependency — raises 429 if AI token budget is exhausted."""
    def checker():
        budget = check_ai_token_budget(user_tier)
        if not budget["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": f"AI token budget exhausted for {(user_tier or biz.tier).lower()} tier",
                    "used": budget["used"],
                    "limit": budget["limit"],
                    "upgrade_url": "https://studio.empirebox.store/pricing",
                },
            )
    return checker
