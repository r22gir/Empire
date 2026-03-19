# Empire Frontend Page Map

**Date:** 2026-03-18
**App:** Empire Command Center (port 3005, Next.js)
**Total pages/screens:** 17
**Status:** 10 REAL, 3 PARTIAL, 2 COSMETIC, 2 PLACEHOLDER

---

## Status Definitions

- **REAL** — Page loads, displays real data, core interactions work
- **PARTIAL** — Page loads and some features work, but key functionality is incomplete
- **COSMETIC** — Page renders UI but has no real data or broken sub-components
- **PLACEHOLDER** — Page exists as a shell with minimal or no content

---

## Page Inventory

| # | Page/Screen | Status | Details |
|---|-------------|--------|---------|
| 1 | ChatScreen | **REAL** | MAX AI chat interface. Message send/receive works. Desk switching works. Conversation history persists in localStorage. |
| 2 | DashboardScreen | **REAL** | KPI cards with real numbers ($2,555 MTD revenue, $5,380 expenses, 6 outstanding invoices). Charts render. |
| 3 | WorkroomPage | **REAL** | 10 tabs: Jobs, Quotes, Customers, Inventory, Yardage Calc, Kanban, CushionBuilder, Intake, Invoices, Settings. All tabs load. Real data in most. |
| 4 | CraftForgePage | **REAL** | CNC/woodwork project management. Project list loads. |
| 5 | SocialForgePage | **REAL** | 16 accounts displayed across 6 platforms. Post scheduling UI. AI guide generation. No OAuth means no actual posting. |
| 6 | PlatformPage | **REAL** | System status, service health, configuration. Shows real backend status. |
| 7 | RecoveryForgeScreen | **REAL** | Bulk image classification interface. Connected to Layer 3 pipeline (18,472 images). Progress tracking. |
| 8 | MarketForgePage | **REAL** | Marketplace listing management. Product catalog view. |
| 9 | LeadForgePage | **REAL** | Lead tracking and pipeline. Lead status cards. |
| 10 | TasksScreen | **REAL** | Task list from MAX task engine. Create, update, complete tasks. |
| 11 | DesksScreen | **REAL** | All 18 desks displayed with status, model routing, and tool counts. |
| 12 | QuoteBuilderScreen | **PARTIAL** | CushionBuilder wizard is wired and works (9 steps). General quote line item pricing needs work — some calculations incomplete. |
| 13 | ContractorForgePage | **PARTIAL** | Page renders with contractor cards. Data is mock/placeholder — no real contractors in the system yet. |
| 14 | Intake pages | **REAL** | Multi-step intake form. 5 real projects created through this flow. |
| 15 | VetForge / PetForge | **PLACEHOLDER** | Page shells exist. No backend endpoints, no data models, no functionality. Future vertical expansion. |
| 16 | InboxScreen | **COSMETIC** | UI renders an inbox layout with message list and detail pane. No real messages. Not connected to email or any message source. |
| 17 | ForgeCRMPage | **COSMETIC** | Top-level page renders. Sub-components (contact detail, activity timeline, deal pipeline) do not load or are empty. Use WorkroomPage > Customers tab instead for real CRM. |

---

## Summary

| Status | Count | Percentage |
|--------|-------|------------|
| REAL | 10 | 59% |
| PARTIAL | 3 | 18% |
| COSMETIC | 2 | 12% |
| PLACEHOLDER | 2 | 12% |

---

## WorkroomPage Tab Detail

The WorkroomPage is the most feature-dense screen with 10 tabs:

| Tab | Status | Notes |
|-----|--------|-------|
| Jobs | REAL | Loads from `/jobs` — currently empty |
| Quotes | REAL | 54 quotes, full CRUD |
| Customers | REAL | CRM with avatars, badges, search |
| Inventory | REAL | 15+ categories, QuickBooks import |
| Yardage Calculator | REAL | Width, repeat, cut calculations |
| Kanban | PARTIAL | Board renders, no jobs to display |
| CushionBuilder | REAL | 9-step wizard with materials calc |
| Intake | REAL | 5 real projects |
| Invoices | REAL | 11 real invoices |
| Settings | REAL | Configuration options |
