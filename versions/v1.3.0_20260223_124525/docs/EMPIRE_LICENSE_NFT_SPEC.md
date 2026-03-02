# Empire License NFT Specification

---

## Core Concept

**All licenses are NFTs** regardless of payment method.

| Payment Method | Result |
|----------------|--------|
| Fiat (Stripe / PayPal) — full price | NFT minted to wallet |
| Crypto (SOL, BNB, …) — 15% off | NFT minted to wallet |
| EMPIRE Token — 20% off | NFT minted to wallet |

License = NFT ownership = software access.

---

## Benefits of NFT Licensing

| Benefit | Description |
|---------|-------------|
| **Transferable** | Sell your license on the secondary market |
| **Business Sale** | Transfer the NFT when selling your business |
| **Verifiable** | On-chain proof — no fake keys |
| **Upgradeable** | Burn current NFT + pay the tier difference = mint higher-tier NFT |
| **Royalties** | 5% of every resale goes to the EmpireBox treasury |

---

## License Tiers & Pricing

| Tier | Fiat Price | Crypto Price | EMPIRE Price |
|------|------------|--------------|--------------|
| Solo | $79 / mo | $67 / mo (15% off) | $63 / mo (20% off) |
| Pro | $249 / mo | $212 / mo | $199 / mo |
| Enterprise | $599 / mo | $509 / mo | $479 / mo |
| Founder (Lifetime) | $2,500 | $2,125 | $2,000 |

---

## NFT Metadata Structure

```json
{
  "name": "Empire Pro License #4521",
  "symbol": "EMPIRE-LIC",
  "attributes": [
    { "trait_type": "Tier",           "value": "Pro" },
    { "trait_type": "Products",       "value": "MarketForge, LuxeForge, LeadForge..." },
    { "trait_type": "Billing",        "value": "Annual" },
    { "trait_type": "Issue Date",     "value": "2026-02-19" },
    { "trait_type": "Expiry",         "value": "2027-02-19" },
    { "trait_type": "Transfer Count", "value": 0 }
  ],
  "properties": {
    "royalty_basis_points": 500
  }
}
```

---

## License Verification Flow

```typescript
async function checkLicense(walletAddress: string): Promise<LicenseStatus> {
  // 1. Query Solana for Empire License NFT in the wallet
  const nfts = await fetchNFTsForWallet(walletAddress, { symbol: 'EMPIRE-LIC' });
  if (nfts.length === 0) return { active: false };

  // 2. Determine tier from metadata attributes
  const tier = nfts[0].attributes.find(a => a.trait_type === 'Tier')?.value;

  // 3. Check expiry
  const expiry = nfts[0].attributes.find(a => a.trait_type === 'Expiry')?.value;
  const active = new Date(expiry) > new Date();

  // 4. Return access level
  return { active, tier, expiry };
}
```

---

## Wallet Onboarding for Non-Crypto Users

1. **Connect existing wallet** — Phantom, Solflare, or any Solana-compatible wallet
2. **Create Empire Wallet** — custodial wallet managed by EmpireBox (no crypto knowledge needed)
3. **Email claim** — NFT held in escrow until the user claims it by connecting a wallet

---

## Secondary Market

- [Magic Eden](https://magiceden.io) and [Tensor](https://tensor.trade) for Solana NFTs
- Direct wallet-to-wallet transfer
- EmpireBox official resale marketplace
- **5% royalty** on all resales (enforced on-chain)

---

## Special Editions

| Edition | Eligibility | Perks |
|---------|-------------|-------|
| **Standard** | Normal purchase | Standard benefits |
| **Founder** | First 1,000 licenses | Gold border art, periodic airdrops |
| **OG** | First 100 licenses | Platinum art, lifetime discounts |
| **Partner** | Top referrers | Unique art, revenue share |

---

_See also: [CRYPTO_PAYMENTS_SPEC.md](./CRYPTO_PAYMENTS_SPEC.md), [EMPIRE_TOKEN_SPEC.md](./EMPIRE_TOKEN_SPEC.md)_
