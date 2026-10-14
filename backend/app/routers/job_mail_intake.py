"""Read-only job-mail intake API. Never sends email or WhatsApp."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.job_mail_intake.service import (
    OUTBOUND_POLICY,
    approve_calendar_proposal,
    list_calendar_proposals,
    list_review_queue,
    list_supplier_events,
    list_timeline_notes,
    run_intake,
)

router = APIRouter(prefix="/job-mail", tags=["job-mail-intake"])


@router.post("/run")
async def run_job_mail_intake():
    """Scan connected inboxes and attach notes. Read-only. Nothing is sent."""
    result = run_intake()
    result["outbound_policy"] = OUTBOUND_POLICY
    result["sent"] = False
    return result


@router.get("/review-queue")
async def job_mail_review_queue(status: str = "unmatched", limit: int = Query(50, le=200)):
    return list_review_queue(status=status, limit=limit)


@router.get("/calendar-proposals")
async def job_mail_calendar_proposals(status: str = "pending", limit: int = Query(50, le=200)):
    return list_calendar_proposals(status=status, limit=limit)


@router.post("/calendar-proposals/{proposal_id}/approve")
async def job_mail_approve_calendar(proposal_id: str):
    result = approve_calendar_proposal(proposal_id)
    if not result.get("ok"):
        raise HTTPException(404, result.get("message") or "proposal not found")
    return result


@router.get("/supplier-events")
async def job_mail_supplier_events(job_id: Optional[str] = None, limit: int = Query(50, le=200)):
    return list_supplier_events(job_id=job_id, limit=limit)


@router.get("/notes")
async def job_mail_notes(job_id: Optional[str] = None, limit: int = Query(50, le=200)):
    return list_timeline_notes(job_id=job_id, limit=limit)
