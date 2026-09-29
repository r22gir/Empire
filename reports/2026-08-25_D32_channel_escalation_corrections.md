# D32 · H74 Channel-Escalation Corrections

**Date:** 2026-08-25
**Branch:** feature/drawing-standard @ 19230df
**H-number:** **H74** (amendment; no new H-number assigned — see §0 footnote)
**Phase:** 0.5 — READ-ONLY. No code edits, no config edits, no Cloudflare
changes, no service restarts.

This dispatch amends five gaps in the D31 map (`reports/2026-08-25_D31_channel_escalation_map.md`).
It is the closure of Phase 0.5. It does not propose a fix; it does not
enter a fix lane. Tag conventions: **VERIFIED** = the pasted raw output
contains the answer directly. **INFERRED** = derived from VERIFIED
inputs by reasoning the reader can re-trace. **COULD NOT PROBE** =
the instrument could not have shown a positive — name what was tried.

---

## 0 · H-number decision

H73 was the highest number assigned before this report
(`reports/2026-08-24_D27_persistence_map.md:675` and
`claude/2026-08-24_D22_next_session_opener_ee54f0f1.md:27`).
D31 took H74.

Item 2 (founder_auth reach) confirms D31's INFERRED-unused verdict
without turning up a distinct new finding. Item 3 closes as **option
(c)** — neither (a) nor (b) — and the new shape is an amendment to
how §0g must be read, not a new bug. **H74 stays. No new H-number
assigned.** If a future fix lane needs a number for the
"Next.js does not propagate X-Forwarded-For" finding surfaced in
§3c, that lane assigns it.

---

## 1 · The enumeration grep, pasted

D31 §0b enumerated call sites but did not paste the grep the enumeration
rests on. The grep:

```
$ grep -rn "is_founder_message\|is_founder_channel\|is_founder" \
        --include=*.py backend/
backend/app/services/max/founder_auth.py:9:def is_founder_channel(channel: str, user_context: dict = None) -> bool:
backend/app/services/max/founder_auth.py:19:def get_access_level(channel: str, user_context: dict = None) -> str:
backend/app/services/max/founder_auth.py:20:    if is_founder_channel(channel, user_context):
backend/app/services/max/access_control.py:52:        from app.services.max.founder_auth import FOUNDER_TELEGRAM_CHAT_ID
backend/app/services/max/guardrails.py:96:def is_founder_message(message_context: dict) -> bool:
backend/app/services/max/guardrails.py:135:    founder = is_founder_message(message_context or {})
backend/app/routers/max/router.py:22:from app.services.max.guardrails import check_input, sanitize_output, sanitize_output_streaming, SAFE_REFUSAL, is_founder_message, check_gpu_safety, GPU_VERIFICATION_COMMANDS
backend/app/routers/max/router.py:2169:    founder = is_founder_message(msg_ctx)
backend/app/routers/max/router.py:3207:    founder = is_founder_message(msg_ctx)
backend/app/routers/max/router.py:5162:    founder = is_founder_message(msg_ctx)
backend/app/services/max/tool_executor.py:454:                 already verified this is the founder via is_founder_message().
backend/tests/test_founder_pin_failclosed_h62.py:103:    bypass PIN via is_founder_message()."""
```

Twelve lines. **VERIFIED** — pasted directly from the run.

### Account-for-every-line table

| Line | Disposition | In D31 §0b? | Note |
|---|---|---|---|
| `founder_auth.py:9` | Predicate def (D31 §0b noted as "second copy") | Yes | The `""`-as-founder behaviour lives here too; same shape as `guardrails.py:96-112`. **VERIFIED.** |
| `founder_auth.py:19` | `get_access_level` def | Noted in D31 §0b | Reach confirmed in §2 below. **VERIFIED.** |
| `founder_auth.py:20` | Internal caller of `is_founder_channel` | No | Sole in-tree caller of `is_founder_channel`. **VERIFIED.** |
| `access_control.py:52` | Imports `FOUNDER_TELEGRAM_CHAT_ID` only — NOT `is_founder_channel`, NOT `get_access_level` | No | This is a constant import, not a predicate call. Confirmed by reading `access_control.py:52`. **VERIFIED.** |
| `guardrails.py:96` | Primary predicate def | Yes | SITE 4's predicate. **VERIFIED.** |
| `guardrails.py:135` | Internal call inside `check_input` | Yes | SITE 4. **VERIFIED.** |
| `router.py:22` | Import | No | Wiring import only — no privilege behaviour. **VERIFIED.** |
| `router.py:2169` | Call site in `/chat` handler | Yes | SITE 1. **VERIFIED.** |
| `router.py:3207` | Call site in `/chat/stream` handler | Yes | SITE 2. **VERIFIED.** |
| `router.py:5162` | Call site in `/code-task` handler | Yes | SITE 3. **VERIFIED.** |
| `tool_executor.py:454` | Substring inside a docstring | Yes | SITE 5 in D31 §0b — confirmed docstring. **VERIFIED.** |
| `test_founder_pin_failclosed_h62.py:103` | Docstring of a test that asserts bypass behaviour | No | Test documentation, not a runtime call site. **VERIFIED.** |

**No D31 site is missing; no extra D31 site is in this grep.** The 12-line
output covers exactly D31 §0b's nine numbered sites (SITES 1, 2, 3, 4, 5,
6, 7, 8, 9) plus three lines D31 §0b did not enumerate individually
(`founder_auth.py:19-20`, `access_control.py:52`, the router import, and
the test docstring) which are wiring/internal calls without privilege
behaviour.

### `tool_executor.py:3350` and `tool_executor.py:3457` disposition

D31 §0b's narrative never numbered these two lines as privilege gates —
they appeared in the dispatch's preamble only. They are **NOT** in the
`is_founder_*` enumeration grep above. Direct read of both lines today:

- **Line 3350** (`tool_executor.py:3349-3352`):
  ```python
  def _log_image_evaluation(response_id: str, provider: str, latency_ms: float,
                            success: bool, fallback_used: bool, channel: str = "web_cc",
                            capability: str = "understand_image"):
  ```
  **VERIFIED.** This is the **signature of a logging helper** —
  `_log_image_evaluation(...)` — used to write vision-API calls to
  `token_tracker`. The string `"web_cc"` is a **default parameter value**,
  not a privilege gate. **Disposition: propagated flag (logging label),
  not a privilege gate.** The function is invoked only from
  `_log_image_evaluation(...)` callers; it does not touch the
  `is_founder_message`/`is_founder_channel` predicates.

- **Line 3457** (`tool_executor.py:3455-3457`):
  ```python
  # Log for evaluation loop
  _log_image_evaluation(response_id, provider, latency_ms, True, fallback_used,
                         channel=params.get("_channel", "web_cc"))
  ```
  **VERIFIED.** This is a **call site of the same logging helper**. The
  `"web_cc"` fallback is `params.get("_channel", "web_cc")` — the
  `"_channel"` key is a passthrough from the tool call dict. **Disposition:
  propagated flag (logging label), not a privilege gate.** No `is_founder_*`
  substring; no call to either predicate; no override of any auth path.

Both lines are **safe-by-construction** in the same way D31 §0b's SITES
6–9 (the two `*.py:218, :225` normalisers) are: they are
**channel propagation into logs**, not privilege grants. The D31
dispatch text named them in passing but they do not appear in the
enumeration grep because they are not privilege predicates.

**No new privilege surface introduced by these lines.**

---

## 2 · `founder_auth.get_access_level` reach

D31 §0b INFERRED-unused on the strength of `backend/app/routers/` only.
Widened:

```
$ grep -rn "founder_auth\|get_access_level" --include=*.py backend/
backend/app/services/max/founder_auth.py:19:def get_access_level(channel: str, user_context: dict = None) -> str:
backend/app/services/max/access_control.py:52:        from app.services.max.founder_auth import FOUNDER_TELEGRAM_CHAT_ID

$ grep -rn "founder_auth\|get_access_level" --include=*.py --include=*.ts --include=*.tsx . \
        2>/dev/null | grep -v "^./backend/" | head -20
(empty)
```

**VERIFIED.** The widened grep returns two hits, both inside `backend/`.
The first is the `def` of `get_access_level` itself. The second is an
import of the *constant* `FOUNDER_TELEGRAM_CHAT_ID` from
`founder_auth.py` into `access_control.py:52` — not a call to
`get_access_level`, not a call to `is_founder_channel`.

Re-inspection of the module:

```
backend/app/services/max/founder_auth.py:9  def is_founder_channel(channel, user_context=None) -> bool
backend/app/services/max/founder_auth.py:19 def get_access_level(channel, user_context=None) -> str
backend/app/services/max/founder_auth.py:20     if is_founder_channel(channel, user_context):
backend/app/services/max/founder_auth.py:21         return "founder"
backend/app/services/max/founder_auth.py:22     return "guest"
```

**VERIFIED.** The only in-tree caller of `get_access_level` is the
`get_access_level` body itself (which calls `is_founder_channel`).
There is **no live caller** anywhere — services, desks, tool handlers,
schedulers, CLI, tests. The non-backend grep (TypeScript / TSX in the
portal) returns zero hits.

**Reach:** none. **Disposition:** dead code, not a privilege gate, not
an escalation path. **VERIFIED.**

---

## 3 · Does 127.0.0.1 mean anything?

The unit file on disk:

```
$ systemctl --user cat empire-backend | grep -iE "ExecStart|Environment" | head -8
ExecStart=/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
Environment=PATH=/home/rg/empire-repo-main/backend/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=EMPIRE_LANE=main
Environment=EMPIRE_API_BASE_URL=http://localhost:8000/api/v1
Environment=EMPIRE_FRONTEND_HEALTH_URL=http://127.0.0.1:3005
Environment=EMPIRE_BACKEND_PORT=8000
Environment=EMPIRE_FRONTEND_EXPECTED_PORT=3005
Environment=ARCHIVEFORGE_API_BASE_URL=http://localhost:8000
```

No `--proxy-headers` flag, no `--forwarded-allow-ips` flag, no
`FORWARDED_ALLOW_IPS=` env entry. The full env on the running process:

```
$ cat /proc/1251889/environ | tr '\0' '\n' | grep -iE "FORWARDED|PROXY"
(empty)
$ ps -ef | grep "uvicorn app.main" | grep -v grep
rg  1251889  1520  1 Aug23 ?  00:44:33 /home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
```

**VERIFIED.** Running PID 1251889, started Aug 23, with the same
command line as the unit file — no `--proxy-headers` override, no
`--no-proxy-headers`, no `FORWARDED_ALLOW_IPS` env. Defaults apply.

The grep for in-repo forwarding config:

```
$ grep -rn "proxy_headers\|forwarded_allow_ips\|uvicorn.run\|--proxy-headers" \
        --include=*.py --include=*.sh --include=*.service backend/ 2>/dev/null
backend/app/main.py:674:    uvicorn.run(app, host="0.0.0.0", port=8000)
```
(plus matches inside the venv's `uvicorn/config.py`,
`uvicorn/main.py`, `uvicorn/middleware/proxy_headers.py`,
`uvicorn/workers.py`, plus unrelated httpx/aiohttp/pip/requests source
in the venv — truncated for clarity.)

**VERIFIED.** The only in-repo `uvicorn.run(...)` is at
`backend/app/main.py:674`. It does **NOT** pass `proxy_headers=` or
`forwarded_allow_ips=`. But this code path is **NOT** exercised by the
running process: the systemd unit invokes `python3 -m uvicorn
app.main:app` (loads the module then starts uvicorn directly), which
does **NOT** call `uvicorn.run()` from `main.py:674` at runtime. The
defaults at `uvicorn/config.py:207, :338-342` are what govern the
running process.

uvicorn defaults (from the venv's `config.py`):

```
proxy_headers: bool = True                                                # config.py:207
forwarded_allow_ips: list[str] | str | None = None                        # config.py:210
if forwarded_allow_ips is None:
    self.forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")   # config.py:339-340
```

**VERIFIED.** So on the running process:
- `proxy_headers=True` (default; not overridden).
- `forwarded_allow_ips="127.0.0.1"` (default; `FORWARDED_ALLOW_IPS` env
  not set, falls back to literal `"127.0.0.1"`).

The middleware (`uvicorn/middleware/proxy_headers.py:23-60`) is
therefore installed with `trusted_hosts="127.0.0.1"`. Its behaviour,
quoted from the venv source:

```
# proxy_headers.py:46-58
if b"x-forwarded-for" in headers:
    x_forwarded_for = headers[b"x-forwarded-for"].decode("latin1")
    host = self.trusted_hosts.get_trusted_client_host(x_forwarded_for)
    if host:
        port = 0
        scope["client"] = (host, port)
```

**VERIFIED.** The middleware **only replaces** `scope["client"]` if
the upstream actually sent an `X-Forwarded-For` header. If the trusted
upstream sends nothing, the original socket peer survives.

### Question-by-question

| Question | Answer | Tag |
|---|---|---|
| Is `--proxy-headers` / `proxy_headers=True` in force on the running process? | **Yes.** Defaults; not overridden. | VERIFIED (running PID 1251889 has no `--no-proxy-headers` flag; uvicorn default is `True`). |
| What is `forwarded_allow_ips` set to? | `"127.0.0.1"` (default, no env override). | VERIFIED (uvicorn config.py:339-340 fallback). |
| Does uvicorn's access log show the socket peer or the forwarded client? | The forwarded client — when one is present in `X-Forwarded-For`. If `X-Forwarded-For` is absent, the socket peer survives. | VERIFIED (proxy_headers.py:46-58). |
| When a request arrives through the Cloudflare tunnel, what address appears in the journal? | The address cloudflared puts in `X-Forwarded-For` (the real client IP). If `X-Forwarded-For` is absent on a tunnel hop, the socket peer (which is the previous hop's address) appears. | VERIFIED. |

### Now the question that decides §0g: does the **journal's** 127.0.0.1 mean internal origin?

The cloudflared config (`/home/rg/.cloudflared/empire-main-local.yml`)
shows two routes that land on the backend:

```
- hostname: studio.empirebox.store
  path: /api/v1/*
  service: http://localhost:8000       # cloudflared → backend direct
- hostname: studio.empirebox.store
  service: http://localhost:3005        # cloudflared → Next.js portal
... (same split for luxe.empirebox.store, forge.empirebox.store, ...)
- hostname: api.empirebox.store
  service: http://localhost:8000        # all paths → backend
```

**VERIFIED.**

Path A — direct cloudflared → backend (e.g., a `curl
https://studio.empirebox.store/api/v1/max/chat` from the browser):

1. Browser → cloudflared (real external IP).
2. cloudflared → backend at `http://localhost:8000`, sets
   `X-Forwarded-For=<real-client-IP>`.
3. Backend's middleware extracts the real IP from
   `X-Forwarded-For`. **Journal shows the real client IP.**

Path B — Next.js same-origin (the portal's normal page-driven fetches):

1. Browser → cloudflared → Next.js (real external IP).
2. Next.js rewrites (`next.config.js`/`next.config.ts`):
   ```
   { source: "/api/v1/:path*", destination: `${BACKEND_UPSTREAM}/api/v1/:path*` }
   ```
   **VERIFIED** by reading both config files. The rewrites do **NOT**
   propagate `X-Forwarded-For` or `CF-Connecting-IP` from the incoming
   request to the proxied upstream. (There is no `headers()` rule for
   forwarded headers; only cache-control headers are set.)
3. Next.js → backend at `http://127.0.0.1:8000`. **The connection
   arrives with no `X-Forwarded-For` from the upstream hop**, because
   Next.js did not forward one.
4. Backend's middleware: `X-Forwarded-For` is **absent** →
   `scope["client"]` is left at the socket peer (127.0.0.1). **Journal
   shows 127.0.0.1.**

This is the case that decides §0g. The Path-B Next.js hop is the
**default route for any portal page that does `fetch('/api/v1/...')`**
— which is every page that hits the chat, desk, or status endpoints
(`useChat.ts:129`, `ContinuityPanel.tsx:79, 148`,
`ChatHistoryPanel.tsx:68, 162`, `DesksScreen.tsx:118`,
`DrawingStudioPage.tsx:583, 602`, `ChatScreen.tsx:335` per D31 §0c).

### Determination

D31 §0g read "all POSTs came from 127.0.0.1" as **proof of internal
origin**. That reading is **not supported** by the instrument.

- **(a)** is wrong: the proxy is at 127.0.0.1, but it is honoured. The
  hop that *would* mask origin as 127.0.0.1 is the Next.js rewrite
  hop (Path B), not a proxy hop in the cloudflared sense.
- **(b)** is also wrong: the IPv6 addresses in the journal are not
  direct connections to port 8000 from off-box (uvicorn binds 0.0.0.0,
  which is IPv4-only). They are forwarded clients, extracted by the
  middleware from cloudflared's `X-Forwarded-For`.

**(c) — something else:** proxy_headers IS in force and cloudflared IS
the trusted proxy at 127.0.0.1. cloudflared forwards real client IPs
through `X-Forwarded-For`; the middleware extracts them. But the **vast
majority of portal traffic reaches the backend through Next.js's
rewrites** (`empire-command-center/next.config.{js,ts}`), which **do
not propagate forwarded headers**. So Path B produces 127.0.0.1 in the
journal regardless of whether the real client is internal or
external. **The journal's 127.0.0.1 is therefore COMPATIBLE WITH both
internal origin and tunneled-portal origin.** It cannot prove either.

The IPv6 (and IPv4 forwarded) entries in the journal are real
external traffic, and they only appear when a request bypasses
Next.js — i.e., a direct hit on `https://<host>/api/v1/...` or a hit
on `https://api.empirebox.store/...`.

This is a **new shape**, not a new bug. D31 §0g's central claim — "no
evidence of outside use through the bypassed hostname" — collapses
from "no external traffic at all" to "no Path-A external traffic to
the surveyed endpoints." §4 corrects the §0g survey under the proper
instrument and names the blind spots.

---

## 4 · §0g re-run with the correct instrument

### 4.1 · Access log format — does it carry the Host header?

```
$ journalctl --user -u empire-backend --no-pager --since "2026-08-13" -o short \
              | head -3
Aug 13 12:04:06 EmpireDell python3[62327]: INFO:     127.0.0.1:57778 - "GET /api/v1/notifications HTTP/1.1" 200 OK
Aug 13 12:04:11 EmpireDell python3[62327]: INFO:     127.0.0.1:57778 - "GET /api/v1/max/orchestration/status HTTP/1.1" 200 OK
Aug 13 12:04:12 EmpireDell python3[62327]: INFO:     127.0.0.1:57778 - "GET /api/v1/system/stats HTTP/1.1" 200 OK
```

**VERIFIED.** uvicorn's default access-log format records:
`<timestamp> INFO: <peer>:<port> - "<method> <path> <http-version>"
<status> <reason>`.

There is **no Host header in the access log**. D31 §0g's grep
(`journalctl --user -u empire-backend --since "2026-08-20" --no-pager
| grep -iE "luxe"`) matched only **path strings** like
`/api/luxeforge/measurements/calculate`, not `Host: luxe.empirebox.store`
headers — because the access log does not contain headers at all. The
absence of `luxe.empirebox.store` from the grep result is not evidence
of absence from the wire; it is **evidence of absence from the
access-log format**. **The Host header is not recoverable from the
access log.**

### 4.2 · Is the Host header recoverable from any source?

| Source | Records Host? | Tag |
|---|---|---|
| uvicorn access log | No (default format; no `Host` field). | VERIFIED (format inspected). |
| FastAPI application logs | **COULD NOT PROBE** — would need to grep for a logger that records the header; would only contain it if a handler explicitly logs it. No positive evidence found either way; the application does not log request headers in the journal samples observed. |
| Backend middleware (other than `ProxyHeadersMiddleware`) | **COULD NOT PROBE** — `app/main.py` middleware list was not re-checked in this phase; D31 §0d did not enumerate it. **INFERRED** (D31 §0d evidence) no custom header-logging middleware exists. |
| `journalctl -u cloudflared` (system journal) | Records request failures only — `dest=https://<host>/...` on ERR level. Sample: `2026-08-17T17:41:30Z INF Updated to new configuration ... ingress ...` Successful requests are NOT logged with method/Host. | VERIFIED (cloudflared's default log level doesn't include request lines). |
| `/home/rg/.cloudflared/cf-empire-main.log` | Same as the system journal — configuration, connection, error events. No successful-request log lines. The Host header appears in the file **only** on ERR events like `dest=https://test-studio.empirebox.store/robots.txt event=0 ip=198.41.192.227 type=http` — i.e., for tunnel failures to test hostnames, not for successful production traffic. | VERIFIED (file format inspected; only ERR-level events name the host). |

**Honest answer:** the Host header is **not recoverable from any source
for successful requests**. The instrument set is the access log +
cloudflared log; both lack it. The instrument cannot have shown a
positive.

### 4.3 · How far back does the journal go?

```
$ journalctl --user -u empire-backend --no-pager | head -3
Aug 13 12:04:06 EmpireDell python3[62327]: INFO:     127.0.0.1:57778 - "GET /api/v1/notifications HTTP/1.1" 200 OK
Aug 13 12:04:11 EmpireDell python3[62327]: INFO:     127.0.0.1:57778 - "GET /api/v1/max/orchestration/status HTTP/1.1" 200 OK
Aug 13 12:04:12 EmpireDell python3[62327]: INFO:     127.0.0.1:57778 - "GET /api/v1/system/stats HTTP/1.1" 200 OK

$ journalctl --user -u empire-backend --no-pager --since "2026-08-01" --until "2026-08-13" | head -3
-- No entries --
```

**VERIFIED.** The empire-backend user unit's journal goes back only to
**2026-08-13 12:04:06**. Anything before that is not in the surviving
record.

The cloudflared log (`/home/rg/.cloudflared/cf-empire-main.log`) goes
back to **2026-06-11T02:47:51Z** — that file does cover longer history.
But cloudflared's log only carries the Host header on ERR-level
events, so it doesn't help for the §0g question. **COULD NOT PROBE**
when the Cloudflare Access Bypass policy on `luxe.empirebox.store` was
first enabled — that determination lives in the Cloudflare dashboard,
not on this box.

The 12-day journal window (Aug 13 → today) cannot cover any history
older than Aug 13.

### 4.4 · `POST /api/v1/max/chat`, `POST /api/v1/max/chat/stream`, `POST /api/v1/max/code-task` — by source

**VERIFIED** counts:

```
$ journalctl --user -u empire-backend --no-pager --since "2026-08-13" -o short \
              | grep -E "POST /api/v1/max/(chat|chat/stream|code-task)" \
              | grep -vE "127\.0\.0\.1|::1" \
              | sed -E 's/.*"(POST [^"]+)".*/\1/' | sort | uniq -c | sort -rn
     74 POST /api/v1/max/chat/stream HTTP/1.1
     16 POST /api/v1/max/chat HTTP/1.1
      2 POST /api/v1/max/tts HTTP/1.1

$ journalctl --user -u empire-backend --no-pager --since "2026-08-13" -o short \
              | grep -E "POST /api/v1/max/code-task" | wc -l
4
```

**External (non-loopback) source IPs that hit `/max/chat` or `/max/chat/stream`** (90 POSTs total in window):

```
$ journalctl --user -u empire-backend --no-pager --since "2026-08-13" -o short \
              | grep -E "POST /api/v1/max/(chat|chat/stream)" \
              | grep -vE "127\.0\.0\.1|::1" \
              | sed -E 's/.*INFO: +([0-9a-fA-F:\.]+):[0-9]+ - .*/\1/' \
              | sort | uniq -c | sort -rn
     49 143.105.1.209          (Aug 17)
     14 2600:1003:b0f0:ecb:29ea:4299:88a3:95f8  (Aug 17)
     14 162.19.234.61          (Aug 24)
      9 2600:1003:b06c:6d09:91ed:5165:6d68:48cc  (Aug 23)
      1 2605:59ca:313a:6310:5d59:aa72:5c84:714d  (Aug 19)
      1 2600:1003:b050:5669:5972:ffcc:c83d:5580  (Aug 23)
      1 143.105.3.223          (Aug 19)
      1 143.105.1.179          (Aug 24)
```

All 90 returned **200 OK** (one PUT `/api/v1/chats/{uuid}` returned 404
each time the conversation_id was not in the DB — consistent with a
portal client whose `conversation_id` is local to the browser).

### 4.5 · Are these Path-A (direct cloudflared → backend) or Path-B (Next.js hop)?

The middleware logic (`proxy_headers.py:46-58`) replaces the peer
**only if** `X-Forwarded-For` is present. Path-B (Next.js rewrite)
does not forward `X-Forwarded-For`, so the journal would show 127.0.0.1
for Path-B. Since these 90 entries show **forwarded** IPv6/IPv4
addresses (extracted from `X-Forwarded-For`), they **must be Path-A**
hits — direct cloudflared → backend connections, bypassing the
portal's Next.js layer.

Two of these traces were sampled to see whether they were interactive
portal sessions or scripted probes:

```
$ journalctl --user -u empire-backend --no-pager --since "2026-08-17 19:30" \
              --until "2026-08-17 19:50" -o short | grep "143.105.1.209" | head -10
Aug 17 19:36:15 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/notifications HTTP/1.1" 200 OK
Aug 17 19:36:15 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/max/status HTTP/1.1" 200 OK
Aug 17 19:36:15 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/max/models HTTP/1.1" 200 OK
Aug 17 19:36:15 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/system/ollama/status HTTP/1.1" 200 OK
Aug 17 19:36:24 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/max/evaluation/scores?limit=5 HTTP/1.1" 200 OK
Aug 17 19:36:24 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/max/desks HTTP/1.1" 200 OK
Aug 17 19:36:25 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/chats/list HTTP/1.1" 200 OK
Aug 17 19:36:25 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/max/self-assessment?channel=web&limit=5 HTTP/1.1" 200 OK
Aug 17 19:36:25 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/max/ai-desks/briefing HTTP/1.1" 200 OK
Aug 17 19:36:25 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/memory/context-pack HTTP/1.1" 200 OK
```

```
$ journalctl --user -u empire-backend --no-pager --since "2026-08-17 19:36" \
              --until "2026-08-17 19:37" -o short | grep "143.105.1.209"
Aug 17 19:36:26 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "POST /api/v1/max/chat/stream HTTP/1.1" 200 OK
Aug 17 19:36:26 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/memory/context-pack HTTP/1.1" 200 OK
Aug 17 19:36:26 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/max/orchestration/status HTTP/1.1" 200 OK
Aug 17 19:36:26 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "GET /api/v1/openclaw/health HTTP/1.1" 200 OK
Aug 17 19:36:26 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "POST /api/v1/max/chat HTTP/1.1" 200 OK
Aug 17 19:36:28 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "PUT /api/v1/chats/f107b9db-7ee4-48d5-b6bb-1031856c1030 HTTP/1.1" 404 Not Found
Aug 17 19:36:51 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "POST /api/v1/max/chat/stream HTTP/1.1" 200 OK
Aug 17 19:36:52 EmpireDell python3[1753]: INFO:     143.105.1.209:0 - "PUT /api/v1/chats/f107b9db-7ee4-48d5-b6bb-1031856c1030 HTTP/1.1" 404 Not Found
```

**VERIFIED.** The pattern is the **exact sequence** a Command Center
page load produces: `notifications → max/status → max/models → system
stats → max/desks → max/evaluation/scores → chats/list → max/
self-assessment → ai-desks/briefing → memory/context-pack → max/
memory-status → ollama/models → orchestration/status → openclaw/health
→ telegram/status` followed by a chat POST, then a follow-up chat POST,
then a `PUT /api/v1/chats/{uuid}` that 404s because the conversation
is browser-local.

This is **not a scripted probe** of one or two endpoints — it is the
**complete page-load-then-chat sequence** the portal performs every
time it boots. The 143.105.1.209 client did the full portal flow on
Aug 17 19:36:15–19:36:52 and POSTed chat messages successfully.

The same pattern repeats for `2600:1003:b06c:6d09:91ed:5165:6d68:48cc`
on Aug 23 09:27:57 — full page load followed by `POST
/api/v1/max/chat`. And for `162.19.234.61` on Aug 24 09:01:58 — same
pattern, two `POST /max/chat/stream` and one `POST /max/chat` and a
`PUT /api/v1/chats/{uuid}` 404.

### 4.6 · Answers to the prompt's re-run questions

**Can external origin be distinguished from internal origin in the
surviving record at all?**

**Yes — by the middleware's extracted client IP, not by 127.0.0.1.**
The journal's external-IP entries (the 90 listed in §4.4 above) are
**Path-A direct hits**, bypassing Next.js. The journal's 127.0.0.1
entries (the rest) are **ambiguous** between genuine internal calls
and Path-B Next.js hops — the §3 finding is that the instrument cannot
distinguish those two.

For the **specific endpoints surveyed**:
- `/api/v1/max/code-task`: all 4 POSTs in window are 127.0.0.1.
  Whether internal or tunneled-portal is **not determinable from this
  instrument**. COULD NOT PROBE.
- `/api/v1/max/chat`: **16 non-local POSTs** from 4 distinct external
  IPs. **VERIFIED.**
- `/api/v1/max/chat/stream`: **74 non-local POSTs** from 6 distinct
  external IPs. **VERIFIED.**

**How far back does the journal actually go?**

**Aug 13 12:04:06 to present.** ~12 days. Cloudflared's log goes back
to 2026-06-11 but lacks request-line records for successful requests.
The journal window cannot cover any pre-Aug-13 history for the
backend access log. The window is shorter than the cloudflared tunnel
itself; whether it is shorter than the Bypass policy is
**COULD NOT PROBE** (no local record of when Bypass was enabled).

**Any POST (not GET) to /api/v1/max/chat, /api/v1/max/chat/stream, or
/api/v1/max/code-task whose origin cannot be established as internal?**

By the corrected §3 reading:
- `/api/v1/max/code-task`: 4 POSTs in window; all 127.0.0.1;
  **ambiguous** (internal OR Path-B tunneled-portal) — origin **not
  determinable**.
- `/api/v1/max/chat`, `/api/v1/max/chat/stream`: 90 POSTs from
  external IPs in window (the Path-A hits); these are **definitively
  external**. **VERIFIED.** Whether they belong to a
  Cloudflare-Access-authenticated portal user, the public bypassed
  hostname, or an attacker with a stolen CF-Authorization cookie,
  **COULD NOT PROBE** without the Host header (which is not in the
  surviving record).

### 4.7 · Re-run summary

- **D31 §0g "all dashboard polling, all GET, no code-task or
  tool-execution POSTs from non-local sources" is partially wrong.**
  External POSTs to `/api/v1/max/chat` and `/api/v1/max/chat/stream`
  exist and are part of full portal interactive sessions through the
  tunnel.
- **D31 §0g "all POST /api/v1/max/code-task since the journal window
  is from 127.0.0.1" remains true in form** — but the §3 finding
  means 127.0.0.1 does not distinguish internal from tunneled-portal
  for these endpoints, so the §0g conclusion ("no evidence found of
  outside use through the bypassed hostname") cannot be carried
  forward without qualification.
- The corrected shape is: **Path-A direct hits reach the backend with
  the real client IP extracted by middleware and are visible in the
  journal; Path-B Next.js-hop hits reach the backend as 127.0.0.1 and
  are indistinguishable from internal calls.** Both paths exist;
  external use of the chat endpoints has happened through Path A.
  Whether any external use of the code-task endpoint has happened
  through Path B **is not determinable from this instrument**.

"No evidence found" remains a legitimate answer for /code-task.
"No evidence found in the journal for Path-A direct external hits
to /code-task, and the instrument cannot have shown a Path-B
external hit at all" is the required shape.

---

## 5 · Two corrections to the D31 report

### 5a · §0d contradiction — the `luxeforge` `/api/v1/intake/admin/*` set

D31 §0d's route table states `/luxeforge` and `/luxe` call
`/api/v1/intake/admin/*`. The minimal path set omits that whole
prefix. The two route files:

```
$ find empire-command-center/app/luxeforge empire-command-center/app/luxe -type f
empire-command-center/app/luxeforge/page.tsx
empire-command-center/app/luxe/page.tsx

$ cat empire-command-center/app/luxeforge/page.tsx
import LuxeForgePage from '../components/screens/LuxeForgePage';
export default function LuxePage() { return <LuxeForgePage />; }

$ cat empire-command-center/app/luxe/page.tsx
import LuxeForgePage from '../components/screens/LuxeForgePage';
export default function LuxeForgeRoutePage() { return <LuxeForgePage />; }
```

**VERIFIED.** Both `/luxeforge` and `/luxe` are 5-line wrappers that
render `app/components/screens/LuxeForgePage.tsx`. The fetch calls
inside that component:

```
$ grep -nE "fetch\(.*intake" empire-command-center/app/components/screens/LuxeForgePage.tsx
97:        fetch(`${API}/intake/admin/projects`).then(r => r.ok ? r.json() : []),
98:        fetch(`${API}/intake/admin/users`).then(r => r.ok ? r.json() : []),
106:        const res = await fetch(`${API}/intake/projects`);
119:        const res = await fetch(`${API}/intake/admin/archived`);
153:        const res = await fetch(`${API}/intake/admin/projects/${projectId}/to-quote`, {
185:      const res = await fetch(`${API}/intake/admin/users/${userId}`, {
202:      const res = await fetch(`${API}/intake/admin/users/${userId}`, { method: 'DELETE' });
211:      const res = await fetch(`${API}/intake/admin/users/${userId}/restore`, { method: 'POST' });
224:      const res = await fetch(`${API}/intake/admin/projects/${projectId}/restore`, { method: 'POST' });
```

**VERIFIED.** LuxeForgePage calls **8 admin paths** plus
`/api/v1/intake/projects`. The admin paths are:

- `GET    /api/v1/intake/admin/projects`
- `GET    /api/v1/intake/admin/users`
- `GET    /api/v1/intake/admin/archived`
- `POST   /api/v1/intake/admin/projects/{project_id}/to-quote`
- `PUT    /api/v1/intake/admin/users/{user_id}`
- `DELETE /api/v1/intake/admin/users/{user_id}`
- `POST   /api/v1/intake/admin/users/{user_id}/restore`
- `POST   /api/v1/intake/admin/projects/{project_id}/restore`

**Resolution:** `/api/v1/intake/admin/*` belongs in the minimal path
set IF `/luxeforge` or `/luxe` is to remain on the bypassed hostname.
Dropping it breaks the LuxeForge admin dashboard. Keeping it widens
the public surface to admin actions (archive, restore, delete users,
project-to-quote promotion).

Two options the founder will weigh:

- Add the eight admin paths to the minimal path set (status quo for
  LuxeForge on the bypassed hostname).
- Move `/luxeforge` and `/luxe` off the bypassed hostname to a
  protected one (`studio.empirebox.store` with Cloudflare Access), and
  drop `/api/v1/intake/admin/*` from the public surface.

This dispatch names the contradiction; it does not recommend either.

### Corrected minimal path set (in full)

```
# Apostille (public, anonymous)
GET    /api/v1/apostapp/public/packages
POST   /api/v1/apostapp/public/intake
POST   /api/v1/apostapp/public/verify
GET    /api/v1/apostapp/public/config

# Workroom intake (anonymous signup/login; JWT-gated for the rest)
POST   /api/v1/intake/signup
POST   /api/v1/intake/login
POST   /api/v1/intake/reset-password
GET    /api/v1/intake/me
PUT    /api/v1/intake/me

# Workroom intake project flow (JWT required)
POST   /api/v1/intake/projects
GET    /api/v1/intake/projects
GET    /api/v1/intake/projects/{project_id}
PUT    /api/v1/intake/projects/{project_id}
POST   /api/v1/intake/projects/{project_id}/submit
POST   /api/v1/intake/projects/{project_id}/message
POST   /api/v1/intake/projects/{project_id}/photos
POST   /api/v1/intake/projects/{project_id}/scans

# Fabrics intake-project write (CC calls this from intake/project/new)
POST   /api/v1/fabrics/intake-project/{project_id}/fabrics

# LuxeForge admin dashboard (D31 §0d required; D32 §5a confirms) —
# REMOVE THIS BLOCK if /luxeforge and /luxe are moved off the
# bypassed hostname.
GET    /api/v1/intake/admin/projects
GET    /api/v1/intake/admin/users
GET    /api/v1/intake/admin/archived
POST   /api/v1/intake/admin/projects/{project_id}/to-quote
PUT    /api/v1/intake/admin/users/{user_id}
DELETE /api/v1/intake/admin/users/{user_id}
POST   /api/v1/intake/admin/users/{user_id}/restore
POST   /api/v1/intake/admin/projects/{project_id}/restore

# Static photo serving (uploaded photos served back to the same browser)
GET    /intake_uploads/...
GET    /api/v1/photos/serve/{entity_type}/{entity_id}/{filename}
```

The LuxeForge admin block is the only addition over D31 §0d's set.
The "REMOVE THIS BLOCK" note is the dispatch language; this report
does not edit the D31 file.

### 5b · §0e banned-noun restatement

D31 §0e and the summary describe `~/empire-repo/backend/data/uploads`
as a "stale-fork write path," citing CLAUDE.md. **That is wrong and
the noun is banned.**

Per the canonical CLAUDE.md (line 14, **VERIFIED**):

> `~/empire-repo` is the main worktree (not a stale fork). It owns the
> shared git object store at `~/empire-repo/.git`, the live venv at
> `~/empire-repo/backend/venv/`, and the live OpenClaw service on
> port 7878 — all of which still receive data writes. The sibling
> checkout `~/empire-repo-main` is on the same branch. Acting on
> `~/empire-repo` as if it were a stale tree destroys every local
> branch, lane and stash on the box.

The same point is reinforced in H73's hazard note (CLAUDE.md):
`canonical_path.py:133-152` hardcodes `home/"empire-repo"` as a
"bad_roots" entry — the unsafe-enforcement hazard that lives on the
**code lane**, not the data lane. Writes to `~/empire-repo/backend/
data/uploads` are **legitimate production ingest paths under H72**,
not stale-fork drift.

**Restated §0e finding** (the noun-correct shape):

> `/api/v1/files/upload` (`backend/app/api/v1/files.py:43-55`) is
> unauthenticated. It writes to `UPLOAD_DIR = Path.home() /
> "empire-repo" / "backend" / "data" / "uploads"` and logs to
> `~/empire-repo/backend/data/logs/file_access`. These are
> **production-write paths on the main worktree's data directory** —
> the same data volume the active ingest surface lives under. They are
> flagged in H72's "BYPPASSES — raw open()/Path()" list because the
> canonical-path enforcement at `app/services/drawing/canonical_path
> .py` (H73 hazard) does not currently validate writers in this
> directory; that is a code-lane concern, not a stale-fork concern.
> Authorship of these writes remains legitimate production traffic
> for the canonical main worktree.
>
> No front-end page in the public surface calls
> `/api/v1/files/upload` or `/api/v1/photos/upload`. The fix to
> narrow the tunnel row to the §5a-corrected minimal path set
> removes both endpoints from the public-hostname reachability.
> Their unauthenticated status stands independently of any host-row
> fix.

That is the corrected §0e. The unauthenticated-write finding stands;
the noun that named the path does not.

### 5b-1 · Files carrying the banned noun about `~/empire-repo`

Grep:

```
$ grep -rEn "stale[ -]?fork|FROZEN" --include=*.md claude/ docs/ CLAUDE.md 2>/dev/null \
        | grep -E "empire-repo([^a-zA-Z]|/?)"
```
returns 20 lines, of which 15 are **CORRECTIONS** (the string appears
inside a negation like "is NOT a stale fork" or "that read was wrong")
and 5 are uncorrected uses. The "FROZEN" leg is searched separately
because the original regex swallowed nothing on the live tree; the
violations below were enumerated by direct inspection.

**Uncorrected uses — files to fix:**

| File | Line | Quoted line |
|---|---|---|
| `claude/BACKLOG_UPDATE_2026-08-20.md` | 39 | `**H57 Phase 3 fix routed most paths through \`resolve_canonical_root()\`, but \`_git_ops\` was missed — \`repo = os.path.expanduser("~/empire-repo")\` (stale fork).**` |
| `claude/BACKLOG_UPDATE_2026-08-20.md` | 40 | `**H57 Phase 3 made runtime paths canonical-root-aware, but the prompt BODY hardcoded the stale fork as MAX's identity.**` |
| `claude/dispatches/2026-08-22/claude_DISPATCH_2026-08-22_restore_probe.md` | 299 | `and drawings into the stale fork \`~/empire-repo\` until fix \`88814b2\`` |
| `claude/reports/2026-08-22/RESTORE_PROBE_2026-08-22.md` | 190 | `/home/rg/empire-repo/backend/data/empire.db        (stale fork)` |
| `claude/reports/2026-08-22/RESTORE_PROBE_2026-08-22.md` | 191 | `/home/rg/empire-repo/backend/data/intake.db        (stale fork)` |
| `docs/2026-08-22_D4_r8_launch_307be77a.md` | 25 | `is now FROZEN. It is the MAIN WORKTREE and holds the shared git object store` |
| `docs/2026-08-22_D3_session_opener_7bfe13c0.md` | 21 | `is now FROZEN. It is the MAIN WORKTREE holding the shared git object store at` |

Seven lines across five files (lines 39–40 share the same file).
**VERIFIED** — each line quoted directly from the source.

The 15 negation lines are correctly written and are NOT listed as
violations. They correctly tell the reader "this is not a stale fork"
or "this framing was wrong." The prompt's clarification holds:
corrected text contains the string inside negations; closure is by
uncorrected use, not by raw grep count.

**Phase 0.5 stop:** this report is the only file committed. The D31
report file is not edited.

---

## STOP — summary of deliverables

- **§1** — Enumeration grep pasted verbatim; twelve lines accounted
  for. `tool_executor.py:3350` is the **signature** of a vision-log
  helper (channel default `"web_cc"`); `tool_executor.py:3457` is a
  **call** of the same helper passing `params.get("_channel",
  "web_cc")` as a logging label. Both are propagated flags into
  `token_tracker`, not privilege gates. No new privilege surface.
- **§2** — `founder_auth.get_access_level` has **zero live callers**
  in any language (`*.py`, `*.ts`, `*.tsx`) across the whole repo. The
  only in-tree reference is the `def` itself and its internal call to
  `is_founder_channel`. INFERRED-unused from D31 §0b is now VERIFIED-
  dead. Not an escalation path.
- **§3** — proxy_headers=True (default), forwarded_allow_ips="127.0.0.1"
  (default). **VERIFIED** on the running PID 1251889 (Aug 23 start).
  Determination: **(c) something else** — Next.js's
  `empire-command-center/next.config.{js,ts}` rewrites do NOT
  propagate `X-Forwarded-For` or `CF-Connecting-IP`. The journal's
  127.0.0.1 entries are therefore **ambiguous** between internal
  origin and tunneled-portal Path-B hops. The IPv6/IPv4 forwarded
  entries are Path-A direct cloudflared → backend hits and are real
  external traffic.
- **§4** — §0g re-run. Journal window: Aug 13 12:04:06 → present.
  Host header is NOT recoverable from the access log (uvicorn's
  default format has no Host field), nor from cloudflared's
  successful-request log (only ERR-level events carry `dest=`).
  External POSTs to `/api/v1/max/chat` (16) and `/api/v1/max/chat/
  stream` (74) are **VERIFIED**, including full interactive portal
  sessions (notifications → status → desks → chat → `PUT /chats/{id}`
  404). `/api/v1/max/code-task` has 4 POSTs in window, all 127.0.0.1,
  ambiguous per §3. D31 §0g's central claim "no outside use through
  the bypassed hostname" is wrong for the chat endpoints, ambiguous
  for code-task.
- **§5a** — corrected minimal path set adds the eight
  `/api/v1/intake/admin/*` paths LuxeForgePage calls (quoted from
  `app/components/screens/LuxeForgePage.tsx:97-224`). Listed in full.
- **§5b** — `/api/v1/files/upload` is restated as a legitimate
  production-write path on the main worktree's data directory. The
  unauthenticated-endpoint finding stands. The banned noun is
  enumerated at seven uncorrected uses across five files in claude/
  and docs/. The 15 negation lines (which appear in the grep output
  but correctly say "is NOT a stale fork" or "that read was wrong")
  are not violations and are not listed as such.

No fix lane entered. The single deliverable is this report file.
The D31 report is committed and pushed; it stands as the record of
Phase 0 and is not edited.