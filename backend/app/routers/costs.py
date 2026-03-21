"""
AI Cost Tracker API — /api/v1/costs/*
Provides cost analytics, budget management, and transaction log.
"""
from fastapi import APIRouter, Query
from app.services.max.token_tracker import token_tracker, COST_RATES, FIXED_COSTS, FEATURES, BUSINESSES

router = APIRouter()


@router.get("/costs/overview")
async def cost_overview(days: int = Query(30, ge=1, le=365)):
    """Full dashboard overview: totals, today, by_model, daily, budget."""
    return token_tracker.get_stats(days)


@router.get("/costs/summary")
async def cost_summary(days: int = Query(30, ge=1, le=365)):
    """Alias for /costs/overview — returns full dashboard summary."""
    return token_tracker.get_stats(days)


@router.get("/costs/today")
async def cost_today():
    """Today's cost summary."""
    stats = token_tracker.get_stats(1)
    return stats["today"]


@router.get("/costs/daily")
async def cost_daily(days: int = Query(30, ge=1, le=365)):
    """Daily cost breakdown."""
    return {"daily": token_tracker.get_daily(days)}


@router.get("/costs/weekly")
async def cost_weekly(weeks: int = Query(12, ge=1, le=52)):
    """Weekly cost breakdown."""
    return {"weekly": token_tracker.get_weekly(weeks)}


@router.get("/costs/monthly")
async def cost_monthly(months: int = Query(12, ge=1, le=24)):
    """Monthly cost breakdown."""
    return {"monthly": token_tracker.get_monthly(months)}


@router.get("/costs/by-provider")
async def cost_by_provider(days: int = Query(30, ge=1, le=365)):
    """Cost breakdown by provider (xAI, Anthropic, Groq, local)."""
    return {"by_provider": token_tracker.get_by_provider(days)}


@router.get("/costs/by-feature")
async def cost_by_feature(days: int = Query(30, ge=1, le=365)):
    """Cost breakdown by feature (chat, vision, tts, etc)."""
    return {"by_feature": token_tracker.get_by_feature(days)}


@router.get("/costs/by-business")
async def cost_by_business(days: int = Query(30, ge=1, le=365)):
    """Cost breakdown by business unit."""
    return {"by_business": token_tracker.get_by_business(days)}


@router.get("/costs/transactions")
async def cost_transactions(limit: int = Query(50, ge=1, le=500)):
    """Recent individual API call transactions."""
    return {"transactions": token_tracker.get_recent_transactions(limit)}


@router.get("/costs/budget")
async def cost_budget():
    """Current budget config and usage."""
    stats = token_tracker.get_stats(30)
    return stats["budget"]


@router.post("/costs/budget")
async def update_budget(
    monthly_budget: float = None,
    alert_threshold: float = None,
    auto_switch: bool = None,
    auto_switch_threshold: float = None,
):
    """Update budget settings."""
    token_tracker.update_budget(monthly_budget, alert_threshold, auto_switch, auto_switch_threshold)
    stats = token_tracker.get_stats(30)
    return {"status": "updated", "budget": stats["budget"]}


@router.get("/costs/tenant/{tenant_id}/usage")
async def tenant_usage(tenant_id: str, days: int = Query(30, ge=1, le=365)):
    """Token usage stats for a specific tenant."""
    return token_tracker.get_tenant_usage(tenant_id, days)


@router.get("/costs/tenant/{tenant_id}/budget")
async def tenant_budget(tenant_id: str, tier: str = Query("pro")):
    """Budget status for a tenant compared to their pricing tier."""
    return token_tracker.get_tenant_budget_status(tenant_id, tier)


@router.get("/costs/rates")
async def cost_rates():
    """Current pricing rates for all models."""
    return {
        "token_rates": COST_RATES,
        "fixed_costs": FIXED_COSTS,
        "features": FEATURES,
        "businesses": BUSINESSES,
    }
