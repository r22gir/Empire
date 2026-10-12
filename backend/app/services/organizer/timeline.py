"""Job timeline strip: measure → install, next step, blockers."""

from __future__ import annotations

STEPS = [
    ("measure", "Measure", ("measure", "site_visit")),
    ("quote", "Quote / approve", ("quote", "followup")),
    ("deposit", "Deposit", ("deposit", "followup")),
    ("fabric", "Fabric in", ("fabric_pickup", "material_order")),
    ("produce", "In production", ("todo", "job_milestone")),
    ("ready", "Ready / pickup", ("pickup", "drop_off", "delivery")),
    ("install", "Install", ("install", "fitting")),
    ("close", "Paid / closed", ("deadline",)),
]

STAGE_HINTS = {
    "lead": "measure",
    "estimate_sent": "quote",
    "deposit_paid": "fabric",
    "fabric_ordered": "fabric",
    "fabric_picked_up": "produce",
    "in_production": "produce",
    "ready": "ready",
    "scheduled": "install",
    "installed": "close",
    "final_invoice": "close",
    "paid_closed": "close",
}


def _done_status(status: str) -> bool:
    return str(status or "").lower() in ("done", "completed", "complete", "paid", "closed")


def build_job_timeline(job: dict, items: list[dict]) -> dict:
    stage = str(job.get("canonical_stage") or job.get("pipeline_stage") or job.get("status") or "").lower()
    by_kind = {}
    for it in items:
        kind = it.get("kind") or it.get("type")
        by_kind.setdefault(kind, []).append(it)

    strip = []
    first_open = None
    for key, label, kinds in STEPS:
        related = []
        for k in kinds:
            related.extend(by_kind.get(k, []))
        if key == "measure" and job.get("site_visit_date"):
            related.append({"kind": "measure", "start_time": job.get("site_visit_date"), "title": "Site visit date"})
        if key == "install" and job.get("install_date"):
            related.append({"kind": "install", "start_time": job.get("install_date"), "title": "Install date"})
        done = bool(related) and all(_done_status(r.get("status")) for r in related if r.get("status"))
        if key == "deposit" and float(job.get("deposit_paid") or 0) > 0:
            done = True
        if STAGE_HINTS.get(stage) == "close" and key != "close":
            done = True
        if stage in ("paid_closed", "installed", "completed") and key in ("install", "close"):
            done = key != "close" or stage == "paid_closed"
        current = STAGE_HINTS.get(stage) == key
        blockers = []
        if key == "fabric" and stage in ("fabric_ordered",) and not any(
            (r.get("kind") == "fabric_pickup" and _done_status(r.get("status"))) for r in related
        ):
            blockers.append("Fabric not marked picked up")
        if key == "deposit" and float(job.get("deposit_paid") or job.get("payment_strip", {}).get("paid") or 0) <= 0:
            if stage in ("estimate_sent", "deposit_paid") or key == "deposit":
                if stage in ("estimate_sent", "lead"):
                    blockers.append("Deposit not recorded")
        if key == "install" and not (job.get("install_date") or any(r.get("start_time") for r in related)):
            if stage in ("ready", "scheduled", "in_production"):
                blockers.append("Install not on the calendar")
        state = "done" if done else ("current" if current else "upcoming")
        if not first_open and state != "done":
            first_open = key
            state = "current"
        strip.append({
            "key": key,
            "label": label,
            "state": state,
            "items": related[:6],
            "blockers": blockers,
        })

    current = next((s for s in strip if s["state"] == "current"), strip[0] if strip else None)
    blockers = []
    for s in strip:
        blockers.extend([{"step": s["key"], "message": b} for b in s.get("blockers") or []])
    next_step = current["label"] if current else "Review job"
    return {
        "job_id": job.get("id"),
        "title": job.get("title") or job.get("job_number"),
        "client": job.get("client_name") or job.get("customer_name"),
        "stage": stage,
        "strip": strip,
        "next_step": next_step,
        "blockers": blockers,
    }
