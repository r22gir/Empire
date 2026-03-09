# SupportForge

> Customer support ticket system with AI-powered response suggestions and knowledge base.

## Status: Dev

## Overview
Full helpdesk system with ticket management, customer profiles, knowledge base articles, and AI-assisted response generation.

## Backend
- **Routers:** 4 files
  - `supportforge_tickets.py` — Ticket CRUD + messaging
  - `supportforge_customers.py` — Customer profiles + context
  - `supportforge_kb.py` — Knowledge base articles + search
  - `supportforge_ai.py` — AI response suggestion + ticket classification
- **Prefixes:** `/api/v1/tickets`, `/api/v1/customers`, `/api/v1/kb`, `/api/v1/ai`
- **Total Endpoints:** 24+

### Key Endpoints
- `POST /api/v1/tickets` — Create ticket
- `POST /api/v1/tickets/{id}/messages` — Add message to ticket
- `GET /api/v1/customers/{id}/context` — Customer context for AI
- `POST /api/v1/kb/search` — Search knowledge base
- `POST /api/v1/ai/suggest-response` — AI response suggestion
- `POST /api/v1/ai/classify-ticket` — Auto-classify ticket

## Frontend
- **Screen:** `app/components/business/support/TicketsPage.tsx`
- **Statuses:** open, in_progress, waiting, resolved, closed
- **Color:** #7c3aed (purple)
