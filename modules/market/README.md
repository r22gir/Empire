# MarketForge

> Multi-marketplace e-commerce management — listings, orders, reviews, seller tools.

## Status: Dev

## Overview
MarketForge connects to external marketplaces (eBay, etc.) for multi-channel selling. Manages product listings, orders, reviews, and seller analytics.

## Backend
- **Routers:** `listings.py`, `marketplaces.py`, `marketplace/orders.py`, `marketplace/products.py`, `marketplace/reviews.py`, `marketplace/seller.py`
- **Prefixes:** `/listings`, `/marketplaces`, `/marketplace/*`

### Key Endpoints
- `POST /listings` — Create listing
- `POST /listings/{id}/publish` — Publish to marketplace
- `POST /marketplaces/{name}/connect` — Connect marketplace account
- `GET /marketplace/products` — List products (filters: category, condition, price)
- `GET /marketplace/seller/orders` — Seller order management
- `POST /marketplace/orders/{id}/review` — Leave review

## Frontend
- **Screen:** `app/components/screens/EcosystemProductPage.tsx` (generic)
- **Color:** #2563eb (blue)

## Integrations
- eBay webhooks (`POST /webhooks/ebay/notification`)
- Preorder system (`/preorders`)
