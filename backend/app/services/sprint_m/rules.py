"""Owner-defined trigger rules. Outbound actions always produce drafts."""

from __future__ import annotations

import json
import uuid
from app.services.sprint_m import drafts as draft_service
from app.services.sprint_m import work_orders
from app.services.sprint_m.store import audit, get_store, now_iso, row_to_dict

TRIGGER_ALIASES = {
    "proposal signed": "proposal_signed",
    "proposal_signed": "proposal_signed",
    "quote approved": "quote_approved",
    "quote_approved": "quote_approved",
    "job scheduled": "job_scheduled",
    "job_scheduled": "job_scheduled",
}

EMAIL_TEMPLATES = {
    "job_scheduled": {
        "subject": "Your Empire Workroom job is scheduled",
        "body": (
            "Hello {customer_name},\n\n"
            "Your job {job_number} is scheduled{when}.\n"
            "Style: {style}\n"
            "Fabric: {fabric}\n"
            "Due: {due_date}\n\n"
            "This is a DRAFT. Max did not send it. Owner approval is required."
        ),
    }
}


def _parse(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def normalize_trigger(event: str) -> str:
    key = (event or "").strip().lower().replace("-", "_")
    key = key.replace(" ", "_") if key in {"proposal_signed", "quote_approved", "job_scheduled"} else key
    return TRIGGER_ALIASES.get(event.strip().lower() if event else "", TRIGGER_ALIASES.get(key, key))


def list_rules() -> list[dict]:
    with get_store() as conn:
        rows = conn.execute("SELECT * FROM sm_rules ORDER BY created_at").fetchall()
    out = []
    for row in rows:
        rule = row_to_dict(row)
        rule["params"] = _parse(rule.pop("params_json", "{}"), {})
        rule["enabled"] = bool(rule["enabled"])
        out.append(rule)
    return out


def create_rule(data: dict, *, actor: str = "owner") -> dict:
    rule_id = data.get("id") or str(uuid.uuid4())[:12]
    now = now_iso()
    trigger = normalize_trigger(data["trigger_event"])
    with get_store() as conn:
        conn.execute(
            """INSERT INTO sm_rules
               (id, name, enabled, trigger_event, action, params_json, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rule_id,
                data["name"],
                1 if data.get("enabled", True) else 0,
                trigger,
                data["action"],
                json.dumps(data.get("params") or {}),
                actor,
                now,
                now,
            ),
        )
        audit(conn, "rule", rule_id, "created", actor, trigger)
    return next(r for r in list_rules() if r["id"] == rule_id)


def evaluate_event(event: str, payload: dict | None = None, *, actor: str = "system") -> dict:
    """Run matching owner rules. Client-facing actions create drafts only."""
    payload = payload or {}
    trigger = normalize_trigger(event)
    fired = []
    with get_store() as conn:
        rows = conn.execute(
            "SELECT * FROM sm_rules WHERE enabled = 1 AND trigger_event = ?",
            (trigger,),
        ).fetchall()
        rules = [row_to_dict(r) for r in rows]

    job_id = payload.get("job_id")
    job = None
    if job_id:
        try:
            job = work_orders.get_organizer_job(job_id)
        except KeyError:
            job = None

    for rule in rules:
        params = _parse(rule.get("params_json"), {})
        action = rule["action"]
        result: dict = {"rule_id": rule["id"], "action": action, "status": "applied"}
        if action == "set_job_status":
            if not job_id:
                result["status"] = "skipped"
                result["reason"] = "job_id required"
            else:
                status = params.get("status") or "sold"
                job = work_orders.update_job_status(job_id, status, actor=actor)
                result["job"] = {"id": job["id"], "status": job["status"]}
        elif action == "draft_client_email":
            if not job:
                result["status"] = "skipped"
                result["reason"] = "job not found"
            else:
                template_key = params.get("template") or "job_scheduled"
                template = EMAIL_TEMPLATES.get(template_key, EMAIL_TEMPLATES["job_scheduled"])
                when = ""
                if job.get("scheduled_at"):
                    when = f" for {job['scheduled_at']}"
                body = template["body"].format(
                    customer_name=job.get("customer_name") or "there",
                    job_number=job.get("job_number") or "",
                    when=when,
                    style=job.get("style") or "—",
                    fabric=", ".join(job.get("fabric_codes") or []) or "—",
                    due_date=job.get("due_date") or "—",
                )
                draft = draft_service.create_draft(
                    channel="email",
                    body=body,
                    job_id=job["id"],
                    customer_id=job.get("customer_id"),
                    to_address=payload.get("customer_email") or job.get("customer_email"),
                    subject=template["subject"],
                    source="rules_engine",
                    rule_id=rule["id"],
                    metadata={"trigger": trigger, "max_sends": False},
                    actor=actor,
                )
                result["draft"] = {"id": draft["id"], "status": draft["status"], "channel": "email"}
        elif action == "draft_client_sms":
            if not job:
                result["status"] = "skipped"
                result["reason"] = "job not found"
            else:
                draft = draft_service.create_draft(
                    channel="sms",
                    body=params.get("body") or f"Update on job {job.get('job_number')}. Draft only — owner must approve.",
                    job_id=job["id"],
                    customer_id=job.get("customer_id"),
                    to_address=payload.get("customer_phone"),
                    source="rules_engine",
                    rule_id=rule["id"],
                    actor=actor,
                )
                result["draft"] = {"id": draft["id"], "status": "draft"}
        else:
            result["status"] = "skipped"
            result["reason"] = f"unknown action {action}"
        fired.append(result)

    with get_store() as conn:
        audit(conn, "rule_event", trigger, "evaluated", actor, json.dumps({"count": len(fired)}))

    return {
        "event": trigger,
        "matched": len(fired),
        "results": fired,
        "max_sends_to_clients": False,
    }
