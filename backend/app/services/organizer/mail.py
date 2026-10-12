"""Read-only pending mail for the Organizer.

Reuses gmail_reader.check_inbox and outlook_reader.search_messages.
Each edition reads only its own owner's token files. Nothing is sent here —
draft replies go to the approval queue for the owner's tap.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from app.services.organizer.constants import OUTBOUND_POLICY
from app.services.organizer.edition import (
    contains_blocked_term,
    edition_meta,
    mailbox_token_paths,
    normalize_space,
    process_edition,
    redact_blocked,
)
from app.services.organizer.parse import infer_space
from app.services.organizer.resolve import attach_matches, search_customers, search_jobs, search_resources
from app.services.organizer.store import insert_item, new_id, now_iso

# Tests assign a list of message dicts here to skip live connectors.
TEST_INBOX: Optional[list] = None

MAIL_ACTIONS = ("open", "draft_reply", "snooze", "todo", "followup")


def parse_from(raw: Optional[str]) -> tuple[str, str]:
    blob = (raw or "").strip()
    addr_m = re.search(r"<([^>]+)>", blob)
    email = (addr_m.group(1) if addr_m else blob).strip().lower()
    name = re.sub(r"<[^>]+>", "", blob).strip().strip('"').strip()
    if "@" in name and not addr_m:
        name = name.split("@")[0].replace(".", " ").title()
    return name, email


def open_href(source: str, message_id: str, extra: Optional[dict] = None) -> str:
    extra = extra or {}
    if extra.get("web_link"):
        return str(extra["web_link"])
    if source == "outlook":
        return "https://outlook.office.com/mail/"
    if message_id:
        return f"https://mail.google.com/mail/u/0/#all/{message_id}"
    return "https://mail.google.com/mail/u/0/#inbox"


def suggest_reply(msg: dict) -> str:
    meta = edition_meta()
    name, _ = parse_from(msg.get("from"))
    who = name or "there"
    subject = (msg.get("subject") or "your note").strip()
    if subject.lower().startswith("re:"):
        subject = subject[3:].strip()
    owner = meta.get("owner") or "me"
    return (
        f"Hi {who},\n\n"
        f"Thanks for your email about {subject}. I wanted to reply so this does not sit unanswered — "
        f"happy to continue from here.\n\n"
        f"— {owner}"
    )


def _state_row(conn, source: str, message_id: str) -> Optional[dict]:
    row = conn.execute(
        """SELECT * FROM organizer_mail_state
           WHERE edition = ? AND source = ? AND message_id = ?""",
        (process_edition(), source, message_id),
    ).fetchone()
    return dict(row) if row else None


def _upsert_state(conn, source: str, message_id: str, **fields) -> dict:
    existing = _state_row(conn, source, message_id)
    stamp = now_iso()
    if existing:
        sets = ["updated_at = ?"]
        params: list = [stamp]
        for key, val in fields.items():
            sets.append(f"{key} = ?")
            params.append(val)
        params.extend([process_edition(), source, message_id])
        conn.execute(
            f"""UPDATE organizer_mail_state SET {', '.join(sets)}
                WHERE edition = ? AND source = ? AND message_id = ?""",
            params,
        )
        return _state_row(conn, source, message_id) or existing
    sid = new_id()
    conn.execute(
        """INSERT INTO organizer_mail_state
           (id, edition, source, message_id, status, snooze_until, space_id, job_id,
            resource_id, approval_id, item_id, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            sid, process_edition(), source, message_id,
            fields.get("status") or "open",
            fields.get("snooze_until"),
            fields.get("space_id"),
            fields.get("job_id"),
            fields.get("resource_id"),
            fields.get("approval_id"),
            fields.get("item_id"),
            fields.get("notes"),
            stamp, stamp,
        ),
    )
    return _state_row(conn, source, message_id) or {"id": sid, **fields}


@contextmanager
def _edition_token_env(source: str):
    """Point the shared readers at this edition's token only, then restore."""
    paths = mailbox_token_paths()
    token = paths.get(source)
    env_key = "GMAIL_TOKEN_PATH" if source == "gmail" else "OUTLOOK_TOKEN_PATH"
    old = os.environ.get(env_key)
    try:
        if token:
            os.environ[env_key] = str(token)
        elif env_key in os.environ and process_edition() != "main":
            os.environ.pop(env_key, None)
        yield token
    finally:
        if old is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = old


def _fetch_gmail() -> list[dict]:
    """Business Gmail (empirebox2026 / workroom@, info@, max@).

    Chat's check_inbox default is unread mail to max@. Do not use that
    filter here. Main always tries the reader; family editions stay
    gated on their own token so they cannot read Rafael's mailbox.
    """
    paths = mailbox_token_paths()
    if process_edition() != "main" and "gmail" not in paths["sources"]:
        return []
    with _edition_token_env("gmail"):
        from app.services.max.gmail_reader import check_inbox
        res = check_inbox(
            limit=20,
            unread_only=False,
            query="in:inbox newer_than:21d",
            disable_default_to_filter=True,
        )
    if not res.get("success"):
        return []
    out = []
    for em in res.get("emails") or []:
        out.append({
            "source": "gmail",
            "message_id": em.get("id"),
            "thread_id": em.get("thread_id") or em.get("threadId") or "",
            "from": em.get("from"),
            "to": em.get("to"),
            "subject": em.get("subject") or "(no subject)",
            "date": em.get("date"),
            "preview": em.get("preview") or "",
            "unread": bool(em.get("unread")),
            "account": "gmail",
            "labels": em.get("labels") or em.get("labelIds") or [],
            "list_unsubscribe": em.get("list_unsubscribe") or "",
        })
    return out


def _fetch_outlook() -> list[dict]:
    paths = mailbox_token_paths()
    if "outlook" not in paths["sources"]:
        return []
    with _edition_token_env("outlook"):
        from app.services.max.outlook_reader import search_messages
        res = search_messages(folder="inbox", since="21d", limit=20, unread_only=False)
    if not res.get("success"):
        return []
    out = []
    for em in res.get("emails") or []:
        out.append({
            "source": "outlook",
            "message_id": em.get("id"),
            "thread_id": em.get("thread_id") or em.get("conversationId") or em.get("id") or "",
            "from": em.get("from"),
            "to": "",
            "subject": em.get("subject") or "(no subject)",
            "date": em.get("date"),
            "preview": em.get("preview") or "",
            "unread": bool(em.get("unread")),
            "account": "outlook",
            "web_link": em.get("web_link"),
        })
    return out


def fetch_raw_messages() -> list[dict]:
    if TEST_INBOX is not None:
        return [dict(m) for m in TEST_INBOX]
    items: list[dict] = []
    items.extend(_fetch_gmail())
    items.extend(_fetch_outlook())
    return items


def _is_hidden(state: Optional[dict], now: str) -> bool:
    if not state:
        return False
    if state.get("status") == "done":
        return True
    if state.get("status") == "snoozed" and (state.get("snooze_until") or "") > now:
        return True
    return False


def _link(conn, msg: dict) -> dict:
    name, email = parse_from(msg.get("from"))
    draft = attach_matches(conn, {
        "subject_name": name,
        "title": msg.get("subject"),
        "space_id": infer_space(f"{msg.get('subject') or ''} {name} {msg.get('preview') or ''}"),
    })
    if email and not draft.get("resource_id"):
        people = search_resources(conn, email) or search_resources(conn, name)
        if people:
            draft["resource_id"] = people[0].get("id")
            draft["assigned_resource_ids"] = [people[0].get("id")]
            draft["matched_people"] = people
    if email and not draft.get("job_id") and not draft.get("customer_id"):
        customers = search_customers(conn, email) or search_customers(conn, name)
        if customers:
            draft["customer_id"] = customers[0].get("id")
            draft["customer_vendor"] = customers[0].get("name")
        jobs = search_jobs(conn, name)
        if jobs:
            draft["job_id"] = jobs[0].get("id")
            draft["job_title"] = jobs[0].get("title")
    return draft


def _waiting_reason(msg: dict) -> str:
    if msg.get("unread"):
        return "unanswered"
    return "waiting"


def decorate_message(conn, msg: dict, state: Optional[dict]) -> Optional[dict]:
    blob = " ".join(str(msg.get(k) or "") for k in ("from", "to", "subject", "preview"))
    if contains_blocked_term(blob):
        return None
    from app.services.max.brief_filters import (
        is_promotional_mail,
        is_self_sent_mail,
        mail_account_label,
    )

    if is_promotional_mail(msg) or is_self_sent_mail(msg):
        return None
    linked = _link(conn, msg)
    space = normalize_space(state.get("space_id") if state and state.get("space_id") else linked.get("space_id"))
    name, email = parse_from(msg.get("from"))
    suggested = suggest_reply(msg)
    source = msg.get("source") or "gmail"
    mid = str(msg.get("message_id") or "")
    href = open_href(source, mid, msg)
    out = {
        "id": f"{source}:{mid}",
        "source": source,
        "message_id": mid,
        "thread_id": msg.get("thread_id") or msg.get("threadId") or "",
        "account": msg.get("account") or source,
        "account_label": mail_account_label(source),
        "labels": msg.get("labels") or msg.get("labelIds") or [],
        "list_unsubscribe": msg.get("list_unsubscribe") or "",
        "from": redact_blocked(msg.get("from") or ""),
        "from_name": redact_blocked(name),
        "from_email": email,
        "to": redact_blocked(msg.get("to") or ""),
        "subject": redact_blocked(msg.get("subject") or ""),
        "date": msg.get("date"),
        "preview": redact_blocked((msg.get("preview") or "")[:280]),
        "unread": bool(msg.get("unread")),
        "waiting": _waiting_reason(msg),
        "space_id": space,
        "job_id": (state or {}).get("job_id") or linked.get("job_id"),
        "job_title": linked.get("job_title"),
        "resource_id": (state or {}).get("resource_id") or linked.get("resource_id"),
        "person_name": (linked.get("matched_people") or [{}])[0].get("name") if linked.get("matched_people") else name,
        "customer_id": linked.get("customer_id"),
        "suggested_reply": suggested,
        "open_href": href,
        "status": (state or {}).get("status") or "open",
        "read_only": True,
        "sent": False,
        "outbound_policy": OUTBOUND_POLICY,
        "actions": [
            {"id": "open", "label": "Open", "group": "mail", "href": href},
            {"id": "draft_reply", "label": "Draft reply", "group": "mail", "draft": True},
            {"id": "snooze", "label": "Snooze", "group": "mail"},
            {"id": "todo", "label": "Turn into to-do", "group": "mail"},
            {"id": "followup", "label": "Turn into follow-up", "group": "mail"},
        ],
    }
    return out


def list_pending(conn, *, limit: int = 40) -> dict:
    from app.services.organizer.store import ensure_schema
    ensure_schema(conn)
    now = now_iso()
    raw = fetch_raw_messages()
    items = []
    for msg in raw:
        if not msg.get("message_id"):
            continue
        state = _state_row(conn, msg.get("source") or "gmail", str(msg["message_id"]))
        if _is_hidden(state, now):
            continue
        decorated = decorate_message(conn, msg, state)
        if decorated:
            items.append(decorated)
    items.sort(key=lambda m: (0 if m.get("unread") else 1, m.get("date") or ""), reverse=False)
    paths = mailbox_token_paths()
    return {
        "count": len(items[:limit]),
        "items": items[:limit],
        "accounts": {
            "edition": process_edition(),
            "connected": paths["sources"],
            "gmail": bool(paths.get("gmail")),
            "outlook": bool(paths.get("outlook")),
        },
        "read_only": True,
        "sent": False,
        "outbound_policy": OUTBOUND_POLICY,
        "note": "Reading only. Draft reply goes to the approval queue — nothing is sent without the owner's tap.",
    }


def run_mail_action(conn, *, action: str, source: str, message_id: str, extra: Optional[dict] = None) -> dict:
    extra = extra or {}
    if action not in MAIL_ACTIONS:
        return {"ok": False, "sent": False, "message": f"Unknown mail action '{action}'"}
    pending = list_pending(conn)
    item = next((i for i in pending["items"] if i["source"] == source and i["message_id"] == message_id), None)
    if not item:
        raw = next((m for m in fetch_raw_messages() if str(m.get("message_id")) == str(message_id) and (m.get("source") or "gmail") == source), None)
        if raw:
            item = decorate_message(conn, raw, _state_row(conn, source, message_id))
    if not item:
        return {"ok": False, "sent": False, "message": "Message not found in this edition's mailboxes."}

    if action == "open":
        return {"ok": True, "sent": False, "action": "open", "href": item["open_href"], "outbound_policy": OUTBOUND_POLICY}

    # confirm is accepted for API symmetry and is never a send.
    if action == "draft_reply":
        body = (extra.get("body") or item.get("suggested_reply") or "").strip()
        from app.services.leadforge.growth import enqueue
        try:
            conn.commit()
        except Exception:
            pass
        approval = enqueue(
            channel="email",
            body=body,
            source="organizer_mail",
            source_ref=f"mail-reply-{source}-{message_id}",
            kind="email",
            title=f"Reply — {item.get('subject')}",
            to_name=item.get("from_name") or "",
            to_address=item.get("from_email") or "",
            subject=item.get("subject") or "",
            job_id=item.get("job_id"),
            customer_id=item.get("customer_id"),
            created_by="organizer",
        )
        _upsert_state(conn, source, message_id, approval_id=str(approval.get("id") or ""), notes="draft_reply")
        return {
            "ok": True,
            "sent": False,
            "action": "draft_reply",
            "approval": approval,
            "requires_confirm": True,
            "outbound_policy": OUTBOUND_POLICY,
            "message": "Reply drafted. Approve & Send is still required — nothing was sent.",
        }

    if action == "snooze":
        until = extra.get("snooze_until")
        if not until:
            until = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
        _upsert_state(conn, source, message_id, status="snoozed", snooze_until=until)
        return {"ok": True, "sent": False, "action": "snooze", "snooze_until": until, "message": "Snoozed. It will return to Pending messages after that time."}

    kind = "todo" if action == "todo" else "followup"
    created = insert_item(conn, {
        "kind": kind,
        "title": item.get("subject") or f"Email from {item.get('from_name')}",
        "job_id": item.get("job_id"),
        "customer_id": item.get("customer_id"),
        "resource_id": item.get("resource_id"),
        "reminder_draft": item.get("suggested_reply") if kind == "followup" else None,
        "notes": f"From {item.get('from')} via {source}: {item.get('preview')}",
        "space_id": item.get("space_id"),
        "status": "open",
        "followup_kind": "general" if kind == "followup" else None,
    })
    _upsert_state(conn, source, message_id, status="done", item_id=(created or {}).get("id"), notes=action)
    return {
        "ok": True,
        "sent": False,
        "action": action,
        "created": created,
        "outbound_policy": OUTBOUND_POLICY,
        "message": f"Saved as a {kind}. Nothing was sent.",
    }
