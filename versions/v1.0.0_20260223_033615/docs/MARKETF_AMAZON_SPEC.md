# MarketF Amazon SP-API Integration — Feature Specification

## Overview

This document specifies the Amazon Seller Platform (SP-API) integration for MarketF, enabling the platform to function as an **aggregator/facilitator** where connected partner stores have their products listed on Amazon through MarketF's centralized Professional Seller account.

## Business Model

| Role | Responsibility |
|------|---------------|
| **MarketF** | Seller of record, Amazon account holder, compliance, fulfillment coordination, customer service, returns |
| **Partner Stores** | Provide product data, inventory counts, brand authorizations |
| **Amazon** | Marketplace, customer traffic, payment processing |

- Partner stores connect to MarketF and submit product data via the Partner Dashboard
- MarketF validates data, lists products under its Professional Seller account
- MarketF handles all Amazon-side obligations (fulfillment, support, returns, compliance)
- Partner stores receive payouts after MarketF's service fees are deducted

## Technical Architecture

### Amazon SP-API Integration Module

Location: `market_forge_app/lib/amazon/`

| File | Purpose |
|------|---------|
| `sp_api_client.py` | Core SP-API HTTP client with OAuth 2.0, rate limiting, audit logging |
| `product_validator.py` | Amazon listing data validation schema |
| `compliance.py` | Kill switch, self-identification headers, compliance logging |

### Frontend Dashboard

Location: `marketf_web/src/components/amazon/`

| Component | Purpose |
|-----------|---------|
| `AmazonDashboard.tsx` | Main Amazon integration dashboard |
| `ListingStatus.tsx` | Amazon listing status display (active/pending/suppressed/error) |
| `ProductUpload.tsx` | Partner product upload form with real-time validation feedback |

## SP-API Setup Requirements

### Amazon Account Prerequisites

1. **Professional Seller Plan** — $39.99/month (required for SP-API bulk operations)
2. **Private SP-API App Registration** — Free for private use (self-authorize only)
   - Register in Seller Central → Apps & Services → Develop Apps
   - Select "Private" (not listed in the marketplace)
   - No $1,400/year developer subscription required for private apps
3. **Brand Registry** — Required if listing branded products (provides brand authorization)

### SP-API OAuth Flow (Private App)

```
1. Register app in Seller Central (get Client ID + Client Secret)
2. Self-authorize: generate Refresh Token via Seller Central OAuth
3. Use Refresh Token to obtain Access Tokens (1-hour TTL)
4. Include Access Token in all SP-API request headers
```

## Product Data Requirements

All fields must be validated before pushing to Amazon SP-API.

| Field | Requirement | Validation Rule |
|-------|-------------|-----------------|
| **UPC/EAN/GTIN** | Real, unique, GS1-verified | Numeric, 12–14 digits, Luhn checksum |
| **Title** | ≤200 chars, no spam/special chars | Regex: no `!$?_{}^`, strip HTML |
| **Bullet Points** | 5 max, ≤300 chars each | Array length ≤5, each ≤300 chars |
| **Description** | ≤1,000 chars, HTML allowed | Strip disallowed tags, ≤1,000 chars |
| **Images** | 7+ images required | Count ≥7, main image = white bg check |
| **Main Image** | White bg (RGB 255,255,255), ≥1,000px longest side, 85–100% product fill, no watermarks | Image analysis validation |
| **Price** | Competitive, decimal format | Positive float, ≤2 decimal places |
| **Inventory** | Real-time sync required | Non-negative integer |
| **Weight** | Exact (for FBA) | Positive float with unit |
| **Dimensions** | Exact L×W×H (for FBA) | Three positive floats with unit |
| **Category** | Valid Amazon category ID | Whitelist of valid category IDs |
| **Brand** | Authorized if Brand Registry | Brand authorization document required |
| **Manufacturer** | Required | Non-empty string |

## Compliance Requirements (Amazon Agent Policy — March 4, 2026)

All automation must comply with Amazon's Agent Policy effective March 4, 2026:

### 1. Self-Identification
Every SP-API call must include a self-identification header:
```
User-Agent: MarketF-EmpireBox/1.0 (Language=Python; Platform=Linux)
x-amz-user-agent: MarketF-EmpireBox/1.0
```

### 2. Kill Switch
- Admin endpoint: `POST /admin/amazon/kill-switch`
- Environment flag: `AMAZON_KILL_SWITCH_ENABLED=true`
- When enabled: immediately halts ALL Amazon API operations
- Must be operable without code deployment (env var or database flag)

### 3. No Scraping
- Only official SP-API endpoints may be used
- No browser automation against Seller Central
- No scraping of Amazon product pages

### 4. Audit Logging
Every SP-API call must be logged with:
- Timestamp (UTC)
- Endpoint called
- Request payload (sanitized — no credentials)
- HTTP response code
- Response summary

### 5. Rate Limiting
Respect Amazon's throttling rules per endpoint:
- Default burst: 1 request/second
- Use exponential backoff on 429 responses
- Implement token bucket or leaky bucket algorithm

## Database Schema

```sql
-- Amazon listings tracking
CREATE TABLE amazon_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    amazon_asin VARCHAR(10),
    amazon_sku VARCHAR(40) NOT NULL,
    listing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- values: pending, active, suppressed, error
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_amazon_listings_store_id ON amazon_listings(store_id);
CREATE INDEX idx_amazon_listings_status ON amazon_listings(listing_status);

-- SP-API compliance audit log
CREATE TABLE amazon_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES amazon_listings(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
        -- values: create, update, delete, price_change, inventory_sync
    request_payload JSONB,
    response_code INTEGER,
    response_body JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_amazon_sync_log_listing_id ON amazon_sync_log(listing_id);
CREATE INDEX idx_amazon_sync_log_created_at ON amazon_sync_log(created_at);
```

## Environment Configuration

Add to `.env` / `.env.example`:

```env
# Amazon SP-API
AMAZON_SELLER_ID=
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
AMAZON_SP_API_CLIENT_ID=
AMAZON_SP_API_CLIENT_SECRET=
AMAZON_SP_API_REFRESH_TOKEN=
AMAZON_KILL_SWITCH_ENABLED=false
AMAZON_SELF_ID_STRING=Automated by MarketF/EmpireBox v1.0
```

## Partner Dashboard Features

- **Product Upload Interface** — Form with real-time validation feedback for all required fields
- **Inventory Sync Status** — Real-time display of inventory sync state per SKU
- **Listing Status** — Per-product status: active / pending / suppressed / error with error details
- **Sales Reporting** — Revenue, units sold, payout tracking
- **Brand Authorization Upload** — Document upload for brand-authorized products

## Implementation Phases

| Phase | Description | Prerequisite |
|-------|-------------|--------------|
| **Phase 0 (Now)** | Documentation + code scaffolding | None |
| **Phase 1** | Amazon Professional Seller account setup | $39.99/mo account |
| **Phase 2** | SP-API app registration + OAuth | Phase 1 |
| **Phase 3** | Product validator + compliance module | Phase 2 |
| **Phase 4** | Live listing push + inventory sync | Phase 3 |
| **Phase 5** | Partner dashboard activation | Phase 4 |

## Implementation Notes

- **Current Status**: Phase 0 — scaffolding and documentation only
- Amazon Professional Seller account must be created before any live API calls
- FBA vs FBM strategy to be decided in Phase 1 (FBA = Amazon handles shipping/storage; FBM = MarketF handles)
- All credentials stored in environment variables only — never commit to source code
- Consider FBA for scalability; FBM for cost control at low volume

## References

- [Amazon SP-API Documentation](https://developer-docs.amazon.com/sp-api/)
- [Amazon Agent Policy (March 4, 2026)](https://sellercentral.amazon.com/help/hub/reference/external/G200386250)
- `conversation_summary.md` in repo root — original source conversation
- `docs/AMAZON_COMPLIANCE_CHECKLIST.md` — operational compliance checklist
