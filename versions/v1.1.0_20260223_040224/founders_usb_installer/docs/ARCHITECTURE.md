# EmpireBox Founders Unit — Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   FOUNDERS UNIT (Beelink EQR5)               │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Dashboard  │  │   OpenClaw   │  │  Control Center  │   │
│  │   :80       │  │   :7878      │  │      :8001       │   │
│  │  (nginx)    │  │  AI Agent    │  │  Fleet Manager   │   │
│  └─────────────┘  └──────┬───────┘  └──────────────────┘   │
│                           │                                   │
│  ┌────────────────────────▼─────────────────────────────┐   │
│  │                 API Gateway :8000                     │   │
│  └────────┬─────────────────────────────┬───────────────┘   │
│           │                             │                     │
│  ┌────────▼────────┐         ┌─────────▼────────┐          │
│  │   PostgreSQL    │         │      Redis        │          │
│  │     :5432       │         │      :6379        │          │
│  └─────────────────┘         └──────────────────┘          │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Ollama :11434                      │    │
│  │   llama3.1:8b  |  codellama:7b  |  nomic-embed-text │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────── Products (On-Demand) ──────────────┐  │
│  │  MarketForge:8010  ContractorForge:8020  Luxe:8030   │  │
│  │  Support:8040      LeadForge:8050        Ship:8060    │  │
│  │  ForgeCRM:8070     RelistApp:8080        Social:8090  │  │
│  │  LLCFactory:8100   ApostApp:8110         Assist:8120  │  │
│  │  EmpirePay:8130                                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────┐                                         │
│  │  Portainer:9000 │  Docker management UI                   │
│  └─────────────────┘                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                    Internet / LAN
                              │
              ┌───────────────┴──────────────┐
              │         Customer Units        │
              │   Phone home to :8001         │
              │   License validation          │
              │   Remote suspend/revoke       │
              └──────────────────────────────┘
```

## Component Descriptions

### Dashboard (Port 80)
nginx serving static HTML. Shows all service links, product grid, and quick command reference.

### OpenClaw (Port 7878)
AI Agent with multi-model support. Founders mode: full system access, no sandbox. Connects to Ollama locally and supports external providers (OpenAI, Anthropic, Google) via API keys added through the UI.

### Control Center (Port 8001)
FastAPI service for fleet management of customer units. Handles:
- Unit registration and heartbeats
- License generation and validation
- Remote actions (suspend, revoke, upgrade)
- Fleet-wide metrics

### API Gateway (Port 8000)
Central entry point for all EmpireBox API calls. Routes to individual product services.

### PostgreSQL (Port 5432)
Primary database for all products. Each product gets its own schema/database.

### Redis (Port 6379)
Caching, session storage, and pub/sub messaging between services.

### Ollama (Port 11434)
Local AI inference. Runs llama3.1:8b (default), codellama:7b (coding), and nomic-embed-text (embeddings).

### Products
13 products running as independent Docker Compose stacks on ports 8010-8130. Started on-demand via `ebox` CLI or by OpenClaw skills.

### Portainer (Port 9000)
Docker management web UI for visual container management.

## Port Reference

| Service | Port | Protocol |
|---------|------|----------|
| Dashboard | 80 | HTTP |
| OpenClaw | 7878 | HTTP |
| API Gateway | 8000 | HTTP |
| Control Center | 8001 | HTTP |
| MarketForge | 8010 | HTTP |
| ContractorForge | 8020 | HTTP |
| LuxeForge | 8030 | HTTP |
| SupportForge | 8040 | HTTP |
| LeadForge | 8050 | HTTP |
| ShipForge | 8060 | HTTP |
| ForgeCRM | 8070 | HTTP |
| RelistApp | 8080 | HTTP |
| SocialForge | 8090 | HTTP |
| LLCFactory | 8100 | HTTP |
| ApostApp | 8110 | HTTP |
| EmpireAssist | 8120 | HTTP |
| EmpirePay | 8130 | HTTP |
| Portainer | 9000 | HTTP |
| Ollama | 11434 | HTTP |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |

## Data Flow

1. **User** → Dashboard (browser) → clicks service links
2. **User** → SSH → runs `ebox` CLI → starts/stops products via Docker Compose
3. **OpenClaw** → reads EmpireBox skills → calls `ebox` commands on behalf of user
4. **Customer Units** → POST /heartbeat → Control Center validates license → returns continue/stop
5. **Products** → connect to PostgreSQL + Redis via Docker network `empirebox`
