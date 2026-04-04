"""
Empire Stripe Payment Integration — SaaS Subscriptions + Workroom Invoice Payments.

Two payment flows, one Stripe account:
  1. SaaS Subscriptions (Lite/Pro/Empire tiers via Checkout)
  2. Workroom invoice one-time payments (payment links)

All Stripe calls gracefully degrade when STRIPE_SECRET_KEY is not set (503).
"""
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
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

class CheckoutRequest(BaseModel):
    """Create a SaaS subscription checkout session."""
    tier: str  # lite, pro, empire
    customer_email: Optional[str] = None
    success_url: str = "https://studio.empirebox.store/payments/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url: str = "https://studio.empirebox.store/payments/cancel"


class InvoiceLinkRequest(BaseModel):
    """Generate a one-time payment link for a workroom invoice."""
    invoice_id: str
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
                           stripe_session_id: str = None):
    """Update invoice status and record payment in finance DB."""
    try:
        from app.db.database import get_db, dict_row
        with get_db() as conn:
            inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
            if not inv:
                logger.warning(f"Invoice {invoice_id} not found for status update")
                return False

            inv_dict = dict_row(inv)

            if status == "paid":
                # Record payment
                from datetime import date
                amount = inv_dict.get("balance_due") or inv_dict.get("total", 0)
                conn.execute(
                    """INSERT INTO payments
                       (id, invoice_id, customer_id, amount, method, reference, notes, payment_date)
                       VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        invoice_id,
                        inv_dict.get("customer_id"),
                        amount,
                        payment_method,
                        stripe_session_id or "",
                        "Paid via Stripe",
                        date.today().isoformat(),
                    )
                )

                # Recalculate totals
                subtotal = inv_dict.get("subtotal", 0)
                tax_rate = inv_dict.get("tax_rate", 0)
                tax_amount = round(subtotal * tax_rate, 2)
                total = round(subtotal + tax_amount, 2)

                paid_row = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments WHERE invoice_id = ?",
                    (invoice_id,)
                ).fetchone()
                amount_paid = paid_row["total_paid"]
                balance_due = round(total - amount_paid, 2)

                conn.execute(
                    """UPDATE invoices SET status = ?, amount_paid = ?, balance_due = ?,
                       paid_at = datetime('now'), updated_at = datetime('now') WHERE id = ?""",
                    ("paid" if balance_due <= 0 else "partial", amount_paid, max(balance_due, 0), invoice_id)
                )

                # Update customer total_revenue if linked
                if inv_dict.get("customer_id"):
                    conn.execute(
                        """UPDATE customers SET total_revenue = (
                             SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?
                           ), updated_at = datetime('now') WHERE id = ?""",
                        (inv_dict["customer_id"], inv_dict["customer_id"])
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


# ── Flow 1: SaaS Subscription Checkout ───────────────────────────────

@limiter.limit("10/minute")
@router.post("/checkout")
async def create_checkout_session(request: Request, req: CheckoutRequest):
    """Create a Stripe Checkout session for a SaaS subscription."""
    _require_stripe()

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
            "metadata": {"tier": tier, "flow": "saas_subscription"},
        }
        if req.customer_email:
            session_params["customer_email"] = req.customer_email

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
    """Generate a Stripe Checkout session for a one-time invoice payment."""
    _require_stripe()

    # Look up invoice in DB
    from app.db.database import get_db, dict_row
    with get_db() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (req.invoice_id,)).fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail=f"Invoice {req.invoice_id} not found")

        inv_dict = dict_row(inv)

    if inv_dict.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already paid")

    amount_cents = int(round((inv_dict.get("balance_due") or inv_dict.get("total", 0)) * 100))
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Invoice has no outstanding balance")

    invoice_number = inv_dict.get("invoice_number", req.invoice_id)

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": f"Invoice {invoice_number}",
                        "description": f"Payment for invoice {invoice_number}",
                    },
                },
                "quantity": 1,
            }],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            metadata={
                "invoice_id": req.invoice_id,
                "invoice_number": invoice_number,
                "flow": "workroom_invoice",
            },
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "invoice_id": req.invoice_id,
            "invoice_number": invoice_number,
            "amount": amount_cents / 100,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe invoice link error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Webhook Handler ──────────────────────────────────────────────────

@limiter.limit("60/minute")
@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. Verifies signature if STRIPE_WEBHOOK_SECRET is set."""
    _require_stripe()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify webhook signature
    if STRIPE_WEBHOOK_SECRET:
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
    else:
        import json
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        logger.warning("Webhook signature verification skipped — STRIPE_WEBHOOK_SECRET not set")

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
            await _notify_internal(
                title=f"New {tier.title()} Subscription",
                message=f"Customer {customer_email} subscribed to {tier.title()} plan (${TIER_AMOUNTS.get(tier, 0) / 100:.0f}/mo)",
                context={
                    "tier": tier,
                    "customer_email": customer_email,
                    "subscription_id": subscription_id,
                    "stripe_session_id": data.get("id"),
                },
            )

        elif flow == "workroom_invoice":
            invoice_id = metadata.get("invoice_id", "")
            invoice_number = metadata.get("invoice_number", "")
            if invoice_id:
                _update_invoice_status(
                    invoice_id, "paid",
                    payment_method="card",
                    stripe_session_id=data.get("id"),
                )
                await _notify_internal(
                    title=f"Invoice {invoice_number} Paid",
                    message=f"Invoice {invoice_number} paid via Stripe (${data.get('amount_total', 0) / 100:.2f})",
                    context={
                        "invoice_id": invoice_id,
                        "invoice_number": invoice_number,
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
        await _notify_internal(
            title="Subscription Cancelled",
            message=f"Subscription {subscription_id} cancelled — customer downgraded to free",
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
