"""
JWT Authentication routes for Empire SaaS.
Signup, login, refresh, logout, and current-user endpoints.
Uses the existing access_users table in SQLite.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
import logging

from app.db.database import get_db, dict_row
from app.utils.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
)

logger = logging.getLogger("empire.auth")
router = APIRouter(tags=["auth"])
security = HTTPBearer(auto_error=False)


# ── Schemas ──────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ──────────────────────────────────────────────────────────

def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and verify JWT from Authorization header."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM access_users WHERE id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="User not found")
            return dict_row(row)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Routes ───────────────────────────────────────────────────────────

@router.post("/signup", response_model=dict)
def signup(data: SignupRequest):
    """Create a new user account. Returns tokens."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM access_users WHERE email = ?", (data.email,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = uuid.uuid4().hex[:16]
        hashed = get_password_hash(data.password)

        conn.execute(
            """INSERT INTO access_users
               (id, name, email, password_hash, role, tier, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'viewer', 'lite', 1, datetime('now'), datetime('now'))""",
            (user_id, data.name, data.email, hashed),
        )

        token_data = {"user_id": user_id, "email": data.email}
        access = create_access_token(token_data)
        refresh = create_refresh_token(token_data)

        logger.info(f"New user signup: {data.email} [{user_id}]")
        return {
            "user": {"id": user_id, "name": data.name, "email": data.email, "role": "viewer", "tier": "lite"},
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    """Authenticate user and return JWT tokens."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM access_users WHERE email = ? AND is_active = 1",
            (data.email,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user = dict_row(row)
        if not user.get("password_hash") or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token_data = {"user_id": user["id"], "email": user["email"]}
        access = create_access_token(token_data)
        refresh = create_refresh_token(token_data)

        logger.info(f"User login: {data.email}")
        return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest):
    """Exchange refresh token for new token pair (rotation)."""
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("user_id")
        email = payload.get("email")
        if not user_id or not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Verify user still exists and is active
        with get_db() as conn:
            row = conn.execute(
                "SELECT id FROM access_users WHERE id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="User not found")

        # Issue new token pair (rotation)
        token_data = {"user_id": user_id, "email": email}
        new_access = create_access_token(token_data)
        new_refresh = create_refresh_token(token_data)

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
def logout():
    """Logout — client should discard tokens. Server-side token blacklist is a future enhancement."""
    return {"status": "ok", "message": "Tokens should be discarded by the client"}


@router.get("/me")
def get_me(user: dict = Depends(_get_current_user)):
    """Get current authenticated user profile."""
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user.get("email"),
        "role": user["role"],
        "tier": user.get("tier", "lite"),
        "desk": user.get("desk"),
        "tokens_used_this_month": user.get("tokens_used_this_month", 0),
    }
