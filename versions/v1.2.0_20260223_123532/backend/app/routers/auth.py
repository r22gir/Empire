"""
Authentication routes for signup, login, and token refresh.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import SignupRequest, LoginRequest, Token, TokenRefreshRequest
from app.schemas.user import UserResponse
from app.services.auth_service import signup_user, login_user, refresh_access_token
from app.utils.helpers import get_token_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=dict)
async def signup(
    signup_data: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user account.
    
    Returns user data and authentication tokens.
    """
    user, tokens = await signup_user(signup_data, db)
    
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        marketforge_email=user.marketforge_email,
        tier=user.tier,
        tokens_used_this_month=user.tokens_used_this_month,
        tokens_limit=get_token_limit(user.tier),
        created_at=user.created_at
    )
    
    return {
        "user": user_response,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type
    }


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return tokens.
    """
    tokens = await login_user(login_data, db)
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate new access token from refresh token.
    """
    tokens = await refresh_access_token(refresh_data.refresh_token, db)
    return tokens
