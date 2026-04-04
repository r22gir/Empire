# Empire Productivity Roadmap
## Ranked by Impact × Effort

---

## Bucket 1: Fix Immediately (broken/confusing)

1. **Remove old LeadForgePage + RelistAppScreen imports** — dead components still imported
   - Fix: Remove imports from page.tsx, delete old files
   - Time: 5 min

2. **Calendar screen shows nothing useful** — opens but no backend
   - Fix: Either hide calendar from quick actions or wire Google Calendar API
   - Time: Hide=5min, Wire=2hrs

3. **Research results don't persist** — findings vanish after navigation
   - Fix: Add "Save to Docs" button on research results
   - Time: 30 min

4. **Video Call screen is dead** — no WebRTC integration
   - Fix: Hide from screen modes until real integration built
   - Time: 5 min

---

## Bucket 2: High-Value Enhancement (10x improvements)

1. **Task auto-execution on create** — already built, verify it runs for every new task
   - Current: Tasks created via API sit as 'todo', need manual execute
   - Enhancement: Auto-execute immediately when created from MAX chat
   - Impact: HIGH — desks produce results without manual trigger

2. **Drawing → Quote one-click flow** — drawing exists, quote requires re-entry
   - Current: Manual "Create Quote" after seeing drawing
   - Enhancement: Pre-fill quote from drawing's job context automatically
   - Impact: HIGH — saves 5-10 min per quote

3. **Prospect → Campaign enrollment from detail panel** — currently separate screens
   - Current: View prospect → go to Campaigns → find campaign → enroll
   - Enhancement: "Enroll in Campaign" dropdown right in prospect detail panel
   - Impact: MEDIUM — saves clicks

4. **Inbox → Task conversion** — emails can't become tasks
   - Current: View email, manually create task
   - Enhancement: "Create Task from Email" button on each message
   - Impact: MEDIUM — captures action items

5. **Campaign auto-execution cron** — campaigns don't execute without manual trigger
   - Current: "Execute Due Steps" button only
   - Enhancement: Add 7:30 AM daily cron for campaign step execution
   - Impact: HIGH — automation actually automates

---

## Bucket 3: Good Overlap (Keep)

- Tasks: quick action + screen + right panel = same data, 3 useful views
- Quotes: Workroom section + Quote Builder = different entry points
- Docs: Module tabs + Document screen = filtered per context

---

## Bucket 4: Overlap to Consolidate

- LeadForgePage (old) + LeadForgePageNew → remove old
- RelistAppScreen (old) + RelistAppPage → remove old

---

## Bucket 5: Dead Features to Wire or Hide

| Feature | Action | Priority |
|---------|--------|----------|
| Calendar | Hide quick action OR wire Google Calendar | Medium |
| Video Call | Hide screen mode | Low |
| SmartListerPanel | Archive (not routed) | Low |
| EcosystemProductPage | Keep as generic fallback | Low |

---

## Bucket 6: Missing Features for Transformation

1. **Global search across all data** — search customers, quotes, jobs, prospects, tasks from ONE bar
   - Impact: HUGE — saves browsing multiple screens

2. **Notification center** — unified alerts for: task completed, campaign response, payment received, drawing ready
   - Impact: HIGH — founder knows what needs attention

3. **Mobile-first quick actions** — phone-optimized create quote, add prospect, execute task
   - Impact: HIGH — founder works from phone via Telegram + CC

4. **Dashboard KPI cards that link to action** — click "8 overdue" → jumps to overdue list
   - Impact: MEDIUM — dashboard becomes actionable

5. **Cross-module navigation** — from any task → see related job → see related quote → see related drawing
   - Impact: HIGH — eliminates context switching

---

## Top 10 Quick Wins (Highest Impact, Lowest Effort)

1. Remove dead imports (LeadForgePage old, RelistAppScreen old) — 5 min
2. Hide Calendar from quick actions (or label "Coming Soon") — 5 min
3. Hide Video Call screen mode — 5 min
4. Add campaign execution to morning cron — 15 min
5. Add "Save to Docs" on Research results — 30 min
6. Add "Create Task from Email" button in Inbox — 30 min
7. Add "Enroll in Campaign" to prospect detail panel — 30 min
8. Pre-fill quote dimensions from drawing job context — 1 hr
9. Add clickable KPI cards on dashboard — 1 hr
10. Add prospect count to right panel quick stats — 15 min
