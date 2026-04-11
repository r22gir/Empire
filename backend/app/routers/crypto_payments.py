# STATUS: FUNCTIONAL — Real DB-backed payment creation, invoice integration,
# ledger tracking, and confirmation flow. Requires CRYPTO_MASTER_SEED env var.
# Pending: automated blockchain monitoring / webhook handler to call /confirm
# endpoints (currently relies on manual or external trigger).

"""
Empire Crypto Payments Router — order-based and invoice-based crypto payment flows.

Supports BTC, ETH, SOL, USDC, and other tokens across multiple chains.
Invoice endpoints bridge the crypto payment system (SQLAlchemy) with the
finance invoice system (raw SQLite / empire.db).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import logging
import os
import httpx

from app.database import get_db
from app.schemas.crypto_payment import (
    CryptoPaymentCreate,
    CryptoPaymentConfirm,
    CryptoPaymentResponse,
    CryptoLedgerEntry,
    SUPPORTED_CHAINS,
    SUPPORTED_TOKENS,
)
from app.services.crypto_payment_service import CryptoPaymentService

logger = logging.getLogger("empire.crypto_payments")

router = APIRouter()

# Internal API base for notifications
API_BASE = f"http://localhost:{os.getenv('API_PORT', '8000')}/api/v1"

# Check if crypto is minimally configured (master seed present)
_CRYPTO_CONFIGURED = bool(os.getenv("CRYPTO_MASTER_SEED"))


# ── Helpers ──────────────────────────────────────────────────────────

def _require_crypto():
    """Raise 503 if crypto payments are not configured."""
    if not _CRYPTO_CONFIGURED:
        raise HTTPException(
            status_code=503,
            detail="Crypto payments not configured — set CRYPTO_MASTER_SEED in .env",
        )


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


def _get_invoice_from_finance_db(invoice_id: str) -> dict:
    """Look up an invoice from the finance SQLite DB (empire.db)."""
    from app.db.database import get_db as get_finance_db, dict_row
    with get_finance_db() as conn:
        row = conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
        if not row:
            return None
        return dict_row(row)


def _record_invoice_crypto_payment(invoice_id: str, amount: float, chain: str,
                                    token: str, tx_hash: str, crypto_payment_id: str):
    """
    Record a payment against an invoice in the finance DB and recalculate totals.
    Mirrors the logic in finance.py record_payment and payments.py _update_invoice_status.
    """
    from app.db.database import get_db as get_finance_db, dict_row
    from datetime import date, datetime

    with get_finance_db() as conn:
        inv = conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
        if not inv:
            logger.warning(f"Invoice {invoice_id} not found for crypto payment update")
            return False

        inv_dict = dict_row(inv)

        # Insert payment record
        conn.execute(
            """INSERT INTO payments
               (id, invoice_id, customer_id, amount, method, reference, notes, payment_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
            (
                invoice_id,
                inv_dict.get("customer_id"),
                amount,
                f"crypto-{chain}-{token}",
                tx_hash,
                f"Crypto payment ({token} on {chain}) — ref: {crypto_payment_id}",
                date.today().isoformat(),
            )
        )

        # Recalculate invoice totals
        subtotal = inv_dict.get("subtotal", 0) or 0
        tax_rate = inv_dict.get("tax_rate", 0) or 0
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)

        paid_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments WHERE invoice_id = ?",
            (invoice_id,)
        ).fetchone()
        amount_paid = paid_row["total_paid"]
        balance_due = round(total - amount_paid, 2)

        status = "paid" if balance_due <= 0 and total > 0 else (
            "partial" if amount_paid > 0 else inv_dict.get("status", "sent")
        )

        paid_at = None
        if status == "paid":
            paid_at = datetime.now().isoformat()

        conn.execute(
            """UPDATE invoices SET tax_amount = ?, total = ?, amount_paid = ?,
               balance_due = ?, status = ?, paid_at = COALESCE(paid_at, ?),
               updated_at = datetime('now') WHERE id = ?""",
            (tax_amount, total, amount_paid, max(balance_due, 0), status, paid_at, invoice_id)
        )

        # Update customer total_revenue if linked
        if inv_dict.get("customer_id"):
            conn.execute(
                """UPDATE customers SET total_revenue = (
                     SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?
                   ), updated_at = datetime('now') WHERE id = ?""",
                (inv_dict["customer_id"], inv_dict["customer_id"])
            )

        return True


# Chain shorthand mapping for convenience
CHAIN_FOR_TOKEN = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "USDC": "ethereum",  # default; can be overridden with explicit chain param
    "BNB": "bnb",
    "USDT": "bnb",
    "BUSD": "bnb",
    "ADA": "cardano",
    "EMPIRE": "solana",
}


# ── Existing order-based endpoints ───────────────────────────────────

@router.post("/", response_model=CryptoPaymentResponse, status_code=201)
async def create_crypto_payment(
    data: CryptoPaymentCreate,
    db: Session = Depends(get_db),
):
    """
    Initiate a new crypto payment for an order.

    Returns a unique wallet address the buyer should send funds to, along with
    the expected amount and payment expiry timestamp.  A 15% discount is applied
    for any crypto payment; 20% when paying with the EMPIRE token.
    """
    try:
        payment = CryptoPaymentService.create_payment(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return payment


@router.get("/chains")
async def list_supported_chains():
    """Return all supported chains and tokens."""
    return {
        "chains": sorted(SUPPORTED_CHAINS),
        "tokens": sorted(SUPPORTED_TOKENS),
        "chain_token_map": CHAIN_FOR_TOKEN,
    }


@router.get("/", response_model=List[CryptoPaymentResponse])
async def list_crypto_payments(
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    status: Optional[str] = Query(None, description="Filter by status: pending, confirming, confirmed, expired, refunded"),
    db: Session = Depends(get_db),
):
    """
    List recent crypto payments across all orders/invoices.
    Used by the admin EmpirePay dashboard to show payment activity.
    Requires CRYPTO_MASTER_SEED to be configured.
    """
    _require_crypto()

    query = db.query(CryptoPayment)
    if status:
        query = query.filter(CryptoPayment.status == status)
    return query.order_by(CryptoPayment.created_at.desc()).limit(limit).all()


@router.get("/order/{order_id}", response_model=List[CryptoPaymentResponse])
async def get_payments_for_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    """List all crypto payments associated with a specific order."""
    return CryptoPaymentService.get_payments_for_order(db, order_id)


# ── Invoice-based crypto payment endpoints ───────────────────────────

@router.post("/invoice/{invoice_id}/generate-address")
async def generate_invoice_crypto_address(
    invoice_id: str,
    token: str = Query("USDC", description="Token to pay with: BTC, ETH, SOL, USDC, etc."),
    chain: Optional[str] = Query(None, description="Blockchain (auto-detected from token if omitted)"),
    db: Session = Depends(get_db),
):
    """
    Generate (or retrieve existing) a crypto wallet address for paying a specific invoice.

    Looks up the invoice in the finance DB, creates a crypto payment record linked
    to the invoice ID, and returns the address + amount details.
    """
    _require_crypto()

    # Validate token
    token = token.upper()
    if token not in SUPPORTED_TOKENS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported token '{token}'. Supported: {sorted(SUPPORTED_TOKENS)}",
        )

    # Resolve chain
    resolved_chain = (chain or CHAIN_FOR_TOKEN.get(token, "")).lower()
    if not resolved_chain or resolved_chain not in SUPPORTED_CHAINS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported chain '{resolved_chain}'. Supported: {sorted(SUPPORTED_CHAINS)}",
        )

    # Look up invoice in finance DB
    invoice = _get_invoice_from_finance_db(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    if invoice.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already paid")
    if invoice.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Invoice is cancelled")

    amount_usd = float(invoice.get("balance_due") or invoice.get("total", 0))
    if amount_usd <= 0:
        raise HTTPException(status_code=400, detail="Invoice has no outstanding balance")

    # Check for existing pending crypto payment for this invoice + token
    from app.models.crypto_payment import CryptoPayment
    existing = (
        db.query(CryptoPayment)
        .filter(
            CryptoPayment.order_id == f"invoice:{invoice_id}",
            CryptoPayment.token == token,
            CryptoPayment.chain == resolved_chain,
            CryptoPayment.status == "pending",
        )
        .first()
    )

    if existing:
        from datetime import datetime
        # If still valid, return the existing address
        if datetime.utcnow() < existing.expires_at:
            return {
                "payment_id": existing.id,
                "invoice_id": invoice_id,
                "invoice_number": invoice.get("invoice_number"),
                "address": existing.wallet_address,
                "chain": existing.chain,
                "token": existing.token,
                "amount_usd": amount_usd,
                "amount_crypto": float(existing.expected_amount),
                "discount_pct": existing.discount_pct,
                "qr_code_url": f"/api/v1/crypto-payments/invoice/{invoice_id}/qr?payment_id={existing.id}",
                "expires_at": existing.expires_at.isoformat(),
                "status": existing.status,
            }
        else:
            # Expire the old one
            existing.status = "expired"
            db.commit()

    # Create new crypto payment linked to invoice
    # Use invoice_id as the "order_id" with a prefix to distinguish
    payment_data = CryptoPaymentCreate(
        order_id=f"invoice:{invoice_id}",
        chain=resolved_chain,
        token=token,
        expected_amount=Decimal(str(amount_usd)),  # placeholder 1:1 USD amount
    )

    try:
        payment = CryptoPaymentService.create_payment(db, payment_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "payment_id": payment.id,
        "invoice_id": invoice_id,
        "invoice_number": invoice.get("invoice_number"),
        "address": payment.wallet_address,
        "chain": payment.chain,
        "token": payment.token,
        "amount_usd": amount_usd,
        "amount_crypto": float(payment.expected_amount),
        "discount_pct": payment.discount_pct,
        "qr_code_url": f"/api/v1/crypto-payments/invoice/{invoice_id}/qr?payment_id={payment.id}",
        "expires_at": payment.expires_at.isoformat(),
        "status": payment.status,
    }


@router.get("/invoice/{invoice_id}/status")
async def get_invoice_crypto_status(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """
    Check the status of crypto payment(s) for a specific invoice.

    Returns all crypto payments associated with this invoice (pending, confirmed, expired).
    """
    # Verify invoice exists
    invoice = _get_invoice_from_finance_db(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    # Find all crypto payments for this invoice
    from app.models.crypto_payment import CryptoPayment
    payments = (
        db.query(CryptoPayment)
        .filter(CryptoPayment.order_id == f"invoice:{invoice_id}")
        .order_by(CryptoPayment.created_at.desc())
        .all()
    )

    # Auto-expire stale payments
    from datetime import datetime
    for p in payments:
        if p.status == "pending" and datetime.utcnow() > p.expires_at:
            p.status = "expired"
    db.commit()

    payment_list = []
    for p in payments:
        payment_list.append({
            "payment_id": p.id,
            "chain": p.chain,
            "token": p.token,
            "address": p.wallet_address,
            "expected_amount": float(p.expected_amount),
            "received_amount": float(p.received_amount) if p.received_amount else None,
            "tx_hash": p.tx_hash,
            "status": p.status,
            "discount_pct": p.discount_pct,
            "created_at": p.created_at.isoformat(),
            "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
            "expires_at": p.expires_at.isoformat(),
        })

    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice.get("invoice_number"),
        "invoice_status": invoice.get("status"),
        "balance_due": float(invoice.get("balance_due", 0)),
        "total": float(invoice.get("total", 0)),
        "crypto_payments": payment_list,
    }


@router.post("/invoice/{invoice_id}/confirm")
async def confirm_invoice_crypto_payment(
    invoice_id: str,
    data: CryptoPaymentConfirm,
    payment_id: str = Query(..., description="The crypto payment ID to confirm"),
    usd_value: Optional[Decimal] = Query(None, description="USD value of the received crypto"),
    db: Session = Depends(get_db),
):
    """
    Confirm a crypto payment for an invoice once the on-chain transaction is verified.

    This endpoint:
    1. Confirms the crypto payment in the crypto_payments table (SQLAlchemy)
    2. Records the payment in the finance DB (empire.db) and updates invoice status
    3. Sends an internal notification

    Intended to be called by a blockchain monitoring service or webhook handler.
    """
    _require_crypto()

    # Verify invoice exists
    invoice = _get_invoice_from_finance_db(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    # Verify the payment belongs to this invoice
    from app.models.crypto_payment import CryptoPayment
    payment = db.query(CryptoPayment).filter(CryptoPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail=f"Crypto payment {payment_id} not found")

    if payment.order_id != f"invoice:{invoice_id}":
        raise HTTPException(status_code=400, detail="Payment does not belong to this invoice")

    # Confirm the crypto payment
    try:
        confirmed = CryptoPaymentService.confirm_payment(db, payment_id, data, usd_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Calculate USD amount: use provided usd_value, or fall back to expected amount
    pay_amount = float(usd_value) if usd_value else float(
        invoice.get("balance_due") or invoice.get("total", 0)
    )

    # Record payment in finance DB and update invoice status
    success = _record_invoice_crypto_payment(
        invoice_id=invoice_id,
        amount=pay_amount,
        chain=confirmed.chain,
        token=confirmed.token,
        tx_hash=data.tx_hash,
        crypto_payment_id=confirmed.id,
    )

    if not success:
        logger.error(f"Failed to record crypto payment in finance DB for invoice {invoice_id}")

    # Send internal notification (NOT Telegram)
    invoice_number = invoice.get("invoice_number", invoice_id)
    await _notify_internal(
        title=f"Invoice {invoice_number} Crypto Payment Confirmed",
        message=(
            f"Invoice {invoice_number} received {float(data.received_amount)} {confirmed.token} "
            f"on {confirmed.chain} (tx: {data.tx_hash[:16]}...) — "
            f"USD value: ${pay_amount:.2f}"
        ),
        context={
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "payment_id": confirmed.id,
            "chain": confirmed.chain,
            "token": confirmed.token,
            "received_amount": float(data.received_amount),
            "usd_value": pay_amount,
            "tx_hash": data.tx_hash,
        },
    )

    # Re-read invoice to get updated status
    updated_invoice = _get_invoice_from_finance_db(invoice_id)

    return {
        "status": "confirmed",
        "payment_id": confirmed.id,
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "invoice_status": updated_invoice.get("status") if updated_invoice else "unknown",
        "chain": confirmed.chain,
        "token": confirmed.token,
        "received_amount": float(data.received_amount),
        "usd_value": pay_amount,
        "tx_hash": data.tx_hash,
    }


# ── Generic payment endpoints (must be AFTER /invoice/ routes) ───────

@router.get("/{payment_id}", response_model=CryptoPaymentResponse)
async def get_crypto_payment(
    payment_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve the status of a crypto payment by its ID."""
    payment = CryptoPaymentService.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/{payment_id}/confirm", response_model=CryptoPaymentResponse)
async def confirm_crypto_payment(
    payment_id: str,
    data: CryptoPaymentConfirm,
    usd_value: Optional[Decimal] = None,
    db: Session = Depends(get_db),
):
    """
    Confirm a crypto payment once the on-chain transaction is verified.

    This endpoint is intended to be called by an internal webhook handler or
    blockchain monitoring service after sufficient confirmations are observed.
    """
    try:
        payment = CryptoPaymentService.confirm_payment(db, payment_id, data, usd_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return payment


@router.get("/{payment_id}/ledger", response_model=List[CryptoLedgerEntry])
async def get_payment_ledger(
    payment_id: str,
    db: Session = Depends(get_db),
):
    """Return the transparency ledger entries for a specific payment."""
    payment = CryptoPaymentService.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return CryptoPaymentService.get_ledger_entries(db, payment_id)
