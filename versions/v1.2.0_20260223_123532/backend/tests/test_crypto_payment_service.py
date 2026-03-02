"""
Unit tests for CryptoPaymentService.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch
import uuid

from app.models.crypto_payment import CryptoPayment, CryptoLedger
from app.schemas.crypto_payment import (
    CryptoPaymentCreate,
    CryptoPaymentConfirm,
    DISCOUNT_CRYPTO,
    DISCOUNT_EMPIRE,
)
from app.services.crypto_payment_service import (
    CryptoPaymentService,
    _derive_wallet_address,
    _discount_for_token,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db():
    """Return a MagicMock that mimics a SQLAlchemy Session."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
    return db


def _make_payment(**kwargs) -> CryptoPayment:
    defaults = dict(
        id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        chain="solana",
        token="USDC",
        wallet_address="SOL-abc123",
        expected_amount=Decimal("50.00"),
        received_amount=None,
        tx_hash=None,
        status="pending",
        discount_pct=DISCOUNT_CRYPTO,
        created_at=datetime.utcnow(),
        confirmed_at=None,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    defaults.update(kwargs)
    p = CryptoPayment()
    for k, v in defaults.items():
        setattr(p, k, v)
    return p


# ---------------------------------------------------------------------------
# _derive_wallet_address
# ---------------------------------------------------------------------------

class TestDeriveWalletAddress:
    def test_deterministic(self):
        a1 = _derive_wallet_address("solana", "order-1")
        a2 = _derive_wallet_address("solana", "order-1")
        assert a1 == a2

    def test_different_orders_give_different_addresses(self):
        a1 = _derive_wallet_address("solana", "order-1")
        a2 = _derive_wallet_address("solana", "order-2")
        assert a1 != a2

    def test_different_chains_give_different_addresses(self):
        a1 = _derive_wallet_address("solana", "order-1")
        a2 = _derive_wallet_address("bnb", "order-1")
        assert a1 != a2

    def test_contains_chain_prefix(self):
        addr = _derive_wallet_address("solana", "order-1")
        assert addr.startswith("SOL-")

    def test_bnb_prefix(self):
        addr = _derive_wallet_address("bnb", "order-1")
        assert addr.startswith("BNB-")


# ---------------------------------------------------------------------------
# _discount_for_token
# ---------------------------------------------------------------------------

class TestDiscountForToken:
    def test_empire_gets_20_pct(self):
        assert _discount_for_token("EMPIRE") == DISCOUNT_EMPIRE

    def test_empire_case_insensitive(self):
        assert _discount_for_token("empire") == DISCOUNT_EMPIRE

    def test_usdc_gets_standard_crypto_discount(self):
        assert _discount_for_token("USDC") == DISCOUNT_CRYPTO

    def test_sol_gets_standard_crypto_discount(self):
        assert _discount_for_token("SOL") == DISCOUNT_CRYPTO

    def test_bnb_gets_standard_crypto_discount(self):
        assert _discount_for_token("BNB") == DISCOUNT_CRYPTO


# ---------------------------------------------------------------------------
# CryptoPaymentService.create_payment
# ---------------------------------------------------------------------------

class TestCreatePayment:
    def test_create_payment_solana_usdc(self):
        db = _make_db()
        data = CryptoPaymentCreate(
            order_id="order-123",
            chain="solana",
            token="USDC",
            expected_amount=Decimal("100.00"),
        )
        payment = CryptoPaymentService.create_payment(db, data)

        db.add.assert_called_once()
        db.commit.assert_called()
        assert payment.chain == "solana"
        assert payment.token == "USDC"
        assert payment.discount_pct == DISCOUNT_CRYPTO
        assert payment.status == "pending"
        assert payment.wallet_address.startswith("SOL-")

    def test_create_payment_empire_token_discount(self):
        db = _make_db()
        data = CryptoPaymentCreate(
            order_id="order-456",
            chain="solana",
            token="EMPIRE",
            expected_amount=Decimal("50.00"),
        )
        payment = CryptoPaymentService.create_payment(db, data)
        assert payment.discount_pct == DISCOUNT_EMPIRE

    def test_create_payment_invalid_chain_raises(self):
        db = _make_db()
        data = CryptoPaymentCreate(
            order_id="order-789",
            chain="bitcoin",
            token="BTC",
            expected_amount=Decimal("0.01"),
        )
        with pytest.raises(ValueError, match="Unsupported chain"):
            CryptoPaymentService.create_payment(db, data)

    def test_create_payment_invalid_token_raises(self):
        db = _make_db()
        data = CryptoPaymentCreate(
            order_id="order-789",
            chain="solana",
            token="DOGE",
            expected_amount=Decimal("100.00"),
        )
        with pytest.raises(ValueError, match="Unsupported token"):
            CryptoPaymentService.create_payment(db, data)

    def test_chain_is_lowercased(self):
        db = _make_db()
        data = CryptoPaymentCreate(
            order_id="order-111",
            chain="Solana",
            token="SOL",
            expected_amount=Decimal("1.00"),
        )
        payment = CryptoPaymentService.create_payment(db, data)
        assert payment.chain == "solana"

    def test_token_is_uppercased(self):
        db = _make_db()
        data = CryptoPaymentCreate(
            order_id="order-222",
            chain="solana",
            token="usdc",
            expected_amount=Decimal("10.00"),
        )
        payment = CryptoPaymentService.create_payment(db, data)
        assert payment.token == "USDC"


# ---------------------------------------------------------------------------
# CryptoPaymentService.confirm_payment
# ---------------------------------------------------------------------------

class TestConfirmPayment:
    def test_confirm_pending_payment(self):
        payment = _make_payment(status="pending")
        db = _make_db()
        db.query.return_value.filter.return_value.first.return_value = payment

        data = CryptoPaymentConfirm(
            tx_hash="abc123txhash",
            received_amount=Decimal("50.00"),
            block_number=12345678,
        )
        result = CryptoPaymentService.confirm_payment(db, payment.id, data)

        assert result.status == "confirmed"
        assert result.tx_hash == "abc123txhash"
        assert result.received_amount == Decimal("50.00")
        assert result.confirmed_at is not None
        # Ledger entry should have been added
        db.add.assert_called_once()

    def test_confirm_already_confirmed_raises(self):
        payment = _make_payment(status="confirmed")
        db = _make_db()
        db.query.return_value.filter.return_value.first.return_value = payment

        data = CryptoPaymentConfirm(tx_hash="abc", received_amount=Decimal("50"))
        with pytest.raises(ValueError, match="Cannot confirm payment"):
            CryptoPaymentService.confirm_payment(db, payment.id, data)

    def test_confirm_expired_payment_raises(self):
        payment = _make_payment(
            status="pending",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )
        db = _make_db()
        db.query.return_value.filter.return_value.first.return_value = payment

        data = CryptoPaymentConfirm(tx_hash="abc", received_amount=Decimal("50"))
        with pytest.raises(ValueError, match="expired"):
            CryptoPaymentService.confirm_payment(db, payment.id, data)
        assert payment.status == "expired"

    def test_confirm_not_found_raises(self):
        db = _make_db()
        db.query.return_value.filter.return_value.first.return_value = None

        data = CryptoPaymentConfirm(tx_hash="abc", received_amount=Decimal("50"))
        with pytest.raises(ValueError, match="not found"):
            CryptoPaymentService.confirm_payment(db, "nonexistent-id", data)


# ---------------------------------------------------------------------------
# CryptoPaymentService.expire_stale_payments
# ---------------------------------------------------------------------------

class TestExpireStalePayments:
    def test_expire_stale_marks_as_expired(self):
        p1 = _make_payment(status="pending", expires_at=datetime.utcnow() - timedelta(minutes=5))
        p2 = _make_payment(status="confirming", expires_at=datetime.utcnow() - timedelta(minutes=1))
        db = _make_db()
        db.query.return_value.filter.return_value.all.return_value = [p1, p2]

        count = CryptoPaymentService.expire_stale_payments(db)
        assert count == 2
        assert p1.status == "expired"
        assert p2.status == "expired"

    def test_expire_stale_returns_zero_when_none(self):
        db = _make_db()
        db.query.return_value.filter.return_value.all.return_value = []

        count = CryptoPaymentService.expire_stale_payments(db)
        assert count == 0


# ---------------------------------------------------------------------------
# CryptoPaymentService.get_payments_for_order
# ---------------------------------------------------------------------------

class TestGetPaymentsForOrder:
    def test_returns_all_payments_for_order(self):
        order_id = str(uuid.uuid4())
        payments = [_make_payment(order_id=order_id) for _ in range(3)]
        db = _make_db()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = payments

        result = CryptoPaymentService.get_payments_for_order(db, order_id)
        assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
