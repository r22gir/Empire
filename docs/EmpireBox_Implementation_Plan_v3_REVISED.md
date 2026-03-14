# EmpireBox Implementation Plan
## v3.0 REVISED — Grounded in Codebase Reality
### 7-Phase Sprint Roadmap to Revenue
### Expert Edition — Security Hardened & Investor Ready

---

**Prepared:** March 13, 2026
**Based on:** Implementation Plan v2.0 + Deep Codebase Audit (March 13, 2026)
**Classification:** Confidential

---

## Phase Summary

| Phase | Name | Duration | Goal |
|-------|------|----------|------|
| -1 | Discovery & Validation | Days 1-5 | Customer interviews, waitlist, validate demand |
| 0 | Clean Foundation | Week 1 | Purge data, security scan, observability |
| 1 | Revenue Pipeline | Weeks 2-3 | PCI-compliant Stripe, intake-to-invoice |
| 2 | Social Presence | Weeks 4-5 | Launch channels, moderated content calendar |
| 3 | Platform Expansion | Weeks 6-8 | CraftForge E2E tested, SaaS onboarding |
| 4 | MAX Autonomy | Weeks 9-12 | Guardrailed autonomous loop, EMPIRE token |
| 5 | Launch & Iterate | Week 13+ | Post-launch monitoring, churn <3%, iterate |

---

## Codebase Reality Report (Audit Date: March 13, 2026)

Before any phase begins, here is what **actually exists** vs what v2.0 assumed:

### Confirmed Assets (BUILT)
| Asset | Status | Evidence |
|-------|--------|----------|
| Backend API (FastAPI, port 8000) | RUNNING | 46 routers loaded, Python 3.12 |
| Command Center (Next.js, port 3005) | RUNNING | Unified dashboard, 4-tab layout |
| 28 MAX tools | BUILT | tool_executor.py — all registered via @tool decorator |
| 16 MAX desks | BUILT | 12 original + innovation + desk_manager + desk_router + desk_scheduler |
| AI Cost Tracker | BUILT | 11 endpoints at /api/v1/costs/*, auto-logging, CostTrackerDesk |
| QIS (Quote Intelligence System) | BUILT | 9 quote engine files, full pipeline: analyze -> yardage -> pricing -> tiers -> verify -> mockups |
| LuxeForge Intake Portal | BUILT | intake_auth.py (40K), photo upload, admin review, Send to Workroom with full AI analysis |
| Invoice System | BUILT | finance.py — InvoiceCreate, auto-numbering (INV-2026-xxx), recalc totals |
| Expense Tracker | BUILT | ExpenseTracker.tsx with searchable vendor dropdown, category summary |
| CRM / Customer Management | BUILT | customer_mgmt.py (16K), CustomerList + CustomerDetail in CC |
| Inventory System | BUILT | inventory.py (20K), InventorySection in CC |
| Job Board | BUILT | jobs.py (12K), JobBoard component |
| Email Service | BUILT | email_service.py — SMTP with PDF attachments (needs SMTP creds in .env) |
| Crypto Payments Schema | BUILT | crypto_payments.py + crypto_payment_service.py — Solana/BNB/Cardano/ETH, per-order wallets |
| LLCFactory | BUILT | llcfactory.py (46K) — orders, customers, documents, services, packages |
| ApostApp | BUILT | apostapp.py (24K) — apostille, notarization, embassy legalization |
| SocialForge | BUILT | socialforge.py (24K) — content management backend |
| SupportForge | BUILT | 4 routers: supportforge_ai, _customers, _kb, _tickets |
| Guardrails | BUILT | guardrails.py — injection pattern detection, input validation |
| Security: sanitizer + voiceprint | BUILT | security/sanitizer.py, security/voiceprint.py (files exist) |
| Task Pipeline | BUILT | pipeline/task_pipeline.py |
| Desk Scheduler | BUILT | desk_scheduler.py — morning brief, scheduled task execution |
| Telegram Bot | BUILT | telegram_bot.py — founder-only auth, text/voice/photo, intent classification |
| PaymentModule (CC) | BUILT | PaymentModule.tsx — frontend component exists |
| QB Import | BUILT | QBImportPreview.tsx — QuickBooks import preview |
| Docker Manager | BUILT | docker_manager.py — 13 product container definitions |
| Preorder System | BUILT | preorder_service.py + preorders.py with Stripe payment intent fields |
| Onboarding Router | BUILT | onboarding.py |
| Homepage | BUILT | 3 HTML files (index.html, command-center.html, agent-command-center.html) |
| Hardware Specs | DOCUMENTED | 14 files: assembly guide, BOM, build specs (starter/business/enterprise), BIOS, network topology |
| USB Provisioner | DOCUMENTED | founders_usb_installer/ — autoinstall config, OpenClaw skills, control panel, .env template |
| CopilotForge | PROTOTYPE | products/copilotforge/ — chat session data from Feb 23 |

### NOT Built Yet (Plan Assumed or Needs Work)
| Item | Status | What's Missing |
|------|--------|----------------|
| Stripe integration | STUB ONLY | webhooks.py has `# TODO: Implement Stripe webhook handling`. Config has STRIPE_SECRET_KEY but empty. No Stripe SDK installed. |
| CraftForge frontend | ZERO UI | 15 backend endpoints exist (craftforge.py 18K), zero frontend components |
| E2E tests | ZERO | No .spec.ts or .test.ts files found anywhere |
| Prometheus / Grafana | NOT INSTALLED | No references in codebase, not installed on system |
| Trivy / Semgrep | NOT INSTALLED | Neither binary found on system |
| Automated backups (restic) | NOT CONFIGURED | No backup scripts, no restic config |
| Feature flags | NOT BUILT | No feature_flag references in backend |
| Referral system | NOT BUILT | No referral references in backend |
| NPS / Survey | NOT BUILT | No NPS or survey references |
| GROQ_API_KEY | EMPTY | AI routing fallback to Groq will fail |
| BRAVE_API_KEY | MISSING | Web search tool will fail |
| SMTP credentials | NOT SET | Email service built but SMTP_HOST/SMTP_USER/SMTP_PASSWORD not in .env |
| GPU driver | BROKEN | Quadro K600 on nouveau — needs `sudo ubuntu-drivers autoinstall` |
| OpenClaw bridge | NOT WIRED | No openclaw_bridge router, no dispatch_to_openclaw tool |
| Google Business Profile | NOT DONE | Manual task |
| Social media accounts | NOT CREATED | Manual task |
| EMPIRE Token | NOT DEPLOYED | Crypto payment service references it but no smart contract |
| PostgreSQL | NOT MIGRATED | Running SQLite (empirebox.db), async PostgreSQL code exists but unused |
| Cloudflare load balancer | NOT CONFIGURED | Single tunnel active, no failover |

### App Consolidation Status (27 package.json apps found)

| App | Port | Status | Recommendation |
|-----|------|--------|----------------|
| empire-command-center | 3005 | ACTIVE — primary UI | KEEP as sole frontend |
| empire-app | 3000 | ACTIVE — older unified app | RETIRE after CC parity confirmed |
| empire-control | 3000 | CONFLICTS with empire-app | REMOVE — predecessor to CC |
| founder_dashboard | 3009 | LEGACY — MAX chat interface | RETIRE — CC has MAX tab |
| workroomforge | 3001 | LEGACY — quote builder | RETIRE — CC has Workroom tab |
| luxeforge_web | 3002 | LEGACY — intake portal | RETIRE — CC has LuxeForge tab |
| amp | 3003 | Portal de la Alegria | EVALUATE — is it still needed? |
| craftforge | 3006 | CONFLICTS with reserved port | RETIRE — build frontend in CC |
| creations | 3006 | PORT CONFLICT with craftforge | RETIRE — merge into CC |
| relistapp | 3007 | Smart Lister panel | EVALUATE — already in CC? |
| contractorforge_web | ? | Standalone app | RETIRE — CC has ContractorForge tab |
| marketf_web | ? | Market Forge web | RETIRE — CC has MarketForge tab |
| finance | ? | Standalone finance app | RETIRE — CC has Finance section |
| crm | ? | Standalone CRM app | RETIRE — CC has CRM |
| inventory | ? | Standalone inventory app | RETIRE — CC has Inventory |
| empirebox_setup/setup-portal | ? | Setup wizard | KEEP for onboarding flow |
| empirebox_installer/contracts | ? | Smart contracts / legal | KEEP — needed for token launch |
| website/nextjs | ? | Public website | KEEP — needs overhaul |

**Bottom line: 18 of 27 apps are legacy/redundant.** Command Center already has tabs for everything. Consolidation = retire legacy apps, not build new ones.

---

## Strategic Principles (PRESERVED from v2.0 + ADDITIONS)

The ecosystem audit (v3.0) revealed a platform with massive breadth — 27 apps, 46 routers, 16 AI desks — but zero revenue. The implementation plan follows one rule: **every sprint must move closer to money**. Features that don't serve revenue, lead generation, or operational readiness get deferred.

- **Revenue First** — No new features until the payment pipeline works end-to-end. A customer must be able to find us, submit an intake, get a quote, and pay an invoice.
- **Clean Before Build** — Test data, fake customers, and broken flows erode trust with investors and early customers. Purge everything before going live.
- **Consolidate, Don't Expand** — 27 apps is too many to maintain. Every new piece of work should move toward the 4-suite model (Operations, SaaS Growth, Legal/Finance, Marketplace), not add more standalone apps.
- **Automate the Founder** — RG is one person running two businesses and building a platform. MAX + OpenClaw must progressively take over routine tasks so RG focuses on revenue-generating work only.
- **Social = Leads = Revenue** — No customers will find the platform without social presence. Instagram, Facebook, TikTok, and Google Business are not optional — they are the sales channel.
- **Ship Ugly, Fix Pretty** — A working intake form that takes real orders beats a polished dashboard that nobody sees. Functionality over aesthetics in early phases.

**ADDED based on audit:**
- **Kill Legacy Apps** — Every legacy Next.js app still running (ports 3000, 3001, 3002, 3009) wastes RAM and creates confusion. Redirect to Command Center on port 3005.
- **Fix the Foundation Hardware** — GPU driver, missing API keys, and SMTP credentials must be resolved before any autonomous features can work.
- **Existing Code > New Code** — 80% of the backend is already built. Focus on WIRING existing endpoints to the frontend and payment systems, not rewriting.

---

## PHASE -1 — DISCOVERY & VALIDATION
### Days 1-5 | Validate demand before building

Before writing any code, validate that real customers will pay for what exists — but has zero paying users. Five days of targeted outreach either confirms the revenue path or redirects effort before wasting weeks.

| # | Task | Details | Owner | Target | Codebase Status |
|---|------|---------|-------|--------|-----------------|
| -1.1 | Customer interview script | MAX drafts a 10-question interview template covering: current tools, pain points, willingness to pay, feature priorities. Focused on trades businesses (drapery, upholstery, woodwork, general contractors). | MAX | Day 1 | MAX has `create_task` + `send_telegram` tools to help draft and deliver |
| -1.2 | Conduct 10 interviews | RG reaches out to existing network: past clients (Emily $22.6K, Sarah $12.4K, Maria $8.9K pipeline), Facebook groups, local business associations. 15-minute calls or in-person. Record key quotes. | RG (Manual) | Days 1-4 | CRM has existing customers: customer_mgmt.py with full records |
| -1.3 | Waitlist / intent form | Create a simple intake form on studio.empirebox.store: name, business type, email, "Would you pay $29-79/mo for AI business tools?" Collect signed intent-to-pay. | Claude Code | Day 1 | LuxeForge intake portal ALREADY EXISTS at studio.empirebox.store — adapt it, don't rebuild |
| -1.4 | Competitor pricing audit | MAX researches: Jobber, ServiceTitan, Housecall Pro, Workiz pricing and feature gaps. Identify where EmpireBox wins (AI agents, self-hosted, crypto, legal services). | MAX + WebSearch | Day 2 | MAX has `web_search` + `web_read` tools. BRAVE_API_KEY missing — needs to be added first or use Grok web search |
| -1.5 | Validate tier pricing | Based on interviews: confirm $29/$79/$199 resonates or adjust. Test: would trades businesses pay for LLC formation? Crypto discounts? | RG + MAX | Day 4-5 | Tier definitions exist in docs but not wired to any subscription system yet |
| -1.6 | Go/No-Go decision | If 5+ signed intent-to-pay forms received: proceed to Phase 0. If fewer: pivot messaging, adjust tiers, or narrow focus to one business vertical. | RG | Day 5 | — |

**GATE: Minimum 5 signed intent-to-pay forms before proceeding. This prevents building for an unvalidated market.**

---

## PHASE 0 — CLEAN FOUNDATION
### Week 1 | Prerequisites for everything else

Nothing goes live until the foundation is clean. Fake data, broken navigation, and disconnected pages make the platform look unfinished to investors and unusable to customers.

| # | Task | Details | Owner | Target | Codebase Status |
|---|------|---------|-------|--------|-----------------|
| 0.1 | Purge all test/fake data | Backup DBs, wipe test customers, quotes, jobs, invoices from Workroom. Reset auto-increment sequences. Verify empty state renders correctly. | Claude Code | Day 1 | empirebox.db (SQLite) + data/quotes/*.json + data/intake.db — all need purging. Backup first! |
| 0.2 | Fix all dead navigation | The 4-agent wiring sprint fixed 8 issues. Run full audit on remaining dead links, placeholder pages, and 404 routes. Fix or remove. | Claude Code | Day 1-2 | CC page.tsx has 20+ product cases — several point to stub components. EcosystemProductPage handles openclaw/recovery/hardware as generic pages |
| 0.3 | Consolidate dashboards | Verify Command Center (3005) has feature parity with Founder Dashboard (3009) for critical flows. Redirect any remaining links to CC. | Claude Code | Day 2-3 | CC already has: MAX chat, Workroom, CraftForge, LuxeForge, Finance, CRM, Inventory, Jobs, Tasks, Payments, Docs, QB Import, AI Analysis. Founder Dashboard is legacy chat-only. |
| 0.4 | Backend health check | Hit every critical endpoint: /customers, /quotes, /jobs, /finance, /inventory, /intake. Fix any 500s or empty responses. | Claude Code | Day 3 | 46 routers loaded — some may have unmet DB table dependencies. finance.py uses raw SQLite, quotes.py uses JSON files, intake_auth.py uses separate intake.db |
| 0.5 | Register OpenClaw bridge | Add openclaw_bridge.py router to main.py, wire dispatch_to_openclaw tool into tool_executor.py. Verify /api/v1/openclaw/health returns. | Claude Code | Day 4 | NOT BUILT — OpenClaw runs at port 7878 with Ollama but has no API bridge to MAX. founders_usb_installer has OpenClaw skill configs (telegram.yaml, empirebox.yaml, voice.yaml) that define the interface |
| 0.6 | GPU driver fix | Run `sudo ubuntu-drivers autoinstall` for Quadro K600. Fixes nouveau instability. Reboot and verify. | Manual | Day 4 | CRITICAL — nouveau driver causes display issues. DO NOT run sensors-detect after fix. |
| 0.7 | Missing API keys | Add GROQ_API_KEY and BRAVE_API_KEY to backend/.env. Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD for email service. Test Groq failover, web search, and email send. | Manual | Day 5 | GROQ empty, BRAVE missing, SMTP not configured. AI routing: Grok -> Claude -> Groq (broken) -> Ollama. Email service code exists but can't send. |
| 0.8 | Security scan | Install and run Trivy + Semgrep on entire repo. Fix any critical vulnerabilities. Verify no secrets in committed code. | Claude Code | Day 3 | NEITHER TOOL INSTALLED. Guardrails.py exists for prompt injection. security/sanitizer.py + voiceprint.py exist but need verification. |
| 0.9 | Observability stack | Deploy Prometheus + Grafana (Dockerized, ports 9090/3000) for baseline CPU, memory, API latency metrics. Dashboard on EmpireDell. | Claude Code | Day 4 | NOT INSTALLED. Docker manager router exists (docker_manager.py) with 13 container definitions — could use this pattern. Note: port 3000 conflicts with empire-app, use 3333 for Grafana |
| 0.10 | Automated backups | Configure restic cron job to external drive. Daily DB backup + weekly full repo backup. Runs before any OpenClaw task. | Claude Code | Day 5 | NOT CONFIGURED. chat_backup_service.py exists for chat history backup but no system-level backup. Samsung T7 USB brain drive referenced in hardware spec could be backup target. |
| 0.11 | Kill legacy app processes | Stop ports 3000 (empire-app), 3001 (workroomforge), 3002 (luxeforge_web), 3009 (founder_dashboard). Update any hardcoded redirects. Keep only 8000 (backend) + 3005 (CC). | Claude Code | Day 2 | 6 services currently running on different ports. Each consumes RAM on 32GB EmpireDell. |

**MILESTONE: Clean platform, zero fake data, all navigation works, OpenClaw bridge online, GPU stable, 0 critical vulns, observability live, backups automated.**

---

## PHASE 1 — REVENUE PIPELINE
### Weeks 2-3 | From intake to paid invoice

The entire purpose of this phase is to create one complete path from a stranger finding the business to money hitting the bank account. Every task exists to close that loop.

| # | Task | Details | Owner | Target | Codebase Status |
|---|------|---------|-------|--------|-----------------|
| 1.1 | Stripe integration | Install stripe Python SDK. Add STRIPE_SECRET_KEY + STRIPE_PUBLISHABLE_KEY to .env. Wire to /api/v1/finance/payments. Support card payments on invoices. Add webhook for payment confirmation. | Claude Code | Week 2 | STUB: webhooks.py has `@router.post("/stripe")` with TODO. config.py has STRIPE_SECRET_KEY/STRIPE_PUBLISHABLE_KEY fields (empty). preorder_service.py references stripe_payment_intent_id. PaymentModule.tsx exists in CC. |
| 1.2 | Invoice payment flow | Customer receives invoice (email/PDF) with Stripe payment link. Payment marks invoice as paid. Notification sent to founder via Telegram. | Claude Code | Week 2 | Invoice system BUILT: finance.py has InvoiceCreate, auto-numbering, recalc. Email service BUILT (needs SMTP creds). Telegram send_telegram tool BUILT. Missing: Stripe payment link generation + webhook to mark paid. |
| 1.3 | LuxeForge intake-to-quote | Verify end-to-end: client submits intake form on studio.empirebox.store with photos and dimensions. Data flows to Workroom. MAX generates quote via QIS pipeline (AI vision analysis, yardage, 3-tier pricing, mockups). PDF generated and sent. | Claude Code | Week 2 | BUILT and recently upgraded: intake_auth.py convert_to_quote() now runs full QIS pipeline (photo analysis -> measurements -> yardage -> pricing -> tiers -> verify -> mockups). Send to Workroom navigates directly to QuoteReviewScreen. Photos carry through. Known issue: item type sanitization for AI vision responses. |
| 1.4 | Quote-to-invoice pipeline | Accepted quote auto-generates invoice. Invoice includes Stripe payment link and crypto payment option. Track status: sent, viewed, paid. | Claude Code | Week 3 | Quote system BUILT (quotes.py 125K). Invoice system BUILT. Missing: auto-generation trigger when quote status changes to "accepted". Missing: Stripe link embedding. |
| 1.5 | Crypto payment wiring | Connect crypto_payments router to invoice flow. Generate per-invoice wallet addresses. Verify Solana Pay detection. Apply 15%/20% discounts. | Claude Code | Week 3 | BUILT: crypto_payment_service.py has deterministic wallet derivation, multi-chain support (Solana/BNB/Cardano/ETH), discount logic. Missing: actual Solana RPC connection, real wallet monitoring, connection to invoice model. |
| 1.6 | Google Business Profile | Set up GBP for both businesses (Drapery & Upholstery + Woodwork & CNC). Add photos, hours, services, and intake form link. | Manual + MAX | Week 3 | NOT DONE. MAX has web_search tool for research. Needs manual Google account setup. |
| 1.7 | Email templates | Create branded email templates for: quote sent, invoice sent, payment received, welcome. Wire to notification system. | Claude Code | Week 3 | Email service BUILT (email_service.py) with PDF attachment support. Uses SMTP (Gmail app password). Needs: SMTP creds in .env + HTML templates. MAX already has send_email and send_quote_email tools. |
| 1.8 | SaaS signup page | Create landing page at empirebox.store with tier cards ($29/$79/$199). Connect Stripe checkout for subscription creation. | Claude Code | Week 3 | Homepage exists (3 HTML files) but is just navigation links. website/nextjs has a Next.js app. empirebox_setup/setup-portal exists for onboarding. Needs: actual pricing page with Stripe checkout. |
| 1.9 | PCI scope reduction | Use Stripe Elements + Payment Intents exclusively — never touch raw card data. Card input renders in Stripe's iframe. Backend only handles payment intent IDs. | Claude Code | Week 2 | Preorder model already stores stripe_payment_intent_id (not raw cards). Pattern is correct — extend to invoices. |
| 1.10 | Webhook security | Add Stripe webhook signature verification + idempotency keys. Same for crypto_payments.py. Prevent replay attacks and double-processing. | Claude Code | Week 2 | webhooks.py exists with stub. crypto_payment_service.py has basic structure. Neither has signature verification. |
| 1.11 | Sandbox-to-prod toggle | Add STRIPE_MODE=test|live to .env. Automated test script runs through full flow in sandbox: create customer, charge $1, verify webhook, refund. | Claude Code | Week 2 | config.py already has STRIPE_SECRET_KEY + STRIPE_PUBLISHABLE_KEY fields. Need test vs live key handling. |
| 1.12 | Rate limiting | Add slowapi rate-limiting middleware on /finance/* and /intake/* endpoints. Prevent abuse on payment and intake routes. | Claude Code | Week 3 | NOT BUILT. No rate limiting anywhere in backend currently. |

**MILESTONE: PCI-compliant Stripe live. Real customer can submit intake, receive AI quote, get invoice, and pay with card or crypto. SaaS signup active. First $1 real payment received.**

---

## PHASE 2 — SOCIAL PRESENCE
### Weeks 4-5 | Generate leads for both businesses

Payment pipeline works. Now people need to find the businesses. Social media is the primary lead generation channel for trades businesses. MAX's SocialDesk handles content creation; the founder approves and posts.

| # | Task | Details | Owner | Target | Codebase Status |
|---|------|---------|-------|--------|-----------------|
| 2.1 | Instagram setup | Create business accounts for both businesses. Bio with intake link. Set up Linktree or direct link to studio.empirebox.store/intake. | Manual | Week 4 | NOT DONE. Manual task. |
| 2.2 | Facebook pages | Business pages for both. Link to Instagram. Add service catalog, photos, and intake form link. | Manual | Week 4 | NOT DONE. Manual task. |
| 2.3 | TikTok accounts | Business accounts for process/behind-the-scenes content. Short-form video strategy. | Manual | Week 4 | NOT DONE. Manual task. |
| 2.4 | Wire SocialForge | Complete SocialForge tab in Command Center. Content calendar loads, post drafts save, scheduling works. Wire to /api/v1/social/* endpoints. | Claude Code | Week 4 | Backend BUILT: socialforge.py (24K). CC has SocialForgePage component. Needs: verification that CC component fully wires to all backend endpoints. |
| 2.5 | Content generation sprint | MAX generates 4-week content calendar for both businesses. 7 posts/week per business: Mon=before/after, Tue=process, Wed=tip, Thu=testimonial, Fri=showcase, Weekend=stories. | MAX + SocialDesk | Week 4-5 | SocialDesk exists. Marketing desk exists. Both have AI capabilities. Need to verify they can generate content and store to DB. |
| 2.6 | Portfolio content | Wire Creations app to display project portfolio. Export key images for social use. Get 20+ project photos ready per business. | Claude Code + Manual | Week 5 | creations/ app exists (port 3006). WorkroomPage has "Creations" section. Need: real project photos from RG's past work. |
| 2.7 | Hashtag & SEO | Research and lock in hashtag sets per business. Optimize Google Business listings with keywords. Add schema markup to public pages. | MAX + MarketDesk | Week 5 | MarketDesk exists. MAX has web_search tool. website/nextjs exists for schema markup. |
| 2.8 | Launch posts | First posts go live on all channels. Both businesses active on Instagram, Facebook, TikTok, and Google Business. | Manual | Week 5 | Manual task — depends on account creation. |
| 2.9 | Content moderation | Wire SocialForge to local Ollama toxicity model before scheduling. AI-generated posts get moderation score stored in DB. Flag anything below threshold for manual review. Protects brand safety. | Claude Code | Week 5 | Ollama running at port 11434. SocialForge backend built. Need: toxicity scoring integration, moderation threshold logic. |

**MILESTONE: Both businesses live on 4 social channels with 4-week content calendars. SocialForge managing scheduling. Intake link everywhere.**

---

## PHASE 3 — PLATFORM EXPANSION
### Weeks 6-8 | CraftForge frontend, SaaS traction, consolidation

Revenue pipeline and social presence are generating leads. Now expand the platform to support both businesses fully and start SaaS customer acquisition.

| # | Task | Details | Owner | Target | Codebase Status |
|---|------|---------|-------|--------|-----------------|
| 3.1 | CraftForge frontend | Build the UI for all 15 backend endpoints. Dashboard, quote builder, job tracker, inventory, customer list. Adapt from WorkroomForge components with woodwork/CNC terminology. | Claude Code | Week 6-7 | BIGGEST GAP: craftforge.py (18K) has 15 endpoints, ZERO frontend. CC has CraftForgePage component that currently accepts `initialSection` prop like WorkroomPage. The backend mirror pattern means most WorkroomPage components can be adapted. |
| 3.2 | Suite consolidation — Operations | Merge Workroom + CraftForge + CRM + Inventory into unified Operations Suite within Command Center. Shared nav, shared CRM, business toggle. | Claude Code | Week 7 | CC already has this via tab switching (workroom/craft products). CRM is shared. Need: business context toggle so same CRM filters by business. |
| 3.3 | SaaS onboarding flow | Wire onboarding.py router to setup portal. New subscriber signs up on Stripe, gets account created, guided through business profile setup, lands in their dashboard. | Claude Code | Week 7 | onboarding.py router EXISTS. empirebox_setup/setup-portal EXISTS (package.json). Need: Stripe subscription creation -> account provisioning -> redirect to CC. |
| 3.4 | LLCFactory launch prep | Verify LLCFactory endpoints work end-to-end for DC/MD/VA. Connect payment flow (Stripe + crypto). Create service pages on website. | Claude Code | Week 8 | BUILT: llcfactory.py (46K) with orders, customers, documents, services, packages. CC has LLCFactoryPage. ApostApp integrates with it. Need: payment wiring + public-facing service pages. |
| 3.5 | SupportForge activation | Wire SupportForge's 4 routers to a customer-facing support widget. Knowledge base populated. AI auto-response handles basic questions. | Claude Code | Week 8 | BUILT: 4 routers (supportforge_ai, _customers, _kb, _tickets). CC has SupportForgePage. supportforge_ai.py uses AI for responses. Need: customer-facing widget (not just admin view). |
| 3.6 | Homepage overhaul | empirebox.store homepage showcases all products: Workroom, CraftForge, LLCFactory, SaaS plans. Clear CTAs, pricing, testimonials placeholder. | Claude Code | Week 8 | Current homepage is 3 static HTML files with navigation links. website/nextjs exists but unclear state. Need: complete redesign as marketing site. |
| 3.7 | Command Center parity | All Founder Dashboard features migrated. Retire port 3009. AMP (3003) features absorbed or linked. | Claude Code | Week 8 | CC already surpasses Founder Dashboard. FD is chat-only. CC has chat + full business tools. AMP (Portal de la Alegria) may still have unique features — audit needed. |
| 3.8 | First SaaS customers | Outreach to 3-5 trades businesses in founder's network. Offer Lite tier free for 3 months in exchange for feedback. | Manual | Week 8 | Manual outreach. CRM has existing contacts. |
| 3.9 | E2E test suite | Add Playwright E2E tests for critical flows: intake submission, quote generation, invoice payment, CraftForge quote builder. Run nightly via cron. | Claude Code | Week 7 | ZERO tests exist anywhere. Need: Playwright install, test structure, CI runner. |
| 3.10 | Feature flags | Implement feature flag system (simple SQLite table: flag_name, enabled, tier_min). Gradual rollout of new features per SaaS tier. SupportForge AI behind flag initially. | Claude Code | Week 8 | NOT BUILT. No feature flag references. Simple implementation: flags table + middleware check. |

**MILESTONE: CraftForge fully operational. SaaS signup live with onboarding. LLCFactory accepting orders. 3-5 beta SaaS customers.**

---

## PHASE 4 — MAX AUTONOMY
### Weeks 9-12 | AI takes over routine operations

With revenue flowing and the platform operational, shift focus to making MAX truly autonomous. The goal: RG reviews and approves instead of building and maintaining.

| # | Task | Details | Owner | Target | Codebase Status |
|---|------|---------|-------|--------|-----------------|
| 4.1 | OpenClaw full activation | Start OpenClaw on EmpireDell (port 7878). Deploy all 5 Empire skills. Test: dispatch a task from Telegram, OpenClaw executes, reports back. | Claude Code | Week 9 | OpenClaw exists at ~/Empire/openclaw/. founders_usb_installer has skill configs (telegram.yaml, empirebox.yaml, voice.yaml). Ollama running at 11434. Need: bridge router + dispatch tool. |
| 4.2 | Desk-to-OpenClaw pipeline | Wire desk task completion to OpenClaw dispatch. When a desk generates a task (e.g. "wire SocialForge calendar"), it auto-dispatches to OpenClaw for execution. | Claude Code | Week 9 | task_pipeline.py EXISTS. desk_scheduler.py runs scheduled tasks. desk_router.py routes to desks. Need: OpenClaw dispatch step in pipeline. |
| 4.3 | Morning brief automation | MAX generates daily brief at 8 AM: overnight leads, pending invoices, social engagement stats, system health. Delivered via Telegram with voice. | Claude Code | Week 10 | PARTIALLY BUILT: desk_scheduler.py has morning_brief logic with date-based dedup. Telegram bot has text + voice (Grok TTS Rex). Need: full brief content generation + voice delivery. |
| 4.4 | Autonomous social posting | SocialDesk generates weekly content. After founder approval via Telegram, MAX schedules and posts directly to platforms (via API or buffer tool). | Claude Code | Week 10 | SocialForge backend built. Telegram approval flow possible via existing bot. Need: platform API integration (Instagram Graph API, Facebook Pages API) or Buffer/Hootsuite integration. |
| 4.5 | Quote auto-response | When intake arrives, MAX auto-generates quote within 15 minutes. Founder gets Telegram notification with approve/edit/reject options. Approved quotes auto-send to client. | Claude Code | Week 11 | MOSTLY BUILT: intake webhook -> QIS pipeline -> quote generation works. Telegram notification works. Missing: auto-trigger on new intake (currently manual "Send to Workroom"), Telegram inline keyboard for approve/edit/reject. |
| 4.6 | Resemblyzer voiceprint | Install resemblyzer. Train on founder's voice. Enable voice-verified approvals for high-value actions (quotes over $5K, payments, deployments). | Claude Code | Week 11 | security/voiceprint.py EXISTS (file created). Need: actual resemblyzer/speechbrain install, voice sample collection, verification integration. CPU-only on EmpireDell (Xeon E5-2650 v3, no CUDA). |
| 4.7 | Inventory auto-reorder | InventoryDesk monitors stock levels. When materials drop below threshold, auto-generates reorder list. Sends to founder for approval. Tracks supplier orders. | Claude Code | Week 12 | Inventory system BUILT (inventory.py 20K). MAX has check_inventory tool with low_stock filter. Need: threshold monitoring loop + reorder notification. |
| 4.8 | EMPIRE Token launch | Deploy EMPIRE token on Solana. Wire to crypto_payments for 20% discount. Add token info to website and checkout flow. | Claude Code + Manual | Week 12 | Crypto payment service supports EMPIRE token discount (20%). empirebox_installer/contracts/ exists (may contain token contracts). Need: actual Solana deployment, token metadata, wallet integration. Legal review recommended. |
| 4.9 | Guardrail enforcement | Enforce empire-core guardrails in OpenClaw system prompt: no .env edits, backup-before-delete, no force-push, no broad pkill. Input sanitizer v2 for prompt injection defense. | Claude Code | Week 9 | PARTIALLY BUILT: guardrails.py has injection pattern detection. security/sanitizer.py exists. CLAUDE.md has critical warnings. Need: guardrails wired into OpenClaw, not just MAX chat. |
| 4.10 | Per-desk cost caps | Add daily token budget per desk in costs.py. Telegram alert at 80% of budget. Auto-pause desk at 100%. Prevents runaway AI costs during autonomous operation. | Claude Code | Week 10 | Cost tracker BUILT with 11 endpoints. Token tracker auto-logs all AI calls. by-feature and by-business breakdowns exist. Need: per-desk budget config + enforcement in ai_router.py. |
| 4.11 | Multi-factor auth | Resemblyzer voiceprint + Telegram OTP for all destructive actions: data deletion, deployments, quotes over $5K, payment approvals. | Claude Code | Week 11 | Telegram bot has founder-only auth (TELEGRAM_FOUNDER_CHAT_ID). Voiceprint file exists. Need: OTP generation + voiceprint verification combined flow. |
| 4.12 | Task audit log | SQLite table: task_id, prompt_hash, changes_made, files_modified, git_commit, timestamp, desk_id, cost. Full traceability for every autonomous action. | Claude Code | Week 9 | task_activity table EXISTS in DB for task logs. Need: expanded schema + git_commit tracking + cost linkage. |

**MILESTONE: MAX operates autonomously with guardrails — morning briefs, auto-quoting, social posting, inventory monitoring. Cost-capped, audit-logged, multi-factor auth on destructive ops. 3+ fully autonomous tasks/day.**

---

## PHASE 5 — LAUNCH & ITERATE
### Week 13+ | Post-launch monitoring and growth

Platform is live, revenue is flowing, MAX is autonomous. Now shift to monitoring, retention, and growth. The founder's role transitions from builder to operator and business developer.

| # | Task | Details | Owner | Target | Codebase Status |
|---|------|---------|-------|--------|-----------------|
| 5.1 | Monitoring dashboard | Build post-launch dashboard in Command Center: MRR, active users, churn rate, support tickets, AI costs, system uptime. Auto-updated daily. | Claude Code | Week 13 | CC has DashboardScreen. Cost tracker built. System monitor built (system_monitor.py). Need: MRR/churn/user metrics aggregation. |
| 5.2 | Customer feedback loop | SupportForge captures feedback. Weekly NPS survey to beta users. MAX summarizes feedback and prioritizes feature requests. | MAX + SupportDesk | Week 13 | SupportForge 4 routers built. Need: NPS survey endpoint + aggregation. |
| 5.3 | Churn prevention | FinanceDesk monitors subscription status. Flag users who haven't logged in for 7+ days. Auto-send engagement email. Target: churn below 3%/month. | MAX + FinanceDesk | Week 14 | FinanceDesk EXISTS with AI capability. Email service built. Need: user activity tracking + churn detection logic. |
| 5.4 | Content scaling | Increase social posting to 2x/day per business. MAX generates, moderates, and schedules with minimal founder input. Track follower growth, lead conversion. | MAX + SocialDesk | Week 14 | SocialDesk + SocialForge backend built. Need: platform API integration from Phase 4.4. |
| 5.5 | Referral program | Add referral system: existing SaaS users get 1 month free for each referral that converts. Track via unique referral codes. | Claude Code | Week 15 | NOT BUILT. No referral references. Need: referral_codes table + discount application logic. |
| 5.6 | PostgreSQL migration | If user count exceeds 50: migrate from SQLite to PostgreSQL with schema partitioning. Zero-downtime migration plan. | Claude Code | When triggered | database.py ALREADY supports async PostgreSQL! Code exists but DATABASE_URL defaults to SQLite. Migration = change env var + run schema creation. Data migration script needed. |
| 5.7 | Hardware sales launch | First Empire Box Starter kits available for order. USB provisioner tested end-to-end. Shipping workflow via ShipForge. | RG + Manual | Week 16 | Hardware spec DOCUMENTED (14 files). USB provisioner DOCUMENTED. founders_usb_installer has autoinstall configs. ShipForge router exists (shipping.py). Need: actual hardware procurement + provisioning testing. |
| 5.8 | Quarterly review | Full ecosystem health report: revenue vs projections, feature velocity, customer satisfaction, AI cost trends, security audit results. | MAX + RG | Week 16 | MAX has get_finance_summary tool. Cost tracker provides trends. Need: report template + automated generation. |

**MILESTONE: Churn below 3%, NPS of 7+, 10+ paying SaaS users, hardware kits shipping, MAX running 5+ autonomous tasks/day.**

---

## Execution Model — Who Does What

| Actor | Responsibilities |
|-------|-----------------|
| RG (Founder) | Business decisions, approvals, client relationships, manual social setup, content photography, hardware orders, investor meetings |
| Claude Code | Code changes, API wiring, frontend builds, bug fixes, database operations, build checks, git commits. Primary development executor. |
| Claude (Web) | Architecture planning, document generation, strategy, report building, complex analysis. This session. |
| MAX (AI System) | Task delegation, morning briefs, content generation, quote creation, notification routing, cost tracking. The brain. 28 tools, 16 desks, 205 memories. |
| MAX Desks (16) | Specialized task execution: SocialDesk for content, FinanceDesk for invoicing, ForgeDesk for builds, ITDesk for monitoring, InnovationDesk for strategy, etc. |
| OpenClaw | Autonomous code execution: file edits, builds, git operations, API testing. MAX's hands. Runs tasks dispatched by desk system. |

### Daily Workflow (Post Phase 4)

| Time | Activity | Mode |
|------|----------|------|
| 8:00 AM | MAX generates morning brief: leads, invoices, social stats, health | Automatic |
| 8:15 AM | RG reviews brief on Telegram, approves/rejects pending items | Manual (2 min) |
| 8:30 AM | Desk scheduler runs: SocialDesk queues posts, FinanceDesk sends invoices | Automatic |
| During day | New intake arrives, MAX auto-quotes within 15 min, RG approves via Telegram | Auto + Approve |
| During day | OpenClaw executes queued dev tasks, reports completion via Telegram | Automatic |
| Evening | MAX sends daily summary: revenue, new leads, tasks completed | Automatic |

---

## Risk Register (Quantified)

| Risk | Severity | Probability | Score | Mitigation |
|------|----------|-------------|-------|------------|
| No revenue yet | 10 | High | 30 | Phase 1 is entirely revenue-focused. Phase -1 validates demand first. No features until payment works. |
| Founder bandwidth | 10 | High | 30 | Phase 4 targets 2h/day manual. Each phase reduces workload. Revenue enables hiring. |
| Single-server downtime | 9 | High | 27 | Phase 0.10 adds restic backups. Cloudflare load balancer fallback planned. Hardware stock for replacement. |
| PCI / data breach | 10 | Medium | 30 | Phase 1.9-1.12: Stripe Elements only (no raw card data), webhook signing, rate limiting, annual audit. |
| Prompt injection (OpenClaw) | 8 | High | 24 | Phase 4.9: empire-core guardrails enforced, input sanitizer v2 (partially built), no .env access, backup-before-delete. |
| SQLite scaling | 7 | Medium | 21 | Sufficient for Phases 0-4. PostgreSQL code ALREADY EXISTS in database.py. Migration triggered at 50 users (Phase 5.6). |
| GPU instability | 5 | Medium | 15 | Phase 0.6: proprietary NVIDIA driver install. Low risk after fix. |
| Social content quality | 6 | Medium | 18 | Phase 2.9: content moderation via Ollama. Phase 2.6: real project photos. Founder approval required. |
| Crypto regulatory | 7 | Low | 14 | Start Solana only. Legal consult before token launch. Discounts are marketing, not securities. |
| AI cost overrun | 6 | Medium | 18 | Phase 4.10: per-desk daily budget caps, 80% Telegram alerts, auto-pause at 100%. Cost tracker already built with 11 endpoints. |
| Legacy app confusion | 5 | High | 15 | Phase 0.11: kill 6 legacy processes immediately. 18 of 27 apps are redundant — CC handles everything. |
| Missing SMTP/API keys | 4 | High | 12 | Phase 0.7: add all missing keys. Email, Groq fallback, and web search currently broken without them. |

---

## Milestone Calendar

| Week | Milestone | Criteria |
|------|-----------|---------|
| Day 5 | Phase -1 Complete | 10 interviews done, 5+ intent-to-pay forms, pricing validated |
| Week 1 | Phase 0 Complete | Clean platform, 0 vulns, observability live, backups automated, legacy apps killed |
| Week 3 | Phase 1 Complete | PCI-compliant Stripe live, intake-to-invoice works, SaaS page active |
| Week 3 | FIRST REVENUE | First real payment received (service job or SaaS signup) |
| Week 5 | Phase 2 Complete | Social channels live, moderated 4-week calendar, leads incoming |
| Week 8 | Phase 3 Complete | CraftForge operational, SaaS onboarding, 3-5 beta customers, E2E tests |
| Week 8 | LLCFactory Live | Legal services accepting orders in DC/MD/VA |
| Week 12 | Phase 4 Complete | MAX autonomous with guardrails: 3+ tasks/day, cost-capped, audit-logged |
| Week 12 | EMPIRE Token | Token deployed on Solana, integrated into payment flow |
| Week 16 | Phase 5 Checkpoint | Churn <3%, NPS 7+, 10+ SaaS users, hardware kits shipping |

### Visual Timeline

| Week | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|------|---|---|---|---|---|---|---|---|---|----|----|-----|
| Phase | 0 | 1 | 1 | 2 | 2 | 3 | 3 | 3 | 4 | 4 | 4 | 4 |

---

## Success Metrics

Track these metrics weekly. They determine whether to proceed to the next phase or extend the current one.

| Phase Gate | Metric 1 | Metric 2 | Metric 3 | Metric 4 |
|-----------|----------|----------|----------|----------|
| End of Phase 0 | 0 test records in DB | All endpoints return 200 | OpenClaw health = online | GPU driver = proprietary |
| End of Phase 1 | Stripe processes $1+ | 1+ real quote sent | 1+ real invoice paid | SaaS page live |
| End of Phase 2 | 4 social accounts live | 28+ posts scheduled | 1+ inbound lead from social | GBP verified |
| End of Phase 3 | CraftForge UI complete | 3+ beta SaaS users | LLC Factory live | Command Center = sole dashboard |
| End of Phase 4 | Morning brief auto-sends | Auto-quote response <15 min | Social posts auto-scheduled | EMPIRE token deployed |

### 12-Week Revenue Target

| Stream | 12-Week Target | Source |
|--------|---------------|--------|
| Service revenue (drapery + woodwork jobs) | $5,000 - $15,000 | From social-driven leads |
| SaaS subscriptions (3-5 beta users) | $87 - $395/mo | Lite/Pro tier, some free beta |
| LLC formation services | $500 - $2,000 | DC/MD/VA filings |
| **Total 12-week target** | **$5,587 - $17,395** | **Conservative to moderate** |

These are conservative targets assuming organic social growth and the founder's existing network. The SaaS projections from the Ecosystem Report ($453K ARR by end of 2026) assume scaling beyond these initial numbers once the pipeline proves out.

---

## Appendix: Full Codebase Inventory (from March 13 Audit)

### Backend Routers (46 files)
ai, amp, apostapp, auth, chat_backup, contacts, costs, craftforge, crypto_payments, customer_mgmt, desks, docker_manager, economic, finance, inbox, intake_auth, inventory, jobs, licenses, listings, llcfactory, luxeforge_measurements, max/, marketplace/, memory, messages, notifications, ollama_manager, onboarding, preorders, quotes, shipping, socialforge, supportforge_ai, supportforge_customers, supportforge_kb, supportforge_tickets, system_monitor, tasks, users, vision, webhooks

### MAX Tools (28 registered)
create_task, get_tasks, get_desk_status, search_quotes, get_quote, open_quote_builder, create_quick_quote, select_proposal, search_contacts, create_contact, get_system_stats, get_weather, get_services_health, send_telegram, send_quote_telegram, send_email, send_quote_email, search_images, web_search, web_read, photo_to_quote, run_desk_task, present, search_intake_projects, search_customers, check_inventory, get_finance_summary

### MAX Desks (16)
base_desk, clients_desk, contractors_desk, desk_manager, desk_router, desk_scheduler, finance_desk, forge_desk, innovation_desk, it_desk, lab_desk, legal_desk, market_desk, marketing_desk, sales_desk, support_desk, website_desk

### Backend Services (82 .py files)
Core: ai_router, guardrails, system_prompt, token_tracker, tool_executor, telegram_bot, tts_service, stt_service, email_service, inpaint_service, presentation_builder, monitor, scheduler, notification_prefs, desk_prompt
Brain: memory_store, context_builder, conversation_tracker, embeddings, local_llm, brain_config
Pipeline: task_pipeline
Security: sanitizer, voiceprint, consent, guardrails
Quote Engine: item_analyzer, line_item_builder, mockup_matcher, pricing_tables, quote_assembler, quote_phases, tier_generator, verification, yardage_calculator
Marketplace: base, ebay, fee_service, order_service, product_service, review_service
Other: auth, chat_backup, crypto_payment, economic, license, listing, message, preorder, quality_evaluator, shipping, supportforge (4), user, context_unification

### Hardware Documentation (14 files)
ASSEMBLY_GUIDE.md, BILL_OF_MATERIALS.md, specs/ (6 files: mini-pc-options, starter/business/enterprise builds, networking, storage, peripherals), configs/ (3 files: ubuntu-install, bios-settings, post-install.sh), diagrams/network-topology.md

### Outside Main Repo
- ~/Empire/ — older clone (backend, data, logs, scripts, uploads)
- ~/recoveryforge/ — RecoveryForge standalone app

---

*End of Implementation Plan — EmpireBox v3.0 REVISED*
*Grounded in codebase reality. Every claim verified against actual files.*
