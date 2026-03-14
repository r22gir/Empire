"""
Crypto Payment Service — Phase 1 implementation.

Supports:
- Bitcoin (BTC)
- Ethereum (ETH, USDC)
- Solana Pay (USDC, SOL) — priority
- BNB Chain (BNB, USDT, BUSD)
- Cardano (ADA) — Phase 2 placeholder

Each order/invoice receives a unique per-order wallet address derived
deterministically from the master seed + order_id using HMAC-SHA256.
In a production deployment the master seed lives in an HSM / secrets manager;
here it falls back to an env variable (CRYPTO_MASTER_SEED) for development.
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.crypto_payment import CryptoPayment, CryptoLedger
from app.schemas.crypto_payment import (
    CryptoPaymentCreate,
    CryptoPaymentConfirm,
    SUPPORTED_CHAINS,
    SUPPORTED_TOKENS,
    DISCOUNT_CRYPTO,
    DISCOUNT_EMPIRE,
)

logger = logging.getLogger(__name__)

# Payment window before a pending payment is considered expired
PAYMENT_EXPIRY_MINUTES = int(os.getenv("CRYPTO_PAYMENT_EXPIRY_MINUTES", "60"))

# Payment status constants
STATUS_PENDING = "pending"
STATUS_CONFIRMING = "confirming"
STATUS_CONFIRMED = "confirmed"
STATUS_EXPIRED = "expired"
STATUS_REFUNDED = "refunded"

# Master seed used to derive per-order wallet addresses deterministically.
# Must be kept secret; load from environment / secrets manager in production.
_env_seed = os.getenv("CRYPTO_MASTER_SEED")
if _env_seed:
    _MASTER_SEED = _env_seed
else:
    # Generate a random seed for this process run; log a warning so operators
    # know they must set CRYPTO_MASTER_SEED to persist addresses across restarts.
    _MASTER_SEED = secrets.token_hex(32)
    logger.warning(
        "CRYPTO_MASTER_SEED environment variable is not set. "
        "A temporary random seed has been generated for this process. "
        "Wallet addresses will NOT be reproducible across restarts. "
        "Set CRYPTO_MASTER_SEED in production."
    )


def _derive_wallet_address(chain: str, order_id: str) -> str:
    """
    Derive a deterministic wallet address for a given chain + order combination.

    This is a *placeholder* implementation that produces a hex-encoded
    HMAC-SHA256 digest of (chain || order_id) keyed on the master seed.
    In production this should be replaced with proper HD-wallet derivation
    (e.g. BIP-32/44 for EVM chains, Solana's BIP-44 m/44'/501'/index').
    """
    key = _MASTER_SEED.encode()
    msg = f"{chain}:{order_id}".encode()
    digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
    # Truncate to a realistic address length and add a chain prefix so it is
    # easy to identify during testing.
    return f"{chain[:3].upper()}-{digest[:40]}"


def _discount_for_token(token: str) -> int:
    """Return the discount percentage applicable for the given token."""
    if token.upper() == "EMPIRE":
        return DISCOUNT_EMPIRE
    return DISCOUNT_CRYPTO


class CryptoPaymentService:
    """Business logic for crypto payment lifecycle management."""

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @staticmethod
    def create_payment(db: Session, data: CryptoPaymentCreate) -> CryptoPayment:
        """
        Create a new pending crypto payment for an order.

        Validates chain/token, derives a unique wallet address, and
        calculates the applicable discount.
        """
        chain = data.chain.lower()
        token = data.token.upper()

        if chain not in SUPPORTED_CHAINS:
            raise ValueError(
                f"Unsupported chain '{chain}'. Supported: {sorted(SUPPORTED_CHAINS)}"
            )
        if token not in SUPPORTED_TOKENS:
            raise ValueError(
                f"Unsupported token '{token}'. Supported: {sorted(SUPPORTED_TOKENS)}"
            )

        wallet_address = _derive_wallet_address(chain, data.order_id)
        discount_pct = _discount_for_token(token)
        now = datetime.utcnow()

        payment = CryptoPayment(
            order_id=data.order_id,
            chain=chain,
            token=token,
            wallet_address=wallet_address,
            expected_amount=data.expected_amount,
            discount_pct=discount_pct,
            status=STATUS_PENDING,
            created_at=now,
            expires_at=now + timedelta(minutes=PAYMENT_EXPIRY_MINUTES),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    # ------------------------------------------------------------------
    # Confirmation (called by webhook handler once tx is seen on-chain)
    # ------------------------------------------------------------------

    @staticmethod
    def confirm_payment(
        db: Session,
        payment_id: str,
        data: CryptoPaymentConfirm,
        usd_value: Optional[Decimal] = None,
    ) -> CryptoPayment:
        """
        Mark a pending/confirming payment as confirmed and record a ledger entry.

        Raises ValueError if the payment is not in a confirmable state or has
        expired.
        """
        payment = db.query(CryptoPayment).filter(CryptoPayment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment '{payment_id}' not found")

        if payment.status not in (STATUS_PENDING, STATUS_CONFIRMING):
            raise ValueError(
                f"Cannot confirm payment with status '{payment.status}'"
            )

        now = datetime.utcnow()
        if now > payment.expires_at:
            payment.status = STATUS_EXPIRED
            db.commit()
            raise ValueError("Payment window has expired")

        payment.status = STATUS_CONFIRMED
        payment.tx_hash = data.tx_hash
        payment.received_amount = data.received_amount
        payment.confirmed_at = now
        db.commit()
        db.refresh(payment)

        # Record inbound ledger entry
        ledger = CryptoLedger(
            payment_id=payment.id,
            chain=payment.chain,
            token=payment.token,
            direction="in",
            amount=data.received_amount,
            usd_value=usd_value,
            tx_hash=data.tx_hash,
            block_number=data.block_number,
        )
        db.add(ledger)
        db.commit()

        return payment

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_payment(db: Session, payment_id: str) -> Optional[CryptoPayment]:
        """Retrieve a payment by ID."""
        return db.query(CryptoPayment).filter(CryptoPayment.id == payment_id).first()

    @staticmethod
    def get_payments_for_order(db: Session, order_id: str) -> List[CryptoPayment]:
        """Retrieve all payments associated with a given order."""
        return (
            db.query(CryptoPayment)
            .filter(CryptoPayment.order_id == order_id)
            .order_by(CryptoPayment.created_at.desc())
            .all()
        )

    @staticmethod
    def expire_stale_payments(db: Session) -> int:
        """
        Mark all pending/confirming payments whose expiry has passed as expired.
        Returns the number of payments expired.
        """
        now = datetime.utcnow()
        stale = (
            db.query(CryptoPayment)
            .filter(
                CryptoPayment.status.in_([STATUS_PENDING, STATUS_CONFIRMING]),
                CryptoPayment.expires_at < now,
            )
            .all()
        )
        for p in stale:
            p.status = STATUS_EXPIRED
        db.commit()
        return len(stale)

    @staticmethod
    def get_ledger_entries(db: Session, payment_id: str) -> List[CryptoLedger]:
        """Return all ledger entries for a payment."""
        return (
            db.query(CryptoLedger)
            .filter(CryptoLedger.payment_id == payment_id)
            .order_by(CryptoLedger.recorded_at)
            .all()
        )
