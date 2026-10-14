"""
JWT Authentication routes for Empire SaaS.
Signup, login, refresh, logout, and current-user endpoints.
Uses the existing access_users table in SQLite.

Studio trusted-device endpoints live here too. They sit on top of the
existing PIN / password / role checks and do not replace them.
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import hmac
import os
import uuid
import logging

from app.db.database import get_db, dict_row
from app.utils.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
)
from app.services import trusted_devices as devices
from app.services.studio_login_guard import (
    record_studio_login_failure,
    record_studio_login_success,
    studio_login_lockout_message,
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

def _configured_founder_pin() -> str:
    """Return FOUNDER_PIN or empty. Never invent a default PIN.

    H62 FIX (2026-08-22): empty default — pre-fix this was "7777"
    (privilege-escalation literal). HOTFIX 4.2 only fixed tool_executor.py.
    """
    founder_pin = os.getenv("FOUNDER_PIN", "")
    if not founder_pin:
        logger.critical(
            "FOUNDER_PIN env var is UNSET. Founder sign-in refuses to issue "
            "a JWT until the operator configures it. Pre-fix this silently "
            "defaulted to a privilege-escalation literal. "
            "(H62 FIX, 2026-08-22)"
        )
    return founder_pin


def _pins_match(given: Optional[str], expected: str) -> bool:
    """Constant-time PIN compare. Hash first so length mismatches cannot 500."""
    left = hashlib.sha256((given or "").encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


def _require_founder_pin(pin: Optional[str]) -> None:
    founder_pin = _configured_founder_pin()
    # Dummy expected when unset so an empty submitted PIN cannot match.
    expected = founder_pin if founder_pin else "\x00UNSET_FOUNDER_PIN"
    matched = _pins_match(pin, expected)
    if not founder_pin or not matched:
        raise HTTPException(status_code=401, detail="Invalid founder PIN")


def _cookie_secure(request: Request) -> bool:
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    if forwarded:
        return forwarded == "https"
    return request.url.scheme == "https"


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        devices.SESSION_COOKIE,
        token,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )


def _set_device_cookie(response: Response, request: Request, raw_token: str, max_age: int) -> None:
    response.set_cookie(
        devices.DEVICE_COOKIE,
        raw_token,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(devices.SESSION_COOKIE, path="/")
    response.delete_cookie(devices.DEVICE_COOKIE, path="/")


def _request_meta(request: Request) -> dict:
    headers = {k.lower(): v for k, v in request.headers.items()}
    remote = request.client.host if request.client else None
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip": devices.client_ip(headers, remote),
        "location": devices.client_location(headers),
    }


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user.get("name"),
        "email": user.get("email"),
        "role": user.get("role"),
        "tier": user.get("tier", "lite"),
    }


def _issue_session(user: dict, request: Request, response: Response) -> dict:
    token_data = {"user_id": user["id"], "email": user.get("email") or ""}
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)
    _set_session_cookie(response, request, access)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": _public_user(user),
    }


def _load_user(user_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM access_users WHERE id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()
    return dict_row(row) if row else None


def _user_from_access_token(token: str) -> Optional[dict]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("user_id")
        if not user_id:
            return None
        return _load_user(user_id)
    except Exception:
        return None


def _get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Verify JWT from Authorization header, then session cookie, then device cookie."""
    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get(devices.SESSION_COOKIE)
    if token:
        user = _user_from_access_token(token)
        if user:
            return user
    device = devices.lookup_active(request.cookies.get(devices.DEVICE_COOKIE) or "")
    if device:
        return devices.user_from_device_row(device)
    raise HTTPException(status_code=401, detail="Not authenticated")


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
def login(data: LoginRequest, request: Request, response: Response):
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

        logger.info(f"User login: {data.email}")
        issued = _issue_session(user, request, response)
        return TokenResponse(
            access_token=issued["access_token"],
            refresh_token=issued["refresh_token"],
        )


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
def logout(response: Response):
    """Logout — discard client tokens and clear Studio session/device cookies."""
    _clear_auth_cookies(response)
    return {"status": "ok", "message": "Tokens should be discarded by the client"}


class FounderPinRequest(BaseModel):
    pin: str


@router.post("/founder-token")
def founder_token(data: FounderPinRequest, request: Request, response: Response):
    """Issue a JWT for the founder user after FOUNDER_PIN verification.

    This lets the Command Center obtain a real Bearer token for the founder
    without requiring email/password auth. The PIN must match FOUNDER_PIN.
    There is no default PIN.
    """
    _require_founder_pin(data.pin)

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, email, role, tier FROM access_users WHERE role = 'founder' AND is_active = 1 LIMIT 1"
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No founder user found")

    user = dict_row(row)
    return _issue_session(user, request, response)


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


# ── Studio sign-in + trusted devices ─────────────────────────────────

class StudioLoginRequest(BaseModel):
    pin: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class RememberDeviceRequest(BaseModel):
    device_name: Optional[str] = None


def _require_studio_role(user: dict) -> dict:
    if str(user.get("role") or "") not in devices.STUDIO_ROLES:
        raise HTTPException(status_code=403, detail="Studio access requires founder or admin")
    return user


def _authenticate_studio(data: StudioLoginRequest) -> dict:
    """Founder PIN or email/password. Does not bypass either check."""
    devices.ensure_schema()
    if data.pin:
        _require_founder_pin(data.pin)
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM access_users WHERE role = 'founder' AND is_active = 1 LIMIT 1"
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No founder user found")
        return dict_row(row)

    if data.email and data.password:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM access_users WHERE lower(email) = lower(?) AND is_active = 1",
                (str(data.email),),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user = dict_row(row)
        if not user.get("password_hash") or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return _require_studio_role(user)

    raise HTTPException(status_code=422, detail="Provide a founder PIN or email and password")


@router.post("/studio-login")
def studio_login(data: StudioLoginRequest, request: Request, response: Response):
    """Owner/operator sign-in for Empire Command Center (Studio)."""
    ip = _request_meta(request).get("ip") or "unknown"
    locked = studio_login_lockout_message(ip)
    if locked:
        raise HTTPException(status_code=429, detail=locked)
    try:
        user = _authenticate_studio(data)
    except HTTPException as exc:
        if exc.status_code == 401:
            lock_msg = record_studio_login_failure(ip)
            if lock_msg:
                raise HTTPException(status_code=429, detail=lock_msg) from exc
        raise
    record_studio_login_success(ip)
    issued = _issue_session(user, request, response)
    issued["remember_offered"] = True
    return issued


@router.get("/session")
def studio_session(request: Request, response: Response):
    """Return the current Studio session, minting one from a trusted device if needed."""
    devices.ensure_schema()
    session_token = request.cookies.get(devices.SESSION_COOKIE)
    if session_token:
        user = _user_from_access_token(session_token)
        if user and str(user.get("role") or "") in devices.STUDIO_ROLES:
            raw_device = request.cookies.get(devices.DEVICE_COOKIE)
            device = devices.lookup_active(raw_device or "")
            if device:
                expires = devices.roll_device(
                    device["id"],
                    **_request_meta(request),
                )
                max_age = int((expires - devices._utcnow()).total_seconds())
                _set_device_cookie(response, request, raw_device, max(max_age, 60))
            return {"authenticated": True, "user": _public_user(user), "via": "session"}

    raw_device = request.cookies.get(devices.DEVICE_COOKIE)
    device = devices.lookup_active(raw_device or "")
    if not device:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = devices.user_from_device_row(device)
    issued = _issue_session(user, request, response)
    expires = devices.roll_device(device["id"], **_request_meta(request))
    max_age = int((expires - devices._utcnow()).total_seconds())
    _set_device_cookie(response, request, raw_device, max(max_age, 60))
    issued["authenticated"] = True
    issued["via"] = "device"
    return issued


@router.post("/remember-device")
def remember_device(
    request: Request,
    response: Response,
    data: RememberDeviceRequest = RememberDeviceRequest(),
    user: dict = Depends(_get_current_user),
):
    """Issue a 90-day rolling httpOnly device cookie after a successful sign-in."""
    _require_studio_role(user)
    raw = devices.new_device_token()
    meta = _request_meta(request)
    record = devices.register_device(
        user["id"],
        raw,
        device_name=data.device_name,
        user_agent=meta["user_agent"],
        ip=meta["ip"],
        location=meta["location"],
    )
    _set_device_cookie(
        response,
        request,
        raw,
        max_age=devices.DEVICE_TTL_DAYS * 24 * 60 * 60,
    )
    return {"ok": True, "device": record}


@router.get("/devices")
def list_trusted_devices(request: Request, user: dict = Depends(_get_current_user)):
    _require_studio_role(user)
    items = devices.list_devices(user["id"], request.cookies.get(devices.DEVICE_COOKIE))
    return {"devices": items}


@router.delete("/devices/{device_id}")
def revoke_trusted_device(
    device_id: str,
    request: Request,
    response: Response,
    user: dict = Depends(_get_current_user),
):
    _require_studio_role(user)
    raw = request.cookies.get(devices.DEVICE_COOKIE)
    current = devices.lookup_active(raw or "")
    ok = devices.revoke_device(user["id"], device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found")
    if current and current.get("id") == device_id:
        response.delete_cookie(devices.DEVICE_COOKIE, path="/")
    return {"ok": True, "revoked": device_id}


@router.post("/devices/revoke-all")
def revoke_all_trusted_devices(
    response: Response,
    user: dict = Depends(_get_current_user),
):
    _require_studio_role(user)
    count = devices.revoke_all(user["id"])
    response.delete_cookie(devices.DEVICE_COOKIE, path="/")
    return {"ok": True, "revoked": count}
