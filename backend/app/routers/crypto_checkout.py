"""
Empire Crypto Checkout — Lightweight crypto payment option for workroom invoices.

Provides wallet addresses + live crypto prices so customers can pay invoices
with BTC, ETH, SOL, USDT, or USDC at a 10% discount. Owner verifies on-chain
manually — no automated blockchain monitoring.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import time
import logging
import httpx

from app.db.database import get_db, dict_row
from app.middleware.rate_limiter import limiter

logger = logging.getLogger("empire.crypto_checkout")

router = APIRouter(prefix="/crypto-checkout", tags=["crypto-checkout"])

# ── Wallet addresses from env ────────────────────────────────────────

WALLETS = {
    "btc":        {"env": "CRYPTO_BTC_ADDRESS",         "label": "Bitcoin (BTC)",       "network": "Bitcoin"},
    "eth":        {"env": "CRYPTO_ETH_ADDRESS",         "label": "Ethereum (ETH)",      "network": "Ethereum (ERC-20)"},
    "sol":        {"env": "CRYPTO_SOL_ADDRESS",         "label": "Solana (SOL)",        "network": "Solana"},
    "usdt_trc20": {"env": "CRYPTO_USDT_TRC20_ADDRESS",  "label": "USDT (TRC-20)",      "network": "Tron (TRC-20)"},
    "usdt_erc20": {"env": "CRYPTO_USDT_ERC20_ADDRESS",  "label": "USDT (ERC-20)",      "network": "Ethereum (ERC-20)"},
}

CRYPTO_DISCOUNT = 0.10  # 10% discount for crypto payments

# CoinGecko IDs mapped to our wallet keys for price lookup
COINGECKO_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
}

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# Internal API base for notifications
API_BASE = f"http://localhost:{os.getenv('API_PORT', '8000')}/api/v1"

# ── Simple price cache (module-level) ────────────────────────────────

_price_cache: dict = {}
_price_cache_ts: float = 0.0
CACHE_TTL_SECONDS = 60


async def _fetch_crypto_prices() -> dict:
    """Fetch live USD prices from CoinGecko, cached for 60 seconds."""
    global _price_cache, _price_cache_ts

    now = time.time()
    if _price_cache and (now - _price_cache_ts) < CACHE_TTL_SECONDS:
        return _price_cache

    ids = ",".join(COINGECKO_IDS.values())
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(COINGECKO_URL, params={
                "ids": ids,
                "vs_currencies": "usd",
            })
            resp.raise_for_status()
            data = resp.json()

        # Map back to our keys: {"btc": 65000.0, "eth": 3400.0, "sol": 180.0}
        prices = {}
        for key, cg_id in COINGECKO_IDS.items():
            if cg_id in data and "usd" in data[cg_id]:
                prices[key] = float(data[cg_id]["usd"])

        _price_cache = prices
        _price_cache_ts = now
        logger.info(f"CoinGecko prices refreshed: {prices}")
        return prices

    except Exception as e:
        logger.error(f"CoinGecko fetch failed: {e}")
        # Return stale cache if available, otherwise empty
        if _price_cache:
            logger.warning("Returning stale price cache")
            return _price_cache
        return {}


# ── Helpers ──────────────────────────────────────────────────────────

def _get_invoice(invoice_id: str) -> dict:
    """Fetch an invoice from the DB or raise 404."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
        return dict_row(row)


async def _notify_internal(title: str, message: str, context: dict = None):
    """Send an internal notification (same pattern as payments.py)."""
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


# ── Schemas ──────────────────────────────────────────────────────────

class CryptoNotifyRequest(BaseModel):
    """Customer confirms they sent a crypto payment."""
    coin: str                          # btc, eth, sol, usdt_trc20, usdc_eth
    tx_hash: Optional[str] = None      # optional transaction hash
    sender_address: Optional[str] = None
    amount_crypto: Optional[float] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None


# ── GET /crypto-checkout/{invoice_id} ────────────────────────────────

@limiter.limit("30/minute")
@router.get("/{invoice_id}")
async def crypto_checkout_details(request: Request, invoice_id: str):
    """
    Return invoice details, wallet addresses, and live crypto prices
    for the customer-facing crypto checkout page.
    """
    inv = _get_invoice(invoice_id)

    if inv.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already paid")

    balance_due = float(inv.get("balance_due") or inv.get("total", 0))
    if balance_due <= 0:
        raise HTTPException(status_code=400, detail="Invoice has no outstanding balance")

    discounted_total = round(balance_due * (1 - CRYPTO_DISCOUNT), 2)

    # Fetch live prices
    prices = await _fetch_crypto_prices()

    # Build per-coin payment options
    coins = []
    for key, wallet_info in WALLETS.items():
        address = os.getenv(wallet_info["env"], "")
        if not address:
            continue  # skip unconfigured wallets

        coin_entry = {
            "coin": key,
            "label": wallet_info["label"],
            "network": wallet_info["network"],
            "address": address,
            "usd_amount": discounted_total,
        }

        # For volatile coins, compute the crypto amount from live price
        if key in prices and prices[key] > 0:
            crypto_amount = round(discounted_total / prices[key], 8)
            coin_entry["crypto_amount"] = crypto_amount
            coin_entry["price_usd"] = prices[key]
        elif key in ("usdt_trc20", "usdt_erc20"):
            # Stablecoins: 1:1 with USD
            coin_entry["crypto_amount"] = discounted_total
            coin_entry["price_usd"] = 1.0

        coins.append(coin_entry)

    return {
        "invoice_id": inv.get("id"),
        "invoice_number": inv.get("invoice_number", invoice_id),
        "customer_name": inv.get("customer_name", ""),
        "original_total": balance_due,
        "crypto_discount_pct": int(CRYPTO_DISCOUNT * 100),
        "discounted_total": discounted_total,
        "coins": coins,
        "prices_fetched_at": datetime.utcfromtimestamp(_price_cache_ts).isoformat() + "Z" if _price_cache_ts else None,
        "note": f"Pay {int(CRYPTO_DISCOUNT * 100)}% less when you pay with crypto. Send the exact amount to one of the addresses below, then click confirm.",
    }


# ── POST /crypto-checkout/{invoice_id}/notify ────────────────────────

@limiter.limit("10/minute")
@router.post("/{invoice_id}/notify")
async def crypto_payment_notify(request: Request, invoice_id: str, req: CryptoNotifyRequest):
    """
    Customer clicks 'I've sent the payment'. Records a pending note on the
    invoice for manual verification — does NOT mark as paid.
    """
    inv = _get_invoice(invoice_id)

    if inv.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already paid")

    coin_label = WALLETS.get(req.coin, {}).get("label", req.coin)
    invoice_number = inv.get("invoice_number", invoice_id)
    balance_due = float(inv.get("balance_due") or inv.get("total", 0))
    discounted_total = round(balance_due * (1 - CRYPTO_DISCOUNT), 2)

    # Build note text
    note_parts = [
        f"[CRYPTO PENDING] Customer reports {coin_label} payment of ${discounted_total:.2f} (10% crypto discount applied).",
    ]
    if req.tx_hash:
        note_parts.append(f"TX hash: {req.tx_hash}")
    if req.sender_address:
        note_parts.append(f"Sender: {req.sender_address}")
    if req.amount_crypto:
        note_parts.append(f"Amount: {req.amount_crypto} {req.coin.upper()}")
    if req.customer_name:
        note_parts.append(f"Name: {req.customer_name}")
    if req.customer_email:
        note_parts.append(f"Email: {req.customer_email}")

    note_text = " | ".join(note_parts)

    # Append note to invoice
    try:
        with get_db() as conn:
            existing_notes = inv.get("notes", "") or ""
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            updated_notes = f"{existing_notes}\n[{timestamp}] {note_text}".strip()

            conn.execute(
                "UPDATE invoices SET notes = ?, updated_at = datetime('now') WHERE id = ?",
                (updated_notes, invoice_id)
            )
    except Exception as e:
        logger.error(f"Failed to update invoice notes for {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to record payment notification")

    # Send internal notification for owner review
    await _notify_internal(
        title=f"Crypto Payment Pending — Invoice {invoice_number}",
        message=f"Customer reports {coin_label} payment of ${discounted_total:.2f} for invoice {invoice_number}. Verify on-chain before marking paid.",
        context={
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "coin": req.coin,
            "tx_hash": req.tx_hash,
            "sender_address": req.sender_address,
            "amount_crypto": req.amount_crypto,
            "discounted_total": discounted_total,
            "customer_name": req.customer_name,
            "customer_email": req.customer_email,
        },
    )

    return {
        "status": "pending_verification",
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "coin": req.coin,
        "discounted_total": discounted_total,
        "message": "Payment notification recorded. The business owner will verify the transaction and update your invoice.",
    }
