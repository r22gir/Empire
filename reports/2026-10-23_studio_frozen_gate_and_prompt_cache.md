# Studio frozen gate + desk prompt cache (2026-10-23)

Max (Studio). Branch `cursor/studio-frozen-gate-cache-c000` off `dell/studio-batch-1014`.
Mock data only. Nothing sent.

## 1. Frozen suite (pytest counts)

```
cd backend && PYTHONPATH=backend python3 -m pytest -q --tb=line tests/test_studio_frozen_gate.py
12 passed in 0.62s
```

Coverage:

| Area | What is frozen |
|---|---|
| Quotes | request phrase + dim; exact mock totals; fractions never decimals; wood/foam vs fabric cuts; draft `sent=False` |
| Drawings | spaced fractions only; `WOOD CUT` / `FOAM CUT` / `FABRIC CUT` labeled separately; fabric codes, not Kravet/Spradling/Fabricut |
| Invoices | mock line subtotal; internal allocation math hidden; 50% deposit + balance; no send field |

Related regressions (same session): `test_drawing_revision_nightlab.py::test_black_and_cognac_resolve_to_workroom_codes`, two QuoteIQ cut/fraction tests, `test_studio_money.py` → **7 passed**.

Gate + cache + improvement-loop tests: **31 passed**.

## 2. Gate demo (reject bad / keep good)

`python3 backend/scripts/demo_studio_frozen_gate.py`

Deliberately bad mock change (`STUDIO_FROZEN_MUTATION=bad`):

```
STUDIO_FROZEN_GATE: NO  passes=0/2  frozen suite failed on first pass — change rejected
kept=false  reverted=true  outbound=false
```

Good / clean change:

```
STUDIO_FROZEN_GATE: YES  passes=2/2  frozen suite green twice — change may be kept
kept=true  outbound=false
```

`DEMO_RESULT PASS`

Wired as a yes/no keep decision in:

- Night Lab `backend/scripts/nightly_improvement_tests.py`
- Atlas `improvement_worker.run_atlas_plan` (change not kept if NO)
- `self_heal._run_canary_tests`
- `maintenance_manager._run_canary_tests`

A change is kept only after **two** green passes.

## 3. Prompt-cache measurements (real chat-path assembler)

`assemble_desk_chat_messages` is the same system-first / user-last shape `ai_router.chat` sends. Two mock turns with different dates, task counts, and user messages. No provider HTTP.

| Desk | Pin | Before LCP (legacy) | After LCP (cache) | Gain | Cache-hit before | Cache-hit after |
|---|---|---|---|---|---|---|
| forge | minimax / minimax | 151 chars (10.21%) | 1524 chars (93.67%) | +1373 | no | **yes** |
| codeforge | minimax / minimax | 159 chars (75.36%) | 251 chars (70.11%) | +92 | no | **yes** |
| finance | none (caching does not apply) | 155 chars (10.06%) | 1527 chars (93.57%) | +1372 | no | no |

Cache-hit here means: the longest common prefix of the two system prompts includes the fixed-end marker (persona, rules, pin, tools). Date, live counts, and the user message stay after that marker.

Routing is unchanged. Pins match existing `DESK_MODEL_ROUTING`.

## 4. Not done

No merge. No deploy. No outbound send. `.env`, `client_aliases.json`, and `business.json` were not committed.
