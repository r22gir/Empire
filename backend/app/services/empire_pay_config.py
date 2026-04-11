"""
Shared EmpirePay constants and helpers.

Canonical source for:
- Supported chains and tokens
- Chain ↔ token mapping
- Discount percentages
- Payment status constants
- Shared Pydantic schemas used across EmpirePay systems

Adopted as canonical from crypto_payments.py / crypto_payment_service.py.
"""

from typing import Dict, Set

SUPPORTED_CHAINS: Set[str] = {"solana", "bnb", "cardano", "ethereum", "bitcoin"}
SUPPORTED_TOKENS: Set[str] = {"SOL", "USDC", "EMPIRE", "BNB", "USDT", "BUSD", "ADA", "ETH", "BTC"}

DISCOUNT_CRYPTO = 15
DISCOUNT_EMPIRE = 20
DISCOUNT_LEGACY = 10

CHAIN_FOR_TOKEN: Dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "USDC": "ethereum",
    "BNB": "bnb",
    "USDT": "bnb",
    "BUSD": "bnb",
    "ADA": "cardano",
    "EMPIRE": "solana",
}

TOKEN_FOR_CHAIN: Dict[str, str] = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "bnb": "BNB",
    "cardano": "ADA",
}

CHAIN_DISPLAY_NAMES: Dict[str, str] = {
    "bitcoin": "Bitcoin",
    "ethereum": "Ethereum",
    "solana": "Solana",
    "bnb": "BNB Chain",
    "cardano": "Cardano",
}

LEGACY_COIN_KEYS: Dict[str, Dict[str, str]] = {
    "btc":        {"label": "Bitcoin (BTC)",       "network": "Bitcoin",        "env": "CRYPTO_BTC_ADDRESS"},
    "eth":        {"label": "Ethereum (ETH)",      "network": "Ethereum (ERC-20)", "env": "CRYPTO_ETH_ADDRESS"},
    "sol":        {"label": "Solana (SOL)",        "network": "Solana",        "env": "CRYPTO_SOL_ADDRESS"},
    "usdt_trc20": {"label": "USDT (TRC-20)",      "network": "Tron (TRC-20)", "env": "CRYPTO_USDT_TRC20_ADDRESS"},
    "usdt_erc20": {"label": "USDT (ERC-20)",      "network": "Ethereum (ERC-20)", "env": "CRYPTO_USDT_ERC20_ADDRESS"},
}

LEGACY_COIN_TO_TOKEN: Dict[str, str] = {
    "btc": "BTC",
    "eth": "ETH",
    "sol": "SOL",
    "usdt_trc20": "USDT",
    "usdt_erc20": "USDT",
}

LEGACY_COIN_TO_CHAIN: Dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "usdt_trc20": "bnb",
    "usdt_erc20": "ethereum",
}

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_CONFIRMING = "confirming"
PAYMENT_STATUS_CONFIRMED = "confirmed"
PAYMENT_STATUS_EXPIRED = "expired"
PAYMENT_STATUS_REFUNDED = "refunded"

PAYMENT_STATUSES = {
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_CONFIRMING,
    PAYMENT_STATUS_CONFIRMED,
    PAYMENT_STATUS_EXPIRED,
    PAYMENT_STATUS_REFUNDED,
}


def discount_for_token(token: str) -> int:
    """Return the discount percentage for a given token."""
    if token.upper() == "EMPIRE":
        return DISCOUNT_EMPIRE
    return DISCOUNT_CRYPTO


def is_chain_supported(chain: str) -> bool:
    return chain.lower() in SUPPORTED_CHAINS


def is_token_supported(token: str) -> bool:
    return token.upper() in SUPPORTED_TOKENS


def resolve_chain_for_token(token: str, explicit_chain: str = None) -> str:
    """Resolve chain for a token, with optional override."""
    if explicit_chain:
        return explicit_chain.lower()
    return CHAIN_FOR_TOKEN.get(token.upper(), "").lower()


def legacy_coin_to_canonical(coin_key: str) -> tuple[str, str]:
    """Convert legacy coin key (btc, eth, etc.) to (chain, token)."""
    token = LEGACY_COIN_TO_TOKEN.get(coin_key, coin_key.upper())
    chain = LEGACY_COIN_TO_CHAIN.get(coin_key, "ethereum")
    return chain, token
