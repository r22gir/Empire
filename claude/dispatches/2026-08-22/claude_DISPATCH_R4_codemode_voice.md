# DISPATCH R4 — CODE MODE + VOICE: WHAT ACTUALLY WORKS
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Mode:** **READ ONLY, ALL PARTS.** Nothing in this dispatch edits, installs,
restarts, or submits a task. It answers two questions with evidence.

**Context:** code execution was dead 106 days (2026-05-06 → 2026-08-20) and was
restored two days ago. Two F-items from that repair are still open in
`reports/2026-08-22_pin_gate_followups.md`. Before deciding whether Code Mode
is the feature that lets MAX act, we need to know what a submitted task
actually does — not what the endpoint is named.

---

## HARD RULES

1. **READ ONLY.** No edits, no installs, no restarts, no `daemon-reload`.
   **Do not submit a code task**, not even a harmless one. Reading the runner
   is the job; running it is a separate decision.
2. **Do not touch** `~/empire-data/brain/*`, the cron, or systemd.
3. Never print PIN values or secrets. PRESENT/ABSENT only.
4. `sqlite3` CLI not installed — use `~/empire-repo-main/backend/venv/bin/python`.
5. Repo: `~/empire-repo-main`, branch `feature/drawing-standard`.
6. **Say what you verified vs. inferred, per claim.** If a capability is
   claimed by a docstring but not visible in code, say so.

---

## PART 1 — WHAT DOES A SUBMITTED CODE TASK ACTUALLY DO?

### 1.1 — Locate and size the runner
```
find ~/empire-repo-main/backend -name 'code_task_runner*' -o -name '*code_task*' | head
wc -l ~/empire-repo-main/backend/app/services/max/code_task_runner.py 2>/dev/null || \
  wc -l $(grep -rl 'def submit' ~/empire-repo-main/backend/app --include='*code_task*')
grep -n '^class \|^def \|^    def ' <runner path>
```
Report the full function/class inventory. That list is the capability surface.

### 1.2 — Trace `submit()` end to end
Read `submit()` and everything it calls, and answer these **specifically**:

- Does it **write files to disk**? Which paths — repo, data dir, temp?
- Does it **execute code**? Via subprocess, exec, a shell, or a sandbox?
- Does it **run tests**?
- Does it **git commit**? **git push**?
- Does it run **synchronously** in the request, or queue for a worker?
- Is it **bounded** — timeout, max steps, max tool calls, cost ceiling?
- What does it **return to the caller** — a diff, a task id, a result object?
- Does the founder **review before anything lands**, or does it land directly?

Deliver a table:
```
CAPABILITY            | YES/NO | file:line | notes
writes files          |        |           |
executes code         |        |           |
runs tests            |        |           |
git commit            |        |           |
git push              |        |           |
founder review gate   |        |           |
timeout / step budget |        |           |
```

**This table is the deliverable.** It answers whether Code Mode is "MAX edits
the repo" or "MAX drafts a suggestion."

### 1.3 — The scorer at line 399
```
sed -n '370,430p' <runner path>
```
What does it score, on what scale, and **what does the score gate**? Does a low
score block the task, or is it advisory? This is open item F1 — report what is
broken about it, from the code, not from the task list.

### 1.4 — What's missing (F5/F6)
Open item: *"STAGE 4 — F5/F6: counters + retry budget."*
```
grep -n 'retry\|budget\|counter\|max_attempts\|attempt' <runner path>
```
Report what exists vs. what those two items would add. **With no retry budget,
what happens when a task fails mid-way?**

### 1.5 — Has it ever run?
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
tabs = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND ("
    "name LIKE '%code%' OR name LIKE '%task%')")]
print("candidate tables:", tabs)
for t in tabs:
    cols = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
    n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"\n{t}  rows={n}\n  cols={cols}")
    for r in con.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 5'):
        print("  ", str(r)[:300])
con.close()
PY
```
Also check the evidence files from the 8/20 repair:
```
ls -la ~/empire-repo-main/codetask_stage3_*.txt
head -40 ~/empire-repo-main/codetask_stage3_evidence.txt
```
**Report: how many real code tasks have ever completed successfully, and when
was the last one?** A restored feature with zero successful runs is restored on
paper.

🛑 **STOP.** Report the capability table, the scorer, F5/F6 gap, and run history.

---

## PART 2 — VOICE MODE IN THE MAX DASHBOARD

The founder needs voice operational in the MAX chat. Establish what exists.

### 2.1 — Backend: STT and TTS
Prior record mentions Groq Whisper (speech-to-text) and Grok "Rex" (text-to-speech).
```
grep -rn 'whisper\|Whisper\|transcri\|speech\|tts\|TTS\|elevenlabs\|audio' \
  ~/empire-repo-main/backend/app --include='*.py' | grep -v test | head -40
curl -s http://localhost:8000/openapi.json | ~/empire-repo-main/backend/venv/bin/python -c "
import sys, json
paths = json.load(sys.stdin).get('paths', {})
hits = [p for p in paths if any(k in p.lower() for k in
        ('voice','audio','speech','tts','stt','transcri','whisper'))]
print('VOICE-RELATED ROUTES:', len(hits))
for p in sorted(hits):
    print(' ', ','.join(sorted(m.upper() for m in paths[p])), p)
"
```

### 2.2 — Are the providers configured?
```
tr '\0' '\n' < /proc/$(systemctl --user show empire-backend.service -p MainPID --value)/environ \
  | grep -Ei 'groq|grok|xai|eleven|whisper|tts|voice' | sed 's/=.*/=<PRESENT>/'
curl -s http://localhost:8000/api/v1/max/models | ~/empire-repo-main/backend/venv/bin/python -m json.tool | grep -iE 'groq|grok|configured|available|disabled' | head -30
```
Report provider → credential PRESENT/ABSENT → enabled or disabled, and **why**
disabled if so (policy vs. missing key). Never print values.

### 2.3 — Frontend: is there a mic in the UI?
```
cd ~/empire-repo-main/empire-command-center
grep -rn 'MediaRecorder\|getUserMedia\|webkitSpeechRecognition\|SpeechRecognition\|audio/webm\|mic' \
  app --include='*.tsx' --include='*.ts' | head -30
grep -rln 'voice\|Voice\|Mic\|microphone' app --include='*.tsx' | head -20
```
Report: does a mic control exist in the chat screen, what does it call, and does
that route exist in the 2.1 inventory? **A button wired to a missing route is
the most likely failure mode — check for it explicitly.**

### 2.4 — Does the portal even serve?
The founder reports the interfaces are stale. Nobody has opened a page — every
check so far has been `curl` against the API.
```
curl -s -o /dev/null -w "portal / → %{http_code}\n" http://localhost:3005/
curl -s -o /dev/null -w "portal /max → %{http_code}\n" http://localhost:3005/max
curl -s http://localhost:3005/max | grep -oiE 'error|not found|exception|__next_error' | head
systemctl --user status empire-portal.service --no-pager | head -12
ls -la ~/empire-repo-main/empire-command-center/.next/BUILD_ID 2>&1
cat ~/empire-repo-main/empire-command-center/.next/BUILD_ID 2>&1
```
Report the build timestamp. **If the build predates recent backend changes, the
UI is serving stale code against a newer API** — which would explain "interfaces
have been stale."

### 2.5 — The two known hardcodes
Prior probe found two hardcoded `localhost:8000` sites; three others use
`process.env.NEXT_PUBLIC_API_URL`. Confirm current state:
```
grep -rn 'localhost:8000' app --include='*.tsx' --include='*.ts' | head -20
grep -rn 'NEXT_PUBLIC_API_URL' app --include='*.tsx' --include='*.ts' | head -20
```
**Report which pages break when accessed from anywhere other than EmpireDell** —
that determines whether voice (or anything) works from the founder's phone.

🛑 **STOP.** Report voice routes, providers, mic control, build age, hardcodes.

---

## REPORT

`~/R4_CODEMODE_VOICE_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```
Print at the end:
```
CODE MODE — WRITES FILES: YES/NO
CODE MODE — EXECUTES: YES/NO
CODE MODE — COMMITS: YES/NO
CODE MODE — FOUNDER GATE: YES/NO
CODE MODE — SUCCESSFUL RUNS EVER: <n>, last: <date>
VOICE — STT ROUTE EXISTS: YES/NO
VOICE — TTS ROUTE EXISTS: YES/NO
VOICE — PROVIDER CONFIGURED: YES/NO
VOICE — MIC CONTROL IN UI: YES/NO
VOICE — END TO END POSSIBLE TODAY: YES/NO
PORTAL BUILD DATE: <date>
PAGES BROKEN OFF-HOST: <n>
```
