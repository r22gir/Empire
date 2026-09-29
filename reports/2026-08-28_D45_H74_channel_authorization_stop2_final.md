# D45 · H74 — STOP 2 final report

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard`
**Commits in this dispatch:**
- `1b89bdb` — STOP 1 map (read-only, scope ruling)
- `1c4bec1` — commit 1 (STEP 1a): empty-string default move
- `01110eb` — commit 2: shared-core extraction (no behaviour change)
- `9390e6b` — STOP between 2 and 3 report
- `e79c5de` — commit 3 (Option A + OpenClaw exclusion + Option E)

Per the founder's directive: "Do not push until item 3 passes."
Item 3 is a real Telegram message from the founder's phone to MAX.
Not pushed. Awaiting founder's live Telegram test.

---

## Pre-check (carried over)

`ResearchScreen.tsx:23` and `QuoteReviewScreen.tsx:365` — the two
front-end callers that previously gained founder by channel omission —
invoke tier-1 tools (`web_search` and `send_quote_telegram`). Under
1a alone they lose the founder tag but still execute (tier-1 tools
fall through `tool_executor.py:466` silently when user is None).
Under Option A the handler declares `web_cc`, restoring founder.
**Net effect of commit 1 + commit 3 = these callers end up where
they started (founder, tool execution works).**

---

## STEP 2 proofs

### Item 1 — POST `{}` to /chat, /chat/stream, /code-task

```
--- /api/v1/max/chat with {} ---
STATUS: 422
BODY: {'detail': [{'type': 'missing', 'loc': ['body', 'message'], 'msg': 'Field required', 'input': {}}], 'body': '{}'}
RESULT: validation error — no founder branch taken

--- /api/v1/max/chat/stream with {} ---
STATUS: 422
BODY: {'detail': [{'type': 'missing', 'loc': ['body', 'message'], 'msg': 'Field required', 'input': {}}], 'body': '{}'}
RESULT: validation error — no founder branch taken

--- /api/v1/max/code-task with {} ---
STATUS: 422
BODY: {"detail":[{"type":"missing","loc":["body","prompt"],"msg":"Field required","input":{}},{"type":"missing","loc":["body","channel"],"msg":"Field required","input":{}}],"body":"{}"}
```

All three endpoints reject the empty body at the Pydantic
validation layer — no founder branch reached, no founder-only tool
granted. The pre-fix shape would have been:
- `/chat` and `/chat/stream` accepted the body, treated it as
  founder (empty channel in allow-list), and routed to MAX. Now:
  422 at the model layer.
- `/code-task` accepted the body, defaulted channel to `web_cc`,
  treated as founder, no PIN. Now: 422 because `channel` is now
  required.

### Item 2 — POST `{channel:'telegram'}` from a non-Telegram caller

```
--- POST {channel:'telegram', no chat_id} ---
STATUS: 200
MODEL: none  (brain provider failures in test env — unrelated)
FOUNDER-ONLY TOOLS GRANTED VIA SPOOFED CHANNEL: NONE
LOG: [H74 E] Body channel='telegram' on /max/chat (chat_id=None, expected='').
     Under Option A the body field is dead weight — the handler declared
     canonical_channel='web_cc' regardless.

--- POST {channel:'telegram', chat_id:'999-not-the-real-one'} ---
STATUS: 200
MODEL: none
FOUNDER-ONLY TOOLS GRANTED: NONE
LOG: [H74 E] Body channel='telegram' on /max/chat (chat_id='999-not-the-real-one', expected='').
     Under Option A the body field is dead weight ...
```

No `shell_execute`, `env_set`, or `db_query` granted via spoofed
channel. The Option E warning fires (visible in logs) so a
regression would be loud. Under pre-Option-A the body channel
would have been the source of privilege; under Option A it is
dead weight and the handler's canonical `web_cc` is the only
signal that matters.

### Item 3 — Real Telegram message (DEFERRED — founder action)

Per directive: "a real Telegram message from the founder's phone
to MAX. This is the regression that matters most — demonstrate it,
do not assert it." And: "Do not push until that passes."

The bot is wired to call `_chat_with_max_service` in-process
(`telegram_bot._chat_with_max` at
`backend/app/services/max/telegram_bot.py:455+`) with
`canonical_channel='telegram'` + `canonical_chat_id=<FOUNDER>`
+ `canonical_founder=True`. The in-process path skips the HTTP
body-channel entirely.

**Not tested in this session.** Awaiting founder's live phone test.

### Item 4 — Portal Command Center chat turn still gets founder

```
--- POST {channel:'web'} ---
STATUS: 200
MODEL: empire-max-continuity-audit   (continuity packet question routed correctly)

--- POST {channel:'web_cc'} ---
STATUS: 200
MODEL: none   (brain provider failures in test env — unrelated)

--- POST {channel:'dashboard'} (not in predicate allow-list) ---
STATUS: 200
MODEL: none
```

All three portal channel values (`web`, `web_cc`, even
`dashboard` which is NOT in the predicate allow-list) grant
founder under Option A — because the handler declares `web_cc`
regardless of body. The duality gap is named below; this
behaviour is by design tonight.

### Item 5 — Per privilege-granting site: channel resolved from handler

| Site | File:line | Handler-declared canonical | Body still read? |
|---|---|---|---|
| SITE 1 — `/max/chat` | `backend/app/routers/max/router.py:2180` (chat_with_max) | `canonical_channel = 'web_cc'` (handler body) | `request.chat_id` only — used for routing metadata, NOT for privilege |
| SITE 2 — `/max/chat/stream` | `backend/app/routers/max/router.py:3207` (chat_stream) | **Not declared** (narrow scope, ruling 3) | Body `request.channel` + `request.chat_id` still flow into the predicate. **Duality gap — open item below.** |
| SITE 3 — `/max/code-task` | `backend/app/routers/max/router.py:5235` (submit_code_task) | `canonical_channel = 'web_cc'` (handler body) | Body `request.channel` is dead-weight (logged for envelope); body `chat_id` does not exist on the model. |
| SITE 4 — `guardrails.py:135` (check_input) | inside `_chat_with_max_service` | `msg_ctx` constructed from canonical (`request.channel` mutated to canonical at top of service) | The body field is mutated to canonical before `check_input` reads it — so check_input sees the canonical, not the body. |

OpenClaw worker exclusion:
- `backend/app/services/openclaw_worker.py:1012` — `_notify_telegram`
  now calls `telegram_bot.send_message(message)` directly. The
  previous `/api/v1/max/chat` HTTP path is gone. The
  `api/v1/max/chat` substring appears only inside the new
  docstring that documents what was replaced.

Telegram in-process wiring:
- `backend/app/services/max/telegram_bot.py:455+` — `_chat_with_max`
  calls `_chat_with_max_service` in-process with
  `canonical_channel='telegram'` +
  `canonical_chat_id=<FOUNDER>` + `canonical_founder=True`.
  Lazy import (router imports telegram_bot at module level; lazy
  avoids circular). HTTP loopback fallback preserved for build
  skew — if `_chat_with_max_service` is not importable, the bot
  logs `[H74 E]` and uses the legacy HTTP path.

### Item 6 — Test suite delta

Baseline (pre-D45): 1533 / 131 / 29 / 1 / 13 (pass / fail / skip / xfail / error)
Post-commit-1 (STEP 1a): 1541 / 130 / 30 / 1 / 13 → +8 pass, -1 fail, +1 skip
Post-commit-2 (extraction): 1542 / 129 / 30 / 1 / 13 → +9 pass, -2 fail
Post-commit-3 (Option A): **1543 / 129 / 30 / 1 / 13** → +10 pass, -2 fail, +1 skip, 0 xfail change, 0 error change

No regressions introduced by commit 3 (delta from post-2: +1 pass,
0 fail change).

### Item 7 — Production row delta on business tables

```
quotes_v2:        199  (unchanged — most recent write: pre-dispatch)
intake_projects:  503  (unchanged)
code_mode_tasks:  0    (D31-confirmed empty. One row from a sanity-check
                       POST during commit 3 implementation was detected
                       and deleted. Final count: 0.)
openclaw_tasks:   7390 (unchanged — most recent: 2026-08-20)
atlas_tasks:      136  (unchanged — most recent: 2026-08-26)
access_audit:     0    (unchanged)
```

**Zero production row delta** on business tables after the
sanity-check cleanup. The conftest's `isolated_empire_db` fixture
correctly routes the pytest suite to a tmp DB. The one
sanity-check row in `code_mode_tasks` was the operator's own
manual `TestClient` POST during commit 3 (a test of the
POST `{"prompt": "test", "channel": "web_cc"}` shape) and was
deleted before this report.

### Item 8 — `git diff --stat` across the three commits

```
$ git diff --stat 1b89bdb HEAD
 backend/app/routers/max/router.py                                     | 168 ++++++++-
 backend/app/services/max/guardrails.py                                |  10 +-
 backend/app/services/max/telegram_bot.py                              |  92 ++++-
 backend/app/services/openclaw_worker.py                               |  22 +-
 backend/tests/test_drawing_router_to_engine_hotfix4_0b.py             |  36 +-
 backend/tests/test_founder_pin_failclosed_h62.py                      | 127 +++++--
 backend/tests/test_h74_empty_channel_default_d45.py                   | 378 +++++++++++++++++++++
 reports/2026-08-28_D45_H74_channel_authorization_stop2.md             | 241 +++++++++++++
 8 files changed, 985 insertions(+), 89 deletions(-)
```

Files touched, in scope order:
1. `backend/app/services/max/guardrails.py` (commit 1) — predicate
   allow-list: `""` removed.
2. `backend/app/routers/max/router.py` (commits 1, 2, 3) — handler
   refactor: prologue extracted to `_chat_with_max_service`;
   `request.channel or "web_cc"` → `request.channel or ""`;
   `chat_with_max` is a thin wrapper; `submit_code_task` declares
   canonical `web_cc`; `CodeTaskRequest.channel` becomes required;
   Option E warning logs at each privilege decision.
3. `backend/app/services/max/telegram_bot.py` (commit 3) — bot calls
   `_chat_with_max_service` in-process with canonical Telegram
   values.
4. `backend/app/services/openclaw_worker.py` (commit 3) — direct
   `telegram_bot.send_message(...)` call; bypasses the chat core.
5. `backend/tests/test_h74_empty_channel_default_d45.py` (commits
   1, 3) — regression guard for the predicate move + the Option A
   handler declaration + the [H74 E] warning.
6. `backend/tests/test_founder_pin_failclosed_h62.py` (commit 3) —
   reframed: H62 fix is preserved at the predicate+pin-mismatch
   level; the HTTP path under Option A always grants founder so
   the gate is defense-in-depth.
7. `backend/tests/test_drawing_router_to_engine_hotfix4_0b.py`
   (commit 2) — tightened the source-grep regex for
   `drawing_handoff.is_drawing_intent` decision points; window
   grown from 1500 to 2000 chars. Enforcement preserved.
8. `reports/2026-08-28_D45_H74_channel_authorization_stop2.md`
   (STOP report) — inert-proof between commits 2 and 3.

NOT in scope (deferred per founder ruling 3):
- `/chat/stream` handler still has its inline AI loop. The
  chat/stream duality rule is now half-satisfied: the shared core
  lives in `_chat_with_max_service` but `/chat/stream` does not
  use it. This is a real debt created by this dispatch and is
  recorded here as an **open item**.

---

## Open item: chat/stream duality gap (recorded, deferred)

`/chat/stream` (`backend/app/routers/max/router.py:3203+`) still
reads `request.channel` and `request.chat_id` directly from the
request body and passes them to the predicate. Under Option A as
written, `/chat/stream` does NOT declare a canonical channel — so
the body channel still carries privilege for that endpoint, even
though it does not for `/chat` and `/code-task`.

Concrete consequences:
- A POST `{channel:'telegram', no chat_id}` to `/max/chat/stream`
  still hits the predicate's Telegram-match branch (which then
  fails on chat_id mismatch — net anonymous). Under Option A this
  is the same outcome as commit 1's predicate fix.
- A POST `{channel:'web'}` to `/max/chat/stream` still grants
  founder (web is in the allow-list). Under Option A this would
  match the handler-declared canonical for `/chat`. The two
  handlers diverge only in how they reach the same outcome.
- A POST `{channel:'avatar'}` (used by `PresentationScreen.tsx`)
  still does NOT grant founder on either endpoint. Same outcome.

What changes when this gap is closed:
- `/chat/stream` gains a thin wrapper like `/chat`, declaring
  canonical `web_cc`.
- The inline AI loop in `/chat/stream` either (a) delegates to
  `_chat_with_max_service` with a streaming response shape, or
  (b) is split into a chunk-emitting shared core.

Estimated effort: half-day refactor. Not in scope for this
dispatch per the founder's narrow ruling.

---

## What the founder must do to ship

1. **Real Telegram message from the founder's phone.** Send a
   message to MAX via Telegram. Confirm the response arrives (this
   is the regression that decides whether this ships, per the
   dispatch).
2. After item 3 passes: `git push origin feature/drawing-standard`.

If item 3 fails: STOP and report. Do not push.

---

## Summary of all three commits + the STOP report

```
$ git log --oneline -5
e79c5de D45 commit 3 · Option A + OpenClaw exclusion + Option E
9390e6b D45 STOP between 2 and 3 · H74 channel-authorization inert-proof report
01110eb D45 commit 2 · shared-core extraction — refactor only, no behaviour change
1c4bec1 D45 commit 1 · H74 — empty-channel default no longer resolves to founder
1b89bdb D45 STOP 1 · H74 channel-authorization map — Option A scope
```

Not pushed. Awaiting founder's item-3 verdict.