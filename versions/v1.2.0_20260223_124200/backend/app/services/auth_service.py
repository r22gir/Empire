"""
Authentication service for user signup, login, and token management.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models import User
from app.schemas.auth import SignupRequest, LoginRequest, Token
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.utils.helpers import generate_marketforge_email
from datetime import datetime, timedelta


async def signup_user(signup_data: SignupRequest, db: AsyncSession) -> tuple[User, Token]:
    """
    Create a new user account.
    
    Args:
        signup_data: Signup request data
        db: Database session
        
    Returns:
        Tuple of (created user, auth tokens)
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == signup_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(signup_data.password)
    marketforge_email = generate_marketforge_email(signup_data.name, signup_data.email)
    
    new_user = User(
        email=signup_data.email,
        password_hash=hashed_password,
        name=signup_data.name,
        marketforge_email=marketforge_email,
        tier="free",
        tokens_used_this_month=0,
        tokens_reset_date=datetime.utcnow() + timedelta(days=30)
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate tokens
    token_data = {"user_id": str(new_user.id), "email": new_user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    tokens = Token(access_token=access_token, refresh_token=refresh_token)
    
    return new_user, tokens


async def login_user(login_data: LoginRequest, db: AsyncSession) -> Token:
    """
    Authenticate user and generate tokens.
    
    Args:
        login_data: Login request data
        db: Database session
        
    Returns:
        Authentication tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Generate tokens
    token_data = {"user_id": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> Token:
    """
    Generate new access token from refresh token.
    
    Args:
        refresh_token: Valid refresh token
        db: Database session
        
    Returns:
        New authentication tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Generate new tokens
        token_data = {"user_id": user_id, "email": email}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        return Token(access_token=new_access_token, refresh_token=new_refresh_token)
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
