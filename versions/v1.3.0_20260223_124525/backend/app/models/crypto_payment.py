from sqlalchemy import Column, String, Numeric, BigInteger, DateTime, SmallInteger
from app.database import Base
from datetime import datetime
import uuid


class CryptoPayment(Base):
    __tablename__ = "crypto_payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, nullable=False, index=True)  # references orders/preorders
    chain = Column(String(20), nullable=False)   # solana | bnb | cardano | ethereum
    token = Column(String(20), nullable=False)   # SOL | USDC | EMPIRE | BNB | ...
    wallet_address = Column(String(100), nullable=False)  # per-order derived address
    expected_amount = Column(Numeric(30, 9), nullable=False)
    received_amount = Column(Numeric(30, 9), nullable=True)
    tx_hash = Column(String(200), nullable=True)
    # pending | confirming | confirmed | expired | refunded
    status = Column(String(20), nullable=False, default="pending")
    discount_pct = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)


class CryptoLedger(Base):
    __tablename__ = "crypto_ledger"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String, nullable=False, index=True)  # references crypto_payments.id
    chain = Column(String(20), nullable=False)
    token = Column(String(20), nullable=False)
    direction = Column(String(4), nullable=False)  # in | out
    amount = Column(Numeric(30, 9), nullable=False)
    usd_value = Column(Numeric(14, 2), nullable=True)
    tx_hash = Column(String(200), nullable=False)
    block_number = Column(BigInteger, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
