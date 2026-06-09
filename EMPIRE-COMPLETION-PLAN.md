# EMPIRE COMPLETION PLAN

**Status:** Planning only. No branches, no worktrees, no implementation, no push.
**Date:** 2026-06-08
**Coordinator:** Empire Completion Coordinator (this Hermes Desktop session)
**Canonical repo:** `/home/rg/empire-repo-main` (HEAD `2867978`, `main`)
**Memory governance:** `HERMES_BACKGROUND_REVIEW_DISABLED=1` is active. `HERMES_HTML_CONTEXT` is OFF.

---

## 1. Executive Summary

### 1.1 What this plan is

A supervised, multi-agent plan to move EmpireBox from scattered working modules into revenue-ready systems. Focus areas, in priority order:

1. **Drawing Quality Sprint 2** (bench → banquette → window → cushion → sofa → chair → headboard → ottoman → cabinet → table)
2. **Apostille App completion** (landing page + intake + vendor routing)
3. **SocialForge Apostille promotion** (30-day bilingual content calendar)
4. **VendorOps Apostille routing** (12-step operational lifecycle)
5. **Multi-agent branch/worktree execution plan** (safe parallel work)

### 1.2 What is possible right now

- Four backend modules (Drawing, Apostille, SocialForge, VendorOps) have working API surfaces (13–25 routes each) and return HTTP 200 on `/health`.
- All four modules are **API-complete, UI-missing**. The missing 20–40% is **front-end + integration + content**, not core engineering.
- Three external CLIs (claude, codex, opencode) are installed, authed, and callable from this session.
- Harry/OpenCode on Tailscale `:8787` is reachable (HTTP 200) and can be driven via copy/paste prompt.
- `delegate_task` sub-agents are available (max 3 concurrent, leaf or orchestrator, max depth 1).

### 1.3 What is NOT possible right now

- Auto-spawning parallel agents that all write to the same worktree (forbidden by design).
- Letting any agent push to `origin/main` of any repo (Founder-mediated merges only).
- Letting any agent write to `~/.hermes/.env`, `.opencode/config.json`, `MEMORY.md`, or `USER.md`.
- Running background memory-review rewrites (kill switch is on, stays on).
- Any change to MAX backend routing (MAX `main` is shared with Harry).

### 1.4 Fastest path to revenue

1. **Apostille MVP v1 landing page + intake form** (days, not weeks; uses existing `/api/v1/apostapp/*`; no backend changes).
2. **Apostille + VendorOps integration** (1–2 weeks; routes each order to a vendor; small data model extension).
3. **SocialForge Apostille campaign content** (days; 30-day bilingual calendar with CTAs to the new landing page).
4. **Drawing Quality Sprint 2** (2–3 weeks; bench → banquette → window; bench may need a rewrite).
5. **VendorOps multi-vendor data model** (1–2 weeks; notaries, translators, couriers, government offices as first-class entities).

---

## 2. Agent Desk Inventory

| Agent / Desk | Available | Directly callable from this Hermes | Can read | Can write | Can run tests | Can inspect runtime | Safe role | Restrictions |
|---|---|---|---|---|---|---|---|---|
| **Hermes Desktop (this session)** | YES (PID 2392462) | n/a — orchestrator | YES | YES (with approval gates) | YES | YES | **Empire Completion Coordinator** | Never edits Empire `main` directly; never pushes; never writes `.env` without approval; never edits `MEMORY.md`/`USER.md` |
| **delegate_task sub-agents (in-session)** | YES (max 3 concurrent, leaf/orchestrator, depth 1) | YES — `delegate_task` tool | YES (isolated) | YES (isolated) | YES | YES (isolated) | **Code auditor / Reporter** | No approval gate inside child; orchestrator enforces via context; leaf cannot `clarify` |
| **Harry / OpenCode (Tailscale `:8787`)** | YES (service active, HTTP 200) | NO — different UI, Founder on phone or desktop browser | YES | YES | YES (TUI) | YES (TUI) | **Code implementer on assigned worktree** | Copy/paste prompt; one workstream at a time; branch must be pre-created |
| **Codex CLI (this machine)** | YES (`~/.local/bin/codex` v0.134.0, authed) | YES — `terminal(pty=true)` | YES | YES | YES (`codex exec`) | NO (no TUI in pty) | **Code implementer, non-interactive** | Needs explicit worktree path; `codex review` is read-only subcommand |
| **Claude Code CLI (this machine)** | YES (`/usr/bin/claude` v2.1.90, auth verified live) | YES — `terminal(pty=true)` | YES | YES | YES | NO (no TUI in pty) | **Code implementer, alternate model** | Same as Codex; useful for cross-model review |
| **OpenCode CLI (this machine)** | YES (`/home/rg/.opencode/bin/opencode` v1.4.3, authed) | YES — `opencode acp` (ACP) or TUI | YES | YES | YES | YES (TUI) | **Code implementer, ACP-attached** | `acp` is the right headless invocation; TUI is the same engine as Harry's |
| **MAX backend (uvicorn `:8000`)** | YES (PID 2301556, operational) | YES — direct HTTP | YES (any route) | **NO** — never write to MAX `main` from an agent | NO | YES (OpenAPI at `/openapi.json`, runtime at `/health`) | **Read-only introspection + smoke-testing** | Routes are runtime-mutable, no test harness exposed over HTTP |
| **OpenClaw (port 7878)** | YES (Python, version 1.0.0, health returns `ok`) | NO | OpenAPI shows 3 routes: `/chat`, `/health`, `/skills` | — | — | — | **Local Ollama-fronted chat model provider** | NOT a delegate-able agent; the skill `openclaw-integration` describes a different design not yet implemented. Do not route `delegate_task` to it. |
| **Curator (memory-review subsystem)** | Disabled (commit `ec8716199`) | n/a | n/a | n/a | n/a | n/a | **OFF** | Do not re-enable during this sprint |

**Callable from this session with no copy/paste:** 4 (delegate_task + 3 CLIs).
**Reachable via copy/paste to Founder:** +1 (Harry).
**Read-only inspection surfaces:** MAX backend, OpenAPI, journals, ports.

---

## 3. Module Readiness

| Module | Current status | Revenue readiness | Missing pieces | Owner agent | Recommended branch |
|---|---|---|---|---|---|
| **Drawing Studio** (Backend) | API-complete (19 routes); renderers for sofa/chair/ottoman/cushion/headboard/millwork/banquette (straight/L/U)/window (31 styles); everything else → `render_generic` (rectangles). `test_drawing_repair_sprint_1.py` exists. | **NOT revenue-ready** — Sprint 1 was stability, not quality; output is "functional schematic, too crude for client presentation" per Founder. | Title block polish, dimension layout, no-overlap, upholstery/welt/skirt/leg/channel annotation, distinct Workroom vs Woodcraft branding, SVG/PDF parity, assumed-dim warnings, drawing quality standard | Hermes Desktop for audit+standard, then Harry or Codex | `feature/drawing-quality-sprint-2` |
| **Apostille App** (Backend) | API-complete (13 routes); 815 lines in `apostapp.py`; **NO front-end pages** | **NOT customer-facing-ready** | Landing page, intake form, upload UI, customer dashboard, quote display, payment handoff (Founder-mediated in v1), disclaimer copy | Hermes Desktop for product/copy, Codex or Claude for front-end | `feature/apostille-completion` |
| **SocialForge** (Backend) | API-complete (21 routes: accounts, campaigns, calendar, connected-accounts, ai-guide, sync); **no visible front-end** | **NOT marketing-ready** | 30-day calendar, bilingual templates, image/video prompt set, CTA definitions, SocialForge-Apostille link | Hermes Desktop for copy/strategy, Codex/Claude for image-prompt set | `feature/socialforge-apostille-campaigns` |
| **VendorOps** (Backend) | API-complete (25 routes); `test_vendorops_core.py` exists; `vendorops_alert_runner.py` service exists; **no front-end, no apostille lifecycle** | **NOT operations-ready for Apostille** | Vendor type extension (notary, translator, courier, gov office), 12-step task lifecycle, reminder/alert rules, customer update triggers, dashboard view | Hermes Desktop for ops design, Harry or Codex | `feature/vendorops-apostille-routing` |
| **MAX backend** | API-complete (987 KB OpenAPI); uvicorn running; `/health` operational | Operational; do not modify during this sprint | None required | No agent touches MAX | n/a |
| **Empire front-end (Next.js)** | 21 top-level routes; `:3000` test, `:3005` live; pages: archiveforge, archiveforge-life, channels, intake, luxe, luxeforge, max, orchestration, portal, presentation, pricing, quote, services, tools, transcriptforge-review, woodcraft, workroom, amp, api | Operational; needs new top-level routes for the four workstreams | New front-end pages for apostille, vendorops, socialforge, drawings-studio | Codex or Claude | (each workstream branch) |

---

## 4. Workstream Plans

### Phase 1 — Drawing Quality Sprint 2

**Phase 1A — Audit (read-only, this batch):** `REPORT-drawing-sprint-2-audit.md`
- Inspect `backend/app/services/vision/{bench_renderer,drawing_service,parametric_templates,renderer_registry,primitives}.py`, `backend/app/routers/drawings.py`, `backend/tests/test_drawing_repair_sprint_1.py`
- Identify why the current bench PDF looks crude: hardcoded stroke widths, placeholder rectangles, dimension overlap, label clipping, which item types hit the `render_generic` fallback
- Identify if DXF export is wired (Founder's audit: "DXF export available but hidden")
- Identify if yardage/fabric logic is connected to drawing output

**Phase 1B — Quality standard (read-only, this batch):** `DRAWING-QUALITY-STANDARD.md`
- **Client presentation drawing** — large title block, clean line work, fabric/finish/wood callouts, no measurements, 1:20 or 1:50 scale
- **Shop/fabrication drawing** — full measurements, dimension callouts, no overlap, cushion/welt/skirt/leg annotations, materials list
- **Measurement-only fallback** — explicit "dimensions assumed" warnings

**Phase 1C — Implementation (gated):** after Founder approves the audit + standard.
- Branch: `feature/drawing-quality-sprint-2`
- Worktree: `/home/rg/empire-repo-main-drawing-sprint-2` (new, from `main`)
- Files: `bench_renderer.py` (highest priority), `drawing_service.py`, `renderer_registry.py`, `parametric_templates.py`, `primitives.py`
- Tests: extend `test_drawing_repair_sprint_1.py`, add `test_drawing_quality_sprint_2.py`
- Agent: Codex (delegate_task) or Harry
- Risk: **medium** — may require bench_renderer rewrite

### Phase 2 — Apostille App Completion

**Phase 2A — Audit (read-only, this batch):** `REPORT-apostille-readiness.md`
- Read `apostapp.py` (815 lines) end-to-end
- Map the 13 routes to the customer journey
- Identify per-step status: exists/works vs stubbed/missing

**Phase 2B — MVP v1 plan (Founder-mediated, no payment automation):**
- Public landing page (Spanish + English, DC/MD/VA, "not legal advice" disclaimer, contact form, ~$ price ranges)
- Intake form (name, email, phone, document type, destination country, urgency, upload)
- Backend creates `customer` + `order` via existing routes
- Founder gets notification (Telegram/MAX outbound)
- Founder generates quote via existing `GET /pricing-calculator`, emails customer
- Customer pays via Zelle/Venmo/wire (Founder's existing accounting, no Stripe)
- Vendor work via VendorOps (depends on Phase 4)
- Customer updates at each status change (manual or scheduled)
- **Defer to v2:** automated payment, automated email, automated vendor handoff

**Phase 2C — Implementation (gated):**
- Branch: `feature/apostille-completion`
- Worktree: `/home/rg/empire-repo-main-apostille-completion` (new)
- Files: new front-end pages `empire-command-center/app/apostille/**`, possibly minor backend notification additions
- Tests: `test_apostille_intake_journey.py`, `test_apostille_pricing.py`
- Agent: Codex or Claude
- Risk: **low** — front-end only, no backend changes expected
- MAX conflict risk: do not modify `services/max/ecosystem_catalog.py` or `services/max/empire_module_knowledge.py` unless required

### Phase 3 — SocialForge Apostille Promotion

**Phase 3A — Audit (read-only, this batch):** `REPORT-socialforge-apostille-gap.md`
- Inspect the 21 SocialForge API routes
- Inspect front-end `channels/` and `archiveforge/` dirs
- Identify: does the front-end have a SocialForge UI? content calendar view? scheduling?

**Phase 3B — Campaign content (read-only, this batch — includes the gap report and a 30-day calendar draft):**
- 30-day Apostille content calendar: mix of English/Spanish, themes (DC/MD/VA, Colombian documents, bilingual, business docs, school/transcript/legal, pickup/dropoff, urgent service, trust/process, "not legal advice")
- Spanish/English post templates: 5–10 reusable, parameterized
- Short video/image prompt set: 10–15 image prompts, 3–5 short-video scripts (30s, bilingual)
- Landing page CTA requirements
- SocialForge integration gap report

**Phase 3C — Implementation (gated):**
- Branch: `feature/socialforge-apostille-campaigns`
- Worktree: `/home/rg/empire-repo-main-socialforge-apostille` (new)
- Files: `backend/app/services/socialforge/apostille_campaigns.py` (new), `empire-command-center/app/socialforge/**` (new or extended)
- Tests: `test_socialforge_apostille_content.py`
- Agent: Hermes Desktop for copy, Codex/Claude for code
- Risk: **low** — additive
- **Do not publish, do not schedule, do not call any platform's publish API.** Founder reviews and clicks publish manually.

### Phase 4 — VendorOps Apostille Routing

**Phase 4A — Audit + design (read-only, this batch):** `REPORT-vendorops-apostille-design.md`
- Read `vendorops_alert_runner.py`, the 25 VendorOps API routes, `test_vendorops_core.py`
- Map the 12-step apostille operational lifecycle to existing VendorOps primitives
- Design the vendor data model extension, task schema, reminder rules, customer update triggers

**Phase 4B — Design (in the report):**
- **Vendor type enum:** `notary_dc`, `notary_md`, `notary_va`, `translator_es_en`, `courier_local`, `courier_national`, `government_office_dc`, `government_office_md`, `government_office_va`, `government_office_usda`
- **Task schema:** `apostille_task` with `task_id`, `order_id`, `vendor_id`, `task_type` (12 steps), `status`, `due_at`, `sla_hours`, `cost_cents`, `notes`, `evidence_url`
- **Reminder/alert rules:** 24h before `due_at` → vendor; at `due_at` → vendor + Founder; 24h overdue → Founder
- **Customer update triggers:** on `task_completed` for the relevant step
- **Dashboard view:** open orders, overdue tasks, vendor count, per-vendor queue

**Phase 4C — Implementation (gated):**
- Branch: `feature/vendorops-apostille-routing`
- Worktree: `/home/rg/empire-repo-main-vendorops-apostille` (new)
- Files: `backend/app/routers/vendorops.py` (new apostille task routes), `backend/app/services/vendorops_alert_runner.py` (extend), `backend/app/models/apostille_vendor_task.py` (new)
- Tests: `test_vendorops_apostille_routing.py`
- Agent: Harry or Codex
- Risk: **medium** — touches the alert runner which is in production

---

## 5. Multi-Agent Branch / Worktree Plan

### 5.1 Rules

1. **One workstream = one branch = one worktree = one agent at a time.** Never two agents on the same branch.
2. **No agent edits `main` directly.** `main` is read-only for all agents except the merge step (Founder-mediated).
3. **All feature branches start from current canonical `main` (HEAD `2867978`).**
4. **Each agent must produce a report before code.** Reports are the audit output of the relevant Phase XA section.
5. **Each implementation branch must have tests/checks.** Reference pattern: `test_drawing_repair_sprint_1.py`.
6. **Hermes Desktop (this session) acts as coordinator, not committer.** I read agent reports, summarize, recommend merge order. I do not write code to Empire branches directly.
7. **Harry/OpenCode and in-session sub-agents (Codex/Claude) may implement, but only after Founder approves the agent's report.**
8. **Founder approves merge order.** No agent pushes. No agent merges.

### 5.2 Proposed branches

| Workstream | Agent | Branch | Worktree path | Files likely touched | Tests | Risk | Approval needed |
|---|---|---|---|---|---|---|---|
| Drawing Quality Sprint 2 | Codex or Harry | `feature/drawing-quality-sprint-2` | `/home/rg/empire-repo-main-drawing-sprint-2` | `backend/app/services/vision/{bench_renderer,drawing_service,parametric_templates,renderer_registry,primitives}.py` | extend `test_drawing_repair_sprint_1.py`, add `test_drawing_quality_sprint_2.py` | medium | (a) audit, (b) standard, (c) branch, (d) implementation, (e) merge |
| Apostille completion | Codex or Claude | `feature/apostille-completion` | `/home/rg/empire-repo-main-apostille-completion` | `empire-command-center/app/apostille/**` (new) | `test_apostille_intake_journey.py`, `test_apostille_pricing.py` | low | (a) audit, (b) v1 plan, (c) branch, (d) implementation, (e) merge |
| SocialForge Apostille campaigns | Hermes for copy, Codex/Claude for code | `feature/socialforge-apostille-campaigns` | `/home/rg/empire-repo-main-socialforge-apostille` | `backend/app/services/socialforge/apostille_campaigns.py` (new), `empire-command-center/app/socialforge/**` | `test_socialforge_apostille_content.py` | low | (a) calendar, (b) templates, (c) branch, (d) implementation, (e) merge |
| VendorOps Apostille routing | Harry or Codex | `feature/vendorops-apostille-routing` | `/home/rg/empire-repo-main-vendorops-apostille` | `backend/app/routers/vendorops.py`, `backend/app/services/vendorops_alert_runner.py`, `backend/app/models/apostille_vendor_task.py` (new) | `test_vendorops_apostille_routing.py` | medium | (a) design, (b) branch, (c) implementation, (d) merge |
| Coordination (this plan) | Hermes Desktop only | `feature/empire-completion-coordination` | n/a — lives in this doc | none | none | zero | (a) writing this doc, (b) accepting this doc as source of truth |

### 5.3 Shared coordination artifact

- **Coordination doc:** `EMPIRE-COMPLETION-PLAN.md` at the repo root of `/home/rg/empire-repo-main` (this file)
- **Report naming convention:** `REPORT-<workstream>-<phase>.md` (e.g., `REPORT-drawing-sprint-2-audit.md`)
- **Quality standard naming:** `<TOPIC>-STANDARD.md` (e.g., `DRAWING-QUALITY-STANDARD.md`)
- **Daily status format:** a single section per workstream with: `branch: feature/...`, `owner: <agent>`, `status: <audit|in-progress|tests-passed|review|merged>`, `blockers: <list>`

### 5.4 Conflict prevention

- No two agents touch the same branch (enforced by the worktree-per-workstream model)
- Empire `main` is the only shared read-only surface (agents read it for context, write to their own branch)
- `.opencode/config.json` is pre-existing dirty state — **no agent touches it**
- `~/.hermes/.env` is local to this session — **no agent touches it**
- `MEMORY.md` and `USER.md` are local to this session — **no agent touches them**
- MAX backend is shared with Harry — **no agent writes to MAX files during this sprint**

### 5.5 Acceptance criteria before merge

- All tests in `backend/tests/` pass (`pytest` against the new worktree's venv)
- The relevant feature's test file exists and is committed in the workstream's branch
- The agent's report is committed alongside the code (`REPORT-<workstream>.md` in the same branch)
- Founder has reviewed the diff and the test output
- No merge conflicts with `main` (worktree should rebase against `main` before merge)
- After merge, `git log --oneline` shows the new commit with a descriptive message

### 5.6 Rollback plan

- Each workstream's branch can be force-reset to a known state if the implementation goes wrong
- Founder can `git revert <merge-sha>` to undo a merged workstream
- Pre-merge: each worktree is independent, so a bad branch can simply be deleted and re-created from `main`

### 5.7 Handoff prompts

**For Harry (OpenCode Tailscale `:8787`)** — paste into Harry's TUI:
```
Workstream: <workstream>
Repo: /home/rg/empire-repo-main
Branch: feature/<branch> (create from main, HEAD 2867978)
Do not edit main.
Do not edit .opencode/config.json.
Do not push.
Read the audit at REPORT-<workstream>-audit.md (Founder will paste) and the standard at <TOPIC>-STANDARD.md.
Implement per the audit's task list.
Run: cd backend && pytest tests/test_<workstream>.py -v
Report back with: files changed, tests passed, before/after comparison, blockers.
```

**For Codex CLI (non-interactive, in a separate terminal):**
```bash
cd /home/rg
git worktree add empire-repo-main-<workstream> -b feature/<branch> main
cd empire-repo-main-<workstream>
git config user.email "founder@empire.local"
git config user.name "Founder via Codex"
codex exec "Implement <workstream> per REPORT-<workstream>-audit.md. Do not edit main. Do not edit .opencode/config.json. Do not push. ..."
```

**For Claude Code CLI (non-interactive, in a separate terminal):**
```bash
cd /home/rg/empire-repo-main-<workstream>
claude -p "Implement <workstream> per REPORT-<workstream>-audit.md. Do not edit main. Do not edit .opencode/config.json. Do not push. ..."
```

**For `delegate_task` sub-agents in this session** (read-only audit phases):
```python
delegate_task(
  goal="<audit goal>. Do NOT write any code or create any files. Return a structured summary in your final response.",
  context="Repo at /home/rg/empire-repo-main. Read <file list>. <audit questions>. CONSTRAINTS: READ-ONLY, no writes, no branches, no pytest, no .opencode/config.json edits.",
  toolsets=["file", "terminal"],
  role="leaf"
)
```

---

## 6. Fastest Path to Revenue (Ranked)

1. **Apostille MVP v1 landing page + intake form** — 1 new front-end page, calls existing `/api/v1/apostapp/*` routes. Days. No backend changes. Founder takes the order, generates a quote, emails a Zelle/Venmo link. **Real revenue.**
2. **Apostille + VendorOps integration** — route each order to a vendor. 1–2 weeks. Unblocks apostille at scale.
3. **SocialForge Apostille campaign content** — 30 days of bilingual content with CTAs to the new landing page. Days. Drives leads into the funnel.
4. **Drawing Quality Sprint 2** — bench → banquette → window. 2–3 weeks. Revenue-adjacent (Empire Workroom is a project pipeline, not a direct sales channel, but drawing quality is the demo for client work).
5. **VendorOps multi-vendor data model** — extend vendor primitives. 1–2 weeks. Unblocks #2 and future VendorOps modules.

---

## 7. Approval Requests

| # | Action | Approve? |
|---|---|---|
| 1 | Create worktrees (`/home/rg/empire-repo-main-{drawing-sprint-2,apostille-completion,socialforge-apostille,vendorops-apostille}`) | ☐ |
| 2 | Create feature branches (`feature/drawing-quality-sprint-2`, `feature/apostille-completion`, `feature/socialforge-apostille-campaigns`, `feature/vendorops-apostille-routing`) | ☐ |
| 3 | Run Phase 1A audit (already done in this batch) | ✓ |
| 4 | Run Phase 2A audit (already done in this batch) | ✓ |
| 5 | Run Phase 3A audit (already done in this batch) | ✓ |
| 6 | Run Phase 4A audit/design (already done in this batch) | ☐ |
| 7 | Write this coordination plan to `EMPIRE-COMPLETION-PLAN.md` | ☐ |
| 8 | Write `REPORT-drawing-sprint-2-audit.md` and `DRAWING-QUALITY-STANDARD.md` (this batch) | ☐ |
| 9 | Write `REPORT-apostille-readiness.md` (this batch) | ☐ |
| 10 | Write `REPORT-socialforge-apostille-gap.md` (this batch) | ☐ |
| 11 | Write `REPORT-vendorops-apostille-design.md` (this batch) | ☐ |
| 12 | Hand off Phase 1C implementation to Harry (after Founder approves audit + standard) | ☐ |
| 13 | Hand off Phase 2C implementation to Codex/Claude (after Founder approves readiness) | ☐ |
| 14 | Enable `HERMES_HTML_CONTEXT=1` for a real run that ingests the four audit reports | ☐ |
| 15 | Run `pytest` against any of the worktrees | ☐ |
| 16 | Restart MAX backend or any service | ☐ |
| 17 | Push any branch to any remote | ☐ |
| 18 | Merge any branch into `main` | ☐ |
| 19 | Edit `~/.hermes/.env` again (kill switch stays on; HTML context stays off) | ☐ |
| 20 | Edit `MEMORY.md` or `USER.md` | ☐ |

---

## 8. Do Not Proceed List

Without explicit Founder approval in a future turn, I will **not**:

- Create worktrees or branches
- Write any `REPORT-*.md` or `DRAWING-QUALITY-STANDARD.md` to disk (except in this approved batch)
- Run `delegate_task` against Empire-repo sub-agents for implementation (read-only audit only, in this batch)
- Modify Empire repo files in any way (read-only inspection is OK)
- Modify `MEMORY.md`, `USER.md`, `~/.hermes/.env`, `.opencode/config.json`
- Touch MAX backend code, routes, or runtime
- Restart any service (gateway, desktop, MAX, opencode-remote)
- Enable `HERMES_HTML_CONTEXT` for any real turn
- Disable the `HERMES_BACKGROUND_REVIEW_DISABLED=1` kill switch
- Send any customer message
- Create any invoice or payment record
- Make any destructive database change
- Push any branch to any remote
- Merge any branch into `main`

The `HERMES_BACKGROUND_REVIEW_DISABLED=1` flag stays **on** for the duration of this multi-agent sprint.

---

## 9. Status of This Document

- **Written:** 2026-06-08
- **Committed:** No (Founder approval required for commit)
- **Pushed:** No
- **Next action:** Awaiting Founder review of this plan and the 5 audit report files written in this batch.
