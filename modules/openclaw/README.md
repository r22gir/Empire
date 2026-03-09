# OpenClaw

> Local AI assistant powered by Ollama — private, on-device AI for Empire operations.

## Status: Active

## Overview
OpenClaw runs local LLMs via Ollama for private AI processing. Integrated into the Command Center as an alternative AI chat interface. Standalone app on port 7878.

## Backend
- **Router:** `backend/app/routers/ollama_manager.py`
- **Prefix:** `/api/v1`
- **Ollama:** Port 11434

### Key Endpoints
- `GET /api/v1/ollama/models` — List installed models
- `POST /api/v1/ollama/pull` — Pull new model
- `DELETE /api/v1/ollama/{model}` — Delete model

## Frontend
- **Command Center:** `ChatScreen.tsx` (OpenClaw mode)
- **Standalone:** `~/Empire/openclaw/` (port 7878)
- **Default Tab:** `chat`

## Notes
- Requires manual start: `cd ~/Empire/openclaw && npm run dev`
- Ollama must be running on port 11434
- Used as fallback in AI routing chain: xAI Grok → Claude → Ollama
