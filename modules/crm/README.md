# ForgeCRM

> Customer relationship management — contacts, pipeline, and deal tracking.

## Status: Dev

## Overview
Centralized CRM for managing customer relationships across all Empire business units. Includes pipeline tracking and quote import capability.

## Backend
- **Router:** `backend/app/routers/customer_mgmt.py`
- **Prefix:** `/api/v1/crm`

### Key Endpoints
- `GET /api/v1/crm/customers` — List customers
- `POST /api/v1/crm/customers` — Create customer
- `GET /api/v1/crm/pipeline` — Deal pipeline

## Frontend
- **Components:** `app/components/business/crm/CustomerList.tsx`, `CustomerDetail.tsx`
- **Screen:** `QuoteReviewScreen.tsx` (shared with workroom/craft/luxe)
- **Color:** #b8960c (gold)
