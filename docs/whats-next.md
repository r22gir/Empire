# What's Next — Prioritized Punch List

**Date:** 2026-03-18
**Basis:** Phase 0 reality check audit findings
**Priority:** Revenue blockers first, then stability, then features

---

## Priority 1: Revenue Blockers

These items directly prevent Empire from collecting money.

### 1. Switch Stripe to Live Keys + Verify Webhook
- **Why:** Test keys cannot process real payments. No revenue until this is done.
- **What:** Replace `sk_test_*` and `pk_test_*` in `.env` with live keys from Stripe dashboard. Update webhook signing secret. Test with a real $1 charge.
- **Effort:** 30 minutes
- **Risk:** Low — Stripe dashboard has the keys ready

### 2. Customer Quote Acceptance Page at `/intake/quote/[id]`
- **Why:** Customers receive quote PDFs by email but have no way to accept online. Without this, every acceptance requires a phone call or email reply.
- **What:** Build a public-facing page that displays the quote, shows line items and total, and has an "Accept & Pay Deposit" button that initiates Stripe checkout.
- **Effort:** 1 session
- **Risk:** Medium — needs to be secure (signed URLs or tokens)

### 3. Auto-Deposit Invoice on Quote Acceptance
- **Why:** When a customer accepts a quote, a deposit invoice should be created automatically. Currently this is manual.
- **What:** On quote acceptance event, auto-create an invoice for the deposit amount (e.g., 50%), mark the quote as accepted, and create a job.
- **Effort:** 1 session
- **Risk:** Low — all the pieces exist, just need wiring

---

## Priority 2: Stability Fixes

These items affect daily usability.

### 4. Fix Telegram Bot systemd Service
- **Why:** MAX on Telegram is the primary mobile interface. Without systemd, the bot dies on any server restart or crash and nobody notices.
- **What:** Create `empire-telegram-bot.service` unit file, enable on boot, add health check.
- **Effort:** 30 minutes
- **Risk:** Low

### 5. Fix chat-backup 500 Error
- **Why:** Conversation backup is failing silently. If the server crashes, recent conversations are lost.
- **What:** Debug the 500 error on `/chat-backup/*` endpoints. Likely a file path or database issue.
- **Effort:** 30 minutes
- **Risk:** Low

---

## Priority 3: Marketing Unblock

### 6. SocialForge OAuth Flows
- **Why:** 16 social media accounts are tracked but none can publish. Marketing is completely manual.
- **What:** Start with Instagram (Meta OAuth 2.0), then expand. Build consent flow, token storage, and auto-publishing worker.
- **Effort:** 2-3 sessions for Instagram alone
- **Risk:** Medium — requires Meta developer app approval (can take days)

---

## Priority 4: Bug Fixes

### 7. Fix payments/checkout Routing (404)
- **Why:** The Stripe checkout creation endpoint returns 404. Even with live keys, checkout won't work until the route is registered.
- **What:** Add the payments/checkout router to the FastAPI app router includes.
- **Effort:** 15 minutes
- **Risk:** Low

### 8. Phone-Optimized MAX Chat View
- **Why:** The Command Center chat works on desktop but is cramped on mobile. Since Telegram bot is unreliable (no systemd), a mobile-friendly web chat is the backup.
- **What:** Responsive CSS for ChatScreen — full-width input, larger touch targets, collapsible sidebar.
- **Effort:** 1 session
- **Risk:** Low

---

## Priority 5: Data Flow Completion

### 9. Job Creation Flow Testing
- **Why:** The Kanban board is empty because no jobs have been created. The quote-to-job conversion has never been tested end-to-end.
- **What:** Create a test job from an existing quote. Verify it appears on the Kanban board. Test status transitions (New -> In Progress -> Review -> Complete).
- **Effort:** 30 minutes
- **Risk:** Low

### 10. Notes Extraction Endpoint Fix
- **Why:** The notes-to-quote extraction feature (commit 3115af2) returns 404. Route was never registered.
- **What:** Add the `/notes/extract` route to the FastAPI router includes. Verify the handler function works.
- **Effort:** 15 minutes
- **Risk:** Low

---

## Summary Table

| # | Item | Priority | Effort | Blocks |
|---|------|----------|--------|--------|
| 1 | Stripe live keys | P1 | 30 min | Revenue |
| 2 | Quote acceptance page | P1 | 1 session | Revenue |
| 3 | Auto-deposit on acceptance | P1 | 1 session | Revenue |
| 4 | Telegram bot systemd | P2 | 30 min | Mobile MAX |
| 5 | Chat-backup 500 fix | P2 | 30 min | Data safety |
| 6 | SocialForge OAuth | P3 | 2-3 sessions | Marketing |
| 7 | Checkout route fix | P4 | 15 min | Payments |
| 8 | Mobile chat view | P4 | 1 session | Mobile UX |
| 9 | Job creation test | P5 | 30 min | Kanban |
| 10 | Notes endpoint fix | P5 | 15 min | Notes-to-Quote |

**Total estimated effort:** ~4-5 focused sessions to clear the entire list.

**Recommended session order:**
- Session A: Items 1, 4, 5, 7, 10 (quick wins, 2 hours)
- Session B: Item 2 (quote acceptance page)
- Session C: Item 3 + 9 (auto-deposit + job flow testing)
- Session D: Item 8 (mobile chat)
- Session E+: Item 6 (SocialForge OAuth, multi-session)
