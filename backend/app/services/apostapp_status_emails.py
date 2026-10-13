"""ApostApp client status emails — drafted only, never auto-sent.

Owner must approve a draft. An explicit send is a second owner action.
Even then, SMTP/SendGrid is skipped unless APOSTAPP_ALLOW_CLIENT_EMAIL_SEND=1.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger("empire.apostapp.emails")

STATUS_COPY = {
    "received": {
        "subject": "We received your ApostApp request — {order_id}",
        "preview": "Your apostille request is in. We will review it within 1 business day.",
        "body": (
            "Hello {customer_name},\n\n"
            "We received your ApostApp request ({order_id}). "
            "We will review your documents and confirm eligibility within 1 business day.\n\n"
            "Track status: https://apostapp.empirebox.store/apostille/status\n"
        ),
    },
    "paid": {
        "subject": "Payment received for ApostApp order {order_id}",
        "preview": "We recorded your test-mode or live payment for this apostille request.",
        "body": (
            "Hello {customer_name},\n\n"
            "Payment is on file for ApostApp order {order_id}. "
            "We will keep you posted as the file moves forward.\n"
        ),
    },
    "notarized": {
        "subject": "ApostApp update — notarization step for {order_id}",
        "preview": "Notarization is complete. We are preparing the next step.",
        "body": (
            "Hello {customer_name},\n\n"
            "Notarization is done for order {order_id}. "
            "Your document is being prepared for submission.\n"
        ),
    },
    "certified": {
        "subject": "ApostApp update — certification step for {order_id}",
        "preview": "Certification is complete. We are preparing submission.",
        "body": (
            "Hello {customer_name},\n\n"
            "Certification is done for order {order_id}. "
            "Your document is being prepared for submission.\n"
        ),
    },
    "at_state": {
        "subject": "ApostApp update — submitted for {order_id}",
        "preview": "Your document has been submitted to the issuing authority.",
        "body": (
            "Hello {customer_name},\n\n"
            "Order {order_id} has been submitted to the issuing authority. "
            "Typical wait is 2-5 business days for state apostilles.\n"
        ),
    },
    "apostilled": {
        "subject": "ApostApp update — apostille issued for {order_id}",
        "preview": "The apostille is issued. We are preparing return shipping.",
        "body": (
            "Hello {customer_name},\n\n"
            "The apostille for order {order_id} has been issued. "
            "We are preparing the return shipment now.\n"
        ),
    },
    "completed": {
        "subject": "ApostApp order {order_id} is on its way",
        "preview": "Your apostilled document has shipped or is ready for pickup.",
        "body": (
            "Hello {customer_name},\n\n"
            "Order {order_id} is complete. Your document is on its way, "
            "or ready for pickup if you chose local pickup.\n"
        ),
    },
}


def _data_root() -> str:
    return os.environ.get(
        "APOSTAPP_DATA_DIR",
        os.path.expanduser("~/empire-repo/backend/data/apostapp"),
    )


def drafts_dir() -> str:
    path = os.path.join(_data_root(), "email_drafts")
    os.makedirs(path, exist_ok=True)
    return path


def client_email_send_enabled() -> bool:
    return os.getenv("APOSTAPP_ALLOW_CLIENT_EMAIL_SEND", "0") in ("1", "true", "True")


def _now() -> str:
    return datetime.utcnow().isoformat()


def _save(draft: dict) -> dict:
    path = os.path.join(drafts_dir(), f"{draft['id']}.json")
    with open(path, "w") as fh:
        json.dump(draft, fh, indent=2, default=str)
    return draft


def _load(draft_id: str) -> Optional[dict]:
    path = os.path.join(drafts_dir(), f"{draft_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def list_drafts(order_id: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
    items = []
    directory = drafts_dir()
    for name in sorted(os.listdir(directory), reverse=True):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name)) as fh:
            item = json.load(fh)
        if order_id and item.get("order_id") != order_id:
            continue
        if status and item.get("status") != status:
            continue
        items.append(item)
    return items


def draft_status_email(order: dict, trigger: str = "received") -> dict:
    """Create a client-facing status email draft. Never sends."""
    customer_name = order.get("customer_name") or "there"
    order_id = order.get("id") or "unknown"
    email = order.get("customer_email") or ""
    copy = STATUS_COPY.get(trigger) or STATUS_COPY["received"]
    ctx = {"customer_name": customer_name, "order_id": order_id}
    draft = {
        "id": uuid.uuid4().hex[:12],
        "order_id": order_id,
        "to_email": email,
        "customer_name": customer_name,
        "trigger": trigger,
        "subject": copy["subject"].format(**ctx),
        "preview": copy["preview"].format(**ctx),
        "body": copy["body"].format(**ctx),
        "status": "drafted",
        "approved_at": None,
        "approved_by": None,
        "sent_at": None,
        "send_result": None,
        "auto_sent": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    _save(draft)
    logger.info(
        "[apostapp-email] drafted trigger=%s order=%s draft=%s (not sent)",
        trigger,
        order_id,
        draft["id"],
    )
    return draft


def get_draft(draft_id: str) -> Optional[dict]:
    return _load(draft_id)


def approve_draft(draft_id: str, approved_by: str = "owner") -> dict:
    draft = _load(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    if draft.get("status") == "sent":
        raise ValueError("already_sent")
    draft["status"] = "approved"
    draft["approved_at"] = _now()
    draft["approved_by"] = approved_by
    draft["updated_at"] = _now()
    return _save(draft)


def reject_draft(draft_id: str, rejected_by: str = "owner") -> dict:
    draft = _load(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    if draft.get("status") == "sent":
        raise ValueError("already_sent")
    draft["status"] = "rejected"
    draft["rejected_at"] = _now()
    draft["rejected_by"] = rejected_by
    draft["updated_at"] = _now()
    return _save(draft)


async def send_approved_draft(draft_id: str, send_fn=None) -> dict:
    """Owner-triggered send of an already-approved draft.

    Never auto-called. Refuses drafts that are not owner-approved.
    Live SMTP/SendGrid stays off unless APOSTAPP_ALLOW_CLIENT_EMAIL_SEND=1.
    """
    draft = _load(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    if draft.get("status") != "approved":
        raise PermissionError("owner_approval_required")
    if draft.get("auto_sent"):
        raise PermissionError("auto_send_forbidden")

    if not client_email_send_enabled():
        draft["status"] = "approved_queued_not_sent"
        draft["send_result"] = "queued_not_sent"
        draft["send_note"] = (
            "Owner approved. Client delivery is off "
            "(APOSTAPP_ALLOW_CLIENT_EMAIL_SEND!=1). Not sent."
        )
        draft["updated_at"] = _now()
        return _save(draft)

    sender = send_fn
    if sender is None:
        from app.services.email.sender import send_email

        sender = send_email

    sent = await sender(draft["to_email"], draft["subject"], draft["body"].replace("\n", "<br>"))
    draft["sent_at"] = _now()
    draft["send_result"] = "sent" if sent else "provider_skipped"
    draft["status"] = "sent" if sent else "approved_queued_not_sent"
    draft["updated_at"] = _now()
    return _save(draft)
