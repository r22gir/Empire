"""
User service for profile and subscription management.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models import User
from app.schemas.user import UserUpdate, SubscriptionInfo
from app.utils.helpers import get_token_limit, calculate_percent_used
from uuid import UUID


async def get_user_by_id(user_id: UUID, db: AsyncSession) -> User:
    """
    Get user by ID.
    
    Args:
        user_id: User UUID
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user not found
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


async def update_user_profile(user: User, update_data: UserUpdate, db: AsyncSession) -> User:
    """
    Update user profile.
    
    Args:
        user: Current user
        update_data: Update data
        db: Database session
        
    Returns:
        Updated user
    """
    if update_data.name is not None:
        user.name = update_data.name
    
    if update_data.notification_settings is not None:
        # Store notification settings (would need a JSON field in User model)
        pass
    
    await db.commit()
    await db.refresh(user)
    
    return user


async def get_subscription_info(user: User) -> SubscriptionInfo:
    """
    Get user subscription information.
    
    Args:
        user: Current user
        
    Returns:
        Subscription information
    """
    token_limit = get_token_limit(user.tier)
    percent_used = calculate_percent_used(user.tokens_used_this_month, token_limit)
    
    return SubscriptionInfo(
        tier=user.tier,
        tokens_used=user.tokens_used_this_month,
        tokens_limit=token_limit,
        percent_used=percent_used,
        renewal_date=user.tokens_reset_date
    )
