# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo Layout

```
~/Empire/
├── backend/           # FastAPI backend (Python 3.12), port 8000
├── founder_dashboard/ # Founder command center (Next.js 14), port 3009
├── empire-app/        # Unified app with full modules (Next.js 14), port 3000
├── workroomforge/     # Quote builder + AI photo analysis (Next.js), port 3001
├── luxeforge_web/     # Designer portal (Next.js 15), port 3002
├── openclaw/          # Skills-augmented local AI (Ollama wrapper), port 7878
├── homepage/          # Static HTML navigation hub, port 8080
├── uploads/           # Uploaded files (images/, documents/, code/, other/)
├── max/               # MAX persistent memory (memory.md)
├── logs/YYYY-MM-DD/   # Session logs
└── venv/              # Shared Python virtualenv
```

## Development Commands

### Start Everything
```bash
~/Empire/launch-all.sh
```

### Individual Services
```bash
# Backend API
cd ~/Empire/backend && source ~/Empire/venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Founder Dashboard (port 3009)
cd ~/Empire/founder_dashboard && npm run dev

# Empire App / Unified Dashboard (port 3000)
cd ~/Empire/empire-app && npm run dev

# WorkroomForge (port 3001)
cd ~/Empire/workroomforge && npm run dev

# LuxeForge (port 3002)
cd ~/Empire/luxeforge_web && npm run dev

# Static homepage (port 8080)
cd ~/Empire/homepage && python3 -m http.server 8080
```

### Build / Production
```bash
npm run build   # run inside any Next.js app directory
npm start       # serves on the app's assigned port
```

## Architecture

### Backend (`backend/`)
- Entry point: `app/main.py` — dynamically loads all routers with `load_router()` (failures are non-fatal)
- All primary routes: `/api/v1/*`
- Key route groups: `/api/v1/max/*` (AI chat + desks + tasks), `/api/v1/chats/*` (chat history), `/api/v1/files/*` (file management), `/api/v1/system/*` (CPU/RAM/disk), `/api/v1/ollama/*` (local model management), `/api/v1/notifications/*`
- AI routing (`app/services/max/ai_router.py`): priority is xAI Grok → Claude → Ollama. Provider selected by env vars (`XAI_API_KEY`, `ANTHROPIC_API_KEY`)
- MAX system prompt (`app/services/max/system_prompt.py`): loads `~/Empire/max/memory.md` (persistent memory) and today's session log at runtime
- Guardrails (`app/services/max/guardrails.py`): input validation runs before every chat call

### Founder Dashboard (`founder_dashboard/`)
- Entry: `src/app/page.tsx` → `ChatLayout` component
- Three-panel layout: `ConversationSidebar` | `ChatArea` | `SystemSidebar`
- Three core hooks:
  - `useChat` — message state, SSE streaming from `/max/chat/stream`, abort control
  - `useChatHistory` — conversation list CRUD via `/chats/*`
  - `useSystemData` — desks, models, files, tasks, reminders (localStorage), AI notifications, service health polling
- API base: `src/lib/api.ts` exports `API_URL` (`NEXT_PUBLIC_API_URL` or `http://localhost:8000/api/v1`)
- All types defined in `src/lib/types.ts`

### Streaming Protocol
Chat responses use SSE (Server-Sent Events). Each `data:` line is JSON with shape `{ type: "text"|"done"|"error", content?: string, model_used?: string }`.

### Design System
- Color palette defined in `globals.css` as CSS vars: `--bg-void: #05050d`, `--gold: #D4AF37`, plus `--purple`, `--fuchsia`, `--cyan`
- Tailwind amber-500/amber-400 for interactive/accent elements
- Fonts: Outfit (UI text) + JetBrains Mono (code) loaded from Google Fonts in `globals.css`
- All icons: `lucide-react` (consistent across every app)
- `TopNav` component (`src/components/TopNav.tsx`) is shared across dashboard pages — pass `currentApp` and `currentPort` props

### Empire-App (`empire-app/`)
The unified all-in-one dashboard. Contains full modules at `/inventory`, `/finance`, `/customers`, `/workroom`, `/creations`, `/tasks`, `/shipping`, `/max`, `/settings`. Distinct from `founder_dashboard` which is the MAX AI-focused interface.

## Critical Hardware Warnings
- **DO NOT run `sensors-detect`** — crashes this machine (Super I/O scan incompatible with AMD Ryzen 7 5825U on kernel 6.17)
- **DO NOT use `pkill -f` with broad patterns** — caused a system crash on Feb 24, 2026
- Temperature monitoring: use `sensors` command (k10temp module is loaded)

## Environment Variables (Backend)
| Variable | Purpose |
|---|---|
| `XAI_API_KEY` | xAI Grok API key (makes Grok the primary model) |
| `ANTHROPIC_API_KEY` | Claude API key |
| `CORS_ORIGINS` | Comma-separated allowed origins (default `*`) |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL override |

## Key Ports
| Service | Port |
|---|---|
| Backend API | 8000 |
| Homepage | 8080 |
| Empire App (unified) | 3000 |
| WorkroomForge | 3001 |
| LuxeForge | 3002 |
| Founder Dashboard | 3009 |
| OpenClaw AI | 7878 |
| Ollama | 11434 |
