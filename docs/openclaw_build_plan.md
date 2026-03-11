# OpenClaw / MAX Autonomous Business & Dev Intelligence — Build Plan

## Context
MAX is the founder's autonomous AI partner running the entire Empire ecosystem. Currently MAX has 12 desks, 22+ tools, 205 memories, and solid infrastructure — but desks are mostly template-based, there's no unified task pipeline for multi-step autonomous work, and the quoting system lacks a multi-phase approval workflow. This plan EXTENDS MAX without touching any existing working code.

## Ground Truth (from deep audit)
- 12 desks: forge/sales/market/marketing/support/finance/clients/contractors/IT/website/legal/lab
- Only 4 desks call AI (forge, sales, marketing, IT) — rest are template-based
- 22 tools in tool_executor.py — all execute real actions
- Telegram bot: founder-only auth, text/voice/photo, intent classification, auto-task creation
- AI routing: Grok → Claude → Ollama (Groq removed — no key, not a dependency)
- Quote system: full QIS pipeline, 3-tier pricing, PDF generation, verification (10 checks)
- Task DB: tasks table with status/priority/desk, task_activity table for logs
- Desks don't write files, commit git, or execute multi-step autonomous work
- Scheduler runs 6 daily snapshot tasks — not ongoing work execution

## Constraint: PRESERVE ALL EXISTING CAPABILITIES
- All 22+ tools remain untouched
- All 12 desks remain functional
- Telegram bot current handling stays
- AI routing chain stays (minus Groq dependency)
- No refactoring, no reorganization of working code
- EXTEND only — new code paths alongside existing ones

---

## Phase 1: Unified Task Pipeline (FOUNDATION)

### New Files
- `backend/app/services/max/pipeline/task_pipeline.py` — core pipeline engine
- `backend/app/services/max/pipeline/__init__.py`

### Extended Files
- `backend/app/db/init_db.py` — ALTER TABLE tasks (add pipeline columns)
- `backend/app/services/max/desks/desk_scheduler.py` — add executor loop
- `backend/app/services/max/telegram_bot.py` — add pipeline commands
- `backend/app/routers/max/router.py` — add pipeline endpoints
- `empire-command-center/app/components/screens/DesksScreen.tsx` — pipeline view

### What It Does
1. Single entry point: `submit_pipeline(title, description, source, channel)`
2. AI breaks high-level task into ordered subtasks with acceptance criteria
3. Routes subtasks to correct desks via existing desk_router
4. Background executor picks up queued subtasks (one at a time per desk)
5. Status: queued → assigned → in_progress → review → complete/failed
6. Founder approval from CC or Telegram for tasks in review state
7. Notifications on completion/failure via existing Telegram integration

### DB Changes (additive only)
```sql
ALTER TABLE tasks ADD COLUMN pipeline_id TEXT;
ALTER TABLE tasks ADD COLUMN subtask_order INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN acceptance_criteria TEXT;
ALTER TABLE tasks ADD COLUMN channel TEXT DEFAULT 'system';
ALTER TABLE tasks ADD COLUMN result_summary TEXT;
```

---

## Phase 2: Desk Execution Upgrades

### Extended Files
- All 12 desk files in `backend/app/services/max/desks/`
- `backend/app/services/max/desks/base_desk.py` — add ai_call helper

### New Files
- `backend/app/services/max/desks/innovation_desk.py` — desk #13

### What It Does
1. Add `ai_call(prompt, model_preference)` to base_desk — wraps ai_router with cost tracking per desk
2. Upgrade template desks: support, finance, market, clients, contractors → use AI for real responses with template as fallback
3. Innovation Desk: market scanning, competitor monitoring, monetization suggestions
4. Cross-desk delegation via pipeline

---

## Phase 3: AI Quoting System Revision

### Extended Files
- `backend/app/routers/quotes.py` — quick quote endpoint, phase advancement
- `backend/app/services/quote_engine/` — phase pipeline logic
- `empire-command-center/app/components/screens/WorkroomPage.tsx` — pipeline dashboard

### New Files
- `empire-command-center/app/components/business/quotes/QuotePipeline.tsx`

### What It Does
**Track 1 — Quick Quote:** dimensions + material + complexity → instant ballpark. Founder-only. "Promote to Full Analysis" button.

**Track 2 — Multi-Phase (extends existing QIS):**
- Phase 0: Intake (existing)
- Phase 1: AI Vision Analysis → founder review
- Phase 2: Measurements & Materials → founder review
- Phase 3: Pricing & Labor → founder review
- Phase 4: Profit & Margin → founder review
- Phase 5: Client Quote PDF → founder approve to send

Each phase stores validated data, carries photos, requires founder approval.

---

## Phase 4: Security Layer

### New Files
- `backend/app/services/max/security/sanitizer.py`
- `backend/app/services/max/security/voiceprint.py`
- `backend/app/middleware/auth_middleware.py`

### What It Does
1. Input sanitization on ALL channels (injection pattern detection + logging)
2. Voiceprint verification for Telegram voice (speechbrain/resemblyzer, CPU-only)
3. Runtime: file write scoping, command timeout, rate limiting
4. Auth middleware for Command Center API requests

---

## Phase 5: Proactive Intelligence & Visibility

### Extended Files
- `backend/app/services/max/desks/desk_scheduler.py` — morning brief, weekly report
- `empire-command-center/app/components/screens/DesksScreen.tsx` — pipeline UI
- `empire-command-center/app/components/layout/RightPanel.tsx` — intelligence cards

### What It Does
1. Daily morning brief (7:30AM) → Telegram + CC dashboard
2. Weekly business report with monetization suggestions
3. Pipeline visualization in Command Center
4. Cost breakdown per desk
5. Priority backlog execution (CraftForge frontend, DEV-badge items)

---

## Verification
- Phase 1: Send task from Telegram → watch breakdown → desk execution → notification
- Phase 2: Ask desk a complex question → get AI-driven response (not template)
- Phase 3: Upload photo → advance through all 5 phases → PDF generated
- Phase 4: Send injection attempt → blocked + logged. Send wrong voice → rejected + alert
- Phase 5: Check morning brief arrives on Telegram. View pipeline in CC.
