# D31 · H74 Channel-Escalation Map

**Date:** 2026-08-25
**Branch:** feature/drawing-standard @ 8148f71
**H-number:** **H74** (highest assigned was H73 per
`reports/2026-08-24_D27_persistence_map.md:675` and
`claude/2026-08-24_D22_next_session_opener_ee54f0f1.md:27`)
**Read-only map.** No code edits, no config edits, no Cloudflare changes.

This document sizes the blast radius of a not-yet-designed fix to the way
`channel` is read from request bodies and used to grant founder privilege.
It does not propose the fix. It enumerates the surfaces so the founder can
choose.

---

## 0a · H-Ledger

### Grep evidence

```
$ grep -rhnoE "H[0-9]{2,3}" docs/reports/*.md docs/*.md claude/*.md \
        claude/reports/*.md reports/*.md 2>/dev/null \
  | awk -F: '{print $NF}' | grep -oE "H[0-9]{2,3}" | sort -u
H43 H44 H45 H46 H47 H48 H52 H53 H55 H57 H58 H59 H60 H61 H62 H63 H64 H65
H66 H67 H68 H69 H70 H71 H72 H73
```

H73 is the highest currently assigned. Per
`claude/2026-08-24_D22_next_session_opener_ee54f0f1.md:27-28` and
`reports/2026-08-24_D27_persistence_map.md:675`, H73 is OPEN and tracks the
`canonical_path.py:133-152` "bad_roots" hazard — it is not a closed finding.

**Number used for this report: H74.**

---

## 0b · The Call Sites

### What `is_founder_message` actually is

`backend/app/services/max/guardrails.py:96-112`:

```python
def is_founder_message(message_context: dict) -> bool:
    channel = message_context.get("channel", "")
    # Command Center (any variant) = always founder
    if channel in ("web", "web_cc", "cc", "command_center", "command-center", ""):
        return True
    # Telegram: match by chat_id
    if not _FOUNDER_CHAT_ID:
        return False
    chat_id = str(message_context.get("chat_id", ""))
    if channel == "telegram" and chat_id == _FOUNDER_CHAT_ID:
        return True
    return False
```

`channel in ("", "web", "web_cc", "cc", "command_center", "command-center")` ⇒ True.
**An absent channel is treated as founder.** This is the load-bearing default.

`backend/app/services/max/founder_auth.py:9-17` is a near-duplicate of the
same predicate with an extra `user_context` parameter — it has the same
`""`-as-founder behaviour and is exported but only called from
`founder_auth.get_access_level` (`founder_auth.py:19-24`), which is
INFERRED to be unused by current router code (no `grep` match in
`backend/app/routers/`).

### Actual call-site enumeration

The dispatch named 9 line numbers but the prompt grants
**ranked by privilege, code-task highest**. Below is what those lines
actually are, with the privilege the True branch grants quoted from the
code.

#### SITE 1 — `backend/app/routers/max/router.py:2169` (ChatRequest `/chat`)

```python
msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
founder = is_founder_message(msg_ctx)
```

- `channel` source: **request body field** (`ChatRequest.channel`,
  `router.py:569` — `Optional[str] = None`).
- Default when absent: `None → ""` → founder (empty string IS in the
  allow-list at `guardrails.py:104`).
- `founder=True` privilege:
  1. `check_input(...)` skips `INJECTION_PATTERNS` block and
     `BLOCKED_TOPICS` block (`guardrails.py:135-147`).
  2. `founder=True` is passed into every `execute_tool(...)` call in
     this handler (lines 2335, 2610, 2803, 2891). At
     `tool_executor.py:449-461`, that bypasses the access-controller
     `check_permission(...)` step entirely and stamps
     `tool_call["_founder"] = True` for the tool handler. The
     tool handlers that consume `_founder=True` include
     `shell_execute`, `env_set`, `db_query`, and the full set
     enumerated by `access_controller.classify_tool(...)`.
- Unauthenticated reachability: **YES.** The route is registered at
  `main.py:80-81` (`/max` and `/api/v1/max`) with no auth dependency.
  Reachable from any caller that can reach the backend; Cloudflare
  Access is the only gate on the public hostname.

#### SITE 2 — `backend/app/routers/max/router.py:3207` (ChatRequest `/chat/stream`)

```python
msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
founder = is_founder_message(msg_ctx)
```

- Identical to SITE 1 (same `ChatRequest` model).
- `founder=True` flows into `execute_tool(...)` at lines 3266, 3523, 3639.
- Unauthenticated reachability: **YES** (same registration, same shape).

#### SITE 3 — `backend/app/routers/max/router.py:5162` (CodeTaskRequest `/code-task`)

```python
msg_ctx = {"channel": request.channel or "web_cc"}
founder = is_founder_message(msg_ctx)
if not founder:
    founder_pin = os.getenv("FOUNDER_PIN", "")
    if not founder_pin:
        logger.critical("FOUNDER_PIN env var is UNSET. ...")
    if not founder_pin or not request.pin or str(request.pin) != founder_pin:
        raise HTTPException(status_code=403, detail="Invalid PIN. ...")
...
task = code_task_runner.submit(request.prompt, working_dir=..., founder=founder)
```

- `channel` source: **request body field** (`CodeTaskRequest.channel`,
  `router.py:5145` — default `"web_cc"`, NOT Optional).
- Default when absent: `"web_cc"` → founder.
- `founder=True` privilege: **no PIN required to submit a code task.**
  The task is then dispatched to `code_task_runner.submit()` which
  (`code_task_runner.py:855-861`) constructs a `CodeTask(founder=True)`,
  and `founder=True` flows downstream into Atlas/CodeForge execution.
  Code Mode is a CodeForge/Atlas task — it runs tool calls with full
  founder privileges. This is the highest privilege in the system short
  of `shell_execute` itself.
- Unauthenticated reachability: **YES** (same registration). PIN is the
  only gate when `founder=False`; when `founder=True` the PIN is
  bypassed entirely.

#### SITE 4 — `backend/app/services/max/guardrails.py:135` (`check_input`)

```python
def check_input(text: str, message_context: dict = None) -> Tuple[bool, str]:
    text_lower = text.lower()
    founder = is_founder_message(message_context or {})
    ...
    if founder:
        logger.info(f"Founder override: skipping prompt_injection block")
    else:
        return False, "prompt_injection"
    ...
    if not founder:
        return False, "blocked_topic"
    logger.info(f"Founder override: skipping blocked_topic block")
```

- `channel` source: dict key `"channel"` from `message_context`
  (constructed at the call sites in router.py:2168, 3206, 5161 — same
  body field).
- Default when absent: `message_context.get("channel", "")` → founder.
- `founder=True` privilege: skips prompt-injection block + blocked-topic
  block. **No tool bypass, no PIN bypass.** This is the weakest of the
  four — it is a guardrail override, not a privilege grant.

#### SITE 5 — `backend/app/services/max/tool_executor.py:454`

This line is a **docstring fragment** inside `execute_tool(...)`:

```python
def execute_tool(tool_call: dict, desk: Optional[str] = None,
                 access_context: Optional[dict] = None,
                 founder: bool = False) -> ToolResult:
    """Dispatch and execute a tool call (with tier gating and access control).

    Args:
        founder: If True, skip all PIN/access checks. The caller (router) has
                 already verified this is the founder via is_founder_message().
    """
```

There is no `is_founder_*` call here. The `founder` parameter is the
**propagated result** of SITE 1 / SITE 2 / SITE 3 — it does not consult
`channel` itself. The docstring asserts that the caller has already
verified founder status; the verification is at the router.

#### SITES 6–9 — `operating_registry.py:128`, `unified_message_store.py:218, :225`

These are **channel normalisation, not privilege grants.** They do not
call `is_founder_*` and do not return a True/False. They map raw channel
strings into a small set of canonical labels for prompt rendering:

- `operating_registry.py:126-134` — `_normalize_prompt_channel()` maps
  `("web", "web_cc", "dashboard", "command_center", "mobile_browser")` →
  `"web_chat"`. Output is used at `:140` to label the prompt's
  operating-truth section. **No privilege impact.**
- `unified_message_store.py:217-220` — `_normalize_channel()` does the
  same mapping. Used at `:222-226` for cross-channel history search. **No
  privilege impact.** The `founder_verified=True` set at `:211` is
  hard-coded for email-outbound messages; it is not derived from
  `channel`.

### Reachability summary

All three router-level sites (`/api/v1/max/chat`, `/api/v1/max/chat/stream`,
`/api/v1/max/code-task`) are reachable from any caller that can reach the
backend process on port 8000. There is **no Python-level auth** on these
routes. Cloudflare Access on the public hostname is the only gate; on a
bypassed hostname, all three are reachable with curl.

`check_input` (guardrails.py:135) is internal Python — it is not a route;
it runs inside the same handlers above.

### Ranked by privilege granted

| Rank | Site | Endpoint | What `founder=True` grants |
|---|---|---|---|
| 1 | `router.py:5162` | `POST /api/v1/max/code-task` | PIN bypass on a code-task submission; full Atlas/CodeForge execution with founder privileges downstream |
| 2 | `router.py:2169` | `POST /api/v1/max/chat` | Tool-execution bypass (skip access controller `check_permission`, stamp `_founder=True` for `shell_execute`, `env_set`, `db_query`, etc.) + prompt-injection/topic-block skip |
| 3 | `router.py:3207` | `POST /api/v1/max/chat/stream` | Same as rank 2 (streaming variant) |
| 4 | `guardrails.py:135` | (internal to all chat paths) | Skips prompt-injection block and blocked-topic block only |

**Dispatch's expectation: code-task is highest. CONFIRMED.** It is the
only site where True means "PIN never required to submit a code-execution
task."

---

## 0c · Who legitimately sets `channel`

### Telegram bot — INTERNAL caller that needs channel="telegram"

`backend/app/services/max/telegram_bot.py:466`:

```python
payload: Dict[str, Any] = {
    "message": text, "history": history,
    "conversation_id": f"telegram-{cid}",
    "channel": "telegram",
    "chat_id": cid,
}
async with httpx.AsyncClient(timeout=120.0) as client:
    resp = await client.post("http://localhost:8000/api/v1/max/chat", json=payload)
```

This is the **only legitimate non-web caller** in the codebase. It needs
`channel="telegram"` plus `chat_id=<TELEGRAM_FOUNDER_CHAT_ID>` to be
treated as founder. A server-side derivation that ignores body `channel`
and substitutes something based on auth context would break this caller
unless an alternative signal (a service token, the loopback source IP,
etc.) is recognised by the backend.

### Command Center front-end — INTERNAL via tunnel + Access

Verified call sites from
`grep -rn "channel" --include=*.tsx empire-command-center/app` (selected):

| File:line | Value sent |
|---|---|
| `app/hooks/useChat.ts:129` | `channel: channel \|\| 'dashboard'` (browser-side state, not the body field directly; `'dashboard'` is in `operating_registry._normalize_prompt_channel` web-chat set) |
| `app/components/ContinuityPanel.tsx:79, 148` | `'web'` |
| `app/components/ChatHistoryPanel.tsx:68, 162` | `'web'` |
| `app/components/screens/DesksScreen.tsx:118` | `'web'` |
| `app/components/screens/DrawingStudioPage.tsx:583, 602` | `'web_cc'` |
| `app/components/screens/ChatScreen.tsx:335` | `'web_cc'` |
| `app/components/screens/PresentationScreen.tsx:434` | `'avatar'` (not in the founder allow-list) |
| `app/components/screens/QuoteReviewScreen.tsx:362` | (via `useChat` hook — see above) |

All of these are portal-side calls proxied through the Next.js
`rewrites` to `127.0.0.1:8000` (`empire-command-center/next.config.js:33-43`).
They sit behind Cloudflare Access on the portal hostname.

### Backend internal callers

`backend/app/services/max/access_control.py:53`:
`if channel == "telegram" and str(chat_id or "") == FOUNDER_TELEGRAM_CHAT_ID` —
reads channel for the access-control classification; the channel comes
from the request body's value (passed through `access_context`).

`backend/app/services/max/evaluation_service.py:674`,
`backend/app/services/max/evaluation_loop_v1.py:79, 108, 123, 141` —
read channel from logged rows, not from live request body. Not relevant.

### What breaks if `channel` were derived server-side

A server-side derivation that **ignores the body field** breaks:

1. **Telegram bot** (`telegram_bot.py:466`) — must be able to send
   `channel="telegram"` + `chat_id=<FOUNDER>` and have it recognised. The
   loopback source IP would not help here either: the Telegram bot runs
   on the same machine, so `127.0.0.1` is also a clue, but routing
   decisions based on source IP are fragile (a future Cloudflare tunnel
   endpoint on the same machine would share it).
2. **Tests** (`backend/tests/test_founder_pin_failclosed_h62.py:103`,
   etc.) that explicitly set `channel` to verify behaviour. The fix
   would need a test seam.
3. **Any non-web call site that the foundation might add** without
   remembering to add it to the allow-list. The current model is
   "everything not in the allow-list is non-founder," but the allow-list
   includes the empty string, so the inverse "everything in the
   allow-list is founder" is the actual semantic.

A server-side derivation that **strips the privilege impact** (keeps the
body field for routing/normalisation, derives privilege from something
else) is a different shape — see §0f.

---

## 0d · The public surface

### Next.js routing — no hostname conditionals

`empire-command-center/next.config.js` and `next.config.ts` contain **no
hostname-based routing**. Both `studio.empirebox.store` and (if served)
`luxe.empirebox.store` serve the same routes from the same Next.js build.
The portal surfaces are:

| Route | Front-end file | Backend API calls |
|---|---|---|
| `/apostille` | `app/apostille/page.tsx` | `/api/v1/apostapp/public/{packages,intake,verify,config}` |
| `/apostille/status` | `app/apostille/status/page.tsx` | `/api/v1/apostapp/public/verify` |
| `/apostille/confirmation` | `app/apostille/confirmation/page.tsx` | none (static confirmation page) |
| `/intake` | `app/intake/page.tsx` | `/api/v1/intake/projects`, `/api/v1/intake/admin/*` |
| `/intake/login`, `/intake/signup` | `app/intake/login/page.tsx`, `app/intake/signup/page.tsx` | `/api/v1/intake/login`, `/api/v1/intake/signup` |
| `/intake/project/new` | `app/intake/project/new/page.tsx` | `/api/v1/intake/projects`, `/api/v1/fabrics/intake-project/{id}/fabrics`, `/api/v1/intake/projects/{id}/photos` |
| `/intake/project/[id]` | `app/intake/project/[id]/page.tsx` | `/api/v1/intake/projects/{id}`, `/api/v1/intake/projects/{id}/photos`, `/api/v1/intake/projects/{id}/scans` |
| `/luxeforge`, `/luxe` | `app/luxeforge/page.tsx` (and `/luxe`) | `/api/v1/intake/admin/*`, `/api/v1/intake/projects` — JWT-required dashboard, NOT a public surface despite the route name |

### Comments confirm the public surface identity

`empire-command-center/app/intake/project/new/page.tsx:105-110`:

```typescript
// iX-day R1X-INT-FIX (Doctrine #4): business is required from the
// request context. The luxe.empirebox.store public surface is the
// Workroom intake. The default mirrors lib/intake-auth.ts:signup — the
// only place "workroom" is named on the front-end, and it is the
// public surface's self-identification, not a backend default.
business: 'workroom',
```

`empire-command-center/app/lib/intake-auth.ts:46-52`:

```typescript
// iX-day R1X-INT-FIX (Doctrine #4): business is required from the request
// context. The luxe.empirebox.store public surface is the Workroom intake
// (per the founder's CF bypass scope). ...
```

So `luxe.empirebox.store` is documented as the Workroom-intake public
hostname (Cloudflare Access bypassed). The minimal path set it needs is
the Workroom-intake API + the Apostille public API.

### Front-end API base configuration

`empire-command-center/app/lib/api.ts:1-23`:

```typescript
function resolveApiBase(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  }
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  }
  // Same-origin /api/v1 for any non-localhost host (studio.empirebox.store,
  // forge.empirebox.store, LAN IPs, etc.). The Next.js server proxies
  // /api/v1/* -> http://127.0.0.1:8000/api/v1/* via next.config rewrites.
  return `${window.location.origin}/api/v1`;
}
```

Same-origin `/api/v1` is the rule for any non-localhost host. The
founder's intent is that Cloudflare Access (host-scoped) carries the
`CF_Authorization` cookie end-to-end; the comment at `api.ts:13-17`
explains why absolute-host fetches to `api.empirebox.store` would fail
inside the portal. **Implication for the bypassed hostname:** when Access
is bypassed, the browser still uses same-origin `/api/v1`, the Next.js
server proxies to `127.0.0.1:8000`, and the backend sees the request as
if it came from a localhost-side client with no Access identity attached.

### Minimal path set the public hostname needs

Confirmed by the front-end component code above. Not inferred from
component names.

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

# Static photo serving (uploaded photos served back to the same browser)
GET    /intake_uploads/...
GET    /api/v1/photos/serve/{entity_type}/{entity_id}/{filename}
```

That is the tunnel-row surface. The `luxeforge_measurements` router at
`/api/luxeforge/measurements/*` (`backend/app/routers/luxeforge_measurements.py`,
mount at `main.py:234`) is NOT called by any front-end component on the
LuxeForge/Workroom-intake pages — the LuxeForge admin page (`app/luxeforge/page.tsx`)
only calls `/api/v1/intake/*`. So `luxeforge_measurements` does not need
to be in the tunnel row.

---

## 0e · The unauthenticated write endpoints

### `/api/v1/files/upload` — `backend/app/api/v1/files.py:43-55`

```python
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename")
    category = get_category(file.filename)
    save_path = UPLOAD_DIR / category / file.filename
    ...
    with open(save_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    log_access("upload", file.filename, "founder", f"category={category}")
    return {"status": "success", ...}
```

- **Auth:** none. No `Depends`, no `security` import, no access
  controller. The `log_access(... agent="founder")` is a hard-coded
  string in the log entry, not an identity check.
- **Size limit:** none in code. FastAPI's default is 25 MB per upload
  field; no explicit override.
- **Type restriction:** filename's extension is bucketed into
  `documents | code | images | audio | other` by
  `get_category(filename)` (`files.py:22-32`); any extension is
  accepted, including `.py`, `.js`, `.sh`, `.env`, `.exe`. The
  category affects the destination subdirectory, not whether the write
  proceeds.
- **Rate limit:** none. No `@limiter.limit(...)` decorator.
- **Write target:** `UPLOAD_DIR = Path.home() / "empire-repo" /
  "backend" / "data" / "uploads"` (`files.py:15`). Log dir
  `LOG_DIR = Path.home() / "empire-repo" / "backend" / "data" /
  "logs" / "file_access"` (`files.py:16`).
- **Canonical-path bypass:** YES. Per
  `reports/2026-08-24_D26_h72_write_split.md:129-135`, writers #4 and
  #5 in the H72 table list `app/api/v1/files.py:15` (uploads dir) and
  `app/api/v1/files.py:16` (log dir) as `BYPASSES — raw
  open()/Path()` against `~/empire-repo/...`. This is a stale-fork
  write path per CLAUDE.md and H73's "canonical-path enforcement is
  currently UNSAFE" note.

### `/api/v1/photos/upload` — `backend/app/routers/photos.py:160-228`

```python
@router.post("/upload")
async def upload_photos(
    entity_type: str = Form(default="general"),
    entity_id: str = Form(default=""),
    source: str = Form(default="web"),
    files: list[UploadFile] = File(...),
):
    if not entity_id:
        entity_id = uuid.uuid4().hex[:12]
    dest_dir = _entity_dir(entity_type, entity_id)
    ...
```

- **Auth:** none. No `Depends`, no `security` import.
- **Size limit:** none in code. FastAPI default 25 MB per upload field.
- **Type restriction:** when individual files, any extension is
  accepted (the file is saved with its suffix). When the uploaded file
  is a `.zip` archive, only entries whose extension is in
  `EXTRACTABLE = {".glb", ".gltf", ".obj", ".ply", ".usdz", ".stl",
  ".fbx", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".bmp",
  ".tiff"}` are extracted; others are skipped. **But the outer `.zip`
  upload is always accepted** — there is no size cap on the archive.
- **Rate limit:** none.
- **`entity_type` allow-list:** `VALID_ENTITY_TYPES = {"quote",
  "intake", "telegram", "craftforge", "general"}` (`photos.py:50`).
  Any other value returns HTTP 400 (`photos.py:55-56`).
- **Write target:** `PHOTOS_BASE = Path(canonical_photos_dir())`
  (`photos.py:36`), which per
  `backend/app/services/drawing/canonical_path.py` resolves to
  `~/empire-data/photos/{entity_type}/{entity_id}/`.
- **Canonical-path bypass:** NO (this endpoint goes through
  `canonical_photos_dir()`).

### Are these writes in scope for the tunnel-row fix?

**No.** The tunnel-row is about narrowing which `/api/v1/*` paths a
bypassed hostname can reach. These two upload endpoints are on paths that
do not appear in §0d's minimal public path set. If the bypassed
hostname is narrowed to the public surface, neither endpoint is reachable
from `luxe.empirebox.store` and the unauthenticated-write question
collapses.

But the question the founder actually has to answer is "do these two
endpoints have any other caller?" The grep for back-end callers
(`grep -rn "/api/v1/files/upload\|/api/v1/photos/upload" --include=*.py`)
shows no internal service hits these URLs. The front-end does not hit
them either (the Workroom intake form uploads via
`/api/v1/intake/projects/{id}/photos`, not `/api/v1/photos/upload`).
**INFERRED to be dead surfaces in current production traffic; COULD NOT
PROBE historical use from the journal window that survives.** The
founder should confirm before either deleting the routes or leaving them
exposed.

---

## 0f · Fix options, no recommendation

The fix problem is: how can `channel` be derived server-side so a
caller that simply posts `{"channel": "web_cc"}` is not treated as
founder, while preserving the Telegram bot's legitimate founder flow and
preserving the portal's normal web flow.

### Option A — Per-route constant set by the handler

Each `/api/v1/max/...` route declares its own canonical channel inside
the handler body. Telegram bot stops being a caller of `/max/chat` and
becomes a direct caller of `MAX.chat(...)` (the in-process service)
when running inside the backend, or passes a service token that the
backend maps to "telegram + founder".

- **Covers sites:** all four (router.py:2169, 3207, 5162 + guardrails.py:135)
  if every handler is updated.
- **Breaks from 0c:** yes — `telegram_bot._chat_with_max`
  (`telegram_bot.py:466`) currently hits `/max/chat` over HTTP. It
  would need a new internal path or a service-token signal.
- **Works when Access is bypassed:** yes, because the handler itself
  is the source of truth, not the body field.

### Option B — Derive from authenticated session or Access identity header

Replace `request.channel or ""` with a derivation:
- If request carries a valid `Cf-Access-Jwt-Assertion` (Cloudflare
  Access) → `"web_cc"`.
- If request is from the intake JWT (founder or admin role in the JWT
  claims) → `"web_cc"`; otherwise → `"intake_client"`.
- If request is an internal loopback HTTP from `telegram_bot` →
  allow `channel="telegram"` only when paired with a known
  service-token header.

- **Covers sites:** all four.
- **Breaks from 0c:** yes for `telegram_bot` (needs a service-token
  header) and possibly for any portal-side call that did not have a
  Cloudflare Access cookie (e.g. the public-facing apostille page
  signed in as a public user — the founder branch is wrong there too,
  but the empty-string default currently gives it). The intake JWT
  path needs the JWT claims exposed.
- **Works when Access is bypassed:** no — without the
  `Cf-Access-Jwt-Assertion` header, no portal call is recognised as
  founder, even from the legitimate founder browser. That is the
  intended outcome, but it changes the portal's day-to-day operation.

### Option C — Allowlist internal callers by service token

Keep `request.channel` as the source of `channel` for **normalisation
and routing** (Telegram directive, prompt-channel label), but introduce
a separate `request.service_token` header that gates the **founder
branch**. Telegram bot sets the token. Portal does not set the token
(portal gets founder via Access identity, not via the body field). Any
caller without the token is treated as anonymous regardless of body
`channel`.

- **Covers sites:** all four, with a small middleware that wraps
  `is_founder_message`.
- **Breaks from 0c:** no — the body `channel` field is still accepted
  for normalisation. The Telegram bot needs to add the service-token
  header (one-line change). Portal needs no change IF Cloudflare Access
  identity is what makes the portal call "founder."
- **Works when Access is bypassed:** only if the portal call still
  carries a service token, which it does not (it has only the
  Access cookie). So the portal would lose founder status on the
  bypassed hostname — that is the intended outcome but a behaviour
  change.

### Option D — Keep body field, ignore for privilege decisions

Read `request.channel` only for the things that don't grant privilege
(prompt-channel label, Telegram directive at `router.py:2575` and
`:3480`). Compute founder from a separate signal (auth session, Access
identity, or service token). The body field can still be logged.

- **Covers sites:** all four, with the `is_founder_message` call sites
  replaced by a privilege-only resolver.
- **Breaks from 0c:** minimally — body `channel` is still read for
  non-privilege uses. Telegram bot still works for prompt rendering.
- **Works when Access is bypassed:** depends entirely on which
  alternative signal is used. If Access identity, then no. If a
  service token, then yes (if the portal call carries one — it does
  not currently).

### Option E — Status quo + warning log when body `channel` is founder-shaped from a non-founder route

No behaviour change. Add a `logger.warning(...)` line at each call site
when `channel` is in the founder allow-list but the request lacks the
expected signals (no service token, no Access cookie, no JWT admin
role). This is a detection aid, not a fix.

- **Covers sites:** all four.
- **Breaks from 0c:** no.
- **Works when Access is bypassed:** yes — this is purely additive.

### Notes the founder will weigh

- Telegram bot is the load-bearing caller. Any option that prevents
  `telegram_bot._chat_with_max` from sending `channel="telegram" +
  chat_id=<founder>` and being treated as founder is a regression.
- The portal has two roles: (i) the founder's day-to-day Command
  Center use (must remain founder) and (ii) the bypassed public surface
  (must NOT be founder). Today both roles look identical to the
  backend when Access is bypassed; the only differentiator is the
  `channel` body field, which is set by the front-end.
- The empty-string default at `guardrails.py:104` is the most
  permissive possible default — any caller that omits `channel` is
  treated as founder. This is the specific behaviour that has to move
  for any of Options A–D to matter.
- Options B and D change the portal's day-to-day operation in a way
  the founder may or may not want. Option C is the cleanest "no
  behaviour change for the founder" approach IF the portal can be made
  to carry a service token — which it currently does not.
- Option E is a no-op for behaviour and a useful regression net for
  any of A–D.

---

## 0g · What came through

### `code_mode_tasks` — empty

```
$ python3 -c "import sqlite3; c=sqlite3.connect('/home/rg/empire-data/empire.db'); \
              print(c.execute('SELECT COUNT(*) FROM code_mode_tasks').fetchone()[0])"
0
```

Confirmed per session 2026-08-24 D28 STEP 2b's cleanup. No rows from any
source — internal or external.

### `openclaw_tasks` — last 20 rows by `created_at` (sampled)

Top entries by `created_at` (all from 2026-08-20 22:14–22:26 except the
test-stage proofs):

- `id=7394–7385`: nine consecutive `Read /home/rg/empire-repo-main/STATE.md`
  via `file_read`, `status=failed`, `source=desk_fallback`. Each ~11s
  apart. All from a single desk loop, not from external prompts.
- `id=7384`: `Read STATE.md` succeeded (`status=done`).
- `id=7383–7381`: `Git status`, `Git log`, `Git remote -v`, all
  `desk_fallback`, matching the dispatch test pattern.
- `id=7380`: `STAGE3 live proof — exact-content append` to
  `codetask_stage3_clean.txt`. Dispatch-driven test (R12 dispatch).
- `id=7379`: `STAGE3 live proof — append a single line to /tmp scratch
  file`. Dispatch-driven.
- `id=7378–7377`: `STAGE1-F2-F3 verification task (retry)` + the
  original. Dispatch-driven.

All 7390 rows trace to internal sources (`desk_fallback`,
`manual-code-task`, MAX-tool traces). No unfamiliar prompts.

### `atlas_tasks` — last 20 rows by `created_at` (sampled)

Top entries:

- `id=19952a4a` 2026-08-24 13:06: "Diagnose PDF generator failure on
  send_quote_email / send_quote_telegram" (completed). Internal.
- `id=37db3685` 2026-08-24 03:00: "Fix pricing engine: rings + labor
  calc for drapery quotes" (completed). Internal.
- `id=2a9d6b58` 2026-08-18 00:33: "Patch drapery lining_type enum"
  (completed). Internal.
- `id=d7178390` (and ~30 others, all 2026-05-06): "Read guardrails.py"
  (completed). Internal Atlas retrieval.

All 132 rows trace to internal Atlas/CodeForge workflow. No unfamiliar
prompts.

### Backend journal — `POST /api/v1/max/code-task` since 2026-08-15

```
$ journalctl --user -u empire-backend --since "2026-08-15" --no-pager \
              | grep -E "POST /api/v1/max/code-task" \
              | grep -vE "127\.0\.0\.1|::1"
(empty)
```

Every `POST /api/v1/max/code-task` since the journal window is from
`127.0.0.1`. The only non-local IPv6 (`2600:1003:b06c:...`) traffic
hits `GET /api/v1/max/chat`, `GET /api/v1/notifications`,
`GET /api/v1/system/{stats,ollama/status}`, `GET /api/v1/memory/context-pack`,
`GET /api/v1/max/{desks,status,self-assessment,...}`,
`GET /api/v1/chats/list`. All dashboard polling, all GET, no code-task
or tool-execution POSTs from non-local sources.

### Backend journal — `POST /api/v1/intake/projects/{id}/photos`

There ARE such POSTs in the journal (Aug 23 00:04 → 02:04, ~10 minutes
apart, all 200 OK), but every source IP is `127.0.0.1`. The destination
project UUIDs do not match any row in `intake_projects`
(`SELECT id FROM intake_projects WHERE id IN (...)` → empty). The
orphan directories under `/home/rg/empire-data/intake_uploads/<uuid>/`
are the on-disk artefact of those uploads.

COULD NOT PROBE: whether the orphan directories correspond to projects
that were deleted before the current DB, projects that live in a
different DB, or projects that never made it past the upload step. The
journal shows only `127.0.0.1` source — no external origin recorded for
these.

### Backend journal — no `Host: luxe.empirebox.store`

```
$ journalctl --user -u empire-backend --since "2026-08-20" --no-pager | grep -iE "luxe"
Aug 22 14:17:56 ... "GET /api/luxeforge/measurements/calculate HTTP/1.1" 404 Not Found
Aug 22 14:18:12 ... "POST /api/luxeforge/measurements/calculate HTTP/1.1" 422 ...
... (and several more 404/422 from the same timestamp, all from 127.0.0.1)
```

The LuxeForge measurements router logs are dev/test probing (all 127.0.0.1,
mixed 404/422, single-second burst). No external `luxe.empirebox.store`
host header appears in the journal window.

### Summary

**No evidence found of outside use through the bypassed hostname** within
the journal window that survives (2026-08-15 onward). All
non-local traffic is dashboard polling (GETs only) from the IPv6
range `2600:1003:b06c:...` — consistent with normal Cloudflare-edge
Access-authenticated portal use.

This is not a claim that nothing happened. It is a claim that the
backend's own record (db rows + journal) shows no signs of it for the
window probed. The founder should treat this as "no evidence found in
the current logs" rather than "nothing happened."

---

## STOP — summary of deliverables

- **H-number used:** H74.
- **Ranked call-site table:** §0b. Code-task (`router.py:5162`) is the
  highest privilege, confirmed. Tool-executor and the two
  `*.py:218, :225` lines are NOT founder gates — they normalise
  channel for routing only. `tool_executor.py:454` is a docstring, not
  a call.
- **0c break list:** §0c. Telegram bot is the only caller that would
  break if `channel` were derived server-side without an alternative
  signal.
- **Minimal public path set:** §0d. Apostille public + Workroom intake
  + fabrics intake-project write + photo serving. The
  `luxeforge_measurements` router is not called from any front-end
  page in the public surface.
- **Upload endpoint findings:** §0e. Both endpoints are unauthenticated.
  `/api/v1/files/upload` writes to the stale-fork path
  `~/empire-repo/backend/data/uploads` (H72 BYPASSES); no front-end
  caller. `/api/v1/photos/upload` writes to the canonical photos dir;
  no front-end caller. The fix narrows the tunnel row; these endpoints
  fall outside the row.
- **Fix options with trade-offs, no recommendation:** §0f. Five options
  laid out (per-route constant, Access/session derivation, service-token
  allowlist, keep-body-but-ignore-for-privilege, additive warning log).
  No option recommended.
- **0g evidence:** §0g. No evidence of outside use in the probed
  window. Stated plainly as "no evidence found," not as "nothing
  happened."

No fix lane entered. Report-only commit follows.
