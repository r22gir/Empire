"""AMP edition identity.

In the AMP edition a caller is identified only by:

* a Cloudflare Access JWT (``Cf-Access-Jwt-Assertion``, or the
  ``CF_Authorization`` cookie Cloudflare sets), verified against the team
  certs and ``CF_ACCESS_AUD``; or
* an AMP login session signed with ``AMP_JWT_SECRET`` and carried in the
  httpOnly ``amp_session`` cookie (or the same token as a bearer).

Client-supplied identity headers are not read. Email delivery is optional:
when SMTP is not configured, ``scripts/amp_allowlist.py login-link`` prints
a one-time link and nothing is sent.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import smtplib
import threading
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from jose import jwt
from jose.exceptions import JWTError

SESSION_COOKIE = "amp_session"
SESSION_AUDIENCE = "amp-access"
LOGIN_AUDIENCE = "amp-login"
SESSION_PURPOSE = "amp_access"
LOGIN_PURPOSE = "amp_login"
LOGIN_TTL_MINUTES = 15
SESSION_TTL_HOURS = 12
OWNER_SESSION_TTL_DAYS = max(1, int(os.getenv("AMP_OWNER_SESSION_TTL_DAYS", "365") or "365"))
MAX_CODE_ATTEMPTS = 5


def _is_production_runtime() -> bool:
    """Public family hosts and EMPIRE_ENV=production are production."""
    for key in ("EMPIRE_ENV", "ENVIRONMENT", "AMP_ENV"):
        if os.getenv(key, "").strip().lower() in {"production", "prod"}:
            return True
    public = (os.getenv("AMP_PUBLIC_BASE_URL") or "").strip().lower()
    return "amp.empirebox.store" in public or "maxine.empirebox.store" in public


def open_access_enabled() -> bool:
    """Local Dell convenience only. Never honor AMP_OPEN_ACCESS in production."""
    raw = os.getenv("AMP_OPEN_ACCESS", "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return False
    if _is_production_runtime():
        return False
    return True


def open_access_owner_email() -> str:
    """Resolve the configured owner from the existing allowlist, without bypassing role checks."""
    from app.services import amp_allowlist

    for entry in amp_allowlist.list_entries():
        if str(entry.get("role") or "").strip().lower() != "owner":
            continue
        email = _norm_email(str(entry.get("email") or ""))
        if email:
            return email
    return _norm_email(
        os.getenv("AMP_OWNER_EMAIL", "").strip()
        or os.getenv("FOUNDER_EMAIL", "").strip()
        or "empirebox2026@gmail.com"
    )

# Headers a browser (or anyone) can set. Never treat these as identity.
CLIENT_IDENTITY_HEADERS = frozenset({
    b"x-user-email",
    b"x-user-name",
    b"x-user-id",
    b"x-remote-user",
    b"x-email",
    b"x-authenticated-user",
    b"x-auth-request-email",
    b"x-auth-request-user",
    b"x-forwarded-email",
    b"x-forwarded-user",
    b"x-forwarded-preferred-username",
    b"cf-access-authenticated-user-email",
    b"cf-access-authenticated-user-id",
})

_lock = threading.Lock()
_certs_cache: dict = {"host": "", "keys": None, "at": 0.0}


class AmpAccessError(Exception):
    """Login could not be issued (missing secret, or email not allowlisted)."""


def _norm_email(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def jwt_secret() -> str:
    secret = os.getenv("AMP_JWT_SECRET", "").strip()
    if not secret:
        raise AmpAccessError("AMP_JWT_SECRET no está configurado")
    return secret


def cookie_secure() -> bool:
    raw = os.getenv("AMP_COOKIE_SECURE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def public_base_url() -> str:
    raw = (
        os.getenv("AMP_PUBLIC_BASE_URL", "").strip()
        or os.getenv("EMPIRE_API_BASE", "").strip()
        or "http://127.0.0.1:8011"
    ).rstrip("/")
    if raw.endswith("/api/v1"):
        raw = raw[: -len("/api/v1")]
    return raw


def login_redirect_path() -> str:
    raw = os.getenv("AMP_LOGIN_REDIRECT", "/login?listo=1").strip()
    return raw or "/login?listo=1"


def access_team_host() -> Optional[str]:
    """Host that serves the team's Access certs. Empty when unset (fail closed)."""
    raw = os.getenv("CF_ACCESS_TEAM_DOMAIN", "").strip().lower().rstrip("/")
    raw = raw.removeprefix("https://").removeprefix("http://").strip("/")
    if not raw:
        return None
    if raw.endswith(".cloudflareaccess.com"):
        return raw
    return f"{raw}.cloudflareaccess.com"


def access_aud() -> Optional[str]:
    raw = os.getenv("CF_ACCESS_AUD", "").strip()
    return raw or None


def fetch_access_certs(host: str) -> dict:
    """GET https://<team>.cloudflareaccess.com/cdn-cgi/access/certs."""
    now = time.time()
    if (
        _certs_cache["keys"]
        and _certs_cache["host"] == host
        and now - float(_certs_cache["at"]) < 3600
    ):
        return _certs_cache["keys"]
    import httpx

    resp = httpx.get(f"https://{host}/cdn-cgi/access/certs", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    _certs_cache.update(host=host, keys=data, at=now)
    return data


def verify_cloudflare_access_jwt(token: str) -> tuple[bool, str]:
    """Return ``(ok, email)``. Email is empty when the token is not trusted.

    Team domain and AUD come only from ``CF_ACCESS_TEAM_DOMAIN`` and
    ``CF_ACCESS_AUD``. Missing config fails closed (no baked-in Workroom AUD).
    """
    host = access_team_host()
    aud = access_aud()
    if not host or not aud or not token:
        return False, ""
    try:
        certs = fetch_access_certs(host)
        claims = jwt.decode(
            token,
            certs,
            algorithms=["RS256"],
            audience=aud,
            issuer=f"https://{host}",
            options={"verify_at_hash": False},
        )
    except Exception:
        return False, ""
    email = _norm_email(str(claims.get("email") or ""))
    if not email or "@" not in email:
        return False, ""
    return True, email


def _encode(payload: dict) -> str:
    return jwt.encode(payload, jwt_secret(), algorithm="HS256")


def _decode(token: str, audience: str) -> Optional[dict]:
    if not token:
        return None
    try:
        secret = jwt_secret()
    except AmpAccessError:
        return None
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], audience=audience)
    except JWTError:
        return None
    if not isinstance(claims, dict):
        return None
    return claims


def _is_owner(email: str) -> bool:
    from app.services import amp_allowlist

    return amp_allowlist.entry_role(email=email) == "owner"


def session_ttl_hours(email: str) -> int:
    return OWNER_SESSION_TTL_DAYS * 24 if _is_owner(email) else SESSION_TTL_HOURS


def create_session_token(email: str, *, ttl_hours: Optional[int] = None) -> str:
    email_n = _norm_email(email)
    ttl = session_ttl_hours(email_n) if ttl_hours is None else ttl_hours
    now = datetime.now(timezone.utc)
    payload = {
        "email": email_n,
        "purpose": SESSION_PURPOSE,
        "aud": SESSION_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl)).timestamp()),
    }
    return _encode(payload)


def session_email(token: str) -> Optional[str]:
    claims = _decode(token, SESSION_AUDIENCE)
    if not claims or claims.get("purpose") != SESSION_PURPOSE:
        return None
    email = _norm_email(str(claims.get("email") or ""))
    if not email:
        return None
    return email


def _challenges_path() -> Path:
    from app.edition import amp_app_dir, assert_under_root, is_family_edition

    path = amp_app_dir() / "login_challenges.json"
    if is_family_edition():
        assert_under_root(path)
    return path


def _load_challenges() -> dict:
    path = _challenges_path()
    if not path.exists():
        return {"challenges": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {"challenges": []}
    data.setdefault("challenges", [])
    return data


def _save_challenges(data: dict) -> None:
    from app.edition import assert_under_root, is_family_edition

    if not is_family_edition():
        return
    path = _challenges_path()
    assert_under_root(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def _purge(data: dict, now: float) -> None:
    kept = []
    for row in data.get("challenges") or []:
        if row.get("used"):
            continue
        if float(row.get("exp") or 0) <= now:
            continue
        kept.append(row)
    data["challenges"] = kept


def _code_hash(code: str) -> str:
    return hashlib.sha256(f"{jwt_secret()}:{code}".encode("utf-8")).hexdigest()


def issue_login_challenge(email: str, *, with_code: bool = True) -> dict:
    """Create a one-time login for an allowlisted email.

    Returns ``{"email", "code", "token", "link", "exp"}``. ``code`` is None
    when ``with_code`` is false (the admin CLI prints the link only).
    Raises ``AmpAccessError`` when the email is not allowlisted or the
    signing secret is missing.
    """
    from app.services import amp_allowlist

    email_n = _norm_email(email)
    if not email_n or "@" not in email_n:
        raise AmpAccessError("Correo inválido")
    # Touch the secret before writing, so a missing secret fails closed.
    jwt_secret()
    if not amp_allowlist.is_allowed(email=email_n):
        raise AmpAccessError("Sin acceso. El correo no está en la lista.")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=LOGIN_TTL_MINUTES)
    jti = secrets.token_urlsafe(24)
    code = f"{secrets.randbelow(1_000_000):06d}" if with_code else None
    token = _encode({
        "email": email_n,
        "purpose": LOGIN_PURPOSE,
        "aud": LOGIN_AUDIENCE,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    })
    row = {
        "email": email_n,
        "jti": jti,
        "code_hash": _code_hash(code) if code else None,
        "exp": int(exp.timestamp()),
        "used": False,
        "attempts": 0,
    }
    with _lock:
        data = _load_challenges()
        _purge(data, now.timestamp())
        data["challenges"].append(row)
        _save_challenges(data)
    return {
        "email": email_n,
        "code": code,
        "token": token,
        "link": f"{public_base_url()}/api/v1/amp/auth/magic?token={quote(token, safe='')}",
        "exp": int(exp.timestamp()),
    }


def _consume_jti(jti: str, email: str) -> bool:
    now = time.time()
    with _lock:
        data = _load_challenges()
        _purge(data, now)
        for row in data["challenges"]:
            if row.get("jti") != jti or row.get("used"):
                continue
            if _norm_email(row.get("email")) != email:
                return False
            if float(row.get("exp") or 0) <= now:
                return False
            row["used"] = True
            _save_challenges(data)
            return True
    return False


def redeem_magic_token(token: str) -> Optional[str]:
    """Consume a one-time magic-link token. Returns the email, or None."""
    from app.services import amp_allowlist

    claims = _decode(token, LOGIN_AUDIENCE)
    if not claims or claims.get("purpose") != LOGIN_PURPOSE:
        return None
    email = _norm_email(str(claims.get("email") or ""))
    jti = str(claims.get("jti") or "")
    if not email or not jti:
        return None
    if not amp_allowlist.is_allowed(email=email):
        return None
    if not _consume_jti(jti, email):
        return None
    return email


def redeem_code(email: str, code: str) -> Optional[str]:
    """Consume a one-time code. Returns the email, or None."""
    from app.services import amp_allowlist

    email_n = _norm_email(email)
    code_n = (code or "").strip()
    if not email_n or not code_n:
        return None
    if not amp_allowlist.is_allowed(email=email_n):
        return None
    try:
        digest = _code_hash(code_n)
    except AmpAccessError:
        return None
    now = time.time()
    with _lock:
        data = _load_challenges()
        _purge(data, now)
        matches = []
        for row in data["challenges"]:
            if row.get("used"):
                continue
            if _norm_email(row.get("email")) != email_n:
                continue
            if not row.get("code_hash"):
                continue
            if float(row.get("exp") or 0) <= now:
                continue
            matches.append(row)
        if not matches:
            _save_challenges(data)
            return None
        for match in matches:
            if hmac.compare_digest(str(match.get("code_hash")), digest):
                match["used"] = True
                _save_challenges(data)
                return email_n
        newest = matches[-1]
        newest["attempts"] = int(newest.get("attempts") or 0) + 1
        if newest["attempts"] >= MAX_CODE_ATTEMPTS:
            newest["used"] = True
        _save_challenges(data)
        return None


def mail_configured() -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    return bool(host and user and password)


def try_send_login_email(email: str, *, link: str, code: Optional[str]) -> bool:
    """Send the login code when SMTP is configured. Sends nothing otherwise."""
    if not mail_configured():
        return False
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587") or "587")
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip() or user
    msg = EmailMessage()
    msg["Subject"] = "Tu acceso a AMP"
    msg["From"] = sender
    msg["To"] = email
    code_line = f"Código: {code}\n" if code else ""
    msg.set_content(
        "Acceso a la edición AMP (Actitud Mental Positiva).\n\n"
        f"{code_line}"
        f"Enlace de un solo uso:\n{link}\n\n"
        "Si no pediste este acceso, ignora este mensaje.\n"
    )
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return True


def request_login_email(email: str) -> bool:
    """Issue a code when the email is allowlisted and SMTP is configured.

    Returns True only when a message was handed to SMTP. A missing address,
    an unknown address, and unconfigured mail all return False and send
    nothing. Unconfigured mail does not store a code: the admin CLI prints
    the link instead. Callers still show the same Spanish response.
    """
    if not mail_configured():
        return False
    try:
        issued = issue_login_challenge(email, with_code=True)
    except AmpAccessError:
        return False
    try:
        return try_send_login_email(issued["email"], link=issued["link"], code=issued["code"])
    except Exception:
        return False


def apply_session_cookie(response, email: str) -> str:
    ttl_hours = session_ttl_hours(email)
    token = create_session_token(email, ttl_hours=ttl_hours)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        max_age=ttl_hours * 3600,
        path="/",
    )
    return token


def clear_session_cookie(response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/", secure=cookie_secure(), httponly=True, samesite="lax")


def header_value(scope, name: str) -> Optional[str]:
    want = name.lower().encode("latin-1")
    for key, value in scope.get("headers") or []:
        if key.lower() == want:
            return value.decode("latin-1")
    return None


def cookie_value(scope, name: str) -> Optional[str]:
    raw = header_value(scope, "cookie")
    if not raw:
        return None
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return None


def strip_client_identity_headers(scope) -> None:
    """Drop spoofable identity headers before the rest of the app reads them."""
    headers = scope.get("headers") or []
    scope["headers"] = [
        (key, value)
        for key, value in headers
        if key.lower() not in CLIENT_IDENTITY_HEADERS
    ]


def resolve_request_email(scope) -> tuple[Optional[str], str]:
    """Identity for one request: ``(email, via)``.

    A valid Cloudflare JWT is authoritative. If its email is present, the
    session is not consulted (the allowlist check still applies). An invalid
    or absent Access token falls through to the AMP session.
    """
    if open_access_enabled():
        return open_access_owner_email(), "open_access"

    cf_token = header_value(scope, "cf-access-jwt-assertion") or cookie_value(scope, "CF_Authorization")
    if cf_token:
        ok, email = verify_cloudflare_access_jwt(cf_token)
        if ok and email:
            return email, "cloudflare"
    session_token = cookie_value(scope, SESSION_COOKIE) or ""
    if not session_token:
        auth = header_value(scope, "authorization") or ""
        if auth.lower().startswith("bearer "):
            session_token = auth.split(" ", 1)[1].strip()
    email = session_email(session_token) if session_token else None
    if email:
        return email, "session"
    return None, ""
