"""One daily brief, built from the live DB, with history and diffs.

Replaces the duplicate 7:30 (desk_scheduler) and 8:00 (MaxScheduler)
generators. Email goes only to Rafael's existing FOUNDER_EMAIL address.
Nothing is sent to clients.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.db.max_ops_schema import ensure_max_ops_schema
from app.services.max.brief_filters import (
    dedupe_mail,
    dedupe_named,
    format_et,
    keep_founder_decision,
    stale_task_count,
)
from app.services.max.channel_text import for_channel, strip_telegram_html
from app.services.max.desks import live_data as ld
from app.services.max.desks.live_services import check_live_services

logger = logging.getLogger("max.daily_brief")

SECTION_KEYS = (
    "today_and_week",
    "money",
    "quotes",
    "leads_and_mail",
    "decisions",
    "desk_report",
    "other_areas",
    "watch_list",
)

SECTION_TITLES = {
    "today_and_week": "Today and this week",
    "money": "Money",
    "quotes": "Quotes needing follow-up",
    "leads_and_mail": "New leads and unanswered mail",
    "decisions": "Decisions waiting on Rafael",
    "desk_report": "Desk report",
    "other_areas": "Other areas",
    "watch_list": "Watch list",
}


def _money(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _names(items: list[dict]) -> set[str]:
    return {str(i.get("name") or i.get("id") or "") for i in items if i}


def _diff_items(current: list[dict], previous: list[dict]) -> tuple[list[dict], list[dict]]:
    prev_names = _names(previous)
    curr_names = _names(current)
    new = [i for i in current if str(i.get("name") or i.get("id") or "") not in prev_names]
    gone = [i for i in previous if str(i.get("name") or i.get("id") or "") not in curr_names]
    return new, gone


def _line_items(
    items: list[dict],
    empty: str,
    *,
    changed: list[dict] | None = None,
    limit: int = 12,
    mark_new: bool = True,
) -> str:
    if not items:
        return empty
    lines = []
    changed_names = _names(changed or [])
    shown = items[:limit]
    for i in shown:
        name = str(i.get("name") or i.get("id") or "")
        flag = " NEW" if mark_new and name in changed_names else ""
        bits = [name]
        if i.get("customer"):
            bits.append(str(i["customer"]))
        if i.get("amount") is not None and i.get("amount") != "":
            bits.append(f"${_money(i.get('amount')):,.2f}")
        if i.get("age_days") is not None:
            bits.append(f"{i['age_days']}d")
        if i.get("start_time"):
            bits.append(format_et(i["start_time"]))
        if i.get("account_label"):
            bits.append(str(i["account_label"]))
        if i.get("status"):
            bits.append(str(i["status"]))
        if i.get("type"):
            bits.append(str(i["type"]))
        # No leading spaces — strip_telegram_html().trim() was flushing the first bullet left.
        lines.append("• " + " — ".join(bits) + flag)
    extra = len(items) - len(shown)
    if extra > 0:
        lines.append(f"+{extra} more")
    return "\n".join(lines)


def _previous_sections(conn, before_date: str) -> dict[str, Any] | None:
    if not ld._table_exists(conn, "daily_briefs"):
        return None
    row = conn.execute(
        "SELECT sections_json FROM daily_briefs WHERE brief_date < ? ORDER BY brief_date DESC LIMIT 1",
        (before_date,),
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0] if not hasattr(row, "keys") else row["sections_json"])
    except (TypeError, json.JSONDecodeError):
        return None


def build_brief_sections(
    snap: dict[str, Any] | None = None,
    *,
    previous: dict[str, Any] | None = None,
    now: datetime | None = None,
    service_rows: list[dict] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    snap = snap or ld.snapshot(now)
    has_prior = previous is not None
    prev = previous or {}
    mark_new = has_prior

    today = snap.get("schedule_today") or []
    week_all = snap.get("schedule_week") or []
    today_keys = {str(i.get("id") or i.get("name") or "") for i in today}
    week = [i for i in week_all if str(i.get("id") or i.get("name") or "") not in today_keys]
    next14 = snap.get("schedule_next14") or []
    overdue_cal = snap.get("schedule_overdue") or []
    new_today, _ = _diff_items(today, prev.get("today_items") or []) if has_prior else ([], [])

    payments = snap.get("payments_since_yesterday") or []
    unpaid = snap.get("unpaid_invoices") or []
    bank = snap.get("bank_notices") or []
    new_pay, _ = _diff_items(payments, prev.get("payment_items") or []) if has_prior else ([], [])

    quotes = snap.get("stale_quotes") or []
    new_quotes, _ = _diff_items(quotes, prev.get("quote_items") or []) if has_prior else ([], [])

    mail = dedupe_mail((snap.get("pending_mail") or []) + (snap.get("unreviewed_inbox") or []))
    new_mail, _ = _diff_items(mail, prev.get("mail_items") or []) if has_prior else ([], [])

    stuck = snap.get("stuck_tasks") or []
    waiting = [t for t in (snap.get("open_tasks") or []) if t.get("status") == "waiting"]
    queue = snap.get("approval_queue") or []
    decisions = dedupe_named(
        [t for t in (stuck + waiting + queue) if keep_founder_decision(t)]
    )
    stale_n = stale_task_count(stuck + (snap.get("open_tasks") or []))

    desk_rows = snap.get("desk_results") or []
    areas = snap.get("other_areas") or {}

    rows = service_rows if service_rows is not None else check_live_services()
    alerts = [r for r in rows if not r.get("up")]
    # Disk high usage is a real alert even if marked up below 95 in checker
    for r in rows:
        if r.get("id") == "disk" and (r.get("pct") or 0) >= 90 and r not in alerts:
            alerts.append(r)

    sections = {
        "today_and_week": {
            "title": SECTION_TITLES["today_and_week"],
            "summary": (
                f"{len(today)} today, {len(week)} this week, "
                f"{len(next14)} next 14 days, {len(overdue_cal)} overdue"
            ),
            "new_count": len(new_today) if mark_new else 0,
            "text": (
                f"Today ({len(today)}):\n{_line_items(today, 'Nothing on the calendar today.', changed=new_today, mark_new=mark_new)}\n"
                f"This week ({len(week)}):\n{_line_items(week, 'Nothing scheduled this week.', mark_new=False)}\n"
                f"Next 14 days ({len(next14)}):\n{_line_items(next14, 'Nothing between next week and two weeks out.', mark_new=False)}\n"
                f"Overdue ({len(overdue_cal)}):\n{_line_items(overdue_cal, 'No overdue installs or deliveries.', mark_new=False)}"
            ),
            "items": today,
        },
        "money": {
            "title": SECTION_TITLES["money"],
            "summary": (
                f"{len(payments)} payment(s) since yesterday "
                f"(${sum(_money(p.get('amount')) for p in payments):,.2f}); "
                f"{len(unpaid)} unpaid"
            ),
            "new_count": len(new_pay) if mark_new else 0,
            "text": (
                f"Received since yesterday ({len(payments)}):\n"
                f"{_line_items(payments, 'No payments since yesterday.', changed=new_pay, mark_new=mark_new)}\n"
                f"Unpaid invoices / deposits ({len(unpaid)}):\n"
                f"{_line_items(unpaid, 'No unpaid invoices.', mark_new=False)}"
                + (
                    f"\nBank / transaction FYI ({len(bank)}):\n"
                    f"{_line_items(bank, 'No bank notices.', mark_new=False)}"
                    if bank else ""
                )
            ),
            "items": unpaid,
        },
        "quotes": {
            "title": SECTION_TITLES["quotes"],
            "summary": f"{len(quotes)} quote(s) awaiting a reply",
            "new_count": len(new_quotes) if mark_new else 0,
            "text": _line_items(quotes, "No quotes awaiting a reply.", changed=new_quotes, limit=10, mark_new=mark_new),
            "items": quotes[:10],
        },
        "leads_and_mail": {
            "title": SECTION_TITLES["leads_and_mail"],
            "summary": f"{len(mail)} unanswered (drafts to approve, not sent)",
            "new_count": len(new_mail) if mark_new else 0,
            "text": _line_items(mail, "No unanswered client email or WhatsApp.", changed=new_mail, mark_new=mark_new),
            "items": mail,
        },
        "decisions": {
            "title": SECTION_TITLES["decisions"],
            "summary": f"{len(decisions)} waiting" + (f", {stale_n} stale >30d" if stale_n else ""),
            "new_count": 0,
            "text": _decisions_text(decisions, stale_n),
            "items": decisions,
        },
        "desk_report": {
            "title": SECTION_TITLES["desk_report"],
            "summary": f"{len(desk_rows)} desk job(s) since yesterday",
            "new_count": 0,
            "text": _desk_report_text(desk_rows),
            "items": [{"name": r.get("job_title"), "status": r.get("status"), "desk": r.get("desk_id")} for r in desk_rows],
        },
        "other_areas": {
            "title": SECTION_TITLES["other_areas"],
            "summary": ", ".join(
                f"{k}: {len(v)}" for k, v in areas.items() if v
            ) or "none",
            "new_count": 0,
            "text": _other_areas_text(areas),
            "items": [i for v in areas.values() for i in v],
        },
        "watch_list": {
            "title": SECTION_TITLES["watch_list"],
            "summary": f"{len(alerts)} real alert(s)",
            "new_count": 0,
            "text": _watch_text(alerts, rows),
            "items": alerts,
        },
        # raw lists for tomorrow's diff
        "today_items": today,
        "next14_items": next14,
        "payment_items": payments,
        "quote_items": quotes,
        "mail_items": mail,
    }
    return sections


def _desk_report_text(rows: list[dict]) -> str:
    if not rows:
        return "No desk jobs recorded since yesterday."
    lines = []
    for r in rows:
        status = r.get("status")
        reason = f" — {r.get('fail_reason')}" if status == "failed" and r.get("fail_reason") else ""
        lines.append(f"• {r.get('desk_id')}: {r.get('job_title')} [{status}]{reason}")
    return "\n".join(lines)


def _decisions_text(decisions: list[dict], stale_n: int) -> str:
    parts: list[str] = []
    if decisions:
        parts.append(_line_items(decisions, "", mark_new=False))
    if stale_n:
        parts.append(f"{stale_n} stale tasks >30d")
    return "\n".join(p for p in parts if p) or "Nothing waiting on Rafael."


def _other_areas_text(areas: dict[str, list[dict]]) -> str:
    lines = []
    for key in ("empire", "family", "personal", "ventures"):
        items = areas.get(key) or []
        if not items:
            continue
        lines.append(f"{key.title()}:")
        lines.append(_line_items(items, "(none)"))
    return "\n".join(lines) if lines else "(nothing new)"


def _watch_text(alerts: list[dict], all_rows: list[dict]) -> str:
    if not alerts:
        return "No service, disk, or usage alerts."
    lines = []
    for r in alerts:
        lines.append(f"• {r.get('name')}: {r.get('detail') or 'alert'}")
    return "\n".join(lines)


def render_brief_html(sections: dict[str, Any], now: datetime) -> str:
    parts = [f"<b>☀️ Morning Brief — {now.strftime('%A, %B %d')}</b>", ""]
    for key in SECTION_KEYS:
        sec = sections.get(key) or {}
        changed = sec.get("new_count") or 0
        flag = f" · {changed} new" if changed else ""
        parts.append(f"<b>{sec.get('title', key)}</b>{flag}")
        parts.append(for_channel(sec.get("text") or "", "plain"))
        parts.append("")
    return "\n".join(parts).strip()


def render_brief_plain(sections: dict[str, Any], now: datetime) -> str:
    return strip_telegram_html(render_brief_html(sections, now))


def latest_brief(conn=None) -> dict[str, Any] | None:
    from app.db.database import get_db

    def _read(c):
        ensure_max_ops_schema(c)
        if not ld._table_exists(c, "daily_briefs"):
            return None
        row = c.execute(
            "SELECT id, brief_date, generated_at, sections_json, text_plain, text_html, text_markdown, previous_brief_id "
            "FROM daily_briefs ORDER BY generated_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        d = dict(row) if hasattr(row, "keys") else {
            "id": row[0], "brief_date": row[1], "generated_at": row[2],
            "sections_json": row[3], "text_plain": row[4], "text_html": row[5],
            "text_markdown": row[6], "previous_brief_id": row[7],
        }
        try:
            d["sections"] = json.loads(d.pop("sections_json"))
        except (TypeError, json.JSONDecodeError):
            d["sections"] = {}
        return d

    if conn is not None:
        return _read(conn)
    with get_db() as c:
        return _read(c)


def persist_brief(
    sections: dict[str, Any],
    *,
    now: datetime | None = None,
    previous_id: str | None = None,
) -> dict[str, Any]:
    from app.db.database import get_db

    now = now or datetime.now()
    html = render_brief_html(sections, now)
    plain = strip_telegram_html(html)
    md = for_channel(html, "markdown")
    bid = uuid.uuid4().hex[:12]
    payload = {
        "id": bid,
        "date": now.strftime("%Y-%m-%d"),
        "brief_date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "sections": {k: {kk: vv for kk, vv in (sections.get(k) or {}).items() if kk != "items"}
                     for k in SECTION_KEYS},
        "html": html,
        "message": plain,
        "text_plain": plain,
        "text_markdown": md,
        "previous_brief_id": previous_id,
    }
    with get_db() as conn:
        ensure_max_ops_schema(conn)
        conn.execute(
            """INSERT INTO daily_briefs
               (id, brief_date, generated_at, sections_json, text_plain, text_html, text_markdown, previous_brief_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                bid, payload["brief_date"], payload["generated_at"],
                json.dumps(sections, default=str),
                plain, html, md, previous_id,
            ),
        )
    return payload


def build_and_persist_brief(
    *,
    now: datetime | None = None,
    snap: dict[str, Any] | None = None,
    service_rows: list[dict] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    snap = snap or ld.snapshot(now)
    from app.db.database import get_db

    with get_db() as conn:
        ensure_max_ops_schema(conn)
        prev_row = conn.execute(
            "SELECT id, sections_json FROM daily_briefs ORDER BY generated_at DESC LIMIT 1"
        ).fetchone()
        previous = None
        previous_id = None
        if prev_row:
            previous_id = prev_row[0] if not hasattr(prev_row, "keys") else prev_row["id"]
            raw = prev_row[1] if not hasattr(prev_row, "keys") else prev_row["sections_json"]
            try:
                previous = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                previous = None
    sections = build_brief_sections(snap, previous=previous, now=now, service_rows=service_rows)
    return persist_brief(sections, now=now, previous_id=previous_id)


def founder_email() -> str:
    return os.environ.get("FOUNDER_EMAIL", "empirebox2026@gmail.com")


async def send_consolidated_brief(
    *,
    now: datetime | None = None,
    snap: dict[str, Any] | None = None,
    send_email: bool = True,
    send_telegram: bool = True,
    notify: bool = True,
) -> dict[str, Any]:
    """Build, persist, and deliver ONE brief. Email only to Rafael."""
    payload = build_and_persist_brief(now=now, snap=snap)
    html = payload["html"]
    plain = payload["text_plain"]

    if notify:
        try:
            from app.routers.notifications import notify_founder

            notify_founder("MAX", "system_alert", "Morning Brief", html, "low")
        except Exception as e:
            logger.warning("brief notify failed: %s", e)

    if send_telegram:
        try:
            from app.services.max.telegram_bot import telegram_bot

            if telegram_bot.is_configured:
                await telegram_bot.send_message(html)
        except Exception as e:
            logger.warning("brief telegram failed: %s", e)

    if send_email:
        try:
            from app.services.max.email_service import EmailService

            svc = EmailService()
            if svc.is_configured:
                to = founder_email()
                svc.send(
                    to=to,
                    subject=f"☀️ Empire Morning Brief — {(now or datetime.now()).strftime('%A, %B %d')}",
                    body_html=html.replace("\n", "<br>"),
                )
                logger.info("Morning brief emailed to %s", to)
        except Exception as e:
            logger.warning("brief email failed: %s", e)

    return payload
