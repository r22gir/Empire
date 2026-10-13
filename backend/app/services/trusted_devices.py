"""Trusted-device tokens for Studio owner sign-in.

After a successful founder/admin sign-in, the owner can remember this
device. The raw token lives only in an httpOnly cookie; the server stores
an HMAC-SHA256 hash. Tokens last 90 days and roll forward on each use.
Revoke (or revoke-all) invalidates immediately — the next request fails.

This module does not weaken existing PIN / password / allowlist checks.
A device token is issued only after those checks already passed.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import unquote_plus

from app.config import settings
from app.db.database import get_db, dict_row

logger = logging.getLogger("empire.trusted_devices")

DEVICE_COOKIE = "empire_device"
SESSION_COOKIE = "empire_session"
DEVICE_TTL_DAYS = 90
STUDIO_ROLES = frozenset({"founder", "admin"})

_SCHEMA_READY = False

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS trusted_devices (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    device_name TEXT,
    user_agent TEXT,
    last_ip TEXT,
    last_location TEXT,
    last_used_at TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES access_users(id)
)
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def hash_device_token(raw_token: str) -> str:
    """HMAC-SHA256 of the raw cookie value. Never store the raw token."""
    secret = (
        getattr(settings, "SECRET_KEY", None)
        or getattr(settings, "secret_key", None)
        or "empire-dev-secret"
    )
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    return hmac.new(secret, raw_token.encode("utf-8"), hashlib.sha256).hexdigest()


def new_device_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_schema() -> None:
    """Idempotent table + column ensure. Safe on empty and live DBs."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS access_users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                telegram_chat_id TEXT UNIQUE,
                desk TEXT,
                pin_hash TEXT,
                failed_pin_attempts INTEGER DEFAULT 0,
                locked_until TEXT,
                is_active INTEGER DEFAULT 1,
                email TEXT,
                password_hash TEXT,
                tier TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        conn.execute(_CREATE_TABLE)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trusted_devices_user "
            "ON trusted_devices(user_id, revoked_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trusted_devices_hash "
            "ON trusted_devices(token_hash)"
        )
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(access_users)").fetchall()
        }
        for col, decl in (
            ("email", "TEXT"),
            ("password_hash", "TEXT"),
            ("tier", "TEXT"),
            ("is_active", "INTEGER DEFAULT 1"),
        ):
            if col not in cols:
                conn.execute(f"ALTER TABLE access_users ADD COLUMN {col} {decl}")
    _SCHEMA_READY = True


def reset_schema_cache() -> None:
    """Test helper — do not use in production request paths."""
    global _SCHEMA_READY
    _SCHEMA_READY = False


def parse_device_name(user_agent: Optional[str]) -> str:
    ua = user_agent or ""
    browser = "Browser"
    device = "Device"
    if "Edg/" in ua or "Edge/" in ua:
        browser = "Edge"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"
    elif "Chrome/" in ua or "CriOS/" in ua:
        browser = "Chrome"
    elif "Firefox/" in ua or "FxiOS/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua:
        browser = "Safari"
    if "iPhone" in ua:
        device = "iPhone"
    elif "iPad" in ua:
        device = "iPad"
    elif "Android" in ua:
        device = "Android"
    elif "Mac OS" in ua or "Macintosh" in ua:
        device = "Mac"
    elif "Windows" in ua:
        device = "Windows"
    elif "Linux" in ua:
        device = "Linux"
    return f"{browser} on {device}"


def client_ip(headers: dict, remote: Optional[str] = None) -> Optional[str]:
    cf = (headers.get("cf-connecting-ip") or "").strip()
    if cf:
        return cf
    forwarded = (headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    real = (headers.get("x-real-ip") or "").strip()
    if real:
        return real
    return remote


def client_location(headers: dict) -> Optional[str]:
    city = headers.get("cf-ipcity") or headers.get("x-vercel-ip-city")
    country = headers.get("cf-ipcountry") or headers.get("x-vercel-ip-country")
    if city:
        city = unquote_plus(str(city)).strip()
    if country:
        country = str(country).strip()
    if country and country.upper() in {"XX", "T1", ""}:
        country = None
    if city and country:
        return f"{city}, {country}"
    if city:
        return city
    if country:
        return country
    return None


def _row_public(row: dict, current_hash: Optional[str] = None) -> dict:
    return {
        "id": row["id"],
        "device_name": row.get("device_name") or "Unknown device",
        "user_agent": row.get("user_agent"),
        "last_used_at": row.get("last_used_at") or row.get("created_at"),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
        "location": row.get("last_location"),
        "current": bool(current_hash and row.get("token_hash") == current_hash),
    }


def register_device(
    user_id: str,
    raw_token: str,
    *,
    device_name: Optional[str],
    user_agent: Optional[str],
    ip: Optional[str],
    location: Optional[str],
) -> dict:
    ensure_schema()
    now = _utcnow()
    expires = now + timedelta(days=DEVICE_TTL_DAYS)
    device_id = secrets.token_hex(8)
    token_hash = hash_device_token(raw_token)
    name = (device_name or "").strip() or parse_device_name(user_agent)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO trusted_devices
               (id, user_id, token_hash, device_name, user_agent, last_ip,
                last_location, last_used_at, created_at, expires_at, revoked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
            (
                device_id,
                user_id,
                token_hash,
                name[:120],
                (user_agent or "")[:400],
                ip,
                location,
                _iso(now),
                _iso(now),
                _iso(expires),
            ),
        )
    logger.info("Trusted device registered user=%s device=%s", user_id, device_id)
    return {
        "id": device_id,
        "device_name": name,
        "expires_at": _iso(expires),
        "location": location,
        "current": True,
    }


def lookup_active(raw_token: str) -> Optional[dict]:
    """Return the device+user row if the cookie is valid, else None.

    Revoked or expired tokens are treated as missing (immediate invalidation).
    """
    if not raw_token:
        return None
    ensure_schema()
    token_hash = hash_device_token(raw_token)
    now = _utcnow()
    with get_db() as conn:
        row = conn.execute(
            """SELECT d.*, u.id AS uid, u.name AS user_name, u.email, u.role,
                      u.tier, u.is_active
               FROM trusted_devices d
               JOIN access_users u ON u.id = d.user_id
               WHERE d.token_hash = ?""",
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        device = dict_row(row)
    if device.get("revoked_at"):
        return None
    expires = _parse_iso(device.get("expires_at"))
    if expires and expires < now:
        return None
    if not device.get("is_active"):
        return None
    if str(device.get("role") or "") not in STUDIO_ROLES:
        return None
    return device


def roll_device(
    device_id: str,
    *,
    ip: Optional[str],
    location: Optional[str],
    user_agent: Optional[str],
) -> datetime:
    """Extend expiry 90 days from now and refresh last-used metadata."""
    ensure_schema()
    now = _utcnow()
    expires = now + timedelta(days=DEVICE_TTL_DAYS)
    with get_db() as conn:
        conn.execute(
            """UPDATE trusted_devices
               SET last_used_at = ?, expires_at = ?,
                   last_ip = COALESCE(?, last_ip),
                   last_location = COALESCE(?, last_location),
                   user_agent = COALESCE(?, user_agent)
               WHERE id = ? AND revoked_at IS NULL""",
            (_iso(now), _iso(expires), ip, location, user_agent, device_id),
        )
    return expires


def list_devices(user_id: str, current_raw_token: Optional[str] = None) -> list[dict]:
    ensure_schema()
    current_hash = hash_device_token(current_raw_token) if current_raw_token else None
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM trusted_devices
               WHERE user_id = ? AND revoked_at IS NULL
               ORDER BY datetime(COALESCE(last_used_at, created_at)) DESC""",
            (user_id,),
        ).fetchall()
    return [_row_public(dict_row(r), current_hash) for r in rows]


def revoke_device(user_id: str, device_id: str) -> bool:
    """Revoke one device. Returns True if a live row was invalidated."""
    ensure_schema()
    now = _iso(_utcnow())
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE trusted_devices
               SET revoked_at = ?
               WHERE id = ? AND user_id = ? AND revoked_at IS NULL""",
            (now, device_id, user_id),
        )
        changed = cur.rowcount > 0
    if changed:
        logger.info("Trusted device revoked user=%s device=%s", user_id, device_id)
    return changed


def revoke_all(user_id: str) -> int:
    ensure_schema()
    now = _iso(_utcnow())
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE trusted_devices
               SET revoked_at = ?
               WHERE user_id = ? AND revoked_at IS NULL""",
            (now, user_id),
        )
        count = cur.rowcount
    logger.info("Trusted devices revoke-all user=%s count=%s", user_id, count)
    return count


def user_from_device_row(device: dict) -> dict[str, Any]:
    return {
        "id": device.get("uid") or device.get("user_id"),
        "name": device.get("user_name") or device.get("name"),
        "email": device.get("email"),
        "role": device.get("role"),
        "tier": device.get("tier") or "lite",
    }
