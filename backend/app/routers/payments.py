"""
Empire Stripe Payment Integration — SaaS Subscriptions + Workroom Invoice Payments.

Two payment flows, one Stripe account:
  1. SaaS Subscriptions (Lite/Pro/Empire tiers via Checkout)
  2. Workroom invoice one-time payments (payment links)

All Stripe calls gracefully degrade when STRIPE_SECRET_KEY is not set (503).
"""
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime
import os
import logging
import httpx

from app.middleware.rate_limiter import limiter

logger = logging.getLogger("empire.payments")

# ── Stripe SDK setup ─────────────────────────────────────────────────

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# SaaS tier price IDs (configured in Stripe dashboard)
STRIPE_PRICE_LITE = os.getenv("STRIPE_PRICE_LITE")
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO")
STRIPE_PRICE_EMPIRE = os.getenv("STRIPE_PRICE_EMPIRE")

TIER_PRICES = {
    "lite": STRIPE_PRICE_LITE,
    "pro": STRIPE_PRICE_PRO,
    "empire": STRIPE_PRICE_EMPIRE,
}

TIER_AMOUNTS = {
    "lite": 2900,   # $29/mo in cents
    "pro": 7900,    # $79/mo
    "empire": 19900, # $199/mo
}

stripe = None
if STRIPE_SECRET_KEY:
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_SECRET_KEY
        stripe = _stripe
        logger.info("Stripe configured successfully")
    except ImportError:
        logger.error("stripe package not installed — run: pip install stripe")
else:
    logger.warning("Stripe not configured — set STRIPE_SECRET_KEY in .env")

# Internal API base for notifications
API_BASE = f"http://localhost:{os.getenv('API_PORT', '8000')}/api/v1"


def _require_stripe():
    """Raise 503 if Stripe is not configured."""
    if stripe is None:
        raise HTTPException(status_code=503, detail="Stripe not configured — set STRIPE_SECRET_KEY in .env")


router = APIRouter(prefix="/payments", tags=["payments"])


# ── Schemas ──────────────────────────────────────────────────────────

# ── ApostApp URL allowlist (R1D-FIX-2) ────────────────────────────────
# Public ApostApp surface hostname (the ONLY host that may receive
# success/cancel redirects for the apostille_one_time flow).
APOSTAPP_PUBLIC_HOST = "apostapp.empirebox.store"

# Operator-side hostnames (gated by Cloudflare Access). MUST NOT appear
# in any apostille_one_time redirect URL — would 302 customers to a
# login page and effectively lose the payment.
_OPERATOR_HOSTS = frozenset({
    "studio.empirebox.store",
    "api.empirebox.store",
    "luxe.empirebox.store",
    "forge.empirebox.store",
    "hermes.empirebox.store",
    "empirebox.store",  # bare apex (no subdomain) — also operator
})


def _validate_apostille_checkout_url(label: str, url: Optional[str]) -> None:
    """Validate a success_url or cancel_url for the apostille_one_time flow.

    Raises HTTPException(400) if the URL is:
      - missing/empty
      - not HTTPS
      - using localhost / 127.0.0.1 (any port or scheme)
      - using any operator hostname (would 302 customer to Access login)
      - using any host other than the public ApostApp surface
        (apostapp.empirebox.store)
      - malformed (cannot be parsed)

    This is the R1D-FIX-2 hardening to prevent silent fallback to
    operator/localhost URLs in the public Apostille payment flow.
    """
    from urllib.parse import urlparse

    if not url or not url.strip():
        raise HTTPException(
            status_code=400,
            detail=f"apostille flow requires {label} (non-empty)",
        )

    try:
        parsed = urlparse(url.strip())
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"apostille flow: {label} is not a valid URL",
        )

    # Scheme: must be https
    if parsed.scheme != "https":
        raise HTTPException(
            status_code=400,
            detail=f"apostille flow: {label} must use https, got {parsed.scheme!r}",
        )

    host = (parsed.hostname or "").lower()

    # Localhost / loopback (any port)
    if host in ("localhost",) or host.startswith("127.") or host == "::1":
        raise HTTPException(
            status_code=400,
            detail=f"apostille flow: {label} cannot use a loopback host (got {host!r})",
        )

    # Operator hostnames — would 302 the customer to a Cloudflare Access login
    if host in _OPERATOR_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"apostille flow: {label} cannot use an operator hostname "
                f"(got {host!r}); must be https://{APOSTAPP_PUBLIC_HOST}/..."
            ),
        )

    # Must be the public ApostApp surface
    if host != APOSTAPP_PUBLIC_HOST:
        raise HTTPException(
            status_code=400,
            detail=(
                f"apostille flow: {label} must use https://{APOSTAPP_PUBLIC_HOST}/..., "
                f"got host {host!r}"
            ),
        )


class CheckoutRequest(BaseModel):
    """Create a checkout session. Supports two flows:
    1. SaaS subscription (tier=lite|pro|empire) — recurring
    2. Apostille one-time payment (apostille_order_id set) — single charge

    URL handling:
      - SaaS flow (default): success_url/cancel_url are optional and default
        to operator-side URLs (studio.empirebox.store), which is correct
        because the SaaS flow is operator-facing.
      - Apostille one_time flow: success_url/cancel_url are REQUIRED and
        MUST be https URLs on the public ApostApp surface
        (apostapp.empirebox.store). The R1B ApostilleIntakeForm.jsx passes
        these explicitly. The backend enforces them at validation time
        (R1D-FIX-2).
    """
    tier: Optional[str] = None  # lite, pro, empire (SaaS only)
    customer_email: Optional[str] = None
    user_id: Optional[str] = None  # internal user id for subscription persistence
    success_url: Optional[str] = "https://studio.empirebox.store/payments/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url: Optional[str] = "https://studio.empirebox.store/payments/cancel"
    # Apostille one-time flow (R1B Fast Lane) — see app/routers/apostapp_public.py
    flow: Optional[str] = None  # "apostille_one_time" for single-charge apostille
    apostille_order_id: Optional[str] = None  # when flow=apostille_one_time
    apostille_package_id: Optional[str] = None  # basic_intake|standard|rush
    apostille_amount_cents: Optional[int] = None  # required when flow=apostille_one_time

    @model_validator(mode="after")
    def _validate_apostille_urls(self):
        """R1D-FIX-2: enforce URL rules for the apostille_one_time flow.

        Only runs when flow == "apostille_one_time". The SaaS branch is
        unaffected (success_url/cancel_url stay optional with operator
        defaults).
        """
        if self.flow == "apostille_one_time":
            _validate_apostille_checkout_url("success_url", self.success_url)
            _validate_apostille_checkout_url("cancel_url", self.cancel_url)
        return self


class InvoiceLinkRequest(BaseModel):
    """Generate a one-time payment link for an invoice (WoodCraft + Workroom).

    Sprint 1d Payment Phase 1: supports full / percentage / fixed
    partial amounts. All amounts resolve server-side. Business identity
    ('workroom' | 'woodcraft') is propagated to the Stripe checkout
    session via metadata → webhook → canonical payments_v2.
    """
    invoice_id: str
    # amount_mode: 'full' (default) charges the entire balance_due;
    # 'percentage' charges amount_value percent (0 < x <= 100);
    # 'fixed' charges exactly amount_value dollars.
    amount_mode: str = "full"
    amount_value: float = 0
    success_url: str = "https://studio.empirebox.store/payments/invoice-success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url: str = "https://studio.empirebox.store/payments/invoice-cancel"


class PortalRequest(BaseModel):
    """Customer portal access."""
    customer_id: str
    return_url: str = "https://studio.empirebox.store/account"


# ── Helpers ──────────────────────────────────────────────────────────

async def _notify_internal(title: str, message: str, context: dict = None):
    """Send an internal notification (logged, not pushed to Telegram)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{API_BASE}/notifications/internal", json={
                "source": "Business",
                "type": "business_event",
                "title": title,
                "message": message,
                "priority": "medium",
                "context": context or {},
            })
    except Exception as e:
        logger.error(f"Failed to send internal notification: {e}")


async def _notify_emergency(title: str, message: str, context: dict = None):
    """Send an emergency notification for payment failures."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{API_BASE}/notifications/emergency", json={
                "source": "Business",
                "type": "error",
                "title": title,
                "message": message,
                "priority": "critical",
                "context": context or {},
            })
    except Exception as e:
        logger.error(f"Failed to send emergency notification: {e}")


def _update_invoice_status(invoice_id: str, status: str, payment_method: str = "card",
                           stripe_session_id: str = None,
                           amount_cents: int = None,
                           business_unit: str = None):
    """Update invoice status and record payment in finance DB.

    Sprint 1d Payment Phase 1:
      - Inserts into canonical `payments_v2` (NOT legacy `payments`)
      - `stripe_session_id` triggers idempotency: if a row with the
        same stripe_session_id already exists, return success without
        inserting (Stripe webhook can retry).
      - Computes amount_paid from SUM(payments_v2.amount) and
        sets invoice status='paid' | 'partial' based on whether balance
        remains.
      - Persists business_unit (from invoice row) on the payment row.
    """
    try:
        from app.db.database import get_db, dict_row
        with get_db() as conn:
            inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
            if not inv:
                logger.warning(f"Invoice {invoice_id} not found for status update")
                return False

            inv_dict = dict_row(inv)

            if status == "paid":
                # IDEMPOTENCY: skip if stripe_session_id already in payments_v2
                if stripe_session_id:
                    existing = conn.execute(
                        "SELECT 1 FROM payments_v2 WHERE stripe_session_id = ? LIMIT 1",
                        (stripe_session_id,),
                    ).fetchone()
                    if existing:
                        logger.info(
                            f"Webhook: stripe_session_id={stripe_session_id} already in payments_v2, skip"
                        )
                        return True

                # Use explicit amount_cents if provided (from metadata); else full balance_due
                from datetime import date
                if amount_cents is not None:
                    amount = amount_cents / 100.0
                else:
                    amount = inv_dict.get("balance_due") or inv_dict.get("total", 0)
                # business_unit: prefer the param (from metadata), else read from invoice row
                bu = business_unit or inv_dict.get("business_unit") or "workroom"

                conn.execute(
                    """INSERT INTO payments_v2
                       (payment_number, invoice_id, customer_id, amount,
                        payment_method, payment_reference, payment_type, status,
                        account_code, notes, business_unit,
                        stripe_session_id, payment_date, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"pay_{stripe_session_id[:24]}" if stripe_session_id
                            else f"pay_{int(date.today().strftime('%Y%m%d'))}_{invoice_id[:6]}",
                        invoice_id,
                        inv_dict.get("customer_id"),
                        amount,
                        payment_method,
                        stripe_session_id or "",
                        "payment",
                        "completed",
                        None,
                        f"Paid via Stripe checkout.session.completed",
                        bu,
                        stripe_session_id or None,
                        date.today().isoformat(),
                        date.today().isoformat() + "T00:00:00",
                        date.today().isoformat() + "T00:00:00",
                    ),
                )

                # Recalculate totals from canonical payments_v2
                subtotal = inv_dict.get("subtotal", 0)
                tax_rate = inv_dict.get("tax_rate", 0)
                tax_amount = round(subtotal * tax_rate, 2)
                total = round(subtotal + tax_amount, 2)

                paid_row = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS total_paid FROM payments_v2 WHERE invoice_id = ?",
                    (invoice_id,),
                ).fetchone()
                amount_paid = paid_row["total_paid"]
                balance_due = round(total - amount_paid, 2)

                new_status = "paid" if balance_due <= 0.005 else "partial"
                conn.execute(
                    """UPDATE invoices SET status = ?, amount_paid = ?, balance_due = ?,
                       paid_at = CASE WHEN ? = 'paid' THEN datetime('now') ELSE paid_at END,
                       updated_at = datetime('now') WHERE id = ?""",
                    (new_status, amount_paid, max(balance_due, 0), new_status, invoice_id),
                )

                # Update customer total_revenue from canonical payments_v2
                if inv_dict.get("customer_id"):
                    conn.execute(
                        """UPDATE customers SET total_revenue = (
                             SELECT COALESCE(SUM(amount), 0) FROM payments_v2 WHERE customer_id = ?
                           ), updated_at = datetime('now') WHERE id = ?""",
                        (inv_dict["customer_id"], inv_dict["customer_id"]),
                    )
            else:
                conn.execute(
                    "UPDATE invoices SET status = ?, updated_at = datetime('now') WHERE id = ?",
                    (status, invoice_id)
                )

            return True
    except Exception as e:
        import traceback
        logger.error(f"Failed to update invoice {invoice_id}: {e}\n{traceback.format_exc()}")
        return False


def _mark_apostille_order_paid(order_id: str, stripe_session_id: str = "", amount_cents: int = 0):
    """Mark an apostille order as paid in the JSON store. Used by the
    apostille_one_time Stripe webhook branch."""
    import json as _json
    import os as _os
    base = _os.path.expanduser("~/empire-repo/backend/data/apostapp/orders")
    path = _os.path.join(base, f"{order_id}.json")
    if not _os.path.exists(path):
        logger.warning(f"Apostille order {order_id} not found for paid flip")
        return False
    try:
        with open(path) as f:
            order = _json.load(f)
        order["paid"] = True
        order["status"] = order.get("status", "received")
        order["payment_session_id"] = stripe_session_id
        order["payment_amount_cents"] = amount_cents
        order["payment_completed_at"] = datetime.utcnow().isoformat()
        order["updated_at"] = datetime.utcnow().isoformat()
        with open(path, "w") as f:
            _json.dump(order, f, indent=2, default=str)
        logger.info(f"Apostille order {order_id} marked paid (${amount_cents/100:.2f})")
        return True
    except Exception as e:
        logger.error(f"Failed to mark apostille order {order_id} paid: {e}")
        return False


# ── Flow 1: SaaS Subscription Checkout ───────────────────────────────

@limiter.limit("10/minute")
@router.post("/checkout")
async def create_checkout_session(request: Request, req: CheckoutRequest):
    """Create a Stripe Checkout session.

    Two flows are supported:
      1. SaaS subscription (tier=lite|pro|empire) — recurring monthly.
      2. Apostille one-time (flow=apostille_one_time + apostille_order_id) — single charge.

    The two flows are mutually exclusive: if flow is set, tier is ignored.
    """
    _require_stripe()

    # ── Flow 2: Apostille one-time payment ──
    if req.flow == "apostille_one_time":
        if not req.apostille_order_id or not req.apostille_amount_cents:
            raise HTTPException(
                status_code=400,
                detail="apostille flow requires apostille_order_id and apostille_amount_cents",
            )
        if req.apostille_amount_cents <= 0:
            raise HTTPException(status_code=400, detail="apostille_amount_cents must be > 0")

        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": req.apostille_amount_cents,
                        "product_data": {
                            "name": f"Apostille — Order {req.apostille_order_id}",
                            "description": f"EmpireBox Apostille Fast Lane — {req.apostille_package_id or 'standard'} package",
                        },
                    },
                    "quantity": 1,
                }],
                success_url=req.success_url,
                cancel_url=req.cancel_url,
                metadata={
                    "apostille_order_id": req.apostille_order_id,
                    "apostille_package_id": req.apostille_package_id or "standard",
                    "flow": "apostille_one_time",
                },
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "apostille_order_id": req.apostille_order_id,
                "amount_cents": req.apostille_amount_cents,
                "flow": "apostille_one_time",
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe apostille checkout error: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    # ── Flow 1: SaaS subscription (default) ──
    if not req.tier:
        raise HTTPException(
            status_code=400,
            detail="Either tier (SaaS) or flow=apostille_one_time (apostille) is required",
        )
    tier = req.tier.lower()
    if tier not in TIER_PRICES:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}. Must be one of: lite, pro, empire")

    price_id = TIER_PRICES[tier]
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"Price ID for tier '{tier}' not configured — set STRIPE_PRICE_{tier.upper()} in .env"
        )

    try:
        session_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": req.success_url,
            "cancel_url": req.cancel_url,
            "metadata": {"tier": tier, "flow": "saas_subscription", "user_id": req.user_id or ""},
        }
        if req.customer_email:
            session_params["customer_email"] = req.customer_email
        if req.user_id:
            session_params["client_reference_id"] = req.user_id

        session = stripe.checkout.Session.create(**session_params)

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "tier": tier,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Flow 2: Workroom Invoice Payment Link ────────────────────────────

@limiter.limit("10/minute")
@router.post("/invoice-link")
async def create_invoice_payment_link(request: Request, req: InvoiceLinkRequest):
    """Generate a Stripe-HOSTED Checkout session for an invoice payment.

    Sprint 1d Payment Phase 1:
      - amount_mode 'full' (default) charges the entire balance_due.
      - amount_mode 'percentage' charges amount_value percent of balance_due.
      - amount_mode 'fixed' charges exactly amount_value dollars.
    All amounts resolve server-side. Business identity is propagated
    via metadata → webhook → canonical payments_v2.
    """
    _require_stripe()

    from app.db.database import get_db, dict_row
    with get_db() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (req.invoice_id,)).fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail=f"Invoice {req.invoice_id} not found")
        inv_dict = dict_row(inv)

    if inv_dict.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already paid")

    total_dollars = float(inv_dict.get("total") or 0)
    balance_dollars = float(inv_dict.get("balance_due") or total_dollars)

    # Resolve amount based on mode
    if req.amount_mode == "full":
        amount_dollars = balance_dollars
    elif req.amount_mode == "percentage":
        if not (0 < req.amount_value <= 100):
            raise HTTPException(status_code=400, detail="percentage must be 0 < x <= 100")
        amount_dollars = round(balance_dollars * (req.amount_value / 100.0), 2)
    elif req.amount_mode == "fixed":
        if req.amount_value <= 0:
            raise HTTPException(status_code=400, detail="fixed amount must be > 0")
        amount_dollars = float(req.amount_value)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"amount_mode must be full|percentage|fixed, got {req.amount_mode!r}",
        )

    if amount_dollars > balance_dollars + 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"amount ${amount_dollars} exceeds outstanding balance ${balance_dollars}",
        )

    amount_cents = int(round(amount_dollars * 100))
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="computed amount is 0")

    invoice_number = inv_dict.get("invoice_number", req.invoice_id)
    business_unit = inv_dict.get("business_unit", "workroom")
    payment_kind = "partial" if amount_dollars < (total_dollars - 0.01) else "full"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": f"Invoice {invoice_number}",
                        "description": f"Payment for invoice {invoice_number} ({payment_kind})",
                    },
                },
                "quantity": 1,
            }],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            metadata={
                "invoice_id": req.invoice_id,
                "invoice_number": invoice_number,
                "business_unit": business_unit,           # ← Phase 1: propagated
                "payment_kind": payment_kind,                # ← Phase 1: 'full'|'partial'
                "amount_cents": str(amount_cents),           # ← Phase 1: redundant safety
                "flow": "workroom_invoice",                  # ← preserves existing handler routing
            },
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "invoice_id": req.invoice_id,
            "invoice_number": invoice_number,
            "amount": amount_dollars,
            "amount_cents": amount_cents,
            "payment_kind": payment_kind,
            "business_unit": business_unit,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe invoice link error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Webhook Handler ──────────────────────────────────────────────────

def _require_webhook_secret():
    """Fail-closed: reject all webhooks if STRIPE_WEBHOOK_SECRET is not configured.

    R1D-FIX safety hardening. The previous behavior fell back to parsing the
    payload without signature verification when the secret was missing, which
    is acceptable in dev (test mode) but unacceptable for live mode — any
    attacker who can reach the webhook URL could forge a
    `checkout.session.completed` event and flip arbitrary orders to `paid=true`.
    For live deployments, the operator must configure STRIPE_WEBHOOK_SECRET
    BEFORE switching Stripe to live mode. If it is missing or empty, every
    webhook request is rejected with HTTP 503, no body is parsed, no order is
    mutated, and the secret value is never logged.
    """
    if not STRIPE_WEBHOOK_SECRET or not STRIPE_WEBHOOK_SECRET.strip():
        # Safe log: only the variable name and the fact that it's missing.
        # Never log the (empty) secret itself, and never log any part of the
        # incoming payload (it could contain PII, signed-but-bad data, etc.).
        logger.error(
            "Webhook rejected: STRIPE_WEBHOOK_SECRET is not configured. "
            "Set STRIPE_WEBHOOK_SECRET in .env to accept live webhooks."
        )
        raise HTTPException(
            status_code=503,
            detail="Webhook unavailable: STRIPE_WEBHOOK_SECRET not configured",
        )


@limiter.limit("60/minute")
@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events.

    Behavior:
      * If STRIPE_SECRET_KEY is not set → 503 (no Stripe configured at all).
      * If STRIPE_WEBHOOK_SECRET is missing/empty → 503 fail-closed (R1D-FIX).
        The request body is NOT parsed, no order is mutated, the secret value
        is not logged.
      * If STRIPE_WEBHOOK_SECRET is set → verify Stripe signature; reject
        invalid signatures (400); accept valid signed events.

    Signed payloads only. No unsigned fallback. This applies to test mode AND
    live mode — there is no dev convenience path that bypasses signature
    verification anymore.
    """
    _require_stripe()
    _require_webhook_secret()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify webhook signature (STRIPE_WEBHOOK_SECRET is guaranteed non-empty
    # by _require_webhook_secret above, so this branch is the only path).
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Webhook: invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    logger.info(f"Webhook received: {event_type}")

    # ── checkout.session.completed ──
    if event_type == "checkout.session.completed":
        metadata = data.get("metadata", {})
        flow = metadata.get("flow", "")

        if flow == "saas_subscription":
            tier = metadata.get("tier", "unknown")
            customer_email = data.get("customer_email", "")
            subscription_id = data.get("subscription", "")
            client_ref = data.get("client_reference_id", "")
            stripe_customer_id = data.get("customer", "")
            period_end = None
            if subscription_id:
                try:
                    sub = stripe.Subscription.retrieve(subscription_id)
                    period_end = sub.get("current_period_end")
                except Exception:
                    pass

            if client_ref:
                with get_db() as conn:
                    conn.execute(
                        """UPDATE access_users SET
                           tier = ?,
                           stripe_customer_id = COALESCE(?, stripe_customer_id),
                           stripe_subscription_id = ?,
                           stripe_current_period_end = ?,
                           updated_at = datetime('now')
                           WHERE id = ?""",
                        (tier, stripe_customer_id, subscription_id,
                         period_end, client_ref),
                    )

            await _notify_internal(
                title=f"New {tier.title()} Subscription",
                message=f"Customer {customer_email} subscribed to {tier.title()} plan (${TIER_AMOUNTS.get(tier, 0) / 100:.0f}/mo)",
                context={
                    "tier": tier,
                    "customer_email": customer_email,
                    "subscription_id": subscription_id,
                    "stripe_session_id": data.get("id"),
                    "user_id": client_ref,
                },
            )

        elif flow == "workroom_invoice":
            invoice_id = metadata.get("invoice_id", "")
            invoice_number = metadata.get("invoice_number", "")
            if invoice_id:
                # Sprint 1d Phase 1: read business_unit + amount_cents from
                # metadata (set by create_invoice_payment_link) so the
                # webhook doesn't have to fetch from Stripe again.
                bu = metadata.get("business_unit")
                amt_cents = None
                mc = metadata.get("amount_cents")
                if mc and str(mc).isdigit():
                    amt_cents = int(mc)
                _update_invoice_status(
                    invoice_id, "paid",
                    payment_method="card",
                    stripe_session_id=data.get("id"),
                    amount_cents=amt_cents,
                    business_unit=bu,
                )
                await _notify_internal(
                    title=f"Invoice {invoice_number} Paid",
                    message=f"Invoice {invoice_number} paid via Stripe (${data.get('amount_total', 0) / 100:.2f})",
                    context={
                        "invoice_id": invoice_id,
                        "invoice_number": invoice_number,
                        "amount": data.get("amount_total", 0) / 100,
                        "stripe_session_id": data.get("id"),
                        "business_unit": bu,
                    },
                )

        elif flow == "apostille_one_time":
            # R1B Fast Lane: flip paid=true on the matching apostille order.
            apostille_order_id = metadata.get("apostille_order_id", "")
            if apostille_order_id:
                _mark_apostille_order_paid(
                    apostille_order_id,
                    stripe_session_id=data.get("id", ""),
                    amount_cents=data.get("amount_total", 0),
                )
                await _notify_internal(
                    title=f"Apostille Order {apostille_order_id} Paid",
                    message=f"Apostille order {apostille_order_id} paid via Stripe (${data.get('amount_total', 0) / 100:.2f})",
                    context={
                        "apostille_order_id": apostille_order_id,
                        "package_id": metadata.get("apostille_package_id", ""),
                        "amount": data.get("amount_total", 0) / 100,
                        "stripe_session_id": data.get("id"),
                    },
                )

    # ── customer.subscription.updated ──
    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id", "")
        status = data.get("status", "")
        customer_id = data.get("customer", "")
        items = data.get("items", {}).get("data", [])
        price_id = items[0].get("price", {}).get("id", "") if items else ""

        # Determine tier from price ID
        tier = "unknown"
        for t, pid in TIER_PRICES.items():
            if pid and pid == price_id:
                tier = t
                break

        period_end = data.get("current_period_end")

        if customer_id:
            with get_db() as conn:
                conn.execute(
                    """UPDATE access_users SET
                       tier = ?, stripe_current_period_end = ?, updated_at = datetime('now')
                       WHERE stripe_customer_id = ?""",
                    (tier, period_end, customer_id),
                )

        await _notify_internal(
            title=f"Subscription Updated",
            message=f"Subscription {subscription_id} updated to {tier} (status: {status})",
            context={
                "subscription_id": subscription_id,
                "tier": tier,
                "status": status,
                "customer_id": customer_id,
            },
        )

    # ── customer.subscription.deleted ──
    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id", "")
        customer_id = data.get("customer", "")

        if customer_id:
            with get_db() as conn:
                conn.execute(
                    """UPDATE access_users SET
                       tier = 'lite', stripe_subscription_id = NULL, updated_at = datetime('now')
                       WHERE stripe_customer_id = ?""",
                    (customer_id,),
                )

        await _notify_internal(
            title="Subscription Cancelled",
            message=f"Subscription {subscription_id} cancelled — customer downgraded to lite",
            context={
                "subscription_id": subscription_id,
                "customer_id": customer_id,
            },
        )

    # ── invoice.payment_failed ──
    elif event_type == "invoice.payment_failed":
        customer_email = data.get("customer_email", "")
        amount = data.get("amount_due", 0) / 100
        subscription_id = data.get("subscription", "")
        await _notify_emergency(
            title="Payment Failed",
            message=f"Payment of ${amount:.2f} failed for {customer_email} (subscription: {subscription_id})",
            context={
                "customer_email": customer_email,
                "amount": amount,
                "subscription_id": subscription_id,
                "attempt_count": data.get("attempt_count", 0),
            },
        )

    return {"status": "ok", "event_type": event_type}


# ── Customer Portal ──────────────────────────────────────────────────

@limiter.limit("10/minute")
@router.get("/portal")
async def customer_portal(request: Request, customer_id: str, return_url: str = "https://studio.empirebox.store/account"):
    """Generate a Stripe Customer Portal link for self-service subscription management."""
    _require_stripe()

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return {"portal_url": session.url}
    except stripe.error.StripeError as e:
        logger.error(f"Portal error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Payment Status ───────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/status/{session_id}")
async def payment_status(request: Request, session_id: str):
    """Check the status of a Stripe Checkout session."""
    _require_stripe()

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        result = {
            "session_id": session.id,
            "status": session.status,
            "payment_status": session.payment_status,
            "customer_email": session.customer_details.email if session.customer_details else None,
            "amount_total": session.amount_total / 100 if session.amount_total else None,
            "currency": session.currency,
            "metadata": dict(session.metadata) if session.metadata else {},
        }

        # Add subscription info if applicable
        if session.subscription:
            result["subscription_id"] = session.subscription

        return result
    except stripe.error.StripeError as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Active Subscriptions ─────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/subscriptions")
async def list_subscriptions(
    request: Request,
    status: str = Query("active", description="Filter by status: active, canceled, past_due, all"),
    limit: int = Query(25, ge=1, le=100),
):
    """List active Stripe subscriptions."""
    _require_stripe()

    try:
        params = {"limit": limit}
        if status != "all":
            params["status"] = status

        subscriptions = stripe.Subscription.list(**params)

        results = []
        for sub in subscriptions.data:
            items = sub.get("items", {}).get("data", [])
            price_id = items[0].get("price", {}).get("id", "") if items else ""

            tier = "unknown"
            for t, pid in TIER_PRICES.items():
                if pid and pid == price_id:
                    tier = t
                    break

            results.append({
                "subscription_id": sub.id,
                "customer_id": sub.customer,
                "status": sub.status,
                "tier": tier,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "created": sub.created,
            })

        return {"subscriptions": results, "count": len(results)}
    except stripe.error.StripeError as e:
        logger.error(f"List subscriptions error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Payment History ──────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/history")
async def payment_history(
    request: Request,
    limit: int = Query(25, ge=1, le=100),
    starting_after: Optional[str] = None,
):
    """List recent Stripe payment intents (payment history)."""
    _require_stripe()

    try:
        params = {"limit": limit}
        if starting_after:
            params["starting_after"] = starting_after

        payments = stripe.PaymentIntent.list(**params)

        results = []
        for pi in payments.data:
            results.append({
                "payment_id": pi.id,
                "amount": pi.amount / 100,
                "currency": pi.currency,
                "status": pi.status,
                "description": pi.description,
                "customer_id": pi.customer,
                "metadata": dict(pi.metadata) if pi.metadata else {},
                "created": pi.created,
            })

        return {
            "payments": results,
            "count": len(results),
            "has_more": payments.has_more,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Payment history error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── PaymentIntent (for client portal direct pay) ────────────────────

@router.post("/create-intent")
async def create_payment_intent(body: dict):
    """Create a Stripe PaymentIntent for direct payment from client portal."""
    _require_stripe()

    invoice_id = body.get("invoice_id")
    amount = body.get("amount")
    customer_email = body.get("customer_email", "")
    description = body.get("description", "Empire Workroom Payment")
    payment_type = body.get("payment_type", "payment")

    if not invoice_id or not amount:
        raise HTTPException(400, "invoice_id and amount required")

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100),
            currency="usd",
            description=description,
            receipt_email=customer_email or None,
            metadata={
                "invoice_id": str(invoice_id),
                "payment_type": payment_type,
                "source": "empire_portal",
            },
        )
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "amount": amount,
        }
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))


# ── Overdue Invoices ────────────────────────────────────────────────

@router.get("/overdue")
async def overdue_invoices():
    """List overdue invoices (unpaid past due_date)."""
    from app.db.database import get_db
    with get_db() as conn:
        now = datetime.now().isoformat()[:10]
        rows = conn.execute("""
            SELECT i.*, c.name as customer_name, c.email as customer_email, c.phone as customer_phone
            FROM invoices i
            LEFT JOIN customers c ON c.id = i.customer_id
            WHERE i.status IN ('sent', 'partial', 'overdue', 'pending')
              AND i.balance_due > 0
              AND i.due_date IS NOT NULL AND i.due_date < ?
            ORDER BY i.due_date ASC
        """, (now,)).fetchall()

        invoices = []
        for r in rows:
            d = dict(r)
            due = d.get("due_date", "")
            if due:
                try:
                    days_overdue = (datetime.now() - datetime.fromisoformat(due)).days
                    d["days_overdue"] = days_overdue
                except (ValueError, TypeError):
                    d["days_overdue"] = 0
            invoices.append(d)

        total_outstanding = sum(i.get("balance_due", 0) for i in invoices)
        return {
            "overdue_invoices": invoices,
            "count": len(invoices),
            "total_outstanding": round(total_outstanding, 2),
        }


# ── Auto-Reminders ──────────────────────────────────────────────────

@router.post("/send-reminders")
async def send_payment_reminders():
    """Send automatic reminders for overdue and upcoming invoices.
    Called by morning cron or manually."""
    from app.db.database import get_db
    reminders_sent = 0
    now = datetime.now()

    with get_db() as conn:
        rows = conn.execute("""
            SELECT i.id, i.invoice_number, i.total, i.balance_due, i.due_date,
                   i.customer_id, c.name as customer_name, c.email as customer_email
            FROM invoices i
            LEFT JOIN customers c ON c.id = i.customer_id
            WHERE i.status IN ('sent', 'partial', 'overdue', 'pending')
              AND i.balance_due > 0
              AND i.due_date IS NOT NULL
              AND c.email IS NOT NULL AND c.email != ''
        """).fetchall()

        reminders = []
        for r in rows:
            d = dict(r)
            due = d.get("due_date", "")
            if not due:
                continue
            try:
                due_dt = datetime.fromisoformat(due)
                days_until = (due_dt - now).days
            except (ValueError, TypeError):
                continue

            reminder_type = None
            if days_until < -7:
                reminder_type = "overdue_final"
            elif days_until < 0:
                reminder_type = "overdue"
            elif days_until <= 3:
                reminder_type = "due_soon"

            if reminder_type:
                reminders.append({**d, "reminder_type": reminder_type, "days_until": days_until})

                # Check for portal link
                portal = conn.execute(
                    "SELECT token FROM client_portal_tokens WHERE customer_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
                    (d["customer_id"],)
                ).fetchone()
                pay_url = f"https://studio.empirebox.store/portal/{portal[0]}" if portal else None

                logger.info(
                    f"Payment reminder ({reminder_type}): {d['customer_name']} — "
                    f"Invoice #{d['invoice_number']} — ${d['balance_due']:.2f} — "
                    f"{'portal: ' + pay_url if pay_url else 'no portal'}"
                )
                reminders_sent += 1

    return {
        "reminders_sent": reminders_sent,
        "reminders": reminders,
    }


@router.post("/send-reminder/{invoice_id}")
async def send_single_reminder(invoice_id: str):
    """Send a payment reminder for a specific invoice."""
    from app.db.database import get_db
    with get_db() as conn:
        inv = conn.execute("""
            SELECT i.*, c.name as customer_name, c.email as customer_email
            FROM invoices i
            LEFT JOIN customers c ON c.id = i.customer_id
            WHERE i.id = ?
        """, (invoice_id,)).fetchone()

        if not inv:
            raise HTTPException(404, f"Invoice {invoice_id} not found")

        d = dict(inv)
        if d.get("balance_due", 0) <= 0:
            return {"status": "no_balance", "message": "Invoice has no outstanding balance"}

        portal = conn.execute(
            "SELECT token FROM client_portal_tokens WHERE customer_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
            (d.get("customer_id"),)
        ).fetchone()
        pay_url = f"https://studio.empirebox.store/portal/{portal[0]}" if portal else None

        logger.info(f"Manual reminder: {d.get('customer_name')} — Invoice #{d.get('invoice_number')} — ${d.get('balance_due', 0):.2f}")

        return {
            "status": "sent",
            "invoice_id": invoice_id,
            "customer": d.get("customer_name"),
            "balance": d.get("balance_due"),
            "portal_url": pay_url,
        }
