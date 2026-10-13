"""Sprint M API — Organizer jobs, rules, drafts, costing, credits, family alerts.

All client outbound messages are drafts. Max never sends to clients.
Family alerts go to the owner only.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.sprint_m import costing, credits, drafts, family_alerts, rules, text_to_pay, work_orders
from app.services.sprint_m.drafts import DraftSendForbidden
from app.services.sprint_m.fabric import FabricCodeError
from app.services.sprint_m.work_orders import QuoteNotApproved

router = APIRouter(prefix="/sprint-m", tags=["sprint-m"])


class QuoteWorkOrderRequest(BaseModel):
    quote: dict[str, Any]


class RuleCreate(BaseModel):
    name: str
    trigger_event: str
    action: str
    params: Optional[dict[str, Any]] = None
    enabled: bool = True


class EvaluateEvent(BaseModel):
    event: str
    payload: Optional[dict[str, Any]] = None


class ScheduleJobRequest(BaseModel):
    scheduled_at: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


class TextToPayRequest(BaseModel):
    channel: str = Field(default="sms")
    provider: Optional[str] = None
    amount: Optional[float] = None
    to_address: Optional[str] = None


class CostLineCreate(BaseModel):
    category: str
    description: str
    planned_amount: float = 0
    actual_amount: float = 0


class CostActualUpdate(BaseModel):
    actual_amount: float


class CreditMemoCreate(BaseModel):
    customer_id: str
    amount: float
    reason: str
    customer_name: Optional[str] = None
    invoice_id: Optional[str] = None
    job_id: Optional[str] = None


class OverpaymentCreate(BaseModel):
    customer_id: str
    amount: float
    invoice_id: Optional[str] = None
    customer_name: Optional[str] = None


class ApplyCreditRequest(BaseModel):
    invoice_id: str
    amount: Optional[float] = None


class FamilyHelpRequest(BaseModel):
    requester: str
    message: str
    source: str = "Pedir ayuda a Max"


@router.get("/status")
def sprint_m_status():
    return {
        "sprint": "M",
        "route_prefix": "/api/v1/sprint-m",
        "db_prefix": "sm_",
        "isolated_store": True,
        "max_sends_to_clients": False,
        "measurements": "fractions",
        "fabric_policy": "docs/FABRIC_CODES.csv sequential registry (PR #128)",
        "organizer": {
            "surface": "WorkroomOrganizer",
            "screen": "calendar",
            "api": "/api/v1/organizer",
            "depends_on": ["#111", "#120", "#129"],
            "duplicate_removed": True,
        },
        "family_alerts": family_alerts.alert_status(),
        "amp_maxine_merged": False,
    }


@router.get("/dashboard")
def dashboard():
    jobs = work_orders.list_organizer_jobs(limit=200)
    draft_rows = drafts.list_drafts()
    alerts = family_alerts.list_alerts(limit=20)
    return {
        "jobs": len(jobs),
        "sold": sum(1 for j in jobs if j.get("status") == "sold"),
        "scheduled": sum(1 for j in jobs if j.get("status") == "scheduled"),
        "drafts_pending": sum(1 for d in draft_rows if d.get("status") == "draft"),
        "drafts_approved": sum(1 for d in draft_rows if d.get("status") == "approved"),
        "family_alerts": len(alerts),
        "max_sends_to_clients": False,
        "recent_jobs": jobs[:8],
        "recent_drafts": draft_rows[:8],
        "recent_alerts": alerts[:5],
        "family_alert_status": family_alerts.alert_status(),
    }


@router.post("/work-orders/from-quote")
def work_order_from_quote(body: QuoteWorkOrderRequest):
    try:
        job = work_orders.create_organizer_job_from_quote(body.quote)
    except QuoteNotApproved as exc:
        raise HTTPException(400, str(exc)) from exc
    except FabricCodeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    costing.seed_planned_from_job(job["id"])
    rules.evaluate_event("quote_approved", {"job_id": job["id"]}, actor="system")
    rules.evaluate_event("proposal_signed", {"job_id": job["id"]}, actor="system")
    return {"status": "created", "job": work_orders.get_organizer_job(job["id"]), "max_sends_to_clients": False}


@router.get("/jobs")
def list_jobs(status: Optional[str] = None, limit: int = Query(50, ge=1, le=200)):
    return {"jobs": work_orders.list_organizer_jobs(status=status, limit=limit)}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    try:
        return work_orders.get_organizer_job(job_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/jobs/{job_id}/status")
def set_job_status(job_id: str, body: StatusUpdate):
    try:
        return work_orders.update_job_status(job_id, body.status, actor="owner")
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/jobs/{job_id}/schedule")
def schedule_job(job_id: str, body: ScheduleJobRequest | None = None):
    body = body or ScheduleJobRequest()
    try:
        job = work_orders.schedule_job(job_id, body.scheduled_at, actor="owner")
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    evaluation = rules.evaluate_event("job_scheduled", {"job_id": job_id}, actor="system")
    return {"job": job, "rules": evaluation, "max_sends_to_clients": False}


@router.get("/rules")
def get_rules():
    return {"rules": rules.list_rules()}


@router.post("/rules")
def add_rule(body: RuleCreate):
    return rules.create_rule(body.model_dump(), actor="owner")


@router.post("/rules/evaluate")
def evaluate_rule(body: EvaluateEvent):
    return rules.evaluate_event(body.event, body.payload or {}, actor="owner")


@router.get("/drafts")
def get_drafts(status: Optional[str] = None, job_id: Optional[str] = None):
    return {"drafts": drafts.list_drafts(status=status, job_id=job_id), "max_sends_to_clients": False}


@router.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: str):
    try:
        return drafts.approve_draft(draft_id, actor="owner")
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/drafts/{draft_id}/send")
def send_draft(draft_id: str):
    try:
        drafts.reject_send(draft_id)
    except DraftSendForbidden as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/jobs/{job_id}/text-to-pay")
def text_to_pay_draft(job_id: str, body: TextToPayRequest):
    try:
        return text_to_pay.create_text_to_pay_draft(
            job_id,
            channel=body.channel,
            provider=body.provider,
            amount=body.amount,
            to_address=body.to_address,
            actor="owner",
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/jobs/{job_id}/costing")
def job_costing(job_id: str):
    try:
        costing.seed_planned_from_job(job_id)
        return costing.summarize_job_cost(job_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/jobs/{job_id}/costing")
def add_cost(job_id: str, body: CostLineCreate):
    try:
        costing.seed_planned_from_job(job_id)
        return costing.add_cost_line(
            job_id,
            category=body.category,
            description=body.description,
            planned_amount=body.planned_amount,
            actual_amount=body.actual_amount,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(400 if isinstance(exc, ValueError) else 404, str(exc)) from exc


@router.post("/costing/{line_id}/actual")
def set_actual(line_id: str, body: CostActualUpdate):
    try:
        return costing.update_actual(line_id, body.actual_amount)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/credits/{customer_id}")
def get_credits(customer_id: str):
    return credits.get_account(customer_id)


@router.post("/credits/memos")
def create_memo(body: CreditMemoCreate):
    try:
        return credits.create_credit_memo(**body.model_dump(), actor="owner")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/credits/overpayments")
def create_overpayment(body: OverpaymentCreate):
    try:
        return credits.record_overpayment(**body.model_dump(), actor="owner")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/credits/{customer_id}/apply")
def apply_credit(customer_id: str, body: ApplyCreditRequest):
    try:
        return credits.apply_credit_to_invoice(
            customer_id=customer_id,
            invoice_id=body.invoice_id,
            amount=body.amount,
            actor="owner",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/family-alerts/status")
def family_alert_status():
    return family_alerts.alert_status()


@router.get("/family-alerts")
def list_family_alerts(limit: int = Query(50, ge=1, le=200)):
    return {"alerts": family_alerts.list_alerts(limit=limit), "status": family_alerts.alert_status()}


@router.post("/family-help")
def family_help(body: FamilyHelpRequest):
    return family_alerts.submit_family_request(
        requester=body.requester,
        message=body.message,
        source=body.source,
    )
