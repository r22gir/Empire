# Empire Workroom

> Core upholstery/sewing business management — quotes, jobs, finance, inventory, customers.

## Status: Active

## Overview
Empire Workroom is the primary business unit. Manages the full lifecycle: customer intake → quote → job → invoice → delivery. Includes AI-powered photo analysis for project estimation.

## Backend
- **Routers:** `quotes.py`, `jobs.py`, `finance.py`, `inventory.py`, `contacts.py`, `vision.py`
- **Prefixes:** `/api/v1/quotes`, `/api/v1/jobs`, `/api/v1/finance`, `/api/v1/inventory`

### Key Endpoints
- `POST /api/v1/quotes` — Create quote
- `POST /api/v1/quotes/{id}/pdf` — Generate quote PDF
- `GET /api/v1/jobs` — List production jobs
- `GET /api/v1/finance/dashboard` — Revenue/expense overview
- `POST /api/v1/vision/analyze` — AI photo analysis (window measurement, mockups)
- `GET /api/v1/inventory` — Materials inventory

## Frontend
- **Screen:** `app/components/screens/WorkroomPage.tsx`
- **Tabs:** Dashboard (KPIs), Quotes, Jobs, Finance, Customers, Photos
- **Shared:** `QuickQuoteBuilder.tsx`, `PhotoAnalysisPanel.tsx`, `FinanceDashboard.tsx`, `JobBoard.tsx`
- **Default Tab:** `dashboard`

## Storage
- Quotes: JSON files in `backend/data/quotes/`
- Images: `~/data/generated/`
