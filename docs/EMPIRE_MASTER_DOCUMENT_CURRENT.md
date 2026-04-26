# EmpireBox Master Document — Current
> Generated: 2026-04-26
> Repo truth: `main`, commit `da3fdf4`, 813 total commits (verified via `git rev-list --count HEAD`)
> Supersedes: empire-ecosystem-report.md (March 18 baseline, 396 commits) and any PDF master documents
> Note: "Old PDF" baselines in this document refer to empire-ecosystem-report.md which was generated 2026-03-18.
  PDFs named EMPIRE_MASTER_DOCUMENT_2026*.pdf are historical only — their claims must be verified against current repo state.
> Author: Claude Code (repo-backed audit, not guesswork)

---

## A. Executive Summary

**EmpireBox** is a comprehensive AI-powered business automation platform self-hosted on EmpireDell (Dell PowerEdge, Xeon E5-2650 v3, 32GB RAM, Ubuntu 24.04). It serves:

1. **Empire Workroom** — Custom drapery & upholstery (active, ~113 customers)
2. **WoodCraft** — Woodwork & CNC (planned, spec exists, no frontend yet)
3. **Empire Platform** — SaaS subscriptions (Lite $29 / Pro $79 / Empire $199/month)

The system is anchored by **MAX** (Multi-Agent eXecutive) — an AI orchestrator with 18 specialized desks, 35+ tools, and persistent memory. MAX routes through a multi-provider AI chain (Grok → Claude → Groq → OpenClaw → Ollama) and communicates via a web-based Command Center and Telegram bot.

**Current state**: 80 Python router files in `backend/app/routers/`, 70 loaded via `load_router()` in `main.py` (see distinction below), 50+ frontend screens, 813 commits, ~1,049 AI calls logged. Largest gaps: CraftForge frontend, full SocialForge/SupportForge backend wiring.

---

## B. Historical Baseline

The **empire-ecosystem-report.md** (March 18, 2026) documented:
- 396 commits, 22 products, 18 desks, 35 tools, 7 databases
- Development period: Feb 22 – Mar 18, 2026
- Source: Full codebase scan (396 commits, 44 screens, 35 tools, 18 desks, 7 databases)

*Note: Any PDF named EMPIRE_MASTER_DOCUMENT_2026*.pdf is an older/alternative historical record.
 Its claims are not authoritative — always verify against current repo state.*

**Changes since March 18 baseline (empire-ecosystem-report.md):**
- 417 new commits (396 → 813)
- TranscriptForge added (legal transcription pipeline, Hermes phases 1–3)
- MAX supermemory/continuity panel added
- VendorOps fully wired (checkout, webhook alert runner, preferences, renewal alerts)
- ArchiveForge V1.2 with MarketForge publish integration
- OpenClaw code task routing + DB executor fixes
- RecoveryForge Layer 3 classification active (18,472 images, LLaVA/Ollama)
- Hermes Phase 3 browser assist operational
- CodeTaskRunner git ops and evidence verification hardened
- Multiple MAX truth/routing boundary fixes

---

## C. Current Architecture

### Backend (FastAPI, port 8000)
- **Entry**: `backend/app/main.py` — loads 70 routers via `load_router()` helper (see router count distinction below)
- **Startup**: File-lock at `/tmp/empire_primary_worker.lock` — singleton background services only on primary worker
- **Router count**: 80 Python files present in `backend/app/routers/`; 70 loaded via `load_router()` in `main.py`; the difference (10 files) includes `__init__.py`, `marketplace/` package, and routers not yet loaded (e.g., some stubs)
- **Background services** (primary worker only):
  - Telegram Bot (webhook mode)
  - Desk Scheduler
  - MAX Scheduler (daily briefs, task checks, reports)
  - MAX Monitor (overdue tasks, inbox, system health)
  - OpenClaw Worker Loop (polls task queue every 30s)
  - Task Auto-Worker (polls todo tasks every 30s)
  - VendorOps Alert Runner (renewal alerts)
  - Startup probes (brain warm-up, health check, urgent task execution)

### Frontend (Next.js 16, port 3005)
- **Entry**: `empire-command-center/app/page.tsx` → `CommandCenter` component
- **No `src/` directory** (flat structure)
- **Screens**: 50+ in `app/components/screens/` (DashboardScreen, QuoteBuilderScreen, TasksScreen, etc.)
- **Sub-apps**: intake/, amp/, portal/, services/ subdirectories

### Database
- `backend/data/empire.db` — main (tasks, customers, invoices, payments, expenses, inventory, vendors, jobs, etc.)
- `backend/data/intake.db` — LuxeForge portal (users, projects)
- `backend/data/brain/memories.db` — MAX persistent memory (~3,000+ entries)
- `backend/data/brain/token_usage.db` — AI cost tracking (~1,049 calls)
- `backend/data/tool_audit.db` — tool execution log
- `backend/data/transcriptforge/` — job storage, chunks, artifacts, transcripts

### AI Provider Routing
**Fallback Chain**: Grok (15s) → Claude Sonnet (30s) → Groq (10s) → OpenClaw (30s) → Ollama (30s)

| Model | Provider | Used For |
|-------|----------|----------|
| grok-3-fast | xAI | Default for all desks |
| claude-sonnet-4-6 | Anthropic | Raven (Analytics), Phoenix (Quality) |
| claude-opus-4-6 | Anthropic | Atlas (CodeForge) |
| groq-llama-3.3-70b | Groq | Fallback |
| openclaw | Local | Autonomous tasks |
| ollama-llama3.1 | Local | Last resort |

### Key Services
| Service | Port | Status |
|---------|------|--------|
| Backend API (FastAPI) | 8000 | Active |
| Command Center (Next.js) | 3005 | Active |
| OpenClaw AI | 7878 | Available |
| Ollama LLM Server | 11434 | Running |
| Cloudflare Tunnel | 443 | Active (studio.empirebox.store, api.empirebox.store) |
| Telegram Bot | — | Embedded, webhook mode |
| PostgreSQL | 5432 | Available (docker) |
| Redis | 6379 | Available (docker) |

---

## D. Product / Module Registry

### 1. Command Center
**Status**: Live
- **Purpose**: Unified Next.js dashboard — main MAX interaction surface
- **Frontend**: `empire-command-center/app/page.tsx`, `app/components/screens/DashboardScreen.tsx`, `DesksScreen.tsx`, `InboxScreen.tsx`, `TasksScreen.tsx`, `MaxContinuityScreen.tsx`, `MemoryBankScreen.tsx`
- **Backend**: Served via Next.js dev server (port 3005), API proxied to backend :8000
- **Data**: In-memory React state + API calls to backend
- **AI integration**: MAX chat (streaming SSE), desk status, continuity panel, supermemory recall
- **Recent changes**: Continuity panel, supermemory recall, openclaw tasks page
- **Docs**: `docs/`, `PORT_REGISTRY.md`, `empire-ecosystem-report.md`

### 2. MAX (Multi-Agent eXecutive)
**Status**: Live
- **Purpose**: AI orchestrator — 18 specialized desks, autonomous scheduling, Telegram notifications
- **Backend**: `backend/app/services/max/` — system_prompt, ai_router, tool_executor, token_tracker, telegram_bot, desks/, brain/, hermes_*.py
- **Desks**: forge_desk (Kai), market_desk (Sofia), marketing_desk (Nova), support_desk (Luna), sales_desk (Aria), finance_desk (Sage), clients_desk (Elena), contractors_desk (Marcus), it_desk (Orion), codeforge_desk (Atlas), website_desk (Zara), intake_desk (Zara), legal_desk (Raven), analytics_desk (Raven), quality_desk (Phoenix), lab_desk (Phoenix), innovation_desk (Spark), cost_tracker_desk (CostTracker)
- **Tools**: 35+ organized in L1 (auto), L2 (confirm), L3 (PIN required)
- **AI routing**: Per-desk model assignment (Atlas→Opus, Raven/Phoenix→Sonnet, others→Grok)
- **Recent changes**: Hermes Phase 1/2/3, supermemory recall, continuity panel, truth grounding fixes
- **Gaps**: Agent name collisions (Zara×2, Raven×2, Phoenix×2), access_audit table empty
- **Docs**: `MAX_BRAIN_SPEC.md`, `AI_DESK_DELEGATION_PLAN.md`, `DESK_CONSOLIDATION_PLAN.md`

### 3. OpenClaw
**Status**: Live
- **Purpose**: Local AI gateway for autonomous code tasks
- **Location**: `~/Empire/openclaw/` (separate from empire-repo), port 7878
- **Backend**: `backend/app/routers/openclaw_bridge.py`, `openclaw_tasks.py`, `app/services/openclaw_worker.py`
- **Task flow**: queued → running → done/failed/paused/cancelled
- **Recent changes**: Code task routing priority fix, DB executor truth fix, CodeTaskRunner git ops hardening
- **Docs**: `openclaw_build_plan.md`, `OPENCLAW_REPO_EDIT_SELF_TEST.md`

### 4. Hermes
**Status**: Live (bounded beneath MAX)
- **Purpose**: MAX's long-running workflow assistant — handles TranscriptForge, memory bridging, browser assist, prep intake
- **Files**: `backend/app/services/max/hermes_phase1.py`, `hermes_phase2.py`, `hermes_phase3.py`, `hermes_memory.py`, `transcriptforge_hermes.py`
- **Skills**: transcriptforge-intake, transcriptforge-qc-review, transcriptforge-critical-field-check, workflow memory capture, correction pattern learning, review checklist generation
- **TranscriptForge states**: uploaded → chunking → first_chunk_processing → first_chunk_ready → processing_remaining_chunks → verification_running → needs_review → approved/corrected_and_approved/rejected

### 5. WorkroomForge
**Status**: Live
- **Purpose**: QB replacement — quotes, invoices, payments, CRM, inventory
- **Frontend**: `empire-command-center/app/workroom/` directory, `WorkroomPage.tsx`
- **Backend**: `backend/app/routers/finance.py`, `customer_mgmt.py`, `inventory.py`, `jobs.py`, `payments.py`, `quotes.py`, `quotes_v2.py`, `expenses.py`
- **Database**: `empire.db` — 113 customers, 156 inventory items, 51 vendors, 9 invoices
- **AI integration**: ForgeDesk (Kai), FinanceDesk (Sage), ClientsDesk (Elena)
- **Gaps**: contacts table unused (customers used instead), access_audit not wired

### 6. WoodCraft / CraftForge
**Status**: Partial (backend ready, frontend absent)
- **Purpose**: Woodwork & CNC business module
- **Frontend**: `empire-command-center/app/components/screens/CraftForgePage.tsx` (stub only)
- **Backend**: `backend/app/routers/craftforge.py` (15+ endpoints)
- **Recent**: woodcraft social plan in `docs/social/`
- **Gaps**: Zero frontend implementation, no product flow
- **Docs**: `docs/CRAFTFORGE_STATUS_2026-03-08.md`, `docs/CRAFTFORGE_SPEC.md`

### 7. LuxeForge
**Status**: Live
- **Purpose**: High-end service business intake portal (drapery/upholstery)
- **Frontend**: `empire-command-center/app/intake/` (intake auth + project submission), `empire-command-center/app/components/screens/LuxeForgePage.tsx`
- **Backend**: `backend/app/routers/intake_auth.py`, `luxeforge_measurements.py`, `backend/data/intake.db`
- **AI integration**: IntakeDesk (Zara), Vision analysis for measurement
- **Recent**: Photo upload/capture fix (b362e3f)

### 8. Finance / Quotes / Invoices / Payments
**Status**: Live
- **Purpose**: Full financial pipeline — 3-option proposals, PDF generation, payment tracking
- **Backend routers**: `finance.py`, `financial.py`, `quotes.py`, `quotes_v2.py`, `payments.py`, `crypto_checkout.py`, `emails.py`, `inbox.py`, `work_orders.py`
- **MAX integration**: FinanceDesk (Sage) owns invoice/expense/P&L
- **Recent**: Founder-priority quote and handoff workflow fix (7acd4ad), quote PDF service
- **Gaps**: Email sending (SendGrid not configured)

### 9. ForgeCRM
**Status**: Partial
- **Frontend**: `app/components/screens/ForgeCRMPage.tsx`
- **Backend**: `backend/app/routers/customer_mgmt.py`, `contacts.py`
- **Database**: `customers` table in empire.db (~113 records)
- **Gaps**: contacts table unused, CRM features scattered

### 10. VendorOps
**Status**: Live
- **Purpose**: Subscription renewals, add-on management, Stripe webhook alerts
- **Backend**: `backend/app/routers/vendorops.py`, `app/services/vendorops_alert_runner.py`
- **Features**: Core add-on, activation CRUD, renewal alerts, webhook alert runner, checkout
- **MAX integration**: MAX ambiguity gate, answer vendorops queries read-only
- **Recent**: `d71192c feat(vendorops): add webhooks alert runner and preferences`, `3183085 feat(vendorops): wire checkout and alert delivery`
- **Docs**: `docs/audit/` (vendorops-related)

### 11. ArchiveForge
**Status**: Live
- **Purpose**: Photo-first intake for collectible print/media (LIFE Magazine focus)
- **Frontend**: `app/components/screens/ArchiveForgePage.tsx`
- **Backend**: `backend/app/routers/archiveforge.py`, `app/routers/recovery.py`
- **Features**: V1.2 Review & Publish, MarketForge push, persistent photo storage, reboxing workflow
- **Recent**: LIFE cover search query-bound, direct LIFE intake page, photo upload/capture fix
- **Docs**: `docs/archiveforge/`

### 12. RecoveryForge
**Status**: Partial (Layer 3 classifier active)
- **Purpose**: File recovery with AI image classification
- **Frontend**: `app/components/screens/RecoveryForgeScreen.tsx`
- **Backend**: `backend/app/routers/recovery.py`, `recovery_control.py`, `app/services/ollama_bulk_classify.py`
- **Status**: Layer 3 bulk classification running (18,472 images, LLaVA/Ollama)
- **Gaps**: Frontend needs review, Layer 3 completion tracking

### 13. RelistApp
**Status**: Partial
- **Purpose**: Cross-platform relisting tool
- **Frontend**: `app/components/screens/RelistAppPage.tsx`, `RelistAppScreen.tsx`
- **Backend**: `backend/app/routers/relistapp.py`, `relist.py`
- **Recent**: RelistAppScreen added, photo upload fix
- **Gaps**: Full marketplace integration not complete

### 14. TranscriptForge
**Status**: Live
- **Purpose**: Legal/high-risk transcription pipeline with Hermes-assisted QC
- **Backend**: `backend/app/routers/transcriptforge.py`
- **Features**: 10-minute chunking, per-chunk + full-document QC, human-only approval gate, Groq Whisper
- **Hermes skills**: intake, qc-review, critical-field-check, memory capture, correction pattern learning
- **States**: uploaded → chunking → first_chunk_processing → first_chunk_ready → processing_remaining_chunks → verification_running → needs_review → approved/corrected_and_approved/rejected
- **Recent**: 11 commits (Mar 19–Apr 26) fixing incidents, triage, state machine, chunk loop, upload background tasks
- **Docs**: `backend/app/services/max/transcriptforge_*.py`

### 15. LeadForge
**Status**: Partial
- **Frontend**: `app/components/screens/LeadForgePage.tsx`, `LeadForgePageNew.tsx`
- **Backend**: `backend/app/routers/leadforge.py`, `app/services/leadforge/`
- **Docs**: `docs/LEADFORGE_SPEC.md`, `docs/leadforge/outreach_templates_by_target.md`
- **Gaps**: Outreach templates need wiring to actual send infrastructure

### 16. SocialForge
**Status**: Partial
- **Frontend**: `app/components/screens/SocialForgePage.tsx`
- **Backend**: `backend/app/routers/socialforge.py`, `social_setup.py`, `app/services/social_service.py`
- **Integrations**: Instagram (INSTAGRAM_API_TOKEN configured), Facebook (FACEBOOK_PAGE_TOKEN configured)
- **Docs**: `docs/social/instagram_setup_plan.md`, `docs/social/facebook_content_plan.md`
- **Gaps**: Semi-automatic posting needs real API wiring, content calendar not operational

### 17. SupportForge
**Status**: Partial
- **Frontend**: `app/components/screens/SupportForgePage.tsx`
- **Backend**: `backend/app/routers/supportforge_tickets.py`, `supportforge_customers.py`, `supportforge_kb.py`, `supportforge_ai.py`, `app/services/supportforge_*.py`
- **Database**: empirebox.db (SupportForge schema, empty)
- **Gaps**: KB not fully populated, AI ticket routing needs testing

### 18. MarketForge
**Status**: Partial
- **Frontend**: `app/components/screens/MarketForgePage.tsx`
- **Backend**: `backend/app/routers/marketforge_products.py`, `marketplaces.py`, `marketplace/`, `listings.py`
- **Features**: Multi-marketplace listing, inventory, Amazon/MarketF integration
- **Recent**: `489053f feat(archiveforge): wire MarketForge product publish route`
- **Gaps**: eBay API not integrated, listing optimization not complete

### 19. ApostApp
**Status**: Partial
- **Frontend**: `app/components/screens/ApostAppPage.tsx`
- **Backend**: `backend/app/routers/apostapp.py`
- **Purpose**: Document apostille & authentication (DC/MD/VA)
- **Docs**: `docs/LLC_FACTORY_APOSTILLE_FORMS_GUIDE.md`, `docs/LLC_FACTORY_NATIONWIDE_REQUIREMENTS.md`
- **Gaps**: Nationwide forms library exists, actual filing integration not wired

### 20. LLCFactory
**Status**: Partial
- **Frontend**: `app/components/screens/LLCFactoryPage.tsx`
- **Backend**: `backend/app/routers/llcfactory.py`
- **Purpose**: LLC formation & compliance (hybrid partner + DIY approach)
- **Docs**: `docs/LLC_FACTORY_FEDERAL_FORMS_GUIDE.md`
- **Gaps**: Partner integration (Northwest Registered Agents) not wired

### 21. ConstructionForge
**Status**: Partial
- **Frontend**: `app/components/screens/ConstructionForgePage.tsx`
- **Backend**: `backend/app/routers/construction.py`
- **Purpose**: Colombian real estate land development
- **Recent**: `18312be feat(empire): update construction forge products` (most recent commit before 8662bb3)

### 22. StoreFrontForge
**Status**: Partial
- **Frontend**: `app/components/screens/StoreFrontForgePage.tsx`
- **Backend**: `backend/app/routers/storefront.py`

### 23. ShipForge
**Status**: Partial
- **Frontend**: `app/components/screens/ShipForgePage.tsx`
- **Backend**: `backend/app/routers/shipping.py`, `app/services/shipping_service.py`

### 24. ContractorForge
**Status**: Partial
- **Frontend**: `app/components/screens/ContractorForgePage.tsx`
- **Backend**: `backend/app/routers/contractorforge_backend/` (separate backend)
- **Gaps**: Backend separate from main empire-repo backend

### 25. AMP (Actitud Mental Positiva)
**Status**: Partial
- **Frontend**: `empire-command-center/app/amp/`
- **Backend**: `backend/app/routers/amp.py`
- **Purpose**: Spanish-language personal development platform
- **Database**: `amp.db` (empty)
- **Gaps**: Current version "didn't capture the idea" — needs rebuild

### 26. Avatar / Presentation Mode
**Status**: Partial
- **Frontend**: `app/components/screens/PresentationScreen.tsx`
- **Backend**: `backend/app/routers/avatar.py`, `presentations.py`
- **Purpose**: 3D avatar (TalkingHead) via iframe
- **Gaps**: TalkingHead iframe needs live browser testing

### 27. Drawing Studio
**Status**: Partial
- **Frontend**: `app/components/screens/DrawingStudioPage.tsx`
- **Backend**: `backend/app/routers/drawings.py`, `custom_shapes.py`, `pattern_templates.py`
- **Purpose**: Architectural bench drawings (SVG + PDF), sewing pattern math + PDF export
- **Recent**: Drawing/studio fixes

### 28. Vision Analysis
**Status**: Live
- **Frontend**: VisionAnalysisPage (part of other screens)
- **Backend**: `backend/app/routers/vision.py`, `app/routers/photos.py`, `app/services/vision/`
- **Features**: Measurement, mockup, outline, upholstery analysis, image generation, inpainting (Stability AI)
- **AI**: Grok vision, Ollama vision router

### 29. Marketplace (MarketF / P2P)
**Status**: Partial
- **Backend**: `backend/app/routers/marketplace/`, `marketplaces.py`, `listings.py`, `relist.py`
- **Purpose**: P2P marketplace with escrow, Stripe Connect payments
- **Gaps**: Stripe Connect onboarding, dispute resolution not wired

### 30. Smart Analyzer / SimulaLab
**Status**: Partial
- **Backend**: `backend/app/api/v1/smart_analyzer.py`
- **Features**: Multi-method analysis, CPU-safe eval dataset pilot
- **Recent**: `061f7bc Add CPU-safe SimulaLab eval dataset pilot`
- **Docs**: `docs/SIMULA_LAB.md`

### 31. Notes-to-Quote / Pattern Templates
**Status**: Partial
- **Backend**: `backend/app/routers/notes_extraction.py`, `pattern_templates.py`, `custom_shapes.py`
- **Purpose**: Voice notes → quotes, sewing pattern math + PDF export
- **Frontend**: `app/components/screens/DocumentScreen.tsx`, `QuoteBuilderScreen.tsx`

---

## E. AI Model Distributor Hub

**Target design** (not yet fully implemented as a unified hub):

| Feature Area | Recommended Model | Selected Model | Free/Local | Fallback | Notes |
|---|---|---|---|---|---|
| Voice/TTS | Grok TTS Rex | Grok TTS Rex | No | None | $0.05/min |
| Transcription/STT | Groq Whisper | Groq Whisper | No | OpenAI Whisper | Fast, cheap |
| Vision/Image Analysis | Grok | Grok | No | Ollama LLaVA | Primary |
| Image Generation | Stability AI | Stability AI | No | Grok | Inpainting |
| Web Chat (general) | Grok | Grok | No | Claude Sonnet | Default desk chain |
| Telegram MAX | Grok | Grok | No | Claude Sonnet | Telegram integration |
| Email MAX | Grok | Grok | No | None | Gmail-bound |
| Code Planning | Claude Opus 4.6 | Claude Opus 4.6 | No | Grok | Atlas/CodeForge |
| Docs/Rendering | Claude Sonnet 4.6 | Claude Sonnet 4.6 | No | Grok | Raven/Analytics |
| Finance/Quotes | Grok | Grok | No | None | Sage/FinanceDesk |
| Support/Ticketing | Grok | Grok | No | None | Luna/SupportDesk |
| Marketing/Social | Grok | Grok | No | None | Nova/MarketingDesk |
| OpenClaw Tasks | OpenClaw | OpenClaw | Yes | Ollama | Local execution |
| Hermes Workflow | Grok | Grok | No | Claude Sonnet | Bounded beneath MAX |
| Transcription QC | Grok | Grok | No | None | TranscriptForge |
| Emergency Mode | Grok | Grok | No | None | Full fallback chain |

**Hermes benchmarks model performance** — per `backend/app/services/max/hermes_memory.py`
**OpenClaw executes safely** — file safety, truncation protection, critical file guard, path validation
**Emergency modes** are per-feature fallbacks, not a global mode

---

## F. Unified UI Direction (Target, Not Implementation)

- **Style**: Dark premium Command Center — deep navy/slate backgrounds, gold/amber accents
- **Shared design system**: Consistent component library across all modules
- **Layout**: Left sidebar navigation, dark panel content areas, metric widgets, routing matrices
- **Benchmark widgets**: Per-feature model performance display
- **Applies to**: Every module/product — Workroom, CraftForge, Finance, CRM, Social, etc.
- **Status**: Direction documented — NOT implemented, NOT a UI redesign task

---

## G. Architecture / Feature Schematic

**Created**: `docs/EMPIRE_SCHEMATIC_MASTER.md` — master ecosystem schematic, per-module flow maps, current vs target, homogeneity matrix, SaaS blueprint.

Key contents:
- Master ecosystem schematic (Mermaid diagram)
- Canonical module flow template
- Per-module current flow maps (MAX, OpenClaw, Hermes, AI Hub, CRM, Photo→Quote→Invoice→Payment, Finance, Drawing Studio, Workroom, CraftForge, ArchiveForge, RecoveryForge, RelistApp, VendorOps, ApostApp, SocialForge, Public surfaces)
- Current vs target notes with gaps and standardization actions
- Homogeneity matrix (nav pattern, API, persistence, upload, AI, job/task, audit, docs, SaaS)
- SaaS replication blueprint (module home, list, detail, create/edit, AI assist, activity log, metrics, docs, permissions, tests)

---

## H. Documentation Governance

1. Every module/product must have an updated documentation section in this document.
2. Any file, AI analysis doc, implementation report, status note, or major update related to a module must be referenced from that module's section.
3. Major implementation work is NOT complete until the relevant docs are updated.
4. Old docs must be marked `historical/deprecated` when superseded.
5. **Repo/runtime truth beats older prose** — if code and old docs disagree, code wins.

---

## I. Recent Change Summary (since March 18, 2026 baseline)

### MAX / AI Routing
- MAX supermemory recall added (`supermemory_recall.py`)
- Continuity panel added to Command Center
- Hermes Phase 1 (memory bridge), Phase 2 (prep intake), Phase 3 (browser assist) — all operational
- MAX truth/routing boundary fixes (multiple commits)
- Gmail truth boundaries fixed
- Cross-channel context injection to compact prompt

### OpenClaw / Code Tasks
- OpenClaw code task routing priority fix
- DB task executor truth fix
- CodeTaskRunner executable tool calls, evidence verification, git ops hardened
- OpenClaw tasks page added to Command Center

### TranscriptForge
- 11 commits post-March 18 for TranscriptForge
- Full transcription pipeline with Groq Whisper
- State machine: uploaded → chunking → first_chunk_processing → first_chunk_ready → processing → verification → needs_review
- Chunk loop fix, incident triage, stuck job recovery, upload background tasks
- Critical field check, pending skill status exactness

### VendorOps
- Webhook alert runner added
- Checkout wired
- Activation CRUD + renewal alerts
- Preferences system
- Core add-on + MAX ambiguity gate

### ArchiveForge
- V1.2 Review & Publish step added
- MarketForge publish route wired
- LIFE cover search made query-bound
- Direct LIFE intake page added
- Reboxing workflow + inventory management
- Persistent photo storage (V1.1)
- Photo upload/capture fix

### RecoveryForge
- Layer 3 classifier running (18,472 images, LLaVA/Ollama)
- RecoveryControl router added

### OpenCode / Launchers
- `opencode.json` configured (build agent, AGENTS.md/CLAUDE.md/.claude-progress.md as instructions)
- Bootstrap/launch scripts: `bootstrap.sh`, `start-empire.sh`, `launch-all.sh`, `start.sh`

### Other
- SimulaLab CPU-safe eval dataset pilot
- Founder-priority quote and handoff workflow fix
- ConstructionForge products updated
- VendorOps MAX ambiguity gate + read-only queries

---

## J. Status Matrix

| Module/Product | Current Status | Frontend Files | Backend Files | Data | AI Integration | Docs Found | Gaps | Next Action |
|---|---|---|---|---|---|---|---|---|
| Command Center | Live | page.tsx, 50+ screens | Next.js 16, API proxy | In-memory | MAX chat/continuity | PORT_REGISTRY.md | — | — |
| MAX | Live | DesksScreen, TasksScreen, MaxContinuityScreen | services/max/, routers/max/ | memories.db, token_usage.db | 18 desks, Hermes | MAX_BRAIN_SPEC.md | Agent name collisions, access_audit empty | Fix agent names, wire access_audit |
| OpenClaw | Live | OpenClawTasksPage | openclaw_bridge, openclaw_tasks, openclaw_worker | Task queue DB | Code tasks, local exec | openclaw_build_plan.md | — | — |
| Hermes | Live | (embedded in MAX) | hermes_phase{1,2,3}.py, hermes_memory.py | Transcript jobs | TranscriptForge, memory bridge | — | — | — |
| WorkroomForge | Live | workroom/ | finance, customer_mgmt, inventory, jobs, payments, quotes | empire.db | ForgeDesk, FinanceDesk, ClientsDesk | empire-ecosystem-report.md | contacts table unused | — |
| WoodCraft/CraftForge | Partial | CraftForgePage.tsx (stub) | craftforge.py | — | — | CRAFTFORGE_STATUS.md, CRAFTFORGE_SPEC.md | Zero frontend | Build CraftForge frontend |
| LuxeForge | Live | intake/, LuxeForgePage.tsx | intake_auth, luxeforge_measurements | intake.db | IntakeDesk, Vision | — | — | — |
| Finance | Live | InvoiceScreen, QuoteBuilderScreen | finance, financial, quotes, payments, inbox | empire.db | FinanceDesk | — | Email not configured | Configure SendGrid |
| ForgeCRM | Partial | ForgeCRMPage.tsx | customer_mgmt, contacts | empire.db | ClientsDesk | — | contacts table unused | Merge/deprecate contacts |
| VendorOps | Live | VendorOpsPage.tsx | vendorops.py, vendorops_alert_runner | empire.db | MAX gate | — | — | — |
| ArchiveForge | Live | ArchiveForgePage.tsx | archiveforge.py | empire.db, file storage | MAX routing | docs/archiveforge/ | — | — |
| RecoveryForge | Partial | RecoveryForgeScreen.tsx | recovery.py, recovery_control.py | empire.db, 18K images | Ollama LLaVA classifier | docs/recovery/ | Frontend review, L3 completion | Complete L3, update frontend |
| RelistApp | Partial | RelistAppPage.tsx, RelistAppScreen.tsx | relistapp.py, relist.py | empire.db | — | docs/relist/ | Marketplace wiring incomplete | Complete relist pipeline |
| TranscriptForge | Live | TranscriptForgePage.tsx | transcriptforge.py | transcriptforge/ jobs dir | Groq Whisper, Hermes | — | — | — |
| LeadForge | Partial | LeadForgePage.tsx, LeadForgePageNew.tsx | leadforge.py | empire.db | — | docs/leadforge/ | Outreach wiring | Wire templates to send infra |
| SocialForge | Partial | SocialForgePage.tsx | socialforge.py, social_setup.py | empire.db | Nova (MarketingDesk) | docs/social/ | Posting not wired | Wire Instagram/Facebook APIs |
| SupportForge | Partial | SupportForgePage.tsx | supportforge_tickets, customers, kb, ai | empirebox.db (empty) | Luna (SupportDesk) | SUPPORTFORGE_*.md | KB not populated | Populate KB, test routing |
| MarketForge | Partial | MarketForgePage.tsx | marketforge_products, marketplaces, listings | empire.db | MarketDesk | MARKETF_*.md | eBay API not integrated | Integrate eBay API |
| ApostApp | Partial | ApostAppPage.tsx | apostapp.py | — | — | LLC_FACTORY_APOSTILLE*.md | Filing not wired | Wire to apostille service |
| LLCFactory | Partial | LLCFactoryPage.tsx | llcfactory.py | — | — | docs/llc/ | Partner integration | Wire to Northwest RA |
| ConstructionForge | Partial | ConstructionForgePage.tsx | construction.py | — | — | — | — | — |
| StoreFrontForge | Partial | StoreFrontForgePage.tsx | storefront.py | — | — | — | — | — |
| ShipForge | Partial | ShipForgePage.tsx | shipping.py, shipping_service | empire.db | MarketDesk | — | Label generation not complete | Complete shipping integration |
| ContractorForge | Partial | ContractorForgePage.tsx | contractorforge_backend/ | — | — | — | Separate backend repo | — |
| AMP | Partial | amp/ | amp.py | amp.db (empty) | — | — | Rebuild needed | Rebuild to match vision |
| Avatar | Partial | PresentationScreen.tsx | avatar.py, presentations.py | — | — | — | TalkingHead untested | Browser test TalkingHead |
| Drawing Studio | Partial | DrawingStudioPage.tsx | drawings.py, custom_shapes.py, pattern_templates.py | — | — | — | — | — |
| Vision Analysis | Live | (embedded) | vision.py, photos.py, vision/ | empire.db | Grok, Ollama | — | — | — |
| Smart Analyzer | Partial | — | smart_analyzer.py | — | — | docs/SIMULA_LAB.md | — | — |

---

## K. April 1 Baseline vs Current Repo Truth

| Old Claim (empire-ecosystem-report.md, 2026-03-18) | Current Status | Classification |
|---|---|---|
| 396 commits (empire-ecosystem-report.md, 2026-03-18) | 813 commits | **Changed** |
| 22 products (empire-ecosystem-report.md) | 30+ modules/products identified in repo/docs | **Changed** (more discovered in audit) |
| 18 AI desks | 18 AI desks (unchanged) | **Still true** |
| 35 tools | 35+ tools (unchanged) | **Still true** |
| 7 databases | 7 logical DBs (empire, intake, brain×2, tool_audit, amp, empirebox) | **Still true** |
| RecoveryForge Layer 3: 18,472 images | Still active, 18,472 images | **Still true** |
| CraftForge: 15 endpoints, zero frontend | Still zero frontend | **Still true** |
| AI fallback chain: Grok→Claude→Groq→OpenClaw→Ollama | Same (unchanged) | **Still true** |
| OpenClaw: local AI gateway | Same | **Still true** |
| Port 8000 (backend), 3005 (CC) | Same | **Still true** |
| Telegram Bot embedded, @Empire_Max_Bot | Same (webhook mode now) | **Still true** |
| Stripe (test keys) configured | Same | **Still true** |
| XAI, Anthropic, Groq, OpenClaw, Telegram all configured | Same | **Still true** |
| agent name collisions (Zara×2, Raven×2, Phoenix×2) | Still present | **Still true** |
| access_audit table empty | Still empty | **Still true** |
| contacts table empty (customers used instead) | Still empty, same workaround | **Still true** |
| OpenClaw Tasks page | Now exists (OpenClawTasksPage.tsx) | **Changed** |
| MAX supermemory/continuity | Now exists | **Changed** |
| Hermes Phase 1/2/3 | Now exists | **Changed** |
| TranscriptForge | Now exists (11 commits post-baseline) | **Changed** |
| VendorOps fully wired | Now live | **Changed** |
| ArchiveForge V1.2 | Now exists | **Changed** |
| OpenCode adoption | opencode.json configured | **Changed** |

---

## L. Validation Results

```
git branch: main
git commit: da3fdf4
total commits: 813 (verified: git rev-list --count HEAD)
backend routers: 80 Python files in routers/, 70 loaded via load_router() in main.py
frontend screens: 50+ components
docs/: ~100+ .md files across multiple subdirs
PORT_REGISTRY.md: current (last updated 2026-03-09)
empire-ecosystem-report.md: March 18 baseline (396 commits)
```

---

## M. Recommended Next Documentation Tasks

1. **Create `docs/EMPIRE_MODULE_REGISTRY.md`** — detailed per-module registry (this master doc serves as the summary)
2. **Create `docs/EMPIRE_ARCHITECTURE_CURRENT.md`** — full architecture diagrams, service flows, homogeneity matrix
3. **Create `docs/EMPIRE_DOCUMENTATION_GOVERNANCE.md`** — rules for doc maintenance, versioning, deprecation
4. **Create `docs/EMPIRE_CHANGELOG_RECENT.md`** — structured changelog for commits since March 18 baseline
5. **Update PORT_REGISTRY.md** — add TranscriptForge storage path, update VendorOps status
6. **Update `docs/CRAFTFORGE_STATUS_2026-03-08.md`** — mark as historical, add current status
7. **Audit CLAUDE.md** — still references old paths (`~/Empire/`, not `~/empire-repo/`)
8. **Create per-module schematics** — Drawing Studio, ArchiveForge, TranscriptForge flow diagrams
9. **Document AI Model Distributor Hub** — formal spec for per-feature model routing table

---

*Document generated by Claude Code — repo-backed audit, 2026-04-26*
*Commit: 8662bb3 (main branch)*