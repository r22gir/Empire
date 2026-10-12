"""Smart follow-up drafts. Never sent — founder approval only."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from app.services.organizer.constants import OUTBOUND_POLICY

STALE_QUOTE_DAYS = 7
LATE_FABRIC_DAYS = 10


def _age_days(value: Optional[str], today: date) -> Optional[int]:
    if not value:
        return None
    raw = str(value)[:10]
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return None
    return (today - d).days


def detect_followups(
    *,
    quotes: list[dict],
    jobs: list[dict],
    today: Optional[date] = None,
) -> list[dict]:
    """Return draft nudges. Nothing is written or sent here."""
    today = today or date.today()
    drafts = []
    awaiting = {"sent", "proposal", "viewed", "estimate_sent"}
    for q in quotes:
        status = str(q.get("status") or "").lower()
        if status not in awaiting:
            continue
        age = _age_days(q.get("sent_at") or q.get("updated_at") or q.get("created_at"), today)
        if age is None or age < STALE_QUOTE_DAYS:
            continue
        name = q.get("customer_name") or q.get("client_name") or "the client"
        drafts.append({
            "kind": "followup",
            "followup_kind": "quote",
            "title": f"Follow up on quote {q.get('quote_number') or q.get('id')} — {name}",
            "reason": f"No reply in {age} days",
            "job_id": q.get("job_id"),
            "customer_id": q.get("customer_id"),
            "source_id": q.get("id"),
            "reminder_draft": (
                f"Hi {name}, just checking that you received the estimate. "
                "Happy to walk through options when you have a moment."
            ),
            "requires_approval": True,
            "sent": False,
        })

    for q in quotes:
        dep_req = float(q.get("deposit_required") or 0)
        dep_paid = float(q.get("deposit_paid") or 0)
        status = str(q.get("status") or "").lower()
        if status in {"accepted", "approved", "won"} and dep_req > 0 and dep_paid + 0.01 < dep_req:
            name = q.get("customer_name") or q.get("client_name") or "the client"
            drafts.append({
                "kind": "followup",
                "followup_kind": "deposit",
                "title": f"Unpaid deposit — {name}",
                "reason": f"Approved quote, deposit {dep_paid:.0f} of {dep_req:.0f} unpaid",
                "job_id": q.get("job_id"),
                "customer_id": q.get("customer_id"),
                "source_id": q.get("id"),
                "reminder_draft": (
                    f"Hi {name}, the deposit is still open on the approved estimate. "
                    "We can hold the production slot once it is in."
                ),
                "requires_approval": True,
                "sent": False,
            })

    fabric_stages = {"fabric_ordered", "fabric_picked_up"}
    for j in jobs:
        stage = str(j.get("canonical_stage") or j.get("pipeline_stage") or j.get("status") or "").lower()
        if stage != "fabric_ordered":
            continue
        age = _age_days(j.get("updated_at") or j.get("created_at") or j.get("scheduled_date"), today)
        if age is None or age < LATE_FABRIC_DAYS:
            continue
        name = j.get("client_name") or j.get("customer_name") or "the job"
        drafts.append({
            "kind": "followup",
            "followup_kind": "general",
            "title": f"Late fabric — {name}",
            "reason": f"Fabric still ordered after {age} days",
            "job_id": j.get("id"),
            "customer_id": j.get("customer_id"),
            "source_id": j.get("id"),
            "reminder_draft": (
                f"Internal: fabric for {name} has been on order {age} days. "
                "Call the supplier, then draft a client update for Rafael to approve."
            ),
            "requires_approval": True,
            "sent": False,
        })

    for d in drafts:
        d["outbound_blocked"] = True
        d["outbound_policy"] = OUTBOUND_POLICY
        d["is_draft_only"] = True
    return drafts
