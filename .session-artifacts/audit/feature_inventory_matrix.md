# Empire Feature Inventory Matrix
## Full Audit — April 4, 2026

### Quick Reference
- **48 screen components** in Command Center
- **29 sidebar nav items**
- **868 API endpoints** across 67 routers
- **23 screen modes**
- **4 services running** (Backend, CC, OpenClaw, Ollama)

---

## TIER A — Production-Grade (Use Daily)

| Feature | Backend | Data | Score | Mobile | Actionability | Notes |
|---------|---------|------|-------|--------|---------------|-------|
| MAX Chat | ✅ 868 endpoints | 46 chats, 486 audit entries | 9.0 | Good | Auto-executing | Core of everything |
| Tasks | ✅ /tasks/ CRUD + execute | 365 tasks, desk execution | 8.0 | Good | Auto-executing | Bridge to desks working |
| Quotes | ✅ /quotes/ + PDF | 17 quotes, PDF gen | 8.5 | Medium | Actionable | Full quote → invoice flow |
| CRM/Customers | ✅ /crm/customers | 132 customers | 7.5 | Good | Actionable | Real QB import data |
| Inventory | ✅ /inventory/ | 155 items | 7.0 | Medium | Actionable | Real data from imports |
| Drawing Studio | ✅ /drawings/ + renderers | 204 styles, 5 renderers | 8.0 | Medium | Actionable | Inline SVG in chat |
| Product Catalog | ✅ /drawings/catalog | 18 cats, 204 styles | 7.0 | Good | View + Draw | Browsable, searchable |
| LeadForge Prospects | ✅ /leadforge/prospects | 278 real prospects | 8.5 | Good | Actionable | Real Brave + Google search |
| LeadForge Campaigns | ✅ /leadforge/campaigns | 3 templates, 13 steps | 7.5 | Medium | Actionable | Enroll + execute |
| Jobs Pipeline | ✅ /jobs/ + unified | 8 jobs | 7.0 | Medium | Actionable | Job → quote → invoice chain |
| Invoices | ✅ /invoices/ + PDF | 8 invoices, PDF gen | 7.5 | Medium | Actionable | From-job auto-fill |
| AI Desks | ✅ 17 desks | 365 tasks executed | 7.5 | N/A | Auto-executing | Real AI results synced to DB |
| Self-Heal | ✅ /max/self-heal-status | Incident table, canary | 6.5 | N/A | Auto-executing | Capability registry |
| Chat History | ✅ /chats/list | 46 conversations | 6.5 | Good | View + Load | Sorted newest first |
| System Health | ✅ /system/health | 4/4 services | 7.0 | Good | View-only | Real-time port checks |

## TIER B — Works, Needs Polish

| Feature | Backend | Data | Score | Issue | Fix Priority |
|---------|---------|------|-------|-------|-------------|
| WorkroomForge | ✅ Full suite | Real data | 7.0 | 14 sections but no unified nav | Medium |
| CraftForge | ✅ 23 endpoints | Real data | 6.5 | Module routing fixed but sparse data | Low |
| SocialForge | ✅ 15 endpoints | 6 drafts | 6.0 | Can't publish (token perm) | High — owner action |
| Desks Screen | ✅ /max/desks | 17 desks | 5.5 | Shows idle status, no quick-execute | Medium |
| Telegram Screen | ✅ Bot active | Messages | 5.5 | View-only, no inline actions | Low |
| Follow-ups | ✅ /campaigns/followups | Working | 6.0 | Empty until campaigns activated | Low |
| Presentation Mode | ✅ Avatar chat | Voice + TTS | 5.0 | Avatar iframe loading issues | Low |
| Business Profile | ✅ Settings page | Editable | 5.0 | Basic form, no branding preview | Low |

## TIER C — Basic / Reference Only

| Feature | Backend | Score | Issue |
|---------|---------|-------|-------|
| Research Screen | ✅ Web search tool | 4.0 | Results don't persist, no save-to-docs |
| Document Screen | ✅ File serve | 3.5 | Static doc list, no real doc management |
| Inbox/Mail | ✅ Gmail check | 4.0 | Can view but limited triage actions |
| OpenClaw Tasks | ✅ 32 skills | 4.0 | Task list view, no inline execution |
| LuxeForge | ✅ Intake portal | 3.5 | Intake works but sparse usage |
| MarketForge | ✅ Endpoints | 3.0 | Frontend wired but no real marketplace data |
| ShipForge | ✅ Endpoints | 3.0 | Needs ShipStation key for real shipping |
| SupportForge | ✅ 4 routers | 3.0 | Ticketing exists but 0 tickets |
| ContractorForge | ✅ Endpoints | 3.0 | Frontend built, sparse data |
| EmpirePay | ✅ Crypto endpoints | 2.5 | Needs real wallet setup |
| EmpireAssist | ✅ Basic | 2.0 | Minimal functionality |
| ApostApp | ✅ 14 endpoints | 3.0 | Full UI but 0 orders |
| LLCFactory | ✅ 18 endpoints | 3.0 | Full UI with services but 0 formations |
| ConstructionForge | ✅ 41 endpoints | 4.0 | Seeded with Argos Campestre (60 lots) |
| StoreFront Forge | ✅ 41 endpoints | 4.0 | Seeded with 50 products, POS terminal |

## TIER D — Partial / Placeholder

| Feature | Issue |
|---------|-------|
| Calendar | No real scheduling backend — chat-based only |
| Video Call | Screen exists but no WebRTC/Zoom integration |
| RelistApp (old) | Legacy screen still exists alongside new RelistAppPage |
| PricingPage | SaaS pricing display — static, no checkout |
| Ecosystem Product | Generic placeholder for unmapped products |

## TIER E — Dead / Should Hide

| Feature | Issue | Recommendation |
|---------|-------|----------------|
| VetForge | "Coming Soon" placeholder | Keep as planned, badge correct |
| PetForge | "Coming Soon" placeholder | Keep as planned, badge correct |
| SmartListerPanel | Old component, not routed | Remove or archive |
| LeadForgePage (old) | Replaced by LeadForgePageNew | Remove import |
| RelistAppScreen (old) | Replaced by RelistAppPage | Remove import |

---

## OVERLAP ANALYSIS

### Good Overlaps (Keep):
- Tasks quick action + Tasks screen + right panel count = same API, different views
- Workroom quotes section + Quote Builder screen = different entry points, same data
- Module Docs tabs + Document screen = same serve endpoint, filtered per module

### Needs Attention:
- Chat history in sidebar vs ChatHistoryPanel component — should share state
- LeadForgePage (old) vs LeadForgePageNew — old should be removed
- RelistAppScreen (old) vs RelistAppPage — old should be removed

### Data Flow Gaps:
- Research → findings DON'T save to documents or tasks
- Calendar → no real backend (chat-based placeholder)
- Email inbox → can't convert email to task or contact
- Drawing → can create quote but requires manual "Create Quote" click

---

## KEY METRICS

| Metric | Value |
|--------|-------|
| Total screen components | 48 |
| Active (Tier A+B) | 23 |
| Basic (Tier C) | 15 |
| Partial (Tier D) | 5 |
| Dead (Tier E) | 5 |
| API endpoints | 868 |
| Database tables | 75+ |
| Real data records | 132 customers, 278 prospects, 365 tasks, 17 quotes, 8 invoices, 8 jobs, 6 social posts, 155 inventory, 204 product styles |
