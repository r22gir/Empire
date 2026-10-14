"""Edition-scoped company setup store.

Founder edition (studio / workroom / unset): overlay under EMPIRE_DATA_DIR
when set. Live Workroom also merges into config/business.json — never in
tests, never for family editions.

Family editions write only under their EMPIRE_DATA_DIR. They never open
the Workroom business.json for write.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.edition import (
    EditionPathError,
    data_root_or_none,
    edition_name,
    is_family_edition,
    is_founder_edition,
    require_data_root,
)
from app.services.company_setup.merge import deep_merge, preserve_existing, public_view
from app.services.company_setup.schema import (
    DEFAULT_BRANDS,
    SECTION_IDS,
    configured_report,
    section_by_id,
)

logger = logging.getLogger("max.company_setup")

_WORKROOM_CONFIG = Path(__file__).resolve().parents[2] / "config" / "business.json"


def _in_test() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("EMPIRE_TEST_GUARD_LOG"))


def edition_company_dir() -> Path:
    if is_family_edition():
        root = require_data_root()
        path = root / "company"
        path.mkdir(parents=True, exist_ok=True)
        return path
    root = data_root_or_none()
    if root is None:
        if _in_test():
            raise EditionPathError("company setup tests must set EMPIRE_DATA_DIR")
        # Live founder without EMPIRE_DATA_DIR: keep overlay next to config.
        path = _WORKROOM_CONFIG.parent / "company_overlay"
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = root / "company"
    path.mkdir(parents=True, exist_ok=True)
    return path


def business_json_path() -> Path:
    override = (os.getenv("COMPANY_SETUP_BUSINESS_PATH") or "").strip()
    if override:
        return Path(override).expanduser()
    return edition_company_dir() / "business.json"


def progress_path() -> Path:
    return edition_company_dir() / "setup_progress.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".company-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _seed_from_workroom() -> dict[str, Any]:
    """Read Workroom business.json for founder edition only. Never in tests."""
    if _in_test() or is_family_edition() or not is_founder_edition():
        return {}
    return _read_json(_WORKROOM_CONFIG)


def load_merged() -> dict[str, Any]:
    overlay = _read_json(business_json_path())
    seed = _seed_from_workroom()
    merged = preserve_existing(seed, deep_merge(seed, overlay))
    return merged


def load_progress() -> dict[str, Any]:
    data = _read_json(progress_path())
    if not data:
        merged = load_merged()
        data = merged.get("company_setup") if isinstance(merged.get("company_setup"), dict) else {}
    return {
        "current_section": data.get("current_section") or "identity",
        "completed_sections": [
            s for s in (data.get("completed_sections") or []) if s in SECTION_IDS
        ],
        "completed": bool(data.get("completed")),
        "updated_at": data.get("updated_at") or "",
        "edition": edition_name(),
    }


def save_progress(progress: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "current_section": progress.get("current_section") or "identity",
        "completed_sections": [
            s for s in (progress.get("completed_sections") or []) if s in SECTION_IDS
        ],
        "completed": bool(progress.get("completed")),
        "updated_at": now,
        "edition": edition_name(),
    }
    _atomic_write(progress_path(), row)
    existing = load_merged()
    existing["company_setup"] = row
    _atomic_write(business_json_path(), existing)
    return row


def _apply_section(existing: dict[str, Any], section_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Map a section payload onto business.json keys without wiping others."""
    body = dict(payload or {})
    body.pop("whatsapp_secrets", None)
    body.pop("secrets", None)
    if section_id == "identity":
        brands = body.get("brands")
        if not brands:
            brands = existing.get("brands") or DEFAULT_BRANDS
        patch = {
            "identity": body,
            "brands": brands,
            "legal_name": body.get("legal_name") or existing.get("legal_name"),
            "dba": body.get("dba") or existing.get("dba"),
        }
        if body.get("legal_name") or body.get("dba") or body.get("business_name"):
            patch["business_name"] = (
                body.get("business_name")
                or body.get("dba")
                or body.get("legal_name")
            )
        if body.get("owner_name"):
            patch["owner_name"] = body.get("owner_name")
        if body.get("tagline") or body.get("business_tagline"):
            patch["business_tagline"] = body.get("tagline") or body.get("business_tagline")
        return preserve_existing(existing, deep_merge(existing, patch))
    if section_id == "contact":
        patch = {
            "contact": body,
            "business_address": body.get("address") or body.get("business_address") or existing.get("business_address"),
            "business_phone": body.get("phone") or body.get("business_phone") or existing.get("business_phone"),
            "business_email": body.get("email") or body.get("business_email") or existing.get("business_email"),
            "business_website": body.get("website") or existing.get("business_website"),
        }
        if body.get("timezone"):
            patch["timezone"] = body.get("timezone")
        return preserve_existing(existing, deep_merge(existing, patch))
    if section_id == "channels":
        patch = {"channels": body}
        phones = body.get("founder_phones") or body.get("owner_phones")
        if phones:
            patch["founder_phones"] = phones
            patch["owner_phones"] = phones
        # Do not let an empty channels payload wipe stored founder phones.
        return preserve_existing(existing, deep_merge(existing, patch))
    if section_id == "services":
        patch = {"services_catalog": body.get("catalog") or body.get("services_catalog") or body.get("services") or []}
        if body.get("rate_cards"):
            patch["rate_cards"] = body["rate_cards"]
        if "labor_rate" in body and body.get("labor_rate") is not None:
            patch["labor_rate"] = body.get("labor_rate")
        return preserve_existing(existing, deep_merge(existing, {**body, **patch, "services_section": body}))
    if section_id == "fabric":
        patch = {"fabric": body}
        if body.get("next_number") is not None:
            patch["fabric_next_number"] = body.get("next_number")
        if body.get("code_format"):
            patch["fabric_code_format"] = body.get("code_format")
        return preserve_existing(existing, deep_merge(existing, patch))
    if section_id == "review":
        return existing
    return preserve_existing(existing, deep_merge(existing, {section_id: body}))


def save_section(section_id: str, payload: dict[str, Any], *, mark_complete: bool = True) -> dict[str, Any]:
    if section_by_id(section_id) is None:
        raise ValueError(f"Unknown company setup section: {section_id}")
    existing = load_merged()
    merged = _apply_section(existing, section_id, payload if isinstance(payload, dict) else {})
    progress = load_progress()
    completed = list(progress.get("completed_sections") or [])
    if mark_complete and section_id not in completed and section_id != "review":
        completed.append(section_id)
    nxt = _next_section(section_id)
    progress.update({
        "current_section": nxt if mark_complete else section_id,
        "completed_sections": completed,
        "completed": bool(progress.get("completed")),
    })
    merged["company_setup"] = {
        "current_section": progress["current_section"],
        "completed_sections": completed,
        "completed": bool(progress.get("completed")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "edition": edition_name(),
    }
    path = business_json_path()
    _atomic_write(path, merged)
    _atomic_write(progress_path(), merged["company_setup"])
    _maybe_mirror_workroom(merged)
    logger.info(
        "company setup section saved edition=%s section=%s path=%s",
        edition_name(),
        section_id,
        path.name,
    )
    return merged


def mark_complete() -> dict[str, Any]:
    existing = load_merged()
    progress = load_progress()
    progress["completed"] = True
    progress["current_section"] = "review"
    existing["company_setup"] = {
        **progress,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "edition": edition_name(),
    }
    _atomic_write(business_json_path(), existing)
    _atomic_write(progress_path(), existing["company_setup"])
    _maybe_mirror_workroom(existing)
    return existing


def _next_section(section_id: str) -> str:
    try:
        idx = SECTION_IDS.index(section_id)
    except ValueError:
        return "identity"
    if idx + 1 < len(SECTION_IDS):
        return SECTION_IDS[idx + 1]
    return "review"


def _maybe_mirror_workroom(merged: dict[str, Any]) -> None:
    """Founder edition live only: merge public fields into config/business.json."""
    if _in_test() or is_family_edition() or not is_founder_edition():
        return
    if not _WORKROOM_CONFIG.exists():
        return
    current = _read_json(_WORKROOM_CONFIG)
    mirrored = preserve_existing(current, deep_merge(current, public_view(merged)))
    try:
        _atomic_write(_WORKROOM_CONFIG, mirrored)
    except OSError as exc:
        logger.warning("company setup could not mirror workroom business.json: %s", type(exc).__name__)


def interview_state() -> dict[str, Any]:
    merged = load_merged()
    progress = load_progress()
    report = configured_report(merged)
    return {
        "edition": edition_name(),
        "family_edition": is_family_edition(),
        "founder_edition": is_founder_edition(),
        "progress": progress,
        "sections": [
            {
                **section_by_id(sid),
                "done": sid in (progress.get("completed_sections") or []) or (
                    sid == "review" and progress.get("completed")
                ),
            }
            for sid in SECTION_IDS
        ],
        "data": public_view(merged),
        "status": report,
        "defaults": {"brands": DEFAULT_BRANDS},
    }


def review_payload() -> dict[str, Any]:
    state = interview_state()
    return {
        "edition": state["edition"],
        "status": state["status"],
        "progress": state["progress"],
        "data": state["data"],
        "sections": state["sections"],
    }
