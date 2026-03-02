"""License verification API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import hashlib
import os

router = APIRouter()


class LicenseVerifyRequest(BaseModel):
    license_key: str
    device_id: Optional[str] = None


class LicenseResponse(BaseModel):
    valid: bool
    tier: Optional[str] = None
    message: str


@router.post("/license/verify")
async def verify_license(request: LicenseVerifyRequest):
    """Verify a license key."""
    # Founder edition keys are valid by default
    if request.license_key.startswith("EMPIRE-FOUNDER-"):
        return LicenseResponse(valid=True, tier="founder", message="Founder Edition - Valid")

    return LicenseResponse(valid=False, tier=None, message="Invalid license key")


@router.get("/license/status")
async def license_status():
    """Get current license status."""
    return {
        "edition": "founder",
        "status": "active",
        "features": ["all"]
    }
