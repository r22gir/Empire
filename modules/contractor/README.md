# ContractorForge

> Contractor and vendor relationship management.

## Status: Dev

## Overview
Manages relationships with contractors and vendors. Tracks contacts, work history, and availability.

## Backend
- **Router:** `backend/app/routers/contacts.py`
- **Prefix:** `/contacts`
- **Types:** client, contractor, vendor, other

### Key Endpoints
- `GET /contacts` — List contacts
- `POST /contacts` — Create contact
- `GET /contacts/{id}` — Get contact detail
- `PATCH /contacts/{id}` — Update contact
- `DELETE /contacts/{id}` — Delete contact

## Frontend
- **Screen:** `app/components/screens/EcosystemProductPage.tsx` (generic)
- **Color:** #d97706 (amber)

## Roadmap
- Contractor scheduling and availability
- Work history and ratings
- Payment tracking per contractor
