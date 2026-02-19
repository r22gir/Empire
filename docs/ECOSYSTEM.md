# EmpireBox Ecosystem

An overview of all products, modules, and infrastructure components in the EmpireBox platform.

---

## Core Platform

| Component | Description |
|-----------|-------------|
| **EmpireBox** | Central SaaS platform — subscriptions, billing, user management |
| **ForgeCRM** | CRM integrated across all Forge products |
| **Empire Wallet** | Custodial Solana wallet for non-crypto users |

---

## Forge Products

| Product | Description |
|---------|-------------|
| **MarketForge** | B2B / B2C marketplace with escrow |
| **ContractorForge** | Project and contract management for contractors |
| **LuxeForge** | High-end service business management (interior design, architects, etc.) |
| **LeadForge** | AI-powered lead generation — embedded in ContractorForge & LuxeForge (see [LEADFORGE_SPEC.md](./LEADFORGE_SPEC.md)) |

---

## Tokenomics & Licensing

| Component | Description |
|-----------|-------------|
| **EMPIRE Token ($EMPIRE)** | Solana SPL utility + governance token — 1B supply (see [EMPIRE_TOKEN_SPEC.md](./EMPIRE_TOKEN_SPEC.md)) |
| **NFT License System** | All licenses are Solana NFTs regardless of payment method (see [EMPIRE_LICENSE_NFT_SPEC.md](./EMPIRE_LICENSE_NFT_SPEC.md)) |

---

## Payments Infrastructure

| Component | Description |
|-----------|-------------|
| **Stripe / PayPal** | Standard fiat checkout |
| **Multi-chain Crypto Payments** | Solana, BNB Chain, Cardano, Ethereum — optional 15% discount (see [CRYPTO_PAYMENTS_SPEC.md](./CRYPTO_PAYMENTS_SPEC.md)) |
| **EMPIRE Token Payments** | Optional 20% discount when paying with $EMPIRE |
| **Crypto Transparency Ledger** | On-chain record of all crypto transactions |

---

## Hardware

| Component | Description |
|-----------|-------------|
| **Solana Seeker Phone** | Priority hardware integration for Solana Pay |
| **Hardware Bundles** | See [HARDWARE_BUNDLES.md](./HARDWARE_BUNDLES.md) |

---

## Related Documentation

- [CRYPTO_PAYMENTS_SPEC.md](./CRYPTO_PAYMENTS_SPEC.md) — Multi-chain payment architecture & DB schema
- [EMPIRE_TOKEN_SPEC.md](./EMPIRE_TOKEN_SPEC.md) — Token details, distribution, DEX strategy
- [EMPIRE_LICENSE_NFT_SPEC.md](./EMPIRE_LICENSE_NFT_SPEC.md) — NFT licensing tiers, metadata, secondary market
- [LEADFORGE_SPEC.md](./LEADFORGE_SPEC.md) — Lead generation module specification
- [SOLANA_PARTNERSHIP.md](./SOLANA_PARTNERSHIP.md) — Solana ecosystem partnerships
- [STRIPE_COMPLIANCE_CHECKLIST.md](./STRIPE_COMPLIANCE_CHECKLIST.md) — Stripe compliance requirements
- [LEGAL_COMPLIANCE_AUDIT.md](./LEGAL_COMPLIANCE_AUDIT.md) — Legal & compliance overview
