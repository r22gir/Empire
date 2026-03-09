# EmpirePay

> Payment processing — crypto, invoicing, and financial transactions.

## Status: Dev

## Overview
Unified payment system supporting crypto payments, invoice management, and transaction ledger.

## Backend
- **Routers:** `crypto_payments.py`, `finance.py`
- **Prefixes:** `/api/v1/crypto-payments`, `/api/v1/finance`

### Key Endpoints
- `POST /api/v1/crypto-payments` — Create crypto payment
- `POST /api/v1/crypto-payments/confirm` — Confirm payment
- `GET /api/v1/crypto-payments/ledger` — Ledger entries
- `POST /api/v1/finance/invoices` — Create invoice
- `POST /api/v1/finance/invoices/{id}/payment` — Record payment

## Frontend
- **Screen:** `app/components/screens/EcosystemProductPage.tsx` (generic)
- **Color:** #16a34a (green)

## Roadmap
- Multi-currency support
- Payment gateway integrations
- Automated invoicing from quotes
