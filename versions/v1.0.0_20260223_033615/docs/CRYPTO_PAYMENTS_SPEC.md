# Crypto Payments Specification

_Expands Issue #23 — Crypto Payments_

---

## Overview

Crypto payment is **optional** and incentivised with a discount. Every payment method (fiat or crypto) results in an NFT license being minted to the buyer's wallet.

| Payment Method | Discount | NFT Minted |
|----------------|----------|------------|
| Fiat (Stripe / PayPal) | 0% | ✅ Yes |
| Crypto (SOL, BNB, ADA, ETH …) | 15% off | ✅ Yes |
| EMPIRE Token ($EMPIRE) | 20% off | ✅ Yes |

---

## Supported Chains & Tokens

| Chain | Tokens | Priority |
|-------|--------|----------|
| Solana | SOL, USDC, EMPIRE | #1 (fits Seeker phone) |
| BNB Chain | BNB, USDT, BUSD | #2 (EVM compatible) |
| Cardano | ADA | #3 (Phase 2) |
| Ethereum | ETH, USDC | #4 (high fees but popular) |

---

## Per-Client Wallet Architecture

- Each client / order receives a **unique wallet address**
- Addresses are derived via **HD wallet** from a master seed
- A **blockchain monitoring service** watches each address for incoming payments
- All transactions are written to the **transparency ledger**

---

## Technical Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│  Payment Gateway │────▶│  Blockchain     │
│   (Next.js)     │     │  (Multi-chain)   │     │  (SOL/BNB/ADA)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Backend       │◀────│  Webhook Handler │◀────│  Transaction    │
│   (FastAPI)     │     │  (Confirmation)  │     │  Confirmed      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Database Schema

### `crypto_payments`

```sql
CREATE TABLE crypto_payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id),
    chain           VARCHAR(20) NOT NULL,          -- 'solana', 'bnb', 'cardano', 'ethereum'
    token           VARCHAR(20) NOT NULL,           -- 'SOL', 'USDC', 'EMPIRE', 'BNB', ...
    wallet_address  VARCHAR(100) NOT NULL,          -- per-order derived address
    expected_amount NUMERIC(30, 9) NOT NULL,
    received_amount NUMERIC(30, 9),
    tx_hash         VARCHAR(200),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending | confirming | confirmed | expired | refunded
    discount_pct    SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ NOT NULL
);
```

### `crypto_ledger`

```sql
CREATE TABLE crypto_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id      UUID NOT NULL REFERENCES crypto_payments(id),
    chain           VARCHAR(20) NOT NULL,
    token           VARCHAR(20) NOT NULL,
    direction       VARCHAR(4) NOT NULL,   -- 'in' | 'out'
    amount          NUMERIC(30, 9) NOT NULL,
    usd_value       NUMERIC(14, 2),
    tx_hash         VARCHAR(200) NOT NULL,
    block_number    BIGINT,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Integration Points

| Product | Use Case |
|---------|----------|
| **MarketForge** | Crypto checkout with escrow for marketplace transactions |
| **EmpireBox** | Subscription payments in SOL / USDC / EMPIRE |
| **ContractorForge / LuxeForge** | Client invoice payments in crypto |
| **License purchases** | NFT minting on payment confirmation |

---

## Implementation Phases

| Phase | Timeline | Scope |
|-------|----------|-------|
| 1 | 60 days | EMPIRE token creation, NFT smart contract, Solana Pay (USDC only), Empire Wallet (custodial) |
| 2 | 90 days | SOL + EMPIRE payments, DEX liquidity pool (Raydium), secondary market (Magic Eden), LeadForge MVP |
| 3 | 120 days | BNB Chain, Cardano (ADA), crypto escrow for MarketForge, LeadForge full release |
| 4 | 180 days | CEX listing exploration, staking rewards, governance voting, Partner/referral NFT editions |

---

_See also: [EMPIRE_TOKEN_SPEC.md](./EMPIRE_TOKEN_SPEC.md), [EMPIRE_LICENSE_NFT_SPEC.md](./EMPIRE_LICENSE_NFT_SPEC.md)_
