"""
Growth endpoints (/api/v1/growth/...): approval queue, ROI, social proof, deposit->won,
Place Details usage, morning brief preview, and the Max Improvements queue.

Send / build actions here are founder taps from the studio and require {"confirm": true}.
Max's module_call bridge is GET-only, so Max can read these but never approve.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.leadforge import growth, place_details
from app.edition import is_family_edition
from app.services.max import improvements as imp

router = APIRouter(prefix="/growth", tags=["growth"])


def _wrap(fn, *a, **k):
    try:
        return fn(*a, **k)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Approval queue ─────────────────────────────────────────────────────────
class ApproveBody(BaseModel):
    confirm: bool = False
    to_address: Optional[str] = None
    to_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class EditBody(BaseModel):
    to_address: Optional[str] = None
    to_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


@router.get("/approvals")
def approvals(status: str = Query("pending"), limit: int = Query(200, le=500)):
    return growth.list_queue(status, limit)


@router.patch("/approvals/{item_id}")
def approvals_edit(item_id: int, body: EditBody):
    return _wrap(growth.edit_item, item_id, **body.model_dump())


@router.post("/approvals/{item_id}/approve")
async def approvals_approve(item_id: int, body: ApproveBody):
    edits = {k: v for k, v in body.model_dump().items() if k != "confirm" and v is not None}
    try:
        return await growth.approve(item_id, confirm=body.confirm, **edits)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/approvals/{item_id}/dismiss")
def approvals_dismiss(item_id: int):
    return _wrap(growth.dismiss, item_id)


# ── Deposit -> won ──────────────────────────────────────────────────────────
@router.post("/deposits/reconcile")
def deposits_reconcile():
    return growth.reconcile_paid_deposits()


# ── ROI ─────────────────────────────────────────────────────────────────────
class SpendBody(BaseModel):
    month: str
    channel: str
    amount: float
    notes: str = ""


@router.get("/roi")
def roi(months: int = Query(12, ge=1, le=36)):
    return growth.roi_report(months)


@router.post("/spend")
def spend_set(body: SpendBody):
    return _wrap(growth.set_spend, body.month, body.channel, body.amount, body.notes)


@router.delete("/spend/{spend_id}")
def spend_delete(spend_id: int):
    if not growth.delete_spend(spend_id):
        raise HTTPException(404, "not found")
    return {"deleted": spend_id}


# ── Social proof ────────────────────────────────────────────────────────────
@router.post("/social-proof/jobs/{job_id}")
def social_proof_job(job_id: str, force: bool = False):
    return _wrap(growth.social_proof_for_job, job_id, force)


@router.post("/social-proof/scan")
def social_proof_scan(days: int = 30):
    return growth.scan_completed_jobs(days)


# ── Google Place Details ────────────────────────────────────────────────────
class PlaceBody(BaseModel):
    limit: int = 25
    prospect_ids: Optional[List[int]] = None
    allow_paid: bool = False


@router.get("/place-details/usage")
def place_usage():
    return place_details.usage()


@router.post("/place-details/enrich")
def place_enrich(body: PlaceBody):
    return place_details.enrich(body.limit, body.prospect_ids, body.allow_paid)


# ── Morning brief preview (no send) ─────────────────────────────────────────
@router.get("/brief/preview")
def brief_preview():
    return {"text": growth.morning_brief_text(), "sent": False,
            "schedule": "Weekdays 7:15 AM ET to Rafael's Telegram chat (empire-growth-brief.timer)"}


# ── Improvements ────────────────────────────────────────────────────────────
class ImpCreate(BaseModel):
    title: str
    problem: str
    proposed_change: str
    affected_modules: Optional[List[str]] = None
    risk: str = "medium"
    acceptance: str = ""
    requested_via: str = "studio"


class Confirm(BaseModel):
    confirm: bool = False
    note: str = ""


class Links(BaseModel):
    pr_url: str = ""
    preview_url: str = ""


@router.get("/improvements")
def imp_list(status: Optional[str] = None):
    return imp.list_requests(status)


@router.post("/improvements")
def imp_create(body: ImpCreate):
    return _wrap(imp.create_request, **body.model_dump())


@router.get("/improvements/{req_id}")
def imp_get(req_id: int):
    r = imp.get(req_id)
    if not r:
        raise HTTPException(404, "not found")
    spec = None
    if r.get("spec_path"):
        try:
            spec = open(r["spec_path"]).read()
        except Exception:
            spec = None
    return {**r, "spec": spec or imp.build_prompt(r)}


@router.post("/improvements/{req_id}/approve")
def imp_approve(req_id: int, body: Confirm):
    # Family editions never launch Cursor builds against the Empire repo.
    if is_family_edition():
        raise HTTPException(404, "Not found")
    return _wrap(imp.approve_build, req_id, confirm=body.confirm)


@router.post("/improvements/{req_id}/refresh")
def imp_refresh(req_id: int):
    return imp.refresh_build(req_id)


@router.post("/improvements/{req_id}/links")
def imp_links(req_id: int, body: Links):
    return _wrap(imp.set_links, req_id, body.pr_url, body.preview_url)


@router.post("/improvements/{req_id}/approve-merge")
def imp_approve_merge(req_id: int, body: Confirm):
    if is_family_edition():
        raise HTTPException(404, "Not found")
    return _wrap(imp.approve_merge, req_id, confirm=body.confirm)


@router.post("/improvements/{req_id}/reject")
def imp_reject(req_id: int, body: Confirm):
    return _wrap(imp.reject, req_id, body.note)
