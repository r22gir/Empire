"""Edition-scoped company setup store.

The overlay file stores ONLY keys the interview changed. It is never a
full snapshot of config/business.json. Later edits to business.json for
keys the interview did not touch stay authoritative.

Family editions write only under their EMPIRE_DATA_DIR. Path overrides
(COMPANY_SETUP_BUSINESS_PATH) are honored only in tests and must stay
inside the edition data dir.
"""
from __future__ import annotations

import logging
import os
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
from app.services.company_setup.io import (
    atomic_write,
    edition_lock,
    ensure_dir,
    in_test,
    read_json,
)

# Re-export so tests can pin the gate without patching io.
from app.services.company_setup.merge import deep_merge, preserve_existing, public_view
from app.services.company_setup.schema import (
    DEFAULT_BRANDS,
    SECTION_IDS,
    SECTION_OVERLAY_KEYS,
    UnknownSectionKey,
    configured_report,
    section_by_id,
    validate_section_payload,
)

logger = logging.getLogger("max.company_setup")

_WORKROOM_CONFIG = Path(__file__).resolve().parents[2] / "config" / "business.json"


def edition_company_dir() -> Path:
    if is_family_edition():
        root = require_data_root()
        return ensure_dir(root / "company", 0o700)
    root = data_root_or_none()
    if root is None:
        if in_test():
            raise EditionPathError("company setup tests must set EMPIRE_DATA_DIR")
        return ensure_dir(_WORKROOM_CONFIG.parent / "company_overlay", 0o700)
    return ensure_dir(root / "company", 0o700)


def _assert_inside_edition(path: Path) -> Path:
    root = data_root_or_none()
    if root is None:
        raise EditionPathError("path overrides require EMPIRE_DATA_DIR")
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise EditionPathError("path override must stay inside the edition data dir") from exc
    return resolved


def _test_override(env_name: str, default: Path) -> Path:
    raw = (os.getenv(env_name) or "").strip()
    if not raw:
        return default
    if not in_test():
        logger.warning("ignoring %s outside tests", env_name)
        return default
    return _assert_inside_edition(Path(raw))


def business_json_path() -> Path:
    return _test_override("COMPANY_SETUP_BUSINESS_PATH", edition_company_dir() / "business.json")


def progress_path() -> Path:
    return edition_company_dir() / "setup_progress.json"


def _seed_path() -> Path | None:
    if in_test():
        raw = (os.getenv("COMPANY_SETUP_SEED_PATH") or "").strip()
        if not raw:
            return None
        return _assert_inside_edition(Path(raw))
    if is_family_edition() or not is_founder_edition():
        return None
    return _WORKROOM_CONFIG


def _seed_from_workroom() -> dict[str, Any]:
    path = _seed_path()
    if path is None:
        return {}
    return read_json(path)


def _read_overlay() -> dict[str, Any]:
    return read_json(business_json_path())


def load_merged() -> dict[str, Any]:
    overlay = _read_overlay()
    seed = _seed_from_workroom()
    return preserve_existing(seed, deep_merge(seed, overlay))


def load_progress() -> dict[str, Any]:
    data = read_json(progress_path())
    if not data:
        overlay = _read_overlay()
        data = overlay.get("company_setup") if isinstance(overlay.get("company_setup"), dict) else {}
    return {
        "current_section": data.get("current_section") or "identity",
        "completed_sections": [
            s for s in (data.get("completed_sections") or []) if s in SECTION_IDS
        ],
        "completed": bool(data.get("completed")),
        "updated_at": data.get("updated_at") or "",
        "edition": edition_name(),
    }


def _progress_row(progress: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_section": progress.get("current_section") or "identity",
        "completed_sections": [
            s for s in (progress.get("completed_sections") or []) if s in SECTION_IDS
        ],
        "completed": bool(progress.get("completed")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "edition": edition_name(),
    }


def _write_overlay(overlay: dict[str, Any]) -> None:
    atomic_write(business_json_path(), overlay, mode=0o600, backup=True)
    progress = overlay.get("company_setup") if isinstance(overlay.get("company_setup"), dict) else {}
    if progress:
        atomic_write(progress_path(), progress, mode=0o600, backup=True)


def save_progress(progress: dict[str, Any]) -> dict[str, Any]:
    with edition_lock(edition_company_dir()):
        overlay = _read_overlay()
        row = _progress_row(progress)
        overlay["company_setup"] = row
        _write_overlay(overlay)
        return row


def _section_patch(section_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Build overlay keys this section owns. Never copies seed fields."""
    body = dict(payload)
    owned = SECTION_OVERLAY_KEYS.get(section_id) or frozenset()
    patch: dict[str, Any] = {}
    if section_id == "identity":
        brands = body.get("brands") or DEFAULT_BRANDS
        identity = {
            "legal_name": body.get("legal_name") or "",
            "dba": body.get("dba") or "",
            "business_name": body.get("business_name") or "",
            "owner_name": body.get("owner_name") or "",
            "tagline": body.get("tagline") or body.get("business_tagline") or "",
            "brands": brands,
        }
        patch = {
            "identity": identity,
            "brands": brands,
            "legal_name": identity["legal_name"] or None,
            "dba": identity["dba"] or None,
        }
        name = identity["business_name"] or identity["dba"] or identity["legal_name"]
        if name:
            patch["business_name"] = name
        if identity["owner_name"]:
            patch["owner_name"] = identity["owner_name"]
        if identity["tagline"]:
            patch["business_tagline"] = identity["tagline"]
    elif section_id == "contact":
        contact = {
            "address": body.get("address") or body.get("business_address") or "",
            "phone": body.get("phone") or body.get("business_phone") or "",
            "email": body.get("email") or body.get("business_email") or "",
            "website": body.get("website") or "",
            "timezone": body.get("timezone") or "",
        }
        patch = {"contact": contact}
        if contact["address"]:
            patch["business_address"] = contact["address"]
        if contact["phone"]:
            patch["business_phone"] = contact["phone"]
        if contact["email"]:
            patch["business_email"] = contact["email"]
        if contact["website"]:
            patch["business_website"] = contact["website"]
        if contact["timezone"]:
            patch["timezone"] = contact["timezone"]
    elif section_id == "channels":
        patch = {"channels": body}
        phones = body.get("founder_phones") or body.get("owner_phones")
        if phones:
            patch["founder_phones"] = phones
            patch["owner_phones"] = phones
    elif section_id == "services":
        catalog = body.get("catalog") or body.get("services_catalog") or []
        patch = {"services_section": body, "services_catalog": catalog}
        if body.get("rate_cards"):
            patch["rate_cards"] = body["rate_cards"]
        if body.get("labor_rate") is not None:
            patch["labor_rate"] = body.get("labor_rate")
        try:
            from app.services.pricing.rate_cards import invalidate_rate_overlay_cache

            invalidate_rate_overlay_cache()
        except Exception:
            pass
    elif section_id == "fabric":
        patch = {"fabric": body}
        if body.get("next_number") is not None:
            patch["fabric_next_number"] = body.get("next_number")
        if body.get("code_format"):
            patch["fabric_code_format"] = body.get("code_format")
    elif section_id == "review":
        return {}
    else:
        patch = {section_id: body}
    return {k: v for k, v in patch.items() if k in owned and v is not None}


def save_section(section_id: str, payload: dict[str, Any], *, mark_complete: bool = True) -> dict[str, Any]:
    if section_by_id(section_id) is None:
        raise ValueError(f"Unknown company setup section: {section_id}")
    clean = validate_section_payload(section_id, payload if isinstance(payload, dict) else {})
    with edition_lock(edition_company_dir()):
        overlay = _read_overlay()
        patch = _section_patch(section_id, clean)
        overlay = deep_merge(overlay, patch)
        progress = load_progress()
        completed = list(progress.get("completed_sections") or [])
        if mark_complete and section_id not in completed and section_id != "review":
            completed.append(section_id)
        progress.update({
            "current_section": _next_section(section_id) if mark_complete else section_id,
            "completed_sections": completed,
            "completed": bool(progress.get("completed")),
        })
        overlay["company_setup"] = _progress_row(progress)
        _write_overlay(overlay)
        _maybe_mirror_patch(patch)
        logger.info(
            "company setup section saved edition=%s section=%s keys=%s",
            edition_name(),
            section_id,
            sorted(patch),
        )
        return load_merged()


def mark_complete() -> dict[str, Any]:
    with edition_lock(edition_company_dir()):
        overlay = _read_overlay()
        progress = load_progress()
        progress["completed"] = True
        progress["current_section"] = "review"
        overlay["company_setup"] = _progress_row(progress)
        _write_overlay(overlay)
        return load_merged()


def _next_section(section_id: str) -> str:
    try:
        idx = SECTION_IDS.index(section_id)
    except ValueError:
        return "identity"
    if idx + 1 < len(SECTION_IDS):
        return SECTION_IDS[idx + 1]
    return "review"


def _maybe_mirror_patch(patch: dict[str, Any]) -> None:
    """Founder live only: write THIS patch's keys into config/business.json.

    Never remirrors the whole overlay. Keys the interview did not change
    are left alone so later business.json edits survive.
    """
    if in_test() or is_family_edition() or not is_founder_edition():
        return
    if not patch or not _WORKROOM_CONFIG.exists():
        return
    current = read_json(_WORKROOM_CONFIG)
    mirrored = deep_merge(current, public_view(patch))
    mirrored = preserve_existing(current, mirrored)
    try:
        atomic_write(_WORKROOM_CONFIG, mirrored, mode=0o600, backup=True)
    except OSError as exc:
        logger.warning("company setup could not patch workroom business.json: %s", type(exc).__name__)


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
                **(section_by_id(sid) or {"id": sid}),
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


__all__ = [
    "UnknownSectionKey",
    "business_json_path",
    "edition_company_dir",
    "interview_state",
    "load_merged",
    "load_progress",
    "mark_complete",
    "review_payload",
    "save_progress",
    "save_section",
]
