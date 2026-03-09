# ShipForge

> Shipping management — rates, labels, and tracking.

## Status: Dev

## Overview
Handles shipping logistics: rate comparison, label purchasing, and shipment tracking.

## Backend
- **Router:** `backend/app/routers/shipping.py`
- **Prefix:** `/shipping`

### Key Endpoints
- `POST /shipping/rates` — Get shipping rates
- `POST /shipping/purchase-label` — Purchase shipping label
- `GET /shipping/tracking/{id}` — Track shipment

## Frontend
- **Screen:** `app/components/business/shipping/ShippingPage.tsx`
- **Features:** Tracking, rate comparison, shipping history
- **Color:** #2563eb (blue)
