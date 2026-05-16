# MAX Operations Capability Registry

Status: v10 test lane only.

## Purpose

The MAX operations capability registry lets the founder speak naturally while MAX maps the request into a safe, approved operation. It is not a rigid command menu. It is a controlled registry of what MAX is allowed to execute, inspect, recommend, or decline in the v10 MAX/Hermes/OpenClaw control plane.

The registry keeps explanatory module questions separate from operational requests. For example, "What is OpenClaw?" remains module knowledge, while "Inspect task 8" is a read-only OpenClaw task inspection capability.

## Current Lane

- Worktree: `/home/rg/empire-repo-v10`
- Branch: `feature/v10.0-test-lane`
- Backend: `8010`
- Frontend: `3010`
- Public test host: `test-studio.empirebox.store`
- Production/stable lanes: out of scope for this v10 feature

## Routing Priority

1. Runtime truth hard overrides for live/stale/service/status checks.
2. Operations capability registry:
   - create with `task_ref`
   - disposition/cancel
   - inspect
   - list
   - Level 1 sprint
   - recommend
   - preflight
3. Hermes artifact memory.
4. Empire module knowledge.
5. General model response.

OpenClaw mentions do not automatically mean module knowledge. If the prompt includes task, task_id, queue, inspect, cancel, create, recommend, duplicate, status, or Level 1 delegation intent, MAX routes through the operations registry first.

## Capability Structure

Each capability defines:

- `capability_id`
- `route_name` / `model_used`
- description and natural language examples
- intent actions and objects
- required and optional entities
- read-only or mutating behavior
- founder approval requirement
- `task_ref` requirement
- allowed and forbidden lanes
- safety gates
- handler name
- fallback message
- report fields

The public status endpoint exposes a compact registry summary through `/api/v1/max/status`. The full registry is available through `/api/v1/max/capabilities`.

## Current Capabilities

- `runtime_lane_verify`: read-only v10 preflight and git/Hermes status.
- `level1_delegation_sprint`: read-only Level 1 sprint planning, exactly three bounded recommendations, no task creation.
- `supervised_repair_recommend_task`: read-only single-task recommendation with Hermes context and a one-time `task_ref`.
- `supervised_openclaw_task_create`: mutating creation of exactly one OpenClaw task from an approved, unconsumed `task_ref`.
- `openclaw_task_inspect`: read-only task inspection by `task_id`.
- `openclaw_task_disposition`: mutating disposition for a single safe v10 task, such as cancelling a duplicate, with explicit founder approval.
- `openclaw_task_list`: read-only queue/recent task listing.
- `hermes_artifact_search`: approved/current Hermes artifact memory retrieval as supporting context.
- `module_knowledge_lookup`: documentation/explanation only.

## Natural Language Parsing

The parser extracts:

- action: verify, start_sprint, recommend, create, inspect, cancel, list, explain, search, approve, dispose, status
- object: runtime lane, OpenClaw task, Hermes artifact, module, queue, sprint
- entities: task_id, task_ref, module, lane, branch, approval phrase, status filter
- modifiers: do not create, read-only, no stable/main, v10 only, approved/current, duplicate, bounded, preflight only, exactly one, exactly three, cancelled

Examples:

- "Run v10 preflight." -> `supervised-v10-repair-preflight`
- "Start Level 1 supervised v10 delegation." -> `supervised-v10-level1-delegation-sprint`
- "Find something small OpenClaw can fix next." -> `supervised-v10-repair-recommend-task`
- "Inspect task 8." -> `supervised-v10-openclaw-task-inspect`
- "Show OpenClaw queue." -> `supervised-v10-openclaw-task-list`
- "Cancel task 8 as duplicate." -> disposition route, blocked until founder approval.
- "Approved task_ref=<TOKEN>. Create exactly one bounded OpenClaw task." -> task creation route.
- "What is OpenClaw?" -> `empire-module-knowledge`

## Approval And Task Ref Rules

Mutating capabilities do not run from ordinary intent alone.

Task creation requires the exact single-task approval pattern:

```text
Approved task_ref=<TOKEN>. Create exactly one bounded OpenClaw task.
```

The `task_ref` must be known, unexpired, unconsumed, lane-bound, branch-bound, and safety-gate-bound. The task payload comes from the stored recommendation, not from a fresh free-form prompt.

Disposition requires explicit founder approval and a single task id. Without approval, MAX reports `failed_gate=founder_approval` and does not mutate task state.

Legacy OpenClaw rows may not contain explicit lane metadata because the task table has no lane columns and older queued validation tasks predate the structured payload contract. MAX may infer `v10-test` only for legacy duplicate task_ref-handshake validation tasks with strong evidence: supervised v10 repair title/scope, codedesk source context, queued status, current v10 runtime, and commit `2140447` reachable from the v10 lane. Arbitrary unknown-lane rows remain blocked with `failed_gate=lane`.

## Safe Fallback

If MAX recognizes an operational request but no approved capability exists, it returns a safe capability-missing response:

```text
I understand this as: <intent>.
I do not yet have an approved execution capability for that action.
Available safe actions are: <list>.
I can recommend a bounded v10 task to add this capability.
```

This prevents unknown operational prompts such as "Pause all OpenClaw jobs" from falling into module documentation or model speculation.

## Level 1 Delegation

Level 1 delegation remains read-only. It verifies the v10 lane, checks git freshness and Hermes artifact status, inspects the queue where supported, confirms task status such as task_id 8, searches approved/current Hermes context, and recommends exactly three bounded v10 tasks.

Batch `task_ref` creation is not supported yet. The current task_ref handshake supports single-task recommendation and creation only.

## Safety Boundaries

- Runtime/repo/database truth outranks Hermes artifact memory.
- Hermes artifact memory is supporting context only.
- Read-only routes create no tasks and mutate no tasks.
- Mutating routes require explicit approval and safety gates.
- The v10 registry must not touch main/stable worktrees or services.
- Production promotion is forbidden from this flow.

## Verification

Targeted tests:

```bash
pytest backend/tests/test_max_operations_capability_registry.py -q
pytest backend/tests/test_max_supervised_repair_routing.py -q
pytest backend/tests/test_max_truth_guardrails.py -q
pytest backend/tests/test_max_hermes_artifact_retrieval.py -q
pytest backend/tests/test_runtime_git_lane_mapping.py -q
```

Runtime checks:

```bash
curl -s http://localhost:8010/api/v1/max/status | python3 -m json.tool
curl -s http://localhost:8010/api/v1/max/capabilities | python3 -m json.tool
curl -s http://localhost:8010/api/v1/hermes/artifacts/status | python3 -m json.tool
```

## Next Steps

1. Expand the read-only OpenClaw task list/filter capability.
2. Add deterministic `task_kind` and `task_signature_hash`.
3. Ingest OpenClaw final reports into Hermes artifacts.
4. Add a Level 1 sprint board.
5. Add batch task_ref support for Level 2 delegation.
