"""Local reviewer auth and assignment store for TranscriptForge.

This is intentionally narrow: it protects the external TranscriptForge review
surface without changing the core founder/internal TranscriptForge flow.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path.home() / "empire-repo" / "backend" / "data" / "transcriptforge" / "reviewer_auth"
ACCOUNTS_PATH = BASE_DIR / "accounts.json"
SESSIONS_PATH = BASE_DIR / "sessions.json"
ASSIGNMENTS_PATH = BASE_DIR / "assignments.json"
PBKDF2_ITERATIONS = 200_000
SESSION_HOURS = 8


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _read_json(path: Path, default: Any) -> Any:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    path.chmod(0o600)


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    _, actual = _hash_password(password, salt_hex)
    return hmac.compare_digest(actual, expected_hash)


def accounts_configured() -> bool:
    return bool(_read_json(ACCOUNTS_PATH, {}))


def create_account(email: str, password: str, role: str = "reviewer", display_name: str = "") -> dict[str, Any]:
    email = email.strip().lower()
    role = role if role in {"viewer", "reviewer", "admin"} else "reviewer"
    if not email or "@" not in email:
        raise ValueError("valid email is required")
    if len(password) < 12:
        raise ValueError("password must be at least 12 characters")

    accounts = _read_json(ACCOUNTS_PATH, {})
    salt, password_hash = _hash_password(password)
    accounts[email] = {
        "email": email,
        "display_name": display_name.strip() or email,
        "role": role,
        "password_salt": salt,
        "password_hash": password_hash,
        "active": True,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _write_json(ACCOUNTS_PATH, accounts)
    return public_user(accounts[email])


def public_user(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": account.get("email"),
        "display_name": account.get("display_name") or account.get("email"),
        "role": account.get("role", "viewer"),
        "active": bool(account.get("active", True)),
    }


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    accounts = _read_json(ACCOUNTS_PATH, {})
    account = accounts.get(email.strip().lower())
    if not account or not account.get("active", True):
        return None
    if not _verify_password(password, account.get("password_salt", ""), account.get("password_hash", "")):
        return None
    return account


def create_session(email: str) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(hours=SESSION_HOURS)
    sessions = _read_json(SESSIONS_PATH, {})
    sessions[token] = {
        "email": email.strip().lower(),
        "created_at": _now_iso(),
        "expires_at": expires_at.isoformat(),
    }
    _write_json(SESSIONS_PATH, sessions)
    return {"token": token, "expires_at": expires_at.isoformat()}


def get_session_user(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    sessions = _read_json(SESSIONS_PATH, {})
    session = sessions.get(token)
    if not session:
        return None
    try:
        expires_at = datetime.fromisoformat(session.get("expires_at", ""))
    except Exception:
        expires_at = _now() - timedelta(seconds=1)
    if expires_at < _now():
        sessions.pop(token, None)
        _write_json(SESSIONS_PATH, sessions)
        return None

    accounts = _read_json(ACCOUNTS_PATH, {})
    account = accounts.get(session.get("email"))
    if not account or not account.get("active", True):
        return None
    return public_user(account)


def logout(token: str | None) -> None:
    if not token:
        return
    sessions = _read_json(SESSIONS_PATH, {})
    sessions.pop(token, None)
    _write_json(SESSIONS_PATH, sessions)


def assign_job(job_id: str, email: str) -> dict[str, Any]:
    email = email.strip().lower()
    assignments = _read_json(ASSIGNMENTS_PATH, {})
    assigned = set(assignments.get(job_id, []))
    assigned.add(email)
    assignments[job_id] = sorted(assigned)
    _write_json(ASSIGNMENTS_PATH, assignments)
    return {"job_id": job_id, "assigned_reviewers": assignments[job_id]}


def revoke_job(job_id: str, email: str) -> dict[str, Any]:
    email = email.strip().lower()
    assignments = _read_json(ASSIGNMENTS_PATH, {})
    assigned = set(assignments.get(job_id, []))
    assigned.discard(email)
    assignments[job_id] = sorted(assigned)
    _write_json(ASSIGNMENTS_PATH, assignments)
    return {"job_id": job_id, "assigned_reviewers": assignments[job_id]}


def reviewer_can_access_job(user: dict[str, Any], job_id: str) -> bool:
    if user.get("role") == "admin":
        return True
    assignments = _read_json(ASSIGNMENTS_PATH, {})
    return user.get("email") in set(assignments.get(job_id, []))


def assigned_job_ids(user: dict[str, Any], all_job_ids: list[str]) -> list[str]:
    if user.get("role") == "admin":
        return sorted(all_job_ids, reverse=True)
    assignments = _read_json(ASSIGNMENTS_PATH, {})
    allowed = {job_id for job_id, emails in assignments.items() if user.get("email") in emails}
    return [job_id for job_id in all_job_ids if job_id in allowed]
