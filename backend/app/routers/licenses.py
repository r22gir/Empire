from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.license import (
    LicenseCreate,
    LicenseResponse,
    LicenseValidation,
    LicenseActivation,
    LicenseActivationResponse
)
from app.services.license_service import LicenseService

router = APIRouter()

@router.post("/generate", response_model=List[LicenseResponse])
async def generate_licenses(
    license_data: LicenseCreate,
    db: Session = Depends(get_db)
):
    """
    Generate one or more license keys (admin only in production)
    """
    licenses = LicenseService.create_licenses(db, license_data)
    return licenses

@router.get("/{key}/validate", response_model=LicenseValidation)
async def validate_license(
    key: str,
    db: Session = Depends(get_db)
):
    """
    Validate a license key
    """
    license = LicenseService.validate_license(db, key)
    
    if not license:
        return LicenseValidation(
            valid=False,
            status="not_found",
            message="License key not found"
        )
    
    return LicenseValidation(
        valid=license.status == "pending",
        plan=license.plan,
        duration_months=license.duration_months,
        hardware_bundle=license.hardware_bundle,
        status=license.status,
        message=f"License is {license.status}"
    )

@router.post("/{key}/activate", response_model=LicenseActivationResponse)
async def activate_license(
    key: str,
    activation_data: LicenseActivation,
    db: Session = Depends(get_db)
):
    """
    Activate a license for a user
    """
    success, message, subscription_details = LicenseService.activate_license(
        db, key, activation_data
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return LicenseActivationResponse(
        success=success,
        message=message,
        subscription_details=subscription_details
    )

@router.get("/my-licenses", response_model=List[LicenseResponse])
async def get_my_licenses(
    user_id: str,  # In production, get from authenticated user
    db: Session = Depends(get_db)
):
    """
    Get all licenses for the authenticated user
    """
    licenses = LicenseService.get_user_licenses(db, user_id)
    return licenses
