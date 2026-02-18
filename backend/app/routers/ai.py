"""
AI routes for content generation and assistance.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.middleware import get_current_user
from app.services.ai_service import AIService
from app.database import get_db

router = APIRouter(prefix="/ai", tags=["AI"])


class GenerateDescriptionRequest(BaseModel):
    """Request to generate product description."""
    title: str
    category: Optional[str] = None
    condition: Optional[str] = None
    photos: List[str] = []


class EnhanceDescriptionRequest(BaseModel):
    """Request to enhance existing description."""
    current_description: str


class SuggestPriceRequest(BaseModel):
    """Request to suggest pricing."""
    title: str
    category: Optional[str] = None
    condition: Optional[str] = None
    description: Optional[str] = None


@router.post("/generate-description")
async def generate_description(
    request: GenerateDescriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate product description using AI.
    """
    ai_service = AIService(current_user, db)
    
    result = await ai_service.generate_description({
        "title": request.title,
        "category": request.category,
        "condition": request.condition,
        "photos": request.photos
    })
    
    return result


@router.post("/enhance-description")
async def enhance_description(
    request: EnhanceDescriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhance existing product description.
    """
    ai_service = AIService(current_user, db)
    
    result = await ai_service.enhance_description(request.current_description)
    
    return result


@router.post("/suggest-price")
async def suggest_price(
    request: SuggestPriceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Suggest pricing for a product.
    """
    ai_service = AIService(current_user, db)
    
    result = await ai_service.suggest_price({
        "title": request.title,
        "category": request.category,
        "condition": request.condition,
        "description": request.description
    })
    
    return result
