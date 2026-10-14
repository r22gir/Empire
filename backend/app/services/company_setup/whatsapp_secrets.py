"""Edition WhatsApp secrets file. Values never go to the client or logs.

Precedence
----------
Process environment (systemd drop-ins / ``empire-backend-secrets.env``)
wins. The edition secrets file is used only when the matching env var is
unset or blank. ``apply_to_environ`` never overwrites a value already in
``os.environ``.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.edition import data_root_or_none, edition_name, is_family_edition, require_data_root
from app.services.company_setup.io import (
    atomic_write,
    edition_lock,
    ensure_dir,
    in_test,
    read_json,
)
from app.services.company_setup.store import edition_company_dir

logger = logging.getLogger("max.company_setup")

SECRET_KEYS = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
)

SECRET_VALUE_RE = re.compile(r"^[A-Za-z0-9_\-.|]+$")
E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")
MAX_TOKEN_LEN = 4096
MAX_ID_LEN = 256
MAX_NUMBERS = 20

_WEBHOOK_HITS: list[float] = []
_WEBHOOK_GUARD = threading.Lock()
_WEBHOOK_MAX = 10
_WEBHOOK_WINDOW = 60.0


class _SecretRedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        for key in SECRET_KEYS:
            val = (os.getenv(key) or "").strip()
            if val and val in msg:
                return False
        return True


logger.addFilter(_SecretRedactFilter())


class SecretValueError(ValueError):
    """Rejected WhatsApp secret or owner number."""


def validate_secret_value(value: str, *, kind: str = "token") -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    cap = MAX_TOKEN_LEN if kind == "token" else MAX_ID_LEN
    if len(raw) > cap:
        raise SecretValueError(f"{kind} exceeds {cap} characters")
    if not SECRET_VALUE_RE.fullmatch(raw):
        raise SecretValueError(
            f"{kind} may only use letters, numbers, and _ - . | (no spaces or newlines)"
        )
    return raw


def validate_e164(value: str) -> str:
    raw = (value or "").strip()
    if not E164_RE.fullmatch(raw):
        raise SecretValueError("Owner numbers must be E.164 like +17035551212")
    return raw


class WhatsAppKeysIn(BaseModel):
    """Founder form body. Extra keys forbidden. Blank means keep stored."""

    model_config = ConfigDict(extra="forbid")

    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_APP_SECRET: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    owner_numbers: Optional[list[str]] = None
    founder_phones: Optional[list[str]] = Field(default=None)

    @field_validator(
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        mode="before",
    )
    @classmethod
    def _secret_chars(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("secret must be a string")
        kind = "token" if len(str(v)) > 64 else "id"
        return validate_secret_value(v, kind=kind) or None

    @field_validator("owner_numbers", "founder_phones", mode="before")
    @classmethod
    def _phones(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            v = [p.strip() for p in v.replace("\n", ",").split(",") if p.strip()]
        if not isinstance(v, list):
            raise ValueError("owner_numbers must be a list")
        if len(v) > MAX_NUMBERS:
            raise ValueError(f"at most {MAX_NUMBERS} owner numbers")
        return [validate_e164(str(item)) for item in v]


def _assert_inside_edition(path: Path) -> Path:
    root = data_root_or_none()
    if root is None:
        from app.edition import EditionPathError

        raise EditionPathError("secrets path overrides require EMPIRE_DATA_DIR")
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        from app.edition import EditionPathError

        raise EditionPathError("secrets path must stay inside the edition data dir") from exc
    return resolved


def secrets_path() -> Path:
    """Edition secrets file. Never under the git tree."""
    override = (os.getenv("EMPIRE_WHATSAPP_SECRETS_PATH") or "").strip()
    if override:
        if not in_test():
            logger.warning("ignoring EMPIRE_WHATSAPP_SECRETS_PATH outside tests")
        else:
            return _assert_inside_edition(Path(override))
    if is_family_edition():
        root = require_data_root()
        return root / "secrets" / "whatsapp.json"
    root = data_root_or_none()
    if root is not None:
        return root / "secrets" / "whatsapp.json"
    if in_test():
        return edition_company_dir() / "secrets" / "whatsapp.json"
    return Path.home() / ".empire" / "secrets" / f"whatsapp-{edition_name()}.json"


def webhook_status_path() -> Path:
    return edition_company_dir() / "whatsapp_webhook_status.json"


def audit_path() -> Path:
    return edition_company_dir() / "audit.jsonl"


def mask_secret(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 4:
        return "••••"
    return f"••••{raw[-4:]}"


def get_secret(name: str) -> str:
    """Env (empire-backend-secrets.env / systemd) wins; file is fallback."""
    env_val = (os.getenv(name) or "").strip()
    if env_val:
        return env_val
    data = read_json(secrets_path())
    return str(data.get(name) or data.get(name.lower()) or "").strip()


def owner_numbers() -> list[str]:
    data = read_json(secrets_path())
    raw = data.get("owner_numbers") or data.get("founder_phones") or []
    if isinstance(raw, str):
        raw = [p.strip() for p in raw.split(",") if p.strip()]
    out: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                phone = str(item.get("phone") or item.get("number") or item.get("wa_id") or "").strip()
            else:
                phone = str(item).strip()
            if phone:
                out.append(phone)
    return out


def _write_audit(event: str, extra: dict[str, Any]) -> None:
    row = {
        "at": datetime.now(timezone.utc).isoformat(),
        "edition": edition_name(),
        "event": event,
        **extra,
    }
    path = audit_path()
    ensure_dir(path.parent, 0o700)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(__import__("json").dumps(row) + "\n")


def save_secrets(payload: dict[str, Any] | WhatsAppKeysIn) -> dict[str, Any]:
    """Write provided secrets. Blank values leave the stored one in place."""
    if isinstance(payload, WhatsAppKeysIn):
        incoming = payload.model_dump(exclude_none=True)
    else:
        incoming = WhatsAppKeysIn.model_validate(payload or {}).model_dump(exclude_none=True)
    path = secrets_path()
    with edition_lock(edition_company_dir()):
        current = read_json(path)
        for key in SECRET_KEYS:
            val = incoming.get(key)
            if isinstance(val, str) and val.strip():
                current[key] = val.strip()
        numbers = incoming.get("owner_numbers")
        if numbers is None:
            numbers = incoming.get("founder_phones")
        if numbers is not None:
            before = list(current.get("owner_numbers") or [])
            current["owner_numbers"] = list(numbers)
            if before != current["owner_numbers"]:
                _write_audit("owner_numbers_changed", {
                    "before_count": len(before),
                    "after_count": len(current["owner_numbers"]),
                })
                logger.info(
                    "whatsapp owner_numbers changed edition=%s before=%s after=%s",
                    edition_name(),
                    len(before),
                    len(current["owner_numbers"]),
                )
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        current["edition"] = edition_name()
        ensure_dir(path.parent, 0o700)
        atomic_write(path, current, mode=0o600, backup=True)
        apply_to_environ()
        logger.info(
            "whatsapp secrets updated edition=%s keys=%s numbers=%s",
            edition_name(),
            [k for k in SECRET_KEYS if bool(str(current.get(k) or "").strip())],
            len(current.get("owner_numbers") or []),
        )
        return status_panel()


def webhook_rate_ok() -> bool:
    now = time.monotonic()
    with _WEBHOOK_GUARD:
        recent = [t for t in _WEBHOOK_HITS if now - t < _WEBHOOK_WINDOW]
        _WEBHOOK_HITS[:] = recent
        if len(recent) >= _WEBHOOK_MAX:
            return False
        _WEBHOOK_HITS.append(now)
        return True


def record_webhook_challenge(*, ok: bool, reason: str = "") -> None:
    """Record only successful Meta subscription checks. Atomic + locked."""
    if not ok:
        return
    if not webhook_rate_ok():
        return
    row = {
        "verified": True,
        "reason": "ok",
        "at": datetime.now(timezone.utc).isoformat(),
        "edition": edition_name(),
    }
    with edition_lock(edition_company_dir()):
        atomic_write(webhook_status_path(), row, mode=0o600, backup=True)


def webhook_state() -> dict[str, Any]:
    data = read_json(webhook_status_path())
    return {
        "verified": bool(data.get("verified")),
        "reason": data.get("reason") or ("never_challenged" if not data else ""),
        "at": data.get("at") or "",
        "endpoint": "/api/v1/whatsapp/webhook",
    }


def status_panel() -> dict[str, Any]:
    """Which keys are set/missing. Masked display only — never raw values."""
    fields = []
    for key in SECRET_KEYS:
        raw = get_secret(key)
        fields.append({
            "key": key,
            "set": bool(raw),
            "masked": mask_secret(raw) if raw else "",
        })
    numbers = owner_numbers()
    missing = [f["key"] for f in fields if not f["set"]]
    return {
        "edition": edition_name(),
        "configured": not missing,
        "missing": missing,
        "fields": fields,
        "owner_numbers_count": len(numbers),
        "owner_numbers_set": bool(numbers),
        "webhook": webhook_state(),
        "secrets_file": "edition",
        "env_precedence": "process_env_wins",
    }


def apply_to_environ() -> None:
    """Fill blank env vars from the edition file. Never override a set env."""
    data = read_json(secrets_path())
    for key in SECRET_KEYS:
        if (os.getenv(key) or "").strip():
            continue
        val = str(data.get(key) or "").strip()
        if val:
            os.environ[key] = val
