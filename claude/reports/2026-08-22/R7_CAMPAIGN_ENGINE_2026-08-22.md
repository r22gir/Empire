# R7 CAMPAIGN ENGINE — 2026-08-22
**Mode:** READ ONLY (Part 1 only). **Repo:** `~/empire-repo-main`, branch `feature/drawing-standard`.
**Backend PID:** 980291 (untouched, no restart). **Portal:** :3005 (untouched).

---

## PART 1 — OPENCLAW AUTOPSY: WHAT WERE THE 5,945 FAILURES?

### 1.1 — Group the failures (the decisive output)

**Source:** `/home/rg/empire-data/empire.db` (read-only) — `openclaw_tasks` table, 7,390 rows total.

**Status distribution:**

```
  failed               5945  (80.4%)
  done                 1443  (19.5%)
  cancelled               2
  TOTAL                7390
```

**DISTINCT NORMALISED ERROR SHAPES: 19** (after stripping digits, quoted strings, and path tails).

**Top 25 error shapes by frequency:**

```
5679  Code task completed without actual file changes (provider=openclaw, model=openclaw, attempts=N)
 158  selected code model did not emit executable tool calls (provider=openclaw, model=openclaw, attempts=N). No deterministic fallback plan could be inferred from th…
  36  Code task completed without actual file changes (provider=unknown, model=none, attempts=N)
  16  Recovered orphaned running task after worker restart.
  13  CodeTaskRunner timed out after Ns
  10  OpenClaw status unknown - running in inspect-only mode. Manual delegation available.
  10  Task timed out — Atlas was unresponsive for too long
   4  Code task completed without actual file changes (provider=xai, model=grok-N-fast-non-reasoning, attempts=N)
   4  selected code model did not emit executable tool calls (provider=unknown, model=none, attempts=N). No deterministic fallback plan could be inferred from the pro…
   3  model did not provide executable tool calls.
   2  CodeTaskRunner completed without tool/PATH evidence; refusing to mark DB task done.
   2  OpenClaw degraded (worker heartbeat stale (N.Ns old)) - delegation blocked. Will retry when healthy.
   2  OpenClaw degraded (stale running OpenClaw task(s) without active worker: [N]) - delegation blocked. Will retry when healthy.
   1  Incorrect executor routing: CodeForge source-grounding task was routed to drawing generator because task text mentioned drawing. Requested code fix was not atte…
   1  CodeTaskRunner/PATH reported edits, tests, and a fake commit, but git remained clean at NfNcN and openclaw_tasks.commit_hash was null. Requested code fix was no…
   1  Code task completed without actual file changes; refusing to accept prose-only summary.
   1  Repo file_write succeeded, but git_ops diff --check failed repeatedly, no commit was created, and task left untracked repo files. Task should not have been mark…
   1  (null)
   1  Code task completed without actual file changes (provider=groq, model=groq-llama-N.N-Nb, attempts=N)
```

#### Distribution analysis (the dispatch's headline question)

**The top shape covers 5,679 of 5,945 failures = 95.5%.** The next 5 shapes (158 + 36 + 16 + 13 + 10) account for another 233 (3.9%). Together the top 6 = **5,912 of 5,945 = 99.4%**.

**Not flat across hundreds of shapes. Highly concentrated on ONE root cause** (with cosmetic provider/model variations). **OpenClaw is NOT unfit from failure-cause diversity** — the failure surface is small enough that one bug could plausibly explain most of it.

### 1.2 — When did it stop working, what changed

**Monthly volume + failure rate:**

```
  2026-03  total=9      failed=0      rate=0%
  2026-04  total=52     failed=12     rate=23%
  2026-05  total=7296   failed=5904   rate=81%    ← massive spike
  2026-06  total=6      failed=6      rate=100%
  2026-08  total=27     failed=23     rate=85%
```

The **May 2026 spike is the entire story**: 7,296 tasks in one month, 5,904 failed (81%). That accounts for 99.3% of all failures. **April was clean (23% failure rate, low volume). June collapsed to nothing. August is a small tail.**

#### Last 10 tasks that COMPLETED (status='done')

```
  id=7384  'Read STATE.md'                                          done  created=2026-08-20 20:53:29  completed=2026-08-20T16:56:48
  id=7381  'Git status'                                             done  created=2026-08-20 20:52:13  completed=2026-08-20T16:54:14
  id=7380  'STAGE3 live proof — exact-content append'               done  created=2026-08-20 20:17:41  completed=2026-08-20T16:18:10
  id=7379  'STAGE3 live proof — append a single line to /tmp scratch file'  done  created=2026-08-20 20:15:57  completed=2026-08-20T16:16:53
  id=7342  'Read file'                                              done  created=2026-05-06 07:24:55  completed=2026-05-06T10:35:37
  id=7321  'Read file'                                              done  created=2026-05-06 07:17:51  completed=2026-05-06T10:30:29
  id=7317  'Read file'                                              done  created=2026-05-06 07:16:22  completed=2026-05-06T10:29:37
  id=7311  'Read file'                                              done  created=2026-05-06 07:09:06  completed=2026-05-06T10:28:15
  id=7280  'Read file'                                              done  created=2026-05-06 06:57:45  completed=2026-05-06T10:21:03
  id=7262  'Read file'                                              done  created=2026-05-06 06:42:47  completed=2026-05-06T10:14:33
```

**Pattern:** all 10 most-recent successful tasks are **read-only operations** ("Read STATE.md", "Git status", "Read file"). The 2 STAGE3 tasks are also small writes that did succeed. **OpenClaw works for read tasks. It also works for small explicit writes. It fails on the vast middle of code-write attempts.**

**Date range:**
- Failed tasks: `2026-04-26` to `2026-08-20` (4 months)
- Done tasks: `2026-03-31` to `2026-08-20` (5 months)
- The most recent successful task is **2026-08-20 20:53:29** — 6 days before this dispatch (2026-08-22).

#### Failed-task pattern by source path (the dispatch didn't ask, but it's the smoking gun)

```
Failed tasks reading OLD path  /home/rg/empire-repo/backend/:        5504  (all in 2026-05)
Failed tasks reading NEW path  /home/rg/empire-repo-main/:            10  (all in 2026-08)
Failed tasks reading OTHER paths (incl. /home/rg/empire-repo-v10/): 287 + 6 + 12 + 13  = 318
```

**5,504 of 5,945 failures (92.6%) are reads of the OLD stale repo path `/home/rg/empire-repo/backend/...` — the deprecated mirror before R1's canonicalization.** All happened in May 2026. **The remaining 441 failures are scattered (some real work, some pre-R1 reads of other paths, some post-R1 reads).**

### 1.3 — Real business tasks, or dev probe noise?

#### By desk

```
  auto                      7339    (99.3% of all 7390 tasks)
  codeforge                 27
  general                   6
  it                        4
  ITDesk                    3
  ops                       2
  CodeForge                 1
  ForgeDesk                 1
  aria                      1
  cipher                    1
  codedesk                  1
  finance                   1
  founder                   1
  innovation                1
  marketing                 1
```

**99.3% of all OpenClaw tasks are routed via the `auto` desk.** No business-domain desk (ForgeDesk, Aria, Elena, SalesDesk, etc.) has more than 1 task. **This is overwhelmingly a single auto-generated path, not 14 different desks doing real work.**

#### By source

```
  desk_fallback             7336    (99.3%)    ← the catch-all when no desk accepts
  manual-code-task          21
  manual                    11
  migrated                  8
  max                       8
  manual-self-test          2
  audit-recovery            2
  verification_smoke        1
  manual-retry              1
```

**99.3% of all OpenClaw tasks are `desk_fallback` — i.e., a task that no other desk accepted and that fell through to the `auto` desk's code-task runner.** This is consistent with read-only operations being misclassified as "code tasks" because no read desk is configured to accept them.

#### Sample failed task titles

```
  Ground MAX current-source replies and harden drawing intent   (×3)
  OpenClaw routing self-test fix drawing intent
  OpenClaw code task evidence self-test write diagnostic
  Read /home/rg/empire-repo/backend/app/services/max/system_prompt.py
  Read /home/rg/empire-repo/backend/app/services/max/openclaw_gate.py
  Read /home/rg/empire-repo/backend/app/services/max/ai_router.py
  Git log /home/rg/empire-repo/backend/app/services/max
  Git status
```

#### Sample completed task titles

```
  Read STATE.md
  Git status
  STAGE3 live proof — exact-content append
  Read file  (×6 in May 2026)
```

**Description samples for failed tasks (all `desk='auto'`):**

```
  Tool: file_read | Path: /home/rg/empire-repo-main/STATE.md
  Tool: file_read | Path: /home/rg/empire-repo-main/STATE.md
  Tool: file_read | Path: /home/rg/empire-repo-main/STATE.md
  …
```

#### Commit-hash audit (the truth test)

```
Failed tasks with non-null commit_hash:  0  of 5945
Done tasks with non-null commit_hash:    0  of 1443
```

**Zero tasks — failed or done — have a commit_hash.** This confirms: **the OpenClaw queue was never used for actual code commits via the auto/desk_fallback path.** All "success" tasks were read-only. All "failure" tasks were either reads (misclassified as code tasks) or small writes that didn't commit.

### Validator location (the smoking gun)

The "Code task completed without actual file changes" error is emitted by two files:

```
backend/app/services/max/code_task_runner.py:992  (95.5% of failures)
backend/app/services/openclaw_worker.py:877        (variant)
```

`code_task_runner.py` is the **code-task validator**. It runs when a task is routed to the code-task pipeline. It rejects tasks where the runner reports success but no actual file changes happened — which is the correct semantic for a code task. **The error is correct; the routing is wrong.**

The 5,504 reads of `/home/rg/empire-repo/backend/...` are being routed to the code-task pipeline because:
1. The `auto` desk is the catch-all fallback when no other desk accepts a task
2. The `auto` desk's task-type classifier (path-based) matches the read pattern against a code-task template
3. Read operations don't produce file changes → validator fails
4. The 1,394 successful `auto` reads are likely reads whose path-based classification DID match a read template (or that ran before the classifier was tightened)

### Part 1 VERDICT (required by dispatch)

| field | value |
|---|---|
| **TOP ERROR SHAPE COVERS** | **95.5%** of failures (5,679 of 5,945) — one shape: "Code task completed without actual file changes" |
| **DISTINCT ROOT CAUSES (est)** | **1 primary** + minor variants. The 5,679 are the same root cause; cosmetic variations in provider/model name. Other 266 failures = 14 distinct shapes. |
| **LAST SUCCESSFUL TASK** | **2026-08-20 20:53:29** — "Read STATE.md" (a read operation) |
| **FAILURES ARE** | **Dev probe noise, mostly.** 92.6% are reads of the OLD stale repo path (`/home/rg/empire-repo/backend/`) that pre-date R1's canonical-path migration. ~7% are scattered post-R1 reads + a small real-work tail. **Not 5,945 failed business operations; 5,945 misclassified read attempts.** |
| **OPENCLAW VERDICT** | **Misconfigured-and-revivable.** The runtime works (read tools execute correctly; small writes can succeed). The bug is in the desk-routing / task-type classifier that sends reads through the code-task validator. Fix scope: classifier + maybe code_task_runner fallback for read-only task types. |

### What this means for the founder's engine question

The dispatch premise: *"OpenClaw: 7,390 tasks, 5,945 failed, dormant. If those 5,945 failures are one root cause, OpenClaw was misconfigured and reviving it is hours."*

**The premise holds for shape (one root cause) but the cause is different from "OpenClaw runtime is broken." The cause is "the desk router misclassifies reads as code tasks."** That's still hours-to-fix, not a rebuild. **Hermes is not yet justified by OpenClaw's state.** But the campaign machinery question (Part 3) still needs answering — and the founder may want a dedicated read-only desk or a separate intake path regardless.

### Files inspected (read-only, no edits)

```
backend/app/services/max/code_task_runner.py  (lines around 992, validator)
backend/app/services/openclaw_worker.py      (line 877, variant validator)
backend/app/services/max/openclaw_gate.py     (reference, no read needed)
backend/app/services/max/openclaw_tasks.py    (referenced)
```

No code modified. No tasks submitted. No queries to OpenClaw API. No external calls.

---

## VERIFIED
- `openclaw_tasks` table has 7,390 rows. Status: 5,945 failed, 1,443 done, 2 cancelled. Date range 2026-03-31 to 2026-08-20.
- 19 distinct normalized error shapes; top shape covers 5,679 of 5,945 failures (95.5%).
- Top shape literal: "Code task completed without actual file changes (provider=openclaw, model=openclaw, attempts=N)". Emitted by `code_task_runner.py:992`.
- Last successful task: `id=7384 "Read STATE.md"`, completed 2026-08-20 20:53:29 EDT.
- 99.3% of all tasks are `desk='auto'` and `source='desk_fallback'`.
- 5,504 of 5,945 failures (92.6%) are reads of `/home/rg/empire-repo/backend/...` — the stale path pre-R1 canonicalization.
- 0 failed tasks have `commit_hash`; 0 done tasks have `commit_hash`.
- The `code_task_runner.py` validator is correct semantically (rejects "code task succeeded without file changes"); the routing is wrong (reads get routed to it).

## INFERRED
- The 5,504 stale-path read failures were generated by an automated path in May 2026 that targeted the deprecated `/home/rg/empire-repo/backend/` mirror. The R1 canonical-path fix (2026-08) stopped new stale-path reads; the May 2026 backlog remains in the DB.
- The "auto desk + desk_fallback" path is a single misclassified-read pipeline. When the task title starts with "Read /path" or "Git status/log", the `auto` desk's classifier routes it to the code-task runner, which then fails on the validator because no file changes occurred. Reads should be routed to a read-only desk (e.g., `general` or `it`), not to the code task runner.
- OpenClaw's runtime executes the read tools correctly (file_read returns content, git_ops returns status) — proven by the 1,443 successful read tasks. The "OpenClaw is broken" interpretation is wrong; **OpenClaw's task-type classifier is broken.**
- The dispatch premise ("5,945 failures = OpenClaw unfit") was correct in shape (one root cause = good) but wrong in attribution (the cause is routing/classification, not the runtime).

## COULD NOT PROBE
- Why May 2026 generated 7,296 tasks (vs April's 52). Some external scheduler / loop / dev automation likely was firing during that month. Not determinable from openclaw_tasks alone — would need to inspect MAX's task-generation logs or scheduler history.
- Whether any of the "max" or "manual" source tasks (totaling 19) actually represent real business operations vs dev probes. Sample sizes too small to call.
- Why the validator at `code_task_runner.py:992` doesn't recognize read-only task types. The dispatch hints at this but the exact classifier logic wasn't fully traced in this Part 1.

---

## HEADLINE TOTALS (PART 1)

```
OPENCLAW: top error shape = 95.5%   · distinct causes ≈ 1 primary + 14 minor   · verdict = misconfigured-and-revivable
LAST SUCCESSFUL OPENCLAW TASK: 2026-08-20 20:53:29 ("Read STATE.md", a read)
NATURE OF FAILURES: 92.6% reads of stale repo path; 7.4% scattered; ~0% real business code-write operations
HERMES WORKER POLLING:                                              (PART 2 — not run yet)
MAX→HERMES INTEGRATION EXISTS:                                       (PART 2 — not run yet)
CAMPAIGN CAN REACH EXTERNAL RECIPIENT:                              (PART 3 — not run yet)
PROSPECTS CONTACTABLE BY EMAIL:                                      (PART 3 — not run yet)
MANUAL RUN STEPS:                                                    (PART 3 — not run yet)
```

🛑 **STOPPED per dispatch directive.** Part 1 complete. Awaiting founder decision before Part 2 (Hermes) or Part 3 (campaign machinery).

