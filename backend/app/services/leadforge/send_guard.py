"""LeadForge confirmed-send helpers. No EmailService calls live here.

Tokens are HMAC over sorted draft ids + expiry. Never log the token.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Iterable, Optional


CONFIRM_TTL_S = 600
MENSAJE_NEED_CONFIRM = (
    "Manito, primero confirma el envío. Pide la vista previa y luego confirma."
)
MENSAJE_BAD_TOKEN = (
    "Manito, esa confirmación ya no vale. Pide otra vista previa."
)
MENSAJE_SEND_DISABLED = (
    "Manito, el envío real está desactivado. Rafael decide cuándo se prende."
)
MENSAJE_LIMIT = (
    "Manito, ese lote pasa el tope de envíos. Baja la cantidad y vuelve a confirmar."
)


def real_send_enabled() -> bool:
    return (os.getenv("LEADFORGE_REAL_SEND_ENABLED") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def max_send_per_request() -> int:
    try:
        return max(1, int(os.getenv("LEADFORGE_MAX_SEND_PER_REQUEST") or "10"))
    except ValueError:
        return 10


def max_send_per_day() -> int:
    try:
        return max(1, int(os.getenv("LEADFORGE_MAX_SEND_PER_DAY") or "25"))
    except ValueError:
        return 25


def confirm_ttl_s() -> int:
    try:
        return max(60, int(os.getenv("LEADFORGE_CONFIRM_TTL_S") or str(CONFIRM_TTL_S)))
    except ValueError:
        return CONFIRM_TTL_S


def _secret() -> bytes:
    for key in ("LEADFORGE_CONFIRM_SECRET", "AMP_JWT_SECRET"):
        val = (os.getenv(key) or "").strip()
        if val:
            return val.encode("utf-8")
    try:
        from app.core.config import settings
        val = str(getattr(settings, "SECRET_KEY", "") or "").strip()
        if val:
            return val.encode("utf-8")
    except Exception:
        pass
    return b"leadforge-confirm-unconfigured"


def mask_email(email: str | None) -> str:
    raw = (email or "").strip()
    if "@" not in raw:
        return "***"
    local, domain = raw.split("@", 1)
    head = local[:1] if local else "*"
    return f"{head}***@{domain}"


def _normalize_ids(draft_ids: Iterable[int]) -> list[int]:
    return sorted({int(i) for i in draft_ids})


def make_confirm_token(draft_ids: Iterable[int], now: Optional[int] = None) -> tuple[str, int]:
    ids = _normalize_ids(draft_ids)
    exp = int(now if now is not None else time.time()) + confirm_ttl_s()
    payload = f"{','.join(map(str, ids))}|{exp}"
    sig = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}|{sig}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii"), exp


def read_confirm_token(token: str | None, now: Optional[int] = None) -> Optional[list[int]]:
    """Return draft ids when the token is well-formed, signed, and unexpired."""
    if not token or not isinstance(token, str):
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        ids_part, exp_s, sig = decoded.rsplit("|", 2)
        exp = int(exp_s)
        if exp < int(now if now is not None else time.time()):
            return None
        payload = f"{ids_part}|{exp_s}"
        expect = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
        if not ids_part:
            return []
        return _normalize_ids(int(x) for x in ids_part.split(",") if x)
    except Exception:
        return None


def token_matches(token: str | None, draft_ids: Iterable[int], now: Optional[int] = None) -> bool:
    got = read_confirm_token(token, now=now)
    if got is None:
        return False
    return got == _normalize_ids(draft_ids)
