# AGENTS.md — EmpireBox Developer Guide

## Project Overview
- **Type**: Multi-product business platform (FastAPI backend + Next.js frontend)
- **Ports**: Backend 8000, Frontend 3005, PostgreSQL 5432
- **Database**: SQLite (`backend/data/empire.db`) + PostgreSQL for prod
- **Entry**: `backend/app/main.py` + `empire-command-center/app/page.tsx`

## Verified Commands

```bash
# Frontend (empire-command-center/)
npm run dev     # Dev server at localhost:3005
npm run build   # Production build
npm run start   # Production server

# Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker (all services)
docker-compose -f docker-compose.yml up -d
```

## Architecture

### Backend (`backend/app/main.py`)
- FastAPI app with ~70 routers loaded via `load_router()` helper
- Routers: MAX AI, files, chats, license, shipping, auth, listings, relist, messages, marketplaces, webhooks, ai, supportforge, crypto, economic, quotes, finance, craftforge, socialforge, avatar, recovery, dev, costs, accuracy, maintenance, inventory, jobs_unified, intake_auth, amp, llcfactory, apostapp, construction, storefront, notes_extraction, pattern_templates, custom_shapes, drawings, fabrics, photos, vision, openclaw_bridge, openclaw_tasks, docker_manager, system_monitor, ollama_manager, notifications, desks, tasks, contacts, leadforge, onboarding, smart_analyzer

### Background Services (run on primary worker only)
- Telegram Bot (`app.services.max.telegram_bot`)
- Desk Scheduler (`app.services.max.desks.desk_scheduler`)
- MAX Scheduler (daily briefs, task checks, reports)
- MAX Monitor (overdue tasks, inbox, system health)
- OpenClaw Worker (polls task queue every 30s)
- Task Auto-Worker (executes todo tasks every 30s)

### Frontend (`empire-command-center/`)
- Next.js 16 with App Router
- No `src/` directory
- Main component: `app/page.tsx` → `CommandCenter`
- Layout: `app/layout.tsx` with I18nWrapper

## Environment
- Config: `backend/.env` (not committed)
- Example: `backend/.env.example`
- Required env vars: `XAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_GEMINI_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `FOUNDER_PIN`

## Key Files for Development
| Purpose | File |
|---------|------|
| Backend entry | `backend/app/main.py` |
| Router loader | `backend/app/main.py:54` (load_router) |
| DB connection | `backend/app/db/database.py` |
| MAX AI service | `backend/app/routers/max/` |
| Frontend entry | `empire-command-center/app/page.tsx` |
| API client | `empire-command-center/app/lib/api.ts` |
| Types | `empire-command-center/app/lib/types.ts` |

## Testing
- Backend: `pytest` (in requirements.txt)
- No test command in package.json

## Gotchas
- Multi-worker mode: background services only run on primary worker (file lock at `/tmp/empire_primary_worker.lock`)
- CORS origins from `CORS_ORIGINS` env (default: `*`)
- SQLite used for dev, PostgreSQL for prod (docker-compose)
- Frontend port 3005 stated in CLAUDE.md but not in package.json (run via `npm run dev` then access on 3005)
