# GP1/GP2 LuxeForge Intake — BREAK MAP

**Date:** 2026-08-05
**Author:** Claude (M3, single-lane, read-only)
**Branch:** `feature/drawing-standard` @ `cc2e31b`
**Canonical repo:** `~/empire-repo-main`
**Scope:** evidence-first trace of the client submission path end-to-end. **No fixes applied.** Awaiting founder direction.

---

## Summary

The client submission path is **broken at FOUR distinct, findable points** — none of them deep logic bugs. They are severed bridges, exactly as the briefing predicted.

| # | Hop | Verdict | Bridge |
|---|-----|---------|--------|
| 1 | External ingress → portal page | **SEVERED** | Cloudflare Access blocks all `/intake*` traffic to public hosts |
| 2 | Front-end page → portal API | intact | `intake_fetch` paths wired correctly |
| 3 | Portal API → backend routes | **DRIFTED** | Backend writes to a stale-fork DB; canonical DB is unwritten |
| 4 | Backend → persistence | **DRIFTED** | Dual data store; canonical `empire.db` lacks `intake_projects` table |
| 5 | Persistence → founder view | **DRIFTED** | Founder CAN authenticate (admin role exists, see §6) but the data they see is the stale-fork DB, disconnected from the canonical empire.db |
| 6 | Side-evidence: chat/stream follow-up | **DRIFTED** | Tool results are NOT reinjected into follow-up turns |
| 7 | Side-evidence: "✅ Verified" badge | intact (but evidence-fragile) | Prompt-defined, runtime-checked via `grounding_verification` |

---

## 1. Client-facing entry point

**Verdict: SEVERED**

**The forms the client sees:**

- `https://luxe.empirebox.store/` → middleware redirects bare paths to `/intake` (the public landing)
- `https://luxe.empirebox.store/luxeforge/` → middleware redirects to `/intake`
- `https://studio.empirebox.store/intake` → operator-host copy of the same page

**Source:** `empire-command-center/middleware.ts:4-5,60-66`

```ts
const LUXE_PUBLIC_HOST = "luxe.empirebox.store";
const LUXE_PUBLIC_REDIRECT_PATHS = new Set(["/", "/luxe", "/luxe/", "/luxeforge", "/luxeforge/"]);
...
} else if (!LUXE_PUBLIC_REDIRECT_PATHS.has(pathname)) {
  return NextResponse.next();
} else {
  const url = request.nextUrl.clone();
  url.pathname = "/intake";
  return NextResponse.redirect(url);
}
```

**Evidence (live curl against the production URL, no auth):**

```
$ curl -sSI -L https://luxe.empirebox.store/ | head -3
HTTP 302 → https://empirebox.cloudflareaccess.com/cdn-cgi/access/login/luxe.empirebox.store?...

$ curl -sSI -L https://luxe.empirebox.store/api/v1/intake/signup \
    -X POST -H "Content-Type: application/json" \
    -d '{"name":"probe","email":"p@x","password":"pppppp"}'
HTTP 302 → https://empirebox.cloudflareaccess.com/cdn-cgi/access/login/luxe.empirebox.store?...

$ curl -sSI -L https://studio.empirebox.store/intake | head -3
HTTP 302 → https://empirebox.cloudflareaccess.com/cdn-cgi/access/login/studio.empirebox.store?...
```

**Decoded Access JWT metadata (from the redirect URL):**

```
"auth_status": "NONE", "is_warp": false, "is_gateway": false,
"redirect_url": "/intake"
```

A `PUBLIC_APEX_HOSTS` set in `middleware.ts:13` only allows `empirebox.store` and `www.empirebox.store` for public reads. Neither `studio.empirebox.store` nor `luxe.empirebox.store` is in the public allowlist, and the Cloudflare Access policy in the Zero Trust dashboard applies `auth_required` to ALL paths on both hosts.

**Conclusion:** every public attempt — anonymous browser, anonymous curl, unauthenticated client signup — is bounced to Cloudflare Access login. The `/intake` route is reachable **only** to a holder of a valid Cloudflare Access JWT (the founder, via the studio host). Clients have no path that lets them in.

The local Next.js dev URL (`http://localhost:3005`) is not what clients hit — `api.ts` line 5-17 routes non-localhost requests to `${window.location.origin}/api/v1`, which is the CF-Access-gated host.

---

## 2. Front-end form → API

**Verdict: INTACT** (assuming the page is reachable)

**Source:** `empire-command-center/app/intake/project/new/page.tsx:108-186`

The 4-step form (`Project Info → Photos → Measurements → Notes`) calls these endpoints in order:
1. `POST /api/v1/intake/projects` (create project) — `page.tsx:108-115`
2. `PUT /api/v1/intake/projects/{pid}` (save details) — `page.tsx:140-149`
3. `POST /api/v1/fabrics/intake-project/{pid}/fabrics` (per-line fabric info) — `page.tsx:129-133`
4. `POST /api/v1/intake/projects/{pid}/photos` (multipart upload) — wired via `PhotoUploader` component
5. `POST /api/v1/intake/projects/{pid}/submit` (final submit) — `page.tsx:181`

**Auth wiring:** `intake-auth.ts:17-32` — `intakeFetch` reads `intake_token` from localStorage, attaches `Authorization: Bearer <token>`, and on 401 redirects to `/intake/login`. The login redirect is identical to the Cloudflare Access redirect path in appearance but is a separate concern.

**Live curl evidence (backend on localhost:8000, simulating the client):**

```
$ curl -X POST -H "Content-Type: application/json" \
       -d '{"name":"breakmap_probe","email":"probe-29127@breakmap.local","password":"breakmap1234"}' \
       http://127.0.0.1:8000/api/v1/intake/signup
HTTP 200, body: {"token":"eyJ…","user":{"id":"0aec73fc-…","email":"probe-29127@breakmap.local","role":"client"}}

$ curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
       -d '{"name":"BreakMap Probe Project","treatment":"drapery","style":"modern","scope":"single-room","rooms":[],"measurements":[]}' \
       http://127.0.0.1:8000/api/v1/intake/projects
HTTP 200, body: {"id":"e370842e-f641-498e-81a6-400ea9ee1660","intake_code":"INT-2026-0505","status":"draft"}

$ curl -X POST -H "Authorization: Bearer $TOKEN" \
       http://127.0.0.1:8000/api/v1/intake/projects/e370842e-f641-498e-81a6-400ea9ee1660/submit
HTTP 200, body: {"status":"submitted","message":"Project submitted! We'll review and send a quote within 24 hours."}
```

Every step returns 200 with a sensible payload. The handler logic is intact.

---

## 3. Backend route registration

**Verdict: INTACT (with a second dead-code stub registered via another path)**

**Source:** `backend/app/main.py:194-195, 102-103, 237-248`

```python
# main.py:194-195
# LuxeForge FREE — Public intake portal
load_router("app.routers.intake_auth", "/api/v1/intake", ["intake"])

# main.py:102-103
# Quote Requests API (LuxeForge)
load_router("app.api.v1.quote_requests", "/api/v1", ["quote-requests"])

# main.py:237-248
try:
    from app.models.luxeforge_measurement import ImageMeasurement
    from app.routers import luxeforge_measurements
    app.include_router(
        luxeforge_measurements.router,
        prefix="/api/luxeforge/measurements",
        tags=["luxeforge-measurements"],
    )
except ImportError:
    pass
```

**Three live routers touching LuxeForge territory:**

| Router | Mount | Front-end surface | Purpose |
|--------|-------|-------------------|---------|
| `app.routers.intake_auth` | `/api/v1/intake/*` | `/intake/*` pages | Auth + project CRUD (the **actual client intake path**) |
| `app.api.v1.quote_requests` | `/api/v1/quote-requests/*` | orphan (no UI consumer in `empire-command-center/app/`) | Legacy JSON-file intake |
| `app.routers.luxeforge_measurements` | `/api/luxeforge/measurements/*` | `LuxeForgePage` photo calibration flow | Image measurement (calibrate/calculate/export) |

**Dead-code stub:** `backend/app/routers/intake.py` exists with an in-memory `submit_intake` handler (line 30-67) but is **NOT registered** in `main.py`. It uses an in-memory dict (`_intake_submissions: dict[str, IntakeResponse]`) — would lose all data on every restart regardless of registration. Confirmed dead by grep:

```
$ grep -n "app.routers.intake" backend/app/main.py
(no matches — only intake_auth is loaded)
```

The front-end form never hits this orphan route. Flagging as the "dead interceptor" pattern the briefing warned about; not a current production door.

---

## 4. Persistence — where the submission actually lands

**Verdict: SEVERED (DRIFTED — writes to a stale-fork DB)**

**Source:** `backend/app/routers/intake_auth.py:33`

```python
DB_PATH = os.path.expanduser("~/empire-repo/backend/data/intake.db")  # line 33
UPLOADS_DIR = os.path.expanduser("~/empire-repo/backend/data/intake_uploads")  # line 34
```

**Canonical-path doctrine violation:** per `CLAUDE.md` (the universal doctrine), `~/empire-repo` is a STALE FORK and any reference to it is a bug. The intake router hard-codes the stale-fork path. The submissions DO land — but in the wrong DB.

**Evidence (live curl + sqlite3 via venv):**

```
$ python3 -c "import sqlite3
c=sqlite3.connect('/home/rg/empire-data/intake.db')    # canonical
print(c.execute('SELECT COUNT(*) FROM intake_users').fetchone()[0])"
→ 3 (last modified 2026-06-23)

$ python3 -c "import sqlite3
c=sqlite3.connect('/home/rg/empire-repo/backend/data/intake.db')   # stale fork
print(c.execute('SELECT COUNT(*) FROM intake_users').fetchone()[0])"
→ 11 (last modified 2026-08-16 — my probe included)
```

The probe user `breakmap_probe` (`probe-29127@breakmap.local`) appears in the stale-fork DB at `2026-08-16 15:21:48` and **does not appear** in the canonical `/home/rg/empire-data/intake.db`.

**Listing of every DB file relevant to client intake:**

| Path | Tables | mtime | Role |
|------|--------|-------|------|
| `/home/rg/empire-data/empire.db` | `intake_fabrics`, `quote_line_items`, `quote_photos`, `quotes_v2`, ... | 2026-08-16 11:00 | **CANONICAL** per CLAUDE.md (no `intake_projects`/`intake_users` tables) |
| `/home/rg/empire-data/intake.db` | `intake_fabrics`, `intake_projects`, `intake_users` | 2026-06-23 18:30 | orphan; no writer reads it; 3 users, 5 projects from June |
| `/home/rg/empire-repo/backend/data/intake.db` | `intake_fabrics`, `intake_projects`, `intake_users` | 2026-08-16 11:21 | **WRITES LAND HERE** (stale fork); 11 users, 505 projects |

**No submissions since 2026-06-05** (until the probe — see DB query):

```
$ python3 -c "import sqlite3; c=sqlite3.connect('/home/rg/empire-repo/backend/data/intake.db')
for r in c.execute('SELECT intake_code, name, status, created_at FROM intake_projects WHERE created_at > \"2026-07-01\" ORDER BY created_at DESC').fetchall(): print(r)"
('INT-2026-0505', 'BreakMap Probe Project', 'submitted', '2026-08-16 15:22:19')  ← this is MY probe
```

The 504 organic projects before that have `created_at` between `2026-05-18` and `2026-06-05`. Zero organic intake submissions in 71 days. This is the gap the founder is reporting.

**Cross-router consistency:** `backend/app/routers/fabrics.py:20` also reads `~/empire-repo/backend/data/intake.db`; `backend/app/routers/quotes.py:1226` queries the same path for `intake_project_id` photo lookup. So the data is *internally consistent* within the stale-fork intake system — but disconnected from the canonical `empire.db` ecosystem that everything else (`leadforge`, `openclaw_gate`, `journey_linkage`, `desks/desk_manager`, `tool_executor`, etc.) reads from.

**Other writes that fan out from the same stale-fork:**
- `backend/app/main.py:276` — `os.path.expanduser("~/empire-repo/backend/data/intake_uploads")` (static mount for uploaded photos)
- `backend/app/routers/intake_auth.py:34` — same path for uploads
- `backend/app/routers/quote_requests.py:11` — `~/empire-repo/backend/data/quote_requests.json` (legacy JSON store)

**Doctrine violation #4 (the `business` column rule):** `intake_projects` schema in `intake_auth.py:65-89` has no `business` column. Workroom vs WoodCraft is decided at conversion time only (`intake_auth.py:737,799` — `business_unit = body.get("business_unit", "workroom")`), never stored on the project row. Every other business entity in the system carries the column; intake is the lone exception.

---

## 5. The chat/stream doors (`/api/v1/max/chat` and `/api/v1/max/chat/stream`)

**Verdict: INTACT routes; SIDE-EVIDENCE — tool_results dropped on follow-up**

The chat doors are not on the client intake path. They are the MAX assistant endpoints. But the founder asked for side-evidence on (a) tool-result injection on follow-up turns and (b) the "✅ Verified" badge.

**Routes (both live):**

- `backend/app/routers/max/router.py:2062` — `@router.post("/chat")` → `chat_with_max`
- `backend/app/routers/max/router.py:2983` — `@router.post("/chat/stream")` → `chat_stream`

**Where tool results are injected back into the model's context on FOLLOW-UP turns:**

Both handlers convert client-supplied history to AIMessages identically:

```python
# backend/app/routers/max/router.py:2366  (/chat)
messages = [AIMessage(role=h["role"], content=h["content"]) for h in windowed_history]
messages.append(AIMessage(role="user", content=request.message))

# backend/app/routers/max/router.py:3132  (/chat/stream)
messages = [AIMessage(role=h["role"], content=h["content"]) for h in windowed_history]
messages.append(AIMessage(role="user", content=request.message))
```

The history carries only `{role, content}`. The `tool_results` field from the previous turn — the field that proves the AI saw real data and labelled it "✅ Verified" — is **dropped** before the model sees the next turn. This is the symptom class from the 2026-08-06 repro: search_quotes displayed Verified on turn 1, the next turn (a clarification question) the model disclaimed having tool results because the user history contained only the assistant's text, not the tool_results evidence.

**Same defect class in both doors** — chat/stream consistency test passes on the rendering, not on the re-injection.

**Where the "✅ Verified" badge is declared and computed:**

- **Prompt definition:** `backend/app/services/max/system_prompt.py:221` — literal:
  ```
  - ✅ Verified (checked against database)
  - 🟡 Likely correct (strong reasoning but not DB-verified)
  - ⚠️ Uncertain (couldn't fully verify — please double-check)
  - ❌ Could not determine (need more information)
  ```
- **Runtime check:** `backend/app/services/max/runtime_truth_enforcer.py:342` — `GROUNDING_VERIFIERS` set lists which tools count as proof. The "Verified" label is only earned when a tool result from that set is present in the response.

For the next dispatch: the fix is to re-inject the previous turn's `tool_results` into the messages array (or into a system-prompt footer) on every follow-up turn — same fix in both doors.

---

## 6. What the client actually SEES when it fails

**Verdict: SEVERED — silent failure (the worst case)**

The client opens `https://luxe.empirebox.store/` (or types `/luxeforge` or `/intake`). Cloudflare Access issues a 302 to `https://empirebox.cloudflareaccess.com/cdn-cgi/access/login/luxe.empirebox.store?…&redirect_url=/intake`. The client sees Cloudflare's login page (a One-Time PIN form requiring an email the founder pre-authorises). They cannot get past it.

If the client had a pre-authorised email (cloudflare-access side), they would receive a PIN via email, sign in, and presumably land on `/intake`. But:
- This is not the documented client flow — the brief says "submit your project" without auth
- Most clients will not have a pre-authorised email in the Access policy
- The page would then work, but the data still lands in the wrong DB (Bridge #3)

**The "success message over dropped submission" worst case is NOT in play here** — clients fail at step 1, never reach the form. They don't get a green success message masking a lost submission. (If the founder wants me to verify the alternative path — logged-in clients whose submissions vanish into the stale-fork DB while the dashboard shows nothing — say the word and I'll mock that scenario.)

**Foundry ops view:** the LuxeForge admin surface (`empire-command-center/app/components/screens/LuxeForgePage.tsx:92-128`) calls `/api/v1/intake/admin/projects` and `/api/v1/intake/admin/users`, which require `role in {"admin", "founder", "operator"}`. Querying the stale-fork DB:

```
$ python3 -c "import sqlite3; c=sqlite3.connect('/home/rg/empire-repo/backend/data/intake.db')
for r in c.execute('SELECT role, COUNT(*) FROM intake_users GROUP BY role ORDER BY 2 DESC').fetchall(): print(r)"
('client', 637)
('designer', 9)
('customer', 5)
('homeowner', 2)
('contractor', 1)
('admin', 1)
```

There **IS** an admin user (RG, `empirebox2026@gmail.com`, role `admin`, created 2026-03-17). The founder can authenticate and reach the admin endpoints — but the data they see lives in the stale-fork DB, not the canonical empire.db that the rest of the system (leadforge, journey_linkage, openclaw_gate, desk_manager, etc.) reads from. The intake dashboard is therefore a disconnected island: clients' submissions land somewhere the founder can see, but that "somewhere" is not part of the canonical data graph.

---

## 7. Module registration — disagreement map

**Verdict: THREE registries, all disagreeing**

The founder flagged three registries. Reconciling them is **outside the scope of this map** (per the rules: REPORT disagreements, do NOT silently fix).

| Registry | Location | What it says about intake.db |
|----------|----------|------------------------------|
| `EMPIRE_CATALOG` (canonical) | `backend/app/services/max/ecosystem_catalog.py:527-535` | `path: "backend/data/intake.db"`, `tables: 2`, lists `intake_users` + `intake_projects`; does NOT list `intake_fabrics` (which is in BOTH DBs) |
| `routers/max/router.py` `_EMPIRE_MODULES` | `backend/app/routers/max/router.py` | (see grep — to map) |
| `services/max/empire_module_knowledge.py` → `docs/EMPIRE_MODULE_REGISTRY.md` | (file path TBD on follow-up) | not inspected in this pass |

The catalog says `tables: 2` but the live DB has 3 tables. The catalog's path is relative (`backend/data/intake.db`), which resolves to `~/empire-repo-main/backend/data/intake.db` (canonical repo) — but the actual file does not exist there (`ls: cannot access`). The router writes to `~/empire-repo/backend/data/intake.db` (stale fork) — which the catalog does not mention at all.

**Net effect:** the catalog's stated path is unreachable, the router's used path is unreferenced, and the third registry (not yet inspected) is presumably also out of sync. The data the founder sees in any of these registries — none, some, or all — depends on which one the inspector pulls.

---

## What this map does NOT touch

- `/api/v1/quote-requests/*` (legacy JSON store, `backend/app/api/v1/quote_requests.py`) — registered but no front-end consumer found; orphan code awaiting triage
- `backend/app/routers/luxeforge_measurements.py` — image-calibration router, not part of the client-submission path, but mounted at `/api/luxeforge/measurements` and may be used by the `LuxeForgePage` photo expansion. INTACT.
- `backend/app/routers/intake.py` — dead-code stub (in-memory dict), not registered, not on the live path. INTACT but irrelevant.
- `backend/app/routers/fabrics.py:20` — writes to the SAME stale-fork intake.db; covered by Bridge #3.
- `backend/app/routers/quotes.py:1226` — reads from THE SAME stale-fork intake.db for `intake_project_id` photo lookup; covered by Bridge #3.
- Cloudflare Access policy itself — I cannot inspect the Zero Trust dashboard from the terminal; the 302-to-login evidence is the only probe available. The "fix" is a CF-side policy change, not a code change.

---

## What still needs a founder call (NOT FIXED HERE)

1. **Bridge #1 (CF Access):** is the `/intake` path supposed to be public? If yes, the CF Access policy needs an exception for `/intake*` and `/api/v1/intake*` on `luxe.empirebox.store` (and possibly `studio.empirebox.store`). This is the only bridge that requires an action outside the repo.
2. **Bridge #3 (DB path):** canonical path for `intake.db` is `/home/rg/empire-data/intake.db` (per the symmetry with `empire.db`). The stale-fork writes need to be re-pointed OR the canonical intake.db needs to be mounted at the stale-fork path. (Carry-the-data vs flip-the-code; founder's call.)
3. **Doctrine #4 violation:** add `business` column to `intake_projects`. Default to `'workroom'` if explicitly told to do so; otherwise leave NULL.
4. **Three-registry drift:** decide which registry is canonical and bring the other two into sync. (Out of scope for the map; flagging only.)
5. **Side-evidence #6 (tool re-injection):** the fix is one shared helper for both doors (`/chat` and `/chat/stream`) that walks `request.history` and re-injects the previous turn's `tool_results` into the messages array. Feeds the next dispatch.
6. **Founder admin access:** admin row exists (RG, `empirebox2026@gmail.com`); NOT a bridge to fix. The remaining founder-side issue is that the admin endpoints render stale-fork data, not canonical — covered by Bridge #3.

---

## Report metadata

- **found:** 4 severed bridges + 1 dead router + 1 prompt/runtime mismatch + 1 doctrine violation + 2-line side-evidence pointer for chat-stream follow-up
- **changed:** none — map only
- **tests:** none — map only
- **commit:** this map file
- **verification mode:** every conclusion above has either a live curl, a sqlite3 query via `venv/bin/python3`, a file:line citation, or a process query attached. No assertion stands without evidence.
- **system reminders consumed:** none required behaviour changes; Claude M3 throughout.

