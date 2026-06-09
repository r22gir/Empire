# EMPIRE-MODULE-READINESS-REGISTRY

**Repo:** `/home/rg/empire-repo-main` · **Branch:** `main` · **HEAD:** `28679781a22c3c7901754067356b3d42bdf226c3`
**Author:** tandem audit (Sub-1 inventory + Sub-3 MAX-first + Hermes reconciliation), 2026-06-09
**Scope:** read-only preparation registry. No code changed. No branches. No push.

## Legend

- **FE** = front-end page/screen exists · **SB** = sidebar entry exists · **BE** = backend router loaded in `main.py`
- **DB** = model/table in `backend/app/models/` · **TS** = ≥1 pytest in `backend/tests/` · **RH** = runtime-healthy
- Readiness: **GREEN** (usable now) · **YELLOW** (internal/polish) · **ORANGE** (prototype/audit) · **RED** (unsafe/broken) · **PARKED** (intentionally paused) · **DEPRECATED** (remove/hide)
- Type: **original-core** / **later-addon** / **experimental** / **planned** / **customer-facing** / **runtime-surface**

---

## Section 1 — Command / Core (5)

| # | Module | Type | FE | SB | BE | DB | TS | RH | Readiness | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **MAX** | original-core | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **GREEN** | Founder AI brain. 18 desks registered (live). Cross-channel continuity prompt-based, not unified UI thread. |
| 2 | **Owner's Desk** | original-core | ✓ | ✓ | — | — | partial | ✓ | **GREEN** | Aggregates MAX/desks/inbox/costs. OwnerContext hardcodes desk count — see widget audit. |
| 3 | **MAX Avatar** | later-addon | ✓ | ✓ | ✓ | — | ✓ | ✓ | **GREEN** | TTS provider key required at runtime. Only `full` mode incurs TTS cost. |
| 4 | **Dashboard** | original-core | ✓ | ✓ | — | — | — | ✓ | **GREEN** | Inline + right-rail composite of MAX/desks/costs/tasks. |
| 5 | **MAX Continuity** | later-addon | ✓ | ✓ | — | — | ✓ | ✓ | **GREEN** | Phone surface is `dead` per operating_registry. Must not claim Phone MAX. |

## Section 2 — Business Modules (13)

| # | Module | Type | FE | SB | BE | DB | TS | RH | Readiness | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 6 | **Empire Workroom** | original-core | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **GREEN** | Upholstery/drapery. `business=workroom` proto-tenant. |
| 7 | **WoodCraft** | original-core | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **GREEN** | Furniture/CNC. `business=woodcraft` proto-tenant. |
| 8 | **StoreFront Forge** | later-addon | ✓ | ✓ | ✓ | ✓ | — | ✓ | **YELLOW** | No dedicated tests. Single-tenant POS. |
| 9 | **ConstructionForge** | later-addon | ✓ | ✓ | ✓ | ✓ | — | ✓ | **YELLOW** | Colombian land CRM. i18n wired. No tests. |
| 10 | **LuxeForge** | later-addon | ✓ | ✓ | ✓ | ✓ | — | ✓ | **YELLOW** | `/luxe` and `/luxeforge` both exist — possible duplicate. |
| 11 | **LLCFactory** | later-addon | ✓ | ✓ | ✓ | JSON | — | ✓ | **YELLOW** | No DB. No Stripe. Manual payment. Same pattern as ApostApp. |
| 12 | **ApostApp** | later-addon | ✓ (admin only) | ✓ | ✓ (15 routes) | JSON | — | ✓ | **ORANGE** | 0 customer-facing landing/intake pages. No Stripe. No email/SMS. No vendor bridge. See REPORT-apostille-readiness.md. |
| 13 | **ForgeCRM** | original-core | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **GREEN** | Customer/contact/lead CRM. |
| 14 | **RelistApp** | later-addon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **YELLOW** | `active_partial` per registry. Legacy paths quarantined. |
| 15 | **TranscriptForge** | later-addon | ✓ | ✓ | ✓ | JSON | — | ✓ | **YELLOW** | Human-approval gate. Groq Whisper. Runtime auth required. |
| 16 | **EmpireAssist** | later-addon (helper layer) | ✓ | ✓ (status: `dev`) | — | — | — | ✓ | **YELLOW → dev** | Frontend-only. No router, no service, no tests. All 6 templates + 3 automations overlap with existing modules (Draft Email↔MAX, Summarize Doc↔ArchiveForge/TranscriptForge, Generate Social Post↔SocialForge, Analyze Data↔Tokens&Costs, Write Proposal↔ForgeCRM/LeadForge, Customer Response↔SupportForge, automations↔ForgeCRM/Workroom/ShipForge). Sidebar downgraded to `dev` on 2026-06-09. **Helper/template layer under MAX, not a standalone active module. Not current implementation priority.** |
| 17 | **EmpirePay** | later-addon | ✓ | ✓ | ✓ | ✓ | — | ✓ | **YELLOW** | Crypto + payment links. Stripe webhook `/api/v1/payments/webhook` is ownership point. |
| 18 | **AMP** | later-addon | ✓ | ✓ | ✓ | separate `data/amp.db` | — | ✓ | **GREEN** | Isolated DB + JWT. Bilingual. Safe to ship as customer-facing standalone. |

## Section 3 — Tools / Ecosystem (19)

| # | Module | Type | FE | SB | BE | DB | TS | RH | Readiness | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 19 | **AI Vision** | later-addon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **GREEN** | `minimax` mmx + xAI grok-vision + stability. |
| 20 | **Drawing Studio** | later-addon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **ORANGE** | API-complete. Output "functional schematic, too crude for client presentation" (REPORT-drawing-sprint-2-audit). Bench rewrite needed. |
| 21 | **Pricing Studio** | later-addon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **GREEN** | `pricing_engine.py` is source of truth. |
| 22 | **SocialForge** | later-addon | ✓ | ✓ | ✓ (21 routes) | JSON | — | ✓ | **YELLOW** | No scheduling daemon. No top-level page route. See REPORT-socialforge-apostille-gap.md. |
| 23 | **OpenClaw** | later-addon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **YELLOW** | Local Ollama-fronted chat model. **NOT a delegate-able agent** (per EMPIRE-COMPLETION-PLAN). Queue: 7357 total, 5916 failed, 1439 done, 0 viable. Worker not draining. |
| 24 | **VendorOps** | later-addon | ✓ | ✓ | ✓ (25 routes) | ✓ | ✓ | ✓ | **YELLOW** | `vo_accounts.category` is free-form. No first-class task/approval/due-date entity. See REPORT-vendorops-apostille-design.md. |
| 25 | **RecoveryForge** | later-addon | ✓ | ✓ | ✓ | JSON + dirs | ✓ | ✓ | **YELLOW** | Uses `/data/images/*` (out-of-repo). Ollama-bound. |
| 26 | **MarketForge** | later-addon | ✓ | ✓ | ✓ | ✓ | partial | ✓ | **YELLOW** | Shared with relistapp. No dedicated tests. |
| 27 | **ContractorForge** | later-addon | ✓ | ✓ | — (uses intake+jobs) | ✓ | partial | ✓ | **YELLOW** | No dedicated router. |
| 28 | **SupportForge** | later-addon | ✓ | ✓ | ✓ | ✓ (sf_*) | — | ✓ | **ORANGE** | Multi-tenant isolated. Operating_registry says `partial`. Runtime logs reported missing `sf_tickets` table. `founder_visible_ctas_truthful: false`. |
| 29 | **LeadForge** | later-addon | ✓ | ✓ | ✓ | ✓ | partial | ✓ | **YELLOW** | `LeadForgePageNew` exists alongside original — possible duplicate. |
| 30 | **ShipForge** | later-addon | ✓ | ✓ | ✓ | ✓ | — | ✓ | **RED** | `shipping.py` is **self-declared PLACEHOLDER**. EasyPost stub, hardcoded test rates, fake tracking. |
| 31 | **ArchiveForge** | later-addon | ✓ | ✓ | ✓ | — (files) | ✓ | ✓ | **GREEN** | Tests pass. |
| 32 | **VetForge** | planned | ✓ (placeholder) | ✓ ("SOON") | — | — | — | n/a | **PARKED** | VA compliance requires legal review. |
| 33 | **PetForge** | planned | ✓ (placeholder) | ✓ ("SOON") | — | — | — | n/a | **PARKED** | No implementation. |
| 34 | **PlatformForge** | original-core | ✓ | ✓ | ✓ | — | ✓ | ✓ | **GREEN** | Docker, Ollama, module registry, system monitor. |
| 35 | **Hardware** | experimental | — | ✓ ("DEV") | — | — | — | n/a | **YELLOW** | Docs-only. No runtime surface in CC. |
| 36 | **System** | original-core | ✓ | ✓ | ✓ | — | ✓ | ✓ | **GREEN** | System monitor + Dev Panel. |
| 37 | **Tokens & Costs** | later-addon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **GREEN** | Per-tenant cost tracking. `tenant_id` model exists; default `"founder"`. |

## Section 4 — Execution / Agent Surfaces (6)

| # | Surface | Type | Readiness | Notes |
|---|---|---|---|---|
| 38 | **Hermes Desktop** | runtime-surface | **GREEN** | Orchestrator session. Read-only coordinator by policy. |
| 39 | **Harry / OpenCode** | runtime-surface | **YELLOW** | Tailscale `:8787`. Requires pre-created branch + copy/paste prompt. |
| 40 | **Codex CLI** | runtime-surface | **GREEN** | `~/.local/bin/codex` v0.134.0. Authed. `codex exec` non-interactive. |
| 41 | **Claude CLI** | runtime-surface | **GREEN** | `/usr/bin/claude` v2.1.90. Authed. |
| 42 | **delegate_task sub-agents** | runtime-surface | **GREEN** | Max 3 concurrent. Depth 1. Leaf cannot `clarify`. |
| 43 | **OpenClaw worker** | runtime-surface | **YELLOW** | NOT a delegate-able agent. Local Ollama front. Worker stalled. |

## Discovered (not in original list)

| # | Module | Type | Readiness | Notes |
|---|---|---|---|---|
| 44 | **Notifications** | addon | **YELLOW** | Topbar unread badge. Falls back to hardcoded items. |
| 45 | **Ecosystem Catalog** | addon | **GREEN** | `app.services.max.ecosystem_catalog` + `operating_registry.json` v2. Spine of truthful MAX behavior. |

---

## Aggregate counts (44 requested + 2 discovered; 6 execution surfaces = 39 modules)

- **GREEN: 16** — MAX, Owner's Desk, MAX Avatar, Dashboard, MAX Continuity, Empire Workroom, WoodCraft, ForgeCRM, AMP, AI Vision, Pricing Studio, ArchiveForge, PlatformForge, System, Tokens & Costs, Ecosystem Catalog, Codex CLI, Claude CLI, delegate_task, Hermes Desktop
- **YELLOW: 16** — StoreFront Forge, ConstructionForge, LuxeForge, LLCFactory, RelistApp, TranscriptForge, EmpireAssist, EmpirePay, SocialForge, OpenClaw, VendorOps, RecoveryForge, MarketForge, ContractorForge, LeadForge, Hardware, Harry/OpenCode, OpenClaw worker, Notifications
- **ORANGE: 3** — ApostApp, Drawing Studio, SupportForge
- **RED: 1** — ShipForge
- **PARKED: 2** — VetForge, PetForge
- **DEPRECATED: 0**

---

## Top 10 Module Risks

1. **ShipForge** — self-declared PLACEHOLDER. Cannot be customer-facing. Fix: set `EASYPOST_API_KEY` + implement real EasyPost SDK calls.
2. **OpenClaw worker** — queue is broken (5916 failed / 7357 total, 0 viable in window). "OpenClaw online · 72 tasks" chip paints green while queue is stalled. Fix: investigate worker restart, then add warn-tone to chip.
3. **ApostApp** — API-complete but no customer landing/intake page. Promote status to `dev` in sidebar until v1 ships.
4. **Drawing Studio** — output quality below client-presentable. Sprint 2 audit lists bench rewrite + primitive dedup. Quality standard drafted, not implemented.
5. **SupportForge** — `partial`, missing `sf_tickets` table, `founder_visible_ctas_truthful: false`. Verify table creation on startup.
6. **SocialForge** — no scheduling daemon. Two `POST /socialforge/post/{instagram,facebook}` endpoints are live. Risk of accidental auto-publish once BusinessOps lands.
7. **VendorOps** — `category` is free-form. Needs `business_id` + `vendor_type` enum.
8. **MAX Continuity** — phone surface is `dead`. Must not claim Phone MAX.
9. **RelistApp** — `active_partial`. Marketplace account sync and auto-publish partial.
10. **Desk count disagreement** — `/max/health` says 18, OwnerContext hardcodes 12, sidebar widget shows 18. Pick one source of truth.

---

## MAX-first routing map (sub-3 lens)

Modules are routed via the 17 registered desks (`desk_manager.py`): analytics, clients, codeforge, contractors, finance, forge, innovation, intake, IT, lab, legal, market, marketing, quality, sales, support, website. Notable desk coverage:

- **Owned by `forge` (Kai):** Empire Workroom, WoodCraft, AI Vision, Drawing Studio, Pricing Studio, StoreFront Forge, ConstructionForge, LuxeForge
- **Owned by `marketing` (Nova):** SocialForge
- **Owned by `market` (Sofia):** MarketForge, RelistApp, ShipForge
- **Owned by `support` (Luna):** SupportForge, TranscriptForge (best fit; no desk assigned)
- **Owned by `legal` (Raven):** LLCFactory
- **Owned by `intake` (Zara):** ApostApp (intake path; **no desk assigned** — needs `legal` for compliance)
- **Owned by `contractors` (Marcus):** ContractorForge, VendorOps
- **Owned by `innovation` (Spark):** VetForge, PetForge (keyword-routed; both parked)
- **Owned by `it` (Orion):** OpenClaw (ops), PlatformForge, System, Hardware, RecoveryForge (with `lab`)
- **Owned by `sales` (Aria):** LeadForge
- **Owned by `clients` (Elena):** ForgeCRM
- **Owned by `finance` (Sage):** Pricing Studio (shared with `forge`)
- **Owned by `analytics` (Raven):** Tokens & Costs
- **Platform-level (no desk):** MAX, MAX Continuity, MAX Avatar, Owner's Desk, AMP, ArchiveForge, EmpirePay, EmpireAssist, Dashboard

**All execution surfaces require Founder approval before code changes** (`HERMES_BACKGROUND_REVIEW_DISABLED=1`; memory-write kill switch; no `.opencode` edits; do not route `delegate_task` to OpenClaw).

---

## BusinessOps / TenantOps dependency map

**Critical finding:** Repo-wide search for `business_id|tenant_id|provisioning|entitlement|package.*tier` returns **zero matches** outside `supportforge_*` model files (which use `tenant_id` as a field name, not a real tenant system). The only existing scoping primitive is `business_unit` inside `vision/product_catalog.py` and a `business=workroom` query param in 2 routes (`memory.py`, `avatar.py`).

There is **no `businesses` table, no `tenants` table, no `packages` table, no entitlement model, no provisioning flow**. The SaaS tiers in the catalog (`$29 lite / $79 pro / $199 empire / $0 founder`) are a **promise in copy, not in code**.

| Module | Needs `business_id`? | Needs tenant scoping? | Needs provisioning? | Needs package assignment? | Depends on BusinessOps landing first? |
|---|---|---|---|---|---|
| Drawing Studio | YES (grows from `business_unit`) | YES | YES | YES | **YES** |
| ApostApp | **YES (top priority)** | YES | **YES** | YES (new tier) | **YES** |
| SocialForge | YES | YES | YES | YES (Growth+) | NO (additive; lock to `business_id=owner_default`) |
| VendorOps | **YES (top priority)** | YES | YES | YES (Starter+ excludes) | **YES** |
| MAX backend / Tokens | YES at meta level | NO at data level yet | YES (platform first) | YES | NO (coexist) |
| Workroom / WoodCraft | YES (`business=` proto-tenant) | YES | YES | YES | NO (already scoped) |
| LLCFactory / LuxeForge / StoreFront / Construction | YES (new tenants when sold) | YES | YES | YES | **YES** |
| VetForge / PetForge | YES (future) | YES | YES | YES (custom) | **YES** |
| AMP | NO (personal dev) | NO | NO | NO | NO |
| ArchiveForge | YES (external customer surface) | YES | YES | YES (public/Starter) | **YES** |
| Owner / Avatar / Dashboard | NO (Founder-only) | NO | NO | NO | NO |

---

## Modules that should NOT be customer-facing yet

1. **ShipForge** — PLACEHOLDER stub. Cannot ship.
2. **Drawing Studio** — output too crude for client presentation.
3. **ApostApp** — no landing/intake page, no notify-founder endpoint, no Stripe, no email/SMS, no vendor bridge.
4. **VendorOps** — no apostille routing, no first-class task model.
5. **OpenClaw worker** — queue stalled. Founder-only.
6. **MAX Code Mode / self_heal / git_operations** — explicitly bounded; founder-only per capability_registry.json.
7. **SupportForge** — runtime logs reported missing `sf_tickets` table.
8. **MAX Continuity** — internal tool only.
9. **Tokens & Costs** — exposes internal tenant/cost data.
10. **VetForge / PetForge** — placeholder pages.

---

## Modules that can be paused safely

- VetForge, PetForge (parked already)
- Hardware (docs-only)
- EmpireAssist (frontend-only; helper/template layer under MAX; sidebar status `dev` since 2026-06-09; no dedicated router, no revenue dependency; do not build backend during current preparation sprint)
- SocialForge (publish-only via manual click; calendar is draft for review)
- RecoveryForge (local Ollama, out-of-repo paths)
- SmartLister (already merged into MarketForge)
- Drawing Studio Sprint 2 (medium risk, no immediate revenue path)
- VendorOps `run_apostille_alerts` (additive; pause until `apostille_tasks` table is in place)

---

## Repo status (from `git status`)

- Modified: `.opencode/config.json` (always-present, out of scope)
- Untracked (6, all planning docs from prior audit batch):
  - `DRAWING-QUALITY-STANDARD.md`
  - `EMPIRE-COMPLETION-PLAN.md`
  - `REPORT-apostille-readiness.md`
  - `REPORT-drawing-sprint-2-audit.md`
  - `REPORT-socialforge-apostille-gap.md`
  - `REPORT-vendorops-apostille-design.md`

Stale inside tracked code (not in git diff):
- `backend/app/routers/shipping.py` — self-declared PLACEHOLDER
- `backend/app/routers/jobs.py` — replaced by `jobs_unified`, still present
- `backend/app/services/max/{tool_executor,system_prompt,tool_safety}.bak-177385539*` — `.bak` files in tree (gitignore does not include `*.bak`)

---

**End of registry. No implementation performed.**
