# QuickBooks Replacement — Full Backend/Frontend Audit

**Generated:** 2026-03-08
**Backend:** FastAPI on :8000 | **Frontend:** Command Center on :3009

---

## 1. ENDPOINT INVENTORY BY FEATURE

### QUOTES (10 endpoints) — ✅ FRONTEND WIRED
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| POST, GET | `/api/v1/quotes` | ✅ WorkroomPage, DashboardScreen, QuoteReviewScreen |
| GET, PATCH, DELETE | `/api/v1/quotes/{quote_id}` | ✅ QuoteReviewScreen |
| POST | `/api/v1/quotes/{quote_id}/accept` | ❌ Not wired |
| POST, GET | `/api/v1/quotes/{quote_id}/pdf` | ❌ Not wired |
| POST | `/api/v1/quotes/{quote_id}/photos` | ❌ Not wired |
| POST | `/api/v1/quotes/{quote_id}/send` | ❌ Not wired |
| POST, GET | `/api/v1/quote-requests` | ❌ Not wired |
| POST | `/api/v1/quote-requests/analyze-photo` | ❌ Not wired |
| GET | `/api/v1/quote-requests/{request_id}` | ❌ Not wired |
| POST | `/api/v1/quote-requests/{request_id}/quote` | ❌ Not wired |

**Data:** 26 quote JSON files, 24 PDFs. Rich schema: rooms, line_items, design_proposals, photos, AI mockups, deposit, tax.

---

### CUSTOMERS / CRM (7 endpoints) — ❌ NO FRONTEND
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| POST, GET | `/api/v1/customers/` | ❌ |
| GET, PATCH, DELETE | `/api/v1/customers/{customer_id}` | ❌ |
| GET | `/api/v1/customers/{customer_id}/context` | ❌ |
| GET | `/api/v1/customers/{customer_id}/tickets` | ❌ |
| POST, GET | `/api/v1/contacts/` | ❌ |
| GET, PATCH, DELETE | `/api/v1/contacts/{contact_id}` | ❌ |

**DB:** `contacts` table: 0 rows. `brain/memories.db` → `customers`: 0 rows, `customer_interactions`: 0 rows.

---

### FINANCE / ECONOMIC (7 endpoints) — ❌ NO FRONTEND
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| GET | `/api/v1/economic/.../dashboard/overview` | ❌ |
| GET | `/api/v1/economic/.../transactions` | ❌ |
| GET | `/api/v1/economic/.../ledger/{entity_type}/{entity_id}` | ❌ |
| GET | `/api/v1/economic/.../projects/{project_id}/efficiency` | ❌ |
| POST | `/api/v1/economic/.../quality/evaluate` | ❌ |
| POST | `/api/v1/economic/.../quality/evaluate-batch` | ❌ |
| GET | `/api/v1/economic/.../quality/prompt-example` | ❌ |

**Note:** Endpoints have a double-prefix bug: `/api/v1/economic/api/v1/economic/...`. No database tables for transactions/invoices/payments.

---

### TASKS (10 endpoints) — ✅ PARTIALLY WIRED
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| POST, GET | `/api/v1/tasks/` | ✅ DesksScreen (per-desk filter) |
| GET | `/api/v1/tasks/dashboard` | ❌ Not wired |
| GET, PATCH, DELETE | `/api/v1/tasks/{task_id}` | ❌ Not wired (modal shows cached data) |
| POST | `/api/v1/tasks/{task_id}/comment` | ❌ Not wired |
| POST, GET | `/api/v1/max/tasks` | ✅ DesksScreen (via ai-desks/tasks) |
| GET | `/api/v1/max/tasks/{task_id}` | ❌ |
| POST | `/api/v1/max/tasks/{task_id}/complete` | ❌ |
| POST | `/api/v1/max/tasks/{task_id}/fail` | ❌ |

**DB:** `tasks`: 45 rows, `task_activity`: 52 rows. Schema includes due_date, follow_up_date, recurrence, source, tags, metadata.

---

### CRAFTFORGE (10 endpoints) — ❌ NO FRONTEND WIRING (app exists but uses hardcoded data)
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| GET | `/api/v1/craftforge/dashboard` | ❌ |
| GET | `/api/v1/craftforge/customers` | ❌ |
| POST, GET | `/api/v1/craftforge/designs` | ❌ |
| GET, PATCH, DELETE | `/api/v1/craftforge/designs/{design_id}` | ❌ |
| POST, GET | `/api/v1/craftforge/inventory` | ❌ |
| PATCH, DELETE | `/api/v1/craftforge/inventory/{item_id}` | ❌ |
| POST, GET | `/api/v1/craftforge/jobs` | ❌ |
| GET, PATCH, DELETE | `/api/v1/craftforge/jobs/{job_id}` | ❌ |

**Data:** `data/craftforge/` directories exist (designs/, inventory/, jobs/, templates/) but all are empty (0 files).

---

### SOCIALFORGE (12 endpoints) — ✅ FRONTEND WIRED
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| GET | `/api/v1/socialforge/dashboard` | ✅ SocialForgePage |
| GET, PUT | `/api/v1/socialforge/profile` | ✅ SocialForgePage |
| GET | `/api/v1/socialforge/accounts` | ✅ SocialForgePage |
| PUT | `/api/v1/socialforge/accounts/{account_id}` | ✅ |
| POST | `/api/v1/socialforge/accounts/ai-guide` | ✅ |
| POST, GET | `/api/v1/socialforge/posts` | ✅ |
| GET, PUT, DELETE | `/api/v1/socialforge/posts/{post_id}` | ✅ |
| POST | `/api/v1/socialforge/generate` | ✅ |
| GET | `/api/v1/socialforge/calendar` | ❌ |
| POST, GET | `/api/v1/socialforge/campaigns` | ❌ |
| DELETE | `/api/v1/socialforge/campaigns/{camp_id}` | ❌ |

**Data:** `business_profile.json`, `accounts.json` (16 social accounts).

---

### TICKETS / SUPPORT (7 endpoints) — ❌ NO FRONTEND
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| POST, GET | `/api/v1/tickets/` | ❌ |
| GET, PATCH, DELETE | `/api/v1/tickets/{ticket_id}` | ❌ |
| POST | `/api/v1/tickets/{ticket_id}/assign` | ❌ |
| POST | `/api/v1/tickets/{ticket_id}/messages` | ❌ |
| POST | `/api/v1/tickets/{ticket_id}/tags` | ❌ |

**DB:** No tickets table in empire.db.

---

### SHIPPING (6 endpoints) — ❌ NO FRONTEND
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| POST | `/shipping/rates` | ❌ |
| POST | `/shipping/labels` | ❌ |
| GET | `/shipping/labels/{label_id}` | ❌ |
| POST | `/shipping/labels/{label_id}/email` | ❌ |
| GET | `/shipping/track/{tracking_number}` | ❌ |
| GET | `/shipping/history` | ❌ |

---

### KNOWLEDGE BASE (7 endpoints) — ❌ NO FRONTEND
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| POST, GET | `/api/v1/kb/articles` | ❌ |
| PATCH, DELETE | `/api/v1/kb/articles/{article_id}` | ❌ |
| GET | `/api/v1/kb/articles/{slug}` | ❌ |
| POST | `/api/v1/kb/articles/{article_id}/vote` | ❌ |
| GET, POST | `/api/v1/kb/categories` | ❌ |
| GET | `/api/v1/kb/categories/{category_id}` | ❌ |
| POST | `/api/v1/kb/search` | ❌ |

---

### MARKETPLACE / LISTINGS (5 endpoints) — ❌ NO FRONTEND
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| GET, POST | `/listings/listings` | ❌ |
| GET, PUT, DELETE | `/listings/listings/{listing_id}` | ❌ |
| POST | `/listings/listings/{listing_id}/publish` | ❌ |
| GET | `/marketplaces/marketplaces` | ❌ |
| POST | `/marketplaces/marketplaces/{name}/connect` | ❌ |

---

### INTAKE PORTAL (9 endpoints) — ✅ FRONTEND WIRED
| Method | Endpoint | Frontend? |
|--------|----------|-----------|
| POST | `/api/v1/intake/signup` | ✅ intake/signup |
| POST | `/api/v1/intake/login` | ✅ intake/login |
| GET | `/api/v1/intake/me` | ✅ |
| GET, POST | `/api/v1/intake/projects` | ✅ intake/dashboard |
| GET, PUT | `/api/v1/intake/projects/{id}` | ✅ intake/project/[id] |
| POST | `/api/v1/intake/projects/{id}/photos` | ✅ |
| POST | `/api/v1/intake/projects/{id}/scans` | ✅ |
| POST | `/api/v1/intake/projects/{id}/message` | ✅ |
| POST | `/api/v1/intake/projects/{id}/submit` | ✅ |

**DB:** `intake.db` → `intake_projects`: 0 rows, `intake_users`: 0 rows.

---

### OTHER SERVICES (wired)
| Feature | Endpoints | Frontend? |
|---------|-----------|-----------|
| MAX Chat/AI | 15+ endpoints | ✅ ChatScreen, TopBar |
| AI Desks | 8 endpoints | ✅ DesksScreen |
| Files | 6 endpoints | ✅ DocumentScreen |
| Memory/Brain | 7 endpoints | ✅ RightPanel, ChatScreen |
| Notifications | 4 endpoints | ✅ InboxScreen |
| System Report | 2 endpoints | ✅ SystemReportScreen |
| Chats/History | 5 endpoints | ✅ ConversationSidebar |
| TTS/STT | 3 endpoints | ✅ ChatScreen (voice) |
| Vision/Mockup | 6 endpoints | ❌ (backend only) |
| Crypto Payments | 4 endpoints | ❌ |
| Onboarding | 2 endpoints | ❌ |
| Docker Control | 3 endpoints | ❌ |
| Messaging | 4 endpoints | ❌ |
| Preorders | 3 endpoints | ❌ |

---

## 2. DATABASE SUMMARY

### empire.db
| Table | Rows | Notes |
|-------|------|-------|
| tasks | 45 | Full task engine — active, 18 columns |
| task_activity | 52 | Audit log for task changes |
| contacts | 0 | CRM table exists but empty |
| desk_configs | 15 | AI desk definitions |

### intake.db
| Table | Rows | Notes |
|-------|------|-------|
| intake_projects | 0 | Customer intake portal |
| intake_users | 0 | Customer auth |

### brain/memories.db
| Table | Rows | Notes |
|-------|------|-------|
| memories | 1,073 | MAX persistent memory |
| conversation_summaries | 39 | Chat summaries |
| customers | 0 | Empty |
| customer_interactions | 0 | Empty |
| knowledge | 0 | Empty |

### brain/token_usage.db
| Table | Rows | Notes |
|-------|------|-------|
| token_usage | 141 | AI API usage tracking |
| budget_config | 1 | Monthly budget settings |

### File-based storage
| Location | Count | Notes |
|----------|-------|-------|
| data/quotes/*.json | 26 | Rich quote data with line items, rooms, proposals |
| data/quotes/pdf/*.pdf | 24 | Generated quote PDFs |
| data/inbox/*.json | 32 | Telegram/system inbox messages |
| data/craftforge/* | 0 | Empty directories (designs, inventory, jobs, templates) |
| data/socialforge/ | 2 | business_profile + 16 social accounts |

---

## 3. WHAT'S MISSING FOR A QB REPLACEMENT

### Critical (must-build)
1. **Invoicing** — No invoice table, no endpoints, no frontend. Need: create from quote, payment tracking, PDF generation, email to customer.
2. **Payments / Deposits** — Quote has `deposit` field but no payment recording system. Need: payment ledger, partial payments, payment methods.
3. **Expense Tracking** — Nothing exists. Need: expense categories, receipt upload, vendor payments, recurring expenses.
4. **Revenue Dashboard** — Economic endpoints exist but have a URL bug and no data. Need: P&L, cash flow, revenue by period.
5. **Customer Database** — CRM tables exist but are empty and not wired. Need: customer list page, customer detail with quote/task/ticket history.

### Important (should-build)
6. **Inventory Management** — CraftForge endpoints exist but data is empty and frontend shows hardcoded values. Need: fabric/hardware stock tracking, reorder alerts, cost tracking.
7. **Job Scheduling** — Task engine exists but no calendar/timeline view. Need: production calendar, installer scheduling, Gantt-style job view.
8. **Ticket System UI** — Full CRUD backend exists. Need: ticket list, detail view, assignment, messaging thread.
9. **Shipping UI** — Full backend exists. Need: rate calculator, label generation, tracking dashboard.

### Nice-to-have (polish)
10. **Reports** — Monthly/quarterly financial reports, customer value reports, production efficiency.
11. **Quote Actions** — Accept, send email, generate PDF from frontend.
12. **Marketplace Dashboard** — Listing management UI for eBay/Facebook.
13. **Knowledge Base UI** — Internal wiki/help center.

---

## 4. BUILD PLAN — Full Business Dashboard

### Phase 1: Finance Core (Invoice + Payments)
**New DB tables:** `invoices`, `payments`, `expenses`, `expense_categories`
**New endpoints:**
- `POST/GET /api/v1/invoices` — CRUD
- `POST /api/v1/invoices/{id}/payment` — record payment
- `POST /api/v1/invoices/{id}/pdf` — generate PDF
- `POST /api/v1/invoices/{id}/send` — email to customer
- `POST/GET /api/v1/expenses` — expense tracking
- `GET /api/v1/finance/dashboard` — P&L, cash flow, revenue summary

**Frontend:** New `FinancePage` screen in Command Center
- Invoice list with status filters (draft/sent/paid/overdue)
- Create invoice from quote (one-click conversion)
- Payment recording with partial payment support
- Expense tracker with category breakdown
- Revenue dashboard with charts (monthly trend, by customer, by service type)

### Phase 2: CRM Wiring
**Frontend:** New `CustomersPage` screen
- Customer list with search, sort by revenue/last contact
- Customer detail: contact info, quote history, invoices, tickets, notes
- Wire to existing `/api/v1/customers` endpoints
- Auto-populate from quote customer data (migration script)

### Phase 3: Production & Inventory
**Frontend:** Wire CraftForge page to real data
- Connect `CraftForgePage` to `/api/v1/craftforge/*` endpoints
- Inventory management: fabric stock, hardware, materials with costs
- Job board: create jobs from accepted quotes, track production stages
- Templates: saved configurations for common window treatments

### Phase 4: Support & Scheduling
**Frontend:** New `TicketsPage` + calendar view
- Wire to `/api/v1/tickets/*` endpoints
- Ticket list, detail, messaging thread
- Calendar view for tasks with due dates
- Installer scheduling with contractor assignment

### Phase 5: Shipping + Marketplace
**Frontend:** Wire shipping and marketplace UIs
- Shipping: rate calculator, label printing, tracking
- Marketplace: listing management, order sync

---

## 5. FRONTEND WIRING SCORECARD

| Feature | Backend Endpoints | Frontend Pages | Wired? | Data? |
|---------|:-:|:-:|:-:|:-:|
| Quotes | 10 | QuoteReview, Workroom | Partial (list only) | 26 quotes |
| Customers/CRM | 7 | None | ❌ | 0 rows |
| Finance/Economic | 7 | None | ❌ | 0 rows, URL bug |
| Tasks | 10 | DesksScreen | Partial | 45 tasks |
| CraftForge | 10 | CraftForgePage (hardcoded) | ❌ | 0 files |
| SocialForge | 12 | SocialForgePage | ✅ | 16 accounts |
| Tickets/Support | 7 | None | ❌ | No table |
| Shipping | 6 | None | ❌ | Unknown |
| KB/Help | 7 | None | ❌ | 0 articles |
| Marketplace | 5 | None | ❌ | Unknown |
| Intake Portal | 9 | 6 pages | ✅ | 0 rows (new) |
| MAX/AI Chat | 15+ | ChatScreen + more | ✅ | 1073 memories |
| AI Desks | 8 | DesksScreen | ✅ | 15 desk configs |
| Files | 6 | DocumentScreen | ✅ | Uploads dir |
| System/Report | 2 | SystemReportScreen | ✅ | Live |
| Notifications | 4 | InboxScreen | ✅ | 32 messages |

**Summary:** ~150 total backend endpoints. ~55% have frontend wiring. The business-critical features (finance, CRM, inventory, tickets) are the ones with zero frontend coverage.

---

*This audit serves as the roadmap for building Empire into a full QuickBooks replacement for the custom drapery business.*
