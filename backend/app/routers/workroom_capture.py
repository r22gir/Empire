"""Founder door: Workroom inbox → LeadForge prospect + ForgeCRM contact + quote draft.

Mounted at /api/v1/workroom-capture. Does not send email.
Keeps the founder inbox door off the public LeadForge intake alias.
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.workroom_capture import (
    CONSENT_VALUES,
    DEFAULT_CAMPAIGN,
    DEFAULT_OWNER,
    INTAKE_STATUSES,
    JOB_TYPES,
    SOURCES,
    CaptureError,
    create_intake,
    get_intake,
    list_intakes,
    open_workroom_quote,
    update_intake,
)

router = APIRouter(prefix="/workroom-capture", tags=["workroom-capture"])


class WorkroomIntakeCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    firm_name: Optional[str] = None
    city_region: Optional[str] = None
    job_type: Literal[
        "drapery_romans",
        "banquette",
        "soft_seating",
        "headboard",
        "mixed",
        "other",
    ]
    message: str
    photo_urls: Optional[list[str]] = None
    source: Literal[
        "meta_ad",
        "instagram",
        "houzz",
        "outreach",
        "web",
        "referral",
        "other",
    ]
    utm_campaign: Optional[str] = None
    consent_contact: Literal["yes", "no", "unknown"]
    business: str = "workroom"
    campaign: str = DEFAULT_CAMPAIGN
    owner: Optional[str] = DEFAULT_OWNER
    next_action: Optional[str] = None
    notes: Optional[str] = None
    received_at: Optional[str] = None


class WorkroomIntakeUpdate(BaseModel):
    status: Optional[
        Literal["new", "needs_info", "quoting", "quoted", "won", "lost", "hold"]
    ] = None
    next_action: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[str] = None
    last_contacted_at: Optional[str] = None


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except CaptureError as exc:
        raise HTTPException(exc.status, exc.message) from exc


@router.get("/intake")
def list_workroom_intake(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Recent manual captures. In-app only — nothing is emailed."""
    return _call(list_intakes, status, limit)


@router.post("/intake")
def post_workroom_intake(body: WorkroomIntakeCreate):
    """Create a LeadForge event and upsert ForgeCRM by email. Does not send email."""
    return _call(create_intake, body.model_dump())


@router.get("/intake/{intake_id}")
def read_workroom_intake(intake_id: int):
    return _call(get_intake, intake_id)


@router.patch("/intake/{intake_id}")
def patch_workroom_intake(intake_id: int, body: WorkroomIntakeUpdate):
    """Update triage fields. Recording contact does not send a message."""
    return _call(update_intake, intake_id, body.model_dump(exclude_unset=True))


@router.post("/intake/{intake_id}/quote")
def post_workroom_quote(intake_id: int):
    """Open a draft Workroom quote prefilled from this intake. Does not send it."""
    return _call(open_workroom_quote, intake_id)


INTAKE_FIELD_ENUMS = {
    "job_type": JOB_TYPES,
    "source": SOURCES,
    "consent_contact": CONSENT_VALUES,
    "status": INTAKE_STATUSES,
}
