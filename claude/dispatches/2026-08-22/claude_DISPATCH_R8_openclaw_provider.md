# DISPATCH R8 — OPENCLAW PROVIDER SELECTOR
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Predecessor:** `R7_CAMPAIGN_ENGINE_2026-08-22.md` Part 1 (the autopsy)
**Founder rulings this implements:**
- Not MiniMax-exclusive. OpenClaw gets **provider selection like MAX has** —
  a dropdown, a chain, switchable.
- Ollama stays available but **off by default** — it was paused because
  RecoveryForge tasks consumed all RAM on a 31 GB box. Re-enabling it without a
  memory ceiling recreates the failure.
- Shared credentials, **independent model preference**. Background work should
  be able to run cheap while MAX chat runs premium.

---

## WHAT THE AUTOPSY ESTABLISHED

**OpenClaw is not broken. It is disconnected.**

- `Ollama connection failed: All connection attempts failed` — **1,412 of 1,447
  errors (97.6%)**. One root cause. Every other error shape is single digits.
- **2026-06-25: 100% failure from that day forward.** Ollama went offline and
  never returned.
- 5,822 of the 7,390 tasks are `test-suite` submissions from a Sept-2025
  harness — **4,921 still `queued`, never picked up.** Real founder work is
  ~1,000 tasks. The "80% failure rate" was mostly a harness talking to itself.
- Last successful task: **2026-04-28.**
- ~60,000 MiniMax tokens burned on tasks that failed *after* the model call.

**Therefore:** no rebuild, no Hermes migration required. OpenClaw needs a
reachable model provider and a gate that does not hard-require Ollama.

---

## HARD RULES

1. **🛑 STOP-GATED.** Part 1 is read-only. Nothing is written until you report
   and I rule.
2. **Do not start Ollama.** It was paused for a reason — RAM exhaustion on a
   31 GB machine. Re-enabling is a separate decision with a memory ceiling.
3. **Do not submit tasks** to OpenClaw until Part 3 explicitly says so, and
   then exactly one.
4. **Do not let the worker drain the queue.** 4,921 queued test-suite tasks
   would execute the moment a model becomes reachable. Part 2 handles this
   **before** Part 3 makes a provider reachable. **Order is not negotiable.**
5. Never print API keys. PRESENT/ABSENT and provider names only.
6. Repo `~/empire-repo-main`, branch `feature/drawing-standard`. Commit each
   part, push.
7. `sqlite3` CLI not installed — use `~/empire-repo-main/backend/venv/bin/python`.
8. Do not restart `empire-backend.service` without saying so first. The
   R1 pins (`MAX_MEMORY_PATH`, `EMPIRE_BRAIN_DIR`) must survive any restart —
   re-prove from `/proc/<pid>/environ` after.

---

## PART 1 — HOW DOES OPENCLAW CALL A MODEL TODAY? (READ ONLY)

### 1.1 — The call site
```
find ~/empire-repo-main/openclaw -name '*.py' | head -20
grep -rn 'ollama\|11434\|OLLAMA' ~/empire-repo-main/openclaw --include='*.py' | head -30
grep -rn 'def .*complet\|def .*chat\|def .*generate\|def .*infer' ~/empire-repo-main/openclaw --include='*.py' | head -20
```
**The decisive question:** does OpenClaw use an Ollama-specific client, or a
generic provider abstraction? That decides whether this is a client swap or a
config change.

Paste the actual model-call function.

### 1.2 — MAX's provider router — what can be reused?
```
grep -rn 'class AIRouter\|def route\|def select_provider\|def get_provider' ~/empire-repo-main/backend/app/services/max/ai_router.py | head -20
sed -n '1,60p' ~/empire-repo-main/backend/app/services/max/ai_router.py
curl -s http://localhost:8000/api/v1/max/models | ~/empire-repo-main/backend/venv/bin/python -m json.tool | head -50
```
Report the provider list with `configured` / `enabled` / `fallback_eligible`
per provider — this is the registry a selector would read.

**Then the integration question:** OpenClaw is a separate process on :7878.
Can it **import** MAX's router (same venv, same tree), or must it call the
backend over HTTP? Check whether `openclaw/` is on the same `PYTHONPATH`:
```
systemctl --user cat empire-openclaw.service | grep -E 'ExecStart|WorkingDirectory|Environment'
~/empire-repo-main/backend/venv/bin/python -c "
import sys; sys.path.insert(0, '/home/rg/empire-repo-main/backend')
from app.services.max.ai_router import AIRouter
print('importable:', AIRouter)
"
```
**Import is preferable** — an HTTP hop adds a failure mode and a second place
for a stale key to hide. But report what is actually possible, not what is
preferable.

### 1.3 — Credentials in OpenClaw's environment
```
OCPID=$(systemctl --user show empire-openclaw.service -p MainPID --value)
echo "openclaw pid: $OCPID"
tr '\0' '\n' < /proc/$OCPID/environ | grep -iE 'minimax|groq|gemini|xai|grok|openai|ollama|api_key|base_url' | sed 's/=.*/=<PRESENT>/'
systemctl --user cat empire-openclaw.service | grep -E 'EnvironmentFile|Environment'
```
**Critical:** `provider-env.conf` is a drop-in on `empire-backend.service`, not
on `empire-openclaw.service`. If MiniMax credentials are absent from OpenClaw's
env, a code change alone accomplishes nothing.

**Reminder from tonight:** systemd merges drop-ins **alphabetically**, and
`systemctl show -p Environment` does **not** display `EnvironmentFile=`
contents. `/proc/<pid>/environ` is the only truth. That shadow cost four probes
today.

### 1.4 — The gate
```
sed -n '1,80p' ~/empire-repo-main/backend/app/services/max/openclaw_gate.py
grep -rn 'ollama\|11434' ~/empire-repo-main/backend/app/services/max/openclaw_gate.py
```
Exactly what does it check, and what does it return on failure? **It refuses
submissions when Ollama is unreachable** — so nothing new can enter the queue.
Fix the worker and leave the gate, and the fix does nothing.

🛑 **STOP.** Report: client type, import-or-HTTP, credentials PRESENT/ABSENT
in OpenClaw's env, and exactly what the gate requires.

---

## PART 2 — QUARANTINE THE QUEUE (BEFORE ANY PROVIDER WORKS)

**4,921 queued test-suite tasks from September 2025.** The moment a model
becomes reachable, a polling worker starts executing them — burning tokens on a
year-old harness. **This must land before Part 3.**

### 2.1 — Confirm the shape (read only)
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
print("queued by source:")
for r in con.execute("""SELECT source, COUNT(*) FROM openclaw_tasks
                        WHERE status='queued' GROUP BY source ORDER BY 2 DESC"""):
    print(f"  {str(r[0]):<28} {r[1]}")
print("\nqueued by month:")
for r in con.execute("""SELECT substr(created_at,1,7), COUNT(*) FROM openclaw_tasks
                        WHERE status='queued' GROUP BY 1 ORDER BY 1"""):
    print(f"  {r[0]}  {r[1]}")
print("\nqueued NOT from test-suite (these may be real work):")
for r in con.execute("""SELECT id, title, source, created_at FROM openclaw_tasks
                        WHERE status='queued' AND source != 'test-suite'
                        ORDER BY created_at DESC LIMIT 20"""):
    print("  ", str(r)[:180])
con.close()
PY
```

**Report the non-test-suite queued tasks in full.** Those may be real work the
founder submitted that never ran. **They are not cancelled without his ruling.**

🛑 **STOP.** Report before writing anything.

### 2.2 — Cancel test-suite backlog (only on go-ahead)
Back up first:
```
cp -av /home/rg/empire-data/empire.db ~/backups/pre-R8-queue-$(date +%Y%m%d_%H%M).db
```
Then set `status='cancelled'` **only** where `source='test-suite'` AND
`status='queued'` AND `created_at < '2026-01-01'`. Add a note field if the
schema has one: `cancelled by R8 2026-08-22 — Sept-2025 harness backlog`.

Report rows affected. Verify the count matches 2.1. **Do not touch any task
whose source is not `test-suite`.**

---

## PART 3 — THE SELECTOR

Only after Parts 1 and 2 are reported and approved.

### 3.1 — Design constraints
- **Reuse MAX's provider registry.** Do not build a second one. Two provider
  systems means two places for a stale key to hide.
- **Shared credentials, independent preference.** OpenClaw picks its own model;
  the keys come from the same source.
- **Chain with working fallback.** MiniMax primary. Groq and Gemini next if
  credentials are present. **Fallback must actually fall back** — MAX currently
  ships `fallback_used: false` with fallback disabled, and that single-provider
  exposure is the thing we are not repeating.
- **Ollama present but disabled by default.** A config entry, not a running
  service. If ever enabled it needs a memory ceiling — note this in the config
  comment.
- **Per-task override** so an expensive task can be pinned to a better model.

### 3.2 — Budget guards (new, and required)
The autopsy found ~60,000 tokens burned on tasks that failed after the model
call. Before the worker runs again:
- **max steps per task**
- **max tool calls per task**
- **abort and surface on breach** rather than retrying into a wall

Without these, one bad task loop can spend real money unattended.

### 3.3 — The gate
Update `openclaw_gate.py`: require **a reachable provider**, not Ollama
specifically. Preserve every other check it makes. **Do not weaken a gate to
make a task pass** — if it refuses for a reason other than provider reachability,
that refusal stays.

### 3.4 — Prove it with exactly ONE task
Submit **one** trivial task — a string transform, no tools, no file writes, no
network beyond the model call. Watch it complete.

**That would be the first successful OpenClaw task since 2026-04-28.**

Report: task id, provider used, tokens consumed, wall time, final status. Then
**stop the worker** or leave the queue drained per founder instruction — do not
let it start processing anything else.

🛑 **STOP.**

---

## REPORT

`~/R8_OPENCLAW_PROVIDER_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```
Print at the end:
```
CLIENT TYPE: ollama-specific / generic-abstraction
INTEGRATION: import / http
MINIMAX CREDS IN OPENCLAW ENV: PRESENT/ABSENT
GATE REQUIRES OLLAMA: YES/NO
QUEUED TEST-SUITE CANCELLED: <n>
QUEUED NON-TEST-SUITE REMAINING: <n>  (founder ruling pending)
PROVIDER CHAIN: <primary> -> <fallback> -> <fallback>
FALLBACK ACTUALLY FALLS BACK: YES/NO
BUDGET GUARDS: steps=<n> tools=<n>
FIRST SUCCESSFUL TASK SINCE 2026-04-28: YES/NO
COMMITS: <hashes, pushed>
```
