# H52 Tool-Selection Map (2026-08-20)

**STOP — Phase 1 read-only map. No fixes.** Per dispatch: "MAP FIRST.
🛑 STOP between phases." Prior context: `reports/2026-08-20_h53_h52_context_map.md`
(commit `eb44b90`). Foundation rules: `claude/DOCTRINE.md` (especially rule
12 — One source of truth / One service layer).

The H52 hypothesis: "MAX cannot SELECT his tools." Confirmed by live
evidence on 2026-08-19 (he ran `empire_runtime_truth_check` unprompted and
returned a verified answer; provider `openclaw`) and 2026-08-20 (he reached
for PIN-gated `shell_execute`, hit the wall, stopped; provider
`minimax-MiniMax-M3`). The map below tells the story in seven answers.

---

## Q5 (RESUMED). IS THERE MORE THAN ONE PROMPT VARIANT PER TURN?

**YES. Two variants. The selection logic lives at:**
- `backend/app/services/max/system_prompt.py:32` — `is_ordinary_text_request(message)` —
  returns `True` if the message contains NONE of the "full prompt" keywords.
- `backend/app/services/max/system_prompt.py:52` — `get_compact_system_prompt(channel)` —
  small prompt (~1500 chars, **NO TOOLS DOC**).
- `backend/app/services/max/system_prompt.py:117` — `get_system_prompt()` —
  full prompt with `{_get_tools_doc()}` (tool_executor.py:4474 — the 42-tool roster).
- `backend/app/services/max/system_prompt.py:663` — `get_system_prompt_with_brain(...)` —
  full prompt + live brain context.

**Selection call sites** (router.py — both `/chat` and `/chat/stream`):
- `backend/app/routers/max/router.py:2469-2478` (non-streaming)
  ```python
  if not request.image_filename and is_ordinary_text_request(request.message):
      enriched_prompt = get_compact_system_prompt(channel=_ch_normalized)
  else:
      enriched_prompt = await get_system_prompt_with_brain(...)
  ```
- `backend/app/routers/max/router.py:3279-3288` (streaming — same pattern)

**The compact variant carries:**
- Founder identity / hierarchy line
- Channel status (60s cached probe)
- Cross-channel snippets (4-hour window, telegram / web / email)
- Hermes bridge (compact=True, 120 chars)
- `founder_email`, `openclaw_url`, today's date
- **NO TOOL ROSTER**
- **NO OPERATING REGISTRY**
- **NO TOOL SAFETY TIERS**
- **NO ROSTER ORDERING**

**The full prompt carries all of the above PLUS** the 42-tool roster
(TOOLS_DOC), operating truth, ecosystem catalog, supermemory recall,
handoff packet, today's session context, live brain context.

**Critical observation — the dispatch's own three verification questions
would all hit the COMPACT prompt:**

| Question (verbatim from dispatch) | Pattern matches | Prompt variant |
|---|---|---|
| "what repo are you reading from, and how do you know?" | none | **compact** (no roster) |
| "what's the state of the system right now?" | none (no "runtime" substring) | **compact** (no roster) |
| "read STATE.md and tell me the current standard pin" | none | **compact** (no roster) |

`is_ordinary_text_request` pattern list (`system_prompt.py:38-48`)
explicitly enumerates 40+ keywords that trigger the full prompt
(create, add, send, git, commit, push, etc.). The dispatch's questions
are meta-questions about the system's state — they have NO action verb
and NO business entity, so the heuristic puts them on the cheap path.

**This is Q5 ANSWERED: yes, multi-variant; yes, the compact variant
omits the entire tool roster; yes, the omitted case includes exactly
the questions where tool selection matters most.** Per dispatch
principle A ("tool roster not optional"): the cheap path is the wrong
path for any question that could lead to a tool call.

---

## Q6 (RESUMED). WHAT DOES THE BANNER READ THAT THE MODEL DOES NOT?

**The banner's data sources are server-side; the system prompt does
NOT push them. The same truth is one tool-call away.**

### Banner source (`get_control_plane()` — control_plane.py:611)
- `identity` — `MAX_IDENTITY` (control_plane.py hard-coded block)
- `provider` — `ai_router.get_routing_state_payload()` — provider_canonical,
  model, fallback_enabled, ai_calls_disabled, lane
- `local_broker` — git branch + commit + repo_root
- `backend` — port 8000 + service active + http /health
- `frontend` — port 3005 + build_id + state
- `openclaw` — state, queue_stats (done / failed / total), worker_heartbeat
  (age_seconds, fresh, current_task_id), proof_source
- `hermes` — state, status, truth_hierarchy, context file mtime
- `memory` — paths, sizes, freshness
- `tool_registry` — control_plane.py:495 — a separate 9-entry control surface
  (NOT the same as TOOLS_DOC)

### Live read confirms
```
$ curl http://127.0.0.1:8000/api/v1/max/control-plane | jq .provider
{
  "provider_canonical": "minimax",
  "model": "MiniMax-M3",
  "provider_label": "MiniMax",
  "fallback_enabled": false,
  "ai_calls_disabled": false,
  "lane": "main"
}
$ jq '.local_broker.repo, .openclaw'
{
  "branch": "feature/drawing-standard",
  "commit": "4201cbf",
  ...
}
"queue_stats": {"cancelled":2, "done":1441, "failed":5933, "total":7376},
"worker_heartbeat": {"status":"polling", "age_seconds":12.817, "fresh":true}
```

### What the system prompt gives MAX (system_prompt.py:117)
- `get_max_brain_context()` (system_prompt.py:519-660) — recent session
  memories, **last 10 git commits**, **port checks for 8000/3005/7878/11434**,
  pending/urgent tasks, cross-channel activity. **60-second cache.**
- **NO `provider` panel** (no model / fallback / lane status)
- **NO `openclaw` queue stats or worker heartbeat**
- **NO `hermes` mtime**
- **NO `tool_registry` (control-plane surface)**
- **NO live registry commit / startup divergence flag**

### What `empire_runtime_truth_check` returns
`runtime_truth_check.py:560-654` returns: `current_commit`, `registry`,
`startup_health`, `openclaw_gate`, `backend_port_8000` /
`backend_port_8010`, `frontend_port_3005` / `frontend_port_3010`,
public API commit + root + memory-bank health, hermes dashboard + cron
status, `stale_or_broken` findings. **It already exists and returns
everything the banner shows.** The tool's description at
`tool_executor.py:4609` says it is "Inspect-only live runtime freshness
check" — but the system prompt does NOT tell MAX to use it for status
questions, and the compact prompt doesn't even list it.

**This is Q6 ANSWERED: the system already knows; the model is not being
told. The "max_status_panel" the founder sees on screen is rebuilt by
the UI from a single endpoint that the system prompt does not
reference.** Per dispatch principle D ("what the banner knows, the model
should know"): either push the same data into the system prompt OR
include a one-line instruction "for system status, call
`empire_runtime_truth_check`" — and make sure the compact prompt has
this tool listed.

---

## Q7 (RESUMED). IS "STARTUP <sha> DIFFERS" STILL REPORTING AFTER CLEAN RESTART?

**YES. Live state right now (2026-08-20 15:31 EDT startup, queried
20:42 EDT):**

```
$ cat /home/rg/empire-repo-main/backend/data/max/startup_health.json
{
  "recorded_at": "2026-08-20T15:31:19.632428+00:00",
  "running_commit_hash": "e854621",
  "running_branch": "feature/drawing-standard",
  ...
  "startup_port_observations": {
    "backend_open_at_record_time": false,  ← noted: backend was DOWN when record was written
    "frontend_open_at_record_time": true,
    ...
  }
}

$ git log --oneline -2
4201cbf docs(dispatch): H52 tool selection
9bb2d6e docs(backlog): code execution RESTORED 2026-08-20 — answer the open Q
```

`startup_commit = e854621`, `current_commit = 4201cbf`. They differ.
The control plane computes this at `control_plane.py:569`:
```python
startup_vs_runtime_match = (startup_commit and commit and startup_commit == commit)
```
…and emits the warning at line 602:
```python
"warning": None if startup_vs_runtime_match else "Startup commit does not match current runtime commit (a git pull/fast-forward has happened since startup)."
```

**Two contributing factors:**
1. **No restart since `4201cbf` was committed.** Commits made after
   the most recent `systemctl --user restart empire-backend` are
   invisible to the startup record. This is the *normal* divergence:
   the file is a snapshot of process boot, not a moving target.
2. **The "backend_open_at_record_time: false" is itself a bug.**
   The startup health record was written with `backend_port: 8000,
   backend_open_at_record_time: false` — meaning the backend was
   NOT open at the moment the file was written. This is a recorded
   bug: the file says the backend wasn't up, even though the backend
   was up enough to write the file. Two seconds later (after the
   startup probes complete) the backend is fine; the record is
   pre-port-up.

**Q7 ANSWERED: yes, "startup differs" still reports, and it will keep
reporting as long as commits are made without a restart. The fix is
not "always restart" — it's either (a) update the file on git pull /
on every "commit succeeded" tool result, (b) expose the divergence
to MAX via the live brain context so the model is not in the dark
about it, or (c) hide the banner's "differs" when the freshness is
less than some threshold. Per dispatch principle D: the model must
be told.**

---

## Q9 (NEW). WHAT DOES THE ROSTER ACTUALLY LOOK LIKE?

**42 tools. Names with **bold** + one-line description. Sections in
order: Data → Action → Approval Gate → Communication → Research →
System → Presentation → Shell Execution → Autonomous → Reset → Payment.**

### Sections and tool positions (selected)

| # | Section | Tool | First-line description |
|---|---|---|---|
| 1 | Data | `search_quotes` | Search quotes by customer or status |
| 2 | Data | `get_quote` | Get full quote details |
| 3 | Data | `search_contacts` | Search customers, contractors, vendors |
| 4 | Data | `create_contact` | Add a new contact |
| 5 | Data | `get_tasks` | Get real tasks |
| 6 | Data | `get_desk_status` | Get task counts |
| 7 | Data | `search_conversations` | Search history across all channels |
| 8 | Action | `create_quick_quote` | **DEPRECATED.** Legacy JSON store |
| 9 | Action | `create_engine_quote` | **CANONICAL.** Uses pricing engine |
| 14 | Approval Gate | `approve_quote` | FOUNDER ONLY + PIN |
| 15 | Approval Gate | `reject_quote` | FOUNDER ONLY + PIN |
| 19 | Approval Gate | `run_desk_task` | Delegate to a desk |
| 20 | Approval Gate | `delegate_to_atlas` | Delegate a CODE task to Atlas |
| 25 | Communication | `svg_to_pdf` | Convert SVG → PDF |
| 26 | Communication | `sketch_to_drawing` | Generate architectural drawings |
| 31 | System | `get_system_stats` | Real CPU, RAM, disk, temperature |
| 32 | System | `get_weather` | Live weather data |
| 33 | System | `get_services_health` | Check which Empire services are running |
| **34** | **System** | **`empire_runtime_truth_check`** | **Inspect-only live runtime freshness check. Returns backend/frontend status, local/public API commit freshness, route health, restart_required, and stale/broken findings. It does not restart services.** |
| 35 | System | `empire_max_continuity_audit` | Inspect current MAX continuity handoff |
| 36 | System | `ollama_toggle` | Turn Ollama on or off |
| 37 | Presentation | `present` | Generate a presentation/report |
| **38** | **Shell Execution** | **`shell_execute`** | **Execute a safe, allowlisted shell command. Blocked patterns are rejected.** Lists 30+ allowed commands. |
| 39 | Autonomous | `dispatch_to_openclaw` | Send task to OpenClaw |
| 40 | Autonomous | `queue_openclaw_task` | Queue task (non-blocking) |
| 41 | Reset | `reset_max_state` | Reset MAX (FOUNDER ONLY) |
| 42 | Payment | `create_invoice_from_quote` | Quote → invoice |

### Key observations (Q9 finding)

- **`shell_execute` has its OWN section, visually prominent.** It is the
  ONLY tool with section-level heading emphasis. All other gated or
  destructive tools live inline within larger sections
  (`approve_quote`, `reject_quote`, `delegate_to_atlas`, `reset_max_state`,
  `create_invoice_from_quote`).
- **`shell_execute`'s description is short and powerful** (2 lines):
  "Execute a safe, allowlisted shell command. Blocked patterns are
  rejected." It does NOT say "founder PIN required" or "PIN-gated" or
  "not currently reachable from this surface." It also does NOT
  say what it can NOT do (e.g., cannot restart services, cannot fetch
  runtime truth — that's `empire_runtime_truth_check`).
- **`empire_runtime_truth_check`'s description is long and qualifying**
  (3 lines): "Inspect-only … It does not restart services." It is
  buried as the 4th tool in the "System Tools" section, after
  `get_services_health` which returns similar data.
- **There are TWO redundant tool entries** for the same job:
  `get_services_health` (#33, 2-line description, "check which
  services are running") and `empire_runtime_truth_check` (#34,
  3-line description, returns "backend/frontend status, local/public
  API commit freshness, route health, restart_required"). The
  inspect-only job is split across two tools; the broader one
  (`empire_runtime_truth_check`) is the one MAX needed on 8/20 and
  was not selected.
- **The roster orders by surface (data / action / approval / comm /
  research / system / presentation / shell / autonomous / reset /
  payment), not by frequency-of-use or by safety-class.** A founder
  asking "is the system healthy?" is led through Data → Action →
  Approval → Communication → Research → System Tools (4 items)
  before reaching Shell (own section, item 1 of 1). The
  inspect-only equivalent is item 4 of 8 in the System Tools
  section — not the first or most prominent item.

**Q9 ANSWERED: the roster is present and complete in the full prompt
(42 tools, sections, descriptions). What the dispatch hypothesised
("a roster that lists a PIN-gated tool first and buries the inspect-
only equivalent") is **partially** the case — `shell_execute` has
section-level emphasis that the inspect-only tools do not, and
`empire_runtime_truth_check` is buried 34th. But the bigger issue is
Q5 — the compact prompt omits the roster entirely.**

---

## Q10 (NEW). DOES THE ROSTER VARY BY PROVIDER?

**The roster itself does NOT vary by provider. What varies is whether
native function-calling tools are sent alongside.**

### Same roster, all providers
- `TOOLS_DOC` (`tool_executor.py:4474`) is a module-level string that
  `get_system_prompt()` interpolates into every prompt via
  `{_get_tools_doc()}` (`system_prompt.py:502`). Every call to
  `ai_router.chat(...)` passes the system prompt as a single string.
  All providers — xAI Grok, Anthropic Claude, Groq, Gemini, OpenAI,
  DeepSeek, Qwen, OpenRouter, OpenClaw, Ollama, MiniMax — receive the
  same text-block-format roster.
- Confirmed by inspecting `ai_router._try_provider_chat()` at
  `ai_router.py:907-985`: each branch passes the same `messages`
  (which contain `system_prompt`) to its provider-specific chat
  function. None of them re-derives the roster.

### Different: native tool definitions
- `XAI_TOOL_DEFINITIONS` (`tool_executor.py:431`) is a separate
  OpenAI-format tool definitions list, passed as the `tools=` parameter
  to the xAI chat call. It enables xAI's native `function_call`
  mechanism (in addition to the text-block format from TOOLS_DOC).
- It is **only** sent when the request includes an image:
  ```python
  # router.py:2486
  _tools = get_xai_tool_definitions() if request.image_filename else None
  ```
- For text-only requests, `tools=None` is passed. MAX must rely on the
  text-block format described in TOOLS_DOC.

### Different: provider's native tool support
- For MiniMax (`supplier_native_tools=False` per `_select_code_model()` at
  `code_task_runner.py:412`), the model MUST use the text-block
  format — MiniMax does not generate native function calls reliably.
  So MiniMax depends entirely on TOOLS_DOC being in the system prompt.
- For providers with native tool support, the model has two paths
  available. Some choose one, some the other, some both.

### Provider-by-provider observation
- 2026-08-19 successful `empire_runtime_truth_check` call: provider
  `openclaw`. Even `openclaw` was on text-block format (it has its own
  prompt assembly via `desk_prompt.py:62` and its own chat
  endpoint). MAX read TOOLS_DOC and emitted the right text block.
- 2026-08-20 failure: provider `minimax-MiniMax-M3`. MiniMax depends
  on TOOLS_DOC for tool awareness. If this turn was a compact prompt
  (Q5 finding — it almost certainly was), MAX had NO tool awareness
  and either (a) hallucinated tools from prior context or (b) used
  whatever tool name was most memorable from earlier turns
  (probably `shell_execute`, given Q9 prominence finding).

**Q10 ANSWERED: the roster itself is identical across providers. What
varies is the provider's native tool support and whether native
function definitions are sent (xAI, image-only). The relevance to
H52 is that MiniMax specifically depends on TOOLS_DOC being present,
and Q5's compact-prompt path strips it.**

---

## Q11 (NEW). IS THE ROSTER BUILT IN MORE THAN ONE PLACE?

**No duplication of the model's view of tools, but YES duplication of
"what tools MAX knows about" via two adjacent shapes:**

### Source A: TOOLS_DOC (the model's view)
- `tool_executor.py:4474` — module-level string. The 42-tool roster.
- Used by: `system_prompt.py:510` (`_get_tools_doc()`), `desk_prompt.py:62`
- Length: ~270 lines markdown.
- This is the ONLY string the model sees as its tool catalogue.

### Source B: XAI_TOOL_DEFINITIONS (native-function view, xAI only)
- `tool_executor.py:431` — list of dicts in OpenAI tool-call JSON schema.
- Used by: `tool_executor.get_xai_tool_definitions()` only, called by
  `router.py:2486` for image-attached requests.
- Contents: 2 entries (some tools).
- Disjoint from TOOLS_DOC for the model's purposes — only used by
  xAI's native `function_call` mechanism.

### Source C: TOOL_REGISTRY (control-plane view, NOT the model's view)
- `control_plane.py:482` — list of dicts with `key`, `description`,
  `runtime` (status). 9 entries. Different concept: surfaces,
  services, not tool calls.
- Used by: `control_plane.get_control_plane()` for the UI's status
  panel only. **Not in any prompt.**

### Source D: TOOL_REGISTRY (dispatcher view, runtime)
- `tool_executor.py:438` — `TOOL_REGISTRY = {}` — the runtime dictionary
  built by `@tool("name")` decorators. This is the actual executable
  set.
- Must stay in sync with TOOLS_DOC manually — if a tool is added via
  the decorator but not listed in TOOLS_DOC, the model can't see it;
  if a tool is in TOOLS_DOC but not registered, calls fail.

### Doctrinal reading
The risk per doctrine rule 12 is not "TOOLS_DOC duplicated"; it is
"TOOLS_DOC and TOOL_REGISTRY must agree, and they are maintained by
hand." Two `DRAWING_KEYWORDS` lists in this repo (the H60 issue)
already bit this codebase. Same class. Same risk.

Also note `operating_registry.json:171` — `autonomy_safety_notes`:
"Callable as `empire_runtime_truth_check`. Inspect-only; does not
restart services." — this is **a third description** of the same tool,
in JSON, only loaded into the operating registry context (system
prompt), not into TOOLS_DOC. Three descriptions of the same tool, in
three places, maintained by hand.

**Q11 ANSWERED: TOOLS_DOC is single-source for the model's view. But
the wider "what tools exist" answer is spread across TOOLS_DOC,
TOOL_REGISTRY (decorator runtime), TOOL_REGISTRY (control plane), and
`operating_registry.json` — at least four locations that must
agree.**

---

## Q12 (NEW). WHY DOES git_ops RETURN EMPTY SILENTLY?

**Two compounding causes.**

### Cause A: No explicit "empty" marker
```python
# tool_executor.py:5189-5200
result = subprocess.run(
    cmd_parts, cwd=repo,
    capture_output=True, text=True, timeout=30,
)
output = result.stdout + result.stderr
duration = int((_time.time() - start) * 1000)
success = result.returncode == 0
return ToolResult(tool="git_ops", success=success, result={
    "command": full_cmd, "output": output[:3000], "exit_code": result.returncode,
})
```

When `result.stdout == ""` AND `result.stderr == ""` AND
`result.returncode == 0`:
- `output = ""`
- `success = True`
- Returns `{"command": "git status", "output": "", "exit_code": 0}`

MAX sees success-with-empty-output. There is no way to distinguish
"git succeeded with no output" from "git succeeded and produced
output that was truncated" from "git didn't even reach the
repository." Per dispatch principle C ("a tool that fails must say
so"): a tool that runs to completion and produces nothing is not a
failure, but it is also not a verification — it is silence, and the
honesty layer must distinguish silence from "I checked and there's
nothing to report."

The `output[:3000]` truncation is silent too: a 5000-line `git log`
returns a string starting with "...", and the model gets no hint
that it is truncated.

### Cause B: hardcoded stale-fork cwd
```python
# tool_executor.py:5178
repo = os.path.expanduser("~/empire-repo")
```

**`~/empire-repo` is the stale fork.** H57 Phase 3 (commit `59d356d`)
was supposed to make all path resolution go through the canonical-root
resolver — `tool_safety.validate_path`, `_file_read`, `_shell_execute`
all do. **`_git_ops` does not.** git_ops runs in the wrong repo. So
even when the model says "git log" and gets output back, that output
is about a fork that was 1,825 files and 1,439 commits behind as of
8/17 — not the canonical repo the model is reasoning about.

`code_task_runner.py` uses `~/empire-repo` directly too (lines 409,
423), but the code-task lane just verified F1 against it and the
findings landed correctly anyway because tool_executor.py's
`_file_write`, `_file_read`, `_shell_execute` go through
`validate_path` first and reject `~/empire-repo` paths — so the
wrong cwd is hidden. git_ops is the one path that doesn't gate on
`validate_path`; it just `cwd=` and runs.

### Combined with Q5
On a turn that hits the compact prompt (no roster), MAX may
never even know `git_ops` exists. On a turn that hits the full
prompt (42-tool roster), MAX knows `git_ops` is at line ~4654 and
calls it. The call:
1. Runs in the stale fork (`~/empire-repo`)
2. Captures `output = stdout + stderr`
3. Returns success with empty output

MAX sees success with empty output, and the user sees a no-op. This
is the same failure class as the 5,931 verdict-without-evidence rows
fixed in the prior dispatch: a verdict that doesn't carry the
evidence it implies.

**Q12 ANSWERED: `git_ops` is silent on emptiness AND runs in the wrong
repo. Both must be fixed. Per dispatch principle C, an empty success
must self-report.**

---

## Summary of answers

| Q | Status | Headline finding | File:line |
|---|---|---|---|
| 5 (multi-variant) | ANSWERED | Two variants; compact omits the roster; the dispatch's three verification questions all hit the compact path | `system_prompt.py:32`, `:52`, `:117`, `:663`; `router.py:2469-2478`, `:3279-3288` |
| 6 (banner vs model) | ANSWERED | Banner reads from `get_control_plane()`; system prompt only sees ports + git log + tasks; the inspect-only truth tool exists but is not pointed at | `control_plane.py:611`; `system_prompt.py:519`; `runtime_truth_check.py:560-654`; `tool_executor.py:4609` |
| 7 (startup differs) | ANSWERED | YES — current `e854621` vs `4201cbf`; record is process-boot snapshot, no auto-refresh; pre-port-up field is itself buggy | `startup_health.py:46-81`; `control_plane.py:569`, `:602` |
| 9 (roster shape) | ANSWERED | 42 tools, sections; `shell_execute` has own section + 2-line description; `empire_runtime_truth_check` is 34th with 3-line qualifier; `get_services_health` duplicates the inspect-only job | `tool_executor.py:4474-4680` |
| 10 (provider variance) | ANSWERED | Roster identical across providers; what varies is native tool-call support; MiniMax depends on TOOLS_DOC (compact strips it) | `ai_router.py:907-985`; `router.py:2486`; `system_prompt.py:502` |
| 11 (multi-source) | ANSWERED | TOOLS_DOC is single-source for the model; BUT TOOLS_DOC + TOOL_REGISTRY (decorator) + TOOL_REGISTRY (control plane) + `operating_registry.json` describe the same tools in four places | `tool_executor.py:438`, `:4474`, `:431`; `control_plane.py:482`; `operating_registry.json:171` |
| 12 (git_ops empty) | ANSWERED | Two causes: no "empty" marker on success-with-empty-output; hardcoded `~/empire-repo` cwd (H57 missed `_git_ops`) | `tool_executor.py:5145-5206`, specifically `:5178`, `:5198` |

---

## Root-cause synthesis

The 8/20 failure was not a model failure. The model did exactly what
its tools told it to do:
- compact prompt → no roster → must rely on memory
- memory of prior roster → `shell_execute` is in its own section,
  short description, prominently placed → highly retrievable
- `shell_execute` is PIN-gated on this surface → block
- the model stopped (correct behaviour — DOCTRINE rule 31, "PIN
  approval never travels through chat or email")

The 8/19 success was not a model virtue. The model picked the right
tool because the right tool was available and the surface (openclaw)
either had a working unlock or, more likely, did not need it.

**The fix lives in the system prompt and tool roster, not in the
model.** Five places to change, in priority order:

1. **`is_ordinary_text_request`** — the cheap path is the wrong path
   for any question that could lead to a tool call. The dispatch's
   "be brief in ordinary chat" intent is fine, but the heuristic
   is too aggressive. Either broaden the patterns (e.g., "state",
   "system", "tool", "repo", "session", "what") or shrink the compact
   prompt's omission — keep a small tool roster with at minimum
   `empire_runtime_truth_check`, `get_services_health`,
   `get_system_stats`, `search_conversations`. (Per dispatch
   principle A.)

2. **Roster ordering and prominence** — inspect-only tools that
   answer the common questions rank ABOVE gated tools that cannot
   run. `empire_runtime_truth_check` and `get_services_health`
   should be in the FIRST section (System / Inspect), not buried
   mid-list. `shell_execute` should not have its own section. (Per
   dispatch principle A.)

3. **`shell_execute` annotation** — describe its gate in the tool
   description. "Founder PIN required via portal approval flow;
   not currently callable from this surface without unlock."
   Better: if there is no working unlock surface (H62), do not
   offer it at all until there is. (Per dispatch principle B.)

4. **`empire_runtime_truth_check` first-line purpose** — add to the
   system prompt's live brain context: "If asked about system
   state, freshness, restart-required, or commit divergence, call
   `empire_runtime_truth_check`." Same for `get_services_health`.
   (Per dispatch principle D.)

5. **`git_ops` fixes** — explicit "empty" marker (`"empty": True` on
   `output == "" and exit == 0`); cwd must go through the
   canonical-root resolver, not `os.path.expanduser("~/empire-repo")`.
   (Per dispatch principle C + H57 Phase 3 follow-through.)

The dispatch's three live verification questions are the test. If
the fix is correct, MAX answers them without naming the tool for the
founder, because the tool selection has become the obvious path.

---

## Stop point

Per dispatch: "🛑 STOP. Report the map. No fixes in Phase 1." Map
delivered above with file:line for every claim. Phase 2 (fix) waits
on founder review.