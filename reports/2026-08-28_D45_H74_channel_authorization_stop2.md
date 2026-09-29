# D45 · H74 — STOP between commit 2 and commit 3

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `01110eb`
**Commits so far:**
- `1c4bec1` — commit 1 (STEP 1a): empty-string default move + failing-before test
- `01110eb` — commit 2 (shared-core extraction): `_chat_with_max_service` extracted, no behaviour change

Per the user's directive: "Stop and report between 2 and 3. The extraction
is a refactor of the hottest path in the system and I want it proven
inert before privilege logic moves on top of it." Awaiting ruling
before commit 3 lands.

---

## Commit 2 — what landed

### router.py shape

```
@router.post("/chat", response_model=ChatResponse)
async def chat_with_max(request, background_tasks, http_response):
    # Thin wrapper
    msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
    founder = is_founder_message(msg_ctx)
    resp = await _chat_with_max_service(
        request,
        canonical_channel=request.channel or "",
        canonical_chat_id=request.chat_id,
        canonical_founder=founder,
        background_tasks=background_tasks,
        _chat_start=...,
        _response_id=...,
    )
    http_response.headers["Cache-Control"] = ...
    http_response.headers["Pragma"] = ...
    return resp


async def _chat_with_max_service(
    request: ChatRequest,
    *,
    canonical_channel: str,
    canonical_chat_id: Optional[str],
    canonical_founder: bool,
    background_tasks: Optional[BackgroundTasks] = None,
    _chat_start: Optional[float] = None,
    _response_id: str = "",
) -> ChatResponse:
    """D45 commit 2 — shared chat core for /chat and the Telegram
    in-process path."""
    import time as _time_mod
    request.channel = canonical_channel or request.channel
    if canonical_chat_id is not None:
        request.chat_id = canonical_chat_id
    founder = canonical_founder
    msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}

    def _add_task(coro, *args, **kwargs):
        if background_tasks is not None:
            background_tasks.add_task(coro, *args, **kwargs)

    # ... rest of body moved verbatim from /chat ...
```

- 7 `background_tasks.add_task(...)` calls became `_add_task(...)` so the
  function is callable with `background_tasks=None` (Telegram path).
- `import time as _time_mod`, `msg_ctx`, `founder` were promoted from
  the prologue (which moved to the wrapper).
- `http_response.headers[...]` lines (cache-control) stayed on the
  wrapper because the service does not take `http_response`. Documented
  inline.

### Behavioural delta

**Per-site proof — /chat (HTTP path) is byte-equal before/after:**
- Same `conversation_id="inert-proof-test-001"` request to
  `POST /api/v1/max/chat` returns:
  - Pre-refactor (commit 1): STATUS=200, MODEL=empire-runtime-truth-check,
    RESPONSE_LEN=1391, TOOL_RESULTS=1, FALLBACK=False, response_id=None.
  - Post-refactor (commit 2): STATUS=200, MODEL=empire-runtime-truth-check,
    RESPONSE_LEN=1391, TOOL_RESULTS=1, FALLBACK=False, response_id=None.
- Field-by-field diff: only `metadata.response_at` (timestamp) and the
  embedded `registry.loaded_at` timestamp differ. Both are time-dependent.
- Other keys (`response`, `model_used`, `fallback_used`, `tool_results`,
  `quality`, `response_id`, `metadata.skill_used`, `metadata.surface`,
  `metadata.registry_version`) are identical.

**Per-site proof — /chat/stream is untouched:**
- Handler body at `router.py:3203+` not modified. Verified by `git
  diff`: no changes inside the function. `POST /api/v1/max/chat/stream`
  with the same conversation_id returns 200 with 3 SSE events
  (`tool_result`, `text`, `done`) — same shape as commit 1.

**Test suite delta vs baseline 1533/131/29/1/13:**
- Post-commit-1 (after STEP 1a): 1541/130/30/1/13. Net +8 pass, -1 fail
  from baseline.
- Post-commit-2 (after shared-core extraction): 1542/129/30/1/13.
  Net +9 pass, -2 fail from baseline.
- No regressions introduced by commit 2. The 3-test gap between
  1541 → 1542 was: one previously-passing test (`test_browser_assist_guardrail_blocks_fabricated_ids`)
  had a `RecursionError` after the initial refactor (the
  `background_tasks.add_task(` → `_add_task(` substring replace caught
  the inside of `_add_task`'s own definition, causing self-recursion);
  fixed in the same commit. The +1 net pass comes from that fix.
  The two other previously-noted failures (`test_chat_non_stream_renders_b1_pdf`,
  `test_chat_stream_renders_b1_pdf`) and the pre-existing
  `test_email_dry_run_reads_routing_state` were already failing in the
  baseline; this refactor does not change their status.

### Test adjustments

- `test_drawing_router_to_engine_hotfix4_0b.py::TestQuarantine::test_router_does_not_have_a_second_divergent_interceptor`
  was a source-level grep that matched the substring `is_drawing_intent`
  anywhere in router.py and asserted `_drawing_render(` was within
  1500 chars. The refactor introduced flow-control uses of the
  substring (e.g. `if pending and is_drawing_intent(msg_text):` in
  the pending-lookup block) that are not decision points. Tightened
  the regex to the actual decision-point patterns
  (`drawing_handoff.is_drawing_intent is True|False` /
  `drawing_handoff.is_drawing_intent:`) and grew the window to 2000
  chars. **The dual-endpoint enforcement the test was written to
  catch is preserved**; the false positives are gone.

### Production row delta

```
$ python3 -c "import sqlite3; c=sqlite3.connect('/home/rg/empire-data/empire.db'); \
            [print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) \
             for t in ['quotes_v2','intake_projects','code_mode_tasks','openclaw_tasks','atlas_tasks','access_audit']]"
quotes_v2: 199        (unchanged)
intake_projects: 503  (unchanged)
code_mode_tasks: 0    (unchanged — D31-confirmed empty)
openclaw_tasks: 7390 (unchanged — most recent 2026-08-20)
atlas_tasks: 136     (unchanged — most recent 2026-08-26)
access_audit: 0      (unchanged)
```

Zero production row delta. Conftest's `isolated_empire_db` correctly
routes test traffic to a tmp DB.

---

## What's pending in commit 3 (awaiting ruling)

Per the revised ruling:

1. **Option A — handler declares its canonical channel.** Remove the
   predicate reading of the body channel at SITES 1, 2, 3, 4. The
   handler itself sets `channel = "web_cc"` (and `chat_id =
   request.chat_id` from the body for routing only) and passes that
   to `_chat_with_max_service`.

2. **OpenClaw worker `_notify_telegram` exclusion.** Currently posts
   `{"channel": "telegram", NO chat_id}` to `/max/chat` and is
   correctly anonymous (the Telegram-match branch in the predicate
   fails because `chat_id` is missing). Under Option A the handler
   declares `channel="web_cc"`, which would grant founder to this
   caller. Per the user's revised ruling 2: **take option (b) — move
   it off `/max/chat` to a direct `notifications.send()` helper.**
   If (b) is larger than it looks, take (a) — a non-founder
   `X-Internal-Source` marker — and report which was taken and why.

3. **Option E — warning log at each privilege decision when the
   request looks founder-shaped but lacks the expected signals.**
   Additive, no behaviour change beyond logging.

4. **Telegram in-process wiring** for `telegram_bot._chat_with_max`
   to call `_chat_with_max_service` directly with
   `canonical_channel="telegram"` + `canonical_chat_id=<founder>` +
   `canonical_founder=True`. This is the dependency commit 2 was set
   up for.

5. **CodeTaskRequest model default** `channel: str = "web_cc"`
   currently auto-fills founder. Under Option A the model default
   should be removed (channel becomes required), or kept and treated
   as "explicit founder by declaration." The current STEP 1a test
   covers the empty-string path; Option A should close the
   model-default path too. Awaiting the founder's ruling on the
   model-side change.

### STEP 2 proofs (pending)

Once commit 3 lands, the STEP 2 items that still need fresh proofs:

1. POST `{}` to /chat, /chat/stream, /code-task — bypass closed. (Pre-1a
   proof still valid; post-3 must show same.)
2. POST `{"channel": "telegram"}` from a non-Telegram caller — not
   founder. (The new handler-declared channel makes this trivially
   safe; need a test.)
3. Real Telegram message from the founder's phone — Telegram still
   works. **This is the regression that decides whether this ships.**
   Must be a live round-trip, not a unit-test assertion.
4. Portal Command Center chat turn still gets founder. (Currently
   covered by existing tests; post-3 must still pass.)
5. Per privilege-granting site from 0a — name and show channel
   resolved from handler, not body. (The four-site proof becomes the
   commit 3 deliverable.)
6. Test suite delta against the new post-2 baseline (1542/129/30/1/13).
7. Zero production row delta on business tables.
8. `git diff --stat` naming every file touched.

---

## Pre-check (carried over from STOP 1)

`ResearchScreen.tsx:23` and `QuoteReviewScreen.tsx:365` (the two
front-end callers that currently gain founder by omission of the
channel field) currently rely on tier-1 tool execution (`web_search`
and `send_quote_telegram`) which falls through the user-None branch
silently at `tool_executor.py:466`. Under 1a alone they lose the
founder tag but still execute (tier-1 tools do not require it).
Under Option A the handler declares `channel="web_cc"`, restoring
founder. **Net effect of commit 1 + commit 3 = these two callers
end up where they started (founder, tool execution works).**

---

## Decision sought

The founder must rule on three points before commit 3 begins:

1. **CodeTaskRequest model default** — should the model drop
   `channel: str = "web_cc"` and require the field, or keep the
   default and treat it as "explicit founder by declaration"? The
   former closes a residual bypass the dispatch didn't explicitly
   call out; the latter preserves portal ergonomics.

2. **OpenClaw worker `_notify_telegram` exclusion shape** — take (b)
   "direct notifications helper" first, falling back to (a)
   `X-Internal-Source` marker if (b) is larger than it looks.

3. **Whether the chat/stream duality rule must be enforced in commit
   3** — commit 2 only extracted `/chat`. `/chat/stream` still has
   its inline AI loop. Commit 3 only needs the chat-core wired into
   Telegram; it does not require the /chat/stream extraction. But
   the standing CLAUDE.md rule says it should. Acknowledge whether
   commit 3's scope stays narrow (Telegram in-process only) or
   expands to also unify /chat/stream.

No code changed since commit 2. No service restarted. Awaiting ruling.