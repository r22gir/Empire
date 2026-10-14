"""Edition WhatsApp secrets file. Values never go to the client or logs."""
from __future__ import annotations

import json
import logging
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.edition import edition_name, is_family_edition, require_data_root, data_root_or_none
from app.services.company_setup.store import edition_company_dir, _in_test

logger = logging.getLogger("max.company_setup")

SECRET_KEYS = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
)

_NEVER_LOG_KEYS = frozenset(SECRET_KEYS) | {
    "access_token",
    "app_secret",
    "verify_token",
    "phone_number_id",
}


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


def secrets_path() -> Path:
    """Edition secrets file. Never under the git tree."""
    override = (os.getenv("EMPIRE_WHATSAPP_SECRETS_PATH") or "").strip()
    if override:
        return Path(override).expanduser()
    if is_family_edition():
        root = require_data_root()
        return root / "secrets" / "whatsapp.json"
    root = data_root_or_none()
    if root is not None:
        return root / "secrets" / "whatsapp.json"
    if _in_test():
        return edition_company_dir() / "secrets" / "whatsapp.json"
    # Live founder without EMPIRE_DATA_DIR: home secrets, not the repo.
    return Path.home() / ".empire" / "secrets" / f"whatsapp-{edition_name()}.json"


def webhook_status_path() -> Path:
    return edition_company_dir() / "whatsapp_webhook_status.json"


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_secrets(data: dict[str, Any]) -> None:
    path = secrets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".wa-secret-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, path)
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def mask_secret(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 4:
        return "••••"
    return f"••••{raw[-4:]}"


def get_secret(name: str) -> str:
    """Return one secret. File wins, then env. Never logs the value."""
    data = _read(secrets_path())
    file_val = str(data.get(name) or data.get(name.lower()) or "").strip()
    if file_val:
        return file_val
    return (os.getenv(name) or "").strip()


def owner_numbers() -> list[str]:
    data = _read(secrets_path())
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


def save_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """Write provided secrets. Blank values leave the stored one in place."""
    current = _read(secrets_path())
    incoming = payload if isinstance(payload, dict) else {}
    for key in SECRET_KEYS:
        val = incoming.get(key)
        if val is None:
            val = incoming.get(key.lower())
        if isinstance(val, str) and val.strip():
            current[key] = val.strip()
    numbers = incoming.get("owner_numbers") or incoming.get("founder_phones")
    if numbers is not None:
        if isinstance(numbers, str):
            numbers = [p.strip() for p in numbers.split(",") if p.strip()]
        if isinstance(numbers, list):
            current["owner_numbers"] = [
                str(n).strip() for n in numbers if str(n).strip()
            ]
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    current["edition"] = edition_name()
    _write_secrets(current)
    apply_to_environ()
    logger.info(
        "whatsapp secrets updated edition=%s keys=%s numbers=%s",
        edition_name(),
        [k for k in SECRET_KEYS if bool(str(current.get(k) or "").strip())],
        len(current.get("owner_numbers") or []),
    )
    return status_panel()


def record_webhook_challenge(*, ok: bool, reason: str = "") -> None:
    row = {
        "verified": bool(ok),
        "reason": "ok" if ok else (reason or "rejected"),
        "at": datetime.now(timezone.utc).isoformat(),
        "edition": edition_name(),
    }
    path = webhook_status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def webhook_state() -> dict[str, Any]:
    data = _read(webhook_status_path())
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
    }


def apply_to_environ() -> None:
    """Load file secrets into process env so the channel can send. No logging."""
    data = _read(secrets_path())
    for key in SECRET_KEYS:
        val = str(data.get(key) or "").strip()
        if val:
            os.environ[key] = val
