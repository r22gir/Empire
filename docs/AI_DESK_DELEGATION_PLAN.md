# AI Desk Delegation Plan

## Architecture: Founder → MAX (Director) → AI Desks

Each Empire app gets its own AI Desk — a specialized AI agent that handles day-to-day operations for that business line. MAX coordinates all desks. The founder supervises and makes final decisions.

MAX acts as the central orchestrator. It receives all inbound tasks, classifies intent, routes work to the appropriate desk, monitors execution, and surfaces summaries and alerts to the founder. No desk operates outside MAX's awareness.

---

## System Overview

```
Founder (Telegram / Founder Dashboard)
         │
         ▼
    MAX (Director)
    /api/v1/max  ──── AI Router: xAI Grok → Claude → Ollama
         │
    ┌────┴────────────────────────────────────────┐
    │           Desk Routing Engine               │
    └──┬──────┬──────┬──────┬──────┬──────────────┘
       │      │      │      │      │
  ForgeDesk  MarketDesk  SocialDesk  AmpDesk  RecoveryDesk  SupportDesk
  (WorkroomForge) (MarketForge) (SocialForge) (AMP) (RecoveryForge) (cross-business)
```

The backend is FastAPI on port 8000. Desk configurations are stored in SQLite via `/api/v1/desks`. Desk chat runs through `/api/v1/max/chat` with the `desk` parameter identifying which desk context to apply.

---

## Desk Definitions

For each desk:
- **Desk name and app it serves**
- **AI responsibilities** — what it handles autonomously
- **Escalation triggers** — when it involves the founder
- **Tools / APIs required**
- **Priority level** — build order

---

## 1. ForgeDesk (WorkroomForge) — PRIORITY 1

**App**: WorkroomForge — custom fabrication shop management (quotes, scheduling, measurements, job tracking)

**Purpose**: Run the day-to-day shop operations autonomously. The founder should only touch this desk for strategic decisions, large deals, and exceptions.

### AI Responsibilities (Autonomous)

- Generate quotes from customer inquiry data using `/api/v1/quotes` (CRUD + PDF)
- Send quote PDFs to customers via email and Telegram
- Track quote status (draft → sent → approved → invoiced)
- Follow up on open quotes after 48 hours automatically
- Send appointment reminders 24 hours and 1 hour before scheduled jobs
- Update job status as work progresses (scheduled → in-progress → completed)
- Log measurement data from field reports
- Send payment reminders at due date and 3 days after
- Maintain customer records in ForgeCRM via `/api/v1/customers`
- Pull weekly revenue totals and job completion rates for morning briefing

### Escalation Triggers

- New customer not previously in CRM requires founder approval before first quote
- Any quote exceeding $5,000 requires founder sign-off before sending
- Customer complaints or disputes of any kind
- Design decisions that require custom fabrication outside standard catalog
- Payment failures or declined transactions
- Scheduling conflicts that cannot be resolved automatically

### Tools / APIs Required

| Tool | Endpoint / Integration |
|------|------------------------|
| Quote CRUD | `POST/GET/PATCH/DELETE /api/v1/quotes` |
| Quote PDF generation | `GET /api/v1/quotes/{id}/pdf` |
| Customer records | `GET/POST/PATCH /api/v1/customers` |
| Job scheduling | Calendar integration (Google Calendar or internal scheduler) |
| Telegram notifications | `/api/v1/max/telegram/send` |
| Email delivery | SMTP / SendGrid integration |
| Payment reminders | Stripe webhook listener |
| Morning briefing contribution | `/api/v1/max/desks/forgedesk/briefing` |

### Capability Matrix

| Capability | Autonomous | Needs Approval |
|------------|------------|----------------|
| Generate quote under $5K | Yes | No |
| Generate quote over $5K | Draft only | Founder reviews + approves before send |
| Send quote to existing customer | Yes | No |
| Send quote to new customer | No | Founder approves new customer first |
| Schedule appointment | Yes | No |
| Reschedule appointment | Yes (notify customer) | No |
| Send appointment reminder | Yes | No |
| Mark job in-progress | Yes | No |
| Mark job complete | Yes | No |
| Send payment reminder | Yes | No |
| Issue refund or credit | No | Always requires founder |
| Add customer to CRM | Yes (existing context) | No |
| Handle customer complaint | Acknowledge receipt only | Founder handles resolution |
| Update quote pricing | Yes (standard rates) | Yes (custom/discounted rates) |
| Generate weekly revenue report | Yes | No |

---

## 2. MarketDesk (MarketForge)

**App**: MarketForge — intelligent marketplace listing creation, inventory management, multi-platform publishing

**Purpose**: Maximize listing quality and sales velocity across all connected marketplaces while keeping inventory accurate.

### AI Responsibilities (Autonomous)

- Create and publish listings using AI-generated descriptions and optimized titles
- Sync inventory counts across connected marketplaces
- Adjust pricing based on competitor data and demand signals
- Process standard orders and trigger fulfillment workflows
- Monitor listing performance and flag underperforming SKUs
- Auto-relist expired listings via RelistApp integration
- Generate weekly inventory and sales reports

### Escalation Triggers

- Customer return requests or refund claims
- Negative reviews (3 stars or below) — desk flags for founder response
- Pricing exceptions requested by buyers
- Out-of-stock situations on high-velocity SKUs
- Marketplace policy violations or listing removals
- New marketplace platform onboarding

### Tools / APIs Required

| Tool | Endpoint / Integration |
|------|------------------------|
| Listings CRUD | `GET/POST/PATCH/DELETE /api/v1/listings` |
| Marketplace sync | `/api/v1/marketplaces` |
| Order management | `/api/v1/marketplace/orders` |
| Inventory tracking | Internal inventory module |
| Seller dashboard | `/api/v1/marketplace/seller` |
| Review monitoring | `/api/v1/marketplace/reviews` |
| Preorder management | `/api/v1/preorders` |

### Capability Matrix

| Capability | Autonomous | Needs Approval |
|------------|------------|----------------|
| Create new listing | Yes | No |
| Publish listing to marketplace | Yes | No |
| Update listing description | Yes | No |
| Adjust price within ±15% of base | Yes | No |
| Adjust price more than 15% | No | Founder approves |
| Process standard order | Yes | No |
| Initiate shipment | Yes | No |
| Apply promotional discount | No | Founder approves |
| Handle return request | Acknowledge only | Founder resolves |
| Respond to negative review | Draft only | Founder reviews before posting |
| Delist a product | No | Founder approves |
| Onboard new marketplace | No | Founder setup required |
| Generate sales report | Yes | No |
| Bulk relist expired listings | Yes | No |

---

## 3. SocialDesk (SocialForge)

**App**: SocialForge — social media management, content scheduling, engagement, analytics

**Purpose**: Maintain consistent brand presence across all platforms without requiring daily founder attention.

### AI Responsibilities (Autonomous)

- Schedule and publish pre-approved content to Facebook, Instagram, Twitter/X, LinkedIn
- Research and apply trending hashtags per platform
- Monitor engagement metrics and generate weekly analytics reports
- Respond to positive comments and standard engagement (likes, thank-you replies)
- Suggest content calendar for founder review each Monday
- Track follower growth and engagement rate per platform

### Escalation Triggers

- Any negative PR situation or viral negative content
- Brand-sensitive content decisions (political, controversial topics)
- Ad spend requests exceeding founder-set threshold (default: $100/day)
- Influencer partnership requests
- Account warnings or platform policy violations
- Comments requiring specific business knowledge to answer accurately

### Tools / APIs Required

| Tool | Endpoint / Integration |
|------|------------------------|
| Content scheduler | SocialForge internal scheduler |
| Platform APIs | Facebook Graph, Instagram, Twitter/X, LinkedIn APIs |
| Analytics | Platform native analytics + internal aggregation |
| Content library | Internal media asset storage |
| Hashtag research | Third-party hashtag tool or internal ML model |

### Capability Matrix

| Capability | Autonomous | Needs Approval |
|------------|------------|----------------|
| Publish scheduled post | Yes (pre-approved content) | No |
| Suggest new content | Yes (draft only) | Founder approves before scheduling |
| Respond to positive comments | Yes | No |
| Respond to negative comments | Draft only | Founder reviews |
| Research hashtags | Yes | No |
| Generate analytics report | Yes | No |
| Schedule ad campaign | No | Founder approves budget + creative |
| Pause underperforming post | Yes (organic only) | No |
| Pause paid ad | No | Founder approves |
| Follow/unfollow accounts | No | Founder directs |
| Delete a post | No | Founder approves |
| Suggest content calendar | Yes | Founder reviews weekly |

---

## 4. AmpDesk (AMP — Apostol Marketing Platform)

**App**: AMP — client-facing marketing and campaign management platform

**Purpose**: Deliver client campaigns autonomously, maintain reporting cadence, and flag anything requiring strategic input.

### AI Responsibilities (Autonomous)

- Manage active client campaigns within approved parameters
- Generate weekly and monthly performance reports for clients
- Create content drafts based on client briefs and brand guidelines
- Monitor campaign KPIs and alert on underperformance
- Maintain content calendars per client
- Schedule and deliver campaign assets on approved timelines
- Track billing milestones and flag upcoming renewals

### Escalation Triggers

- New client onboarding — always requires founder kickoff call and strategy brief
- Budget changes requested by client (increase or decrease)
- Strategy pivots or campaign direction changes
- Client dissatisfaction signals (negative feedback, cancellation risk)
- Creative disputes or brand guideline conflicts
- Billing disputes or payment failures

### Tools / APIs Required

| Tool | Endpoint / Integration |
|------|------------------------|
| Campaign management | AMP internal campaign engine |
| Content creation | AI generation + asset library |
| Client reporting | Automated PDF/email reports |
| Analytics aggregation | Multi-platform analytics APIs |
| Billing tracking | Stripe subscription data |
| Telegram (founder only) | `/api/v1/max/telegram/send` |

### Capability Matrix

| Capability | Autonomous | Needs Approval |
|------------|------------|----------------|
| Execute approved campaign | Yes | No |
| Generate client report | Yes | No |
| Create content draft | Yes | Founder/client reviews |
| Publish content to client channels | Yes (approved content only) | No |
| Adjust campaign targeting | Yes (within brief) | No |
| Increase campaign budget | No | Founder + client approval |
| Onboard new client | No | Founder leads onboarding |
| Change campaign strategy | No | Founder + client approval |
| Respond to client messages | Draft only | Founder reviews |
| Pause a campaign | Yes (notify founder) | No |
| Cancel client contract | No | Founder only |
| Propose upsell to client | Draft only | Founder approves pitch |

---

## 5. RecoveryDesk (RecoveryForge)

**App**: RecoveryForge — addiction recovery support platform with daily check-ins, group coordination, and crisis tools

**Purpose**: Maintain platform operations, coordinate support resources, and ensure crisis escalation is immediate and reliable. Given the sensitive nature of this app, this desk operates with a high escalation bias.

### AI Responsibilities (Autonomous)

- Send daily check-in prompts to enrolled users
- Track check-in completion rates and flag missed check-ins
- Route support group coordination messages
- Maintain resource directory (meeting schedules, hotlines, provider listings)
- Generate weekly engagement and wellness trend reports
- Send automated encouragement messages on recovery milestones

### Escalation Triggers

- Any user expressing crisis, self-harm, or relapse — IMMEDIATE escalation
- Technical failures affecting crisis intervention tools
- New provider or group leader onboarding
- HIPAA compliance concerns or data requests
- Any content moderation issue in group spaces
- User account security concerns

### Tools / APIs Required

| Tool | Endpoint / Integration |
|------|------------------------|
| User check-in system | RecoveryForge check-in API |
| Crisis alerting | Immediate Telegram push to founder + crisis team |
| Resource directory | Internal CMS |
| Group coordination | Secure messaging module |
| HIPAA audit log | Compliance logging system |
| Engagement analytics | Internal analytics |

### Capability Matrix

| Capability | Autonomous | Needs Approval |
|------------|------------|----------------|
| Send daily check-in | Yes | No |
| Send milestone message | Yes | No |
| Route group messages | Yes | No |
| Flag missed check-in | Yes (notify care team) | No |
| Crisis escalation | Immediate — auto-escalate | Cannot be blocked |
| Add resource to directory | Yes | No |
| Remove resource from directory | No | Founder reviews |
| Onboard new provider | No | Founder vets + approves |
| Access user health records | No | Never — human only |
| Respond to legal/data requests | No | Founder + legal counsel |
| Disable user account | No | Founder or safety team |

---

## 6. SupportDesk (Cross-Business)

**App**: SupportForge — AI-powered customer support, ticket management, multi-channel communication

**Purpose**: First line of defense for all customer-facing support across every Empire app. Reduce founder support burden by handling routine issues autonomously.

### AI Responsibilities (Autonomous)

- Receive and classify incoming support tickets from all channels
- Route tickets to the correct app-specific desk (ForgeDesk for WorkroomForge issues, MarketDesk for listing issues, etc.)
- Respond to FAQ-tier questions using knowledge base
- Acknowledge all tickets within 5 minutes with a confirmation and expected response time
- Track ticket status from open → in-progress → resolved
- Generate weekly support volume and resolution time reports
- Identify recurring issues and flag patterns for product improvements

### Escalation Triggers

- Any ticket unresolved after 24 hours
- VIP customer tickets (defined by tag or spend threshold)
- Technical problems requiring backend access or code changes
- Legal or compliance-related inquiries
- Customer expressing extreme frustration or threatening action
- Tickets requiring refunds over the auto-approve limit

### Tools / APIs Required

| Tool | Endpoint / Integration |
|------|------------------------|
| Ticket CRUD | `GET/POST/PATCH /api/v1/tickets` |
| Customer records | `GET/POST/PATCH /api/v1/customers` |
| Knowledge base | `/api/v1/supportforge/kb` |
| AI response generation | `/api/v1/supportforge/ai` |
| Telegram (customer-facing) | Outbound ticket updates to customers |
| Telegram (founder alerts) | VIP + urgent escalation alerts |
| Multi-desk routing | `/api/v1/max/tasks` with `desk_id` |

### Capability Matrix

| Capability | Autonomous | Needs Approval |
|------------|------------|----------------|
| Acknowledge ticket | Yes | No |
| Answer FAQ question | Yes | No |
| Route ticket to correct desk | Yes | No |
| Send status update to customer | Yes | No |
| Close resolved ticket | Yes | No |
| Issue refund under $50 | Yes | No |
| Issue refund $50–$200 | Yes (notify founder) | No |
| Issue refund over $200 | No | Founder approves |
| Respond to VIP customer | Draft only | Founder reviews |
| Handle legal/compliance inquiry | No | Founder + legal |
| Access system logs for debugging | No | Founder or dev |
| Create knowledge base article | Draft only | Founder publishes |
| Ban/block a customer | No | Founder approves |

---

## How MAX Routes Tasks to the Right Desk

MAX uses a three-layer routing strategy:

### Layer 1 — Intent Classification

Every incoming message is processed by the AI router (xAI Grok → Claude → Ollama fallback chain). The system prompt instructs MAX to identify:

1. **Business domain** — which Empire app is involved
2. **Action type** — query, create, update, escalate, report
3. **Urgency** — routine, time-sensitive, critical

### Layer 2 — Keyword and Context Matching

MAX maintains a routing table with domain keywords:

| Keywords / Signals | Target Desk |
|--------------------|-------------|
| quote, job, measurement, customer visit, fabrication, workroom | ForgeDesk |
| listing, inventory, order, marketplace, SKU, relist, Amazon, eBay | MarketDesk |
| post, content, hashtag, engagement, followers, Instagram, Facebook | SocialDesk |
| campaign, client, AMP, marketing, ad creative, brand | AmpDesk |
| recovery, check-in, sobriety, group meeting, crisis | RecoveryDesk |
| ticket, complaint, support, help request, customer issue | SupportDesk |

### Layer 3 — `desk_id` Routing

The API parameter `desk` in `/api/v1/max/chat` directly targets a desk's system prompt and tool set. When the Founder Dashboard or any automated trigger sends a request, it specifies the `desk_id` explicitly:

```json
POST /api/v1/max/chat
{
  "message": "Follow up on open quotes older than 48 hours",
  "desk": "forgedesk"
}
```

Tasks created via `/api/v1/max/tasks` carry a `desk_id` field that binds the task to the responsible desk. The desk_manager service (at `app/services/max/desk_manager.py`) tracks ownership, status, and completion.

### Ambiguous Routing Fallback

If intent classification cannot determine the correct desk with confidence above 80%, MAX sends the task to SupportDesk for human-assisted routing, and notifies the founder via Telegram.

---

## How Desks Report Back to MAX

### Daily Summaries at Midnight

Each desk generates a structured JSON summary at `00:00` local time and posts it to a central aggregation endpoint. MAX compiles these into a unified nightly report stored in the session log.

**Summary schema per desk:**

```json
{
  "desk_id": "forgedesk",
  "report_date": "2026-02-27",
  "tasks_completed": 12,
  "tasks_pending": 3,
  "tasks_failed": 0,
  "escalations_raised": 1,
  "escalation_details": ["Quote #0047 exceeds $5K threshold — awaiting founder approval"],
  "revenue_impact": 4200.00,
  "alerts": [],
  "metrics": {
    "quotes_sent": 5,
    "appointments_scheduled": 3,
    "jobs_completed": 4
  }
}
```

### Event-Driven Alerts

Desks do not wait for the midnight summary to surface critical information. Alert events are pushed in real time via the Telegram bot integration whenever:

- An escalation trigger fires
- A task fails after retry
- A time-sensitive item requires action before end of day
- A crisis event is detected (RecoveryDesk)

**Alert format:**

```
[FORGDESK ALERT] Quote #0047 ($6,200) ready for founder review.
Customer: J. Martinez | Job: Custom cabinet set | Due: Mar 3
Action: Approve or reject → /api/v1/quotes/0047
```

---

## How the Founder Reviews Desk Performance

### Weekly Dashboard (Fridays at 09:00)

MAX generates a consolidated weekly performance dashboard delivered to the Founder Dashboard (`localhost:3009`) and via Telegram summary.

**KPIs per desk:**

| Desk | KPI Set |
|------|---------|
| ForgeDesk | Quotes sent, conversion rate, avg quote value, jobs completed, revenue collected |
| MarketDesk | Listings active, orders processed, avg order value, inventory turnover, negative review count |
| SocialDesk | Posts published, avg engagement rate, follower growth, top performing content |
| AmpDesk | Active campaigns, client satisfaction score, on-time delivery rate, MRR from clients |
| RecoveryDesk | Daily check-in completion rate, active users, crisis escalations, milestone achievements |
| SupportDesk | Tickets received, first-response time, resolution rate, escalation rate, CSAT score |

### Dashboard Access

The Founder Dashboard at port 3009 displays real-time desk status via the `useSystemData` hook, which polls desk health and task states. Each desk is a card showing:

- Status (active / idle / alert)
- Tasks completed today
- Open tasks
- Last escalation timestamp
- Quick-action buttons (view tasks, send message to desk, view log)

---

## Morning Briefing Format

Each morning at `07:00`, MAX compiles a briefing from all active desks and delivers it via Telegram. Each desk contributes one section. The briefing is designed to be read in under 3 minutes.

```
EMPIRE MORNING BRIEFING — February 27, 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ForgeDesk (WorkroomForge)
Status: Active
Pending: 2 quotes awaiting send | 1 quote over $5K needs your approval
Alerts: Quote #0047 ($6,200) — J. Martinez, due Mar 3
Metrics: 4 jobs completed yesterday | $3,800 collected

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MarketDesk (MarketForge)
Status: Active
Pending: 8 new orders to fulfill | 3 listings need photo update
Alerts: 1 negative review (3 stars) on SKU-2241 — draft response ready
Metrics: 14 orders yesterday | $1,204 GMV

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SocialDesk (SocialForge)
Status: Active
Pending: Content calendar for next week needs your review
Alerts: None
Metrics: 3 posts published | 2.4% avg engagement | +47 followers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AmpDesk (AMP)
Status: Active
Pending: Monthly report for Client A due Friday
Alerts: None
Metrics: 3 campaigns active | 0 client escalations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RecoveryDesk (RecoveryForge)
Status: Active
Pending: 2 users missed yesterday's check-in — care team notified
Alerts: None
Metrics: 91% check-in completion | 0 crisis events

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SupportDesk (Cross-Business)
Status: Active
Pending: 4 open tickets (1 >24h — needs your attention)
Alerts: 1 ticket from VIP customer (spend >$2K) — draft response ready
Metrics: 18 tickets resolved yesterday | 4.2 min avg first response

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTIONS NEEDED TODAY:
1. Approve Quote #0047 — ForgeDesk
2. Review negative review response — MarketDesk
3. Review VIP support ticket — SupportDesk
4. Approve next week's content calendar — SocialDesk
```

---

## Telegram Integration Policy

The Telegram bot integration (`app/services/max/telegram_bot.py`) enforces a strict policy on which desks can communicate with customers directly and which can only message the founder.

### Desks with Direct Customer Messaging

| Desk | Customer Channels | Permitted Message Types |
|------|-------------------|------------------------|
| **ForgeDesk** | Customer phone/email via Telegram bot | Appointment reminders, quote delivery, payment reminders, job status updates |
| **SupportDesk** | Customer Telegram or linked chat | Ticket acknowledgments, status updates, FAQ responses, resolution confirmations |

**Rationale**: These two desks have the highest volume of routine customer touchpoints where autonomous messaging reduces friction without brand risk.

### Desks that Message the Founder Only

| Desk | Telegram Target | Message Types |
|------|----------------|---------------|
| **MarketDesk** | Founder only | Order alerts, inventory warnings, negative review drafts, pricing flags |
| **AmpDesk** | Founder only | Client report delivery, escalation alerts, campaign pause notifications |
| **SocialDesk** | Founder only | Content calendar drafts, engagement anomalies, platform alerts |
| **RecoveryDesk** | Founder + designated crisis team | Crisis alerts (immediate), daily summary, milestone reports |

**Rationale**: MarketDesk and AmpDesk messaging has higher brand and financial stakes. SocialDesk communications require strategic approval. All outbound content from these desks goes to the founder for review before any external send.

### Telegram Message Routing Implementation

```python
# Pseudo-logic in desk_manager / telegram_bot integration:
CUSTOMER_MESSAGING_ENABLED = ["forgedesk", "supportdesk"]
FOUNDER_ONLY_DESKS = ["marketdesk", "ampdesk", "socialdesk", "recoverydesk"]

def route_telegram(desk_id: str, message: str, recipient: str):
    if desk_id in CUSTOMER_MESSAGING_ENABLED:
        send_to_customer(recipient, message)
        log_outbound(desk_id, recipient, message)
    else:
        send_to_founder(message, context=desk_id)
```

All outbound messages are logged to the audit trail regardless of destination.

---

## Implementation Roadmap

### Phase 1 — ForgeDesk (Q1 2026)

**Target**: January–March 2026

**Deliverables**:
- ForgeDesk system prompt and desk config in SQLite (`desk_configs` table)
- Quote automation: auto-generate, auto-send, auto-follow-up via `/api/v1/quotes`
- Customer CRM integration: new customer intake, history lookup, tagging
- Scheduling automation: appointment booking, reminders, conflict detection
- Telegram outbound: ForgeDesk sends appointment + payment reminders to customers
- Escalation handler: quotes over $5K flagged to founder via Telegram
- Morning briefing: ForgeDesk section wired into 07:00 summary
- Midnight summary: ForgeDesk nightly JSON report to MAX aggregator

**Success criteria**:
- Founder can go a full week without manually touching the quote pipeline
- All customer appointments have automated reminders
- Zero missed escalations on high-value quotes

---

### Phase 2 — MarketDesk + SupportDesk (Q2 2026)

**Target**: April–June 2026

**Deliverables**:
- MarketDesk system prompt and desk config
- Listing automation: AI-generated descriptions, bulk publish, multi-marketplace sync
- Inventory sync: real-time stock updates across platforms
- Order processing: auto-acknowledge, trigger fulfillment, update tracking
- SupportDesk system prompt and desk config
- Ticket routing engine: classify and route to correct desk by app domain
- FAQ responder: knowledge base-powered automatic responses
- SLA tracker: first-response time monitoring, escalation on breach
- SupportDesk Telegram: customer-facing ticket status updates
- MarketDesk Telegram: founder-only order and review alerts
- Both desks wired into morning briefing and midnight summary

**Success criteria**:
- 80%+ of support tickets resolved without founder involvement
- All marketplace listings maintain description quality score >85%
- Order processing latency under 2 minutes from purchase to acknowledgment

---

### Phase 3 — SocialDesk + AmpDesk (Q3 2026)

**Target**: July–September 2026

**Deliverables**:
- SocialDesk system prompt and desk config
- Content scheduling pipeline: draft → founder review → schedule → publish
- Hashtag research automation: platform-specific trending tag integration
- Engagement monitoring: comment classification, positive auto-response
- Weekly analytics report generation per platform
- AmpDesk system prompt and desk config
- Campaign management framework: execute approved campaigns autonomously
- Client reporting: automated weekly/monthly PDF reports
- Content creation pipeline: brief → AI draft → approval workflow
- Campaign KPI monitoring: alert on underperformance thresholds
- Both desks wired into morning briefing and midnight summary

**Success criteria**:
- Social posting cadence maintained with zero founder scheduling effort
- Client reports delivered on time for 100% of accounts
- Founder content review time under 15 minutes per week

---

### Phase 4 — RecoveryDesk + Cross-Desk Orchestration (Q4 2026)

**Target**: October–December 2026

**Deliverables**:
- RecoveryDesk system prompt and desk config
- Daily check-in automation: prompt delivery, completion tracking, missed check-in alerts
- Crisis escalation pipeline: immediate Telegram push to founder + crisis team, zero latency
- HIPAA-compliant audit logging for all RecoveryDesk actions
- Milestone detection and celebration messaging
- Cross-desk orchestration layer:
  - MAX routes multi-desk tasks (e.g., a new customer needs quote + support ticket + social welcome)
  - Desk-to-desk handoff protocol (SupportDesk hands off to ForgeDesk for job-specific issues)
  - Cross-desk conflict resolution (scheduling conflicts, shared customer records)
  - Unified task dependency graph: task completion in one desk triggers downstream tasks in another
- Full autonomous morning briefing: all 6 desks contribute, MAX formats and sends
- Midnight summary aggregation: single nightly report across all desks
- Weekly performance dashboard: all desk KPIs in one Founder Dashboard view
- Desk health monitoring: alert founder if any desk goes silent for >2 hours during business hours

**Success criteria**:
- All 6 desks operational and reporting daily
- Founder daily intervention time under 30 minutes for routine operations
- Zero missed crisis escalations from RecoveryDesk
- Cross-desk handoff success rate >95%

---

## Technical Implementation Notes

### Backend Wiring

All desks are registered in the `desk_configs` SQLite table. The schema supports:

```sql
CREATE TABLE desk_configs (
  desk_id     TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  icon        TEXT,
  color       TEXT,
  system_prompt TEXT,
  tools       TEXT,   -- JSON array of tool identifiers
  layout      TEXT,   -- JSON array for UI layout config
  sort_order  INTEGER DEFAULT 0,
  is_active   INTEGER DEFAULT 1,
  created_at  TEXT DEFAULT (datetime('now')),
  updated_at  TEXT DEFAULT (datetime('now'))
);
```

Desk system prompts define the agent's persona, tool access list, escalation rules, and output format requirements. They are loaded at chat time by the AI router.

### Task Engine Integration

Tasks created via `/api/v1/max/tasks` carry a `desk_id`. The `desk_manager` service tracks state transitions:

```
pending → in_progress → completed
                    └→ failed (with error + retry count)
```

Failed tasks with retry exhausted trigger Telegram alerts. All task events are logged.

### AI Router Chain

MAX uses a priority chain for AI inference:

1. **xAI Grok** — primary (fastest, most capable for business reasoning)
2. **Claude** — fallback if Grok unavailable
3. **Ollama (local)** — final fallback running on the Beelink mini PC

This chain ensures desks continue operating during cloud provider outages, with gracefully degraded capability on local Ollama.

### Guardrails

Every message processed by any desk passes through `app/services/max/guardrails.py` before AI inference. Input validation blocks:
- Prompt injection attempts
- PII extraction attempts
- Overly broad destructive commands

Sanitized output is logged and returned. No desk can bypass guardrails.

### Data Residency

All desk data, task logs, customer records, and audit trails are stored locally on the Beelink mini PC. No sensitive operational data is sent to cloud providers beyond the message content required for AI inference (which itself is subject to Grok/Anthropic/Ollama privacy policies).

---

## Governance and Override Policy

The founder retains ultimate authority over all desk actions. Override mechanisms:

1. **Telegram override**: Send "STOP [desk_name]" to pause all autonomous actions from a desk immediately
2. **Dashboard kill switch**: Each desk card in the Founder Dashboard has a pause/resume toggle
3. **API override**: `PATCH /api/v1/desks/{desk_id}` with `{"is_active": false}` disables the desk
4. **Escalation acknowledgment**: Escalation alerts require explicit founder acknowledgment before the desk proceeds on the flagged item

All founder overrides are logged with timestamp and action taken.

---

## Related Documentation

- [ECOSYSTEM.md](./ECOSYSTEM.md) — Full product ecosystem overview
- [EMPIRE_DESKS_AND_TASK_ENGINE_PLAN.md](./EMPIRE_DESKS_AND_TASK_ENGINE_PLAN.md) — Task engine specification
- [EMPIRE_ASSIST_SPEC.md](./EMPIRE_ASSIST_SPEC.md) — EmpireAssist messenger integration
- [TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md) — Telegram bot configuration
- [API.md](./API.md) — Full backend API reference
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Deployment and infrastructure guide
- [CRASH_RECOVERY_RUNBOOK.md](./CRASH_RECOVERY_RUNBOOK.md) — System recovery procedures
