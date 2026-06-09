# REPORT — Module ⇄ Widget ⇄ MAX-First ⇄ BusinessOps Crosswalk

**Repo:** `/home/rg/empire-repo-main` · **Branch:** `main` · **HEAD:** `28679781a22c3c7901754067356b3d42bdf226c3`
**Author:** Hermes reconciliation of Sub-1, Sub-2, Sub-3, 2026-06-09
**Scope:** read-only crosswalk tying module readiness to sidebar visibility, widget visibility, MAX routing, and BusinessOps/TenantOps entitlement impact. No code changed.

## Crosswalk (rows are modules, columns are visibility/impact surfaces)

Legend: ✓ = visible · `dev`/`active`/`soon` = sidebar badge · 🟢/🟡/🟠/🔴/⏸️ = readiness

| Module | Readiness | Sidebar visibility | Widget visibility | MAX desk / routing | BusinessOps/TenantOps impact |
|---|---|---|---|---|---|
| **MAX** | 🟢 GREEN | Command section · active | ContinuityPanel "MAX Truth" row (compact) · OpenClaw gate pill · TopBar model picker | Platform-level; no tenant | None yet (meter per package later) |
| **Owner's Desk** | 🟢 GREEN | Command section · active (gold) | OwnerContext aggregates desk/inbox/cost/tasks | Platform | Hidden from any tenant view |
| **MAX Avatar** | 🟢 GREEN | Command section · active | ContinuityPanel "surface" field; TopBar model picker | Platform | Founder-only |
| **MAX Continuity** | 🟢 GREEN | Infrastructure · active | ContinuityPanel pills B1–B9 | Platform | Internal only — not customer |
| **Dashboard** | 🟢 GREEN | Right rail toggle | DashboardScreen + inline composite | Quality + Analytics (Phoenix/Raven) | None — composite widget |
| **Empire Workroom** | 🟢 GREEN | Business · active | Module cards (Quotes/Invoices/CRM/Inventory/Tasks/Shipping/Costs) on right panel | `forge` (Kai) + `finance` + `clients` | `business=workroom` proto-tenant |
| **WoodCraft** | 🟢 GREEN | Business · active | RightPanel cards (CRM/Materials/Orders/Tasks/Costs) | Alias to `forge` | `business=woodcraft` proto-tenant |
| **ForgeCRM** | 🟢 GREEN | Tools · active | RightPanel CustomerList/Detail | `clients` (Elena) | Tenant-scoped per Workroom/WoodCraft |
| **AMP** | 🟢 GREEN | Tools · active | AMP routes (`/amp/cursos` etc.) | Platform (separate `data/amp.db`) | None — personal dev |
| **AI Vision** | 🟢 GREEN | Tools · active | VisionAnalysisPage; mmx CLI | `forge` (Kai) | Inherits `business_unit` |
| **Pricing Studio** | 🟢 GREEN | Tools · active | PricingStudioScreen deep-link from `/pricing` | `forge` + `finance` | Inherits Workroom/WoodCraft |
| **ArchiveForge** | 🟢 GREEN | Tools · active | `/archiveforge`, `/archiveforge-life` | Platform (file storage) | **YES** — public/Starter tier |
| **PlatformForge** | 🟢 GREEN | Infrastructure · active | PlatformPage; orchestration route | `it` (Orion) | Platform |
| **System** | 🟢 GREEN | Infrastructure · active | SystemReportScreen + DevPanel | `it` (Orion) | Platform |
| **Tokens & Costs** | 🟢 GREEN | Infrastructure · active | Inside System/Dashboard; per-tenant cost | `analytics` (Raven) | Per-tenant cost (Starter/Growth/Empire) |
| **Ecosystem Catalog** | 🟢 GREEN | n/a (internal) | Drives truthful MAX capability claims | Platform | Spine for tenant entitlement later |
| **Ecosystem Catalog** | 🟢 GREEN | n/a (internal) | Drives truthful MAX capability claims | Platform | Spine for tenant entitlement later |
| **Codex CLI** | 🟢 GREEN | n/a (runtime surface) | n/a | Execution surface | n/a |
| **Claude CLI** | 🟢 GREEN | n/a (runtime surface) | n/a | Execution surface | n/a |
| **delegate_task** | 🟢 GREEN | n/a (runtime surface) | n/a | Execution surface | n/a |
| **Hermes Desktop** | 🟢 GREEN | n/a (runtime surface) | n/a | Execution surface | n/a |
| **StoreFront Forge** | 🟡 YELLOW | Tools · active | StoreFrontForgePage | `intake` (Zara) + `forge` | **YES** — Starter+ (single-tenant rewrite needed) |
| **ConstructionForge** | 🟡 YELLOW | Tools · active | ConstructionForgePage (es/en) | `intake` + `forge` | **YES** — new tenant (Colombian market) |
| **LuxeForge** | 🟡 YELLOW | Tools · active | `/luxe` and `/luxeforge` (dup route) | `intake` + `forge` | **YES** — new tenant |
| **LLCFactory** | 🟡 YELLOW | Ecosystem · active | LLCFactoryPage | `legal` (Raven) | **YES** — new tenant (JSON → DB) |
| **RelistApp** | 🟡 YELLOW | Tools · active | RelistAppPage + SmartListerPanel | `market` (Sofia) | **YES** — `pricing_tiers` already (lite/pro/empire) |
| **TranscriptForge** | 🟡 YELLOW | Tools · active | `/transcriptforge-review` + page | `support` (Luna) best fit (no desk) | **YES** — tenant-scoped (legal docs) |
| **EmpireAssist** | 🟡 YELLOW | Tools · active | EmpireAssistPage | None (helper utility) | None this sprint |
| **EmpirePay** | 🟡 YELLOW | Tools · active | EmpirePayPage | None | Tenant-scoped wallets (later) |
| **SocialForge** | 🟡 YELLOW | Ecosystem · active (pink) | SocialForgePage; no widget chips | `marketing` (Nova) | **YES** — language, target landing per tenant |
| **OpenClaw** | 🟡 YELLOW | Ecosystem · active (orange) | BottomBar dot; ContinuityPanel pill; TopBar model picker; **"OpenClaw online · 72 tasks" chip in chat row (FALSELY green)** | `it` (Orion) for ops; **NOT a delegate-able agent** | n/a (internal surface) |
| **VendorOps** | 🟡 YELLOW | Ecosystem · active (teal) | VendorOpsPage | `contractors` (Marcus) for primitives | **YES (top priority)** — `business_id` + `vendor_type` |
| **RecoveryForge** | 🟡 YELLOW | Ecosystem · active (cyan) | RecoveryForgeScreen | `it` + `lab` | None — local-only |
| **MarketForge** | 🟡 YELLOW | Tools · active | MarketForgePage + SmartListerPanel | `market` (Sofia) | Tenant-scoped (marketplace accounts) |
| **ContractorForge** | 🟡 YELLOW | Tools · active | ContractorForgePage | `contractors` (Marcus) | Tenant-scoped (shared intake+jobs) |
| **LeadForge** | 🟡 YELLOW | Tools · active | LeadForgePage + LeadForgePageNew (dup) | `sales` (Aria) | Tenant-scoped (campaigns) |
| **Hardware** | 🟡 YELLOW | Infrastructure · "DEV" badge | None | `it` (Orion) | None this sprint |
| **Notifications** | 🟡 YELLOW | n/a (addon) | TopBar unread badge; falls back to hardcoded | Platform | None |
| **Harry / OpenCode** | 🟡 YELLOW | n/a (runtime surface) | n/a | Execution | n/a |
| **OpenClaw worker** | 🟡 YELLOW | n/a (runtime surface) | n/a | `it` (Orion) | n/a |
| **ApostApp** | 🟠 ORANGE | Ecosystem · active (gold, MISLEADING — should be `dev` until v1 ships) | BottomBar news ticker does NOT mention apostille; OwnerContext not referenced | **NO desk assigned** — needs `legal` (Raven) for compliance + `intake` (Zara) for customer | **YES (top priority)** — new tenant, JSON → DB |
| **Drawing Studio** | 🟠 ORANGE | Tools · active (gold) | RightPanel Tasks widget; bench renderers lack fabric/material callout chips | `forge` (Kai) | Inherits Workroom/WoodCraft via `business_unit` |
| **SupportForge** | 🟠 ORANGE | Tools · active | TicketsPage + SupportForgePage; missing `sf_tickets` table at runtime | `support` (Luna) | **YES** — already multi-tenant isolated |
| **ShipForge** | 🔴 RED | Tools · active | ShipForgePage (PLACEHOLDER stub) | `market` (Sofia) — desk field null | **YES** — not customer-facing until EasyPost wired |
| **VetForge** | ⏸️ PARKED | Tools · "SOON" badge | Placeholder page only | `innovation` (Spark) | Deferred (VA compliance) |
| **PetForge** | ⏸️ PARKED | Tools · "SOON" badge | Placeholder page only | `innovation` (Spark) | Deferred |

---

## Modules grouped by BusinessOps dependency

### Tier A — must land BusinessOps/TenantOps FIRST (no current scoping)

1. **ApostApp** — top priority, no desk, no tenant, JSON storage
2. **VendorOps** — top priority, `category` is free-form, needs `business_id` + `vendor_type`
3. **Drawing Studio** — `business_unit` grows to `business_id`
4. **LLCFactory** — JSON → DB, no Stripe
5. **LuxeForge / StoreFront Forge / ConstructionForge** — new SaaS tenants, no multi-tenant yet
6. **ArchiveForge** — already external-facing, needs explicit tenant scoping
7. **VetForge / PetForge** — should not surface until BusinessOps exists

### Tier B — additive to BusinessOps (can land after)

1. **SocialForge** — lock to `business_id=owner_default` for now
2. **MAX backend / Tokens & Costs** — per-tenant cost meter
3. **LeadForge, MarketForge, RelistApp, ContractorForge** — campaign/marketplace scoping
4. **TranscriptForge** — legal docs are inherently tenant-scoped

### Tier C — no BusinessOps dependency

- Owner / Avatar / Dashboard (Founder-only)
- AMP (personal dev)
- MAX Continuity (internal)
- Ecosystem Catalog (platform)

---

## Sidebar visibility changes recommended

| Current sidebar label | Current badge | Recommended badge | Reason |
|---|---|---|---|
| ApostApp | active (gold) | `dev` | 0 customer-facing pages, no Stripe, no email |
| ShipForge | active | `dev` or HIDE | self-declared PLACEHOLDER |
| SupportForge | active | `dev` | `partial`, missing `sf_tickets` table |
| Drawing Studio | active (gold) | `dev` | "too crude for client presentation" |
| OpenClaw | active (orange) | keep, but **fix chip in chat row** (warn tone) | queue stalled |
| VetForge / PetForge | "SOON" | keep | parked |
| Hardware | "DEV" | keep | docs-only |

---

## Widget visibility changes recommended

| Widget | Action | Reason |
|---|---|---|
| "Founder > MAX" | HIDE | decoration |
| "MiniMax" chip (chat row) | HIDE | duplicate of TopBar model picker |
| "Text routing ready" | SHOW_ONLY_ON_ERROR | rarely informative |
| "Vision offline" | FIX_LABEL → "Vision: cloud" | misleading (cloud vision still works) |
| "Voice configured" | SHOW_ONLY_ON_ERROR | rarely changes |
| "OpenClaw online · 72 tasks" | FIX_LABEL → "OpenClaw online · 72 queued (stalled)" with warn tone | queue not draining |
| "Code Mode CodeForge / Atlas" | MOVE_TO_SYSTEM_DETAILS | technical |
| "Self-heal guided" | SHOW_ONLY_ON_ERROR | constant amber alarm |
| "17 desks subordinate" | KEEP_MAIN, relabel "18 desks" | live count is 18 |
| "Upload image/doc" | REMOVE or wire onClick | fake button |
| "Public MAX" | MOVE_TO_SYSTEM_DETAILS | marketing link in status row |
| MAX Truth "Registry OK" | MOVE_TO_SYSTEM_DETAILS | debug |
| MAX Truth "Handoff stale" | SHOW_ONLY_ON_ERROR | normal after reboot |
| MAX Truth "Checked HH:MM:SS" | REMOVE_IF_STALE | set on mount, never auto-refreshes |
| MAX Truth "Live truth wins." | REMOVE / DEBUG only | engineering telemetry |
| BottomBar `db`/`grok`/`claude` dots | HIDE | never polled, always amber |
| BottomBar news ticker | HIDE | hardcoded fiction |
| BottomBar newspaper chevron | MOVE_TO_SYSTEM_DETAILS | noise |
| "Check" / "Monitor Check" notifications | FIX_LABEL | mis-categorized as buttons |

---

## What stays on main MAX surface (proposed)

**Header:** EMPIRE logo · Search · Model picker (single source of truth) · Notifications bell · Settings/Client toggle · Avatar

**Chat-screen status row (clean 4-line strip):**
1. Routing line: `minimax · MiniMax-M3 · cloud` (only show fallback/voice/vision on non-OK)
2. Desks line: `18 desks ▸` (click → Desks)
3. OpenClaw line: `OpenClaw healthy · worker 4s` (click → OpenClawTasksPage)
4. MAX Truth pill (compact, click to expand; only show stale/warn states)

**Bottom bar:** single `System: OK · Ollama OFF` pill → opens System Details drawer

**Removed:** all 6 service dots except `backend`/`ollama`/`tg`, news ticker, newspaper chevron, "Upload image/doc" chip, "Public MAX" chip, "Founder > MAX" breadcrumb, "Live truth wins." text, "Handoff stale" pill (unless error).

---

## Top 5 cross-cutting risks (consolidated)

1. **No BusinessOps/TenantOps code exists in the repo.** Repo-wide search for `business_id|tenant_id|provisioning|entitlement|package.*tier` returns zero matches outside `supportforge_*` model fields. The SaaS tiers in the catalog (`$29 lite / $79 pro / $199 empire / $0 founder`) are a **promise in copy, not in code**. This confirms BusinessOps is the correct #2 priority in the standing plan.
2. **Desk count disagreement across surfaces.** Runtime registers 18 desks. Sidebar widget hardcodes "18 desks". `system_prompt.py` and `PresentationScreen.tsx` say 18. But `desks_online:17` from `/max/health` and `OwnerContext` "12 AI Desks" (RightPanel line 357) disagree. Pick `AIDeskManager.router.desk_ids.count` as the single source of truth.
3. **ApostApp and OpenClaw worker are mis-marked as healthy.** ApostApp is `active` in sidebar but has 0 customer pages, no Stripe, no email, no tenant. OpenClaw chip says `online · 72 tasks` in green while the queue is stalled with 5916 historical failures. Both need warning state in the UI.
4. **BottomBar service dots are dev telemetry, not Founder status.** `db`, `grok`, `claude` are never polled by `useSystemData` so they always show amber. The hardcoded news ticker is fiction. The bar is dev telemetry in Founder's face.
5. **Auto-publishing is the #1 accidental-revenue risk for SocialForge once BusinessOps lands.** Publish endpoints are live; "no scheduler daemon" is the only thing keeping them manual. When BusinessOps onboarding auto-creates a MarketingDesk task, it must not wire it to a scheduled-post executor. The MAX desk `marketing.handle_task()` should refuse `publish` actions until Founder turns auto-publish on per-tenant.

---

**End of crosswalk. No implementation performed.**
