# H81 · FOUNDER FLAG · PHASE 1 MAP

**Date:** 2026-09-01
**Repo:** `~/empire-repo-main` · branch `feature/drawing-standard`
**HEAD actually at start of dispatch:** `0041e3d` ("handoff: session close 2026-09-01 tuesday")
**HEAD dispatch referenced:** `de313a6` (one commit before — D52 itself)
**Phase:** 1 of 2 — MAP ONLY. No edits to source. No commits except this report.
**Hazard reference:** `memory/hazard_h81_founder_bypass.md`

---

## 0. Dispatch discrepancies noticed (FILE over dispatch — per dispatch rule)

| Item | Dispatch said | File actually says | Disposition |
|---|---|---|---|
| HEAD | `de313a6` | `0041e3d` (`git log --oneline -1`) | Report uses actual HEAD `0041e3d`. D52 itself is the parent commit. |
| `guardrails.py` location | "guardrails.py (~96-118)" | Two files exist; the live one is `backend/app/services/max/guardrails.py` (268 lines). `backend/app/services/security/guardrails.py` (63 lines) is the older GuardrailsService stub and has no `is_founder_message`. | Function referenced at `services/max/guardrails.py:96-118`. |
| `backend/main.py` | "26-line stub" | 27 lines (off by 1). `backend/app/main.py` (705 lines) is the live FastAPI app. | Both verified. |
| DANGEROUS_TOOLS contents | `{"shell_execute", "env_set"}` after D52 | `tool_executor.py:68 = {"shell_execute", "env_set"}` — matches. | No discrepancy on the literal set. But see §11 — test file expects 3 tools and is now stale. |

---

## 1. `is_founder_message()` — full body, real location

**File:** `backend/app/services/max/guardrails.py`
**Lines:** 96–118

```python
def is_founder_message(message_context: dict) -> bool:
    """Determine if message is from the founder.
    CC / web = always founder (Command Center is the owner's tool).
    Telegram = match by chat_id.
    Unknown channel = not founder (require PIN fallback).
    H74 (D45, 2026-08-28): missing or unrecognized channel resolves to
    anonymous, NEVER founder. Pre-fix the allow-list tuple contained ""
    and `request.channel or ""` defaulted to "", so any caller omitting
    the `channel` body field walked past every privilege gate. The empty
    string is intentionally absent from the tuple below.
    """
    channel = message_context.get("channel", "")
    # Command Center (any variant) = always founder.
    # NO empty string in this tuple: see H74 docstring above.
    if channel in ("web", "web_cc", "cc", "command_center", "command-center"):
        return True
    # Telegram: match by chat_id
    if not _FOUNDER_CHAT_ID:
        return False
    chat_id = str(message_context.get("chat_id", ""))
    if channel == "telegram" and chat_id == _FOUNDER_CHAT_ID:
        return True
    return False
```

**Inputs:**
- `message_context.get("channel", "")` — one key, one string lookup.
- `message_context.get("chat_id", "")` — only read in the Telegram branch.
- `_FOUNDER_CHAT_ID` is a module-level capture at line 9: `os.getenv("TELEGRAM_FOUNDER_CHAT_ID")`.

**What it does NOT do:**
- No identity check beyond channel-name string match and (telegram) chat_id string equality.
- No token, no session cookie, no signature, no secret, no IP allowlist, no User-Agent check, no TLS client cert, no rate limit.
- The Telegram-match path is a literal string compare of `chat_id == _FOUNDER_CHAT_ID`. Nothing in the function reads the request headers, the connection, or anything else.

**Confirmed allow-list tuple (exact):**
```python
("web", "web_cc", "cc", "command_center", "command-center")
```
No empty string in it (H74 fix verified at line 110). Telegram-match only works if `_FOUNDER_CHAT_ID` is set AND `chat_id` matches. The function therefore reduces to: **"channel name matches an allow-list, OR channel is telegram AND chat_id equals the env-captured value"** — that is the entire identity model.

---

## 2. Where does `channel` come from? — the crux

Three router handlers and one in-process bot caller all reach `is_founder_message`. **Their channel provenance differs by call site.**

### 2a. `/api/v1/max/chat` (router.py:2162) — HARDENED

```python
# router.py:2185-2190 (verbatim)
canonical_channel = "web_cc"
canonical_chat_id: Optional[str] = request.chat_id  # body-supplied, may be None
msg_ctx = {"channel": canonical_channel, "chat_id": canonical_chat_id or ""}
founder = is_founder_message(msg_ctx)
```

And inside the shared service body at line 2256:
```python
request.channel = canonical_channel or request.channel
```

The handler **declares `canonical_channel = "web_cc"` server-side** and overwrites `request.channel` before any privilege gate runs. A client cannot influence the channel value here — only chat_id, which is irrelevant on the web_cc branch. There is also a warning log at line 2240 if the body claims `channel="telegram"` ("H74 E — spoof-detection warning"), so the body is read for telemetry but not for privilege.

**Effective gate:** anyone who can reach `127.0.0.1:8000`'s `/api/v1/max/chat`. The body field does not influence founder.

### 2b. `/api/v1/max/chat/stream` (router.py:3308) — NOT HARDENED. **THIS IS THE FINDING.**

```python
# router.py:3308-3314 (verbatim)
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint for MAX chat with brain context."""
    msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
    founder = is_founder_message(msg_ctx)
    if founder:
        logger.info(f"Founder message (stream) detected via chat_id={request.chat_id}")
```

**No canonical override.** No server-side declaration. `request.channel` is read straight from the JSON body and fed to `is_founder_message`. With `channel in ("web", "web_cc", "cc", "command_center", "command-center")` (the function's allow-list), a client that posts:

```json
POST /api/v1/max/chat/stream
{"message": "...", "channel": "web_cc", "chat_id": ""}
```

gets `founder = True`. The downstream `execute_tool(..., founder=founder)` calls at router.py:3371, 3628, 3744 then pass that flag through, and `execute_tool` skips the entire PIN/access gate (see §3).

The same body field is also used downstream for:
- `request.channel` as a key for pending drawing-job lookup (router.py:3400, 3408, 3409, 3414, 3416) — i.e. namespace keying, not a separate privilege.
- `_q_channel = Channel.TELEGRAM if request.channel == "telegram" else Channel.CHAT` (router.py:3858) — telemetry.

These side effects don't grant anything, but they confirm `request.channel` flows deep into the handler.

**Severity:** anyone who can reach `127.0.0.1:8000` (same exposure as /chat) can additionally **bypass the body-channel hardening** because the stream door never applied Option A. The chat/stream divergence called out in the dispatch has materialised — D45 commit 3 closed `/chat` and `/code-task` but not `/chat/stream`.

### 2c. `/api/v1/max/code-task` (router.py:5273) — HARDENED

```python
# router.py:5289, 5318-5319 (verbatim)
# Option A: the handler declares canonical_channel = "web_cc".
canonical_channel = "web_cc"
...
msg_ctx = {"channel": canonical_channel, "chat_id": ""}
founder = is_founder_message(msg_ctx)
```

Same pattern as /chat. Body channel is logged for spoof detection (line 5309) but not used for privilege. If `founder=False`, the handler falls back to `FOUNDER_PIN` check (line 5322-5330) using the env var directly — so a non-CC caller without a PIN gets 403.

### 2d. Telegram bot in-process path (telegram_bot.py:455-503) — server-derived

The bot calls `_chat_with_max_service` directly (in-process), passing `canonical_channel="telegram"` and `canonical_founder=True`. The latter is set unconditionally because the bot has already verified the chat_id against its own `self.founder_chat_id` (set at line 232 from `TELEGRAM_FOUNDER_CHAT_ID`). The HTTP-loopback fallback (line 519-539) is only used if `_chat_with_max_service` is not importable (a build-skew indicator) and would silently lose founder under Option A — but is not the active path.

**Net result of §2:** the **stream endpoint is the only door** where the channel value reaching `is_founder_message` is client-controllable. /chat and /code-task are server-derived. The telegram path is server-derived from a chat_id check. There is no H74-class empty-string default and no inner string-equality default that lets any field other than channel/chat_id into the predicate.

---

## 3. `tool_executor.py` dangerous-tools branch — what `if founder:` skips

**Function signature:** `def execute_tool(tool_call: dict, desk: Optional[str] = None, access_context: Optional[dict] = None, founder: bool = False) -> ToolResult:` at line 455.

**Branch of interest, lines 462-535 (verbatim):**

```python
        tool_name = tool_call.get("tool", "")
        try:
            # ── FOUNDER BYPASS: CC / Telegram founder = full access, no PIN ──
            if founder:
                logger.info(f"Founder auto-auth — executing '{tool_name}' without PIN/access check")
                tool_call["_founder"] = True  # pass founder flag to tool handlers
            else:
                # Access control check (non-founder users)
                if access_context and access_controller:
                    user = access_context.get("user")
                    if user:
                        level = int(access_controller.classify_tool(tool_name))
                        action, _ = access_controller.check_permission(user, tool_name, desk)
                        if action == "deny":
                            access_controller.audit_log(user.get("id", ""), tool_name, level, "denied", channel=user.get("channel", ""))
                            return ToolResult(tool=tool_name, success=False, error="Access denied: insufficient permissions")
                        if action == "locked":
                            return ToolResult(tool=tool_name, success=False, error="Account locked due to failed PIN attempts. Try again in 15 minutes.")
                        if action == "confirm":
                            session_id = access_controller.create_pending_session(...)
                            ...
                            access_controller.audit_log(user.get("id", ""), tool_name, level, "pending_confirm", channel=user.get("channel", ""))
                            return ToolResult(...)
                        if action == "pin":
                            session_id = access_controller.create_pending_session(...)
                            ...
                            access_controller.audit_log(user.get("id", ""), tool_name, level, "pending_pin", channel=user.get("channel", ""))
                            return ToolResult(...)

                # Dangerous tool PIN gate (HOTFIX 4.2 fail-closed)
                if tool_name in DANGEROUS_TOOLS:
                    if not FOUNDER_PIN:
                        logger.critical("BLOCKED dangerous tool '%s' invocation: FOUNDER_PIN env var is unset. ...", tool_name)
                        return ToolResult(tool=tool_name, success=False, error=...)
                    pin = (access_context or {}).get("pin")
                    if not pin:
                        return ToolResult(tool=tool_name, success=False, error=f"⚠️ Tool '{tool_name}' is restricted. Please provide your founder PIN to proceed.")
                    if str(pin) != FOUNDER_PIN:
                        logger.warning(f"Invalid PIN attempt for dangerous tool '{tool_name}'")
                        return ToolResult(tool=tool_name, success=False, error="❌ Invalid PIN. Access denied.")
                    logger.info(f"PIN verified — executing dangerous tool '{tool_name}'")
```

**What `if founder:` skips (vs the `else:` branch):**
- The entire `access_controller.classify_tool` / `check_permission` flow (deny/locked/confirm/pin).
- The `access_controller.audit_log(...)` calls for denied/pending_confirm/pending_pin outcomes.
- The dangerous-tools PIN gate (the `if tool_name in DANGEROUS_TOOLS:` block — including the fail-closed empty-PIN check, the missing-PIN check, and the `str(pin) != FOUNDER_PIN` check).

**What `if founder:` does NOT skip (i.e. still runs for founder):**
- The tier check at line 538: `tier_error = require_tool(tool_name)` — tool-tier gating still applies.
- The tool-name auto-correct block at line 543+.
- The actual tool handler dispatch (e.g. `_shell_execute` at line 4536).
- Inside `_shell_execute` (line 4556-4563), the ALLOWED_COMMANDS allowlist is bypassed for founder (`founder = params.get("_founder", False)`), but BLOCKED_PATTERNS at line 4548 are NOT bypassed — `rm -rf`, `pkill -9`, `sensors-detect`, etc. are always blocked. **Caveat:** `pkill -f` (broad pattern) is not in BLOCKED_PATTERNS and would not be caught. That is a separate finding beyond H81 scope.
- Tier / desk / approval gates that downstream handlers enforce.

**`DANGEROUS_TOOLS` literal at line 68:** `{"shell_execute", "env_set"}`. Confirmed. db_query was removed by D52 (see in-file comment lines 62-67) and the rationale is documented. **However:** `backend/tests/test_founder_pin_failclosed_hotfix4_2.py:251-258` still asserts `assert len(te.DANGEROUS_TOOLS) == 3` and `"db_query" in te.DANGEROUS_TOOLS`. The test is stale and would fail if run. Reported, not fixed.

---

## 4. Blast radius — every call site of the founder flag

Raw grep output (`grep -rn "is_founder_message\|founder=\|is_founder\b" backend/ --include="*.py"`, filtered to remove `.bak-` files):

| File:line | What consumes the flag | What the flag gates there |
|---|---|---|
| `app/services/max/guardrails.py:141` | `check_input(text, message_context)` calls `founder = is_founder_message(message_context or {})` then uses it to SKIP prompt-injection blocks (`logger.info("Founder override: skipping prompt_injection block")`) and SKIP blocked_topic blocks. | Only the guardrail skip. Tool executor NOT involved. Still bypasses input blocks (e.g. "ignore previous instructions"). |
| `app/routers/max/router.py:2190` | `/chat` handler — `founder = is_founder_message(msg_ctx)`. | Feeds `execute_tool(... founder=founder)` at lines 2429, 2704, 2897, 2997. Covers runtime_truth_check (2429), search_tc (2704, 2997), and the main tool-dispatch loop at 2897. **All tools that pass through the chat tool loop are affected.** |
| `app/routers/max/router.py:3312` | `/chat/stream` handler — same predicate call. | Feeds `execute_tool(... founder=founder)` at lines 3371, 3628, 3744. Same tool coverage as /chat. **This is the door the dispatch §5 warned about.** |
| `app/routers/max/router.py:5319` | `/code-task` handler — `founder = is_founder_message(msg_ctx)`. | If `founder=True`, skips PIN gate at line 5322-5330. If `founder=False`, requires PIN or 403. Founder flag then persists into `code_task_runner.submit(..., founder=founder)` at line 5339, which writes `task.founder` to the DB (column `founder` in `code_mode_tasks`, code_task_persistence.py:122). At execution time, `code_task_runner.py:1046` calls `execute_tool(t, desk="codeforge", founder=task.founder)`. **Persistence to DB means a founder-True task lives past the request boundary.** |
| `app/services/max/code_task_persistence.py:499` | `CodeTask.from_row(...)` reads `founder=bool(row["founder"])` and constructs a CodeTask dataclass. | Restores the persisted founder flag. No predicate call here. |
| `app/services/max/code_task_runner.py:834,860,1046` | `CodeTaskRunner.submit(..., founder=bool)`; persists to DB; on task execution calls `execute_tool(t, ..., founder=task.founder)`. | **Transitive gate.** A /code-task submission under founder=True persists a row that, when later executed, will re-run tool calls with founder=True. The audit DB (tool_executions) does not log this path because the executor's tool-registration path bypasses log_execution for shell_execute. |
| `app/services/max/telegram_bot.py:493-500` | `_chat_with_max(... canonical_founder=True)` — sets `canonical_founder=True` directly, bypassing the predicate. | Server-derived from the bot's own `self.founder_chat_id` check. The `is_founder_message` predicate is not called on this path. |
| `app/services/security/guardrails.py` | `audit_log` method (line 36 of file, line 288 actual) — only inside the GuardrailsService class. | Unrelated to founder. Records GuardrailsService events. |

**Outside the grep — founder-bypassed consumers I checked:**
- `app/routers/portal_button_compat.py:106-107` — calls `execute_tool(...)` without the `founder=` argument, so the default `founder=False` applies. PIN-gated for dangerous tools. Not affected by H81.

**Net blast radius summary:**
- The founder flag is consumed in **three router handlers** (`/chat`, `/chat/stream`, `/code-task`) and **two service paths** (`telegram_bot._chat_with_max`, `code_task_runner.execute_tool`).
- It gates the dangerous-tools PIN gate (`tool_executor.py:498-535`) and the access-control permission system (deny/locked/confirm/pin actions).
- It does NOT gate a send path, a DB write, or any external action in `tool_executor.py` itself. The downstream handlers (`_shell_execute`, `_env_set`) honour the flag.
- `telegram_bot.py` also passes `canonical_founder=True` into `_chat_with_max_service`, which routes through `/chat`'s handler — but with the canonical override, the founder flag is server-set, not body-set.
- The founder flag DOES persist via `code_task_runner` to the `code_mode_tasks` DB. A task submitted under founder=True can later execute under founder=True across process restarts. This is intended (H62 fix narrative at line 5321-5327 of router.py describes the founder-PIN gate at submission; the persistence is by design), but means an attacker who can submit a code-task today can also cause its tool calls to run as founder later.

**Does founder gate a send path?** No — there is no Telegram send, no email send, no webhook send, no Stripe call, no client-facing communication that checks the founder flag at the executor level. The Telegram bot's `_send_voice_reply` (line 545) and other send paths do not call `is_founder_message` and do not consult `execute_tool`'s `founder` parameter. Client-facing email is governed by `send_email`'s own allowlist and the standing `DEFAULT_EMAIL_CC = ("rafa22giraldo@gmail.com",)` (line 58). The Telegram bot's chat handler is server-derived as noted.

---

## 5. Both doors — `/chat` vs `/chat/stream`

| Aspect | `/api/v1/max/chat` (router.py:2162) | `/api/v1/max/chat/stream` (router.py:3308) |
|---|---|---|
| `canonical_channel` declared in handler | YES — line 2187: `canonical_channel = "web_cc"` | NO |
| Body `channel` overrides privilege | NO — line 2256: `request.channel = canonical_channel or request.channel` | YES — line 3311 reads `request.channel or ""` straight into `msg_ctx` |
| Body-claims-telegram spoof log | YES — line 2240 | NO equivalent |
| Code-task-style fallback to PIN | No — the body is just overwritten, no PIN branch in the canonical web_cc path | No equivalent — if founder=True the executor skips the gate, if founder=False the executor requires PIN through the normal `access_context` flow |
| Founder → tool executor | YES (lines 2429, 2704, 2897, 2997) | YES (lines 3371, 3628, 3744) |
| Auth context (`_ac_context` / `_stream_ac_context`) | Built from body + canonical override | Built from body only (no canonical override) |

**This divergence is the live H81 finding.** The `/chat` handler was hardened by D45 commit 3 (Option A) but the `/chat/stream` handler was not updated. Any client that can reach the backend (which is bound to `127.0.0.1:8000`, see §7) can POST `{"message": "<anything>", "channel": "web_cc"}` to `/chat/stream` and receive `founder=True` from the predicate.

The shared logic that follows (drawing handoff, runtime_truth_check, code-task offload, search_tc) is largely the same on both routes, so the rest of the privilege surface is identical once founder is True — it's the door that's open wider, not the room behind it.

---

## 6. The PIN — storage and fail-mode

- **Storage location:** `os.getenv("FOUNDER_PIN", "")` at `tool_executor.py:88`. The env var is supplied by the systemd EnvironmentFile. The live service loads from:
  - `/home/rg/.config/empirebox/empire-backend-secrets.env` (verified via `systemctl --user show empire-backend` → `EnvironmentFiles=`). Other EnvironmentFiles also loaded: `gemini.env`, `empire-backend.env`, `empire-backend-smtp.env`. None of these is in the repo tree.
  - `grep FOUNDER_PIN ~/.config/empirebox/empire-backend-secrets.env` returns `FOUNDER_PIN=<REDACTED>` — value present, not empty. No print of the value here per dispatch.
- **Empty/unset behaviour:** **FAIL-CLOSED.** Lines 97-108 fire a one-shot CRITICAL log on import when `not FOUNDER_PIN`, and the gate at lines 505-522 refuses every dangerous-tool invocation with a structured error when FOUNDER_PIN is empty. Pre-fix this defaulted to `"7777"` — see HOTFIX 4.2 docstring lines 69-87.
- The same `FOUNDER_PIN` env is consulted at `router.py:5322` (code-task handler PIN check) and `auth.py:184` (H62 fix comment). The fail-closed default is consistent across these three sites.
- A second env var, `FOUNDER_APPROVAL_PIN`, exists for the quote-approval path (`tool_executor.py:1872-1895`) — separate concern, separate flow.

---

## 7. Other ingress reaching the executor

- **Live FastAPI app:** `backend/app/main.py` (705 lines), uvicorn entrypoint at line 673-674. `systemctl --user show empire-backend` confirms: `ExecStart=/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- **Bind address:** `127.0.0.1`, NOT `0.0.0.0`. External exposure is only via reverse proxy / tunnel (Cloudflare Tunnel per memory entry). H81 exposure therefore requires:
  - The founder's own browser via the portal,
  - A local process on EmpireDell that can reach 127.0.0.1:8000,
  - The reverse proxy / Cloudflare Tunnel path reaching the backend,
  - An opencode-remote-spawned uvicorn squatter (CLAUDE.md warns: prior incidents caused 85k+ crash-loop). Not active per current state, but a recorded hazard class.
- **`backend/main.py` (27 lines):** confirmed the stub — only `/`, `/health`, and a transcription router are loaded. The module imports `from transcribe import router` at top level. It does NOT mount the max router, the access controller, or any of the audit tools. It is dead code as far as H81 is concerned. The live service points at `app.main:app` from the empire-repo-main working directory, so this stub does not run.
- **Webhook routes:** `backend/app/routers/webhooks.py` exposes:
  - `POST /webhooks/email/inbound`, `POST /email/inbound` (line 49-50)
  - `POST /webhooks/ebay/notification`, `POST /ebay/notification` (line 180-181)
  - `POST /webhooks/stripe`, `POST /stripe` (line 214-215)
  - `POST /webhooks/telegram-webhook` (line 244) — note: separate from the long-poll bot
  - And in `backend/app/routers/vendorops.py:848`: `POST /vendorops/activation/stripe-webhook`
  - And `backend/app/routers/payments.py:631`: `POST /webhook`
  - **None of these call `execute_tool` or `is_founder_message`.** `grep -rn "execute_tool\|is_founder_message" backend/app/routers/webhooks.py backend/app/routers/payments.py backend/app/routers/vendorops.py` returns ZERO matches. Webhook payloads route into `unified_message_store.add_message(...)` and the inbox/tasks endpoints; they do not get a founder flag.

- **Sequencing note from the dispatch:** if webhooks could reach the tool executor, H81 would land before webhooks. As of this map, they do not, so the two dispatches (H81 and Stripe webhooks) are independent.

---

## 8. Detective — has H81 been exercised?

**Audit DB:**
- Path: `~/empire-repo/backend/data/tool_audit.db` (tool_audit.py:15 — hardcoded `os.path.expanduser("~/empire-repo/backend/data/tool_audit.db")`, **not empire-repo-main**). H73-class finding: audit writes to the stale fork path. The DB is on the live machine because `~/empire-repo` is still mounted and writable (see CLAUDE.md canonical-paths warning), but a clean canonical-path resolver on the audit module would point it at empire-repo-main. Flagged, not in H81 scope.
- File exists: `-rw------- 1 rg rg 1921024 Sep 1 09:11 /home/rg/empire-repo/backend/data/tool_audit.db` (1.9 MB).
- Rows: **7928** total. First row: `2026-03-17T02:43:38.822907`. Last row: `2026-09-01T13:11:04.189331`. ~5.5 months of history.
- Row counts by tool (top): `file_read=6364`, `git_ops=574`, `file_write=431`, `db_query=322`, `search_conversations=92`, `file_append=62`, `service_manager=47`, `test_runner=15`, `file_edit=14`, `project_scaffold=6`, `package_manager=1`.
- **Zero rows for `shell_execute` and `env_set`** across the entire 7928-row window.
- Schema (lines 24-35): `id, timestamp, tool, params, result, access_level, approved_via, desk, success, duration_ms`. **No channel, no user_id, no founder column.** The audit DB cannot distinguish a web-channel founder-bypassed dangerous-tool call from a non-event.

**Why the zero rows are inconclusive:**
- `env_set` handler (line 5362) DOES call `log_execution("env_set", ...)` at line 5394 — only on the success path. The audit DB would record successful env_set writes. Zero rows means zero successful env_set calls in 5.5 months.
- `shell_execute` handler (line 4536) **NEVER calls `log_execution`.** The grep on the dangerous-tools audit chain shows the only `log_execution` calls in tool_executor.py are for `file_read`, `file_write`, `file_append` (around lines 5034-5168). Shell commands leave no DB footprint at all — only the INFO log line at `tool_executor.py:466`: `"Founder auto-auth — executing 'shell_execute' without PIN/access check"`.
- Net: in 7928 rows, there is no record of either dangerous tool running. env_set has logging; shell_execute does not. The audit DB cannot answer "did a founder-bypassed shell_execute run from a web channel yesterday?" — that information lives only in `journalctl --since=yesterday | grep "Founder auto-auth"` against `max.tool_executor` logger output.

**Where to look next (recommendation, not action):** `journalctl -u empire-backend --since='30 days ago' | grep -F 'Founder auto-auth — executing'` — would surface any INFO log lines from the bypass branch. Without running that, this map cannot confirm whether the H81 path has been exercised. The dispatch prohibits a service restart, so this can be done read-only. The journal will tell us "yes it ran" but not "from which channel" — that signal is gone.

**Blind spot findings (item 8 itself is a finding):**
- The audit DB schema lacks channel/user/founder columns. A founder-bypassed dangerous-tool call leaves an INFO line and nothing else.
- `shell_execute` has no `log_execution` call at all, regardless of how it's invoked. Even a non-founder PIN-verified `shell_execute` would not land in this DB.
- `env_set` logs success but not failure (only `success=True` branch calls log_execution at line 5394; the except at line 5399 does not log).

---

## 9. Concrete recommended fix shape — proposal, not code

Per dispatch: "Do not propose the fix in code. You may propose it in prose at the end, ranked by blast radius, and the founder rules."

Ranked by smallest blast radius first:

1. **`/chat/stream` must apply D45 Option A.** Declare `canonical_channel = "web_cc"` in `chat_stream` (router.py:3308) and pass it through `_chat_with_max_service` (or apply the line 2256 equivalent inside the stream handler body). One-line surgical change to close the only open door. Leaves every other consumer of `is_founder_message` untouched. Affects 0 features in production unless the stream endpoint is being called with non-web_cc channels today (no evidence either way — no audit log).
2. **Add `log_execution("shell_execute", ...)` and a channel-fingerprint field to the audit DB.** Add a migration to `tool_executions` adding `channel TEXT` and `founder INTEGER`. Calls in `_shell_execute` (line 4536) and `_env_set` (line 5362) should write the channel and the `_founder` flag. Even after fix #1 lands, this is the only way to retrospectively answer "did this run?". Independent of fix #1.
3. **Strip `founder=True` for `shell_execute`/`env_set` specifically.** Inside `execute_tool` at line 465, force the dangerous-tools branch to require PIN regardless of `founder` (e.g. set a local `effective_founder = founder and tool_name not in DANGEROUS_TOOLS`). Closes dangerous tools but lets every other consumer of founder keep working. Larger semantic change — affects the assumption that "founder = full access" which is documented in tool_executor.py:464.

If fix #1 alone lands, the residual exposure is: the audit DB still cannot distinguish channels, and any future divergence between /chat and /chat/stream reintroduces the same defect. Fixes #2 + #3 are defense-in-depth.

Founder rules already in CLAUDE.md that bear on the choice: "Chat/stream duality — any logic in a chat handler lives in ONE shared function called by BOTH" (note: this rule has been honoured for /chat's body but Option A did not get applied to /chat/stream, so the rule's enforcement did not catch this). The fix should land in the shared service so the divergence cannot return.

---

## 10. STOP — no fix lands in this dispatch

The dispatch directive is: 🛑 STOP AFTER THE MAP. No code edits. No commits to source. No service restart. No PIN entry. No client-facing anything.

---

## 11. Phase 2 backlog correction — H81 Phase 2B Task D1

Phase 2 chat-output listed in its handed-forward backlog:

> `router.py:5322` PIN fallback on `/code-task` is unreachable while founder is unconditional (Task 1 made it reachable — should now work).

**This is wrong.** Task 1 (commit `df7ac67`) changed only the executor's gate at `tool_executor.py:455-535` — pulling the dangerous-tools PIN gate out of the `else:` branch so it runs uniformly for founder and non-founder. Task 1 did not change how founder is granted by the chat handlers. Verified against the file on 2026-09-01:

- `backend/app/routers/max/router.py:5293` — `/code-task` handler still declares `canonical_channel = "web_cc"` server-side.
- `backend/app/routers/max/router.py:5318-5319` — `msg_ctx = {"channel": canonical_channel, "chat_id": ""}` and `founder = is_founder_message(msg_ctx)` — `canonical_channel="web_cc"` returns True from the predicate.
- `backend/app/routers/max/router.py:5320` — `if not founder:` is therefore always False on the canonical /code-task path.
- `backend/app/routers/max/router.py:5322-5330` — the FOUNDER_PIN fallback at the cited line is therefore **still unreachable** as of HEAD `dd72de8`.

The correct state: `/code-task`'s FOUNDER_PIN fallback becomes reachable when Phase 3 introduces a path that grants `founder=False` to a `/code-task` caller. Today every caller reaches `founder=True` and the gate at line 5320 is skipped.

This section exists because the wrong claim did not land in any committed file — it lived in the Phase 2 chat-output. A future reader who runs `git log --all -p` on the repo will not find it; this section is the durable record of the correction.

---

## Report envelope

- **found:** the live H81 exposure is the `/api/v1/max/chat/stream` handler at `router.py:3308-3312`, which reads `request.channel` from the JSON body without applying D45 Option A. Any local-process or proxy-reachable client can POST `{"channel": "web_cc", "chat_id": ""}` to that route and get `founder=True` from `is_founder_message`, which `execute_tool` honours by skipping the entire PIN gate for `shell_execute` and `env_set`. /chat and /code-task are hardened; telegram bot is server-derived from chat_id; webhooks do not reach the executor. The audit DB cannot detect this — schema lacks channel/founder columns, and `shell_execute` never calls `log_execution`. In 7928 audit rows since 2026-03-17, zero `shell_execute` and zero `env_set` rows exist.
- **changed:** none — map only. No source files were modified.
- **tests:** none — no code changed.
- **commit hash:** 581d78d (Phase 1 map), with section 11 added in Phase 2B Task D1 (commit pending).

---

## Appendix A — raw grep output

```
$ git status --short
 M max/memory.md
?? backend/app/services/max/runtime_truth_enforcer.py.bak-20260831-225728
?? backend/app/services/max/tool_executor.py.bak-20260831-221952
?? reference/recovered/r6_woodwork/client_change_order.py.bak-20260830-160109
?? reference/recovered/r6_woodwork/invoice_change_order.py.bak-20260830-160229
?? reports/2026-08-31_r6_invoice_phase7.md
?? reports/2026-08-31_r6_invoice_phase7.png
?? uploads/EST-2026-261-mock.pdf
```

The two `.bak-` files in `backend/app/services/max/` are out-of-band artifacts of prior sessions (timestamps 2026-08-31). They are not modified by this dispatch and are out of scope. The `max/memory.md` modification predates this dispatch and is untouched.

```
$ git log --oneline -3
0041e3d handoff: session close 2026-09-01 tuesday
de313a6 D52: db_query read-only and ungated; H80 round-aware halt on tool failure; partial receipt suppression
a21fc0f R6 invoice: bill to Lauren Bassett / LB Design, name end client in project block

$ git rev-parse HEAD
0041e3d16343cc1d33c8be7fb126d00d6e4ddf3e

$ git branch --show-current
feature/drawing-standard
```

## Appendix B — audit DB raw counts

```
$ sqlite3 ~/empire-repo/backend/data/tool_audit.db 'SELECT tool, COUNT(*) FROM tool_executions GROUP BY tool ORDER BY 2 DESC'
file_read|6364
git_ops|574
file_write|431
db_query|322
search_conversations|92
file_append|62
service_manager|47
test_runner|15
file_edit|14
project_scaffold|6
package_manager|1

$ sqlite3 ~/empire-repo/backend/data/tool_audit.db "SELECT COUNT(*) FROM tool_executions WHERE tool='shell_execute'"
0

$ sqlite3 ~/empire-repo/backend/data/tool_audit.db "SELECT COUNT(*) FROM tool_executions WHERE tool='env_set'"
0

$ sqlite3 ~/empire-repo/backend/data/tool_audit.db 'SELECT MIN(timestamp), MAX(timestamp) FROM tool_executions'
2026-03-17T02:43:38.822907 | 2026-09-01T13:11:04.189331
```

## Appendix C — service binding and env source

```
$ systemctl --user show empire-backend | grep -E 'WorkingDirectory|ExecStart|EnvironmentFiles'
WorkingDirectory=/home/rg/empire-repo-main/backend
ExecStart={ path=/home/rg/empire-repo-main/backend/venv/bin/python3 ; argv[]=/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 65 ; ... }
EnvironmentFiles=/home/rg/.config/empirebox/gemini.env
EnvironmentFiles=/home/rg/.config/empirebox/empire-backend.env
EnvironmentFiles=/home/rg/.config/empirebox/empire-backend-smtp.env
EnvironmentFiles=/home/rg/.config/empirebox/empire-backend-secrets.env
```

Bind address is 127.0.0.1, not 0.0.0.0. External exposure is via reverse proxy / Cloudflare Tunnel.
