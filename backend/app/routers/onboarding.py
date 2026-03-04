"""
Onboarding router — first-time business setup.
POST /api/v1/onboarding/setup configures business.json for new installations.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.config.business_config import biz, BusinessConfig, CONFIG_PATH

router = APIRouter()


class OnboardingRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100)
    owner_name: str = Field(..., min_length=1, max_length=100)
    industry: str = Field(default="general")
    tax_rate: float = Field(default=0.0, ge=0, le=0.5)
    currency: str = Field(default="USD", max_length=3)
    timezone: str = Field(default="America/New_York")
    ai_assistant_name: Optional[str] = Field(default="MAX")
    tier: str = Field(default="free")


class OnboardingResponse(BaseModel):
    success: bool
    message: str
    config: dict


@router.post("/onboarding/setup", response_model=OnboardingResponse)
async def setup_business(req: OnboardingRequest):
    """First-time business configuration. Creates/updates business.json."""
    global biz

    # Validate tier
    valid_tiers = ["free", "lite", "pro", "empire"]
    if req.tier not in valid_tiers:
        raise HTTPException(400, f"Invalid tier. Must be one of: {valid_tiers}")

    # Update config
    import app.config.business_config as cfg
    new_config = BusinessConfig(
        business_name=req.business_name,
        owner_name=req.owner_name,
        industry=req.industry,
        tax_rate=req.tax_rate,
        currency=req.currency,
        timezone=req.timezone,
        ai_assistant_name=req.ai_assistant_name or "MAX",
        tier=req.tier,
    )
    new_config.save()

    # Reload singleton
    cfg.biz = BusinessConfig.load()

    from dataclasses import asdict
    return OnboardingResponse(
        success=True,
        message=f"{req.business_name} configured successfully",
        config=asdict(cfg.biz),
    )


@router.get("/onboarding/status")
async def onboarding_status():
    """Check if onboarding has been completed (business.json exists with non-default name)."""
    is_configured = CONFIG_PATH.exists() and biz.business_name != "Empire"
    from dataclasses import asdict
    return {
        "configured": is_configured or biz.owner_name != "Founder",
        "business_name": biz.business_name,
        "tier": biz.tier,
        "config": asdict(biz),
    }
