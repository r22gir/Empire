from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.database import get_db
from app.schemas.crypto_payment import (
    CryptoPaymentCreate,
    CryptoPaymentConfirm,
    CryptoPaymentResponse,
    CryptoLedgerEntry,
)
from app.services.crypto_payment_service import CryptoPaymentService

router = APIRouter()


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


@router.get("/order/{order_id}", response_model=List[CryptoPaymentResponse])
async def get_payments_for_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    """List all crypto payments associated with a specific order."""
    return CryptoPaymentService.get_payments_for_order(db, order_id)


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
