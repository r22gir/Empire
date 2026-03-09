# Empire Command Center — Frontend-to-Backend Wiring Audit

**Audit Date:** 2026-03-08
**Frontend:** `/home/rg/empire-repo/empire-command-center/app/`
**Backend:** `/home/rg/empire-repo/backend/app/`
**API Base:** `http://localhost:8000/api/v1` (set via `NEXT_PUBLIC_API_URL`)

---

## 1. All Frontend API Endpoints & Status

### Legend
- **OK** — Route exists in backend and is registered in main.py with correct prefix
- **404** — Route does not exist or prefix mismatch causes 404
- **MISSING** — No backend route exists at all

| Frontend File | Frontend Calls | Resolved URL | Backend Router | Backend Route | Status |
|---|---|---|---|---|---|
| DocumentScreen.tsx | `API + '/files'` | `/api/v1/files` | `api.v1.files` (prefix `/files`, loaded at `/api/v1`) | `GET /files` implied | **OK** |
| ChatScreen.tsx | `API + '/files/upload'` | `/api/v1/files/upload` | `api.v1.files` | POST `/upload` | **OK** |
| ChatScreen.tsx | `/api/transcribe` | `/api/transcribe` | `main.py` inline route | POST `/api/transcribe` | **OK** |
| ChatScreen.tsx | `API + '/max/tts'` | `/api/v1/max/tts` | `routers.max` (prefix `/max`, loaded at `/api/v1`) | POST `/tts` | **OK** |
| ResearchScreen.tsx | `API + '/max/chat/stream'` | `/api/v1/max/chat/stream` | `routers.max` | POST `/chat/stream` | **OK** |
| ResearchScreen.tsx | `API + '/memory/search?q=...'` | `/api/v1/memory/search` | `routers.memory` (no prefix, loaded at `/api/v1`) | GET `/memory/search` | **OK** |
| DashboardScreen.tsx | `API + '/quotes?limit=10'` | `/api/v1/quotes` | `routers.quotes` (prefix `/quotes`, loaded at `/api/v1`) | GET `""` | **OK** |
| QuoteReviewScreen.tsx | `API + '/quotes?limit=1'` | `/api/v1/quotes` | `routers.quotes` | GET `""` | **OK** |
| QuoteReviewScreen.tsx | `API + '/quotes/' + id` | `/api/v1/quotes/{id}` | `routers.quotes` | GET `/{quote_id}` | **OK** |
| QuoteReviewScreen.tsx | `API + '/max/chat/stream'` | `/api/v1/max/chat/stream` | `routers.max` | POST `/chat/stream` | **OK** |
| WorkroomPage.tsx | `API + '/quotes?limit=20'` | `/api/v1/quotes` | `routers.quotes` | GET `""` | **OK** |
| InboxScreen.tsx | `API + '/notifications'` | `/api/v1/notifications` | `routers.notifications` (no prefix, loaded at `/api/v1`) | GET `/notifications` | **OK** |
| InboxScreen.tsx | `API + '/quotes?limit=5'` | `/api/v1/quotes` | `routers.quotes` | GET `""` | **OK** |
| InboxScreen.tsx | `API + '/max/desks/status'` | `/api/v1/max/desks/status` | `routers.max` | GET `/desks/status` | **OK** |
| PlatformPage.tsx | `API + '/max/system'` | `/api/v1/max/system` | **NONE** | — | **404** |
| PlatformPage.tsx | `API + '/max/services'` | `/api/v1/max/services` | **NONE** | — | **404** |
| DesksScreen.tsx | `API + '/max/ai-desks/{id}/detail'` | `/api/v1/max/ai-desks/{id}/detail` | `routers.max` | GET `/ai-desks/{desk_id}/detail` | **OK** |
| DesksScreen.tsx | `API + '/tasks?desk={id}&limit=50'` | `/api/v1/tasks` | `routers.tasks` (prefix `/tasks`, loaded at `/api/v1`) | GET implied via query | **OK** |
| DesksScreen.tsx | `API + '/max/ai-desks/tasks'` | `/api/v1/max/ai-desks/tasks` | `routers.max` | POST `/ai-desks/tasks` | **OK** |
| SystemReportScreen.tsx | `API + '/max/system-report'` | `/api/v1/max/system-report` | `routers.max` | GET `/system-report` | **OK** |
| SystemReportScreen.tsx | `API + '/max/changelog'` | `/api/v1/max/changelog` | `routers.max` | GET `/changelog` | **OK** |
| CostTracker.tsx | `API + '/costs/overview?days=30'` | `/api/v1/costs/overview` | `routers.costs` (no prefix, loaded at `/api/v1`) | GET `/costs/overview` | **OK** |
| CostTracker.tsx | `API + '/costs/transactions?limit=100'` | `/api/v1/costs/transactions` | `routers.costs` | GET `/costs/transactions` | **OK** |
| CostTracker.tsx | `API + '/costs/by-provider?days=30'` | `/api/v1/costs/by-provider` | `routers.costs` | GET `/costs/by-provider` | **OK** |
| CostTracker.tsx | `API + '/costs/by-feature?days=30'` | `/api/v1/costs/by-feature` | `routers.costs` | GET `/costs/by-feature` | **OK** |
| CostTracker.tsx | `API + '/costs/by-business?days=30'` | `/api/v1/costs/by-business` | `routers.costs` | GET `/costs/by-business` | **OK** |
| CostTracker.tsx | `API + '/costs/daily?days=30'` | `/api/v1/costs/daily` | `routers.costs` | GET `/costs/daily` | **OK** |
| CostTracker.tsx | `API + '/costs/weekly?weeks=12'` | `/api/v1/costs/weekly` | `routers.costs` | GET `/costs/weekly` | **OK** |
| CostTracker.tsx | `API + '/costs/monthly?months=12'` | `/api/v1/costs/monthly` | `routers.costs` | GET `/costs/monthly` | **OK** |
| FinanceDashboard.tsx | `API + '/finance/dashboard?range=...'` | `/api/v1/finance/dashboard` | `routers.finance` (prefix `/finance`, loaded at `/api/v1`) | GET `/dashboard` | **OK** |
| FinanceDashboard.tsx | `API + '/finance/payments?limit=10'` | `/api/v1/finance/payments` | `routers.finance` | GET `/payments` | **OK** |
| FinanceDashboard.tsx | `API + '/finance/expenses?limit=10'` | `/api/v1/finance/expenses` | `routers.finance` | GET `/expenses` | **OK** |
| ExpenseTracker.tsx | `API + '/finance/expenses'` | `/api/v1/finance/expenses` | `routers.finance` | GET/POST `/expenses` | **OK** |
| InvoiceList.tsx | `API + '/finance/invoices'` | `/api/v1/finance/invoices` | `routers.finance` | GET/POST `/invoices` | **OK** |
| TicketsPage.tsx | `API + '/tickets/'` | `/api/v1/tickets/` | `routers.supportforge_tickets` (no prefix, loaded at `/api/v1/tickets`) | GET/POST `/` | **OK** |
| TicketsPage.tsx | `API + '/tickets/{id}'` | `/api/v1/tickets/{id}` | `routers.supportforge_tickets` | GET/PATCH/DELETE `/{ticket_id}` | **OK** |
| TicketsPage.tsx | `API + '/tickets/{id}/messages'` | `/api/v1/tickets/{id}/messages` | `routers.supportforge_tickets` | POST `/{ticket_id}/messages` | **OK** |
| CraftForgePage.tsx | `API + '/craftforge/jobs'` | `/api/v1/craftforge/jobs` | `routers.craftforge` (no prefix, loaded at `/api/v1/craftforge`) | GET `/jobs` | **OK** |
| CraftForgePage.tsx | `API + '/craftforge/designs'` | `/api/v1/craftforge/designs` | `routers.craftforge` | GET `/designs` | **OK** |
| CraftForgePage.tsx | `API + '/craftforge/customers'` | `/api/v1/craftforge/customers` | `routers.craftforge` | GET `/customers` | **OK** |
| CraftForgePage.tsx | `API + '/inventory/items?business=craftforge'` | `/api/v1/inventory/items` | `routers.inventory` (prefix `/inventory`, loaded at `/api/v1`) | GET `/items` | **OK** |
| SocialForgePage.tsx | `SF_API + '/dashboard'` etc. | `/api/v1/socialforge/*` | `routers.socialforge` (loaded at `/api/v1/socialforge`) | — | **Needs verification** |
| ShippingPage.tsx | `SHIP_API + '/shipping/*'` | `/shipping/*` | `routers.shipping` (no prefix, loaded at `/shipping`) | `/rates`, `/labels`, `/track/...`, `/history` | **OK** |
| JobBoard.tsx | `API + '/jobs/'` | `/api/v1/jobs/` | `routers.jobs` (prefix `/jobs`, loaded at `/api/v1`) | GET `/` | **OK** |
| JobBoard.tsx | `API + '/jobs/from-quote/{id}'` | `/api/v1/jobs/from-quote/{id}` | `routers.jobs` | POST `/from-quote/{quote_id}` | **OK** |
| CalendarView.tsx | `API + '/jobs/calendar'` | `/api/v1/jobs/calendar` | `routers.jobs` | GET `/calendar` | **OK** |
| CustomerList.tsx | `API + '/crm/customers'` | `/api/v1/crm/customers` | `routers.customer_mgmt` (prefix `/crm`, loaded at `/api/v1`) | GET `/customers` | **OK** |
| CustomerList.tsx | `API + '/crm/customers/import-from-quotes'` | `/api/v1/crm/customers/import-from-quotes` | `routers.customer_mgmt` | POST `/customers/import-from-quotes` | **OK** |
| CustomerDetail.tsx | `API + '/crm/customers/{id}'` | `/api/v1/crm/customers/{id}` | `routers.customer_mgmt` | GET `/customers/{customer_id}` | **OK** |
| CustomerDetail.tsx | `API + '/crm/customers/{id}/{endpoint}'` | `/api/v1/crm/customers/{id}/quotes` etc. | `routers.customer_mgmt` | GET `/customers/{customer_id}/quotes` etc. | **OK** |
| QuoteActions.tsx | `API + url` (dynamic) | various `/api/v1/...` | Depends on action | Depends on action | **OK** (passthrough) |

---

## 2. Known Broken Endpoints — Detailed Analysis

### 2.1 `/api/v1/max/system` — **404 (MISSING ROUTE)**
- **Called by:** `PlatformPage.tsx` line 11
- **Problem:** The MAX router (`routers/max/router.py`) has NO `/system` endpoint. It has `/system-report` (line 889) but not `/system`.
- **Nearby match:** `system_monitor.py` has `/system/stats` loaded at `/api/v1` → resolves to `/api/v1/system/stats`.
- **Fix:** Either add a `/system` route to the MAX router, or change frontend to call `API + '/system/stats'`.

### 2.2 `/api/v1/max/services` — **404 (MISSING ROUTE)**
- **Called by:** `PlatformPage.tsx` line 12
- **Problem:** No `/services` endpoint exists anywhere in the MAX router or system_monitor.
- **Fix:** Add a `GET /services` endpoint to the MAX router (or system_monitor) that returns service status info.

### 2.3 `/api/v1/finance/invoices` — **OK (ROUTE EXISTS)**
- **Called by:** `InvoiceList.tsx` lines 65, 194
- **Backend:** `routers/finance.py` has `GET /invoices` and `POST /invoices` with `prefix="/finance"`, loaded at `/api/v1`.
- **Resolved path:** `/api/v1/finance/invoices` — **this should work**.
- **If still showing 404:** The issue is likely a runtime error in the finance router (DB connection, missing table, import error). Check `load_router` output at startup.

### 2.4 `/api/v1/finance/expenses` — **OK (ROUTE EXISTS)**
- **Called by:** `FinanceDashboard.tsx` line 64, `ExpenseTracker.tsx` lines 49, 69
- **Backend:** `routers/finance.py` has `GET /expenses` and `POST /expenses`.
- **Same note as invoices** — if 404, it's a runtime load failure.

### 2.5 `/api/v1/notifications` — **OK (ROUTE EXISTS)**
- **Called by:** `InboxScreen.tsx` line 31
- **Backend:** `routers/notifications.py` has `GET /notifications`, no prefix, loaded at `/api/v1`.
- **Resolved path:** `/api/v1/notifications` — **should work**.
- **Caveat:** Registered AFTER `if __name__` block in main.py (line 208). This is fine for uvicorn but unusual. If running via `python main.py`, routers after line 203 won't be registered until after the server starts (race condition, but uvicorn import-based loading avoids this).

### 2.6 `/api/v1/quotes/quick` — **MISSING ROUTE**
- **Not found in any frontend file** in the command center (no reference to `/quotes/quick`).
- **Backend:** `routers/quotes.py` has no `/quick` endpoint.
- **Status:** Not called by this frontend. May be called by a different frontend (WorkroomForge?).

### 2.7 `/api/v1/tasks` — **OK (ROUTE EXISTS)**
- **Called by:** `DesksScreen.tsx` line 80 (`/tasks?desk={id}&limit=50`)
- **Backend:** `routers/tasks.py` has `prefix="/tasks"`, loaded at `/api/v1`. Registered at line 212.
- **Resolved path:** `/api/v1/tasks` — **should work**.

### 2.8 `/api/v1/max/ai-desks/*` — **OK (ROUTES EXIST)**
- **Called by:** `DesksScreen.tsx` lines 79, 107
- **Backend:** `routers/max/router.py` has:
  - `GET /ai-desks/{desk_id}/detail` (line 702)
  - `POST /ai-desks/tasks` (line 672)
  - `GET /ai-desks/status` (line 695)
- **Resolved via:** MAX router prefix `/max` + load prefix `/api/v1` → `/api/v1/max/ai-desks/*`.

### 2.9 `/api/v1/max/system-report` — **OK (ROUTE EXISTS)**
- **Called by:** `SystemReportScreen.tsx` line 34
- **Backend:** `routers/max/router.py` has `GET /system-report` (line 889).
- **Resolved path:** `/api/v1/max/system-report` — **should work**.

### 2.10 `/api/v1/costs/*` — **OK (ALL ROUTES EXIST)**
- **Called by:** `CostTracker.tsx` lines 86-112
- **Backend:** `routers/costs.py` has all matching endpoints (overview, transactions, by-provider, by-feature, by-business, daily, weekly, monthly). No prefix, loaded at `/api/v1`.

---

## 3. Summary of Issues Found

### Confirmed Missing Endpoints (will 404)

| Endpoint | Called By | Issue | Fix Needed |
|---|---|---|---|
| `/api/v1/max/system` | PlatformPage.tsx:11 | No route exists | Add `GET /system` to MAX router OR change frontend to `/system/stats` |
| `/api/v1/max/services` | PlatformPage.tsx:12 | No route exists | Add `GET /services` to MAX router returning service health list |

### Possibly Broken (routes exist but may fail at runtime)

| Endpoint | Called By | Concern |
|---|---|---|
| `/api/v1/finance/invoices` | InvoiceList.tsx | Route exists. If 404, check if `routers.finance` fails to load (DB/import error). Run backend and check startup logs for `✗ Failed app.routers.finance`. |
| `/api/v1/finance/expenses` | ExpenseTracker.tsx, FinanceDashboard.tsx | Same as above — shares the finance router. |
| `/api/v1/notifications` | InboxScreen.tsx | Route registered after `if __name__` block (line 208). Works with uvicorn but placement is unusual. |
| `/api/v1/desks/*` and `/api/v1/tasks/*` | DesksScreen.tsx | Registered after `if __name__` block (lines 211-213). Same caveat. |

### Router Registration Ordering Issue

Lines 207-224 in `main.py` register routers **after** the `if __name__ == "__main__"` block. While this works when the app is loaded via `uvicorn app.main:app` (because Python executes the entire module), it is a code smell and could cause confusion. The following routers are affected:

- `routers.notifications` (line 208)
- `routers.desks` (line 211)
- `routers.tasks` (line 212)
- `routers.contacts` (line 213)
- `routers.onboarding` (line 216)
- `smart_analyzer` (lines 219-224)

**Recommendation:** Move these `load_router()` calls above the `if __name__` block for clarity.

---

## 4. Quick Fix Checklist

1. **PlatformPage.tsx** — Two options:
   - **(A) Frontend fix:** Change `API + '/max/system'` to `API + '/system/stats'` and remove or replace the `/max/services` call.
   - **(B) Backend fix:** Add two new endpoints to `routers/max/router.py`:
     - `GET /system` — proxy to system_monitor stats
     - `GET /services` — return list of Empire services and their status

2. **main.py ordering** — Move lines 207-224 above the `if __name__` guard (line 203). This is a cleanliness fix, not a bug, but prevents future confusion.

3. **Runtime load failures** — If invoices/expenses/notifications still 404 despite routes existing, run:
   ```bash
   cd ~/Empire/backend && source ~/Empire/venv/bin/activate
   python -c "from app.main import app; print('All routers loaded')"
   ```
   Check output for any `✗ Failed` lines to identify import/DB errors.

---

## 5. Backend Router Files Reference

| Router File | Prefix in File | Loaded at (main.py) | Effective Path |
|---|---|---|---|
| `routers/max/router.py` | `/max` | `""` and `/api/v1` | `/max/*` and `/api/v1/max/*` |
| `routers/quotes.py` | `/quotes` | `/api/v1` | `/api/v1/quotes/*` |
| `routers/notifications.py` | (none) | `/api/v1` | `/api/v1/notifications/*` |
| `routers/costs.py` | (none) | `/api/v1` | `/api/v1/costs/*` |
| `routers/finance.py` | `/finance` | `/api/v1` | `/api/v1/finance/*` |
| `routers/tasks.py` | `/tasks` | `/api/v1` | `/api/v1/tasks/*` |
| `routers/desks.py` | `/desks` | `/api/v1` | `/api/v1/desks/*` |
| `routers/customer_mgmt.py` | `/crm` | `/api/v1` | `/api/v1/crm/*` |
| `routers/inventory.py` | `/inventory` | `/api/v1` | `/api/v1/inventory/*` |
| `routers/jobs.py` | `/jobs` | `/api/v1` | `/api/v1/jobs/*` |
| `routers/craftforge.py` | (none) | `/api/v1/craftforge` | `/api/v1/craftforge/*` |
| `routers/socialforge.py` | — | `/api/v1/socialforge` | `/api/v1/socialforge/*` |
| `routers/memory.py` | (none) | `/api/v1` | `/api/v1/memory/*` |
| `routers/shipping.py` | (none) | `/shipping` | `/shipping/*` |
| `routers/system_monitor.py` | (none) | `/api/v1` | `/api/v1/system/*` |
| `routers/supportforge_tickets.py` | (none) | `/api/v1/tickets` | `/api/v1/tickets/*` |
| `routers/inbox.py` | `/inbox` | `/api/v1` | `/api/v1/inbox/*` |
| `api/v1/files.py` | `/files` | `/api/v1` | `/api/v1/files/*` |
