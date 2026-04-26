# EmpireBox Master Schematic
> Generated: 2026-04-26 | Commit: 12cf18e
> Companion to: EMPIRE_MASTER_DOCUMENT_CURRENT.md, EMPIRE_ARCHITECTURE_CURRENT.md, EMPIRE_MODULE_REGISTRY.md

---

## 1. Master Ecosystem Schematic

```mermaid
flow TB
    subgraph External["Public / External"]
        Browser["Browser<br/>studio.empirebox.store:3005"]
        Telegram["Telegram<br/>@Empire_Max_Bot"]
        PublicWeb["Public Web<br/>/intake / /client-portal"]
    end

    subgraph Cloudflare["Cloudflare Tunnel :443"]
        Studio["studio.empirebox.store"]
        API["api.empirebox.store"]
    end

    subgraph Frontend["Command Center (Next.js :3005)"]
        CC["CommandCenter<br/>page.tsx"]
        Screens["50+ screens<br/>components/screens/"]
        SubApps["intake/ amp/ portal/<br/>services/ workroom/"]
    end

    subgraph Backend["FastAPI Backend (:8000)"]
        APIRoutes["70 loaded routers<br/>load_router() in main.py"]
        MAXAI["MAX AI Orchestrator<br/>system_prompt, ai_router,<br/>tool_executor, 18 desks"]
        Background["Background Services<br/>(primary worker only)"]
    end

    subgraph DataLayer["Data / Storage"]
        EmpireDB["empire.db<br/>customers, invoices,<br/>tasks, inventory"]
        IntakeDB["intake.db<br/>LuxeForge users/projects"]
        Brain["brain/memories.db<br/>3,000+ memories"]
        TokenDB["brain/token_usage.db<br/>1,049 AI calls"]
        Photos["backend/data/photos/<br/>entity-based storage"]
        CraftData["backend/data/craftforge/<br/>JSON files (designs, jobs)"]
        Transcript["backend/data/<br/>transcriptforge/"]
    end

    subgraph AIProviders["AI Provider Chain"]
        Grok["xAI Grok<br/>grok-3-fast"]
        ClaudeS["Anthropic Claude<br/>claude-sonnet-4-6"]
        ClaudeO["Anthropic Claude<br/>claude-opus-4-6"]
        GroqL["Groq<br/>llama-3.3-70b"]
        OpenClawL["OpenClaw<br/>port 7878"]
        OllamaL["Ollama<br/>localhost:11434"]
    end

    subgraph OpenClawSys["OpenClaw System"]
        OCBridge["openclaw_bridge.py<br/>MAX → OpenClaw dispatch"]
        OCTasks["openclaw_tasks.py<br/>Task queue API"]
        OCWorker["openclaw_worker.py<br/>Polls every 30s"]
        OCRunner["OpenClaw runner<br/>port 7878"]
    end

    subgraph HermesSys["Hermes (beneath MAX)"]
        HPhase1["hermes_phase1.py<br/>Memory bridge"]
        HPhase2["hermes_phase2.py<br/>Prep intake"]
        HPhase3["hermes_phase3.py<br/>Browser assist"]
        HMemory["hermes_memory.py<br/>Benchmark capture"]
    end

    Browser -->|"HTTPS :443"| Studio
    Telegram -->|"Bot API"| Backend
    PublicWeb -->|"HTTP :8000"| API

    Studio --> CC
    CC --> Screens
    CC --> SubApps

    CC -->|"/api/*"| APIRoutes
    API -->|"proxied"| APIRoutes

    APIRoutes --> MAXAI
    APIRoutes --> Background

    MAXAI -->|"Per-desk routing"| AIProviders
    MAXAI --> HermesSys
    MAXAI --> OpenClawSys

    Background --> Telegram
    Background --> OCRunner

    APIRoutes --> EmpireDB
    APIRoutes --> IntakeDB
    APIRoutes --> Brain
    APIRoutes --> Photos
    APIRoutes --> CraftData
    APIRoutes --> Transcript

    Grok -->|"fallback chain"| ClaudeS --> GroqL --> OpenClawL --> OllamaL
```

**Key Routing Rules:**
- All browsers → Cloudflare → Next.js (3005) → backend (8000)
- Telegram → FastAPI directly (webhook mode)
- Public intake → FastAPI directly (port 8000)
- MAX: Atlas→Opus, Raven/Phoenix→Sonnet, all others→Grok
- Hermes: bounded beneath MAX, never autonomous
- OpenClaw: local code execution, file safety enforced

---

## 2. Canonical Module Flow Template

Every EmpireBox module should follow this pattern:

```
User Entry Point
      │
      ▼
┌─────────────────┐
│  UI Page/Route  │  ← e.g., app/components/screens/ModulePage.tsx
│  (Next.js)      │    - fetches initial data via api.ts
└────────┬────────┘    - user actions trigger API calls
         │             - state managed in React
         ▼
┌─────────────────┐
│  API Route      │  ← e.g., backend/app/routers/module.py
│  (FastAPI)      │    - router = APIRouter(prefix="/api/v1/module")
│                 │    - Pydantic schemas for req/res
└────────┬────────┘    - calls service layer
         │
         ▼
┌─────────────────┐
│  Service Layer  │  ← e.g., backend/app/services/module_service.py
│  (Business      │    - validation, orchestration
│   Logic)        │    - no DB access directly (use get_db())
└────────┬────────┘
         │
    ┌────┴─────────────────────────────┐
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  │DB/Storage│  │  AI/MAX  │  │External  │
    │  │get_db() │  │ tool_exec│  │ Stripe,  │
    │  │         │  │Hermes    │  │Telegram  │
    │  └──────────┘  └──────────┘  └──────────┘
    └─────────────────────────────────────────
         │
         ▼
┌─────────────────┐
│  Response       │  ← JSON response or redirect
│  / Result       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Logs/Audit     │  ← tool_audit.db, max_response_audit,
│                 │    task_activity, access_audit (if wired)
└─────────────────┘
```

**Standard file locations per module:**
```
Frontend:  empire-command-center/app/components/screens/ModulePage.tsx
           empire-command-center/app/services/module_service/

Backend:   backend/app/routers/module_name.py
           backend/app/services/module_service.py

Data:      empire.db → relevant tables
           OR backend/data/module_name/*.json (for JSON-file storage)
           OR backend/data/photos/{entity_type}/{entity_id}/

AI:        backend/app/services/max/desks/module_desk.py (if has desk)
           backend/app/services/max/hermes_*.py (if Hermes workflow)
```

---

## 3. Per-Module Current Flow Maps

### 3.1 MAX (Multi-Agent eXecutive)

**Entry points:** ChatScreen.tsx (browser), Telegram bot (messaging)
**Backend:** `backend/app/routers/max/router.py` (3734 lines), `services/max/`

```
User message (browser/telegram)
        │
        ▼
MAX router /chat endpoint
        │
        ▼
ai_router.py — determine model per desk
        │
        ├─ Grok (default, 15s) ─────────────────────────┐
        ├─ Claude Sonnet (Raven/Phoenix, 30s) ─────────┤
        ├─ Claude Opus (Atlas, 30s) ────────────────────┤
        ├─ Groq Llama (fallback, 10s) ──────────────────┤
        ├─ OpenClaw (autonomous, 30s) ──────────────────┤
        └─ Ollama LLaVA (last resort, 30s) ─────────────┘
        │
        ▼
system_prompt.py — load MAX brain (identity, 18 desks, tools)
        │
        ▼
tool_executor.py — evaluate L1/L2/L3 tools
        │
        ├─ L1 (auto): search_quotes, get_tasks, send_telegram...
        ├─ L2 (confirm): delete, bulk ops
        └─ L3 (PIN): shell_execute, dispatch_to_openclaw
        │
        ▼
token_tracker.py — log every AI call (model, tokens, cost)
        │
        ▼
Response (streaming SSE to browser, Telegram message)
        │
        ▼
Background (if long task):
  → Hermes Phase 1/2/3 for complex workflows
  → OpenClaw dispatch for code tasks
  → desk_scheduler for autonomous desk tasks
  → MAX memory store (brain/memories.db)
```

**Current gaps:**
- access_audit not wired (tool executions not recorded)
- Agent name collisions: Zara×2, Raven×2, Phoenix×2

---

### 3.2 OpenClaw

**Entry points:** OpenClawTasksPage.tsx, MAX dispatch (tool_executor.py)
**Backend:** `openclaw_bridge.py`, `openclaw_tasks.py`, `services/openclaw_worker.py`
**Runtime:** `~/Empire/openclaw/` port 7878

```
MAX tool_executor → dispatch_to_openclaw (L3 tool)
        │
        ▼
openclaw_bridge.py — check openclaw_gate
        │
        ▼
openclaw_tasks.py POST /api/v1/openclaw/tasks
        │  Creates task: queued state
        │  Stores in empire.db openclaw_tasks table
        ▼
openclaw_worker.py (background, polls every 30s)
        │
        ├─ Worker picks up queued task
        ├─ Sends to OpenClaw runner (port 7878)
        ├─ OpenClaw executes code with file safety
        │    - truncation protection
        │    - critical file guard
        │    - path validation (~/empire-repo/ only)
        │    - auto-backup .bak
        └─ Updates task: running → done/failed
        │
        ▼
Result stored in openclaw_tasks table
MAX notified via response
Frontend updated via polling OpenClawTasksPage
```

**Current gaps:** None major — task queue, worker, gate, file safety all operational

---

### 3.3 Hermes

**Entry points:** Triggered by MAX for long-running workflows
**Backend:** `hermes_phase1.py`, `hermes_phase2.py`, `hermes_phase3.py`, `hermes_memory.py`

```
MAX identifies long-running / multi-step workflow
        │
        ▼
MAX delegates to Hermes (bounded beneath MAX, never autonomous)
        │
        ├─ Phase 1 (memory bridge):
        │    heremes_phase1.py — recall prior context, inject memory
        │
        ├─ Phase 2 (prep intake):
        │    hermes_phase2.py — prep LuxeForge submissions, routing
        │
        ├─ Phase 3 (browser assist):
        │    hermes_phase3.py — web research, multi-source synthesis
        │
        └─ TranscriptForge workflow:
             hermes_transcriptforge.py — intake, qc-review,
             critical-field-check, correction pattern learning
        │
        ▼
Hermes skills (PENDING beneath MAX):
  - transcriptforge-intake
  - transcriptforge-qc-review
  - transcriptforge-critical-field-check
  - workflow memory capture
  - correction pattern learning
  - review checklist generation
        │
        ▼
MAX retains state authority — Hermes reports back, MAX approves
```

**Current gaps:** Hermes benchmark data not yet surfaced in UI

---

### 3.4 AI Model Distributor Hub

**Location:** `backend/app/services/max/ai_router.py` + `ecosystem_catalog.py`

```
Feature/Task incoming
        │
        ▼
ecosystem_catalog.py — model routing table
        │
        ├─ Voice/TTS         → Grok TTS Rex
        ├─ STT/Transcription → Groq Whisper
        ├─ Vision            → Grok (primary), Ollama LLaVA (fallback)
        ├─ Image Gen         → Stability AI, Grok (fallback)
        ├─ Web Chat (MAX)    → Grok, fallback Claude Sonnet
        ├─ Telegram MAX      → Grok, fallback Claude Sonnet
        ├─ Code Planning      → Claude Opus 4.6 (Atlas)
        ├─ Docs/Rendering     → Claude Sonnet 4.6 (Raven)
        ├─ Finance/Quotes    → Grok (Sage/FinanceDesk)
        ├─ Support/Ticketing  → Grok (Luna/SupportDesk)
        ├─ Marketing/Social   → Grok (Nova/MarketingDesk)
        ├─ OpenClaw Tasks     → OpenClaw local
        ├─ Hermes Workflow    → Grok, fallback Claude Sonnet
        ├─ Transcription QC  → Grok
        └─ Emergency          → Full fallback chain
        │
        ▼
Timeout chain per call:
  Grok (15s) → Claude Sonnet (30s) → Groq (10s) → OpenClaw (30s) → Ollama (30s)
        │
        ▼
Result → token_tracker.log()
hermes_memory.py captures benchmark data
```

**Current gaps:** Hub is not yet unified — routing is per-desk in system_prompt, not centralized. AI routing table in this doc is target design, not current implementation.

---

### 3.5 CRM (ForgeCRM)

**Entry points:** ForgeCRMPage.tsx, customer_mgmt router
**Backend:** `customer_mgmt.py`, `contacts.py` (unused)

```
User → ForgeCRMPage.tsx
        │
        ▼
GET /api/v1/customers → customer_mgmt.py
        │
        ▼
empire.db → customers table (113 rows)
        │
        ▼
Customer list / detail displayed
        │
        ├─ Create: POST /api/v1/customers
        ├─ Update: PUT /api/v1/customers/{id}
        └─ Delete: DELETE /api/v1/customers/{id} [L2 confirm]
        │
        ▼
MAX ClientsDesk (Elena) can read/update customer preferences
MAX FinanceDesk (Sage) reads customer for invoice matching
```

**Current gaps:** `contacts` table (0 rows) unused — customers table used instead. No unified contact model.

---

### 3.6 Photo → Quote → Invoice → Payment (Core Workroom Flow)

**Entry:** LuxeForgePage.tsx, QuoteBuilderScreen.tsx, ChatScreen
**Routers:** `photos.py`, `quotes.py`, `quotes_v2.py`, `finance.py`, `payments.py`

```
┌─ PHOTO UPLOAD ────────────────────────────────────────────────────┐
│ User → QuoteBuilderScreen / intake page                          │
│        │                                                         │
│        ▼                                                         │
│ POST /api/v1/photos (multipart, entity_type="quote")              │
│        │                                                         │
│        ▼                                                         │
│ photos.py router                                                  │
│   → PHOTOS_BASE/quote/{quote_id}/  (backend/data/photos/)        │
│   → Validates entity_type, sanitizes entity_id                   │
│   → Returns: {url, thumbnail_url, entity_type, entity_id}         │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ VISION ANALYSIS (optional) ─────────────────────────────────────┐
│ POST /api/v1/vision/analyze                                       │
│        → Grok vision OR Ollama LLaVA                              │
│        → Returns measurements, mockup, outline                     │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ QUOTE CREATION ──────────────────────────────────────────────────┐
│ POST /api/v1/quotes (3-option proposal)                          │
│        │                                                         │
│        ▼                                                         │
│ quotes.py → create_3_option_quote()                               │
│   → Options: Essential / Designer / Premium                       │
│   → Stores quote in empire.db (JSON) OR quotes_v2.py              │
│   → Generates PDF via quote_pdf_service.py                       │
│   → Sends via send_telegram (MAX tool)                            │
│        │                                                         │
│        ▼                                                         │
│ Customer accepts option → POST /api/v1/quotes/{id}/select        │
│        │                                                         │
│        ▼                                                         │
│ quote selected → creates job record                              │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ INVOICE ────────────────────────────────────────────────────────┐
│ POST /api/v1/finance/invoices                                    │
│        │                                                         │
│        ▼                                                         │
│ finance.py router → creates invoice record                       │
│   → Links to customer, job, quote                                │
│   → Stores in empire.db invoices table (9 rows)                   │
│   → Sends invoice PDF via email OR Telegram                       │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ PAYMENT ────────────────────────────────────────────────────────┐
│ POST /api/v1/payments                                             │
│        │                                                         │
│        ▼                                                         │
│ payments.py router → records payment                              │
│   → Cash / check / card / Zelle / Venmo / wire                   │
│   → Updates invoice status: paid / partial / overdue              │
│   → Logs to empire.db payments table                              │
│        │                                                         │
│        ▼                                                         │
│ FinanceDesk (Sage) → P&L dashboard updates                       │
└───────────────────────────────────────────────────────────────────┘
```

**Current gaps:** Email not configured (SendGrid missing). contacts table unused.

---

### 3.7 Finance

**Entry:** InvoiceScreen.tsx, FinanceDesk
**Backend:** `finance.py`, `financial.py`, `quotes.py`, `quotes_v2.py`, `inbox.py`, `payments.py`, `expenses.py`

```
FinanceDesk (Sage) — AI agent owns invoice/expense/P&L
        │
        ▼
InvoiceScreen.tsx → /api/v1/finance/invoices
        │
        ├─ GET / — list invoices (filter by business, status, date)
        ├─ POST / — create invoice
        ├─ GET /{id} — invoice detail
        ├─ PUT /{id} — update invoice
        └─ DELETE /{id} — soft delete [L2 confirm]
        │
        ▼
empire.db → invoices table (9 rows), payments table (2 rows), expenses table (6 rows)
        │
        ▼
P&L calculation: income - expenses = net
Budget tracking: monthly budget $50 default, 80% alert threshold
        │
        ▼
FinanceDesk (Sage) — daily brief includes financial summary
MAX Monitor checks for overdue invoices
```

**Current gaps:** Email not configured, access_audit not wired.

---

### 3.8 Drawing Studio

**Entry:** DrawingStudioPage.tsx
**Backend:** `drawings.py`, `custom_shapes.py`, `pattern_templates.py`

```
User → DrawingStudioPage.tsx
        │
        ├─ POST /api/v1/drawings — create SVG drawing
        ├─ GET /api/v1/drawings — list drawings
        ├─ GET /api/v1/drawings/{id} — download SVG/PDF
        │
        ▼
drawings.py router
  → Generates SVG from user input
  → Converts to PDF via Cairo or similar
  → Stores in backend/data/drawings/
        │
        ▼
pattern_templates.py — sewing pattern math + PDF export
  → custom_shapes.py — custom shape definitions
        │
        ▼
User downloads SVG/PDF
```

**Current gaps:** No AI integration, no desk assigned, no DB persistence of drawings metadata.

---

### 3.9 Workroom (Empire Workroom)

**Entry:** WorkroomPage.tsx, QuoteBuilderScreen.tsx
**Backend:** `finance.py`, `quotes.py`, `customer_mgmt.py`, `inventory.py`, `jobs.py`

```
User → WorkroomPage.tsx
        │
        ├─ Quotes (3-option proposals)
        ├─ Invoices
        ├─ Payments
        ├─ Customers (CRM)
        ├─ Inventory (156 items)
        ├─ Jobs (4 active)
        └─ Vendors (51)
        │
        ▼
ForgeDesk (Kai) — AI agent for workroom operations
  → Creates quotes, follows up, manages tasks
  → Reads/writes empire.db directly
        │
        ▼
FinanceDesk (Sage) — financial pipeline
ClientsDesk (Elena) — client relationships
```

**Status:** Most complete product module. Contacts table unused (customers used).

---

### 3.10 WoodCraft / CraftForge

**Entry:** CraftForgePage.tsx (stub only)
**Backend:** `craftforge.py` (JSON file storage)

```
CraftForgePage.tsx — STUB, no real implementation
        │
        ▼
craftforge.py router (15+ endpoints)
  → JSON file storage: backend/data/craftforge/{designs,jobs,inventory,templates}/
  → Counter file: _counter.json (CF-2026-001, JOB-2026-001...)
        │
        ▼
No DB tables, no AI desk, no frontend
        │
        ▼
Biggest product gap in EmpireBox
```

**Current gaps:** Zero frontend, no desk assigned, JSON file storage (not DB), no product/job flow.

---

### 3.11 ArchiveForge

**Entry:** ArchiveForgePage.tsx, archiveforge-life/ pages
**Backend:** `archiveforge.py`, `recovery.py`

```
User → ArchiveForgePage.tsx
        │
        ├─ POST /api/v1/archiveforge/items — create item
        ├─ GET /api/v1/archiveforge/items — list
        ├─ POST /api/v1/archiveforge/{id}/rebox — rebox workflow
        └─ POST /api/v1/archiveforge/{id}/publish — MarketForge push
        │
        ▼
archiveforge.py
  → V1.2 Review & Publish step
  → Persistent photo storage (backend/data/photos/archiveforge/)
  → Reboxing workflow with metadata
  → LIFE cover search (query-bound)
  → MarketForge product publish route wired
        │
        ▼
MAX routes ArchiveForge tasks to appropriate desk
```

**Current gaps:** Photo upload was broken, fixed (b362e3f). MarketForge publish recently wired.

---

### 3.12 RecoveryForge

**Entry:** RecoveryForgeScreen.tsx
**Backend:** `recovery.py`, `recovery_control.py`, `services/ollama_bulk_classify.py`

```
User → RecoveryForgeScreen.tsx
        │
        ├─ GET /api/v1/recovery/status — L3 classifier status
        ├─ POST /api/v1/recovery/trigger — trigger classification
        └─ GET /api/v1/recovery/results — fetch results
        │
        ▼
recovery_control.py → ollama_bulk_classify.py
  → LLaVA model via Ollama (localhost:11434)
  → 18,472 images processed in bulk
  → Results stored in empire.db
        │
        ▼
Layer 3 classifier running (background, not foreground-visible)
Frontend needs review — completion tracking UI missing
```

**Current gaps:** Frontend needs completion tracking UI, L3 status not visible.

---

### 3.13 RelistApp

**Entry:** RelistAppPage.tsx, RelistAppScreen.tsx
**Backend:** `relistapp.py`, `relist.py`, `listings.py`

```
User → RelistAppPage.tsx
        │
        ├─ POST /api/v1/relist/items — create relist task
        ├─ GET /api/v1/relist — list relist tasks
        └─ POST /api/v1/relist/{id}/publish — publish to marketplace
        │
        ▼
relistapp.py → relist.py
  → Cross-platform relisting
  → Integrates with marketplace listings
  → Photo upload via photos.py
        │
        ▼
MarketDesk (Sofia) — marketplace operations
MarketForge integration (eBay not yet integrated)
```

**Current gaps:** Marketplace wiring incomplete, eBay API not integrated.

---

### 3.14 VendorOps

**Entry:** VendorOpsPage.tsx
**Backend:** `vendorops.py`, `services/vendorops_alert_runner.py`

```
User → VendorOpsPage.tsx
        │
        ├─ GET /api/v1/vendorops/status
        ├─ POST /api/v1/vendorops/subscriptions
        ├─ POST /api/v1/vendorops/checkout — Stripe checkout
        └─ GET /api/v1/vendorops/alerts
        │
        ▼
vendorops.py
  → vo_subscriptions, vo_accounts, vo_alerts tables
  → Tier system: free/starter/pro
  → Stripe integration for checkout
  → Forbidden credential keys (password, api_key, etc.)
        │
        ▼
vendorops_alert_runner.py (background service)
  → Polls for renewal alerts
  → Sends via Telegram when channels available
  → Respects user preferences
        │
        ▼
MAX ambiguity gate — MAX answers VendorOps queries read-only
```

**Status:** Most fully wired VendorOps module. No major gaps.

---

### 3.15 ApostApp

**Entry:** ApostAppPage.tsx
**Backend:** `apostapp.py`

```
User → ApostAppPage.tsx
        │
        ├─ GET /api/v1/apostapp/forms — list forms (nationwide library)
        ├─ POST /api/v1/apostapp/submit — submit for processing
        └─ GET /api/v1/apostapp/status/{id} — track status
        │
        ▼
apostapp.py
  → DC/MD/VA apostille services
  → Nationwide requirements library (docs/)
  → No actual filing integration wired
        │
        ▼
No AI desk, no DB tables, no frontend workflow beyond form display
```

**Current gaps:** Filing not wired to actual apostille service.

---

### 3.16 SocialForge

**Entry:** SocialForgePage.tsx
**Backend:** `socialforge.py`, `social_setup.py`, `services/social_service.py`

```
User → SocialForgePage.tsx
        │
        ├─ GET /api/v1/socialforge/accounts
        ├─ POST /api/v1/socialforge/posts — create post
        └─ GET /api/v1/socialforge/calendar
        │
        ▼
social_service.py
  → INSTAGRAM_API_TOKEN configured
  → FACEBOOK_PAGE_TOKEN configured
  → Semi-automatic posting (user confirms each)
        │
        ▼
MarketingDesk (Nova) — social media content, campaigns
No actual live posting wired (APIs exist but posting not tested)
```

**Current gaps:** Live posting not operational, content calendar not functional.

---

### 3.17 Public Website / Intake / Client Portal

**Entry:** studio.empirebox.store (Cloudflare → Next.js :3005)

```
Public user → studio.empirebox.store
        │
        ├─ /intake/* → intake_auth.py (LuxeForge public portal)
        │    → intake_users, intake_projects (intake.db)
        │    → Photo upload via photos.py
        │    → Vision analysis for measurements
        │
        ├─ /client-portal/* → client_portal.py
        │    → Token-based customer access
        │    → View quotes, invoices, payments
        │
        └─ /api/v1/luxeforge/measurements
             → Image measurement results
             → Vision analysis endpoint
```

**Current gaps:** Public website (`homepage/` port 8080) separate from Command Center.

---

## 4. Current vs Target Notes

| Module | Current Flow | Intended Flow | Gap | Standardization Action |
|--------|--------------|---------------|-----|------------------------|
| MAX | Per-desk routing via system_prompt, AI chain with fallbacks | Centralized AI Model Distributor Hub with per-feature routing table | Routing scattered in system_prompt, no unified hub | Create centralized `ai_distributor.py` with routing table |
| OpenClaw | Task queue → worker → OpenClaw runner, file safety enforced | Same + Hermes benchmarks surfaced in UI | Hermes benchmark data not visible | Add benchmark widget to OpenClawTasksPage |
| Hermes | Bounded beneath MAX, Phase 1/2/3, PENDING skills | MAX retains state authority, Hermes executes sub-workflows | No UI for Hermes skill status | Add Hermes status panel to MAX continuity screen |
| AI Hub | Per-desk model assignment in system_prompt | Unified hub table: feature → model → free/local → fallback → cost | Not implemented as hub, routing is ad-hoc | Formal spec + implementation of ai_distributor.py |
| CRM | customers table (113 rows), contacts unused | Unified contact model with customer/vendor/contractor | contacts table empty, duplicate model | Deprecate contacts, use customers as canonical |
| Photo upload | photos.py router, entity-based storage | Same pattern for all photo types | Inconsistent: some modules bypass photos.py | Enforce photos.py for ALL photo uploads |
| Quotes | 3-option proposals, PDF, Telegram delivery | Same + email delivery (SendGrid) | Email not configured | Configure SendGrid |
| CraftForge | JSON file storage (designs, jobs, inventory), zero frontend | DB tables, full frontend, desk assigned | Biggest product gap | Build CraftForge frontend following standard pattern |
| Finance | empire.db invoices/payments/expenses | Same + email invoicing + access_audit | access_audit empty, email missing | Wire access_audit, configure SendGrid |
| Workroom | Most complete module, contacts unused | Same | contacts table duplicate | Deprecate contacts table |
| VendorOps | vo_subscriptions/alerts/accounts in empire.db, full frontend | Same + SaaS tier management | No multi-tenant isolation | Add tenant_id for SaaS replication |
| ArchiveForge | photos + archiveforge + MarketForge push | Same + full rebox workflow UI | Photo upload was broken, now fixed | Test full rebox workflow end-to-end |
| RecoveryForge | Ollama LLaVA bulk classify, no frontend status | Same + L3 progress UI | No completion tracking in frontend | Add L3 status panel to RecoveryForgeScreen |
| SocialForge | API tokens configured, semi-automatic approach | Live posting via Instagram/Facebook APIs | Posting not wired | Wire social_service.py to live APIs |
| ApostApp | Nationwide forms library, no filing integration | Wire to actual apostille service | Filing not wired | Partner integration or direct filing API |
| Public Intake | intake_auth.py for LuxeForge, photos.py for uploads | Same + unified client portal for all public surfaces | Homepage (port 8080) separate from CC | Merge homepage into Command Center or clearly separate |
| Drawing Studio | drawings.py → SVG/PDF, no AI, no DB metadata | Add AI desk (LabDesk/Phoenix), persist metadata in empire.db | No AI integration, no DB | Add desk assignment, add drawings table to empire.db |

---

## 5. Homogeneity Matrix

| Module | Nav Pattern | API Pattern | Data Persistence | Upload | AI Desk | Job/Task | Audit | Docs | SaaS |
|--------|------------|-------------|-------------------|--------|---------|---------|-------|------|------|
| MAX | ChatScreen | max/router.py | memories.db | N/A | ✅ 18 desks | tasks | max_response_audit | ✅ MAX_BRAIN_SPEC | partial |
| OpenClaw | OpenClawTasksPage | openclaw_tasks.py | empire.db tasks | N/A | dispatch tool | openclaw_tasks | partial | openclaw_build_plan | partial |
| Hermes | (embedded) | (triggered) | transcriptforge/ | N/A | (bounded) | (workflow) | partial | (in MAX docs) | no |
| Workroom | WorkroomPage + tabs | finance/quotes | empire.db | photos.py | ForgeDesk | jobs | access_audit ❌ | empire-ecosystem-report | partial |
| CraftForge | CraftForgePage (stub) | craftforge.py | JSON files ❌ | ❌ | ❌ | ❌ | ❌ | CRAFTFORGE_STATUS | no |
| LuxeForge | intake/ pages | intake_auth | intake.db | photos.py | IntakeDesk | ❌ | ❌ | partial | no |
| Finance | InvoiceScreen | finance.py | empire.db | ❌ | FinanceDesk | ❌ | access_audit ❌ | partial | partial |
| ForgeCRM | ForgeCRMPage | customer_mgmt | empire.db | ❌ | ClientsDesk | ❌ | ❌ | partial | partial |
| VendorOps | VendorOpsPage | vendorops.py | empire.db vo_* | ❌ | MAX gate | ❌ | partial | partial | starter |
| ArchiveForge | ArchiveForgePage | archiveforge.py | empire.db + files | photos.py ✅ | partial | ❌ | ❌ | docs/archiveforge/ | no |
| RecoveryForge | RecoveryForgeScreen | recovery.py | empire.db + files | ❌ | ❌ | ollama_bulk_classify | ❌ | docs/recovery/ | no |
| RelistApp | RelistAppPage | relistapp.py | empire.db | photos.py | ❌ | ❌ | ❌ | docs/relist/ | no |
| TranscriptForge | TranscriptForgePage | transcriptforge.py | transcriptforge/ dir | ✅ | Hermes | transcript jobs | partial | backend/ | no |
| SocialForge | SocialForgePage | socialforge.py | empire.db | ❌ | MarketingDesk | ❌ | ❌ | docs/social/ | no |
| LeadForge | LeadForgePage | leadforge.py | empire.db | ❌ | ❌ | ❌ | ❌ | docs/leadforge/ | no |
| ApostApp | ApostAppPage | apostapp.py | ❌ | ❌ | ❌ | ❌ | ❌ | LLC_FACTORY_APOSTILLE* | no |
| Drawing Studio | DrawingStudioPage | drawings.py | ❌ | ❌ | ❌ | ❌ | ❌ | partial | no |
| SupportForge | SupportForgePage | supportforge_*.py | empirebox.db (empty) | ❌ | SupportDesk | tickets | ❌ | SUPPORTFORGE_*.md | no |

**Legend:** ✅ = done | ❌ = missing/null | partial = incomplete

**Key observations:**
- **Most consistent:** MAX, Workroom, VendorOps, ArchiveForge (photos.py)
- **Least consistent:** CraftForge (JSON files, no DB, no frontend), ApostApp (no persistence), Drawing Studio (no AI, no DB)
- **AI integration:** 10 modules have AI desk or Hermes involvement; 8 have none
- **Audit logging:** Most modules have no explicit audit trail; access_audit table is empty across the board
- **SaaS readiness:** VendorOps has tier structure (starter point); most others have no tenant isolation

---

## 6. SaaS Replication Blueprint

Every EmpireBox product module should follow this structure for multi-tenant SaaS replication:

### Module Home
```
/module-name
  → Dashboard with key metrics
  → Recent activity feed
  → Quick actions (Create, View List, Settings)
  → AI assist panel (floats on right or bottom)
```

### List Page
```
/module-name/list
  → Filterable/searchable table or card grid
  → Bulk actions (select multiple → action)
  → Sort by: date, status, name, value
  → Pagination (or infinite scroll)
  → Export (CSV/PDF)
```

### Detail Page
```
/module-name/{id}
  → Header: name, status badge, key metadata
  → Tab sections: Overview, Activity, Documents, Settings
  → Right sidebar: AI assist, related items, notes
  → Action buttons: Edit, Delete (L2 confirm), Duplicate
```

### Create/Edit Flow
```
/module-name/new or /module-name/{id}/edit
  → Multi-step wizard or single-page form
  → Inline validation (field-level errors)
  → Auto-save draft every 30s
  → AI-assisted field population ("AI fill" button)
  → Submit → validation → success → redirect to detail
```

### AI Assist Panel (standard across all modules)
```
[Floating panel — bottom-right or right sidebar]
  → "Ask about this [module]" text input
  → MAX desk responds (appropriate desk for module)
  → Suggested actions based on context
  → Recent conversation thread (collapsible)
```

### Task/Activity Log
```
[Tab on detail page or standalone /module-name/activity]
  → Chronological list: who did what when
  → Actor avatar, action description, timestamp
  → Filter by: actor, action type, date range
  → MAX task assignments visible here
```

### Status/Metrics Widget
```
[Header area of module home]
  → Key numbers: total, active, this month, value
  → Trend indicators: ↑↓ vs last month
  → Color coded: green (good), yellow (warning), red (critical)
```

### Docs Link
```
[Footer of every module page]
  → "Docs: [Module Name]" → opens relevant doc
  → Icon: 📄 or link to docs/MODULE_SPEC.md
```

### Permissions
```
Standard role matrix per module:
  Viewer: read-only, no actions
  Operator: create, edit own, no delete
  Manager: create, edit, delete own desk
  Admin: full access, can manage users/roles
  Founder: override all, L3 PIN bypass
```

### Standard API Pattern
```python
# Every module router:
router = APIRouter(prefix="/api/v1/module", tags=["module"])

class ModuleSchema(BaseModel):
    name: str
    status: str
    tenant_id: Optional[str] = None  # SaaS isolation

@router.get("")
async def list_items(tenant_id: str = Query(...)):
    # Verify tenant access
    items = db.execute("SELECT * FROM module WHERE tenant_id = ?", (tenant_id,))
    return {"items": items, "total": len(items)}

@router.post("")
async def create(req: ModuleSchema, tenant_id: str = Query(...)):
    # Verify tenant, create, return new item

@router.get("/{item_id}")
async def get_item(item_id: int, tenant_id: str = Query(...)):
    # Verify tenant + ownership, return item
```

### Test/Verification
```python
# Every module should have:
tests/test_module_flow.py:
  - test_module_crud_operations
  - test_module_permissions
  - test_module_ai_integration (if AI desk assigned)
  - test_module_audit_logging (if audit wired)
  - test_module_saas_isolation (if tenant_id present)
```

---

## Appendix: Known Inconsistencies Summary

| Pattern | Status | Modules Following | Modules Not Following |
|---------|--------|-------------------|----------------------|
| APIRouter with prefix `/api/v1/module` | ✅ Standard | MAX, OpenClaw, Finance, VendorOps, ArchiveForge, ... | Some legacy routers use different prefixes |
| Pydantic schemas for req/res | ✅ Standard | Most routers | Some use raw dict |
| DB via get_db() | ✅ Standard | Most routers | Some (craftforge.py) use JSON files |
| Photos via photos.py | ✅ Standard | ArchiveForge, LuxeForge, Workroom | Some modules bypass it |
| AI desk assigned | ✅ Standard | MAX, Workroom, Finance, LuxeForge, Social, Support, Market | CraftForge, ApostApp, Drawing, Recovery, Relist, Lead |
| Task activity logged | ⚠️ Partial | MAX (task_activity table) | Most others don't log |
| access_audit wired | ❌ Missing | None | All modules — access_audit empty |
| tenant_id for SaaS | ❌ Missing | VendorOps (starter tier) | All others |
| docs/MODULE_SPEC.md | ⚠️ Partial | MAX, Workroom, CraftForge, Lead, Support | Most others lack module-specific docs |

---

*Schematic generated by Claude Code — repo audit, 2026-04-26*
*Commit: 12cf18e (main)*