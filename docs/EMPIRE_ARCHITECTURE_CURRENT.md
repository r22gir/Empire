# EmpireBox Architecture — Current
> Generated: 2026-04-26 | Commit: da3fdf4 (813 commits verified via `git rev-list --count HEAD`)
> Status: partial — high-level documented, per-module flows need completion

---

## System Overview

```
                        ┌─────────────────────────────────┐
                        │      Cloudflare Tunnel          │
                        │  studio.empirebox.store :443     │
                        │  api.empirebox.store :443        │
                        └──────────────┬──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
              ┌─────▼─────┐     ┌──────▼──────┐   ┌──────▼──────┐
              │  Browser  │     │   Telegram  │   │  HTTP API  │
              │  (CC :3005)│     │  (@Empire   │   │  (:8000)   │
              │           │     │  Max_Bot)   │   │            │
              └─────┬─────┘     └──────┬──────┘   └──────┬──────┘
                    │                │                 │
                    └────────────────┼─────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │   FastAPI Backend     │
                         │   (port 8000, uvicorn)│
                         │   primary worker only │
                         └───────────┬───────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
  ┌───────▼───────┐         ┌────────▼────────┐       ┌────────▼────────┐
  │  MAX (18 desks)│         │   Routers (80 files, 70 loaded)  │       │ Background Svc │
  │  AI Router    │         │   finance, crm,  │       │ Telegram Bot   │
  │  Tool Executor│         │   max, vendorops,│       │ Desk Scheduler │
  │  Hermes       │         │   archive, etc.   │       │ OpenClaw Worker│
  └───────┬───────┘         └────────┬────────┘       │ MAX Monitor    │
          │                          │               │ VendorOps Alert│
          │            ┌─────────────┼──────────────┐               │
          │            │             │              │               │
  ┌───────▼───────────▼──┐  ┌───────▼──────┐  ┌────▼─────────────┐
  │  AI Provider Chain    │  │  Database    │  │  Service Layer   │
  │  Grok → Claude →     │  │  empire.db   │  │  openclaw_worker │
  │  Groq → OpenClaw →   │  │  intake.db   │  │  desk_scheduler  │
  │  Ollama              │  │  brain/*     │  │  max_scheduler   │
  └──────────────────────┘  └─────────────┘  └─────────────────┘
```

---

## Service Map

| Service | Port | Location | Status | Notes |
|---------|------|----------|--------|-------|
| FastAPI Backend | 8000 | `~/empire-repo/backend/` | Active | Primary API |
| Command Center | 3005 | `~/empire-repo/empire-command-center/` | Active | Next.js 16 |
| OpenClaw AI | 7878 | `~/Empire/openclaw/` | Available | Local AI gateway |
| Ollama LLM | 11434 | System service | Running | LLaVA for classification |
| Cloudflare Tunnel | 443 | cloudflared | Active | studio + api subdomains |
| Telegram Bot | — | Embedded in backend | Active | Webhook mode |
| PostgreSQL | 5432 | Docker | Available | Prod only |
| Redis | 6379 | Docker | Available | Prod only |
| WorkroomForge | 3001 | `~/empire-repo/workroomforge/` | Active | Legacy standalone |
| LuxeForge | 3002 | `~/empire-repo/luxeforge_web/` | Active | Legacy standalone |
| AMP | 3003 | `~/empire-repo/amp/` | Active | Legacy standalone |
| RelistApp | 3007 | `~/empire-repo/relistapp/` | Active | Legacy standalone |
| Founder Dashboard | 3009 | `~/empire-repo/founder_dashboard/` | Active | Legacy standalone |

*Note: Most frontends now served via Command Center (port 3005) with Next.js routing. Standalone servers are legacy.*

---

## Backend Architecture

### Entry Point
`backend/app/main.py` — FastAPI app, loads 70 routers via `load_router()` helper; 80 Python files present in `backend/app/routers/` (the difference: `__init__.py`, `marketplace/` subpackage, and any unloaded stubs)

### Primary Worker Lock
File lock at `/tmp/empire_primary_worker.lock` — singleton services (Telegram, schedulers, workers) run on primary worker only to prevent conflicts.

### Router Categories

**MAX/AI Routers**:
- `max/` — MAX chat, desk routing, memory, continuity
- `openclaw_bridge.py` — MAX→OpenClaw dispatch
- `openclaw_tasks.py` — OpenClaw task queue
- `transcriptforge.py` — Legal transcription pipeline

**Business Routers**:
- `finance.py`, `financial.py` — QB replacement, invoices, P&L
- `quotes.py`, `quotes_v2.py` — 3-option proposals
- `customer_mgmt.py` — CRM (113 customers)
- `contacts.py` — Contacts (unused, customers used instead)
- `inventory.py` — 156 inventory items
- `jobs.py`, `jobs_unified.py` — Job tracking
- `payments.py` — Payment recording
- `emails.py` — Email sending (not configured)
- `inbox.py` — Invoice inbox

**Intake/Client Portal**:
- `intake_auth.py` — LuxeForge intake auth
- `client_portal.py` — Token-based customer access
- `luxeforge_measurements.py` — Image measurement

**Product/Listing Routers**:
- `marketforge_products.py` — Product management
- `marketplaces.py` — Marketplace integration
- `listings.py` — Listing creation/management
- `relistapp.py`, `relist.py` — Relisting
- `archiveforge.py` — Collectible print/media intake
- `craftforge.py` — Woodwork/CNC (partial)

**Social/Content**:
- `socialforge.py` — Social media management
- `supportforge_tickets.py`, `supportforge_customers.py`, `supportforge_kb.py`, `supportforge_ai.py`
- `leadforge.py` — Lead generation

**Specialized Services**:
- `vendorops.py` — Subscription renewals, add-ons
- `llcfactory.py` — LLC formation
- `apostapp.py` — Document apostille
- `construction.py` — Colombian real estate
- `storefront.py` — Retail POS
- `shipping.py` — Shipping management
- `avatar.py`, `presentations.py` — 3D avatar
- `drawings.py` — Drawing studio
- `fabrics.py` — Fabric library
- `photos.py` — Unified photo storage
- `vision.py` — Vision analysis

**System Routers**:
- `docker_manager.py` — Docker management
- `system_monitor.py` — System health
- `ollama_manager.py` — Ollama management
- `notifications.py` — Notification system
- `desks.py`, `tasks.py`, `contacts.py` — Task engine
- `costs.py` — AI cost tracking (11 endpoints)
- `accuracy.py` — AI accuracy monitoring
- `maintenance.py` — MAX autonomous maintenance
- `dev.py` — Dev panel
- `qr.py` — QR code generation

### Background Services
```
startup:
  → acquire_primary_worker_lock()
  → write_startup_health_record()
  → create_all_tables() [unified business migration]
  → telegram_bot.start_webhook_mode()  [primary only]
  → desk_scheduler.start()              [primary only]
  → max_scheduler.start()               [primary only]
  → max_monitor.start()                 [primary only]
  → openclaw_worker_loop()              [primary only]
  → vendorops_alert_runner.start()      [primary only]
  → _task_auto_worker()                [primary only]
  → _startup_probes()                  [brain warm-up, health check]
```

---

## Frontend Architecture

### Command Center (Main)
`empire-command-center/app/` — Next.js 16, App Router, **no `src/` directory**

- `page.tsx` → CommandCenter component (4 tabs: MAX, Workroom, CraftForge, Platform)
- `layout.tsx` → I18nWrapper
- `globals.css` → design system
- `components/screens/` → 50+ screen components
- `components/hooks/` → custom hooks
- `components/lib/` → api.ts, types.ts, utilities
- Subdirectories: `amp/`, `intake/`, `portal/`, `services/`, `max/`, `archiveforge-life/`, `workroom/`, `woodcraft/`, `transcriptforge-review/`

### Screen Categories

| Category | Screens |
|----------|---------|
| MAX/AI | ChatScreen, DesksScreen, TasksScreen, MaxContinuityScreen, MemoryBankScreen, OpenClawTasksPage, SystemReportScreen |
| Workroom | WorkroomPage, QuoteBuilderScreen, QuoteReviewScreen, InvoiceScreen, JobsScreen |
| Finance | InvoiceScreen, PricingPage, BusinessProfileScreen |
| CRM | ForgeCRMPage, InboxScreen, DocumentScreen |
| Products | CraftForgePage, LuxeForgePage, LeadForgePage, LeadForgePageNew, SocialForgePage, SupportForgePage, MarketForgePage |
| Specialized | ArchiveForgePage, RecoveryForgeScreen, RelistAppPage, RelistAppScreen, DrawingStudioPage, AvatarPage, PresentationScreen |
| Legal | TranscriptForgePage, ApostAppPage, LLCFactoryPage |
| Business | ContractorForgePage, ConstructionForgePage, ShipForgePage, StoreFrontForgePage, VendorOpsPage |
| Meta | DashboardScreen, PlatformPage, ProductCatalogPage, EcosystemProductPage, EmpireAssistPage, EmpirePayPage, SmartListerPanel |

### Legacy Standalone Frontends
- `workroomforge/` (port 3001) — legacy Workroom standalone
- `luxeforge_web/` (port 3002) — legacy LuxeForge
- `amp/` (port 3003) — legacy AMP
- `relistapp/` (port 3007) — legacy RelistApp
- `founder_dashboard/` (port 3009) — legacy Founder Dashboard

---

## Database Architecture

### empire.db (Main)
```
tasks (139 rows) — all desk tasks with lifecycle
task_activity (165 rows) — task history/changelog
desk_configs (15 rows) — AI desk configuration
customers (113 rows) — CRM
invoices (9 rows) — invoice records
payments (2 rows) — payment records
expenses (6 rows) — expense tracking
inventory_items (156 rows) — materials/hardware
vendors (51 rows) — vendor directory
jobs (4 rows) — job tracking
max_response_audit (94 rows) — AI response quality
access_users (5 rows) — user accounts
access_sessions (0 rows) — tool auth sessions
access_audit (0 rows) — tool execution audit (NOT WIRED)
contacts (0 rows) — unused, customers used instead
```

### intake.db (LuxeForge)
```
intake_users (3 rows) — portal user accounts
intake_projects (5 rows) — client project submissions
```

### brain/memories.db (MAX Memory)
```
memories (3,000+ rows) — persistent memory entries
conversation_summaries (99 rows) — chat summaries
customers (0 rows) — brain customer context
customer_interactions (0 rows) — interaction tracking
knowledge (0 rows) — knowledge base
```

### brain/token_usage.db (AI Cost)
```
token_usage (1,049 rows) — every AI API call
budget_config (1 row) — monthly budget ($50 default)
```

### tool_audit.db
```
tool_executions (46 rows) — tool execution history
```

### transcriptforge/ (File-based)
```
transcriptforge/jobs/ — job records
transcriptforge/chunks/ — audio chunks
transcriptforge/artifacts/ — processed artifacts
transcriptforge/transcripts/ — final transcripts
```

### empirebox.db (SupportForge — empty)
### amp.db (AMP — empty, 4 tables)

---

## AI Provider Routing

### Fallback Chain
```
Grok (15s timeout)
  → Claude Sonnet 4.6 (30s timeout)
  → Groq Llama 3.3 70B (10s timeout)
  → OpenClaw (30s timeout)
  → Ollama LLaVA (30s timeout)
```

### Per-Desk Model Assignment
| Desk | Agent | Model |
|------|-------|-------|
| CodeForge | Atlas | **Opus 4.6** |
| AnalyticsDesk | Raven | **Sonnet 4.6** |
| QualityDesk | Phoenix | **Sonnet 4.6** |
| All others | (varies) | grok-3-fast |

### Provider Config
| Provider | Env Var | Purpose | Status |
|----------|---------|---------|--------|
| xAI Grok | XAI_API_KEY | Primary chat/vision/TTS | ✅ |
| Anthropic Claude | ANTHROPIC_API_KEY | Sonnet + Opus | ✅ |
| Groq | GROQ_API_KEY | Fast inference + Whisper STT | ✅ |
| OpenClaw | OPENCLAW_GATEWAY_TOKEN | Local AI gateway | ✅ |
| Ollama | localhost:11434 | Local LLaVA | ✅ |
| Stability AI | STABILITY_API_KEY | Image inpainting | ✅ |
| Brave Search | BRAVE_API_KEY | Web search fallback | ✅ |
| OpenAI | OPENAI_API_KEY | **Not used** | ❌ |

---

## Homogeneity / Standardization Matrix

| Module | Uses Standard Router Pattern | Has Frontend Screen | Has DB Table | Has AI Desk | Follows File Safety | Notes |
|--------|------------------------------|--------------------|--------------|-------------|---------------------|-------|
| MAX | ✅ | ✅ (DesksScreen, TasksScreen) | ✅ (tasks) | ✅ (18 desks) | ✅ | System anchor |
| WorkroomForge | ✅ | ✅ | ✅ | ✅ (ForgeDesk) | ✅ | Most complete product |
| Finance | ✅ | ✅ | ✅ | ✅ (FinanceDesk) | ✅ | |
| LuxeForge | ✅ | ✅ | ✅ (intake.db) | ✅ (IntakeDesk) | ✅ | |
| CraftForge | ✅ | ❌ (stub only) | ❌ | ❌ | ✅ | Biggest gap |
| ArchiveForge | ✅ | ✅ | ✅ | Partial | ✅ | |
| RecoveryForge | ✅ | ✅ | ✅ | ❌ | ✅ | |
| RelistApp | ✅ | ✅ | ✅ | ❌ | ✅ | |
| TranscriptForge | ✅ | ✅ | file-based | ❌ (Hermes) | ✅ | |
| VendorOps | ✅ | ✅ | ✅ | ✅ (MAX gate) | ✅ | |
| SupportForge | ✅ | ✅ | empirebox.db (empty) | ✅ (SupportDesk) | ✅ | KB not populated |
| SocialForge | ✅ | ✅ | ✅ | ✅ (Nova) | ✅ | Posting not wired |
| LeadForge | ✅ | ✅ | ✅ | ❌ | ✅ | Outreach not wired |
| MarketForge | ✅ | ✅ | ✅ | ✅ (MarketDesk) | ✅ | eBay not integrated |
| ApostApp | ✅ | ✅ | ❌ | ❌ | ✅ | Filing not wired |
| LLCFactory | ✅ | ✅ | ❌ | ❌ | ✅ | Partner not wired |
| Construction | ✅ | ✅ | ❌ | ❌ | ✅ | |
| ShipForge | ✅ | ✅ | ✅ | ✅ (MarketDesk) | ✅ | Labels incomplete |
| AMP | ✅ | ✅ | amp.db (empty) | ❌ | ✅ | Needs rebuild |
| Avatar | ✅ | ✅ | ❌ | ❌ | ✅ | TalkingHead untested |
| Drawing Studio | ✅ | ✅ | ❌ | ❌ | ✅ | |

---

## Standard Patterns (What "Good" Looks Like)

### Router Pattern
```python
router = APIRouter(prefix="/api/v1/module", tags=["module"])

class Schema(BaseModel):
    field: str

@router.post("")
async def create(req: Schema):
    return {"id": "new-id"}
```

### Desk Pattern
- `backend/app/services/max/desks/forge_desk.py` — implements BaseDesk
- Agent name, role, system prompt, tool permissions
- Model routing via ecosystem_catalog.py

### Frontend Screen Pattern
- `app/components/screens/ModulePage.tsx`
- Uses `app/lib/api.ts` for backend calls
- Uses `app/lib/types.ts` for TypeScript types

---

## SaaS Replication Blueprint

Each module should be replicable as multi-tenant SaaS:
1. **Schema isolation** — tenant_id on all tables
2. **Router-level auth** — verify tenant before data access
3. **Per-tenant AI routing** — model quotas per tenant
4. **Webhook isolation** — per-tenant callback URLs
5. **Billing integration** — VendorOps-style subscription management

---

*Architecture doc generated by Claude Code — repo audit, 2026-04-26*
*Commit: da3fdf4 (main)*