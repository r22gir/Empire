# Empire AI Harness Profiles

**Date:** 2026-04-30
**Branch:** feature/v10.0-test-lane
**Status:** Phase 2A — Metadata-only MAX integration (live routing NOT changed)

---

## What Are Empire AI Harness Profiles

Empire AI Harness Profiles are **model/provider-specific routing metadata bundles** that give MAX and OpenClaw a typed, policy-aware way to select AI providers instead of using ad-hoc provider chains.

Each profile captures:
- Which provider/model should handle which task types
- Prompt style, system instructions, and tool policy
- Approval requirements and file access constraints
- Fallback chain, emergency behavior, and telemetry settings
- Cost/speed/quality/reliability tiers

The goal is to make routing **explainable**, **auditable**, and **future-proof** as Empire adds more AI providers.

---

## Why Empire Needs Them

The current routing in `ai_router.py` uses complexity-based keyword matching + hardcoded provider chains. This works but has gaps:

1. **No explicit task type** — routing is implicit via keyword analysis, not explicit task intent
2. **No routing explanation** — MAX can't explain why a provider was chosen
3. **No policy metadata** — tool/file/approval policy is the same for all providers
4. **No emergency override flag** — falls through chain instead of jumping to emergency profile
5. **No budget mode** — can't prefer free/local when cost-constrained
6. **No per-profile system instructions** — all providers share the same system prompt
7. **OpenClaw task dispatch carries no metadata** — no harness profile info attached

Harness profiles solve these by making routing a first-class, typed, auditable concern.

---

## How Profiles Differ from Generic Model Routing

Generic routing picks a model based on availability or cost. Harness profiles add:

| Concern | Generic Routing | Harness Profiles |
|---|---|---|
| Task type | Implicit / keyword | Explicit typed task type |
| Provider preference | Single primary | Per-task priority order |
| Tool policy | Global | Per-profile (strict/default/permissive/disabled) |
| File access | Global | Per-profile (read_only/read_write/none) |
| Approval required | Global | Per-profile (none/founder/review) |
| System instructions | Shared | Profile-specific blocks |
| Fallback chain | Implicit provider order | Explicit profile IDs |
| Emergency behavior | Fail-through chain | Dedicated emergency profile |
| Routing explanation | None | Full RoutingExplanation object |
| Telemetry | Cost-only | Routing decisions logged |

---

## Profile Selection Rules

1. **Emergency override:** If `emergency_override=True`, select `grok_emergency_repair_profile` (provider=xai) for any task, unless disabled.

2. **Explicit provider/model:** If `requested_provider` or `requested_model` is provided, select the highest-priority enabled profile matching that provider AND supporting the task type. Emergency-only profiles are excluded.

3. **Default for task type:** If no explicit request, use the highest-priority enabled profile where `task_type in default_for_tasks`.

4. **Fallback to MAX default:** If no default for task type, fall back to `max_default_chat_profile`.

5. **Final Ollama fallback:** If no profiles at all, use `ollama_budget_fallback_profile`.

Disabled profiles are never selected.

---

## Starter Profiles

| Profile ID | Provider | Model | Best For | Key Policy |
|---|---|---|---|---|
| `claude_repo_audit_profile` | anthropic | claude-sonnet-4-6 | Architecture review, repo audit, docs | Read-only, founder approval, verify tests |
| `openai_codex_patch_profile` | openai | gpt-4o | Code edits, patching, tests | Read-write, founder approval, required tests |
| `grok_emergency_repair_profile` | xai | grok-4-fast-non-reasoning | Emergency fallback, low-credit mode | Read-only, founder approval, conservative retry |
| `gemini_research_visual_profile` | google | gemini-2.5-flash | Research, multimodal/visual analysis | Read-only, no approval needed |
| `qwen_local_coding_profile` | ollama/local | qwen | Local budget coding, agentic tests | Read-write, founder approval, tests required |
| `minimax_visual_quote_profile` | minimax | MiniMax-M1 | Visual quote, image-assisted workflows | Read-only, founder approval for prices |
| `ollama_budget_fallback_profile` | ollama/local | llama3.1 | Free local fallback, summarization | Read-only, no approval, no tool use |
| `opencode_repo_execution_profile` | openclaw/local | openclaw | Repo execution, terminal-based tasks | Read-write, founder approval, tests required |
| `max_default_chat_profile` | xai | grok-4-fast-non-reasoning | General MAX chat, support, marketing | Read-only, no approval |
| `claude_opus_critical_profile` | anthropic | claude-opus-4-6 | Critical code quality, maximum reasoning | Read-write, founder approval, required tests |

---

## Task Types

```
code_patch, repo_audit, documentation, ui_ux_review,
visual_analysis, quote_generation, pricing_review,
image_to_quote, customer_support, finance_analysis,
marketing, emergency_repair, model_benchmark,
max_chat, openclaw_task, opencode_task,
transcription, voice_tts, vision,
drawing_studio, recovery_archive_analysis,
summarization, research
```

---

## Emergency Grok Override Behavior

When `emergency_override=True`:
- `grok_emergency_repair_profile` is selected regardless of task type
- `emergency_override=True` is set in the RoutingExplanation
- This bypasses normal priority and explicit provider requests
- Used when MAX detects a low-credit situation, urgent repair need, or health check failure

---

## Fallback Behavior

Each profile has an optional `fallback_profile_ids` list. When selection fails (profile unavailable, disabled, or no match), the registry:
1. Tries the primary selection rules
2. If no match, falls through to `max_default_chat_profile`
3. If that fails, falls back to `ollama_budget_fallback_profile`

Fallback chains are exposed via `GET /api/v1/ai-harness/status`.

---

## Telemetry / Logging

Routing decisions are logged to `backend/data/logs/ai_harness_routing.jsonl`.

Each entry contains (sanitized — never logs API keys, secrets, or full prompts):
- `timestamp`
- `channel`
- `task_type`
- `selected_provider`
- `selected_model`
- `selected_harness_profile`
- `fallback_used`
- `fallback_reason`
- `emergency_override`
- `success` / `error`

Log is append-only. Access via `GET /api/v1/ai-harness/telemetry`.

---

## Current Integration Status

### Phase 2A — Metadata-Only Integration

**What is LIVE in Phase 2A:**
- Profile registry + selection service: **active**
- All 6 endpoints including new `routing-status`: **active**
- Harness metadata attached to MAX `/chat` and `/chat/stream` responses: **active**
  - Metadata fields: `harness_profile_id`, `harness_provider`, `harness_model`, `harness_task_type`, `harness_reason`, `harness_fallback_used`, `harness_emergency_override`, `harness_policy_summary`
  - Attached to `metadata.harness` in `ChatResponse` and SSE `done` events
- `get_last_routing_decision()`: **active** — tracks last profile selection module-level
- Telemetry path fix: **active** — writes to `~/empire-repo-v10/backend/data/logs` when running from v10 worktree
- Emergency override available: **yes** (profile exists and is enabled)
- Emergency override NOT auto-triggered: **correct** (Phase 2B)

**What is NOT live (unchanged):**
- `ai_router.py` provider selection: **UNCHANGED** — no live routing change
- `AIRouter.chat()` / `chat_stream()`: still uses existing complexity-based chains
- `AIResponse` dataclass: harness metadata NOT in response dataclass itself
- OpenClaw task dispatch: no harness metadata attached yet
- Frontend read-only panel: **not implemented** (Phase 2B)
- MAX tools: all remain `implemented: false`

### Phase 2B Candidates (Next)

1. **Live MAX provider routing** — Wire harness profile into `AIRouter.chat()` model selection (requires live provider testing)
2. **MAX explanation UI** — Show active harness profile + reason in MAX chat interface
3. **OpenClaw harness metadata** — Attach to `TaskRequest` if safe metadata field exists
4. **Frontend read-only panel** — Profile status, last routing, registry counts

---

## How to Add a New Provider/Profile

1. Add task type constants to `ai_harness_profiles.py` if needed
2. Create a new `AIHarnessProfile` instance with all required fields
3. Add it to `_default_profiles()` list
4. Register in the `AIHarnessProfileRegistry.__init__()` (automatic via list iteration)
5. Update tests and docs

Example:
```python
AIHarnessProfile(
    id="my_new_profile",
    display_name="My AI — Task Focus",
    provider="my_provider",
    model="my-model",
    task_types=[TASK_TYPE_CODE_PATCH],
    description="Best for...",
    default_for_tasks=[TASK_TYPE_CODE_PATCH],
    priority=30,
    recommended_for=[TASK_TYPE_CODE_PATCH],
    prompt_style="technical",
    system_instructions="You are a...",
    tool_policy="default",
    file_access_policy="read_write",
    approval_policy="founder",
    testing_policy="required",
    risk_level="medium",
)
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/ai-harness/profiles` | List all profiles (enabled_only=true by default) |
| GET | `/api/v1/ai-harness/profiles/{profile_id}` | Get one profile |
| GET | `/api/v1/ai-harness/recommend?task_type=...` | Get recommended profiles for task type |
| POST | `/api/v1/ai-harness/select` | Select best profile for task |
| GET | `/api/v1/ai-harness/status` | Registry status, counts, chains, warning |
| GET | `/api/v1/ai-harness/routing-status` | Last routing decision + Phase 2A metadata-only status |
| GET | `/api/v1/ai-harness/telemetry` | Recent routing decisions from JSONL log |
| GET | `/api/v1/ai-harness/status` | Registry status, defaults, chains, warnings |
| GET | `/api/v1/ai-harness/telemetry` | Recent routing decisions (sanitized) |

---

## Limitations and Future Work

- **Live routing not integrated** — Phase 2 requires wiring into `AIRouter.chat()`
- **Per-branch OpenClaw targeting** — Not yet enforced; opencode profile notes this
- **Provider availability not tracked live** — Only key presence check
- **Frontend UI** — Read-only panel not yet implemented
- **Benchmark** — No benchmarking in this pass; no fake benchmark UI
- **Multi-turn conversation routing** — Profiles select per-turn, not per-conversation yet
- **Per-tenant profiles** — All profiles are global (Phase 2+)

---

## Files

| File | Purpose |
|---|---|
| `backend/app/services/ai_harness_profiles.py` | Profile registry, selection logic, telemetry |
| `backend/app/routers/ai_harness.py` | REST endpoints |
| `backend/tests/test_ai_harness_profiles.py` | Unit tests (26 tests) |
| `docs/AI_HARNESS_PROFILES_AUDIT.md` | Pre-implementation audit |
| `docs/AI_HARNESS_PROFILES.md` | This document |
