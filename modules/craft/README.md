# WoodCraft (CraftForge)

> CNC routing, 3D printing, and woodworking business unit.

## Status: Active

## Overview
WoodCraft manages CNC/3D print design-to-production workflows. Tracks designs, production jobs, material inventory, and generates quotes with templates.

## Backend
- **Router:** `backend/app/routers/craftforge.py`
- **Prefix:** `/api/v1/craftforge`
- **Storage:** JSON files in `backend/data/craftforge/`

### Key Endpoints
- `POST /api/v1/craftforge/designs` — Create design
- `GET /api/v1/craftforge/designs` — List designs
- `POST /api/v1/craftforge/jobs` — Create production job
- `GET /api/v1/craftforge/jobs` — List jobs
- `POST /api/v1/craftforge/inventory` — Add material
- `GET /api/v1/craftforge/inventory` — Material stock

## Frontend
- **Screen:** `app/components/screens/CraftForgePage.tsx`
- **Tabs:** Dashboard, Designs, Jobs, Inventory, Customers
- **Shared:** `QuickQuoteBuilder.tsx`, `FinanceDashboard.tsx`, `JobBoard.tsx`
- **Default Tab:** `dashboard`
