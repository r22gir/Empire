# Tokens & Costs

> AI token usage tracking and cost analytics.

## Status: Active

## Overview
Tracks AI API usage, token consumption, and costs across all models (xAI Grok, Claude, Ollama, Groq). Provides daily/weekly breakdowns and budget management.

## Backend
- **Router:** `backend/app/routers/costs.py`
- **Prefix:** `/api/v1`

### Key Endpoints
- `GET /api/v1/costs/overview` — Full dashboard (days param 1-365)
- `GET /api/v1/costs/today` — Today's summary
- `GET /api/v1/costs/daily` — Daily breakdown
- `GET /api/v1/costs/weekly` — Weekly breakdown
- `GET /api/v1/costs/by-model` — Cost per AI model
- Budget management endpoints

## Frontend
- **Screen:** `app/components/business/costs/CostTracker.tsx`
- **Color:** #b8960c (gold)
- **Default Tab:** `costs`
