"""AMP edition access allowlist.

Stored in the instance data root (allowlist.json). The AMP process ships
with only the owner/admin account. Unlisted callers get a Spanish
"sin acceso" response from the edition middleware.

Workroom never consults this file.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from app.edition import allowlist_path, assert_under_root, is_family_edition


def _owner_email() -> str:
    return (
        os.getenv("AMP_OWNER_EMAIL", "").strip()
        or os.getenv("FOUNDER_EMAIL", "").strip()
        or "empirebox2026@gmail.com"
    ).lower()


def _owner_username() -> str:
    return (os.getenv("AMP_OWNER_USERNAME", "").strip() or "owner").lower()


def _empty() -> dict:
    return {
        "entries": [
            {
                "email": _owner_email(),
                "username": _owner_username(),
                "role": "owner",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }


def load_allowlist() -> dict:
    path = allowlist_path()
    if is_family_edition():
        assert_under_root(path)
    if not path.exists():
        data = _empty()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return data
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = _empty()
    data.setdefault("entries", [])
    return data


def save_allowlist(data: dict) -> None:
    path = allowlist_path()
    if is_family_edition():
        assert_under_root(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_entries() -> list[dict]:
    return list(load_allowlist().get("entries") or [])


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def is_allowed(*, email: Optional[str] = None, username: Optional[str] = None) -> bool:
    email_n = _norm(email)
    user_n = _norm(username)
    if not email_n and not user_n:
        return False
    for entry in list_entries():
        if email_n and _norm(entry.get("email")) == email_n:
            return True
        if user_n and _norm(entry.get("username")) == user_n:
            return True
    return False


def entry_role(*, email: Optional[str] = None, username: Optional[str] = None) -> Optional[str]:
    email_n = _norm(email)
    user_n = _norm(username)
    for entry in list_entries():
        if email_n and _norm(entry.get("email")) == email_n:
            return entry.get("role") or "member"
        if user_n and _norm(entry.get("username")) == user_n:
            return entry.get("role") or "member"
    return None


def add_entry(*, email: Optional[str] = None, username: Optional[str] = None, role: str = "member") -> dict:
    email_n = _norm(email)
    user_n = _norm(username)
    if not email_n and not user_n:
        raise ValueError("Se requiere email o username")
    if role not in {"owner", "admin", "member"}:
        raise ValueError("Rol inválido")
    data = load_allowlist()
    for entry in data["entries"]:
        if email_n and _norm(entry.get("email")) == email_n:
            entry["role"] = role
            if user_n:
                entry["username"] = user_n
            save_allowlist(data)
            return entry
        if user_n and _norm(entry.get("username")) == user_n:
            entry["role"] = role
            if email_n:
                entry["email"] = email_n
            save_allowlist(data)
            return entry
    entry = {
        "email": email_n or None,
        "username": user_n or None,
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data["entries"].append(entry)
    save_allowlist(data)
    return entry


def remove_entry(*, email: Optional[str] = None, username: Optional[str] = None) -> bool:
    email_n = _norm(email)
    user_n = _norm(username)
    if not email_n and not user_n:
        raise ValueError("Se requiere email o username")
    data = load_allowlist()
    kept = []
    removed = False
    for entry in data["entries"]:
        match = (email_n and _norm(entry.get("email")) == email_n) or (
            user_n and _norm(entry.get("username")) == user_n
        )
        if match:
            if entry.get("role") == "owner" and _norm(entry.get("email")) == _owner_email():
                raise ValueError("No se puede quitar la cuenta owner")
            removed = True
            continue
        kept.append(entry)
    data["entries"] = kept
    save_allowlist(data)
    return removed
