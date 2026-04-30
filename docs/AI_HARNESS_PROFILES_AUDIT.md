# Empire AI Harness Profiles — Architecture Audit

**Date:** 2026-04-30
**Branch:** feature/v10.0-test-lane
**Starting commit:** f7c8e4a
**Author:** Claude Code / Empire v10 session

---

## 1. What Are Empire AI Harness Profiles

Empire AI Harness Profiles are **model/provider-specific routing metadata bundles** that replace ad-hoc provider selection with typed, policy-aware routing decisions. Each profile captures:

- Which provider/model should handle which task type
- What prompt style, system instructions, and tool policy apply
- Approval requirements and file access constraints
- Fallback chain, emergency behavior, and telemetry settings

The goal is to make routing **explainable**, **auditable**, and **future-proof** as Empire adds more AI providers (xAI, Claude, Gemini, OpenClaw, Ollama, MiniMax, etc.).

---

## 2. Current AI Routing State

### 2.1 Where MAX Chooses Providers/Models

**Primary file:** `backend/app/services/max/ai_router.py` (class `AIRouter`)

**Route selection flow:**

```
1. Incoming message → classify_complexity(message)
   - SIMPLE: greetings only → Gemini Flash
   - MODERATE: default → xAI Grok → Groq → Claude Sonnet → Gemini
   - COMPLEX: → Claude Sonnet → Grok → GPT-4o → Groq
   - CRITICAL: code/file → Claude Opus → Claude Sonnet

2. Conversation floor enforcement via _conversation_floors dict
   (never downgrades within a conversation)

3. Per-desk model override via DESK_MODEL_ROUTING dict
   - codeforge → Claude Opus
   - analytics → Claude Sonnet
   - quality → Claude Sonnet
   - innovation → Claude Sonnet
   - forge/minimaxi/it/marketing/support → MiniMax
   - sales → Groq
   - costtracker → OpenAI Nano
   (All other desks fall through to complexity routing)
```

**Legacy fallback chain** (for desk/explicit model routes):
```
GroK → Claude → Groq → OpenClaw → Ollama
```

**Key providers:**
| Provider | Key env var | Model |
|---|---|---|
| xAI Grok | XAI_API_KEY | grok-4-fast-non-reasoning |
| Anthropic Claude | ANTHROPIC_API_KEY | claude-sonnet-4-6 / claude-opus-4-6 |
| Groq | GROQ_API_KEY | llama-3.3-70b |
| Google Gemini | GOOGLE_GEMINI_API_KEY | gemini-2.5-flash |
| OpenAI | OPENAI_API_KEY | gpt-4.1-nano / gpt-4o-mini / gpt-4o |
| MiniMax | MINIMAX_API_KEY | MiniMax-M1 |
| OpenClaw | — | openclaw local |
| Ollama | — | ollama-llama |

### 2.2 Fallback Routing

Fallback is built into `_build_complexity_chain()` and the legacy provider chain. When a provider fails, the next in chain is tried automatically. No explicit fallback profile IDs — fallback is implicit in provider ordering.

### 2.3 OpenClaw Task Dispatch

**Files:**
- `backend/app/routers/openclaw_bridge.py` — dispatches tasks to OpenClaw via `/api/v1/openclaw/dispatch`
- `backend/app/routers/openclaw_tasks.py` — persistent task queue with status tracking
- `backend/app/services/openclaw_worker.py` — worker loop polling task queue every 30s

OpenClaw dispatch flow:
```
MAX desk task → POST /api/v1/openclaw/dispatch → task_queue[] → OpenClaw Worker → OpenClaw port 7878
```

No harness profile metadata is attached to OpenClaw tasks currently. TaskRequest only has: task_id, title, description, priority, desk, skills_needed.

### 2.4 OpenCode Representation

OpenCode is invoked via `_openclaw_chat()` in ai_router.py (line 644). Not a separate profile — it routes through the OpenClaw agent. There is a `opencode.json` at repo root but no active OpenCode router in the backend.

### 2.5 AI Desks

Defined in `DeskSelector.tsx` (17 desks):
- codedesk, marketdesk, marketingdesk, supportdesk, salesdesk, finacedesk, clientsdesk, contractorsdesk, itdesk, websitedesk, legaldesk, labdesk, innovationdesk, intakedesk, analyticsdesk, qualitydesk, qadesk

Per-desk routing is via `DESK_MODEL_ROUTING` in `ai_router.py`.

### 2.6 Provider Health/Status Tracking

Provider availability is tracked via API key presence (bool flags). No live health checks for AI providers beyond connection attempts during routing. The `EmpireTopBar` shows backend (8000) and frontend (3010) health only.

### 2.7 Task Type in Routing

Task type is **implicit** via complexity classification (`TaskComplexity` enum: SIMPLE/MODERATE/COMPLEX/CRITICAL). There is no explicit `task_type` parameter passed into routing decisions beyond message content analysis. Complexity classification uses keyword matching + message length — no AI call.

### 2.8 Hardcoded Model Selection

Primary model is hardcoded based on available keys (priority: xAI > Claude > Groq > Ollama). Model variants (Opus/Sonnet) are hardcoded per complexity tier or desk. The per-desk DESK_MODEL_ROUTING dict is the closest thing to a profile, but it only maps desk → model, not policies or task types.

### 2.9 Emergency Grok/xAI Override

No explicit emergency override exists. If xAI is the primary and fails, it falls through to Claude → Groq → etc. The `_build_complexity_chain` is the implicit fallback chain. No `emergency_override` flag.

### 2.10 Frontend AI Model Control

`EmpireTopBar.tsx` shows status pills for Backend (8000) and v10 Frontend (3010) only. No AI Model Control UI is currently implemented. `MAXDeskScreen.tsx` shows no active model indicator in the chat UI.

### 2.11 MAX Response Metadata

The `AIResponse` dataclass has: `content`, `model_used`, `fallback_used`, `function_calls`. No task_type, harness_profile_id, routing_reason, or emergency_override fields.

### 2.12 Cost/Success/Failure Logging

`token_tracker.log_chat()` logs all AI calls with model, input, output, feature, business, source, tenant_id. This is the telemetry layer. It logs to the costs system.

### 2.13 MAX Tools Backend Implementation

From `ChatInterface.tsx` TOOL_REGISTRY, all 20 tools are `implemented: false`. No MAX tool currently executes a real backend API call. The `handleToolClick` gate prevents execution.

### 2.14 OpenClaw Branch Targeting

OpenClaw currently uses its own checked-out branch. There is no per-task or per-profile branch targeting in the bridge. The `openclaw_gate` tracks allow/defer/block state but not branch routing.

---

## 3. Routing Flow Diagram (Text Form)

```
User Message
    │
    ▼
classify_complexity()  ── keyword / length analysis, no AI call
    │
    ├── SIMPLE ────────────────────────────────────────────► Gemini Flash
    ├── MODERATE ──► xAI Grok ─► Groq ─► Claude Sonnet ────► Gemini (last resort)
    ├── COMPLEX ──► Claude Sonnet ─► Grok ─► GPT-4o ─────► Groq
    └── CRITICAL ──► Claude Opus ─► Claude Sonnet ─────────► STOP
         │
         ▼ (desk override)
DESK_MODEL_ROUTING[desk] if desk specified
         │
         ▼ (legacy fallback chain)
GROK → CLAUDE → GROQ → OPENCLAW → OLLAMA (if no desk/explicit model)
```

**Stream path:** `chat_stream()` follows the same complexity chain but yields chunks via SSE.

---

## 4. Gaps

| # | Gap | Severity |
|---|---|---|
| G1 | No typed task_type enum — routing is implicit via keyword matching | High |
| G2 | No harness profiles — only provider chains, no policy/approval/tool metadata | High |
| G3 | No emergency Grok override flag — falls through chain instead of jumping to emergency profile | High |
| G4 | No routing explanation output — MAX can't explain why a provider was chosen | Medium |
| G5 | No per-profile system instruction blocks — all providers share same system prompt | Medium |
| G6 | OpenClaw task dispatch carries no harness profile metadata | Medium |
| G7 | Frontend has no AI Model Control UI or active model indicator | Medium |
| G8 | Provider health is not tracked live — only key presence | Low |
| G9 | No budget_mode flag — can't prefer free/local when budget-constrained | Low |
| G10 | No JSONL routing telemetry log — cost log exists but routing decisions not logged separately | Low |
| G11 | OpenClaw branch targeting is not enforced — only process-based protection | Medium |

---

## 5. Safest Implementation Plan

### Phase 1 (This Pass) — Registry + Selection + Safe Endpoints + Telemetry

1. **Create typed task type constants** (no enum, plain strings for compatibility)
2. **Create `backend/app/services/ai_harness_profiles.py`** with starter profiles and profile registry
3. **Create `backend/app/routers/ai_harness.py`** with read-only/selection endpoints
4. **Add lightweight JSONL routing telemetry** (reuse existing logging paths)
5. **Wire router into `backend/app/main.py`**
6. **Add tests** for profile selection, emergency override, fallback
7. **Add docs** `docs/AI_HARNESS_PROFILES.md` and update this audit
8. **Frontend: read-only status panel only** if AI Model Control UI already exists and is easy to extend

### Phase 2 — Live MAX Integration

1. Attach routing metadata to AIResponse dataclass
2. Pass task_type through chat flow
3. Integrate `select_profile()` into `AIRouter.chat()` and `chat_stream()`
4. Add profile metadata to OpenClaw TaskRequest
5. Expose active model/profile in frontend MAX UI

### Phase 3 — OpenClaw/OpenCode Integration

1. Add harness_profile_id + routing_reason to OpenClaw task dispatch metadata
2. Add opencode_repo_execution_profile policy to OpenCode invocation
3. Enforce per-branch OpenClaw targeting

---

## 6. What Will Be Changed in This Pass

- New file: `backend/app/services/ai_harness_profiles.py`
- New file: `backend/app/routers/ai_harness.py`
- New file: `backend/data/logs/ai_harness_routing.jsonl` (if telemetry added)
- Wire `ai_harness.py` into `main.py`
- New tests in `backend/tests/`
- New doc: `docs/AI_HARNESS_PROFILES.md`
- Update `docs/AI_HARNESS_PROFILES_AUDIT.md`
- Update `.claude-progress.md`

**NO changes to:**
- `ai_router.py` (live routing, no rewrite)
- `openclaw_bridge.py` / `openclaw_tasks.py` (no metadata additions this pass)
- `ChatInterface.tsx` (keep current tool registry as-is)
- `MAXDeskScreen.tsx` (keep hardened layout)
- Pricing/quote/payment logic
- Stable/production code

---

## 7. What Will NOT Be Changed in This Pass

| Item | Reason |
|---|---|
| `AIRouter.chat()` / `chat_stream()` | Too risky — requires live testing of all providers |
| `DESK_MODEL_ROUTING` | Works, no need to replace with profiles yet |
| OpenClaw task metadata | No safe DB migration in this pass |
| Any MAX tool enabled | All currently `implemented: false` — backend not verified |
| OpenClaw branch behavior | Not yet supported |
| Pricing/quote logic | Explicitly out of scope |
| Frontend benchmark buttons | Fake UI is prohibited |
| Stable/production | Explicitly protected |
