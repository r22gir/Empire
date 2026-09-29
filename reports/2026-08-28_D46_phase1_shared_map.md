# D46 · Phase 1 — Shared Map (read-only)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `ee43f0b`
**DB opened read-only via** `sqlite3.connect('file:/home/rg/empire-data/empire.db?mode=ro', uri=True)`
**Note (read-only warning):** the prod directory already contains a
zero-byte sibling at `empire.db?mode=ro` from a past mistake; that
file is left untouched and not part of this audit.

---

## 1a — The customer count, four screens

### Screen 1 · ForgeCRM header (5)

- **Component:** `empire-command-center/app/components/business/crm/CustomerList.tsx`
- **File:** `app/components/screens/ForgeCRMPage.tsx:92` mounts `<CustomerList ... business="woodcraft" />`
- **Endpoint:** `GET /api/v1/crm/customers?business=woodcraft`
  (default `limit=100`; backend `customer_mgmt.py:57`)
- **SQL:** `SELECT * FROM customers WHERE business = 'woodcraft' ORDER BY name ASC LIMIT 100`
- **Header value:** `customers.length` rendered at `CustomerList.tsx:600`
- **DB truth:** 5 rows where `business='woodcraft'` — **VERIFIED**.

### Screen 2 · ForgeCRM Quick Stats (500, $100,338.63)

- **Component:** `empire-command-center/app/components/screens/ForgeCRMPage.tsx`
- **Endpoint:** `GET /api/v1/crm/customers?limit=500` (no business filter)
- **SQL:** `SELECT * FROM customers ORDER BY name ASC LIMIT 500` (no WHERE)
- **Header value:** `stats.total` from `custs.length` — capped at 500
- **Revenue:** `stats.revenue = sum(total_revenue)` over the fetched 500
- **DB truth:** sum over the first 500 customers by name ASC = **$100,338.63** — **VERIFIED**.
- **Total customers in table:** 557 (not visible on the screen — the 57 oldest are not in the cap)

### Screen 3 · Workroom › Customers (100, with Designers 6 / Residential 92 / Commercial 2)

- **Component:** `empire-command-center/app/components/business/crm/CustomerList.tsx`
- **File:** `WorkroomPage.tsx:105` mounts `<CustomerList ... business="workroom" />`
- **Endpoint:** `GET /api/v1/crm/customers?business=workroom` (default limit=100)
- **SQL:** `SELECT * FROM customers WHERE business = 'workroom' ORDER BY name ASC LIMIT 100`
- **Header value:** `customers.length` (badge at `CustomerList.tsx:600`) — 100
- **Per-type counts:** `counts` derived from filtered `customers` array at `CustomerList.tsx:527-534`
- **DB truth (first 100 of 535 workroom customers by name ASC):**
  - residential: 92 — **VERIFIED**
  - designer: 6 — **VERIFIED**
  - commercial: 2 — **VERIFIED**
  - contractor: 0 (3 exist in full table; not in first 100)
- **Total workroom:** 535

### Screen 4 · Workroom › Overview (5 Customers · 5 recent)

- **Component:** `empire-command-center/app/components/screens/WorkroomPage.tsx:195-`
- **Endpoint:** `GET /api/v1/crm/customers?limit=5&sort_by=updated_at&sort_dir=desc&business=workroom`
- **SQL:** `SELECT * FROM customers WHERE business = 'workroom' ORDER BY updated_at DESC LIMIT 5`
- **"5 Customers" value:** `finance?.customers?.total || customers.length || 0`. The `/api/v1/finance/dashboard` response has no `customers.total` field — verified at `finance.py:1053-1082` — so the fallback is `customers.length` = **5**.
- **"5 recent" sub:** `${customers.length} recent` — same 5.
- **DB truth:** the limit-5 query returns 5 rows — **VERIFIED**.
- **Total workroom customers (real):** 535. The "5" is the API-returned count for a 5-row limit, not the table total.

### Which number is correct?

| Screen | Reported | Actual table reality |
|---|---|---|
| ForgeCRM header | **5** (woodcraft customers) | 5 woodcraft customers in `customers` table — exact match |
| ForgeCRM Quick Stats | **500** (count cap) / **$100,338.63** (revenue over those 500) | 557 total; sum over ALL 557 is also **$100,338.63** (revenue is sum-stable because the 57 oldest customers have $0 total_revenue) |
| Workroom Customers | **100** (count cap of 535) | 535 workroom customers exist |
| Workroom Overview | **5 / 5 recent** (count cap of 535) | 535 workroom customers exist |

**No number is wrong.** Each number is correct for the query it represents. The four screens are computing different things from different queries. The display is accurate to the data the query returns.

---

## 1b — Fixtures in production (NOT deleted — evidence only)

### Customers fixtures

| id | name | email | type | business | source | created_at |
|---|---|---|---|---|---|---|
| 1000a947 | `[MOCK EXAMPLE — not an EmpireBox record] Jane Demo` | (empty) | residential | workroom | (NULL) | 2026-08-24 15:51:21 |
| b7adff25 | `[MOCK EXAMPLE — not an EmpireBox record] Jane Demo` | (empty) | residential | workroom | (NULL) | 2026-08-24 16:00:44 |
| 4aac02ec | `Canonical Customer 85c2440d` | (empty) | — | — | — | 2026-08-23 15:05:03 |
| … 55 more `Canonical Customer <hash>` rows … | | | | | | 2026-08-23 / 2026-08-24 |
| 3f817faf1543f049 | `Jane Smith` | jane@example.com | — | — | — | 2026-04-29 22:20:44 |
| 3c40bfb6df79f7d4 | `Founder WoodCraft Audit` | founder-woodcraft-audit@example.com | — | — | — | 2026-04-25 03:06:18 |
| 2238533faf384f40 | `Founder WoodCraft Persist` | founder-woodcraft-persist@example.com | — | — | — | 2026-04-25 03:08:49 |

**Counts:** 2 `[MOCK EXAMPLE]` · 56 `Canonical Customer` · 1 `Jane Smith` · 2 `Founder WoodCraft *`

### Quotes fixtures

| quote_number | customer_name | total | status | created_at |
|---|---|---|---|---|
| EST-2026-261 | `[MOCK EXAMPLE — not an EmpireBox record] Jane Demo` | $1,512.40 | draft | 2026-08-24 09:04 |
| EST-2026-257 | Canonical Customer 15715831 | $123.45 | draft | 2026-08-23 11:04 |
| EST-2026-258 | Canonical Customer 05cacb1c | $123.45 | draft | 2026-08-23 11:04 |
| EST-2026-259 | Canonical Customer 85c2440d | $123.45 | draft | 2026-08-23 11:04 |
| EST-2026-082 | Demo Client | $0.00 | draft | 2026-04-03 |
| EST-2026-082-c9aa | Demo Client | $0.00 | proposal | 2026-04-03 |
| 64 TrustTest rows | TrustTest | mostly $100/$108.25 | mixed | 2026-08-22 / 23 |
| 18 HOTFIX5 Test rows | HOTFIX5 Test | $2,900 / $3,133.33 / $3,600 | draft | 2026-08-23 |
| 24 Canonical Customer rows | Canonical Customer <hash> | $123.45 | draft | 2026-08-22 / 23 |

**Counted in Workroom pipeline ($28,046.96)?**
- EST-2026-261 [MOCK] = **yes** ($1,512.40)
- EST-2026-257/258/259 [Canonical] = **yes** ($370.35 total)
- 8 TrustTest in pipeline (EST-2026-243..250) = **yes** ($808.25)
- 5 HOTFIX5 in pipeline (EST-2026-251..255) = **yes** ($15,666.66)
- Total fixtures in pipeline: **$18,357.66**

**Counted in ForgeCRM Quick Stats revenue ($100,338.63)?**
- All 557 customers (including 56 Canonical + 2 MOCK + 1 Jane Smith + 2 Founder WoodCraft) appear in the `total_revenue` sum.
- 56 Canonical: each has 0 quotes referenced from the customer row (canonical rows have `total_revenue=NULL` or 0)
- 2 [MOCK EXAMPLE] customers: total_revenue = NULL (created without quotes; quotes_v2 carries the Jane Demo quote but it's a draft and not in their revenue)
- 1 Jane Smith: 0 quotes
- 2 Founder WoodCraft: 0 quotes

The sum is not noticeably inflated by fixture rows because their `total_revenue` columns are NULL/0. **Quotes_v2 fixture customers** carry their amounts on quotes_v2, not customers — but Workroom › Customers screen count is inflated by the 100-row cap (which includes 0-quote fixtures). The pipeline dollar figure ($28,046.96) IS inflated by **$18,357.66 of fixtures**.

### Origin attribution (what created them)

| Fixture pattern | Source identified |
|---|---|
| `[MOCK EXAMPLE — not an EmpireBox record] Jane Demo` (2 customers + 1 quote) | **VERIFIED:** `backend/app/services/max/system_prompt.py:385` includes this literal as a guard for MAX's mock-quote creation feature. The founder asked MAX via chat to create a mock quote; MAX wrote a real record to `quotes_v2` (EST-2026-261, $1,512.40) and created 2 customers in the chat flow. Founder-flagged by the `[MOCK EXAMPLE]` prefix but still in the real DB. |
| `Canonical Customer <hash>` (56 customers + 24 quotes) | **VERIFIED:** `backend/tests/test_quote_tools_canonical_hotfix.py:46` calls `create_quote({customer_name: "Canonical Customer <marker>", ...})`. The file's docstring (lines 17–21) claims HOTFIX 4 wired it to the isolated test DB, but rows dated 2026-08-23 to 2026-08-24 are **in the prod DB**, not the test DB. The HOTFIX 4 isolation fix is incomplete for this file (or was bypassed by some other code path that also creates these rows). |
| `Jane Smith` / `Founder WoodCraft Audit` / `Founder WoodCraft Persist` | **NOT identified in current source.** Timestamps 2026-04-25 to 2026-04-29 predate the HOTFIX 4 conftest isolation fix (2026-07-15). Likely from pre-fix pytest runs that wrote to prod. Unidentified source file. |
| `TrustTest` (64 quotes) | **VERIFIED:** `backend/tests/test_quote_pin_bypass_hotfix4_1.py:84` writes `customer_name: "TrustTest"` via `create_quote`. The file reads `os.environ["EMPIRE_TASK_DB"]` and would route to the isolated test DB if the conftest ran first. Rows dated 2026-08-22/23 are **after** the HOTFIX 4 conftest fix — yet they are in prod. Same defect class as `Canonical Customer`: the conftest's isolation is incomplete for this file. |
| `HOTFIX5 Test` (18 quotes) | **NOT identified in current source.** Timestamps 2026-08-23. Probably HOTFIX 5 test fixtures (the file name `test_quote_price_override_hotfix5.py` matches). Unidentified source file (the fixture string wasn't found in this file's source via grep). |
| `Demo Client` (2 quotes) | **NOT identified.** Timestamps 2026-04-03. Old pre-fix. |

**Origin summary:**
- **Verified creation paths (current source):** `test_quote_tools_canonical_hotfix.py:46` (Canonical), `test_quote_pin_bypass_hotfix4_1.py:84` (TrustTest), `system_prompt.py:385` mock-quote feature ([MOCK EXAMPLE])
- **Unidentified (legacy pre-fix or current source grep misses):** Jane Smith, Founder WoodCraft Audit/Persist, HOTFIX5 Test, Demo Client

### Per-row — whether it is counted in any figure shown on a screen

- 56 Canonical Customer + 2 [MOCK EXAMPLE] + 1 Jane Smith + 2 Founder WoodCraft = **61 fixture customers**
  - **Counted in:** Workroom › Customers (100, capped, includes fixture rows); ForgeCRM Quick Stats (500, capped, sum is not inflated because fixture `total_revenue` is 0); ForgeCRM header (5, but ONLY if filtered by `business='woodcraft'` — and none of the 61 are woodcraft, so this 5 is real)
- 12 fixture quotes in the Workroom pipeline → **$18,357.66** of the displayed $28,046.96

**One row that needs founder attention before any delete:** the `[MOCK EXAMPLE]` records are clearly flagged in their own text but the prefix lives in `customer_name` and `customer_email` only — a single-space typo or strip would erase the warning. The dispatch notes "one of them may be inside a real invoice" — the MOCK EXAMPLE quote (EST-2026-261) has a PDF on disk (`/home/rg/empire-data/quotes/pdf/EST-2026-261.pdf`) and has been referenced in chat history. **Do not delete without checking PDF references first.**

---

## 1c — $28,046.96 revenue pipeline

### The query

```
GET /api/v1/quotes-v2?limit=20&business=workroom
```

at `WorkroomPage.tsx:67`, default sort order. Backend route at
`backend/app/routers/quotes_v2.py` — exact match returns 20 quotes
ordered by `created_at DESC` (verified via the manual SQL run).

### Itemization (first 20 by created_at DESC)

| # | Quote # | Customer | Total | Status | Fixture? |
|---|---|---|---|---|---|
| 1 | EST-2026-262 | Becky | $4,084.05 | draft | real |
| 2 | EST-2026-261 | [MOCK EXAMPLE — not an EmpireBox record] Jane Demo | $1,512.40 | draft | **FIXTURE** |
| 3 | EST-2026-260 | Danielle Ferguson III | $5,506.25 | draft | real |
| 4 | EST-2026-259 | Canonical Customer 85c2440d | $123.45 | draft | **FIXTURE** |
| 5 | EST-2026-258 | Canonical Customer 05cacb1c | $123.45 | draft | **FIXTURE** |
| 6 | EST-2026-257 | Canonical Customer 15715831 | $123.45 | draft | **FIXTURE** |
| 7 | EST-2026-256 | Routed Customer 819acc2c | $99.00 | draft | **FIXTURE** |
| 8 | EST-2026-255 | HOTFIX5 Test | $2,900.00 | draft | **FIXTURE** |
| 9 | EST-2026-254 | HOTFIX5 Test | $3,133.33 | draft | **FIXTURE** |
| 10 | EST-2026-253 | HOTFIX5 Test | $2,900.00 | draft | **FIXTURE** |
| 11 | EST-2026-252 | HOTFIX5 Test | $3,600.00 | draft | **FIXTURE** |
| 12 | EST-2026-251 | HOTFIX5 Test | $3,133.33 | draft | **FIXTURE** |
| 13 | EST-2026-250 | TrustTest | $100.00 | founder_review | **FIXTURE** |
| 14 | EST-2026-249 | TrustTest | $100.00 | founder_review | **FIXTURE** |
| 15 | EST-2026-248 | TrustTest | $100.00 | founder_review | **FIXTURE** |
| 16 | EST-2026-247 | TrustTest | $100.00 | sent | **FIXTURE** |
| 17 | EST-2026-246 | TrustTest | $100.00 | founder_review | **FIXTURE** |
| 18 | EST-2026-245 | TrustTest | $108.25 | draft | **FIXTURE** |
| 19 | EST-2026-244 | TrustTest | $100.00 | draft | **FIXTURE** |
| 20 | EST-2026-243 | TrustTest | $100.00 | founder_review | **FIXTURE** |

**Sum:** $28,046.96 — **VERIFIED**.

### Sum with fixtures excluded

- Real rows in the 20: Becky ($4,084.05) + Danielle Ferguson III ($5,506.25) = **$9,590.30**
- Fixture rows in the 20: $18,357.66 (see table above for breakdown)
- **Real-to-fixture ratio:** 33.6% / 66.4%

The pipeline is two-thirds fixtures. Of the fixture total, HOTFIX5 Test alone accounts for $15,666.66 (55.8% of the displayed pipeline; 85.2% of the fixtures in the pipeline).

---

## 1d — SYSTEM (6) sidebar items

| # | Sidebar name | Component | Endpoints hit | What it does |
|---|---|---|---|---|
| 1 | PlatformForge | `PlatformPage.tsx` | `GET /system/stats`, `GET /system/metrics`, `GET /max/system-report` | CPU/RAM/disk/temps/brain-sync; active_ports grid; OpenClaw port 7878 indicator |
| 2 | OpenClaw | `OpenClawTasksPage.tsx` | (mostly internal task API; legacy OpenClaw queue) | OpenClaw task list with create-new form |
| 3 | MAX Continuity | `MaxContinuityScreen.tsx` | (read-only views; no live fetches visible in component) | Runtime truth, handoff state, OpenClaw gate health, recent MAX evaluation signals |
| 4 | System | `SystemReportScreen.tsx` | `GET /max/system-report` | Legacy system report view (overlaps with PlatformForge's `/max/system-report` fetch) |
| 5 | Tokens & Costs | `CostTracker.tsx` (lazy in `page.tsx:70`) | (cost/token endpoints; uses `useSystemData()` hook) | Token usage and cost breakdown |
| 6 | Hardware | `EcosystemProductPage.tsx` (status='dev') | `GET /system/stats` (EcosystemProductPage fetches at `:118`) | Generic product page shell — Hardware product is `status='dev'` per `LeftNav.tsx:111` |

---

## 1e — Payments / Docs / Customers duplication

### Payments (5+)

All callers use the **same** `PaymentModule` component parameterized by `product`:

| Caller file | Product param |
|---|---|
| `EmpirePayPage.tsx:801` | `pay` |
| `EmpireAssistPage.tsx:416` | `assist` |
| `ForgeCRMPage.tsx:233` | `crm` |
| `SocialForgePage.tsx:1358` | `social` |
| `ShipForgePage.tsx:118` | `ship` |
| `WorkroomPage.tsx:134` | `workroom` |
| `MarketForgePage.tsx:875` | `market` |
| `VisionAnalysisPage.tsx:307` | `vision` |
| `LLCFactoryPage.tsx:614` | `llc` |
| `ContractorForgePage.tsx:252` | `contractor` |
| `LeadForgePage.tsx:861` | `lead` |
| `ApostAppPage.tsx:2263` | `apost` |
| `CraftForgePage.tsx:64` | `craft` |
| `SupportForgePage.tsx:701` | `support` |

→ **14 callers, ONE shared component.**

### Docs (7+)

All callers use the **same** `ProductDocs` component parameterized by `product`:

| Caller file | Product param |
|---|---|
| `EmpirePayPage.tsx:802` | `pay` |
| `EmpireAssistPage.tsx:417` | `assist` |
| `LuxeForgePage.tsx:307` | `luxe` |
| `ForgeCRMPage.tsx:236` | `crm` |
| `VendorOpsPage.tsx:562` | `vendorops` |
| `EcosystemProductPage.tsx:598` | `productId` |
| `SocialForgePage.tsx:1362` | `social` |
| `RelistAppPage.tsx:58` | `relist` |
| `ShipForgePage.tsx:119` | `ship` |

→ **9 callers, ONE shared component.**

### Customers (4+)

| Caller file | Component | Endpoint hit |
|---|---|---|
| `ForgeCRMPage.tsx:92` | `<CustomerList ... business="woodcraft" />` | `GET /api/v1/crm/customers?business=woodcraft` |
| `WorkroomPage.tsx:105` | `<CustomerList ... business="workroom" />` | `GET /api/v1/crm/customers?business=workroom` |
| `LLCFactoryPage.tsx:609, :1080` | local `CustomersSection` | likely `/api/v1/llc/customers` or `/api/v1/crm/customers` |
| `ApostAppPage.tsx:2253` | local `renderCustomers()` | likely `/api/v1/apostapp/public/customers` or its own private |
| `CraftForgePage.tsx:57` | (likely local) | (TBD in Phase 3 batch) |
| `StoreFrontForgePage.tsx:47, :327` | local `CustomersSection` | likely `/api/v1/storefront/customers` |
| `SupportForgePage.tsx:699` | `<CustomersTab />` | (TBD in Phase 3 batch) |

→ **2 products use shared `CustomerList`; 5+ products use local implementations.**

### Verdict on duplication

- **Payments:** shared (1 component, 14 callers)
- **Docs:** shared (1 component, 9 callers)
- **Customers:** **partially duplicated** — 2 of 7+ products share a component; the rest are local

For the Customers surface, a single `CustomerList` with a `business` prop already exists and is used by ForgeCRM + Workroom. The 5+ local Customers implementations likely hit different backend endpoints (e.g., `/api/v1/llc/customers`, `/api/v1/apostapp/private/customers`, etc.) — they are not interchangeable with the ForgeCRM/Workroom CustomerList. **Phases 2 / 3 will need to enumerate each one's endpoint to confirm whether they share data.**

---

## STOP 1 — note

The dispatch amended to "All three phases run. Phase 3 is not gated."
This report is committed as the Phase 1 deliverable. The audit
continues to Phase 2.

No writes, no deletes, no restarts. Fixtures are reported and left in
place per the standing rule.