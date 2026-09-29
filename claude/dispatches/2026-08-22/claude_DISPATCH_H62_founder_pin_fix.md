# DISPATCH H62-FIX — CLOSE THE THREE REMAINING `"7777"` DEFAULTS
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Predecessor:** R2 §B5 (read-only trace, `~/R2_INFRA_2026-08-22.md`)
**Severity:** security. Small diff, high consequence.

---

## THE FINDING

HOTFIX 4.2 (2026-07-24) removed the privilege-escalation default
`os.getenv("FOUNDER_PIN", "7777")` from `app/services/max/tool_executor.py`
and replaced it with a fail-closed pattern. **It did not reach three other
call sites:**

| file:line | role |
|---|---|
| `app/routers/max/router.py:5027` | MAX route PIN check |
| `app/routers/max/router.py:5060` | MAX route PIN check |
| `app/routers/auth.py:184` | **JWT issue path — the highest-consequence one** |

All three still fall back to the literal `"7777"` when the env var is unset.
While `founder-pin.conf` sets the value they are dormant. If that drop-in is
ever removed, renamed, cleared, or fails to load, all three grant
founder-equivalent access — **routing around the fail-closed gate that was
built to prevent exactly this.**

The tree's own comments (`tool_executor.py:65–68, 97, 497`) name `"7777"` as
the privilege-escalation default. The intent was to remove it everywhere.

**DOCTRINE:** *make the wrong thing unreachable, not merely discouraged.*
Today it is reachable and held back by one config file.

Additional context: the running process (PID 955477) currently carries `7777`
in its environment — inherited at launch from an older drop-in revision, not
from a code default. So the value the fix was meant to eliminate is the value
in force in production right now. **That is corrected by a restart, which is
Part 3 of this dispatch and requires founder go-ahead.**

---

## HARD RULES

1. **🛑 STOP-GATED.** Three parts. Report and wait after each.
2. **Match the existing fixed pattern.** Do not invent a new one. Read
   `tool_executor.py` around line 82 first and copy its shape exactly.
3. **Fail closed.** No default. Unset env → refuse + log CRITICAL. Never
   fall back to any literal.
4. **Never print PIN values** — not in output, not in logs, not in the report,
   not in commit messages. Report PRESENT/ABSENT only.
5. **Do not weaken any gate.** If a site currently refuses something, it must
   still refuse it after the change.
6. Repo: `~/empire-repo-main`, branch `feature/drawing-standard`.
7. `sqlite3` CLI not installed — use `~/empire-repo-main/backend/venv/bin/python`.

---

## PART 1 — READ THE REFERENCE PATTERN, THEN THE THREE SITES

**Read only. No edits.**

```
sed -n '60,110p' ~/empire-repo-main/backend/app/services/max/tool_executor.py
```
Report the exact fail-closed shape: how it reads the env, what it does when
empty, what it logs, and what it returns to the caller.

Then each target site with enough surrounding context to see the control flow:
```
sed -n '5010,5045p' ~/empire-repo-main/backend/app/routers/max/router.py
sed -n '5045,5075p' ~/empire-repo-main/backend/app/routers/max/router.py
sed -n '165,205p'   ~/empire-repo-main/backend/app/routers/auth.py
```

For each, report:
- What the PIN is compared against, and what happens on match vs mismatch.
- **What the caller gets on refusal** — 401? 403? silent false? This decides
  whether the fix changes behaviour for legitimate callers.
- Whether `auth.py:184` issues a JWT, and what claims it carries.

Then sweep for any site the trace missed:
```
grep -rn 'FOUNDER_PIN' ~/empire-repo-main/backend --include='*.py'
grep -rn '"7777"\|'"'"'7777'"'"'' ~/empire-repo-main/backend/app --include='*.py'
```
Report **every** hit. If a fourth site exists, name it.

🛑 **STOP.** Report the pattern, the three sites, the refusal behaviour, and
whether the sweep found anything beyond the three.

---

## PART 2 — THE FIX

Apply the fail-closed pattern from `tool_executor.py` to all three sites (plus
any fourth found in Part 1).

Required properties:
- `os.getenv("FOUNDER_PIN", "")` — **empty default, never a literal.**
- `if not pin:` → refuse, log CRITICAL, do not authenticate.
- Refusal path must be identical to the existing mismatch path so legitimate
  callers see no new behaviour.
- **Comment each site** with why the literal was removed and the date, so the
  next person doesn't reintroduce it as a convenience.

Then prove it, without restarting the service:
```
cd ~/empire-repo-main/backend
# 1. no literal survives anywhere
grep -rn '"7777"' app --include='*.py' && echo "STILL PRESENT — FAIL" || echo "clean"
# 2. every FOUNDER_PIN read is empty-defaulted
grep -rn 'FOUNDER_PIN' app --include='*.py'
# 3. imports still resolve
~/empire-repo-main/backend/venv/bin/python -c "
import app.routers.auth, app.routers.max.router, app.services.max.tool_executor
print('imports ok')
"
```

Write a negative test that proves the wrong thing is now unreachable: with
`FOUNDER_PIN` unset in a subprocess env, the PIN check must refuse — **and it
must refuse when handed the literal `7777`.** That test is the artifact that
stops this regressing. Put it in `backend/tests/`.

Run it. Paste the output.

Commit on `feature/drawing-standard`. **Push.** Commit message names the
sites and references HOTFIX 4.2 as the partial fix — no PIN values.

🛑 **STOP.** Report diff, grep proof, test output, commit hash.

---

## PART 3 — RESTART (FOUNDER GO-AHEAD REQUIRED)

Do not run this without explicit approval in the session.

The running process carries the stale value. A restart picks up the current
drop-in and the new code. It also activates R2 B4's unit-file changes.

**Before restarting, state plainly what will change**, then wait.

On go-ahead:
```
systemctl --user daemon-reload
systemctl --user restart empire-backend.service
sleep 8
systemctl --user show empire-backend.service -p MainPID --value
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
curl -s -m 5 http://localhost:8000/api/v1/max/health | head -c 300; echo
```

Then re-prove **R1 survived the restart** — this is the critical check:
```
BPID=$(systemctl --user show empire-backend.service -p MainPID --value)
tr '\0' '\n' < /proc/$BPID/environ | grep -E 'MAX_MEMORY_PATH|EMPIRE_BRAIN_DIR|FOUNDER_PIN' | sed 's/=.*/=<redacted>/'
```
Expect all three PRESENT. **If `MAX_MEMORY_PATH` or `EMPIRE_BRAIN_DIR` is
missing, R1 has reverted — stop and report immediately.**

Then confirm brain writes still land canonical:
```
stat -c '%n %y' /home/rg/empire-data/brain/*.db /home/rg/empire-repo/backend/data/brain/*.db
```
Canonical should be current; the old lane must stay frozen.

Corridor sanity:
```
for r in "/api/v1/quotes-v2/stats" "/api/v1/crm/customers?limit=5" "/api/v1/jobs/dashboard"; do
  curl -sL -o /dev/null -w "%{http_code} $r\n" "http://localhost:8000$r"
done
```

🛑 **STOP.** Report new PID, health, R1 env proof, brain mtimes, corridor.

---

## REPORT

`~/H62_FIX_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```
Print at the end:
```
SITES FIXED: <n>
LITERAL "7777" REMAINING IN app/: <n>   (must be 0)
NEGATIVE TEST PASSES: YES/NO
COMMIT: <hash, pushed>
RESTARTED: YES/NO
R1 PINS SURVIVED RESTART: YES/NO/N-A
```
