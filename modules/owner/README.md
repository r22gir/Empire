# Owner's Desk

> Central command hub for the Empire ecosystem founder.

## Status: Active

## Overview
The Owner's Desk is the primary interface for managing the entire Empire ecosystem. It provides AI chat (MAX), desk management, inbox, research, documents, video calls, and Telegram integration.

## Backend
- **Router:** `backend/app/routers/max/router.py`
- **Prefix:** `/api/v1` and root `/`
- **Endpoints:** 39 (AI chat streaming, desk management, task execution, tool integration)
- **AI Routing:** xAI Grok → Claude → Ollama (priority fallback)

### Key Endpoints
- `POST /max/chat` — AI chat with SSE streaming
- `GET /max/ai-desks` — List all AI desk agents
- `POST /max/ai-desks/tasks` — Fire task to desk agent
- `GET /max/ai-desks/{desk}/tasks` — Get desk task history
- `POST /api/v1/memory/add` — Add to MAX memory
- `GET /api/v1/system/stats` — System health

## Frontend
- **Screen:** `app/components/screens/ChatScreen.tsx`
- **Additional:** `DesksScreen.tsx`, `InboxScreen.tsx`, `ResearchScreen.tsx`, `DocumentScreen.tsx`, `VideoCallScreen.tsx`, `TelegramScreen.tsx`
- **Default Tab:** `chat`

## AI Desk Agents (12)
forge, sales, support, marketing, finance, clients, contractors, it, website, legal, lab, market

## Dependencies
- xAI Grok API, Claude API, Ollama (port 11434)
- Telegram Bot API
- DeskScheduler (daily 8AM-10:30AM)
