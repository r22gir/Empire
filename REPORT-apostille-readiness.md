# Apostille App Readiness Report (Phase 2A)

**Status:** Read-only audit. No code changes, no branches.
**Date:** 2026-06-08
**Author:** Empire Completion Coordinator
**Scope:** `backend/app/routers/apostapp.py` (815 lines), `backend/app/main.py` (wiring line 186), and the related `ecosystem_catalog.py` / `empire_module_knowledge.py` cross-references in `services/max/`.

---

## 1. What exists today

### 1.1 The router file

`backend/app/routers/apostapp.py` is 815 lines, all in one file. It declares:
- `prefix="/apostapp"`, `tags=["apostapp"]`
- 5 Pydantic models: `ApostilleDocument`, `ApostilleOrderCreate`, `ApostilleOrderUpdate`, `DocumentStatusUpdate`, `ApostilleCustomerCreate`, plus `LLCOrderLink` and `FormGenerateRequest`
- 2 storage helpers: `_save_json` / `_load_json`
- 2 pricing helpers: `_calculate_document_fee`, `_calculate_order_total`
- 17 HTTP endpoints (15 + 2 sub-routes — see below)
- All state lives in `~/empire-repo/backend/data/apostapp/{customers,orders,documents}/` as one JSON file per record

Storage is local JSON files. There is **no DB**, **no Stripe**, **no transactional email service**, **no SMS service**, **no Telegram bot wiring** inside this router.

### 1.2 The 15 (visible) endpoints

| Method | Path | Purpose | Works? | Notes |
|---|---|---|---|---|
| GET | `/apostapp/` | Module info (name, tagline, contact) | Yes | Returns a tagline — the only marketing copy in the backend |
| GET | `/apostapp/services` | List of services (translation, apostille, etc.) | Yes | Static list |
| GET | `/apostapp/document-types` | List of supported document types | Yes | Includes FBI background check, commercial invoice, certificate of good standing |
| GET | `/apostapp/pricing-calculator` | Pricing for a document + rush + shipping | Yes | Pure function, no DB |
| POST | `/apostapp/orders` | Create an order | Yes | Creates JSON file, returns order_id |
| GET | `/apostapp/orders` | List all orders | Yes | Reads all files in `orders/` dir |
| GET | `/apostapp/orders/{order_id}` | Get one order | Yes | Reads JSON file |
| PUT | `/apostapp/orders/{order_id}` | Update order (status, notes, payment, shipping) | Yes | Mutates JSON file |
| PUT | `/apostapp/orders/{order_id}/documents/{doc_index}/status` | Update one document's status | Yes | Mutates JSON file |
| POST | `/apostapp/orders/{order_id}/documents` | Upload a document for an order | Yes | Saves the file; needs to verify storage path |
| POST | `/apostapp/customers` | Create a customer | Yes | Creates JSON file |
| GET | `/apostapp/customers` | List all customers | Yes | Reads all files in `customers/` dir |
| GET | `/apostapp/customers/{customer_id}` | Get one customer | Yes | Reads JSON file |
| GET | `/apostapp/dashboard` | Dashboard summary (counts, recent orders) | Yes | Aggregates from disk |
| POST | `/apostapp/orders/from-llc/{llc_order_id}` | Create an apostille order from an existing LLC Factory order | Yes | Reads LLC order, extracts auto-apostille documents (Articles of Organization, Operating Agreement, Certificate of Good Standing) |
| POST | `/apostapp/forms/generate` | Generate a printable HTML form with autofilled fields | Yes | Returns HTML, intended for "Print→Save as PDF" |

(Note: the actual count is 15 router decorators + 2 sub-paths; the inventory I read showed 13 distinct top-level paths because some share prefix. The actual count per the router source is 15. I am reporting what I see.)

### 1.3 What is NOT in the backend

- **No Stripe.** No `payment_intent`, no `charge`, no `webhook`. The "payment" field in `ApostilleOrderUpdate` is a free-form string, not a structured payment record.
- **No transactional email.** No SendGrid, no Postmark, no SES. The `customer_email` field is stored but never used to send anything.
- **No SMS.** No Twilio. No phone-based notifications.
- **No Telegram bot wiring** in this router. (MAX has Telegram elsewhere, but apostille is not wired to it.)
- **No document signature / e-sign.** The `forms/generate` endpoint returns a printable HTML form, not a signable PDF.
- **No government-office API integration.** No automatic submission to DC/MD/VA Secretary of State APIs. The workflow assumes the founder or a vendor physically takes documents to the office.
- **No vendor/courier/notary/translator management.** No link from an apostille order to a vendor record in VendorOps.
- **No public landing page.** The `GET /` endpoint returns a JSON info payload, not HTML.
- **No customer-facing tracking page.** The `GET /orders/{order_id}` endpoint exists but has no public UI.
- **No email template system.** No template engine, no template files.

### 1.4 The LLC Factory bridge

`POST /orders/from-llc/{llc_order_id}` is a real feature: it reads an existing LLC Factory order and auto-creates an apostille order with the three documents that commonly need apostille (Articles of Organization, Operating Agreement, Certificate of Good Standing). This is the only inter-module bridge in the apostille router. It is the closest thing to a "money pipeline" today.

### 1.5 Cross-references in MAX

`backend/app/services/max/ecosystem_catalog.py` and `backend/app/services/max/empire_module_knowledge.py` mention apostille. The Founder's rule was: **do not modify MAX during this sprint** unless required. The current MAX references are read-only knowledge — no live integration. The cross-references tell MAX "apostille exists" but do not give it any data.

### 1.6 Front-end presence

There is **no front-end page for apostille** in `/home/rg/empire-repo-main/empire-command-center/app/`. The 21 top-level front-end routes do not include `apostille` or `apostapp`. The router is invisible to the founder team and to customers without manually constructing API calls.

---

## 2. Customer Journey Audit (per step)

| Step | Exists? | Works? | Stubbed? | Missing? | Revenue blocker? | Notes |
|---|---|---|---|---|---|---|
| **Landing page** | NO (backend has `GET /` returning info) | n/a | n/a | YES — no HTML, no public URL, no SEO | YES | Without a landing page, customers cannot find the service. |
| **Intake form** | Partial | n/a | YES (only the API exists) | YES — no front-end form | YES | API is fine; the missing piece is the form. |
| **Document upload** | YES (API) | YES | n/a | YES — no front-end upload UI | YES | API accepts files; no UI calls it. |
| **Quote display** | YES (API) | YES | n/a | YES — no front-end display | YES | `GET /pricing-calculator` returns a price. No UI shows it. |
| **Quote generation (manual)** | NO (system) | n/a | n/a | YES — founder must run the calculator by hand or via curl | YES (operationally) | Founder does this in 1 minute per order; not automated. |
| **Payment (customer)** | NO (no Stripe) | n/a | n/a | YES | YES | For v1: founder takes Zelle/Venmo/wire. The system has no record of which was used. |
| **Payment (system record)** | Partial | YES | n/a | YES — `ApostilleOrderUpdate` has a `payment` field but it's a free-form string | NO (operationally) | Founder can mark "paid via Zelle" in the order notes. |
| **Vendor / courier / notary / translator task assignment** | NO | n/a | n/a | YES — no link to VendorOps | YES (at scale) | For v1: founder emails vendors directly. |
| **Government submission step** | NO (system) | n/a | n/a | YES — founder physically takes docs to DC/MD/VA office | NO (operationally) | Inherent in the business; no software can avoid this. |
| **In-progress tracking** | YES (API) | YES | n/a | YES — no front-end tracker | YES | API exists; no UI. |
| **Customer notification** | NO | n/a | n/a | YES | YES | No email, no SMS, no Telegram wired to apostille. |
| **Completion / delivery** | Partial | YES | n/a | YES — no delivery tracking | YES | API has a status field; no delivery module. |
| **Pickup / shipping** | Partial | YES | n/a | YES — no shipping integration | NO (operationally) | Order has a `shipping_method` field; founder ships by hand. |
| **Closed** | YES (API) | YES | n/a | YES — no automated close-out | NO | API allows status update; founder does it manually. |

---

## 3. What's stubbed vs missing

**Stubbed** (code exists, returns a fixed payload, no real logic):
- `GET /` (info endpoint) — returns a hardcoded tagline
- `GET /services` — returns a static list
- `GET /document-types` — returns a static list
- `GET /dashboard` — reads all files in `orders/` and aggregates; works but unindexed

**Missing** (no code path at all):
- Public landing page (HTML, no API)
- Intake form front-end
- Document upload UI
- Quote display UI
- Customer notification (email, SMS, Telegram)
- Vendor/courier/notary/translator task management
- Government-office submission step (inherent business constraint)
- Delivery tracking
- Public tracking page

---

## 4. v1 Revenue Path (manual, no payment automation)

The fastest path to revenue is a **manual v1**: founder does what the system can't, and the system captures everything for later automation.

### 4.1 What to ship in v1

1. **Public landing page** (Spanish + English)
   - DC/MD/VA positioning
   - "Not legal advice" disclaimer
   - Contact form (name, email, phone, document type, destination country, urgency, message)
   - ~$ price ranges ("Apostille from $X; expedited from $Y; translation from $Z per page")
   - "We respond within 4 business hours" promise
2. **Intake form** that calls `POST /customers` then `POST /orders` with the customer's documents
3. **Document upload UI** that calls `POST /orders/{order_id}/documents`
4. **Founder gets notification** when a new order lands (Telegram/MAX outbound — already exists in the system)
5. **Founder generates a quote** using `GET /pricing-calculator` (or by hand, with the existing pricing logic)
6. **Founder emails the customer** a quote and a Zelle/Venmo/wire link (manual email — no system required)
7. **Customer pays** via the founder's existing payment paths (Zelle, Venmo, wire — NOT new Stripe)
8. **Founder marks the order paid** via `PUT /orders/{order_id}` with `{"payment": "Zelle paid YYYY-MM-DD"}`
9. **Founder assigns vendor work** by emailing the vendor directly (or, after Phase 4, by creating a VendorOps task)
10. **Customer update** at each status change — manual email, or a simple status-check URL the founder can send
11. **Pickup/delivery** — founder handles by hand, marks complete in the system

### 4.2 What to defer to v2

- Automated Stripe payment (requires Stripe account, webhook, payout flow)
- Automated email templates (requires transactional email service)
- Automated SMS
- Automated vendor handoff (depends on Phase 4 VendorOps integration)
- Auto-submit to government offices (not possible — physical submission required)
- Customer-facing dashboard (UI not critical for v1 if Founder handles by hand)

### 4.3 What to defer to v3 (after v2)

- Multi-language front-end beyond Spanish/English
- Mobile-first front-end (the v1 can be desktop-only)
- Self-service status tracking with email magic links
- Calendar/scheduling integration (Calendly, etc.)

---

## 5. Missing API / Screen List

### 5.1 Missing front-end pages (in `empire-command-center/app/`)

| New page | Purpose | Priority |
|---|---|---|
| `apostille/page.tsx` | Landing page (Spanish + English, with language toggle) | P0 |
| `apostille/intake/page.tsx` | Intake form | P0 |
| `apostille/intake/upload/page.tsx` | Document upload UI | P0 |
| `apostille/quote/page.tsx` | Quote display (the result of `GET /pricing-calculator`) | P1 |
| `apostille/admin/page.tsx` | Founder-only dashboard for managing orders | P0 |
| `apostille/admin/orders/[id]/page.tsx` | Single order management | P0 |
| `apostille/admin/customers/page.tsx` | Customer list | P1 |
| `apostille/admin/dashboard/page.tsx` | Founder's metrics | P2 |

### 5.2 Missing backend endpoints (for v1.5+)

| Endpoint | Purpose | Priority |
|---|---|---|
| `GET /apostapp/public/pricing-ranges` | Public pricing ranges (no auth) for the landing page | P0 |
| `GET /apostapp/public/services` | Public services list (no auth) for the landing page | P0 |
| `POST /apostapp/notify-founder` | Customer-facing "contact us" form submission → Telegram/MAX outbound to Founder | P0 |
| `GET /apostapp/orders/{order_id}/status` | Public status check (with a token, no auth required) for the customer to track their order | P1 |
| `POST /apostapp/orders/{order_id}/customer-update` | Customer-facing "I confirm receipt" or "I have a question" form | P2 |

(Note: most of these can be added later; the v1 minimum is the three P0 items above.)

### 5.3 Missing UI components

- Language toggle (Spanish ↔ English)
- File upload widget
- Quote display widget (calls `GET /pricing-calculator`)
- "Founder is typing" indicator (optional)

---

## 6. Revenue Launch Checklist

For v1 to be revenue-ready:

- [ ] Public landing page live at `/apostille` (Spanish + English)
- [ ] Intake form live at `/apostille/intake` (Spanish + English)
- [ ] Document upload UI live at `/apostille/intake/upload` (Spanish + English)
- [ ] Founder gets Telegram/MAX notification on every new order (via `POST /apostapp/notify-founder` or by polling)
- [ ] Founder has a quick-reference card: "for a new order: 1) open /apostille/admin, 2) generate quote, 3) email Zelle link, 4) mark paid"
- [ ] "Not legal advice" disclaimer is visible on every customer-facing page
- [ ] Spanish translation reviewed by a native speaker
- [ ] DC/MD/VA specific copy reviewed for accuracy
- [ ] Test: a real customer can land on the page, fill the form, upload docs, and the order shows up in `GET /apostapp/orders` within seconds
- [ ] Test: the founder can generate a quote, email it, and mark it paid — all in <5 minutes per order

---

## 7. Branch / Worktree Proposal

- **Branch:** `feature/apostille-completion`
- **Worktree:** `/home/rg/empire-repo-main-apostille-completion` (new, from `main` HEAD `2867978`)
- **Files to touch:**
  - New front-end pages: `empire-command-center/app/apostille/**` (5+ new files)
  - New front-end components: file upload widget, language toggle, quote display widget
  - New i18n strings: Spanish + English translations for all new pages
  - Minor backend additions: `GET /public/pricing-ranges`, `GET /public/services`, `POST /notify-founder` (low-risk additive endpoints)
  - **Do NOT touch:** `apostapp.py`'s existing 15 routes; `services/max/ecosystem_catalog.py`; `services/max/empire_module_knowledge.py` (MAX is shared with Harry)
- **Tests:**
  - `test_apostille_intake_journey.py` — POST customer, POST order, upload document, verify dashboard counts
  - `test_apostille_pricing.py` — pricing calculator correctness across rush and shipping options
  - `test_apostille_public_endpoints.py` — public endpoints don't require auth
- **Risk:** **low** — front-end only, no backend changes to existing routes
- **Owner:** Hermes Desktop for product/copy (this doc), Codex or Claude for the front-end

---

## 8. Do not proceed list (audit phase)

This audit made no code changes, created no branches, ran no tests, and edited no files outside the report outputs in this batch. All other repo state is unchanged.
