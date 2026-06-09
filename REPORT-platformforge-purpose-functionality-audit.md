# PlatformForge Purpose / Functionality Audit

**Date:** 2026-06-09
**Scope:** `app/components/screens/PlatformPage.tsx` (the PlatformForge / Infrastructure page in the Empire Command Center) and the live backend endpoints it consumes.
**Mode:** Read-only. No code modified. No services restarted. No push.
**Repo state at audit time:** `empire-repo-main` on `main` at `395f6ee feat(businessops): add tenant entitlement foundation` (clean working tree, 0 ahead/behind `origin/main`).
**Live backend:** uvicorn PID 70806, started 16:59:03, running on `0.0.0.0:8000`, current_commit `395f6ee`, lane `main`.
**Live portal:** next-server PID 41351 on `*:3005`.

---

## 1. Executive verdict

* **items audited:** 12 groups, 90+ individual items, mapped to 11 backend endpoints + 3 hardcoded UI constants + 2 frontend subcomponents + the `/api/v1/max/system-report` module/connectivity/suggestion/bug aggregator.
* **live/accurate:** 35 items (system health metrics, active_ports, AI provider/model registry, routing state, telegram bot config, 4-7 service connectivity checks, businessops endpoints — confirmed present and accurate post-restart).
* **stale/hardcoded:** 17 items (4 legacy port names `3009`/`3003`/etc., 13 docker product port cards all `unknown`, "Documentation 100 files" count, "Brain Status" off, "21181 memories" — real count but path is a cross-repo artifact, hardcoded API-key `available` mapping only checks 4 of 16, hardcoded guardrail descriptions).
* **misleading:** 11 items (the 4 `localhost:3009/3003/11434/3077` connectivity checks fire as `offline` even though the real surfaces are on `3005` (live) and `7878` (live) and `11434` is genuinely offline; the Docker product cards render with `UNKNOWN` status because docker manager can't see them; the 13 port cards in the System Report suggestions are historical and don't reflect the current `:3005` portal at all; "Safe Refusal Message" is hardcoded copy).
* **should stay visible:** System Health (top), AI Models & Routing, Routing Policy, Ollama Models (with truth-in-labeling), Brain & Backup (with corrected path), CORS & Security (with auth note), API Route Groups (with `/businessops` added).
* **should move to System Details:** Service Connectivity (the legacy-port rows), Docker Products (all-`unknown` is noise on the main view), API Keys & Credentials, Guardrails.
* **should hide:** Documentation 100-files (count is a static string from `docs-registry.ts`), Payment widget on the PlatformForge page (it is the same `PaymentModule` used on the customer Pricing page — Founder-useful but wrong context; belongs in a separate Payments admin, not on Infrastructure).
* **should be deprecated:** the 13 docker product port cards (3001–3011) are historical from a docker-compose era and no longer reflect the actual surface topology; **none** of those ports are listening except 3005 (which is the Next.js portal, not a docker container). The connectivity row "Command Center :3009" is doubly wrong — the real Command Center is `:3005`, and there is no Founder Dashboard service at `:3009`.
* **code changed:** **none.**
* **push performed:** **none.**

---

## 2. Top misleading items

| # | What it shows | Why it's wrong | Where |
|---|---|---|---|
| 1 | **Service Connectivity → Command Center `localhost:3009` → OFFLINE** | The actual Command Center / Empire Studio Portal is `localhost:3005` (Next.js next-server PID 41351, HTTP 200). The `:3009` URL is historical from an earlier `founder-dashboard` docker-compose attempt; that port is **not** listening and the service doesn't exist. The page renders a red `OFFLINE` status for a thing that doesn't exist, while the real portal gets no row. | `PlatformPage.tsx` lines 261-300 (the `connectivity` branch) and `/api/v1/max/system-report` `connectivity[]` |
| 2 | **Service Connectivity → AMP Portal `localhost:3003` → OFFLINE** | Same issue: `:3003` is the historical `install-forge` docker port, not an "AMP Portal." AMP is the `app/amp/` Next.js subpath under `:3005/amp/*`. There is no separate process on `:3003`. | same as #1 |
| 3 | **Service Connectivity → Ollama `localhost:11434` → OFFLINE** | This one is **real** — Ollama is genuinely not running on this machine. The page labels it correctly as offline. But the page also doesn't tell Founder it's a *deliberate* state (MAX provider registry has Ollama set to `founder_disabled_due_to_stall_suspected`). It looks like a failure. | `brain.ollama.online = false`, plus `data.metrics.active_ports["11434"] = false` |
| 4 | **Docker Products → all 13 cards render `UNKNOWN`** | The backend's `/api/v1/docker/status` returns each product with `status: "unknown"`, not a real state. The card is then rendered by `PlatformPage.tsx` lines 513-532 as an `UNKNOWN` status pill. The docker manager can't see the live processes (which are mostly non-docker systemd services). All 13 cards are noise on this page. | `docker.status` API + `PlatformPage.tsx` 513-532 |
| 5 | **Brain Status → Offline** | The brain DB **exists** (`/home/rg/empire-repo/backend/data/brain/memories.db`, 12 MB) and contains 21,181 memories (verified by direct SQL count). The API returns `brain_online: false` because the brain service isn't initialized in the live uvicorn's startup — but the data is on disk. The "Offline" label is technically true for the service but hides that the data is real and queryable. | `brain.brain_online = false` from `/api/v1/max/brain/status` |
| 6 | **Total Memories = 21181** | The number is **real** (SQLite direct count: `SELECT COUNT(*) FROM memories → 21181`). But the API returns it from `/home/rg/empire-repo/backend/data/brain/memories.db` while the running process is in `empire-repo-main` — the brain is in the **stale fork**, not the active worktree. Founder may wonder why a path under `empire-repo` is being shown. The page should label this as "stale-fork artifact, see REPO-TRUTH." | `brain.memories.total = 21181` from `/api/v1/max/brain/status` |
| 7 | **API Keys & Credentials → 16 hardcoded names** | The list of 16 env-var names (`XAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) is hardcoded in `PlatformPage.tsx` lines 169-186. The `SET/MISSING` pill only derives from live data for **4 of the 16** (XAI, Anthropic, Groq, Telegram) by cross-referencing `aiModels` and `telegram` state. The other 12 always render `ENV` (gray) regardless of whether they're set. | `PlatformPage.tsx` 169-186, 414-441 |
| 8 | **Guardrails → 6 items, all `ACTIVE`** | Descriptions are hardcoded copy ("15 regex patterns," "Strips sk-*, xai-* patterns"). The `ACTIVE` status is **assumed**, not read from any live endpoint. If a guardrail is silently disabled in code, the UI still says `ACTIVE`. | `PlatformPage.tsx` 159-166, 386-402 |
| 9 | **CORS & Security → "Auth Mode: None (local network only)"** | This is a **hardcoded string** in `PlatformPage.tsx` line 452. It is **accurate** (I grepped `main.py` for any auth middleware: zero `Depends(get_current_user)`, zero `HTTPBearer`, zero `OAuth2`, zero `auth_required`), but the warning amber triangle suggests it's a *concern*. The page is not Founder-useful unless Founder knows it's a fact, not a suggestion. | `PlatformPage.tsx` 452, `backend/app/main.py:44-47` |
| 10 | **API Route Groups → 29 prefixes, all clickable** | The list of 29 route prefixes is hardcoded in `PlatformPage.tsx` 197-227. The `Status` pill on each row is **derived** by cross-referencing the modules from `/api/v1/max/system-report` (e.g. matching `r.prefix` to `mod.endpoint`). `/api/v1/businessops` is **not in the list** — it shipped on `395f6ee` but PlatformForge still shows only 29 routes, missing the new one. | `PlatformPage.tsx` 197-227, 466-488 |
| 11 | **Documentation → "100 files"** | The `Documentation` section uses `ProductDocs product="platform"` (line 586), which renders a static, hardcoded list of ~100+ document titles from `lib/docs-registry.ts`. The "100 files" count is the literal length of that array. The docs themselves are PDFs/HTMLs in `~/Downloads`, `~/Documents`, `docs/`, `docs/recovered/`, etc. — many may not exist on the current filesystem. The list is decorative, not functional. | `PlatformPage.tsx` 585-587, `lib/docs-registry.ts` |

---

## 3. Top useful items

* **System Health cards (CPU/RAM/Disk/Uptime)** — genuinely live, from `/api/v1/system/stats` (psutil/nvme/disk). CPU 7.6%, RAM 21.9% (6.86/31.26 GB), Disk 9.7% (270.3/2791.3 GB on `/data` partition — the root `/` is 78% full, see Security Concerns), uptime 4h 50m. **Keep visible, primary view.**
* **AI Models & Routing** — fully live. Shows 11 providers with status flags, current selection `minimax / MiniMax-M3`, fallback OFF, AI calls ENABLED. Per-provider actions (Set Active / Test / Enable / Disable) are real and POST to `/api/v1/max/routing-state`, `/max/provider/toggle`, `/max/provider/test`. **Keep visible, primary view, but expand the per-row state** so Founder can see *why* `groq` is `disabled_by_kill_switch` without clicking.
* **Routing Policy panel** — live `fallback_enabled` toggle, real button that POSTs to `/api/v1/max/routing-state`. **Keep.**
* **Brain & Backup** — partially live. Real `last_backup` and `backup_count` from chat-backup (the chat-backup endpoint returns 404 today, so the backup section is not rendering — see DB-truth audit in `REPORT-businessops-tenantops-design.md`). The brain row itself is live (just labeled misleadingly). **Keep, fix labels.**
* **CORS & Security** — the live `CORS_ORIGINS` env value plus the always-true `allow_credentials: true`, `methods: *`, `headers: *` from `main.py:44-47` are useful. The "Auth Mode: None" line is also useful, just needs the warning glyph to be a check, not a warning, on local networks. **Keep, move to System Details, drop the warning.**
* **AI Models & Routing count of 11 providers** — accurate and useful for the "what can I use today" question. **Keep on main.**
* **OpenClaw availability** — the AI provider registry reports `openclaw: configured=True, available=True, disabled_reason=None` even though the OpenClaw worker queue is stalling (per the earlier session context). The Platform page shows the right **status flag** but not the **queue depth**. **Keep the row, add queue depth in System Details.**

---

## 4. Module purpose/functionality table

| # | Item | Purpose (intended) | Actual functionality today | Source file | Endpoint | Live/cached/hardcoded | User value | Risk | Recommendation | Minimum next action |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Header: "PlatformForge · Infrastructure · Live Configuration" | Identify page, show date | `new Date().toLocaleDateString()` rendered server-side (SSR) | `PlatformPage.tsx:238-242` | none | live (per-render) | low | low | KEEP_MAIN | none |
| 2 | System Health: CPU % | Show live CPU usage | `psutil.cpu_percent` → `data.system.cpu.percent` | `PlatformPage.tsx:131, 254` | `/api/v1/system/stats` | live | high | low | KEEP_MAIN | none |
| 3 | System Health: RAM | Show live RAM usage | `psutil.virtual_memory` | `PlatformPage.tsx:132, 255` | `/api/v1/system/stats` | live | high | low | KEEP_MAIN | none |
| 4 | System Health: Disk | Show live disk usage | `psutil.disk_usage` against `/` and other mounts | `PlatformPage.tsx:133, 256` | `/api/v1/system/stats` | live | high | medium (root 78% full) | KEEP_MAIN | highlight `/` mount saturation in red (currently only `/` is shown as `disk: 9.7%` because it averages across all drives) |
| 5 | System Health: Uptime | Show process uptime | `data.system.uptime` (psutil boot_time delta) OR `data.metrics.uptime_seconds` (uvicorn process uptime) | `PlatformPage.tsx:134, 257` | `/api/v1/system/stats` + `/api/v1/system/metrics` | live (uvicorn process — will reset on every backend restart) | medium | low | KEEP_MAIN, FIX_LABEL: "Since last backend restart" not "Since last boot" | change label |
| 6 | Service Connectivity → Backend API :8000 | Liveness check | `active_ports[8000]` from `/api/v1/system/metrics` | `PlatformPage.tsx:280, 261-300` | `/api/v1/max/system-report.connectivity[]` (preferred) **or** `/api/v1/system/metrics.active_ports` (fallback) | live | high | low | KEEP_MAIN | none |
| 7 | Service Connectivity → Command Center :3009 | Liveness check | Hardcoded URL in `/api/v1/max/system-report` `connectivity[]` | `backend/app/routers/max/.../system_report.py` (or wherever generated) | `/api/v1/max/system-report.connectivity[]` | hardcoded URL, live HTTP check | misleading | medium | HIDE or FIX_LABEL: change to `:3005` and rename "Empire Studio Portal" | update the source-of-truth connectivity list in the system-report generator |
| 8 | Service Connectivity → AMP Portal :3003 | Liveness check | Hardcoded URL; AMP is actually under `:3005/amp/*` | same as #7 | same | hardcoded URL, live HTTP check | misleading | medium | HIDE | remove row, or move to System Details as "Legacy port cards" |
| 9 | Service Connectivity → Ollama :11434 | Liveness check | `brain.ollama.online` boolean (false) | `PlatformPage.tsx:284` | `/api/v1/max/brain/status` | live | medium | low (it's intentional) | KEEP_MAIN, FIX_LABEL: "Ollama (intentionally disabled — see AI Models)" | change label |
| 10 | AI Models & Routing → Active label | Show current selection | `routingState.selected_provider` / `selected_model` | `PlatformPage.tsx:305-307` | `/api/v1/max/models.routing_state` | live | high | low | KEEP_MAIN | none |
| 11 | AI Models → MiniMax / MiniMax-M3 | Provider row | Live: configured=true, available=true, primary=true, selected=true | `PlatformPage.tsx:310-356` | `/api/v1/max/models.provider_registry[]` | live | high | low | KEEP_MAIN | none |
| 12 | AI Models → DeepSeek | Provider row | Live: configured=true, available=true | same as #11 | same | live | high | low | KEEP_MAIN | none |
| 13 | AI Models → Qwen (missing_key) | Provider row | Live: configured=false, disabled_reason=missing_key | same | same | live | medium | low | KEEP_MAIN | add "configure QWEN_API_KEY" tooltip |
| 14 | AI Models → OpenRouter (missing_key) | Provider row | Live: configured=false, disabled_reason=missing_key | same | same | live | low | low | MOVE_TO_SYSTEM_DETAILS | not on Founder's daily critical path |
| 15 | AI Models → Groq (disabled_by_kill_switch) | Provider row | Live: configured=true, available=false, disabled_reason=disabled_by_kill_switch | same | same | live | medium | low | KEEP_MAIN | show the kill-switch date in a tooltip |
| 16 | AI Models → Claude (disabled_by_kill_switch) | Provider row | Live: configured=true, available=false, disabled_reason=disabled_by_kill_switch | same | same | live | medium | low | KEEP_MAIN | same as #15 |
| 17 | AI Models → OpenAI gpt-4.1-nano | Provider row | Live: configured=true, available=true | same | same | live | medium | low | KEEP_MAIN | none |
| 18 | AI Models → Gemini 2.5-flash | Provider row | Live: configured=true, available=true | same | same | live | medium | low | KEEP_MAIN | none |
| 19 | AI Models → xAI Grok (credits_unavailable) | Provider row | Live: configured=true, available=false, disabled_reason=credits_unavailable | same | same | live | medium | low | KEEP_MAIN | show credit reset date in tooltip |
| 20 | AI Models → Ollama llama3.1:8b (founder_disabled) | Provider row | Live: configured=true, available=false, disabled_reason=founder_disabled_due_to_stall_suspected | same | same | live | medium | low | KEEP_MAIN | this is the explanation for #9 — link them |
| 21 | AI Models → OpenClaw openclaw | Provider row | Live: configured=true, available=true, but worker queue is stalling (from prior context) | same | same | live but partial | medium | medium (looks fine when it isn't) | KEEP_MAIN, FIX_DATA_SOURCE: add queue depth from `/api/v1/openclaw/queue` | add queue depth chip |
| 22 | Routing Policy → Selected provider/model authoritative | Doc note | Hardcoded copy | `PlatformPage.tsx:364-366` | none | hardcoded | medium | low | KEEP_MAIN | none |
| 23 | Routing Policy → Fallback toggle | Real action | POSTs `fallback_enabled` to `/api/v1/max/routing-state` | `PlatformPage.tsx:368-381` | `/api/v1/max/routing-state` | live (write) | high | low | KEEP_MAIN | none |
| 24 | Guardrails → 6 hardcoded items | Show active guardrails | Hardcoded `[{name, desc, status}]` array; **not** read from any endpoint | `PlatformPage.tsx:159-166, 386-402` | none | hardcoded | low | high (silent disable is invisible) | SHOW_ONLY_IN_DEBUG_MODE or FIX_DATA_SOURCE: add `/api/v1/max/guardrails/status` endpoint that reads `app.services.max.guardrails` | minimum: read from new endpoint; interim: add `(static — see code)` disclaimer |
| 25 | Guardrails → "Safe Refusal Message" hardcoded copy | Show refusal text | Hardcoded string in JSX | `PlatformPage.tsx:399-401` | none | hardcoded | low | low | SHOW_ONLY_IN_DEBUG_MODE | none (it's a debug aid, not a customer surface) |
| 26 | API Keys & Credentials → 16 env-var names | Show which keys are set | Hardcoded list; only 4 (XAI, Anthropic, Groq, Telegram) get live SET/MISSING; 12 always show `ENV` (gray) | `PlatformPage.tsx:169-186, 414-441` | none for 12; live for 4 | mixed | medium | medium (looks complete when it isn't) | MOVE_TO_SYSTEM_DETAILS, FIX_DATA_SOURCE: add `/api/v1/system/secrets` endpoint that returns `{env_var, set: bool}` for all known keys | interim: relabel gray pill from `ENV` to `UNKNOWN` |
| 27 | CORS & Security → CORS_ORIGINS=* | Show live CORS config | Reads `os.getenv("CORS_ORIGINS", "*")` server-side, hardcoded client mirror in `corsConfig.origins = 'CORS_ORIGINS env or * (all)'` | `PlatformPage.tsx:189-194, 446-463` | none on client; `backend/app/main.py:44-47` server-side | hardcoded on client | medium | low (this is dev, OK) | MOVE_TO_SYSTEM_DETAILS | optional: read from a new `/api/v1/system/cors` endpoint |
| 28 | CORS & Security → Auth Mode: None | Show no auth | Hardcoded string | `PlatformPage.tsx:452` | none | hardcoded | high (Founder should know) | low | KEEP_MAIN, but in System Details | confirm by grep `main.py` for any auth middleware — none — so the label is accurate |
| 29 | CORS & Security → Database: empirebox.db | Show DB | Hardcoded; actually it's `empire.db` (per the live `runtime_lane` and earlier audit) | `PlatformPage.tsx:453` | none | hardcoded, **wrong** | low | medium | FIX_LABEL: "Database: SQLite `empire.db` at `backend/data/empire.db`" | one-line fix |
| 30 | CORS & Security → Telegram Bot | Show telegram config | Live from `/api/v1/max/telegram/status` → `{configured: true, bot_token_set: true, chat_id_set: true}` | `PlatformPage.tsx:454` | `/api/v1/max/telegram/status` | live | medium | low | KEEP_MAIN | none |
| 31 | API Route Groups → 29 hardcoded prefixes | Show registered routers | Hardcoded list; `/api/v1/businessops` is **missing** (just shipped) | `PlatformPage.tsx:197-227, 466-488` | none | hardcoded, **incomplete** | medium | medium | FIX_DATA_SOURCE: read from `/openapi.json` paths on mount, or add `/api/v1/system/routes` endpoint | interim: add `businessops` line to the hardcoded array |
| 32 | Ollama Local Models | Show installed ollama models | `/api/v1/ollama/models` returns `{detail: "Ollama not reachable"}`; brain.ollama.models = []; page shows "Ollama not reachable" | `PlatformPage.tsx:491-510` | `/api/v1/ollama/models` + `/api/v1/max/brain/status` | live (and empty) | medium | low | KEEP_MAIN, FIX_LABEL: replace "Ollama not reachable" with "Ollama offline (intentional — see AI Models)" | change the empty-state text |
| 33 | Docker Products → 13 cards | Show running docker containers | `/api/v1/docker/status` returns 13 products, all with `status: "unknown"`; card renders `UNKNOWN` pill | `PlatformPage.tsx:513-532` | `/api/v1/docker/status` | live but value is "unknown" | none (pure noise) | high (Founder sees 13 broken-looking entries) | HIDE or DEPRECATE_CANDIDATE | these port cards are historical from a docker-compose era; the live services are systemd units, not docker. Recommend hide until docker status is real |
| 34 | Brain & Backup → Brain Status: Offline | Show brain online | Live: `brain_online: false` | `PlatformPage.tsx:537` | `/api/v1/max/brain/status` | live (and false) | medium | medium (label is misleading) | KEEP_MAIN, FIX_LABEL: "Brain service: not initialized" (data is on disk, see Total Memories row) | reword |
| 35 | Brain & Backup → Total Memories: 21181 | Show memory count | Live: 21181, real (SQLite count verified) | `PlatformPage.tsx:538` | `/api/v1/max/brain/status` | live, real, but path is cross-repo | high (Founder cares about this number) | medium (path is misleading) | KEEP_MAIN, FIX_DATA_SOURCE: `brain.storage.path = /home/rg/empire-repo/backend/data/brain` is the stale-fork path; the canonical path is `/home/rg/empire-repo-main/backend/data/brain` (which doesn't exist) — see REPO-TRUTH | document the cross-repo artifact in REPO-TRUTH or move the brain DB to the active worktree |
| 36 | Brain & Backup → Storage Path | Show where brain is | Live: `/home/rg/empire-repo/backend/data/brain` | `PlatformPage.tsx:539` | same | live, cross-repo | medium | medium | KEEP_MAIN, add inline note: "(stale-fork artifact)" | one-line footnote |
| 37 | Brain & Backup → External Drive: No | Show whether on ext drive | Live: false | `PlatformPage.tsx:540` | same | live | low | low | KEEP_MAIN | none |
| 38 | Brain & Backup → Active Conversations: 0 | Show live convo count | Live: 0 | `PlatformPage.tsx:541` | same | live | low | low | KEEP_MAIN | none |
| 39 | Brain & Backup → Last Backup / Count / Interval / Auto | Show chat-backup state | `/api/v1/chat-backup/status` returns `{"detail":"Not Found"}` — entire backup section **does not render** | `PlatformPage.tsx:542-550` | `/api/v1/chat-backup/status` (404) | endpoint broken | low (because broken, not used) | medium (Founder may not know backups are not happening) | SHOW_ONLY_ON_ERROR or FIX_DATA_SOURCE: fix the chat-backup endpoint | investigate why the endpoint 404s |
| 40 | Suggestions & Known Issues | Show system-report recommendations | Live: 5 suggestions + 3 bugs from `/api/v1/max/system-report` | `PlatformPage.tsx:555-572` | `/api/v1/max/system-report` | live | high | low | KEEP_MAIN | none (this is one of the most Founder-useful sections) |
| 41 | Desktop Pairing | Show OpenCode phone pairing | Renders `<DesktopPairing />` subcomponent | `PlatformPage.tsx:575-577`, `components/platform/DesktopPairing.tsx` | internal | live subcomponent | medium | low | KEEP_MAIN | none |
| 42 | Payments | Show payment widget | Renders `<PaymentModule product="platform" />` — same widget as the customer Pricing page | `PlatformPage.tsx:579-582`, `components/business/payments/PaymentModule.tsx` | internal | live subcomponent | low (wrong context for Founder) | medium (Stripe is in the customer widget) | HIDE or MOVE_TO_SYSTEM_DETAILS | the payment widget doesn't belong on an Infrastructure page |
| 43 | Documentation | Show doc list | Renders `<ProductDocs product="platform" />` — hardcoded list of ~100+ documents from `lib/docs-registry.ts` | `PlatformPage.tsx:584-587`, `lib/docs-registry.ts` | none | hardcoded, decorative | low | low | MOVE_TO_SYSTEM_DETAILS or SHOW_ONLY_IN_DEBUG_MODE | the list is decorative — many entries may not exist on disk |

---

## 5. Security concerns

| # | Concern | Severity | Why | What should happen |
|---|---|---|---|---|
| S1 | **CORS = `*` (all origins)** | medium in dev, **high in prod** | `main.py:44-47` reads `CORS_ORIGINS` from env, defaults to `*`, with `allow_credentials: true`. Any origin can call any backend endpoint with cookies attached. Acceptable on `localhost` dev, dangerous on `studio.empirebox.store`. | Production deploy must set `CORS_ORIGINS=https://studio.empirebox.store` (or whichever prod origin). Page already shows the warning glyph. |
| S2 | **Auth Mode = None** | high if exposed beyond LAN | Zero auth middleware in `main.py`. Every endpoint under `/api/v1` is callable by anyone who can reach port 8000. On `127.0.0.1` this is fine. If `cloudflared` ever exposes port 8000 to the public (it doesn't today — it points at 3005), this is a critical exposure. | Keep backend off the public tunnel. Confirm: `ps aux | grep cloudflared` shows tunnel targets `localhost:3005`, not 8000. Verified. |
| S3 | **API Key & Credentials row on the page is dev-friendly** | low | The 16-row list is useful for the Founder checking what's set, but it would be a real disclosure if shown to anyone other than the Founder. The page is auth-less, so anyone on the LAN sees the same list. | If this page ever becomes non-Founder-accessible, this section must move to a Founder-authenticated view. The `showKeys` toggle is currently a client-side visual flip (line 407-411) — it does not actually hide the names, just the monospace formatting. |
| S4 | **No API key redaction on the page output** | low | The page shows env-var names (`XAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) and the provider name + purpose. It does **not** show the key values. ✓ no secrets leak. But the layout makes it look like secrets are being displayed. | Cosmetic. The "Hide names" / "Show names" toggle is honest — it shows the *variable name* and toggles to the *provider name*; neither is a secret. Confirmed safe. |
| S5 | **Crypto wallet seed (`CRYPTO_MASTER_SEED`) is in the API key list** | medium | The 16-row list includes `CRYPTO_MASTER_SEED` (`Crypto wallet seed for payments`). Showing that this seed exists on disk is not a leak of the value, but it is a hint that crypto payments are configured. | If the platform page is ever exposed beyond Founder-access, remove `CRYPTO_MASTER_SEED` and `INTAKE_JWT_SECRET` from this list. Move to a Founder-only System Details page. |
| S6 | **Root `/` is 78% full** | medium operational | `/api/v1/system/stats` shows `disk.percent: 9.7` (averaged across all drives) but `disk.drives[]` reveals root `/` is **78.2%** full (`67.6/91.1 GB` on `/dev/sda1`), while `/data` (1.74 TB) is only 1.6% full. The "Disk" card on the page shows the 9.7% average, masking the root saturation. | Frontend fix: render the highest-percent drive as the card value with a red color. Currently `disk: 9.7%` is green, hiding the 78% root. |
| S7 | **`/media/rg/BACK UP NW` is 100% full** | low operational | One external drive is full. The page doesn't surface this at all. | If the platform page shows per-drive status, this should appear. Currently it doesn't (only `disk.drives[]` does, and the page only shows `disk.percent` and `disk.total_gb`). |

---

## 6. Legacy / stale port map findings

The PlatformForge page surfaces 18 port references in total (4 in the Service Connectivity section + 13 docker product cards + 1 backend :8000 reference). Of those, the actual listening ports on the current machine are exactly 4:

| Port | Process | Service | What PlatformForge says | Truth |
|---|---|---|---|---|
| `127.0.0.1:9120` | (hermes-related) | Hermes Desktop dashboard | **not shown** | (not on the page) |
| `0.0.0.0:8787` | opencode serve (Tailscale) | OpenCode remote (phone pairing) | **not shown on the System Health row**, but DesktopPairing subcomponent pairs against it | (subcomponent uses it) |
| `0.0.0.0:7878` | openclaw | OpenClaw | "Ollama" is listed at :11434 (wrong), OpenClaw at :7878 is **not listed in Service Connectivity at all** | hidden in main view |
| `0.0.0.0:8000` | uvicorn | Backend API | ✓ "Backend API :8000" | accurate |
| `*:3005` | next-server | Empire Studio Portal (Command Center) | ✗ "Command Center :3009 → OFFLINE" | **wrong** (should be :3005 ONLINE) |

The 13 docker port cards (3001–3011) reference ports that are **not listening at all**. They reflect a historical docker-compose topology:

| Card | Port | Should be |
|---|---|---|
| Workroom Forge :3001 | not listening | Workroom is a backend router, no separate frontend service |
| LuxeForge :3002 | not listening | LuxeForge is `app/luxe/` Next.js subpath under :3005 |
| Install Forge :3003 | not listening | Was AMP install flow, now part of :3005/amp |
| Quote Forge :3004 | not listening | Quotes is a backend router, rendered inside :3005/quotes |
| MAX AI :8000 | listening | ✓ (but it's the backend, not a separate product) |
| OpenClaw AI :7878 | listening | ✓ (but missing from Service Connectivity row) |
| SupportForge :3005 | listening | ✗ wrong port (this is the same Next.js portal that hosts everything) |
| CryptoPay :3006 | not listening | not a separate service |
| ListingBot :3007 | not listening | not a separate service |
| ShippingBot :3008 | not listening | not a separate service |
| Analytics :3010 | not listening | not a separate service |
| Founder Dashboard :3009 | not listening | **this is the URL the page keeps complaining about** |
| Marketplace Hub :3011 | not listening | not a separate service |

**Net finding:** the 13 docker port cards are 100% stale. They were useful when each product was a separate docker container on a separate port. They are now **noise**. Either:
- (a) HIDE the entire Docker Products section from the main view (recommended — Founder has to scroll past 13 broken-looking entries), OR
- (b) Replace with a "Listening Ports" section that reads `ss -tlnp` and shows the 4-5 things actually live.

---

## 7. BusinessOps visibility update

`/api/v1/businessops` shipped on commit `395f6ee` (2026-06-09) and is live on the running backend. The PlatformForge page does **not** reflect it:

* **API Route Groups section:** 29 hardcoded prefixes, no `businessops` row. → **Should add.** Trivial frontend-only fix in `PlatformPage.tsx` lines 197-227. The `system-report` endpoint also does not list it (I confirmed: `any business? → []`). Either fix the system-report generator too, or add it manually to the hardcoded array.
* **AI Models & Routing section:** no entry for `businessops` (correct — it's not an AI provider).
* **Brain & Backup section:** no entry (correct — businessops is a router, not a memory system).
* **Suggestions & Known Issues section:** no entry. Could add a row: "BusinessOps Phase 1 live (16 routes, 9 bo_ tables seeded)". Useful for Founder.
* **System Health → uptime / restart-needed indicator:** the page doesn't show a "Handoff restart needed" badge, but the live backend's `current_commit.hash == startup_commit.hash == 395f6ee` (per `/api/v1/max/status`), so the backend is in sync. No new badge needed.

**Net:** the only BusinessOps-specific change is one line in the route list. **Minimum next action: add `businessops` to the routeGroups array in `PlatformPage.tsx:227`.**

---

## 8. Recommended UI cleanup lane

This is a *proposal*, not an implementation. Founder approval required before any code change.

### 1. Main PlatformForge view (Founder-critical, always visible)

```
[Header: PlatformForge · Infrastructure · Live Configuration · Refresh]

System Health (4 cards)
  CPU %  |  RAM %  |  Disk %  |  Uptime (since last backend restart)

AI Models & Routing
  Active: minimax / MiniMax-M3 · fallback OFF · AI calls ENABLED
  [provider list with Set Active / Test / Enable / Disable per row]
  Routing Policy panel with fallback toggle

CORS & Security (collapsed by default)
  Allowed Origins, Methods, Headers, Auth Mode, Database, Telegram Bot
  WARN glyph only if CORS != expected for the current lane

API Route Groups (collapsed)
  30+ rows (add /api/v1/businessops) — all real routes from /openapi.json
  clickable to open in new tab
  status pill derived from /api/v1/max/system-report.modules[]

Suggestions & Known Issues (from system-report)
  bugs in red, suggestions in amber
```

### 2. System Details drawer (collapsed by default, click to expand)

```
Service Connectivity (the 4 live checks)
  Backend API :8000       [ONLINE]
  Empire Studio Portal :3005 [ONLINE]  ← fix from "Command Center :3009"
  OpenClaw :7878          [ONLINE]    ← add (currently missing)
  Ollama :11434           [OFFLINE — intentionally disabled]  ← fix from raw OFFLINE

Brain & Backup
  Brain service: not initialized
  Total Memories: 21181 (stale-fork artifact — see REPO-TRUTH)
  Storage Path: /home/rg/empire-repo/backend/data/brain
  External Drive: No
  Active Conversations: 0
  Chat Backup: (currently not running — endpoint 404) ← show this

Ollama Local Models (collapsed)
  empty list with proper "Ollama offline (intentional — see AI Models)" label

Listening Ports (NEW)
  Replaces the 13 docker cards
  4-5 real rows from `ss -tlnp`: 8000, 3005, 7878, 8787, 9120
  each with process name and a "what is this" tooltip
```

### 3. Developer Debug section (collapsed, behind a small "Show debug" toggle)

```
Guardrails
  6 hardcoded items, but with a "(static copy — see app.services.max.guardrails)" disclaimer
  until a /api/v1/max/guardrails/status endpoint exists

API Keys & Credentials
  16 env-var names, but each row reads from a new /api/v1/system/secrets endpoint
  that returns {env_var, set: bool, last_used: ts}
  removes the "12 always show ENV gray" problem

Routing State (raw)
  full JSON dump of /api/v1/max/models.routing_state
  useful for incident debugging

Docker Products (collapsed under debug)
  current 13 cards, with a header that says "Historical docker-compose topology — most rows are stale"
  keep for now in case the docker manager gets fixed
```

### 4. Security / Secrets section (FUTURE, Founder-only)

```
API Keys (raw, with show-secret toggle and audit log of every reveal)
  only accessible after Founder-PIN re-auth
  the current 16-row list, but with the actual key prefix visible on demand
  (e.g. "XAI_API_KEY = xai-***abc (last rotated 2026-04-12)")
```

This section is **out of scope for now** — the page is local-LAN-only, so the current "API Keys & Credentials" row in the System Details drawer is fine.

### 5. Deprecated / Legacy ports hidden section (collapsed, clearly labeled as historical)

```
Legacy Docker Port Map (do not use)
  13 rows with historical ports
  bold note: "These ports are not listening. The Empire Studio Portal runs on :3005."
```

### Items to **remove entirely** from PlatformForge

* **Payment widget (`PaymentModule product="platform"`)** — the Stripe widget doesn't belong on an Infrastructure page. Move to a separate `/payments` admin page (or remove until the customer-facing Pricing page is wired up).
* **Documentation 100-files decorative list** — the static list in `lib/docs-registry.ts` is decorative. Either fix it (real-time file count from `find` + actual `xdg-open` links) or remove from this page. Belongs in a separate Documentation page if anywhere.

---

## 9. Implementation priority (suggested, Founder-approved lanes only)

| Lane | Effort | Risk | Founder value | Notes |
|---|---|---|---|---|
| L0 — **Truth labels**: rename "Command Center :3009" to "Empire Studio Portal :3005" + "Ollama OFF" to "Ollama OFF (intentional)" + "Database: empirebox.db" to "Database: empire.db" | trivial | low | high | one-liner edits in system-report generator + PlatformPage.tsx |
| L1 — **Add businessops to API route list** | trivial | none | high | add one row to `PlatformPage.tsx:227` |
| L2 — **Add live openclaw queue depth** | small | low | medium | add new chip in the OpenClaw AI provider row, sourced from `/api/v1/openclaw/queue` |
| L3 — **Replace 13 docker port cards with `ss -tlnp` truth** | medium | low | high | requires a new `/api/v1/system/listening-ports` endpoint + a small UI component |
| L4 — **Fix the hardcoded API-keys list** (read from new `/api/v1/system/secrets` endpoint) | medium | medium (could surface new info) | medium | requires new endpoint that returns `{env_var, set: bool}` for all 16 known keys; the 12 currently-gray rows become accurate |
| L5 — **Make the Guardrails section live** (read from `/api/v1/max/guardrails/status`) | medium | low | medium | new endpoint that introspects `app.services.max.guardrails` |
| L6 — **Move Service Connectivity, API Keys, Guardrails, Documentation to System Details drawer** | medium | low | medium | pure frontend restructuring; no new endpoints |
| L7 — **Deprecate the 13 docker product cards** | trivial | low | medium | hide behind "Show legacy" toggle; new users never see them |
| L8 — **Remove Payment widget from PlatformForge** | trivial | low | low | one-line delete; the widget is the same one on Pricing |
| L9 — **Address the 21,181-memories cross-repo artifact** | medium | medium | high | requires a decision: move the brain DB to `empire-repo-main/backend/data/brain/`, or symlink, or leave it and label the page. Out of scope for this audit but worth flagging. |

All lanes are **report-only** today. No lane is in implement-mode.

---

## 10. Truth audit — direct answers to Founder's specific questions

| Founder question | Answer | Source |
|---|---|---|
| Why does Command Center say `localhost:3009` offline while actual portal is on `:3005`? | The Service Connectivity entry in `/api/v1/max/system-report` is hardcoded to probe `http://localhost:3009`. The `:3009` port is from a previous era's `founder-dashboard` docker-compose attempt and is not listening. The real Command Center / Empire Studio Portal is the Next.js service on `*:3005` (PID 41351, HTTP 200). The page also does not have a `:3005` row, so the actual portal gets no status. | `connectivity[]` field of `/api/v1/max/system-report` + `ss -tlnp` + `curl :3005` |
| Is AMP Portal `:3003` real or stale? | Stale. There is no process listening on `:3003`. AMP is the Next.js subpath `app/amp/` under `:3005/amp/*` (with login at `:3005/amp/login`). | `ss -tlnp` + `find app -maxdepth 3 -iname 'login*'` (only finds `/amp/login` and `/intake/login`) |
| Are the product port cards historical/legacy and should be hidden? | Yes, all 13 are historical from a docker-compose era. The live Empire topology is: backend on `:8000` (uvicorn), portal on `:3005` (Next.js, hosts all subpages), openclaw on `:7878`, opencode on `:8787` (Tailscale), hermes on `:9120`. The 13 docker cards render `UNKNOWN` status because the docker manager can't see systemd services. Recommend hide from main view. | `/api/v1/docker/status` returns all 13 with `status: "unknown"`; `ss -tlnp` shows none of 3001-3011 are listening |
| Is Brain Status real, stale, or from old memory system? | The brain **service** is genuinely not initialized in the live uvicorn (`brain_online: false`). The brain **data** is real and lives at `/home/rg/empire-repo/backend/data/brain/memories.db` (12 MB, 21,181 rows, last modified 17:01 today). The path points at the **stale fork** (`empire-repo`), not the active worktree (`empire-repo-main`) — see REPO-TRUTH for the canonical cross-link. | `brain.brain_online` + `sqlite3 .tables` + `stat -c '%y'` |
| Is "21181 memories" a real count or stale scan? | Real. `SELECT COUNT(*) FROM memories` on `/home/rg/empire-repo/backend/data/brain/memories.db` returns 21181. The DB has 6 tables; only `memories` and `conversation_summaries` (592) have rows. The other 4 (`customers`, `customer_interactions`, `knowledge`, `tasks`) are empty. | direct SQL count |
| Is CORS `*` and Auth Mode `None` acceptable only for local/dev? | CORS `*` with `allow_credentials: true` is acceptable on `localhost` only. Acceptable on `studio.empirebox.store` ONLY because the public tunnel (`cloudflared`) only exposes `:3005`, not `:8000`. If `:8000` is ever tunneled, set `CORS_ORIGINS=https://studio.empirebox.store` in the systemd unit. Auth Mode `None` is confirmed by grepping `main.py` for any auth middleware (none). | `main.py:44-47` + `grep -E "HTTPBearer|OAuth2|get_current_user|require_auth" main.py` → 0 matches |
| Is the Stripe/payment widget real or placeholder? | Real Stripe widget from `components/business/payments/PaymentModule.tsx`. It is the same component used on the customer Pricing page (`PaymentModule product="platform"`). On PlatformForge it is **contextually wrong** — Founder sees a customer-facing payment widget on an Infrastructure page. Recommend remove from this page. | `grep -rn "PaymentModule" app/components/screens/PlatformPage.tsx` + `components/business/payments/PaymentModule.tsx` |
| Should OpenCode pairing URL use LAN IP or Tailscale URL? | **Tailscale.** The systemd unit `opencode-remote.service` listens on `0.0.0.0:8787`, but the host's Tailscale IP is `100.110.233.75` (more reliable for phone pairing than `192.168.1.190` which is the Wi-Fi LAN). The current `DesktopPairing` subcomponent may default to LAN — verify and switch to Tailscale for off-LAN access. | `ip -4 -o addr show` + `systemctl --user cat opencode-remote.service` |
| Should missing API keys be visible to Founder or moved to System Details? | **Move to System Details, but keep visible to Founder.** The current 16-row list is hardcoded; only 4 of 16 get live SET/MISSING. Other 12 always show `ENV` (gray) regardless of whether they're set. Founder-useful but inaccurate. Add a new `/api/v1/system/secrets` endpoint that returns accurate `{env_var, set: bool}` for all 16, then move the whole section to System Details drawer. | `PlatformPage.tsx:169-186, 414-441` + the conditional `isSet` derivation |
| Should Ollama OFF/unavailable be intentional and not look like a failure? | Yes, it is intentional. The AI Models row for Ollama shows `disabled_reason: founder_disabled_due_to_stall_suspected`. The page should label the Ollama section "Ollama (intentionally disabled — see AI Models)" instead of "Ollama not reachable" (which reads as a failure). | `provider_registry.ollama.disabled_reason` + `brain.ollama.online` |
| Should OpenClaw show available despite worker queue stall? | No, that's currently misleading. The provider registry says `openclaw: available: true` (no kill switch), but the worker queue is stalling (per earlier session context). Add a queue-depth chip to the OpenClaw row, sourced from `/api/v1/openclaw/queue` (or wherever the worker reports its queue). | `provider_registry.openclaw` + earlier session context |
| Should new `/api/v1/businessops` appear in the API inventory? | **Yes — and it doesn't yet.** 29 hardcoded route prefixes in the page, no `businessops` row. Add it. One-line fix. | `PlatformPage.tsx:197-227` |

---

## 11. Git status

```
$ git rev-parse --abbrev-ref HEAD
main

$ git rev-parse HEAD
395f6ee86a6923f69c2d05b66acffb3242d193e9

$ git log --oneline -1
395f6ee feat(businessops): add tenant entitlement foundation

$ git status --short
(empty)

$ git rev-list --left-right --count origin/main...main
0	0
```

Working tree clean. No edits in this session. No branches created. No worktrees. No commits. No push.

---

## 12. Files inspected

**Frontend** (the PlatformForge page surface):
* `empire-command-center/app/components/screens/PlatformPage.tsx` (644 lines, 36 KB)
* `empire-command-center/app/lib/docs-registry.ts` (the 100-doc list — read header)
* `empire-command-center/app/lib/api.ts` (the `API` and `API_BASE` constants — used to confirm URLs)

**Backend endpoints** (probed live, no code read beyond main.py):
* `GET /api/v1/system/stats` — psutil system metrics
* `GET /api/v1/system/metrics` — active_ports, uptime
* `GET /api/v1/max/models` — provider_registry + routing_state (full)
* `GET /api/v1/max/health` — desks online, telegram
* `GET /api/v1/max/brain/status` — brain, ollama, memories
* `GET /api/v1/max/system-report` — connectivity[], modules[], suggestions[], bugs[]
* `GET /api/v1/ollama/models` — ollama list (returned `not reachable`)
* `GET /api/v1/max/telegram/status` — bot config
* `GET /api/v1/docker/status` — 13 docker product stubs
* `GET /api/v1/chat-backup/status` — 404 (broken, see #39)
* `GET /api/v1/businessops/health` — confirmed live (200, phase 1, table counts)

**Configuration / system** (probed live):
* `ss -tlnp` — 5 listening ports
* `curl` probes to all 15 ports the page references
* `ip -4 -o addr show` — LAN IP 192.168.1.190 + Tailscale 100.110.233.75
* `systemctl --user cat opencode-remote.service` — pairing port 8787
* `systemctl --user cat empire-backend.service` — backend unit (earlier audit)
* `systemctl --user list-units` — 5 empire-related units
* `backend/app/main.py:44-47` — CORS config
* `grep` for any auth middleware in main.py → 0 matches
* `sqlite3` direct queries on `/home/rg/empire-repo/backend/data/brain/memories.db` — 6 tables, real counts

---

**No implementation performed. No push performed.**
