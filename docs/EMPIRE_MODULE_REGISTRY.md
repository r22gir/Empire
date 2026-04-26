# EmpireBox Module Registry
> Generated: 2026-04-26 | Commit: 8662bb3
> Purpose: Per-module detail registry — companion to EMPIRE_MASTER_DOCUMENT_CURRENT.md

---

## How to Use This Registry

Each entry documents one product/module. Fields:
- **Status**: live / partial / stub / deprecated / unknown
- **Frontend**: key files and screens
- **Backend**: key routers, services, and endpoints
- **Data**: tables, files, storage paths
- **AI/MAX**: integration points with MAX, Hermes, OpenClaw
- **Docs**: related documentation files
- **Gaps**: known issues or missing pieces
- **Last verified**: commit or date of last check

---

## Command Center

**Status**: live
**Purpose**: Unified Next.js dashboard — primary MAX interaction surface
**Last verified**: 8662bb3

### Frontend
- `empire-command-center/app/page.tsx` — main entry, CommandCenter component
- `app/components/screens/DashboardScreen.tsx` — 4-tab dashboard
- `app/components/screens/DesksScreen.tsx` — desk status overview
- `app/components/screens/InboxScreen.tsx` — inbox management
- `app/components/screens/TasksScreen.tsx` — task list across all desks
- `app/components/screens/MaxContinuityScreen.tsx` — continuity panel
- `app/components/screens/MemoryBankScreen.tsx` — memory/knowledge browser
- `app/components/screens/OpenClawTasksPage.tsx` — OpenClaw task queue
- `app/components/screens/SystemReportScreen.tsx` — system health/report

### Backend
- Served via Next.js dev server port 3005
- API proxied through `/api` routes to backend port 8000
- `empire-command-center/app/lib/api.ts` — API client
- `empire-command-center/app/lib/types.ts` — TypeScript types

### AI/MAX
- MAX chat interface (streaming SSE via `/api/v1/max/chat`)
- Desk status polling (`/api/v1/max/desks`)
- Continuity panel (supermemory recall, context injection)
- OpenClaw task management via OpenClawTasksPage

### Docs
- `PORT_REGISTRY.md`
- `empire-ecosystem-report.md`

---

## MAX (Multi-Agent eXecutive)

**Status**: live
**Purpose**: AI orchestrator with 18 specialized desks, autonomous scheduling, Telegram notifications
**Last verified**: 8662bb3

### Backend Core
- `backend/app/services/max/system_prompt.py` — MAX brain (identity + rules)
- `backend/app/services/max/ai_router.py` — multi-provider AI routing
- `backend/app/services/max/tool_executor.py` — 35+ tools (2860+ lines)
- `backend/app/services/max/token_tracker.py` — cost tracking
- `backend/app/services/max/telegram_bot.py` — Telegram integration (webhook mode)
- `backend/app/services/max/stt_service.py` — Groq Whisper STT
- `backend/app/services/max/tts_service.py` — Grok TTS Rex
- `backend/app/services/max/inpaint_service.py` — Stability AI inpainting

### Desks (18 total)
| Desk | Agent | Role | Model |
|------|-------|------|-------|
| ForgeDesk | Kai | Workroom operations, quotes, follow-up | Grok |
| MarketDesk | Sofia | Marketplace operations, listings, shipping | Grok |
| MarketingDesk | Nova | Social media, content, campaigns | Grok |
| SupportDesk | Luna | Customer support, tickets, escalation | Grok |
| SalesDesk | Aria | Sales pipeline, leads, proposals | Grok |
| FinanceDesk | Sage | Invoices, payments, expenses, P&L | Grok |
| ClientsDesk | Elena | Client relationships, preferences | Grok |
| ContractorsDesk | Marcus | Installers, scheduling, assignments | Grok |
| ITDesk | Orion | Systems admin, services, monitoring | Grok |
| CodeForge | Atlas | Code creation, editing, testing, git | **Opus 4.6** |
| WebsiteDesk | Zara | Website, SEO, portfolio | Grok |
| IntakeDesk | Zara | LuxeForge submissions, routing | Grok |
| LegalDesk | Raven | Contracts, compliance, legal docs | Grok |
| AnalyticsDesk | Raven | Business intelligence, reports | **Sonnet 4.6** |
| QualityDesk | Phoenix | AI accuracy monitoring, digests | **Sonnet 4.6** |
| LabDesk | Phoenix | R&D sandbox, prototyping | Grok |
| InnovationDesk | Spark | Market scanning, competitor watch | Grok |
| CostTrackerDesk | CostTracker | Token usage, budget monitoring | Grok |

### MAX Routers
- `backend/app/routers/max/` — MAX router module
- `backend/app/routers/max/router.py` — main MAX API (3734 lines)
- `backend/app/routers/openclaw_bridge.py` — MAX→OpenClaw dispatch
- `backend/app/routers/openclaw_tasks.py` — OpenClaw task queue

### Background Services
- `app.services.max.telegram_bot` — Telegram polling/webhook
- `app.services.max.desks.desk_scheduler` — autonomous desk tasks
- `app.services.max.scheduler` — daily briefs, task checks, reports
- `app.services.max.monitor` — overdue tasks, inbox, system health
- `app.services.openclaw_worker` — OpenClaw task queue polling

### AI Routing (Per-Desk Model Assignment)
```python
# From ecosystem_catalog.py / system_prompt.py
Atlas → claude-opus-4-6
Raven → claude-sonnet-4-6
Phoenix → claude-sonnet-4-6
Others → grok-3-fast
Fallback chain: Grok (15s) → Claude Sonnet (30s) → Groq (10s) → OpenClaw (30s) → Ollama (30s)
```

### Hermes Integration
- `hermes_phase1.py` — memory bridge
- `hermes_phase2.py` — prep intake
- `hermes_phase3.py` — browser assist
- `hermes_memory.py` — Hermes memory/benchmark capture
- `transcriptforge_hermes.py` — TranscriptForge QC workflow

### Data
- `backend/data/brain/memories.db` — memories table (~3,000+ entries)
- `backend/data/brain/token_usage.db` — token_usage table (~1,049 calls)
- `backend/data/empire.db` — tasks table (139 tasks)

### Gaps
- Agent name collisions: Zara (website + intake), Raven (legal + analytics), Phoenix (quality + lab)
- `access_audit` table empty — audit logging not wired
- `contacts` table unused — `customers` used instead

### Docs
- `docs/MAX_BRAIN_SPEC.md`
- `docs/AI_DESK_DELEGATION_PLAN.md`
- `docs/DESK_CONSOLIDATION_PLAN.md`
- `docs/max-sync-status.md`

---

## OpenClaw

**Status**: live
**Purpose**: Local AI gateway for autonomous code tasks
**Last verified**: 8662bb3

### Location
- Code: `~/Empire/openclaw/` (separate from empire-repo)
- Port: 7878
- Config: `OPENCLAW_GATEWAY_TOKEN` in `backend/.env`

### Backend Integration
- `backend/app/routers/openclaw_bridge.py` — MAX→OpenClaw dispatch
- `backend/app/routers/openclaw_tasks.py` — task queue API (queued/running/done/failed/paused/cancelled)
- `backend/app/services/openclaw_worker.py` — worker loop (polls every 30s)

### Task Flow
```
create_task → queued → running → done/failed/paused/cancelled
              ↓
         worker picks up, dispatches to OpenClaw
         updates status, stores result/error/files_modified
```

### Task Schema
- title, description, desk, priority (1–10), source, assigned_to, max_retries
- parent_task_id for chaining
- files_modified (JSON), commit_hash on completion

### Recent Fixes
- `4f4c127` — OpenClaw code task routing priority
- `ee268c9` — OpenClaw DB task executor truth
- `8662bb3` — Fix CodeTaskRunner git ops and commit validation

### Docs
- `docs/openclaw_build_plan.md`
- `docs/OPENCLAW_REPO_EDIT_SELF_TEST.md`

---

## Hermes

**Status**: live (bounded beneath MAX)
**Purpose**: MAX's long-running workflow assistant
**Last verified**: 8662bb3

### Files
- `backend/app/services/max/hermes_phase1.py` — memory bridge
- `backend/app/services/max/hermes_phase2.py` — prep intake
- `backend/app/services/max/hermes_phase3.py` — browser assist
- `backend/app/services/max/hermes_memory.py` — benchmark/model memory
- `backend/app/services/max/transcriptforge_hermes.py` — TranscriptForge integration
- `backend/app/services/max/transcriptforge_incidents.py` — incident triage

### Skills
- `transcriptforge-intake` (PENDING)
- `transcriptforge-qc-review` (PENDING)
- `transcriptforge-critical-field-check` (PENDING)
- workflow memory capture
- correction pattern learning
- review checklist generation

### TranscriptForge States
```
uploaded → chunking → first_chunk_processing → first_chunk_ready →
processing_remaining_chunks → verification_running → needs_review →
approved / corrected_and_approved / rejected
```

### Boundaries (from transcriptforge.py header)
- Hermes: PENDING skills, memory capture, pattern learning
- MAX: job state authority, approval boundary, runtime truth

### Docs
- `backend/app/routers/transcriptforge.py` (docstring)

---

## WorkroomForge

**Status**: live
**Purpose**: QB replacement — quotes, invoices, payments, expenses, CRM, inventory
**Last verified**: 8662bb3

### Frontend
- `empire-command-center/app/workroom/` — workroom-specific components
- `app/components/screens/WorkroomPage.tsx`
- `app/components/screens/QuoteBuilderScreen.tsx`
- `app/components/screens/InvoiceScreen.tsx`
- `app/components/screens/JobsScreen.tsx`

### Backend Routers
- `backend/app/routers/finance.py` — main finance/QB replacement
- `backend/app/routers/financial.py` — finance-v2 compatibility
- `backend/app/routers/quotes.py` — quote system (v1)
- `backend/app/routers/quotes_v2.py` — quote system (v2)
- `backend/app/routers/customer_mgmt.py` — CRM
- `backend/app/routers/inventory.py` — inventory management
- `backend/app/routers/jobs.py` — job tracking
- `backend/app/routers/jobs_unified.py` — unified job router
- `backend/app/routers/payments.py` — payment recording
- `backend/app/routers/emails.py` — email sending (not configured)
- `backend/app/routers/inbox.py` — inbox

### Database (empire.db)
| Table | Approx Rows | Purpose |
|-------|-------------|---------|
| customers | 113 | CRM |
| invoices | 9 | Invoice records |
| payments | 2 | Payment records |
| expenses | 6 | Expense tracking |
| inventory_items | 156 | Materials/hardware |
| vendors | 51 | Vendor directory |
| jobs | 4 | Job tracking |

### AI Integration
- ForgeDesk (Kai) — workroom operations
- FinanceDesk (Sage) — invoices, P&L
- ClientsDesk (Elena) — client relationships

### Gaps
- `contacts` table empty — `customers` used instead
- Email not configured (SendGrid missing)
- `access_audit` empty

### Docs
- `empire-ecosystem-report.md`
- `docs/ECOSYSTEM.md`

---

## WoodCraft / CraftForge

**Status**: partial (backend ready, frontend absent)
**Purpose**: Woodwork & CNC business module
**Last verified**: 8662bb3

### Frontend
- `empire-command-center/app/components/screens/CraftForgePage.tsx` — stub only, no real implementation

### Backend
- `backend/app/routers/craftforge.py` — 15+ endpoints (router)
- `backend/app/services/craftforge/` — service layer

### Data
- No database tables yet
- Storage: `backend/data/` (general)

### AI Integration
- No desk assigned yet

### Gaps
- **Zero frontend** — biggest product gap
- No product flow / order tracking
- No CNC job management

### Docs
- `docs/CRAFTFORGE_STATUS_2026-03-08.md` (historical — pre-March 8)
- `docs/CRAFTFORGE_SPEC.md`
- `docs/CRAFTFORGE_SPACESCAN_ADDENDUM.md`
- `docs/social/woodcraft_social_plan.md`

---

## LuxeForge

**Status**: live
**Purpose**: High-end service business intake portal (drapery/upholstery)
**Last verified**: 8662bb3

### Frontend
- `empire-command-center/app/intake/` — intake auth + project submission
  - `intake/auth.tsx`, `intake/page.tsx`, `intake/project/page.tsx`
- `app/components/screens/LuxeForgePage.tsx`
- `app/quote/` — quote pages
- `app/services/llc/` — LLC factory service pages

### Backend
- `backend/app/routers/intake_auth.py` — intake auth router
- `backend/app/routers/luxeforge_measurements.py` — image measurement
- `backend/app/routers/fabrics.py` — fabric library
- `backend/app/routers/notes_extraction.py` — voice notes → quotes
- `backend/app/routers/pattern_templates.py` — sewing pattern math + PDF

### Database
- `backend/data/intake.db` — intake_users, intake_projects tables
  - intake_users: 3 records
  - intake_projects: 5 records

### AI Integration
- IntakeDesk (Zara) — LuxeForge submissions, routing
- Vision analysis (measurement, mockup, outline)

### Recent Fixes
- `b362e3f` — fix(archiveforge): restore photo upload and capture

### Docs
- `docs/INDUSTRY_TEMPLATES.md`

---

## Finance / Quotes / Invoices / Payments

**Status**: live
**Purpose**: Full financial pipeline — 3-option proposals, PDF generation, payment tracking
**Last verified**: 8662bb3

### Backend Routers
- `backend/app/routers/finance.py` — canonical finance
- `backend/app/routers/financial.py` — finance-v2
- `backend/app/routers/quotes.py`, `quotes_v2.py` — 3-option proposals
- `backend/app/routers/payments.py` — payment recording
- `backend/app/routers/crypto_checkout.py` — crypto payments
- `backend/app/routers/inbox.py` — invoice inbox
- `backend/app/routers/work_orders.py` — work orders
- `backend/app/routers/pricing.py` — pricing engine

### Services
- `backend/app/services/quote_service.py` — quote creation/engine
- `backend/app/services/quote_pdf_service.py` — PDF generation
- `backend/app/services/financial_service.py` — financial calculations
- `backend/app/services/pricing_engine.py` — tier-based pricing

### AI Integration
- FinanceDesk (Sage) — invoices, P&L, expenses

### Recent Fixes
- `7acd4ad` — Fix founder-priority quote and handoff workflows

### Gaps
- Email not configured (SendGrid)
- `access_audit` empty

---

## ForgeCRM

**Status**: partial
**Purpose**: Customer relationship management
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/ForgeCRMPage.tsx`

### Backend
- `backend/app/routers/customer_mgmt.py` — primary CRM router
- `backend/app/routers/contacts.py` — contacts table (unused)
- `backend/app/routers/emails.py` — email sending

### Data
- `empire.db.customers` — ~113 records (primary CRM store)
- `empire.db.contacts` — empty (unused)

### AI Integration
- ClientsDesk (Elena) — client relationships, preferences

### Gaps
- contacts table unused (duplication of customers)
- CRM features scattered across multiple routers

---

## VendorOps

**Status**: live
**Purpose**: Subscription renewals, add-on management, Stripe webhook alerts
**Last verified**: 8662bb3

### Backend
- `backend/app/routers/vendorops.py` — core router
- `backend/app/services/vendorops_alert_runner.py` — renewal alert runner
- `backend/app/services/pricing_engine.py` — pricing tiers

### Features
- Core add-on system
- Activation CRUD
- Renewal alerts (polling via vendorops_alert_runner)
- Webhook alert runner (d71192c)
- Checkout wired (3183085)
- Preferences system

### AI Integration
- MAX ambiguity gate
- MAX answers vendorops queries read-only

### Recent Commits
- `d71192c` — feat(vendorops): add webhooks alert runner and preferences
- `3183085` — feat(vendorops): wire checkout and alert delivery
- `8ce64c4` — feat(vendorops): add activation crud and renewal alerts
- `6776acc` — feat(vendorops): add command center add-on screen
- `5325d9a` — feat(vendorops): add core add-on and max ambiguity gate

### Docs
- `docs/audit/` (vendorops-related files)

---

## ArchiveForge

**Status**: live
**Purpose**: Photo-first intake for collectible print/media (LIFE Magazine focus)
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/ArchiveForgePage.tsx`
- `app/archiveforge-life/` — LIFE-specific pages

### Backend
- `backend/app/routers/archiveforge.py`
- `backend/app/routers/recovery.py` — recovery control

### Features (V1.2)
- Direct LIFE intake page
- V1.2 Review & Publish step
- MarketForge product publish route (wired)
- Reboxing workflow + inventory management
- Persistent photo storage (V1.1)
- Photo upload + capture

### Recent Fixes
- `e3a6f33` — fix(archiveforge): make LIFE cover search query-bound
- `77dc2da` — feat(archiveforge): add V1.2 Review & Publish step + MarketForge push
- `b362e3f` — fix(archiveforge): restore photo upload and capture
- `ccda33d` — feat(archiveforge): include rebox metadata in item type

### Docs
- `docs/archiveforge/`

---

## RecoveryForge

**Status**: partial (Layer 3 classifier active)
**Purpose**: File recovery with AI image classification
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/RecoveryForgeScreen.tsx`

### Backend
- `backend/app/routers/recovery.py` — recovery router
- `backend/app/routers/recovery_control.py` — recovery control
- `backend/app/services/ollama_bulk_classify.py` — LLaVA/Ollama bulk classification
- `backend/app/services/ollama_vision_router.py` — vision routing

### Status
- Layer 3 bulk classification running (18,472 images)
- Classifier: LLaVA via Ollama (localhost:11434)

### Gaps
- Frontend needs review/completion
- Layer 3 completion tracking UI

### Docs
- `docs/recovery/` (results in `~/recoveryforge-results/`)

---

## RelistApp

**Status**: partial
**Purpose**: Cross-platform relisting tool
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/RelistAppPage.tsx`
- `app/components/screens/RelistAppScreen.tsx`

### Backend
- `backend/app/routers/relistapp.py` — relist router
- `backend/app/routers/relist.py` — relist operations
- `backend/app/routers/listings.py` — listing management

### Recent Fixes
- RelistAppScreen added
- Photo upload fix

### Gaps
- Full marketplace integration not complete
- Listing optimization not wired

### Docs
- `docs/relist/` (MASTER_PLAN.md)

---

## TranscriptForge

**Status**: live
**Purpose**: Legal/high-risk transcription pipeline with Hermes-assisted QC
**Last verified**: 8662bb3

### Backend
- `backend/app/routers/transcriptforge.py` — main router
- `backend/data/transcriptforge/` — storage directory
  - `jobs/` — job records
  - `chunks/` — audio chunks
  - `artifacts/` — processed artifacts
  - `transcripts/` — final transcripts

### State Machine
```
uploaded → chunking → first_chunk_processing → first_chunk_ready →
processing_remaining_chunks → verification_running → needs_review →
approved / corrected_and_approved / rejected
```

### Configuration
- Chunk duration: 600s (10 min)
- Chunk overlap: 3s
- Provider: Groq Whisper
- Approval: human-only (never auto-approved)

### Hermes Skills (PENDING beneath MAX)
- transcriptforge-intake
- transcriptforge-qc-review
- transcriptforge-critical-field-check

### QC Thresholds
- min_segment_confidence: 0.7
- (configurable via QC_THRESHOLDS dict)

### Recent Commits (11 post-March 18)
- `739d362` — fix(empire): harden runtime truth and transcript review
- `9f2ba0b` — fix(transcriptforge): keep Hermes pending skill status exact
- `8fcdcfe` — fix(transcriptforge): broaden Hermes first consult matching
- `e08641e` — chore(transcriptforge): add pending stuck job triage skill
- `3101d0c` — fix(transcriptforge): persist active chunk transcribing state
- `20cf508` — fix(transcriptforge): add incident triage and truthful first chunk pause
- `87071f4` — fix(transcriptforge): stop final chunk loop
- `7bf95c2` — fix(transcriptforge): gate kickoff at first chunk
- `560288d` — fix(transcriptforge): start upload background tasks
- `d4869bb` — fix(transcriptforge): correct router mount prefix
- `55eeeea` — feat(transcriptforge): add full transcription pipeline with Groq Whisper

---

## LeadForge

**Status**: partial
**Purpose**: AI-powered lead generation and nurturing
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/LeadForgePage.tsx`
- `app/components/screens/LeadForgePageNew.tsx` (newer version)

### Backend
- `backend/app/routers/leadforge.py` — main router
- `backend/app/services/leadforge/` — service layer

### Docs
- `docs/LEADFORGE_SPEC.md`
- `docs/leadforge/outreach_templates_by_target.md`

### Gaps
- Outreach templates not wired to actual send infrastructure

---

## SocialForge

**Status**: partial
**Purpose**: Social media management and automation
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/SocialForgePage.tsx`

### Backend
- `backend/app/routers/socialforge.py` — main router
- `backend/app/routers/social_setup.py` — setup router
- `backend/app/services/social_service.py` — social media service

### Integrations
- Instagram: `INSTAGRAM_API_TOKEN` configured
- Facebook: `FACEBOOK_PAGE_TOKEN` configured

### Approach
- Semi-automatic (user confirms each platform creation)
- Content calendar and scheduling (planned)

### Docs
- `docs/social/instagram_setup_plan.md`
- `docs/social/facebook_content_plan.md`

### Gaps
- Posting not wired to live Instagram/Facebook APIs
- Content calendar not operational

---

## SupportForge

**Status**: partial
**Purpose**: AI-powered customer support and ticketing
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/SupportForgePage.tsx`

### Backend
- `backend/app/routers/supportforge_tickets.py` — ticket management
- `backend/app/routers/supportforge_customers.py` — customer management
- `backend/app/routers/supportforge_kb.py` — knowledge base
- `backend/app/routers/supportforge_ai.py` — AI routing
- `backend/app/services/supportforge_ticket.py`
- `backend/app/services/supportforge_customer.py`
- `backend/app/services/supportforge_kb.py`
- `backend/app/services/supportforge_ai.py`

### Data
- `empirebox.db` — SupportForge database (empty)
- Tables: tickets, customers, kb_articles (empty)

### AI Integration
- SupportDesk (Luna) — tickets, escalation

### Docs
- `docs/SUPPORTFORGE_IMPLEMENTATION.md`
- `docs/SUPPORTFORGE_QUICKSTART.md`
- `docs/SUPPORTFORGE_README.md`

### Gaps
- Knowledge base not populated
- AI ticket routing needs testing

---

## MarketForge

**Status**: partial
**Purpose**: Multi-marketplace listing creation, photo enhancement, AI descriptions
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/MarketForgePage.tsx`

### Backend
- `backend/app/routers/marketforge_products.py`
- `backend/app/routers/marketplaces.py`
- `backend/app/routers/listings.py`
- `backend/app/routers/relist.py`
- `backend/app/services/listing_service.py`
- `backend/app/services/marketplace/` — marketplace services

### Recent
- `489053f` — feat(archiveforge): wire MarketForge product publish route

### Docs
- `docs/MARKETF_OVERVIEW.md`
- `docs/MARKETF_AMAZON_SPEC.md`
- `docs/MARKETF_API.md`
- `docs/MARKETF_FEES.md`
- `docs/MARKETF_SELLER_GUIDE.md`

### Gaps
- eBay API not integrated
- Listing optimization incomplete

---

## ApostApp

**Status**: partial
**Purpose**: Document apostille & authentication (DC/MD/VA)
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/ApostAppPage.tsx`

### Backend
- `backend/app/routers/apostapp.py` — apostille router

### Docs
- `docs/LLC_FACTORY_APOSTILLE_FORMS_GUIDE.md`
- `docs/LLC_FACTORY_NATIONWIDE_REQUIREMENTS.md`

### Gaps
- Filing not wired to actual apostille service

---

## LLCFactory

**Status**: partial
**Purpose**: LLC formation & compliance (hybrid partner + DIY approach)
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/LLCFactoryPage.tsx`

### Backend
- `backend/app/routers/llcfactory.py` — LLC formation router

### Model
- Partner with Northwest Registered Agents for state filings
- DIY EIN and forms via ApostApp integration

### Docs
- `docs/LLC_FACTORY_FEDERAL_FORMS_GUIDE.md`

### Gaps
- Partner integration not wired

---

## ConstructionForge

**Status**: partial
**Purpose**: Colombian real estate land development
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/ConstructionForgePage.tsx`

### Backend
- `backend/app/routers/construction.py` — construction router

### Recent
- `18312be` — feat(empire): update construction forge products (last commit before current HEAD)

---

## StoreFrontForge

**Status**: partial
**Purpose**: Retail store management / POS
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/StoreFrontForgePage.tsx`

### Backend
- `backend/app/routers/storefront.py` — storefront router

---

## ShipForge

**Status**: partial
**Purpose**: Shipping solutions, rate comparison, label generation
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/ShipForgePage.tsx`

### Backend
- `backend/app/routers/shipping.py` — shipping router
- `backend/app/services/shipping_service.py` — shipping service

### Data
- `empire.db` — vendor, inventory data

### AI Integration
- MarketDesk (Sofia) — shipping integration

### Gaps
- Label generation not complete
- Carrier rate comparison not fully wired

---

## ContractorForge

**Status**: partial
**Purpose**: Universal SaaS for service businesses (contractors)
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/ContractorForgePage.tsx`

### Backend
- `empire-repo/contractorforge_backend/` — separate backend repository
- Not part of main empire-repo backend

### Gaps
- Separate backend from main empire-repo

---

## AMP (Actitud Mental Positiva)

**Status**: partial (needs rebuild)
**Purpose**: Spanish-language personal development platform
**Last verified**: 8662bb3

### Frontend
- `empire-command-center/app/amp/` — AMP pages

### Backend
- `backend/app/routers/amp.py` — AMP router

### Data
- `backend/data/amp.db` — empty (4 tables, no data)

### Note
- "Current version didn't capture the idea" — needs rebuild

---

## Avatar / Presentation Mode

**Status**: partial (untested)
**Purpose**: 3D avatar (TalkingHead) via iframe
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/PresentationScreen.tsx`

### Backend
- `backend/app/routers/avatar.py` — avatar router
- `backend/app/routers/presentations.py` — presentation mode

### Gaps
- TalkingHead iframe needs live browser testing

---

## Drawing Studio

**Status**: partial
**Purpose**: Architectural bench drawings (SVG + PDF), sewing pattern math + PDF export
**Last verified**: 8662bb3

### Frontend
- `app/components/screens/DrawingStudioPage.tsx`

### Backend
- `backend/app/routers/drawings.py` — drawing router
- `backend/app/routers/custom_shapes.py` — custom shapes
- `backend/app/routers/pattern_templates.py` — pattern math + PDF export

### Features
- SVG drawing generation
- PDF export
- Pattern template generation

---

## Vision Analysis

**Status**: live
**Purpose**: AI-powered image analysis and measurements
**Last verified**: 8662bb3

### Backend
- `backend/app/routers/vision.py` — main vision router
- `backend/app/routers/photos.py` — unified photo storage
- `backend/app/services/vision/` — vision services
- `backend/app/services/ollama_vision_router.py` — Ollama vision

### Features
- Measurement (LuxeForge measurements)
- Mockup generation
- Outline detection
- Upholstery analysis
- Image generation
- Inpainting (Stability AI)

### AI Providers
- Grok vision (primary)
- Ollama LLaVA (fallback/local)

---

## Smart Analyzer / SimulaLab

**Status**: partial
**Purpose**: Multi-method analysis, business intelligence
**Last verified**: 8662bb3

### Backend
- `backend/app/api/v1/smart_analyzer.py` — smart analyzer router

### Recent
- `061f7bc` — Add CPU-safe SimulaLab eval dataset pilot

### Docs
- `docs/SIMULA_LAB.md`

---

## MarketF (P2P Marketplace)

**Status**: partial (planned)
**Purpose**: P2P marketplace with escrow, Stripe Connect payments
**Last verified**: 8662bb3

### Backend
- `backend/app/routers/marketplace/` — marketplace subpackage
- `backend/app/routers/marketplaces.py` — marketplaces router

### Gaps
- Stripe Connect onboarding not wired
- Dispute resolution not implemented

---

## Notes-to-Quote / Document Processing

**Status**: partial
**Purpose**: Voice notes → structured quotes, document extraction
**Last verified**: 8662bb3

### Backend
- `backend/app/routers/notes_extraction.py` — notes to quote
- `backend/app/routers/custom_shapes.py` — custom shape definitions
- `backend/app/services/quote_service.py` — quote engine

### Frontend
- `app/components/screens/DocumentScreen.tsx`
- `app/components/screens/QuoteBuilderScreen.tsx`
- `app/components/screens/QuoteReviewScreen.tsx`

---

## OpenCode

**Status**: live (adopted)
**Purpose**: Agent framework config (build agent, instruction chain)
**Last verified**: 8662bb3

### Config File
- `~/empire-repo/opencode.json`

### Instructions Chain
1. `AGENTS.md` — developer guide
2. `CLAUDE.md` — session instructions
3. `.claude-progress.md` — active session progress

### Agent Config
- `default_agent`: "plan"
- `share`: "manual"
- `build` agent with elevated permissions
- `permission`: bash/edit → ask, webfetch/websearch → allow

---

*Module registry generated by Claude Code — repo audit, 2026-04-26*