"""
Pydantic schemas for LuxeForge measurement endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class MeasurementPoint(BaseModel):
    x: float
    y: float


class MeasurementLine(BaseModel):
    label: str = ""
    start: MeasurementPoint
    end: MeasurementPoint
    pixels: float
    real_length: Optional[float] = None


class CalibrateRequest(BaseModel):
    image_id: UUID
    reference_pixels: float = Field(..., gt=0, description="Pixel length of the reference line")
    reference_real: float = Field(..., gt=0, description="Real-world length of the reference object")
    reference_unit: str = Field("inches", pattern="^(inches|cm)$")


class CalculateRequest(BaseModel):
    image_id: UUID
    lines: List[MeasurementLine]


class ExportRequest(BaseModel):
    image_id: UUID
    format: str = Field("quote", pattern="^(quote|json|csv)$")


class MeasurementResponse(BaseModel):
    id: UUID
    image_id: UUID
    reference_pixels: float
    reference_real: float
    reference_unit: str
    measurements: List[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CalculateResponse(BaseModel):
    image_id: UUID
    reference_unit: str
    lines: List[MeasurementLine]


class ExportResponse(BaseModel):
    image_id: UUID
    format: str
    data: Any
