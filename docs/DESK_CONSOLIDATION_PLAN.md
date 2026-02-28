# Desk & Agent Consolidation Plan

**Date:** 2026-02-28
**Status:** PROPOSAL — no code changes yet

---

## Problem

Three overlapping systems handle "desks" and "agents" with duplicated roles, inconsistent architectures, and no single source of truth:

| System | Location | Bots | Architecture | Status |
|--------|----------|------|--------------|--------|
| New AI Desks | `app/services/max/desks/` | 4 desks | Async BaseDesk classes, LLM+keyword router, brain memory | ForgeDesk production; 3 placeholders |
| Legacy DeskManager | `app/services/max/desk_manager.py` | 8 bots | Pydantic models, domain-match routing, in-memory state | Fully defined, no real task logic |
| Standalone Agents | `~/Empire/agents/` | 6 bots | Async Agent ABC, Orchestrator, JSON file memory | Stub implementations, not wired to backend |
| DB Desk Configs | `app/routers/desks.py` + `desks.json` | 13 desks | SQLite rows with system prompts, tools, widgets | UI config only — no AI execution |

---

## Overlap Map

The table below maps every bot/desk across all four systems. Rows are grouped by business function.

| Function | DB Desk (13) | Legacy DeskManager (8) | New AI Desk (4) | Standalone Agent (6) | Verdict |
|----------|-------------|----------------------|-----------------|---------------------|---------|
| **Workroom / Production** | `operations`, `design`, `estimating` | ProductBot | **ForgeDesk** | QuoteBot | Merge into **ForgeDesk** (already built) |
| **Sales / Leads** | `sales` | SalesBot | — | LeadBot | New **SalesDesk** |
| **Customer Support** | `support` | SupportBot | SupportDesk (placeholder) | SupportBot | Build out **SupportDesk** |
| **Marketing / Content** | `marketing` | ContentBot | SocialDesk (placeholder) | — | Build out **SocialDesk** → rename **MarketingDesk** |
| **Marketplace / Listings** | — | — | MarketDesk (placeholder) | ListingBot, ShipBot | Build out **MarketDesk** |
| **Finance / Billing** | `finance` | FinanceBot | — | — | New **FinanceDesk** |
| **Clients / CRM** | `clients` | — | — | — | New **ClientsDesk** |
| **Contractors** | `contractors` | — | — | — | New **ContractorsDesk** |
| **Dev / Code** | — | DevBot | — | — | Drop (not a runtime desk — use Claude Code) |
| **QA / Testing** | — | QABot | — | — | Drop (not a runtime desk — use CI/CD) |
| **Ops / Infra** | `it` | OpsBot | — | — | New **ITDesk** |
| **Website / SEO** | `website` | — | — | — | New **WebsiteDesk** |
| **Legal** | `legal` | — | — | — | New **LegalDesk** |
| **R&D Lab** | `lab` | — | — | — | New **LabDesk** |
| **Telegram** | — | — | — | TelegramBot | Keep as utility, not a desk (notification channel) |

---

## Target Architecture

One system. Every desk is a `BaseDesk` subclass. The DB desk configs provide UI metadata. Standalone agents become capabilities within desks.

```
app/services/max/desks/
├── __init__.py
├── base_desk.py              # Existing — no changes needed
├── desk_router.py            # Existing — expand keyword map per new desks
├── desk_manager.py           # Existing AIDeskManager — register all desks
│
├── forge_desk.py             # KEEP (production template)
├── sales_desk.py             # NEW — absorbs SalesBot + LeadBot
├── support_desk.py           # BUILD OUT — absorbs SupportBot (legacy) + SupportBot (agent)
├── marketing_desk.py         # RENAME social_desk.py — absorbs ContentBot
├── market_desk.py            # BUILD OUT — absorbs ListingBot + ShipBot
├── finance_desk.py           # NEW — absorbs FinanceBot
├── clients_desk.py           # NEW — CRM operations
├── contractors_desk.py       # NEW — installer/vendor management
├── it_desk.py                # NEW — absorbs OpsBot
├── website_desk.py           # NEW — SEO, portfolio, content
├── legal_desk.py             # NEW — contracts, compliance
└── lab_desk.py               # NEW — experimental / sandbox
```

### What gets retired

| Retired | Reason |
|---------|--------|
| `app/services/max/desk_manager.py` (legacy) | Replaced by `desks/desk_manager.py` (AIDeskManager) |
| `~/Empire/agents/` orchestrator + base | Replaced by BaseDesk + AIDeskManager |
| `~/Empire/agents/builtin/*` individual bots | Logic absorbed into desk subclasses |

### What stays unchanged

| Kept | Reason |
|------|--------|
| `app/routers/desks.py` + SQLite `desk_configs` | UI metadata (icons, colors, shortcuts, widgets) — not execution logic |
| `app/routers/tasks.py` + SQLite `tasks` | Task CRUD used by frontend — desks will read/write here |
| `desks/base_desk.py` | Proven abstract base |
| `desks/desk_router.py` | Expand keyword map, keep LLM fallback |
| `desks/forge_desk.py` | Production template |
| TelegramBot | Becomes a shared utility service, callable by any desk |

---

## ForgeDesk Template — Pattern to Follow

Every new desk must follow the ForgeDesk pattern:

```python
class SalesDesk(BaseDesk):
    desk_id = "sales"
    desk_name = "SalesDesk"
    desk_description = "..."
    capabilities = ["lead_capture", "pipeline_management", ...]

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        # Route by keyword to specific handler
        if "lead" in combined:
            return await self._handle_lead(task)
        elif "follow" in combined:
            return await self._handle_followup(task)
        ...

    async def _handle_lead(self, task):
        # Business logic (from LeadBot: scoring, qualification)
        # Brain memory integration
        # Auto-escalation rules
        await self.complete_task(task, result)
        return task
```

Key patterns from ForgeDesk:
1. **Keyword routing** in `handle_task()` to specific `_handle_*` methods
2. **Business constants** as class-level variables (thresholds, rates)
3. **Auto-escalation** for high-value or high-risk items
4. **Brain memory** logging via `_log_to_brain()`
5. **Customer history** lookup via memory store
6. **Briefing section** for morning reports

---

## Migration: What Goes Where

### SalesDesk ← SalesBot + LeadBot

| Source | Capability | Migration |
|--------|-----------|-----------|
| Legacy SalesBot | domains: leads, pipeline, follow_ups, quotes, proposals | Map to capabilities |
| Standalone LeadBot | Lead scoring (email_bonus + budget), qualification threshold ≥30, CRM entry | Port scoring logic into `_handle_lead()` |
| DB `sales` desk | System prompt (sales cycle, lead sources, bilingual) | Use as desk_description + routing context |
| DB `sales` desk | Tools: add_lead, update_lead_stage, schedule_followup | Wire as callable actions |

### SupportDesk ← SupportBot (legacy) + SupportBot (agent)

| Source | Capability | Migration |
|--------|-----------|-----------|
| Legacy SupportBot | domains: tickets, inquiries, faq, escalations, feedback | Map to capabilities |
| Standalone SupportBot | Keyword auto-response (shipping, refund, cancel, invoice), escalation logic | Port into `_handle_ticket()` |
| DB `support` desk | System prompt (warranty, common issues, professional responses) | Use as desk_description |

### MarketingDesk ← ContentBot + SocialDesk (placeholder)

| Source | Capability | Migration |
|--------|-----------|-----------|
| Legacy ContentBot | domains: listings, descriptions, social_media, seo, images | Map to capabilities |
| Placeholder SocialDesk | capabilities: content_scheduling, engagement_tracking, audience_analytics | Keep and expand |
| DB `marketing` desk | System prompt (Instagram, Pinterest, before/after, hashtags) | Use as desk_description |

### MarketDesk ← ListingBot + ShipBot + MarketDesk (placeholder)

| Source | Capability | Migration |
|--------|-----------|-----------|
| Standalone ListingBot | Multi-channel listing (MarketForge, RelistApp, SocialForge) | Port into `_handle_listing()` |
| Standalone ShipBot | Order fulfillment (label gen, tracking, customer notify) | Port into `_handle_shipping()` |
| Placeholder MarketDesk | capabilities: listing_creation, inventory_sync, pricing_analysis | Keep and expand |

### FinanceDesk ← FinanceBot

| Source | Capability | Migration |
|--------|-----------|-----------|
| Legacy FinanceBot | domains: invoicing, payments, expenses, reports, subscriptions | Map to capabilities |
| DB `finance` desk | System prompt (margins, P&L, drapery economics) | Use as desk_description |

### ITDesk ← OpsBot

| Source | Capability | Migration |
|--------|-----------|-----------|
| Legacy OpsBot | domains: servers, deployment, monitoring, backups, ci_cd, security | Map to capabilities |
| DB `it` desk | System prompt (port monitoring, Switchboard, RAM/disk) | Use as desk_description |

### ClientsDesk, ContractorsDesk, WebsiteDesk, LegalDesk, LabDesk ← DB only

These have rich system prompts and tool definitions in the DB but no legacy bot or agent equivalent. Build as new BaseDesk subclasses using the DB desk config as the specification.

### TelegramBot → Shared Utility

```python
# app/services/max/telegram.py (or similar)
class TelegramNotifier:
    """Any desk can call this to send alerts."""
    async def send(self, message: str, chat_id: str = None) -> bool
```

Desks call `self.notify_telegram(message)` via a BaseDesk helper method.

---

## DeskRouter Expansion

Add keywords for all new desks:

```python
KEYWORD_MAP = {
    "forge":       ["quote", "estimate", "drape", "shade", "cornice", "valance",
                    "fabric", "window treatment", "workroom", "measurement", "install"],
    "sales":       ["lead", "prospect", "pipeline", "proposal", "follow up",
                    "consultation", "referral", "close", "deposit"],
    "support":     ["ticket", "complaint", "refund", "return", "warranty",
                    "service request", "issue", "unhappy"],
    "marketing":   ["social media", "post", "instagram", "content", "hashtag",
                    "campaign", "before after", "pinterest", "facebook"],
    "market":      ["listing", "marketplace", "ebay", "inventory", "shipping",
                    "relist", "fulfillment", "tracking"],
    "finance":     ["invoice", "payment", "expense", "revenue", "profit",
                    "billing", "subscription", "p&l"],
    "clients":     ["client", "customer record", "contact info", "preferences",
                    "meeting prep", "thank you note"],
    "contractors": ["installer", "seamstress", "availability", "contractor",
                    "crew", "pay rate", "schedule install"],
    "it":          ["server", "deploy", "monitoring", "uptime", "port",
                    "restart", "logs", "disk space", "RAM"],
    "website":     ["seo", "portfolio", "web copy", "meta description",
                    "google business", "homepage"],
    "legal":       ["contract", "terms", "compliance", "liability", "insurance",
                    "LLC", "agreement"],
    "lab":         ["experiment", "prototype", "test feature", "vision api",
                    "sandbox", "R&D"],
}
```

---

## DB Desk Config Alignment

Ensure every `BaseDesk.desk_id` matches a row in `desk_configs`:

| desk_id | In DB? | In desks/? | Action |
|---------|--------|-----------|--------|
| operations | Yes | No | Merge into `forge` (operations = ForgeDesk's production tracking) |
| design | Yes | No | Merge into `forge` (design = ForgeDesk's treatment selection) |
| estimating | Yes | No | Merge into `forge` (estimating = ForgeDesk's quote builder) |
| finance | Yes | No | Create `finance_desk.py` |
| sales | Yes | No | Create `sales_desk.py` |
| clients | Yes | No | Create `clients_desk.py` |
| contractors | Yes | No | Create `contractors_desk.py` |
| support | Yes | Placeholder | Build out `support_desk.py` |
| marketing | Yes | No | Rename `social_desk.py` → `marketing_desk.py` |
| website | Yes | No | Create `website_desk.py` |
| it | Yes | No | Create `it_desk.py` |
| legal | Yes | No | Create `legal_desk.py` |
| lab | Yes | No | Create `lab_desk.py` |
| forge | No | Yes (production) | Add row to `desk_configs` |
| market | No | Placeholder | Add row to `desk_configs` |

**Result:** `operations`, `design`, and `estimating` stay as DB rows for their UI layouts but route to ForgeDesk for AI execution. All others get 1:1 desk_id ↔ BaseDesk mapping.

---

## Build Order

Phase 1 — Foundation (no new desks, just cleanup):
1. Delete legacy `desk_manager.py` (the one at `services/max/desk_manager.py`)
2. Add `forge` and `market` rows to `desk_configs` in `desks.json`
3. Map `operations`/`design`/`estimating` DB desks to route to ForgeDesk
4. Wire TelegramBot as shared utility

Phase 2 — High-value desks (absorb most legacy bots):
5. Build `SalesDesk` (absorbs SalesBot + LeadBot)
6. Build out `SupportDesk` (absorbs both SupportBots)
7. Build out `MarketDesk` (absorbs ListingBot + ShipBot)
8. Rename + build `MarketingDesk` (absorbs ContentBot)
9. Build `FinanceDesk` (absorbs FinanceBot)

Phase 3 — Remaining desks (DB-only sources):
10. Build `ClientsDesk`
11. Build `ContractorsDesk`
12. Build `ITDesk` (absorbs OpsBot)
13. Build `WebsiteDesk`
14. Build `LegalDesk`
15. Build `LabDesk`

Phase 4 — Cleanup:
16. Archive `~/Empire/agents/` (move to `~/Empire/agents_legacy/`)
17. Update `desk_router.py` keyword map
18. Update `AIDeskManager.initialize()` to register all desks
19. Verify all 13 DB desk_ids resolve to a running BaseDesk subclass
20. End-to-end test: submit task via API → routed → handled → result

---

## Risk Notes

- **ForgeDesk is production** — don't break it during consolidation
- **DB desk configs drive the frontend UI** — changing desk_ids would break the dashboard
- **Standalone agents have no real API calls** — they're stubs, so we're porting logic patterns, not live integrations
- **Legacy DeskManager may be imported elsewhere** — grep for `from.*desk_manager import` before deleting
- **TelegramBot has real credentials** — treat token migration carefully

---

## Success Criteria

- [ ] Single `desks/` directory contains all desk logic
- [ ] Every DB `desk_config` row maps to a `BaseDesk` subclass (or routes to one)
- [ ] Legacy `desk_manager.py` deleted, no imports remain
- [ ] `~/Empire/agents/` archived, no active imports
- [ ] `AIDeskManager.initialize()` registers all desks
- [ ] `DeskRouter` can route tasks to every desk (LLM + keyword fallback)
- [ ] ForgeDesk still works identically
- [ ] Morning briefing includes all desks
