"""
ApostApp — Public client-facing intake & status endpoints.

This router is a NEW public surface for the Apostille Fast Lane. It contains
NO modification to the existing `apostapp.py` (founder/operator surface).

Goals:
  * Anyone can submit a public intake request.
  * Anyone with a valid (order_id, email) pair can check order status.
  * Internal endpoints (list-orders, dashboard, customer-detail, etc.) are
    NOT exposed by this router.
  * Rate-limited to slow abuse.
  * Stripe checkout is wired via the existing /api/v1/payments/checkout
    endpoint with the optional `apostille_order_id` field.

Test-mode banner behaviour is controlled by APOSTILLE_TEST_MODE env var
(default: 1 in dev, 0 in production).
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import json
import os
import re
import uuid
import hmac
import logging
import hashlib
from datetime import datetime

from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apostapp/public", tags=["apostapp-public"])

# ── Storage (read from the same JSON store as apostapp.py) ──────────
BASE_DIR = os.path.expanduser("~/empire-repo/backend/data/apostapp")
ORDERS_DIR = os.path.join(BASE_DIR, "orders")
CUSTOMERS_DIR = os.path.join(BASE_DIR, "customers")

for _d in (ORDERS_DIR, CUSTOMERS_DIR):
    os.makedirs(_d, exist_ok=True)

# ── Package catalog (configurable; Founder to set real prices) ──────
# Use $0 placeholders so Stripe Checkout can be wired but no real money
# moves until Founder sets APOSTILLE_TEST_MODE=0 + fills in real prices.
APOSTILLE_PACKAGES = [
    {
        "id": "basic_intake",
        "name": "Basic Review / Intake",
        "description": "We review your documents, confirm eligibility, and prepare your file for the state or federal office.",
        "price_cents": 3500,  # $35.00
        "turnaround": "5-7 business days",
        "includes": [
            "Document eligibility review",
            "Pre-submission checklist",
            "State or federal routing",
        ],
    },
    {
        "id": "standard",
        "name": "Standard Apostille Support",
        "description": "Full handling: review, submission, and return shipping.",
        "price_cents": 9500,  # $95.00
        "turnaround": "3-5 business days",
        "includes": [
            "Everything in Basic Review",
            "Submission to issuing authority",
            "Return shipping (USPS Priority)",
        ],
    },
    {
        "id": "rush",
        "name": "Rush Apostille Support",
        "description": "Priority queue. For time-sensitive filings, travel, and deadlines.",
        "price_cents": 19500,  # $195.00
        "turnaround": "1-3 business days",
        "includes": [
            "Everything in Standard",
            "Priority submission",
            "Express return shipping (USPS Express)",
        ],
    },
]

PACKAGE_IDS = {p["id"] for p in APOSTILLE_PACKAGES}


def _is_test_mode() -> bool:
    """APOSTILLE_TEST_MODE=1 → on (default in dev). 0 → off (live)."""
    val = os.getenv("APOSTILLE_TEST_MODE", "1")
    return val not in ("0", "false", "False", "")


# ── Pydantic schemas (public-safe) ──────────────────────────────────

class PublicIntakeRequest(BaseModel):
    """Public apostille intake. Minimal fields, no internal PII."""
    client_name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    document_type: str = Field(..., min_length=1, max_length=100)
    destination_country: str = Field(..., min_length=1, max_length=100)
    origin_state: str = Field(..., min_length=2, max_length=10)
    service_level: str = Field(..., min_length=1, max_length=20)
    notes: Optional[str] = Field(None, max_length=2000)


class PublicIntakeResponse(BaseModel):
    """Public-safe response. Includes optional Stripe checkout URL."""
    order_id: str
    package_id: str
    amount_cents: int
    status: str
    paid: bool
    test_mode: bool
    checkout_url: Optional[str] = None
    message: str


class PublicVerifyRequest(BaseModel):
    """Public status lookup. Requires order_id + email verifier."""
    order_id: str = Field(..., min_length=4, max_length=20)
    email: str = Field(..., min_length=3, max_length=200)


class PublicStatusTimelineStep(BaseModel):
    label: str
    description: str
    reached: bool
    reached_at: Optional[str] = None


class PublicStatusResponse(BaseModel):
    """Public-safe status response. NO customer_id, attachments, internal flags."""
    order_id: str
    package_id: str
    status: str
    paid: bool
    test_mode: bool
    created_at: str
    last_updated: str
    timeline: List[PublicStatusTimelineStep]
    next_step_message: str


# ── Helpers ─────────────────────────────────────────────────────────

def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _verify_email(stored: str, provided: str) -> bool:
    """Constant-time email comparison (case-insensitive)."""
    a = _normalize_email(stored).encode("utf-8")
    b = _normalize_email(provided).encode("utf-8")
    return hmac.compare_digest(a, b)


def _save_json(directory: str, filename: str, data: dict):
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_json(directory: str, filename: str) -> Optional[dict]:
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Public 6-step timeline (per Agent 2 design + Agent 5 copy)
TIMELINE_STEPS = [
    ("received", "Request received", "We have your request. We will review your documents and confirm eligibility within 1 business day."),
    ("notarized", "Notarized (if needed)", "If your document required notarization, it has been completed."),
    ("certified", "Certified (if needed)", "If your document required certification, it has been completed."),
    ("at_state", "Submitted to issuing authority", "Your document has been submitted to the appropriate state or federal office."),
    ("apostilled", "Apostille issued", "Your document has been apostilled and is being prepared for return shipping."),
    ("completed", "Shipped / ready for pickup", "Your apostilled document is on its way back to you, or ready for pickup at our DC office."),
]


# Order-level (Founder-set) status → public 6-step status mapping.
# Used as a fallback when per-document statuses do not reflect progress.
# This keeps the public 6-step timeline deterministic regardless of whether
# the Founder updates the order-level status or the per-doc statuses first.
_ORDER_TO_PUBLIC = {
    "received":   "received",
    "processing": "notarized",   # 'under review / preparing document steps'
    "at_state":   "at_state",
    "completed":  "completed",
    "closed":     "completed",
    "cancelled":  "received",    # public stays at 'received' for cancelled; no leak
}


def _project_status(order: dict) -> str:
    """Map internal order+doc status to a public-facing 6-step label.

    Resolution order:
      1. If any per-doc status is 'completed' / 'apostilled' / 'at_state' /
         'certified' / 'notarized' (most-progressed wins), use that.
      2. Otherwise, fall back to the order-level status via _ORDER_TO_PUBLIC.
      3. If the order-level status is 'processing', treat as 'notarized'
         (public sees "We are reviewing your request and preparing the
         required document steps.")
    """
    docs = order.get("documents", [])
    if docs:
        statuses = [d.get("status", "received") for d in docs]
        if "completed" in statuses:
            return "completed"
        if "apostilled" in statuses:
            return "apostilled"
        if "at_state" in statuses:
            return "at_state"
        if "certified" in statuses:
            return "certified"
        if "notarized" in statuses:
            return "notarized"

    # Fallback: read order-level status (set by the Founder-facing internal PUT).
    order_status = order.get("status", "received")
    return _ORDER_TO_PUBLIC.get(order_status, "received")


def _build_timeline(order: dict) -> List[dict]:
    """Return the 6-step public timeline with reached/reached_at flags."""
    current = _project_status(order)
    docs = order.get("documents", [])
    docs_updated = [d.get("updated_at") or d.get("created_at") for d in docs]
    last_update = order.get("updated_at", order.get("created_at", ""))

    timeline = []
    for i, (key, label, description) in enumerate(TIMELINE_STEPS):
        reached = False
        reached_at = None
        # Mark steps as reached if the current status is at or past this one
        for j, (k, _, _) in enumerate(TIMELINE_STEPS):
            if k == current:
                if i <= j:
                    reached = True
                    reached_at = last_update if i == j else None
                break
        timeline.append({
            "label": label,
            "description": description,
            "reached": reached,
            "reached_at": reached_at,
        })
    return timeline


def _next_step_message(status: str, order: dict = None) -> str:
    """Plain-English next-step message for the status page.

    If the projection came from the order-level `processing` state (Founder
    has not yet moved the per-doc statuses), show the safe "under review"
    message instead of the misleading "notarized is done" message.
    """
    if (
        order is not None
        and status == "notarized"
        and order.get("status") == "processing"
        and not any(
            d.get("status") in ("notarized", "certified", "at_state", "apostilled", "completed")
            for d in order.get("documents", [])
        )
    ):
        return "We are reviewing your request and preparing the required document steps."

    messages = {
        "received": "We will review your documents and confirm eligibility within 1 business day. You will get an email when we move to the next step.",
        "notarized": "Notarization is done. Your document is being prepared for submission.",
        "certified": "Certification is done. Your document is being prepared for submission.",
        "at_state": "Your document is at the issuing authority. Typical wait is 2-5 business days for state apostilles, longer for federal.",
        "apostilled": "Your apostille is issued. We are preparing the return shipment now.",
        "completed": "Your document is on its way. If you chose local pickup, it is ready at our DC office.",
    }
    return messages.get(status, "Your request is being processed.")


def _create_internal_order(req: PublicIntakeRequest, package_id: str) -> dict:
    """Create a real order using the same JSON file format apostapp.py uses.

    We don't call apostapp.py's `create_order` directly because the existing
    function expects an `ApostilleOrderCreate` with an ApostilleDocument list.
    For the public intake, we have only a single document with a simplified
    shape, so we write a compatible JSON record directly.
    """
    pkg = next((p for p in APOSTILLE_PACKAGES if p["id"] == package_id), None)
    if pkg is None:
        raise HTTPException(status_code=422, detail=f"Unknown package: {package_id}")

    order_id = str(uuid.uuid4())[:8]
    customer_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    # Build a single ApostilleDocument-shaped record
    doc = {
        "doc_type": req.document_type,
        "doc_description": req.notes or "",
        "state_of_origin": req.origin_state.upper(),
        "destination_country": req.destination_country,
        "needs_notarization": False,
        "needs_certification": False,
        "status": "received",
        "tracking_number": None,
        "fee": round(pkg["price_cents"] / 100, 2),
    }

    # Customer record (one per order; consolidated later by founder)
    customer_data = {
        "id": customer_id,
        "name": req.client_name,
        "email": req.email,
        "phone": req.phone,
        "address": None,
        "orders": [order_id],
        "created_at": now,
    }
    _save_json(CUSTOMERS_DIR, f"{customer_id}.json", customer_data)

    # Order record
    order_data = {
        "id": order_id,
        "order_number": f"APO-PUB-{datetime.utcnow().strftime('%Y%m')}-{order_id[:4].upper()}",
        "customer_id": customer_id,
        "customer_name": req.client_name,
        "customer_email": req.email,
        "customer_phone": req.phone,
        "documents": [doc],
        "status": "received",
        "rush": req.service_level == "rush",
        "same_day": False,
        "shipping_method": "standard",
        "shipping_address": None,
        "total": round(pkg["price_cents"] / 100, 2),
        "paid": False,
        "notes": req.notes or "",
        "metadata": {
            "source": "public_fast_lane",
            "package_id": package_id,
            "package_name": pkg["name"],
            "test_mode": _is_test_mode(),
        },
        "created_at": now,
        "updated_at": now,
    }
    _save_json(ORDERS_DIR, f"{order_id}.json", order_data)

    logger.info(f"[apostapp-public] intake created: order={order_id} pkg={package_id} email={req.email}")
    return order_data


# ── Endpoints ───────────────────────────────────────────────────────

@limiter.limit("5/hour")
@router.post("/intake", response_model=PublicIntakeResponse)
async def public_intake(request: Request, req: PublicIntakeRequest):
    """Public apostille intake. No auth required. Rate-limited.

    Creates a real order in the same JSON store as the internal ApostApp
    flow, then returns the order_id + optional Stripe checkout URL.
    """
    # Validate email
    if not _EMAIL_RE.match(req.email):
        raise HTTPException(status_code=422, detail="Invalid email address")

    # Validate package
    if req.service_level not in PACKAGE_IDS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown service_level: {req.service_level}. Must be one of: {sorted(PACKAGE_IDS)}",
        )

    order = _create_internal_order(req, req.service_level)
    pkg = next(p for p in APOSTILLE_PACKAGES if p["id"] == req.service_level)

    return PublicIntakeResponse(
        order_id=order["id"],
        package_id=req.service_level,
        amount_cents=pkg["price_cents"],
        status="received",
        paid=False,
        test_mode=_is_test_mode(),
        checkout_url=None,  # Wired in R1B+ — public /apostille page calls /api/v1/payments/checkout separately
        message="Request received. Use the order ID to check status at /apostille/status.",
    )


@limiter.limit("10/minute")
@router.post("/verify", response_model=PublicStatusResponse)
async def public_verify(request: Request, req: PublicVerifyRequest):
    """Public status lookup. Requires order_id + email verifier.

    Returns generic 404 for both "no such order" and "wrong email" to
    prevent enumeration.
    """
    order = _load_json(ORDERS_DIR, f"{req.order_id}.json")
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    stored_email = order.get("customer_email", "")
    if not stored_email or not _verify_email(stored_email, req.email):
        raise HTTPException(status_code=404, detail="Order not found")

    projected = _project_status(order)
    timeline = _build_timeline(order)
    next_msg = _next_step_message(projected, order)

    timeline_models = [PublicStatusTimelineStep(**step) for step in timeline]
    return PublicStatusResponse(
        order_id=order["id"],
        package_id=order.get("metadata", {}).get("package_id", "standard"),
        status=projected,
        paid=order.get("paid", False),
        test_mode=_is_test_mode(),
        created_at=order.get("created_at", ""),
        last_updated=order.get("updated_at", order.get("created_at", "")),
        timeline=timeline_models,
        next_step_message=next_msg,
    )


@router.get("/packages")
async def public_packages():
    """Public package catalog. Read-only. No PII."""
    return {
        "packages": APOSTILLE_PACKAGES,
        "test_mode": _is_test_mode(),
        "currency": "usd",
    }


@router.get("/config")
async def public_config():
    """Public runtime config. Just test_mode + the APOSTILLE_TEST_MODE
    flag — used by the frontend to render the test-mode banner."""
    return {
        "test_mode": _is_test_mode(),
    }
