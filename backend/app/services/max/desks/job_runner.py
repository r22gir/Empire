"""Run scheduled desk jobs against real DB data, review, retry, persist.

Drafts for clients go to the approval queue (waiting tasks). Nothing
is sent outbound.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Callable

from app.db.max_ops_schema import ensure_max_ops_schema
from app.services.max.desks import live_data as ld
from app.services.max.desks.live_services import check_live_services, format_health_report
from app.services.max.desks.review_gate import ReviewVerdict, review_desk_output

logger = logging.getLogger("max.desks.job_runner")

JobFn = Callable[[dict[str, Any]], tuple[str, list[dict]]]


def _money(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _approval_note(drafts: list[dict]) -> str:
    if not drafts:
        return ""
    lines = [
        "",
        "Drafts for Rafael to approve (not sent):",
    ]
    for d in drafts:
        lines.append(f"  - {d.get('name')}: {d.get('draft')}")
    return "\n".join(lines)


def job_finance_invoice_audit(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    findings = snap.get("unpaid_invoices") or []
    overdue = snap.get("overdue_invoices") or []
    title = f"Morning Invoice Audit — {len(findings)} unpaid, {len(overdue)} overdue"
    empty = "No unpaid invoices in empire.db."
    body = ld.format_named_findings(title, findings, empty)
    if overdue:
        body += "\n\nOverdue (named):"
        for f in overdue:
            body += f"\n  - {f.get('name')} — {f.get('customer')}, ${_money(f.get('amount')):,.2f}, {f.get('age_days')}d"
    return body, findings


def job_finance_metrics(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    m = snap.get("metrics") or {}
    unpaid = snap.get("unpaid_invoices") or []
    payments = snap.get("payments_since_yesterday") or []
    lines = [
        "Daily Business Metrics (from empire.db)",
        f"  Customers: {m.get('customers', 0)}",
        f"  Jobs pending/active: {m.get('jobs_pending', 0)}; completed: {m.get('jobs_completed', 0)}",
        f"  Invoices unpaid: {m.get('invoices_unpaid', 0)}; paid: {m.get('invoices_paid', 0)}",
        f"  Revenue recorded: ${_money(m.get('revenue')):,.2f}; expenses: ${_money(m.get('expenses')):,.2f}",
        f"  Open tasks: {m.get('open_tasks', 0)}; inventory items: {m.get('inventory_items', 0)}",
        f"  Payments since yesterday: {len(payments)} (${sum(_money(p.get('amount')) for p in payments):,.2f})",
    ]
    if unpaid:
        lines.append("Unpaid invoices:")
        for f in unpaid[:12]:
            lines.append(
                f"  - {f.get('name')} — {f.get('customer')}, ${_money(f.get('amount')):,.2f}, {f.get('status')}"
            )
    findings = unpaid + payments
    return "\n".join(lines), findings


def job_sales_stale_quotes(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    findings = snap.get("stale_quotes") or []
    title = f"Stale Quote Follow-Up Scan — {len(findings)} quote(s) older than 3 days"
    empty = "No quotes older than 3 days awaiting a response."
    body = ld.format_named_findings(title, findings, empty)
    drafts = []
    for f in findings:
        drafts.append({
            "name": f.get("name"),
            "draft": (
                f"Hi {f.get('customer')}, checking in on {f.get('name')} "
                f"(${_money(f.get('amount')):,.0f}, {f.get('age_days')}d). "
                f"Want to review or adjust the estimate? — draft only, not sent."
            ),
        })
    return body + _approval_note(drafts), findings


def job_forge_pipeline(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    quotes = snap.get("open_quotes") or []
    jobs = snap.get("jobs_active") or []
    today = snap.get("schedule_today") or []
    lines = [
        f"Today's Pipeline Summary — {len(quotes)} open quotes, {len(jobs)} active jobs, {len(today)} events today",
    ]
    if quotes:
        lines.append("Open quotes:")
        for f in quotes:
            lines.append(
                f"  - {f.get('name')} — {f.get('customer')}, ${_money(f.get('amount')):,.2f}, {f.get('status')}"
            )
    else:
        lines.append("No open quotes in quotes_v2.")
    if jobs:
        lines.append("Active jobs:")
        for f in jobs:
            lines.append(
                f"  - {f.get('name')} — {f.get('customer')}, {f.get('status')}"
            )
    if today:
        lines.append("Today on the calendar:")
        for f in today:
            lines.append(
                f"  - {f.get('name')} ({f.get('type')}) — {f.get('customer')} at {f.get('start_time')}"
            )
    return "\n".join(lines), quotes + jobs + today


def job_support_tickets(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    mail = snap.get("pending_mail") or []
    inbox = snap.get("unreviewed_inbox") or []
    family = snap.get("family_tickets") or []
    open_tasks = [t for t in (snap.get("open_tasks") or []) if t.get("desk") == "support"]
    # Family stays isolated — listed separately, never as client tickets.
    client = mail + inbox + open_tasks
    lines = [
        f"Open Ticket Summary — {len(client)} client item(s), {len(family)} family-help (isolated)",
    ]
    if client:
        lines.append("Client / Workroom / Empire:")
        for f in client:
            lines.append(
                f"  - {f.get('name')} — {f.get('customer') or f.get('source') or f.get('desk') or 'open'}, {f.get('status') or f.get('channel')}"
            )
    else:
        lines.append("No open client tickets, pending mail, or unreviewed inbox items.")
    if family:
        lines.append("Family-help (isolated, not Workroom):")
        for f in family:
            lines.append(f"  - {f.get('name')} — {f.get('customer')}, {f.get('status')}")
    return "\n".join(lines), client + family


def job_it_health(snap: dict[str, Any] | None = None, checkers: dict | None = None) -> tuple[str, list[dict]]:
    kwargs = checkers or {}
    rows = check_live_services(**kwargs)
    text = format_health_report(rows)
    findings = [{
        "kind": "service",
        "name": r["name"],
        "status": "up" if r.get("up") else "down",
        "customer": r.get("detail"),
    } for r in rows]
    return text, findings


def job_analytics_metrics(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    return job_finance_metrics(snap)


def job_quality_audit(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    stuck = snap.get("stuck_tasks") or []
    overdue = snap.get("overdue_tasks") or []
    results = snap.get("desk_results") or []
    failed = [r for r in results if r.get("status") == "failed"]
    lines = [
        f"AI Quality Audit — {len(failed)} failed desk job(s) yesterday, {len(stuck)} stuck task(s), {len(overdue)} overdue",
    ]
    if failed:
        for r in failed:
            lines.append(
                f"  - {r.get('desk_id')}: {r.get('job_title')} — {r.get('fail_reason') or 'failed'}"
            )
    if stuck:
        lines.append("Stuck tasks (escalated to Rafael):")
        for f in stuck[:15]:
            lines.append(
                f"  - {f.get('name')} [{f.get('desk')}] — {f.get('age_days')}d, {f.get('status')}"
            )
    if not failed and not stuck and not overdue:
        lines.append("No failed desk jobs, stuck tasks, or overdue work in the DB.")
    return "\n".join(lines), stuck + overdue


def job_marketing_draft(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    jobs = snap.get("jobs") or []
    quotes = snap.get("open_quotes") or []
    named = jobs[:3] or quotes[:3]
    lines = [
        "Daily Social Media Post — draft only, not posted",
    ]
    if named:
        item = named[0]
        lines.append(
            f"Draft caption (approve before posting): "
            f"\"On the bench: {item.get('name')} for {item.get('customer')}. "
            f"Custom work, measured and made here.\""
        )
        lines.append("Hashtags (draft): #EmpireWorkroom #CustomDrapery #DCDesign")
        for f in named:
            lines.append(f"  Source: {f.get('name')} — {f.get('customer')}")
    else:
        lines.append("No recent jobs or quotes to name. Draft held — nothing to post.")
    return "\n".join(lines), named


def job_clients_care(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    mail = snap.get("pending_mail") or []
    unpaid = snap.get("unpaid_invoices") or []
    today = snap.get("schedule_today") or []
    findings = mail + unpaid + today
    lines = [
        f"Client Care Scan — {len(mail)} unanswered, {len(unpaid)} unpaid, {len(today)} visits today",
    ]
    for f in mail:
        lines.append(f"  - Mail {f.get('name')} from {f.get('customer')} ({f.get('channel')}) — draft only")
    for f in unpaid:
        lines.append(f"  - Invoice {f.get('name')} — {f.get('customer')}, ${_money(f.get('amount')):,.2f}")
    for f in today:
        lines.append(f"  - Today: {f.get('name')} — {f.get('customer')} ({f.get('type')})")
    if not findings:
        lines.append("No unanswered client mail, unpaid invoices, or visits today.")
    return "\n".join(lines), findings


def job_contractors_pickups(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    week = [e for e in (snap.get("schedule_week") or []) if e.get("type") in ("pickup", "drop_off", "fabric_pickup", "delivery")]
    lines = [f"Vendor Pickup Scan — {len(week)} pickup/delivery event(s) this week"]
    if week:
        for f in week:
            lines.append(f"  - {f.get('name')} — {f.get('customer')} at {f.get('start_time')} ({f.get('type')})")
    else:
        lines.append("No pickup or delivery events on the calendar this week.")
    return "\n".join(lines), week


def job_intake_review(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    inbox = [i for i in (snap.get("unreviewed_inbox") or [])]
    mail = snap.get("pending_mail") or []
    findings = inbox + mail
    lines = [f"New Intake Review — {len(findings)} unanswered inbound item(s)"]
    for f in findings:
        lines.append(f"  - {f.get('name')} — {f.get('customer') or f.get('source') or f.get('channel')}")
    if not findings:
        lines.append("No new intake or unanswered inbound items.")
    return "\n".join(lines), findings


def job_market_leads(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    quotes = [q for q in (snap.get("open_quotes") or []) if q.get("status") == "draft"]
    mail = snap.get("pending_mail") or []
    findings = quotes + mail
    lines = [f"Listing and Lead Scan — {len(quotes)} draft quotes, {len(mail)} inbound"]
    for f in findings:
        lines.append(f"  - {f.get('name')} — {f.get('customer')}")
    if not findings:
        lines.append("No new draft quotes or inbound leads.")
    return "\n".join(lines), findings


def job_legal_approvals(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    waiting = [t for t in (snap.get("open_tasks") or []) if t.get("status") == "waiting"]
    stuck = snap.get("stuck_tasks") or []
    findings = waiting + stuck
    lines = [f"Approvals Waiting Review — {len(waiting)} waiting, {len(stuck)} stuck"]
    for f in findings:
        lines.append(f"  - {f.get('name')} [{f.get('desk')}] — {f.get('status')}")
    if not findings:
        lines.append("No decisions waiting on Rafael.")
    return "\n".join(lines), findings


def job_website_watch(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    # Read-only watch. No outbound.
    text, findings = job_it_health(snap)
    return "Storefront Watch (read-only)\n" + text, findings


def job_lab_family(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    family = snap.get("family_tickets") or []
    lines = [
        f"Family Help Ticket Scan — {len(family)} open (isolated from Workroom)",
    ]
    for f in family:
        lines.append(f"  - {f.get('name')} — {f.get('customer')}, {f.get('status')}")
    if not family:
        lines.append("No open family-help tickets.")
    return "\n".join(lines), family


def job_innovation_other(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    areas = snap.get("other_areas") or {}
    findings: list[dict] = []
    lines = ["Ventures and Personal Scan (Organizer)"]
    for area in ("personal", "ventures", "empire"):
        items = areas.get(area) or []
        findings.extend(items)
        if items:
            lines.append(f"{area.title()}:")
            for f in items:
                lines.append(f"  - {f.get('name')} ({f.get('start_time') or f.get('area')})")
    if not findings:
        lines.append("No personal, venture, or extra Empire organizer items this week.")
    return "\n".join(lines), findings


def job_codeforge_failed(snap: dict[str, Any]) -> tuple[str, list[dict]]:
    results = [r for r in (snap.get("desk_results") or []) if r.get("status") == "failed"]
    findings = [{
        "kind": "failed_job",
        "name": r.get("job_title"),
        "customer": r.get("desk_id"),
        "status": r.get("fail_reason"),
    } for r in results]
    lines = [f"Failed Job Retry Scan — {len(results)} failed desk result(s)"]
    for f in findings:
        lines.append(f"  - {f.get('name')} [{f.get('customer')}] — {f.get('status')}")
    if not findings:
        lines.append("No failed desk jobs to retry.")
    return "\n".join(lines), findings


JOB_REGISTRY: dict[str, JobFn] = {
    "Morning Invoice Audit": job_finance_invoice_audit,
    "Daily Business Metrics": job_finance_metrics,
    "Stale Quote Follow-Up Scan": job_sales_stale_quotes,
    "Today's Pipeline Summary": job_forge_pipeline,
    "Open Ticket Summary": job_support_tickets,
    "Morning Service Health Check": job_it_health,
    "AI Quality Audit": job_quality_audit,
    "Daily Social Media Post": job_marketing_draft,
    "Client Care Scan": job_clients_care,
    "Vendor Pickup Scan": job_contractors_pickups,
    "New Intake Review": job_intake_review,
    "Listing and Lead Scan": job_market_leads,
    "Approvals Waiting Review": job_legal_approvals,
    "Storefront Watch": job_website_watch,
    "Family Help Ticket Scan": job_lab_family,
    "Ventures and Personal Scan": job_innovation_other,
    "Failed Job Retry Scan": job_codeforge_failed,
}


def _run_job_once(title: str, snap: dict[str, Any], checkers: dict | None = None) -> tuple[str, list[dict]]:
    fn = JOB_REGISTRY.get(title)
    if fn is job_it_health or title == "Morning Service Health Check" or title == "Storefront Watch":
        return job_it_health(snap, checkers)
    if not fn:
        # Generic real-data fallback for unknown titles.
        unpaid = snap.get("unpaid_invoices") or []
        quotes = snap.get("stale_quotes") or []
        tasks = snap.get("open_tasks") or []
        findings = unpaid + quotes + tasks
        body = ld.format_named_findings(
            f"{title} — live DB snapshot",
            findings,
            f"{title}: no matching invoices, quotes, or open tasks.",
        )
        return body, findings
    return fn(snap)


def persist_desk_result(
    *,
    desk_id: str,
    job_title: str,
    status: str,
    findings: list[dict],
    result_text: str,
    fail_reason: str | None,
    retry_count: int,
    executed_at: datetime,
    result_id: str | None = None,
) -> str:
    from app.db.database import get_db

    rid = result_id or uuid.uuid4().hex[:12]
    with get_db() as conn:
        ensure_max_ops_schema(conn)
        conn.execute(
            """INSERT INTO desk_job_results
               (id, desk_id, job_key, job_title, status, findings_json, result_text,
                fail_reason, retry_count, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rid, desk_id, f"{desk_id}:{job_title}", job_title, status,
                json.dumps(findings, default=str)[:8000],
                (result_text or "")[:8000],
                fail_reason,
                retry_count,
                executed_at.isoformat(),
            ),
        )
    return rid


def persist_task_row(
    *,
    task_id: str,
    desk_id: str,
    title: str,
    description: str,
    status: str,
    result_text: str,
    fail_reason: str | None = None,
) -> None:
    from app.db.database import get_db

    # tasks.status CHECK has no 'failed' — store failed as cancelled + reason.
    db_status = status
    if status == "failed":
        db_status = "cancelled"
    summary = result_text or ""
    if fail_reason and status == "failed":
        summary = f"FAILED: {fail_reason}\n{summary}"
    with get_db() as conn:
        ensure_max_ops_schema(conn)
        existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if existing:
            conn.execute(
                """UPDATE tasks SET status = ?, result_summary = ?, completed_at = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (db_status, summary[:2000], datetime.now().isoformat(), task_id),
            )
        else:
            conn.execute(
                """INSERT INTO tasks
                   (id, title, description, status, priority, desk, result_summary,
                    completed_at, created_by, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'normal', ?, ?, ?, 'scheduler', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (task_id, title, (description or "")[:500], db_status, desk_id,
                 summary[:2000], datetime.now().isoformat()),
            )
        try:
            conn.execute(
                """INSERT INTO task_activity (task_id, actor, action, detail)
                   VALUES (?, 'scheduler', ?, ?)""",
                (task_id, "auto_completed" if status == "done" else "auto_failed", summary[:500]),
            )
        except Exception:
            pass


def escalate_stuck_tasks(now: datetime | None = None, older_than_days: int | None = None) -> list[dict]:
    """Turn stuck tasks into waiting approvals / founder notifications."""
    from app.db.database import get_db
    from app.routers.notifications import notify_founder

    now = now or datetime.now()
    with get_db() as conn:
        ensure_max_ops_schema(conn)
        stuck = ld.query_stuck_tasks(conn, older_than_days, now)
        if not stuck:
            return []
        cols = ld._cols(conn, "tasks")
        if "status" in cols:
            ids = [s["id"] for s in stuck if s.get("id")]
            if ids:
                conn.execute(
                    f"UPDATE tasks SET status = 'waiting', updated_at = CURRENT_TIMESTAMP "
                    f"WHERE id IN ({','.join('?' * len(ids))}) AND status IN ('todo','in_progress')",
                    ids,
                )
    names = ", ".join(f"{s.get('name')} ({s.get('age_days')}d)" for s in stuck[:8])
    notify_founder(
        "MAX",
        "decision_needed",
        f"{len(stuck)} stuck task(s) need Rafael",
        f"{len(stuck)} task(s) older than {older_than_days or 'N'} days: {names}",
        "high",
        {"stuck_task_ids": [s.get("id") for s in stuck]},
    )
    return stuck


def run_scheduled_job(
    desk_id: str,
    title: str,
    description: str = "",
    *,
    snap: dict[str, Any] | None = None,
    checkers: dict | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Execute a scheduled job, review, retry once, persist.

    Done only when the review gate passes. Otherwise retry once, then fail.
    """
    now = now or datetime.now()
    snap = snap or ld.snapshot(now)
    task_id = uuid.uuid4().hex[:12]
    retry_count = 0
    result_text, findings = _run_job_once(title, snap, checkers)
    verdict = review_desk_output(
        result_text,
        findings=findings,
        require_named=bool(findings),
    )
    if not verdict.passed:
        retry_count = 1
        # Rebuild from DB once — catches transient read errors.
        snap = ld.snapshot(now)
        result_text, findings = _run_job_once(title, snap, checkers)
        verdict = review_desk_output(
            result_text,
            findings=findings,
            require_named=bool(findings),
        )

    if verdict.passed:
        status = "done"
        fail_reason = None
    else:
        status = "failed"
        fail_reason = verdict.reason

    persist_desk_result(
        desk_id=desk_id,
        job_title=title,
        status=status if status == "done" else "failed",
        findings=findings,
        result_text=result_text,
        fail_reason=fail_reason,
        retry_count=retry_count,
        executed_at=now,
        result_id=task_id,
    )
    persist_task_row(
        task_id=task_id,
        desk_id=desk_id,
        title=title,
        description=description,
        status=status,
        result_text=result_text,
        fail_reason=fail_reason,
    )
    if title == "AI Quality Audit" or title == "Approvals Waiting Review":
        try:
            escalate_stuck_tasks(now)
        except Exception as e:
            logger.warning("stuck-task escalation failed: %s", e)

    logger.info("Scheduled job %s/%s → %s (retry=%s)", desk_id, title, status, retry_count)
    return {
        "id": task_id,
        "desk_id": desk_id,
        "title": title,
        "status": status,
        "result": result_text,
        "fail_reason": fail_reason,
        "retry_count": retry_count,
        "findings": findings,
        "review": verdict,
    }
