"""Workroom intake door shared by LeadForge (thin) and LuxeForge (rich).

POST /api/v1/leadforge/intake
GET  /api/v1/leadforge/intake/{lead_id}
POST /api/v1/leadforge/intake/{lead_id}/quote

LuxeForge posts capture_channel=luxeforge with measure notes and photo URLs.
LeadForge thin ads post capture_channel=leadforge (the default). Both write
the same ForgeCRM customer, LeadForge prospect, and quotes.create_quote path.

Auth / public host: this route is not behind the intake-portal JWT so the
Command Center brief can submit. It is still not an ad destination.
luxe.empirebox.store redirects /luxe and /luxeforge to /intake, and public
cc/api hosts have been 521 or Cloudflare Access gated. Ship the form on the
Command Center routes; do not claim a public self-serve portal.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional

from app.services.leadforge.workroom_intake import (
    IntakeError,
    create_workroom_quote_from_lead,
    get_workroom_lead,
    submit_workroom_intake,
)

router = APIRouter(prefix="/leadforge", tags=["workroom-intake"])

JobType = Literal[
    "drapery_romans",
    "banquette",
    "soft_seating",
    "headboard",
    "mixed",
    "other",
]
Source = Literal[
    "meta_ad",
    "instagram",
    "houzz",
    "outreach",
    "web",
    "referral",
    "other",
]


class WorkroomIntakeIn(BaseModel):
    full_name: str = Field(min_length=1)
    email: str
    phone: Optional[str] = None
    firm_name: Optional[str] = None
    city_region: Optional[str] = None
    job_type: JobType
    message: str = Field(min_length=1)
    measure_notes: Optional[str] = None
    photo_urls: list[str] = Field(default_factory=list)
    source: Source
    utm_campaign: Optional[str] = None
    consent_contact: bool
    capture_channel: Literal["luxeforge", "leadforge"] = "leadforge"
    business: Literal["workroom"] = "workroom"


def _raise(exc: IntakeError) -> None:
    raise HTTPException(status_code=exc.status, detail=exc.detail)


@router.post("/intake")
def post_workroom_intake(body: WorkroomIntakeIn):
    """Create or update the Workroom lead, CRM contact, and prospect."""
    try:
        return submit_workroom_intake(body.model_dump())
    except IntakeError as exc:
        _raise(exc)


@router.get("/intake/{lead_id}")
def read_workroom_intake(lead_id: int):
    try:
        return get_workroom_lead(lead_id)
    except IntakeError as exc:
        _raise(exc)


@router.post("/intake/{lead_id}/quote")
async def open_workroom_quote(lead_id: int):
    """Prefill and create a Workroom quote from the latest brief."""
    try:
        return await create_workroom_quote_from_lead(lead_id)
    except IntakeError as exc:
        _raise(exc)
