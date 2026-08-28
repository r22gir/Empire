# D45 · H74 Channel-Authorization Map (Option A scope)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `639eaf40`
**H-number:** **H74** (carried from D31, no new number)
**Phase:** STEP 0 — READ-ONLY. No code edits, no config edits, no service restarts.

This dispatch answers the five 0a–0e questions for **Option A**
(handler-declares-channel). It does not propose a fix; it sizes the fix.
The 🛑 STOP 1 ask: founder's ruling on (a) any caller that would lose
founder status under Option A and (b) the Telegram in-process path,
which is larger than the dispatch text suggests.

---

## 0a · The eight numbered sites, current line numbers and disposition

The dispatch cites eight numbered lines plus "any site those line
numbers have drifted from." Line numbers below are taken from the
working tree at `639eaf40`. None have drifted from D31.

### SITE 1 — `backend/app/routers/max/router.py:2169` (`/chat` handler)

```python
2162 @router.post("/chat", response_model=ChatResponse)
2163 async def chat_with_max(request: ChatRequest, background_tasks: BackgroundTasks, http_response: Response):
...
2168     msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
2169     founder = is_founder_message(msg_ctx)
```

- `channel` source: **request body field** (`ChatRequest.channel`,
  `router.py:569` — `Optional[str] = None`). `request.channel or ""`
  means a missing key passes as `""`.
- `founder=True` privilege: **YES.** Full tool-execution bypass
  (`execute_tool` at `tool_executor.py:459-461` skips the
  `check_permission` gate and stamps `_founder=True` for the tool
  handlers); prompt-injection and blocked-topic guards are skipped
  (`guardrails.py:135-147`).
- Unauthenticated reachability: **YES** — route is registered with no
  `Depends(...)` (per D31 §0b).
- **Disposition: PRIVILEGE-GRANTING. In scope.**

### SITE 2 — `backend/app/routers/max/router.py:3207` (`/chat/stream` handler)

```python
3203 @router.post("/chat/stream")
3204 async def chat_stream(request: ChatRequest):
...
3206     msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
3207     founder = is_founder_message(msg_ctx)
```

- `channel` source: **request body field** (same `ChatRequest` model).
- `founder=True` privilege: **YES.** Same privilege flow as SITE 1.
- Unauthenticated reachability: **YES.**
- **Disposition: PRIVILEGE-GRANTING. In scope.**

### SITE 3 — `backend/app/routers/max/router.py:5162` (`/code-task` handler)

```python
5142 class CodeTaskRequest(BaseModel):
5143     prompt: str
5144     pin: str = ""
5145     channel: str = "web_cc"
...
5161     msg_ctx = {"channel": request.channel or "web_cc"}
5162     founder = is_founder_message(msg_ctx)
5163     if not founder:
5164         # H62 FIX (2026-08-22): empty default — pre-fix this was "7777" (privilege-escalation literal)...
5165         founder_pin = os.getenv("FOUNDER_PIN", "")
```

- `channel` source: **request body field** (`CodeTaskRequest.channel`
  at `router.py:5145` — default `"web_cc"`, NOT Optional). Note the
  default is `"web_cc"` at the model, then `request.channel or "web_cc"`
  at the call site — the same effective default.
- `founder=True` privilege: **YES.** PIN bypass on a code-task
  submission. `code_task_runner.submit(..., founder=founder)` at
  `router.py:5182` dispatches a `CodeTask(founder=True)` to
  Atlas/CodeForge execution (the highest privilege downstream).
- Unauthenticated reachability: **YES.** PIN is the only gate when
  `founder=False`; when `founder=True` the PIN is bypassed.
- **Disposition: PRIVILEGE-GRANTING. In scope. The dispatch's
  standing rule applies: "Treat /max/chat as at least as privileged"
  — code-task sits above /max/chat in the privilege table, but the
  bypass mechanism is identical.**

### SITE 4 — `backend/app/services/max/guardrails.py:135` (`check_input`)

```python
133 def check_input(text: str, message_context: dict = None) -> Tuple[bool, str]:
134     text_lower = text.lower()
135     founder = is_founder_message(message_context or {})
```

- `channel` source: dict key `"channel"` from `message_context`. At the
  router call sites the dict is built from the request body field —
  SITE 1, 2, 3 each pass through this same gate.
- `founder=True` privilege: **YES, but weakest.** Skips the
  prompt-injection block and blocked-topic block at
  `guardrails.py:135-147`. **No tool bypass, no PIN bypass.**
- Unauthenticated reachability: N/A — internal Python, runs inside the
  same handlers.
- **Disposition: PRIVILEGE-GRANTING. In scope.**

### SITE 5 — `backend/app/services/max/tool_executor.py:449-455` (the line `454` is inside a docstring)

```python
449 def execute_tool(tool_call: dict, desk: Optional[str] = None,
450                  access_context: Optional[dict] = None,
451                  founder: bool = False) -> ToolResult:
452     """Dispatch and execute a tool call (with tier gating and access control).
453
454     Args:
455         founder: If True, skip all PIN/access checks. The caller (router) has
456                  already verified this is the founder via is_founder_message().
457     """
```

- **No `is_founder_*` call here.** The `founder` parameter is the
  propagated result of SITE 1 / SITE 2 / SITE 3 — it does not consult
  `channel` itself. The line 454 the dispatch cites is **inside a
  docstring**, not an executable statement. (VERIFIED — read directly.)
- **Disposition: NOT a privilege gate. NOT in scope.** A fix that
  covers SITES 1–4 covers SITE 5 by construction (the value that
  arrives here is whatever SITES 1–4 decided).

### SITE 6 — `backend/app/services/max/operating_registry.py:126-134`

```python
126 def _normalize_prompt_channel(channel: str | None) -> str:
127     ch = (channel or "web").lower()
128     if ch in {"web", "web_cc", "dashboard", "command_center", "mobile_browser"}:
129         return "web_chat"
130     if ch == "telegram":
131         return "telegram"
132     if ch == "email":
133         return "email"
134     return ch
```

- The function is consumed at `:140` to label the prompt's
  operating-truth section. **No `is_founder_*` call. No privilege
  decision.**
- The allow-list here is **larger** than the founder predicate's
  allow-list (`mobile_browser` and `dashboard` are added). This is
  cosmetic — both inputs collapse to `"web_chat"`.
- **Disposition: NOT a privilege gate. Label-reading only. The
  dispatch's rule "label-reading sites are not in scope" applies.
  Untouched by Option A.**

### SITES 7–8 — `backend/app/services/max/unified_message_store.py:217-220` and `:222-226`

```python
217 def _normalize_channel(self, channel: str | None) -> str:
218     if channel in {"web", "web_cc", "dashboard", "command_center", "mobile_browser", "studio_browser"}:
219         return "web_chat"
220     return channel or "system"
221
222 def _channel_aliases(self, channel: str | None) -> list[str]:
223     normalized = self._normalize_channel(channel)
224     if normalized == "web_chat":
225         return ["web_chat", "web", "web_cc", "dashboard", "command_center", "mobile_browser", "studio_browser"]
226     return [normalized]
```

- Both functions are consumed by cross-channel history search. **No
  `is_founder_*` call. No privilege decision.** Note the `studio_browser`
  addition over D31's quoted set — D31 §0b quoted 5 keys; the actual
  set at `:218` is 6.
- **Disposition: NOT privilege gates. Label-reading only. Untouched
  by Option A.**

### Coverage gap (the 4-vs-9 question D31 §0f papered over)

- D31 §0f's Options A–E each claim "covers all four sites." The four
  are the privilege-granting SITES 1–4 above. **Options A–E
  implicitly admit they do NOT touch SITES 5–8.** That is correct —
  SITES 5–8 are not privilege gates, so they should not be touched.
- The 9-vs-4 gap is therefore: **5 of the 9 are label-reading or
  docstring noise, and only 4 are privilege-granting.** The fix scope
  is the 4, not the 9.

---

## 0b · Both predicates — files, lines, callers

### Predicate A — `guardrails.is_founder_message`

- File: `backend/app/services/max/guardrails.py:96-112`.
- Source:
  ```python
  96 def is_founder_message(message_context: dict) -> bool:
   ...
  102     channel = message_context.get("channel", "")
  103     # Command Center (any variant) = always founder
  104     if channel in ("web", "web_cc", "cc", "command_center", "command-center", ""):
  105         return True
  106     # Telegram: match by chat_id
  107     if not _FOUNDER_CHAT_ID:
  108         return False
  109     chat_id = str(message_context.get("chat_id", ""))
  110     if channel == "telegram" and chat_id == _FOUNDER_CHAT_ID:
  111         return True
  112     return False
  ```
- Callers (the grep `is_founder_message`):
  ```
  $ grep -rn "is_founder_message" --include=*.py backend/
  backend/app/services/max/guardrails.py:96:def is_founder_message(message_context: dict) -> bool:
  backend/app/services/max/guardrails.py:135:    founder = is_founder_message(message_context or {})
  backend/app/routers/max/router.py:22:from app.services.max.guardrails import check_input, sanitize_output, sanitize_output_streaming, SAFE_REFUSAL, is_founder_message, check_gpu_safety, GPU_VERIFICATION_COMMANDS
  backend/app/routers/max/router.py:2169:    founder = is_founder_message(msg_ctx)
  backend/app/routers/max/router.py:3207:    founder = is_founder_message(msg_ctx)
  backend/app/routers/max/router.py:5162:    founder = is_founder_message(msg_ctx)
  backend/tests/test_founder_pin_failclosed_h62.py:103:    bypass PIN via is_founder_message()."""
  ```
- Callers of `is_founder_message` at runtime (4 sites):
  - `router.py:2169` (SITE 1, privilege-granting)
  - `router.py:3207` (SITE 2, privilege-granting)
  - `router.py:5162` (SITE 3, privilege-granting)
  - `guardrails.py:135` (SITE 4, privilege-granting — internal to all
    three router paths above; they pass `msg_ctx` into `check_input`)
- `tool_executor.py:454` is a docstring substring only, not a runtime
  caller (VERIFIED — see SITE 5).
- `test_founder_pin_failclosed_h62.py:103` is in a test docstring.

### Predicate B — `founder_auth.is_founder_channel` (and `get_access_level`)

- File: `backend/app/services/max/founder_auth.py` (the whole file —
  25 lines).
- Source:
  ```python
   7 FOUNDER_TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_FOUNDER_CHAT_ID", "")
   9 def is_founder_channel(channel: str, user_context: dict = None) -> bool:
  10     """web_cc = always founder. telegram + founder chat ID = always founder."""
  11     if channel in ("web_cc", "web", "cc", "command_center", "command-center", ""):
  12         return True
  13     if channel == "telegram" and user_context:
  14         chat_id = str(user_context.get("chat_id", ""))
  15         if chat_id and chat_id == FOUNDER_TELEGRAM_CHAT_ID:
  16             return True
  17     return False
  18
  19 def get_access_level(channel: str, user_context: dict = None) -> str:
  20     if is_founder_channel(channel, user_context):
  21         return "founder"
  22     if user_context and user_context.get("pin_verified"):
  23         return "authenticated"
  24     return "anonymous"
  ```
- Callers (the grep):
  ```
  $ grep -rn "founder_auth\|get_access_level\|is_founder_channel" --include=*.py backend/
  backend/app/services/max/founder_auth.py:9:def is_founder_channel(channel: str, user_context: dict = None) -> bool:
  backend/app/services/max/founder_auth.py:19:def get_access_level(channel: str, user_context: dict = None) -> str:
  backend/app/services/max/founder_auth.py:20:    if is_founder_channel(channel, user_context):
  backend/app/services/max/access_control.py:52:        from app.services.max.founder_auth import FOUNDER_TELEGRAM_CHAT_ID
  backend/app/services/max/access_control.py:53:        if channel == "telegram" and str(chat_id or "") == FOUNDER_TELEGRAM_CHAT_ID:
  ```
- Live callers of `is_founder_channel`: **zero.** The only caller is
  `get_access_level`'s body at line 20. `get_access_level` itself has
  zero callers in the entire tree (per D32 §2 VERIFIED-dead finding).
- `access_control.py:52` imports the constant `FOUNDER_TELEGRAM_CHAT_ID`
  only, not the predicate. `access_control.py:53` is a parallel
  implementation of the Telegram-founder check, not a call to the
  predicate.
- **Disposition: predicate B is dead code. A fix covering predicate A
  alone is a fix.**

### Why both predicates matter even when one is dead

`founder_auth.py` exports `FOUNDER_TELEGRAM_CHAT_ID` (the env-derived
  string `TELEGRAM_FOUNDER_CHAT_ID`) and is imported by `access_control.py:52`
  for its own parallel check. The dead predicate `is_founder_channel`
  is one of two parallel implementations of the same allow-list + Telegram
  match logic. Under Option A the founder allow-list no longer exists in
  the predicates (the route declares the channel), so:

- The whole `is_founder_channel` function becomes unreachable.
- `get_access_level` becomes unreachable.
- The `FOUNDER_TELEGRAM_CHAT_ID` constant stays useful for the
  Telegram bot's internal caller path (1c) and for `access_control.py`'s
  parallel check at `:53` (which is **not** in scope and must keep
  working as-is — see "Additive where possible").

---

## 0c · The empty-string default — verbatim and reach paths

### Predicate A — `guardrails.py:102-105`

```python
102     channel = message_context.get("channel", "")
103     # Command Center (any variant) = always founder
104     if channel in ("web", "web_cc", "cc", "command_center", "command-center", ""):
105         return True
```

The empty string is the second-to-last element of the allow-list tuple.
`message_context.get("channel", "")` returns `""` when the key is
absent — there is no `None` check, no `not channel` guard, no
"unrecognised channel" branch.

### Predicate B — `founder_auth.py:11-12`

```python
11     if channel in ("web_cc", "web", "cc", "command_center", "command-center", ""):
12         return True
```

Same shape. `""` is in the allow-list.

### Paths that reach the founder branch with `channel` absent

Every router call site uses `request.channel or ""` and then
`is_founder_message(message_context)`. A missing `channel` key:

- `router.py:2168` → `msg_ctx["channel"] = ""` → predicate A →
  `channel in (..., "")` → True.
- `router.py:3206` → same.
- `router.py:5161` → `msg_ctx["channel"] = "web_cc"` (because the model
  default at `:5145` is `"web_cc"`, and `request.channel or "web_cc"`
  catches None). **Note: `CodeTaskRequest.channel` is `str = "web_cc"`,
  not Optional, so the empty default at A is unreachable for this
  handler — but `"web_cc"` IS in the allow-list, so the effect is the
  same: the default is founder.**
- `guardrails.py:135` (internal — receives the same `msg_ctx` dict).

### The fix shape (per dispatch standing rules)

Per STEP 1a: "Missing or unrecognized `channel` resolves to anonymous.
Both predicates. No exceptions, no allowlist of empty values." This
collapses the `""` membership to `False` in both predicates. It does
NOT require touching the router; it is one line in each predicate plus
a regression test.

---

## 0d · Telegram's call path today

### Transport and payload (current)

`backend/app/services/max/telegram_bot.py:455-487`:

```python
455 async def _chat_with_max(
456     self, text: str, image_filename: Optional[str] = None, chat_id: Optional[str] = None,
457         user_meta: Optional[Dict[str, Any]] = None,
458 ) -> tuple[str, str, list]:
 ...
 463         cid = str(chat_id or self.founder_chat_id or "default")
 464         history = _get_history(cid)[-_MAX_HISTORY:]
 465         try:
 466             payload: Dict[str, Any] = {"message": text, "history": history, "conversation_id": f"telegram-{cid}", "channel": "telegram", "chat_id": cid}
 467             if image_filename:
 468                 payload["image_filename"] = image_filename
 469             async with httpx.AsyncClient(timeout=120.0) as client:
 470                 resp = await client.post("http://localhost:8000/api/v1/max/chat", json=payload)
 471                 if resp.status_code == 200:
 472                     data = resp.json()
 ...
```

- Transport: HTTP POST to `http://localhost:8000/api/v1/max/chat` over
  loopback. `httpx.AsyncClient(timeout=120.0)`.
- Payload keys: `message`, `history`, `conversation_id="telegram-<cid>"`,
  `channel="telegram"`, `chat_id=<cid>` (always set, even though the
  front-end sends it as Optional).
- `chat_id` value: `str(chat_id or self.founder_chat_id or "default")`
  — for a real founder message this is the integer `TELEGRAM_FOUNDER_CHAT_ID`
  stringified.

### Bot process topology

- **No `empire-telegram-bot.service`** runs:
  ```
  $ systemctl --user list-units --type=service --all | grep -iE "telegram|empire"
  cloudflared-apex-public.service    loaded active running ...
  cloudflared-empire-main.service    loaded active running ...
  empire-backend.service             loaded active running ...
  empire-openclaw.service            loaded active running ...
  empire-portal.service              loaded active running ...
  ```
- **The bot runs in-process** inside the backend. `backend/app/main.py:406-415`:
  ```python
  406     # Telegram Bot — webhook mode (avoids Conflict error from polling)
  407     try:
  408         from app.services.max.telegram_bot import telegram_bot
  409         if telegram_bot.is_configured:
  410             asyncio.create_task(telegram_bot.start_webhook_mode())
  411             print("✓ Telegram Bot: starting in webhook mode")
  ```
  This runs as part of the backend's startup hook. The bot instance is
  imported in many backend-internal modules already (scheduler.py:85,
  monitor.py:98, control_plane.py:226, task_pipeline.py:559,
  tool_executor.py:755, desks/base_desk.py:154, desks/desk_scheduler.py:250+
  and others) — the singleton `telegram_bot` is reachable from any
  in-process caller.
- A standalone launcher exists at `backend/run_telegram_bot.py` but is
  **not the active path** in production.

### What an in-process call would need

The dispatch anticipates an in-process call from
`telegram_bot._chat_with_max` to the MAX service directly. To do that,
the handler body at `router.py:2163-...` (`chat_with_max`) must be
callable from Python without going through the HTTP layer. Two
options:

1. **Extract a shared core function** from `chat_with_max` (the
   `/chat` handler) and call it directly. This is the clean shape,
   and it would also honor the CLAUDE.md "Chat/stream duality" rule
   (the streaming handler at `router.py:3203` is currently a separate
   inline copy, not a shared function — see `runtime_truth_enforcer.py:1019-1021`
   documenting the same point).
2. **Bypass the route layer entirely** and call underlying helpers
   directly (the `_process_chat_message` style, if such a function
   exists — it does not appear to).

### Why this is larger than the dispatch text suggests

The dispatch says "one caller, one file." It is one caller in
`telegram_bot.py`, but the file it lands in (`router.py`) does not
expose a callable core. The handler body is ~470 lines and contains
inline history truncation, prompt-injection check, sanitizer check,
tool dispatch, response sanitization, telemetry — none of it is
extracted. Extracting a core means:

- Refactor `chat_with_max` to delegate to a new
  `_process_chat_message(...)` async function.
- Refactor `chat_stream` to call the **same** function (this is the
  Chat/stream-duality rule that already applies; the dispatch
  acknowledges it for `/max/chat/stream`).
- Wire `telegram_bot._chat_with_max` to call the new function with
  the `channel="telegram"` and `chat_id=<cid>` baked in (Option A
  shape — the function declares its own canonical channel internally).
- The streaming-response shape (`StreamingResponse` with SSE chunks)
  cannot be reused for the bot, which wants a non-streaming
  `(html, plain_text, tool_results)` triple. The shared function
  returns a `ChatResponse`-shaped dict, and the bot adapts to it.
- This is not "one file." It is router.py + telegram_bot.py +
  a new shared module, plus tests.

**REPORT per the dispatch's "stop and report if larger than it looks":**
this is larger than it looks. Three options the founder can rule on:

- **α. Extract the shared core** (router.py + telegram_bot.py
  refactor; honors the Chat/stream-duality rule; required if Option A
  is the chosen fix shape; ~half-day work).
- **β. Add a service-token header** for the bot (one-line request
  change + one-line server-side check; but Option A was chosen
  precisely *because* the dispatch rejected token-shaped options: "a
  service token is another secret to hold, rotate and leak").
- **γ. Defer Option A** until the chat-core refactor lands.

The dispatch's chosen fix Option A presupposes α. The STEP 1
implementation cannot proceed without the founder's ruling on which
of α/β/γ governs this leg.

---

## 0e · Every caller that sets `channel` on `/api/v1/max/*`

### Front-end (Command Center)

| File:line | Endpoint hit | channel value sent | Currently founder? | Under Option A |
|---|---|---|---|---|
| `empire-command-center/app/hooks/useChat.ts:129` | `POST /max/chat/stream` | `channel \|\| 'dashboard'` (state value) | YES (web/dashboard in allow-list) | YES (handler declares `web_cc`) — **no change** |
| `empire-command-center/app/components/ContinuityPanel.tsx:79` | `POST /max/chat` | `'web'` | YES | YES — no change |
| `empire-command-center/app/components/ContinuityPanel.tsx:148` | `POST /max/chat` | `'web'` | YES | YES — no change |
| `empire-command-center/app/components/screens/DrawingStudioPage.tsx:578-584` | `POST /max/chat` | `'web_cc'` | YES | YES — no change |
| `empire-command-center/app/components/screens/ResearchScreen.tsx:23` | `POST /max/chat/stream` | **NO channel key** (body: `{message, model, history}`) | YES (empty `""` in allow-list) | YES (handler declares `web_cc`) — no change |
| `empire-command-center/app/components/screens/QuoteReviewScreen.tsx:365` | `POST /max/chat/stream` | **NO channel key** (body: `{message, model, history}`) | YES (empty `""` in allow-list) | YES (handler declares `web_cc`) — no change |
| `empire-command-center/app/components/screens/ChatScreen.tsx:335` | `POST /max/code-task` | `'web_cc'` | YES | YES — no change |

The two no-channel entries (`ResearchScreen.tsx:23`,
`QuoteReviewScreen.tsx:365`) **are NEW relative to D31 §0c's table.**
Both currently exploit the empty-string default to gain founder. They
do NOT lose founder under Option A — they gain it via the handler's
declaration. Both are inside the founder's portal flow and are
expected to keep working as founder.

### Out-of-scope front-end callers (not hitting `/max/*`)

These post to other endpoints and are NOT in scope:

- `app/components/screens/PresentationScreen.tsx:431-435` — `POST
  /avatar/chat` (not `/max/*`), channel `'avatar'`. Currently NOT
  founder (`'avatar'` not in allow-list). Out of scope.
- `app/components/screens/DesksScreen.tsx:118` — channel `'web'`,
  endpoint not `/max/*`. Out of scope.
- `app/components/screens/DrawingStudioPage.tsx:602` — second fetch in
  this file; endpoint not `/max/*`. Out of scope.
- `app/components/ChatHistoryPanel.tsx:107, :117` — these are UI
  state constructors (`setTelegramChats(...)`) for history display.
  Not POSTs. Out of scope.

### Internal callers (back-end → back-end, loopback HTTP)

| File:line | Endpoint hit | channel value sent | Currently founder? | Under Option A |
|---|---|---|---|---|
| `backend/app/services/max/telegram_bot.py:466-470` | `POST /api/v1/max/chat` | `'telegram'` + `chat_id=<FOUNDER>` | YES | **YES, but only via in-process path.** See 0d — Option A breaks the HTTP path because the route declares `web_cc` regardless of body. **Telegram regresses unless the in-process refactor lands.** |
| `backend/app/services/openclaw_worker.py:1012-1021` (`_notify_telegram`) | `POST /api/v1/max/chat` | `'telegram'` + **no `chat_id`** | **NO** (Telegram branch fails; falls through to `return False`) | **NO** (handler declares `web_cc`, but this caller would gain founder that it currently does not have — see ⚠ below). **NOT what we want.** |
| `backend/app/routers/llcfactory.py:730-735` | `POST /api/v1/max/chat/stream` | **NO channel key** (body: `{message, desk_id}`) | YES (empty `""` → founder) | YES (handler declares `web_cc`) — no change |

**Net behaviour change under Option A:**

| Caller | Current | Under Option A | Net |
|---|---|---|---|
| All front-end CC callers (7 sites) | founder | founder | no change |
| Telegram bot | founder | **needs in-process path (0d)** | regression unless refactor lands |
| OpenClaw worker `_notify_telegram` | NOT founder | founder (handler declares `web_cc`) | **GAINS founder** — see ⚠ |
| LLCFactory `/max/chat/stream` | founder (via empty) | founder (via handler) | no change |

**⚠ The OpenClaw worker note.** `_notify_telegram` posts to
`/max/chat` with `channel: "telegram"` and no `chat_id`. Currently the
Telegram-branch check fails because `chat_id` is missing, so the
caller is correctly anonymous. Under Option A, if the handler declares
`channel="web_cc"` internally, the worker gains founder. This is a
**privilege escalation for an internal notification path** that was
previously anonymous by accident. The fix must exclude this caller
from the founder path.

Two ways to exclude it, both need the founder's ruling:

- **Exclude by token** — the worker adds a non-founder marker
  (e.g., `X-Internal-Source: openclaw-notify`). The handler checks
  for the marker and refuses founder. (This is Option E / Option C
  territory — the dispatch ruled out service tokens but did not
  rule out non-founder markers.)
- **Move the worker off /max/chat** — `_notify_telegram` becomes a
  direct call to a `notifications.send()` helper, not through MAX.
  This is the clean shape and removes a privilege surface.

### Tests that set `channel` on `/api/v1/max/*`

Out of scope for runtime, but in scope for "what breaks if the empty
default moves":

- `backend/tests/test_max_runtime_truth_check.py:272, :310, :341` —
  POST `/max/chat` with `channel: "web"`.
- `backend/tests/test_max_truth_guardrails.py`, `test_drawing_router_to_engine_hotfix4_0b.py`,
  `test_drawing_vector_b2.py`, `test_h44_canonical_quote_source.py`,
  `test_hermes_phase2.py`, `test_max_control_plane.py` — all POST to
  `/max/chat` or `/max/chat/stream`.

These tests assert `channel: "web"` or omit channel. The default move
does not break tests that explicitly send `"web"`. Tests that omit
channel will fail unless updated; the regression-guard test for STEP
1a explicitly posts `{}` and is expected to fail against pre-fix
code, so this is consistent.

---

## 🛑 STOP 1 — decisions sought from the founder

Three questions must be ruled on before STEP 1 begins:

1. **Telegram in-process path.** 0d shows the fix is larger than
   "one file." Which governs?
   - **(α) Extract shared chat-core** in `router.py`, wire
     `telegram_bot._chat_with_max` to it. Required for Option A as
     written. ~half-day refactor.
   - **(β) Service-token header** for the bot. Rejected by the
     dispatch text but technically valid; keeps the bot's HTTP path
     working with one-line changes on both sides.
   - **(γ) Defer Option A** until the chat-core refactor lands in a
     separate lane. The empty-default move (1a) still lands first.

2. **OpenClaw worker `_notify_telegram` is about to gain founder
   accidentally.** 0e shows the only non-front-end back-end caller
   that currently has no founder status. Under Option A as written,
   it inherits founder from the handler. Which governs?
   - **(a)** Add a non-founder marker (`X-Internal-Source`) and check
     it in the handler. Tiny, principled.
   - **(b)** Move `_notify_telegram` off `/max/chat` entirely to a
     direct `notifications.send()` helper. Cleanest; removes a
     surface.

3. **The 9-vs-4 coverage gap.** 0a shows 4 privilege-granting sites
   (SITES 1–4) and 5 non-privilege sites (SITES 5–8 plus
   `tool_executor.py:454`). SITES 6–8 are channel-normalisation
   functions; SITE 5 is a docstring. Confirm the fix scope is SITES
   1–4 only, and label-reading sites (SITES 6–8) are untouched. (This
   matches the dispatch's "label-reading sites are not in scope" but
   is worth a verbal confirm.)

---

## STOP — summary of deliverables

- **0a:** Eight numbered sites verified at the line numbers D31
  quoted; none have drifted. Four are privilege-granting
  (`router.py:2169`, `router.py:3207`, `router.py:5162`,
  `guardrails.py:135`); four are not (`tool_executor.py:454` is a
  docstring; `operating_registry.py:128` and `unified_message_store.py:218,
  :225` are channel normalisers with no `is_founder_*` call). The
  D31 §0f "four sites" gap is real and is now resolved: SITES 5–8 are
  not privilege gates and are out of scope.
- **0b:** Predicate A `guardrails.is_founder_message` is called from
  four runtime sites (SITES 1–4) plus the import. Predicate B
  `founder_auth.is_founder_channel` is dead (zero live callers in any
  language). A fix covering predicate A alone is sufficient.
- **0c:** Empty-string default is `channel = message_context.get("channel", "")`
  in predicate A and the same shape in predicate B. Four router
  call sites reach the founder branch via `request.channel or ""` and
  the empty default.
- **0d:** Telegram bot is **in-process** inside the backend (started
  by `main.py:410`); no separate systemd service. Bot calls
  `/max/chat` over loopback HTTP with `channel="telegram"` and
  `chat_id=<FOUNDER>`. **In-process path requires extracting a shared
  chat-core function from the `/chat` and `/chat/stream` handlers —
  not "one file."**
- **0e:** Eight front-end and three back-end callers enumerated. Net
  behavior change under Option A: zero front-end callers lose founder
  (one GAINS — `PresentationScreen.tsx:434` is OUT OF SCOPE because
  it hits `/avatar/chat` not `/max/*`). One back-end caller gains
  founder accidentally (`openclaw_worker.py:_notify_telegram`). One
  back-end caller regresses (`telegram_bot._chat_with_max`).

No fix lane entered. Report-only. Awaiting founder's ruling on the
three STOP 1 questions above.