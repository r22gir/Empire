"""Company setup interview — founder-only, edition-scoped, merge-only.

Replaces the single-shot POST /onboarding/setup that rebuilt business.json
from a dataclass and wiped business_phone / founder_phones.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.edition import edition_name, is_family_edition
from app.services.company_setup.auth import require_verified_founder
from app.services.company_setup.invites import create_invite, list_invites
from app.services.company_setup.schema import SECTION_IDS, configured_report, is_configured, section_by_id
from app.services.company_setup.store import (
    interview_state,
    load_merged,
    load_progress,
    mark_complete,
    review_payload,
    save_progress,
    save_section,
)
from app.services.company_setup.whatsapp_secrets import save_secrets, status_panel

router = APIRouter()


class SectionSave(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    mark_complete: bool = True


class ProgressSave(BaseModel):
    current_section: Optional[str] = None
    completed_sections: Optional[list[str]] = None
    completed: Optional[bool] = None


class InviteIn(BaseModel):
    email: str
    role: str = "viewer"
    name: str = ""


class WhatsAppKeysIn(BaseModel):
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_APP_SECRET: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    owner_numbers: Optional[list[str]] = None
    founder_phones: Optional[list[str]] = None


def _founder(request: Request) -> dict:
    return require_verified_founder(request)


@router.get("/onboarding/status")
async def onboarding_status(request: Request):
    """Configured check. Founder session required — does not leak the file."""
    _founder(request)
    data = load_merged()
    report = configured_report(data)
    return {
        "configured": is_configured(data),
        "edition": edition_name(),
        "family_edition": is_family_edition(),
        **report,
    }


@router.get("/onboarding/interview")
async def get_interview(request: Request):
    _founder(request)
    return interview_state()


@router.get("/onboarding/interview/review")
async def get_review(request: Request):
    _founder(request)
    return review_payload()


@router.put("/onboarding/interview/{section_id}")
async def put_section(section_id: str, body: SectionSave, request: Request):
    _founder(request)
    if section_by_id(section_id) is None:
        raise HTTPException(400, f"Unknown section. Must be one of: {SECTION_IDS}")
    try:
        save_section(section_id, body.data, mark_complete=body.mark_complete)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return interview_state()


@router.post("/onboarding/interview/progress")
async def post_progress(body: ProgressSave, request: Request):
    _founder(request)
    current = load_progress()
    if body.current_section:
        current["current_section"] = body.current_section
    if body.completed_sections is not None:
        current["completed_sections"] = body.completed_sections
    if body.completed is not None:
        current["completed"] = body.completed
    save_progress(current)
    return interview_state()


@router.post("/onboarding/interview/complete")
async def complete_interview(request: Request):
    _founder(request)
    mark_complete()
    return interview_state()


@router.get("/onboarding/team/invites")
async def get_invites(request: Request):
    _founder(request)
    return {"invites": list_invites()}


@router.post("/onboarding/team/invites")
async def post_invite(body: InviteIn, request: Request):
    """Record an invite. Never sends email or WhatsApp."""
    _founder(request)
    try:
        row = create_invite(body.email, body.role, body.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"invite": row, "sent": False}


@router.get("/onboarding/whatsapp")
async def get_whatsapp_keys(request: Request):
    _founder(request)
    return status_panel()


@router.post("/onboarding/whatsapp")
async def post_whatsapp_keys(body: WhatsAppKeysIn, request: Request):
    _founder(request)
    payload = body.model_dump(exclude_none=True)
    return save_secrets(payload)


@router.post("/onboarding/setup")
async def setup_business(request: Request, body: dict[str, Any] | None = None):
    """Legacy single-shot path. Merges identity only — never replaces the file."""
    _founder(request)
    payload = body if isinstance(body, dict) else {}
    identity = {
        "legal_name": payload.get("legal_name") or payload.get("business_name") or "",
        "dba": payload.get("dba") or payload.get("business_name") or "",
        "business_name": payload.get("business_name") or "",
        "owner_name": payload.get("owner_name") or "",
        "tagline": payload.get("business_tagline") or payload.get("tagline") or "",
    }
    save_section("identity", identity, mark_complete=True)
    contact = {}
    for src, dest in (
        ("business_address", "address"),
        ("business_phone", "phone"),
        ("business_email", "email"),
        ("timezone", "timezone"),
    ):
        if payload.get(src):
            contact[dest] = payload[src]
    if contact:
        save_section("contact", contact, mark_complete=True)
    state = interview_state()
    return {
        "success": True,
        "message": "Merged into company setup. Use the interview to finish.",
        "configured": state["status"]["configured"],
        "edition": edition_name(),
    }
