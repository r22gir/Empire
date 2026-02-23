from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LicenseBase(BaseModel):
    plan: str = Field(..., description="Subscription plan: free, lite, pro, empire")
    duration_months: int = Field(..., description="Duration in months")
    hardware_bundle: Optional[str] = Field(None, description="Hardware bundle type if applicable")

class LicenseCreate(LicenseBase):
    quantity: int = Field(1, description="Number of licenses to generate")

class LicenseResponse(LicenseBase):
    id: str
    key: str
    status: str
    created_at: datetime
    activated_at: Optional[datetime]
    expires_at: Optional[datetime]
    user_id: Optional[str]
    preorder_id: Optional[str]
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class LicenseValidation(BaseModel):
    valid: bool
    plan: Optional[str]
    duration_months: Optional[int]
    hardware_bundle: Optional[str]
    status: str
    message: Optional[str]

class LicenseActivation(BaseModel):
    user_id: str = Field(..., description="User ID to activate license for")

class LicenseActivationResponse(BaseModel):
    success: bool
    message: str
    subscription_details: Optional[dict]
