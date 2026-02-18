"""
User routes for profile and subscription management.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User
from app.middleware import get_current_user
from app.schemas.user import UserResponse, UserUpdate, SubscriptionInfo
from app.services.user_service import update_user_profile, get_subscription_info
from app.utils.helpers import get_token_limit

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        marketforge_email=current_user.marketforge_email,
        tier=current_user.tier,
        tokens_used_this_month=current_user.tokens_used_this_month,
        tokens_limit=get_token_limit(current_user.tier),
        created_at=current_user.created_at
    )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile.
    """
    updated_user = await update_user_profile(current_user, update_data, db)
    
    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        name=updated_user.name,
        marketforge_email=updated_user.marketforge_email,
        tier=updated_user.tier,
        tokens_used_this_month=updated_user.tokens_used_this_month,
        tokens_limit=get_token_limit(updated_user.tier),
        created_at=updated_user.created_at
    )


@router.get("/me/subscription", response_model=SubscriptionInfo)
async def get_subscription(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user subscription information.
    """
    return await get_subscription_info(current_user)
