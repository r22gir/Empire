"""Actionable Organizer: see, click, go and do. Outbound stays draft until a founder tap."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional
from urllib.parse import quote as urlquote

from app.services.organizer.constants import OUTBOUND_POLICY
from app.services.organizer.parse import parse_quick_add
from app.services.organizer.resolve import search_jobs
from app.services.organizer.store import (
    conflicts_for_payload,
    enrich_item,
    insert_item,
    insert_schedule_event,
    load_event,
    now_iso,
    parse_ids,
)
from app.services.organizer.timeutil import event_window, to_iso


def _job_row(conn, job_id: Optional[str]) -> Optional[dict]:
    if not job_id:
        return None
    try:
        row = conn.execute(
            """SELECT j.*, c.name as customer_name, c.phone as customer_phone, c.email as customer_email,
                      c.address as customer_address
               FROM jobs j LEFT JOIN customers c ON j.customer_id = c.id WHERE j.id = ?""",
            (job_id,),
        ).fetchone()
    except Exception:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def load_board_item(conn, item_id: Optional[str]) -> Optional[dict]:
    if not item_id:
        return None
    ev = load_event(conn, item_id)
    if ev:
        return ev
    try:
        row = conn.execute("SELECT * FROM organizer_items WHERE id = ?", (item_id,)).fetchone()
        if row:
            return enrich_item(conn, dict(row))
    except Exception:
        pass
    try:
        cap = conn.execute("SELECT * FROM organizer_captures WHERE id = ?", (item_id,)).fetchone()
        if cap:
            data = dict(cap)
            data["kind"] = "material_order"
            data["capture_id"] = data["id"]
            data["title"] = data.get("caption") or data.get("filename") or "file"
            data["relpath"] = data.get("relpath")
            return data
    except Exception:
        pass
    return None


def _quote_for_job(conn, job: dict) -> Optional[dict]:
    if not job:
        return None
    qid = job.get("quote_id")
    if qid:
        try:
            row = conn.execute("SELECT * FROM quotes_v2 WHERE id = ?", (qid,)).fetchone()
            if row:
                return dict(row)
        except Exception:
            pass
    try:
        row = conn.execute(
            """SELECT * FROM quotes_v2
               WHERE customer_id = ? OR client_name LIKE ?
               ORDER BY updated_at DESC LIMIT 1""",
            (job.get("customer_id"), f"%{job.get('client_name') or job.get('customer_name') or '___'}%"),
        ).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def _phone(item: dict, job: Optional[dict]) -> str:
    return (item.get("phone") or (job or {}).get("customer_phone") or (job or {}).get("client_phone") or "").strip()


def _email(job: Optional[dict], item: dict) -> str:
    return (item.get("email") or (job or {}).get("customer_email") or (job or {}).get("client_email") or "").strip()


def _addr(item: dict, job: Optional[dict]) -> str:
    return (item.get("location_address") or (job or {}).get("address") or (job or {}).get("customer_address") or "").strip()


def _enqueue(**kwargs) -> dict:
    from app.services.leadforge.growth import enqueue
    kwargs.setdefault("source", "organizer")
    return enqueue(**kwargs)


def available_actions(item: dict, job: Optional[dict] = None, *, quote: Optional[dict] = None) -> list[dict]:
    """Direct buttons for one row. Each has href and/or action id."""
    kind = (item.get("kind") or item.get("type") or "").lower()
    phone = _phone(item, job)
    addr = _addr(item, job)
    mail = _email(job, item)
    actions = []
    if addr:
        actions.append({
            "id": "navigate",
            "label": "Navigate",
            "group": "stop",
            "href": f"https://maps.google.com/?q={urlquote(addr)}",
            "performs": "open_maps",
        })
    if phone:
        actions.append({
            "id": "call",
            "label": "Call",
            "group": "stop",
            "href": f"tel:{''.join(ch for ch in phone if ch.isdigit() or ch == '+')}",
            "performs": "open_tel",
        })
        actions.append({
            "id": "text",
            "label": "Text",
            "group": "stop",
            "draft": True,
            "performs": "draft_sms",
        })
    if mail:
        actions.append({
            "id": "email",
            "label": "Email draft",
            "group": "stop",
            "draft": True,
            "performs": "draft_email",
        })

    if job:
        actions.append({"id": "send_quote", "label": "Send quote", "group": "job", "draft": True, "performs": "draft_quote_email"})
        actions.append({"id": "order_fabric", "label": "Order fabric", "group": "job", "draft": True, "performs": "order_fabric"})
        actions.append({"id": "request_deposit", "label": "Request deposit", "group": "job", "draft": True, "performs": "request_deposit"})
        actions.append({"id": "book_install", "label": "Book install", "group": "job", "draft": False, "performs": "book_install"})

    if kind in {"followup", "reminder", "call"} or item.get("reminder_draft") or item.get("followup_kind"):
        actions.append({
            "id": "approve_send",
            "label": "Approve & Send",
            "group": "followup",
            "draft": True,
            "requires_confirm": True,
            "performs": "approve_send",
        })

    if item.get("capture_id") or item.get("relpath") or kind in {"material_order"}:
        actions.append({"id": "attach_file", "label": "Attach to email/quote", "group": "file", "draft": True, "performs": "attach_file"})
    actions.append({"id": "ask_max", "label": "Ask Max", "group": "file", "href": f"/?product=owner&ask={urlquote((item.get('title') or 'this item')[:200])}", "performs": "ask_max"})

    if item.get("start_time") and not item.get("read_only"):
        actions.append({"id": "notify_crew", "label": "Notify crew (draft)", "group": "move", "draft": True, "performs": "notify_crew"})

    # Dedup by id
    seen = set()
    out = []
    for a in actions:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        a["outbound_policy"] = OUTBOUND_POLICY
        out.append(a)
    return out


def attach_actions(conn, items: list[dict]) -> list[dict]:
    cache: dict = {}
    decorated = []
    for item in items:
        row = dict(item)
        jid = row.get("job_id")
        if jid and jid not in cache:
            cache[jid] = _job_row(conn, jid)
        row["actions"] = available_actions(row, cache.get(jid) if jid else None)
        decorated.append(row)
    return decorated


def _draft_message(kind: str, item: dict, job: Optional[dict], extra: str = "") -> dict:
    name = (job or {}).get("client_name") or (job or {}).get("customer_name") or item.get("customer_vendor") or "there"
    title = item.get("title") or kind
    when = (item.get("start_time") or item.get("due_at") or "")[:16].replace("T", " ")
    addr = _addr(item, job)
    if kind == "sms":
        body = extra or f"Hi {name}, this is Empire Workroom about {title}" + (f" on {when}" if when else "") + "."
        return {"channel": "sms", "subject": "", "body": body, "to_address": _phone(item, job), "to_name": name}
    if kind == "crew":
        body = extra or f"Schedule update: {title}" + (f" is now {when}" if when else "") + (f" at {addr}" if addr else "") + "."
        return {"channel": "sms", "subject": "Crew update", "body": body, "to_address": "", "to_name": "crew"}
    if kind == "quote":
        body = extra or f"Hi {name}, here is the estimate for your project. Reply with any questions — happy to walk through it."
        return {"channel": "email", "subject": f"Estimate — {name}", "body": body, "to_address": _email(job, item), "to_name": name}
    if kind == "deposit":
        body = extra or f"Hi {name}, the deposit is ready when you are. We hold the production slot once it is in."
        return {"channel": "email", "subject": f"Deposit — {name}", "body": body, "to_address": _email(job, item), "to_name": name}
    if kind == "fabric":
        body = extra or f"Please confirm fabric order / ETA for {title} ({name})."
        return {"channel": "email", "subject": f"Fabric order — {name}", "body": body, "to_address": "", "to_name": "supplier"}
    body = extra or item.get("reminder_draft") or f"Hi {name}, just checking in about {title}."
    return {"channel": "email", "subject": f"Follow-up — {name}", "body": body, "to_address": _email(job, item), "to_name": name}


def _save_draft(msg: dict, *, job_id=None, customer_id=None, source_ref=None, title="") -> dict:
    return _enqueue(
        channel=msg.get("channel") or "email",
        body=msg["body"],
        source="organizer",
        source_ref=source_ref,
        kind="followup" if msg.get("channel") != "email" else "email",
        title=title or msg.get("subject") or "Organizer draft",
        to_name=msg.get("to_name") or "",
        to_address=msg.get("to_address") or "",
        subject=msg.get("subject") or "",
        job_id=job_id,
        customer_id=customer_id,
        created_by="organizer",
    )


async def run_action(conn, *, action: str, item: dict, confirm: bool = False, extra: Optional[dict] = None) -> dict:
    extra = extra or {}
    job = _job_row(conn, extra.get("job_id") or item.get("job_id"))
    quote = _quote_for_job(conn, job) if job else None
    sent = False
    performed = []
    approval = None
    href = None
    created = None

    if action == "navigate":
        addr = _addr(item, job)
        href = f"https://maps.google.com/?q={urlquote(addr)}" if addr else None
        performed.append("navigate")
    elif action == "call":
        phone = _phone(item, job)
        href = f"tel:{phone}" if phone else None
        performed.append("call")
    elif action in {"text", "email", "draft_sms", "draft_email"}:
        kind = "sms" if action in {"text", "draft_sms"} else "email"
        msg = _draft_message(kind, item, job, extra.get("body") or "")
        approval = _save_draft(msg, job_id=item.get("job_id"), customer_id=(job or {}).get("customer_id"),
                               source_ref=f"{action}-{item.get('id')}", title=msg.get("subject"))
        performed.append("draft")
    elif action == "send_quote":
        msg = _draft_message("quote", item, job)
        if quote:
            msg["body"] += f"\n\nQuote {quote.get('quote_number') or quote.get('id')}."
            msg["body"] += f"\nOpen: /?screen=quote&id={quote.get('id')}"
        approval = _save_draft(msg, job_id=item.get("job_id"), customer_id=(job or {}).get("customer_id"),
                               source_ref=f"quote-{item.get('id')}-{quote.get('id') if quote else 'none'}",
                               title="Send quote")
        href = f"/?screen=quote&id={quote['id']}" if quote else "/?product=workroom&section=quotes"
        performed.append("draft_quote")
    elif action == "request_deposit":
        pay = None
        if quote:
            try:
                from app.routers.finance import create_quote_deposit_pay_link
                pay = create_quote_deposit_pay_link(quote["id"])
                performed.append("deposit_link_created")
            except Exception as exc:
                pay = {"error": str(exc)}
        msg = _draft_message("deposit", item, job)
        if pay and pay.get("pay_link"):
            link = pay["pay_link"].get("url") or pay["pay_link"].get("checkout_url") or ""
            if link:
                msg["body"] += f"\n\nPay deposit: {link}"
        approval = _save_draft(msg, job_id=item.get("job_id"), customer_id=(job or {}).get("customer_id"),
                               source_ref=f"deposit-{item.get('id')}", title="Request deposit")
        created = {"pay_link": pay}
        performed.append("draft_deposit")
    elif action == "order_fabric":
        if job:
            try:
                conn.execute(
                    "UPDATE jobs SET pipeline_stage = ?, updated_at = ? WHERE id = ?",
                    ("fabric_ordered", now_iso(), job["id"]),
                )
                performed.append("job_stage_fabric_ordered")
            except Exception:
                pass
        created = insert_item(conn, {
            "kind": "material_order",
            "title": f"Fabric order — {job.get('client_name') or item.get('title') if job else item.get('title')}",
            "job_id": (job or {}).get("id") or item.get("job_id"),
            "status": "open",
            "notes": "Internal fabric order. Supplier email is a draft.",
        })
        msg = _draft_message("fabric", item, job)
        approval = _save_draft(msg, job_id=item.get("job_id"), title="Order fabric")
        performed.append("fabric_todo")
    elif action == "book_install":
        start = extra.get("start_time") or item.get("start_time")
        if not start:
            start = f"{date.today().isoformat()}T09:00:00"
        payload = {
            "kind": "install",
            "type": "install",
            "title": extra.get("title") or f"Install — {(job or {}).get('client_name') or item.get('title')}",
            "job_id": (job or {}).get("id") or item.get("job_id"),
            "start_time": start,
            "end_time": extra.get("end_time"),
            "location_address": _addr(item, job),
            "phone": _phone(item, job),
            "assigned_resource_ids": extra.get("assigned_resource_ids") or item.get("assigned_resource_ids") or [],
        }
        conflicts = conflicts_for_payload(conn, payload)
        if conflicts and not extra.get("confirm_conflicts"):
            return {
                "ok": False, "sent": False, "conflicts": conflicts, "silent_overwrite": False,
                "message": "Install not booked. Confirm the conflict to keep this slot.",
            }
        created = insert_schedule_event(conn, payload)
        performed.append("booked_install")
    elif action == "notify_crew":
        msg = _draft_message("crew", item, job, extra.get("body") or "")
        approval = _save_draft(msg, job_id=item.get("job_id"), source_ref=f"crew-{item.get('id')}-{item.get('start_time')}",
                               title="Tell the crew")
        performed.append("crew_draft")
    elif action == "attach_file":
        msg = _draft_message("email", item, job, extra.get("body") or "Please see the attached file.")
        approval = _save_draft(
            msg, job_id=item.get("job_id"),
            source_ref=f"file-{item.get('id') or item.get('capture_id')}",
            title="Attach file to email",
        )
        href = f"/?product=owner&ask={urlquote('Attach this Organizer file to the quote or email: ' + str(item.get('title') or item.get('id')))}"
        performed.append("file_draft")
    elif action == "ask_max":
        href = f"/?product=owner&ask={urlquote(extra.get('ask') or item.get('title') or 'Organizer item')}"
        performed.append("ask_max")
    elif action == "approve_send":
        msg = _draft_message("followup", item, job, extra.get("body") or item.get("reminder_draft") or "")
        approval = extra.get("approval_id")
        if not approval:
            approval = _save_draft(msg, job_id=item.get("job_id"), customer_id=(job or {}).get("customer_id"),
                                   source_ref=f"follow-{item.get('id')}", title=item.get("title") or "Follow-up")
        if confirm:
            from app.services.leadforge.growth import approve as growth_approve
            approval_id = approval.get("id") if isinstance(approval, dict) else approval
            try:
                approval = await growth_approve(int(approval_id), confirm=True)
                sent = bool(approval.get("sent"))
                performed.append("approved")
            except PermissionError as exc:
                return {"ok": False, "sent": False, "message": str(exc), "approval": approval}
        else:
            performed.append("draft_ready")
    else:
        return {"ok": False, "sent": False, "message": f"Unknown action '{action}'"}

    return {
        "ok": True,
        "action": action,
        "performed": performed,
        "sent": sent,
        "approval": approval,
        "created": created,
        "href": href,
        "requires_confirm": action == "approve_send" and not confirm,
        "outbound_policy": OUTBOUND_POLICY,
        "message": (
            "Sent after founder tap." if sent
            else "Draft ready. Approve & Send still required for anything outbound."
        ),
    }


def parse_command(text: str, *, today: Optional[date] = None) -> dict:
    """'move Marley's install to Friday and tell the crew' → structured command."""
    raw = (text or "").strip()
    lower = raw.lower()
    out = parse_quick_add(raw, today=today)
    out["command"] = "create"
    out["tell_crew"] = bool(re.search(r"\b(tell|notify|text|message)\b.+\bcrew\b|\bcrew\b.+\b(tell|notify|text)", lower))
    out["tell_client"] = bool(re.search(r"\b(tell|text|email|notify)\b.+\b(client|customer|them|her|him)\b", lower))
    if not out.get("subject_name"):
        moved = re.search(r"\b(?:move|reschedule)\s+([A-Za-z][\w'&.-]+)", raw, re.I)
        if moved:
            out["subject_name"] = re.sub(r"'s$", "", moved.group(1), flags=re.I)
    if out.get("subject_name"):
        out["subject_name"] = re.sub(r"'s$", "", str(out["subject_name"]), flags=re.I)
    if re.search(r"\bmove\b|\breschedul", lower):
        out["command"] = "move"
    if re.search(r"\bsend (the )?quote\b|\bemail the estimate\b", lower):
        out["command"] = "send_quote"
    if re.search(r"\bdeposit\b", lower) and re.search(r"\b(request|send|ask)\b", lower):
        out["command"] = "request_deposit"
    if re.search(r"\border fabric\b|\bfabric order\b", lower):
        out["command"] = "order_fabric"
    return out


async def run_command(conn, text: str, *, confirm: bool = False) -> dict:
    cmd = parse_command(text)
    jobs = search_jobs(conn, cmd.get("subject_name") or "") if cmd.get("subject_name") else []
    job = jobs[0] if jobs else None
    job_id = (job or {}).get("id")
    if cmd["command"] == "move":
        ev = None
        if job_id:
            row = conn.execute(
                """SELECT * FROM schedule_events WHERE job_id = ? AND (type = 'install' OR event_kind = 'install')
                   AND status != 'cancelled' ORDER BY start_time DESC LIMIT 1""",
                (job_id,),
            ).fetchone()
            ev = dict(row) if row else None
        if not ev:
            row = conn.execute(
                """SELECT * FROM schedule_events WHERE title LIKE ? AND status != 'cancelled'
                   ORDER BY start_time DESC LIMIT 1""",
                (f"%{cmd.get('subject_name') or cmd.get('title')}%",),
            ).fetchone()
            ev = dict(row) if row else None
        if not ev or not cmd.get("start_time"):
            return {"ok": False, "sent": False, "draft": cmd, "message": "Could not resolve the event or the new time. Nothing moved."}
        start, end = event_window(cmd["start_time"], cmd.get("end_time"))
        payload = {
            "id": ev["id"],
            "start_time": to_iso(start),
            "end_time": to_iso(end),
            "title": ev.get("title"),
            "location_address": ev.get("location_address"),
            "assigned_resource_ids": parse_ids(ev.get("assigned_resource_ids")),
        }
        from app.services.organizer.store import assignment_ids
        payload["assigned_resource_ids"] = assignment_ids(conn, event_id=ev["id"])
        conflicts = conflicts_for_payload(conn, payload, exclude_id=ev["id"])
        if conflicts and not confirm:
            return {"ok": False, "sent": False, "conflicts": conflicts, "silent_overwrite": False,
                    "command": cmd, "event_id": ev["id"],
                    "message": "Not moved. Confirm the conflict to keep this slot."}
        conn.execute(
            "UPDATE schedule_events SET start_time = ?, end_time = ?, updated_at = ? WHERE id = ?",
            (payload["start_time"], payload["end_time"], now_iso(), ev["id"]),
        )
        item = {**ev, "start_time": payload["start_time"], "end_time": payload["end_time"], "job_id": ev.get("job_id")}
        notify = None
        if cmd.get("tell_crew"):
            notify = await run_action(conn, action="notify_crew", item=item, extra={"job_id": ev.get("job_id")})
        return {
            "ok": True, "sent": False, "command": "move", "event_id": ev["id"],
            "start_time": payload["start_time"], "crew_draft": notify,
            "message": "Calendar updated." + (" Crew message drafted — Approve & Send required." if notify else ""),
            "outbound_policy": OUTBOUND_POLICY,
        }
    if cmd["command"] in {"send_quote", "request_deposit", "order_fabric"}:
        item = {"title": cmd.get("title"), "job_id": job_id, "kind": cmd["command"]}
        return await run_action(conn, action=cmd["command"], item=item, extra={"job_id": job_id})
    # default: draft create
    return {"ok": True, "sent": False, "command": "draft", "draft": cmd, "requires_confirmation": True,
            "message": "Draft only. Confirm to save. Nothing sent.", "outbound_policy": OUTBOUND_POLICY}
