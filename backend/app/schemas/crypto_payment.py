from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Supported chains and tokens
# ---------------------------------------------------------------------------
SUPPORTED_CHAINS = {"solana", "bnb", "cardano", "ethereum", "bitcoin"}
SUPPORTED_TOKENS = {"SOL", "USDC", "EMPIRE", "BNB", "USDT", "BUSD", "ADA", "ETH", "BTC"}

# Discount percentages per payment method
DISCOUNT_CRYPTO = 15   # 15% off for any crypto payment
DISCOUNT_EMPIRE = 20   # 20% off when paying with EMPIRE token


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CryptoPaymentCreate(BaseModel):
    order_id: str = Field(..., description="Order or pre-order ID this payment belongs to")
    chain: str = Field(..., description="Blockchain: solana | bnb | cardano | ethereum")
    token: str = Field(..., description="Token symbol: SOL | USDC | EMPIRE | BNB | ...")
    expected_amount: Decimal = Field(..., description="Amount of token expected from buyer", gt=0)


class CryptoPaymentConfirm(BaseModel):
    tx_hash: str = Field(..., description="On-chain transaction hash")
    received_amount: Decimal = Field(..., description="Actual amount received on-chain", gt=0)
    block_number: Optional[int] = Field(None, description="Block number of the confirming tx")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CryptoPaymentResponse(BaseModel):
    id: str
    order_id: str
    chain: str
    token: str
    wallet_address: str
    expected_amount: Decimal
    received_amount: Optional[Decimal]
    tx_hash: Optional[str]
    status: str
    discount_pct: int
    created_at: datetime
    confirmed_at: Optional[datetime]
    expires_at: datetime

    class Config:
        from_attributes = True


class CryptoLedgerEntry(BaseModel):
    id: str
    payment_id: str
    chain: str
    token: str
    direction: str
    amount: Decimal
    usd_value: Optional[Decimal]
    tx_hash: str
    block_number: Optional[int]
    recorded_at: datetime

    class Config:
        from_attributes = True
