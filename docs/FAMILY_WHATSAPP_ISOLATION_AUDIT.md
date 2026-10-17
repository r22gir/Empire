# Family WhatsApp isolation audit (Phase 0)

**Audit only.** No behavior changes, no merge, no deploy.

Written 2026-10-10. Covers Max-e (Juan Diego, edition `amp`, port **8011**, data `/data/amp`) and Maxine (Camilo, edition `maxine`, port **8012**, data `/data/maxine`) versus Rafael’s founder / Workroom edition (unset `EMPIRE_EDITION`, port **8000**, typical data `~/empire-data`, host `studio.empirebox.store`).

Rules this Phase 0 must keep: draft-only / no sends to clients; **20%** usage cap per brother; included models only (family: MiniMax M3); never print secrets; nothing deployed from this document.

---

## Bases checked

| Tree | Tip (this audit) | WhatsApp stack |
|------|------------------|----------------|
| **`feature/amp-edition`** (this PR’s base) | `25cff7ae` | **`backend/app/services/whatsapp_cloud.py`** + `backend/app/routers/whatsapp.py`. Voice-to-document borrador, owner-number gate, `$EMPIRE_DATA_DIR/whatsapp.db`. **No** Phase 0 job folders, **no** chat-log viewer, **no** `client_aliases` merge. |
| **`origin/cursor/whatsapp-phase0-folders-8454`** (PR #94, includes PR #91) | `9c34d3eb` | **`backend/app/services/max/whatsapp_channel.py`**, `whatsapp_log.py`, `whatsapp_folders.py`. Chat log + media + inbox + jobs + founder-only repo aliases. |
| **`origin/deploy/pr82-84-85`** | `86f5889a` | `whatsapp_channel.py` + calling + webhook router. **No** `whatsapp_log.py`, **no** `whatsapp_folders.py`, **no** chats API. |
| **`origin/cursor/guided-whatsapp-setup-9d3e`** (PR #80, draft, **not merged**) | — | Interview-embedded Meta walkthrough + `$EMPIRE_DATA_DIR/whatsapp_credentials.json`. |

### PR #92 is on this base

[PR #92](https://github.com/r22gir/Empire/pull/92) (`Max-e Spanish search and AMP interview defaults`) **merged into `feature/amp-edition` at 2026-10-10T20:40:47Z**. Merge commit `bca37347305e077eaf326fe5aa5e83b52e57400d` is an ancestor of `25cff7ae`. This docs branch is cut from that tip.

### How WhatsApp from PR #91 / #94 reaches family editions

**It is not in `feature/amp-edition`.** Family processes that run from this tree (Max-e `deploy/empire-amp.service` → `/home/rg/empire-repo/backend` on 8011; Maxine `deploy/empire-maxine.service` → `/home/rg/empire-maxine/backend` on 8012) load **`whatsapp_cloud.py`**, not `max/whatsapp_channel.py`.

| If family uvicorn is started from… | WhatsApp code they get |
|------------------------------------|------------------------|
| `feature/amp-edition` (current Dell family path) | `whatsapp_cloud.py` only |
| `deploy/pr82-84-85` | Channel + calling; **no** durable chat log / folders / alias isolation from #94 |
| PR #94 branch (`cursor/whatsapp-phase0-folders-8454`) | Full Phase 0 stack + `is_founder_edition()` |

There is **no automatic backport**. Phase 0 isolation from #91/#94 reaches amp/maxine only after an explicit cherry-pick or merge of those files onto a family checkout (or after family units are pointed at a tree that already contains them). Until then, family WhatsApp is the older Cloud module documented in `docs/WHATSAPP_CHANNEL.md` on this branch.

---

## 1. Isolation matrix (amp and maxine)

Same answers for both brothers unless a row says otherwise. “Separate” means a distinct path or env file when the edition unit is configured as documented (`deploy/AMP_EDITION.md`, `deploy/MAXINE_EDITION.md`, `deploy/empire-amp.env.example`, `deploy/empire-maxine.env.example`).

| Store / control | Max-e (`amp`) | Maxine (`maxine`) | Founder (Workroom) | Separate from Rafael? | Separate from each other? | Paths / code |
|-----------------|---------------|-------------------|--------------------|-----------------------|---------------------------|--------------|
| **Data dir** | `/data/amp` | `/data/maxine` | `~/empire-data` (typical) | **Yes**, if `EMPIRE_DATA_DIR` set | **Yes** | `backend/app/edition.py` `EDITION_PROFILES`, `require_data_root()`, `apply_amp_process_paths()`; env `EMPIRE_DATA_DIR` |
| **WhatsApp state DB (this branch)** | `/data/amp/whatsapp.db` | `/data/maxine/whatsapp.db` | `~/empire-data/whatsapp.db` if `EMPIRE_DATA_DIR` unset | **Yes**, if data root set; **falls back to `~/empire-data`** if not | **Yes** | `whatsapp_cloud._state_path()` |
| **WhatsApp chat log (PR #94 only)** | `/data/amp/whatsapp/whatsapp_chat_log.db` | `/data/maxine/whatsapp/whatsapp_chat_log.db` | `$EMPIRE_DATA_DIR/whatsapp/whatsapp_chat_log.db` | **Yes**, after #94 is on the process | **Yes** | `backend/app/services/max/whatsapp_log.py` `_db_path()` — **file does not exist on this branch** |
| **labels.json (PR #94 only)** | `/data/amp/whatsapp/labels.json` | `/data/maxine/whatsapp/labels.json` | edition file or `WHATSAPP_LABELS` | **Yes** (after #94) | **Yes** | `whatsapp_log._phonebook_paths()`. **Not on this branch.** Amp-edition uses `WHATSAPP_OWNER_NUMBERS` only. |
| **Inbox / media (this branch)** | `$root/wa-media` next to `whatsapp.db`; brain inbox `$root/inbox` | same under `/data/maxine` | Workroom data / checkout | **Intended yes**; see leaks | **Yes** if roots differ | `whatsapp_cloud` media folder; `edition.brain_sync_storage_paths()` |
| **Inbox / media (PR #94)** | `/data/amp/whatsapp/{inbox,media}/` | `/data/maxine/whatsapp/{inbox,media}/` | founder `$EMPIRE_DATA_DIR/whatsapp/…` | **Yes** after #94 | **Yes** | `whatsapp_log.inbox_dir()`, `media_dir()` |
| **Jobs root (PR #94 only)** | `/data/amp/jobs` (or `WHATSAPP_JOBS_ROOT`) | `/data/maxine/jobs` | founder `$EMPIRE_DATA_DIR/jobs` | **Yes** after #94 | **Yes** | `doc_lookup.jobs_root()`, `data_paths.jobs_dir()`. **No job-folder filing on this branch** (photos → ConstructionForge timeline via `instance_files.save_photo()`). |
| **client_aliases (this branch)** | **Module absent** | **Module absent** | N/A on this tree | N/A | N/A | No `doc_lookup.py` / `client_aliases.json` read in family WhatsApp on `feature/amp-edition`. |
| **client_aliases (after PR #94)** | **Only** `/data/amp/client_aliases.json` | **Only** `/data/maxine/client_aliases.json` | Merge **repo** `backend/app/config/client_aliases.json` + edition file | **Yes** (`is_founder_edition()`) | **Yes** | `doc_lookup.load_client_aliases()`, `is_founder_edition()` (`9c34d3eb`). Repo file is **founder-only**. |
| **WhatsApp env file / secrets** | `/home/rg/empire-amp.env` (not committed) | `/home/rg/empire-maxine.env` | `backend/.env` via `systemd/empire-backend.service` | **Yes**, if operators do not copy Workroom `.env` | **Yes** | `deploy/empire-amp.service` `EnvironmentFile=`; `deploy/empire-maxine.service`. Templates **do not yet list `WHATSAPP_*`**. |
| **Webhook route** | `GET/POST /api/v1/whatsapp/webhook` | same path | same path | Route name is **shared**; **host/port differ** | Same | `backend/app/routers/whatsapp.py`. Family docs: `https://<this-instance-host>/api/v1/whatsapp/webhook`. PR #80 defaults `https://wa-amp.empirebox.store/…` and `https://wa-maxine.empirebox.store/…` (those hostnames are **not** in `deploy/AMP_EDITION.md`). |
| **Hostname / process** | `amp.empirebox.store` UI; uvicorn **127.0.0.1:8011** | `maxine.empirebox.store`; **127.0.0.1:8012** | `studio.empirebox.store`; **8000** | **Yes** | **Yes** | `edition.EDITION_PROFILES`; cloudflared notes in `deploy/AMP_EDITION.md` |
| **Founder PIN** | Optional `# FOUNDER_PIN=` in amp env; family **web** login is allowlist + `AMP_JWT_SECRET`, not Rafael’s PIN | same in maxine env | `FOUNDER_PIN` in Workroom `.env` | **Separate if set per file**; empty on family is fail-closed for PIN tools | **Yes** if different values | `deploy/empire-*.env.example`; `tool_executor.py`; `routers/auth.py` |
| **Meta tokens** | Must be **this instance’s** `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` | Own set | Rafael’s set | **Yes** when env files differ; channel ignores other `PHONE_NUMBER_ID`s | **Yes** | `whatsapp_cloud.missing_config()`, `channel_status()`; docs: “do not share a token” |
| **Allowlist (this branch)** | `WHATSAPP_OWNER_NUMBERS` — **Juan Diego +57 317 443 7313** (set by hand; **not in the example env**) | `WHATSAPP_OWNER_NUMBERS` — **Camilo +57 312 284 2350** (same) | Workroom owner numbers in Workroom env | **Yes** if each env lists only that brother | **Yes** | `whatsapp_cloud.owner_numbers()`. Empty list → channel `closed`, no replies. |
| **Allowlist (PR #94)** | Must **not** inherit repo `backend/app/config/business.json` (Rafael `business_phone`). Use edition `labels.json` + `WHATSAPP_FOUNDER_PHONES` | same | `founder_allowlist()` | **Not automatically**; see M2 | **Not automatically** | `whatsapp_channel.founder_allowlist()` |
| **Web allowlist (site login)** | `/data/amp/amp/allowlist.json` | `/data/maxine/amp/allowlist.json` | Workroom does not use this | **Yes** | **Yes** | `amp_allowlist.allowlist_path()` |
| **Usage cap / models** | 20%, MiniMax M3 forced | 20%, MiniMax M3 forced | Uncapped Workroom models | Separate `usage.db` | Separate | `instance_usage.py`, `docs/INSTANCE_USAGE_CAP.md`; `apply_amp_process_paths()` sets `INSTANCE_USAGE_CAP_PCT=20`, `MAX_SELECTED_PROVIDER=minimax` |
| **Draft / send** | `documents_auto_send: False`; PDF only after `envía el borrador` / `send the draft`; owner numbers only | same | PR #94: allowlist + “Not sent” on photo quotes | **No client sends** | — | `whatsapp_cloud.send_draft_document()`, `_reply_pipeline()` |

**Bottom line for (1):** With documented systemd env files and distinct Meta apps, **data dir, WhatsApp DB, inbox/media (intended), jobs (after #94), edition aliases (after #94), env/secrets, host/port, PIN, tokens, and owner-number allowlist are designed to be fully separate**. Gaps: example env files omit `WHATSAPP_*` and owner numbers; webhook hostnames for dedicated `wa-amp` / `wa-maxine` are unspecified on this branch; PR #94 allowlist still merges repo `business.json` unless family labels override; two checkout-relative leaks (below) can still see Rafael’s tree when Max-e shares `/home/rg/empire-repo`.

---

## 2. Can Max-e or Maxine see Rafael’s chats, jobs, clients, quotes?

**By design, no** — if `EMPIRE_EDITION`, `EMPIRE_DATA_DIR`, `EMPIRE_TASK_DB`, `EMPIRE_API_BASE`, Meta tokens, and owner numbers are the family values, and (after #94) `is_founder_edition()` is false.

**In practice, yes, through the leak paths below.** Severity is for a family process that is *supposed* to be isolated.

### HIGH

| ID | What leaks | Why | Where |
|----|------------|-----|--------|
| **H1** | Rafael **inbox JSON** (email/workroom inbox files) | `/api/v1/inbox/*` always uses `~/empire-repo/backend/data/inbox` with no `is_family_edition()` guard. Max-e’s unit uses that same checkout. | `backend/app/routers/inbox.py` (`INBOX_DIR`) |
| **H2** | Rafael **client names and addresses** via WhatsApp job hints | On **PR #91 only** (not this branch, not #94), `load_client_aliases()` reads repo `backend/app/config/client_aliases.json`. `new job dahlia` → `nehal-elrefai`. | `doc_lookup.py` on PR #91. **Fixed on PR #94 `9c34d3eb`** (`is_founder_edition()`). |
| **H3** | Rafael **quotes / customer names** | `doc_lookup._quote_customer()` queries `quotes_v2` on `get_db()` / `EMPIRE_TASK_DB`. Default Workroom DB is `~/empire-data/empire.db`. Shared task DB ⇒ WhatsApp text with `EST-…` resolves Rafael’s customer. | PR #94 `doc_lookup._quote_customer()`; family must set `EMPIRE_TASK_DB=/data/amp/empire.db` or `/data/maxine/empire.db` (examples already do). |
| **H4** | Rafael **Final Docs** | `whatsapp_channel.whatsapp_doc_request()` → `find_docs()` → `EMPIRE_PORTAL_INTERNAL_URL` default `http://localhost:3005` (Workroom UI). | PR #94 `whatsapp_channel.py` (~1404), `doc_lookup._hub_base()` |
| **H5** | Rafael **chats / jobs / quotes via Max tools** | Allowlisted inbound WhatsApp on the #94 channel runs the full Max text handler (`routers/max/router.py`). Wrong data dir or API origin ⇒ Workroom tools. | PR #94 `whatsapp_channel.default_text_handler` |
| **H6** | Full **WhatsApp chat log** | Command Center `GET /api/v1/whatsapp/chats*` is PIN-gated but **not edition-bound**. Pointing family UI at Workroom `:8000` (or sharing `FOUNDER_PIN` + proxy) shows Rafael’s log. | PR #94 `backend/app/routers/whatsapp.py` |
| **H7** | Entire WhatsApp + jobs tree | Shared `EMPIRE_DATA_DIR` or `WHATSAPP_JOBS_ROOT` across units. | Operational; `data_paths.data_root()` |

H2–H6 apply **only after** the #91/#94 stack is on the family process. H1 and H7 apply **today** on `feature/amp-edition` if Max-e shares Rafael’s checkout.

### MEDIUM

| ID | What leaks | Why | Where |
|----|------------|-----|--------|
| **M1** | Legacy **chat JSON** under the checkout | `/api/v1` chats file API uses `backend/data/chats` relative to the repo, not `$EMPIRE_DATA_DIR`. Max-e on `/home/rg/empire-repo` can read/write Rafael’s legacy chat files. Unified store is edition-scoped. | `backend/app/api/v1/chats.py` (`CHATS_DIR`) |
| **M2** | Rafael’s **phone in family allowlist** (PR #94) | `founder_allowlist()` always loads repo `backend/app/config/business.json` `business_phone`. Family channel would accept Rafael’s WhatsApp as “owner” unless labels/env override. | `whatsapp_channel.founder_allowlist()` |
| **M3** | Cross-talk of **24h windows / last-docs** (PR #94) | `whatsapp_channel._state_path()` is `backend/data/whatsapp_channel_state.json` — **not** under `EMPIRE_DATA_DIR`. Shared checkout ⇒ shared state. | `whatsapp_channel.py` lines 59–60 |
| **M4** | WhatsApp state falls back to **`~/empire-data`** | If `data_root_or_none()` is None, `_state_path()` uses `~/empire-data/whatsapp.db`. Mis-set family unit → Rafael’s WhatsApp SQLite. | `whatsapp_cloud._state_path()` on this branch |
| **M5** | Shared **`backend/.env`** load | `main.py` `load_dotenv(backend/.env)`. Edition keys are preserved from systemd, but a missing `EnvironmentFile` leaves Workroom tokens/PIN/data dir. | `backend/app/main.py`; `deploy/empire-amp.service` |
| **M6** | Draft **quotes co-mingled** | Photo-quote on #94 writes `quotes_v2` for that process. Shared task DB ⇒ family drafts sit next to Rafael’s ESTs. | `whatsapp_channel.default_photo_handler` |
| **M7** | Example **owner email** is still `empirebox2026@gmail.com` | Both `deploy/empire-amp.env.example` and `empire-maxine.env.example` seed `AMP_OWNER_EMAIL` with Rafael’s mailbox. Site allowlist can start as Rafael, not the brother. | env examples; `amp_allowlist` seed |

### LOW

| ID | What leaks | Why | Where |
|----|------------|-----|--------|
| **L1** | Disabled Workroom routers still hardcode `~/empire-repo/backend/data/*` | Hidden by `AMP_DISABLED_PREFIXES` (`edition.py`) for craft/luxe/drawings. Any accidentally exposed route is a footgun. | e.g. fabrics / apostapp / archiveforge routers |
| **L2** | Committed `client_aliases.json` in git | Runtime blocked for family on #94; still visible in any clone. | `backend/app/config/client_aliases.json` (PR #94 tree) |
| **L3** | `migrate_json_chats()` can read checkout chats | Only if someone runs that migration on a family host. | `unified_message_store.py` |
| **L4** | Multi-worker on one edition DB | Duplicate WhatsApp asks; not a cross-edition read. | `docs/WHATSAPP_CHANNEL.md` on PR #94 |

**Quotes on this branch:** family `apply_amp_process_paths()` creates `$EMPIRE_DATA_DIR/quotes` and sets `EMPIRE_TASK_DB`. Canonical `data_paths.quotes_data_dir()` follows `EMPIRE_DATA_DIR`. **Quotes stay isolated when those env vars are correct.** The leak is H3/M6 when they are not.

**Chats on this branch:** the **unified** assistant store is under `$EMPIRE_DATA_DIR/assistant/brain/`. The **legacy** `/chats` file API is the leak (M1). There is no `whatsapp_chat_log.db` until #94.

---

## 3. Guided setup (PR #80) vs in-site Spanish tutorial

### What PR #80 covers

[PR #80](https://github.com/r22gir/Empire/pull/80) is **draft, open, not merged**, base `feature/amp-edition`. It adds a **WhatsApp step inside the existing Spanish interview**, not a standalone help page.

| Piece | Path (on `cursor/guided-whatsapp-setup-9d3e`) |
|-------|-----------------------------------------------|
| Interview route | `/amp/empresas/entrevista` — `empire-command-center/app/amp/empresas/entrevista/page.tsx` |
| Step order | `app/lib/interviewWelcome.mjs`: … `empresa` → **`whatsapp`** → `industria` … (Maxine inserts `argos` after welcome) |
| Dashboard link | `WhatsAppStatus.tsx` “Configurar →” opens the **full** entrevista (not the WhatsApp step) |
| Save / test API | `POST /api/v1/whatsapp/credentials`, `POST /api/v1/whatsapp/test` (read-only Graph GET) |
| Secret file | `$EMPIRE_DATA_DIR/whatsapp_credentials.json` mode `0600` (`whatsapp_cloud.py` on that branch) |
| Tests | `backend/tests/test_whatsapp_setup.py` (mocks; no live Graph) |
| Docs | `docs/WHATSAPP_CHANNEL.md` EN + ES on that branch |

**Screens (embedded `WhatsAppSetupStep`):** intro (text / voice / PDF; Phase 2 voice-call note) → already-have-Meta? → **7 Meta steps** (own Facebook, **not Rafael’s**; Business app; WhatsApp product; Meta **test number**; 6-digit verify; Phone Number ID + 24h token; App Secret) → credentials form (IDs, token, secret, **owner numbers**, optional verify token) → webhook URL + verify token copy → Probar / Guardar / skip.

**Checkpoints PR #80 already defines:** own Facebook; Business app; WhatsApp product; test number verified; IDs copied; callback URL + `messages` subscribed; owner number saved; file `0600`; Graph test OK; `webhook_verified`.

**It does assume each brother’s own Meta account and own Cloud API test number.** Copy on the step says to use **TU PROPIA cuenta de Facebook (no la de Rafael)**.

### What is missing for a brother to finish alone

On **`feature/amp-edition` today** the entrevista page **exists** (`app/amp/empresas/entrevista/page.tsx`) but **`interviewWelcome.mjs` has no `whatsapp` step**. `/ayuda/voz` only points at `docs/WHATSAPP_CHANNEL.md` (repo markdown, not a rendered page). Example env files have **no `WHATSAPP_*` and no owner numbers**.

Even after PR #80:

- No standalone **`/ayuda/whatsapp`** (device-access pattern already exists at `/ayuda/dispositivos`).
- Dashboard “Configurar” does not deep-link `?paso=whatsapp`.
- Maxine still uses the `/amp/empresas/…` URL on `maxine.empirebox.store`.
- `wa-amp.empirebox.store` / `wa-maxine.empirebox.store` are **code defaults only** — not in `deploy/AMP_EDITION.md` / `MAXINE_EDITION.md`. Brothers cannot complete Meta’s callback without Rafael (or ops) publishing those hostnames to **8011 / 8012**.
- 24h token → permanent system-user token is mentioned, not a click-path.
- No post-onboarding settings page; skip does not persist `whatsapp_setup_status` in the UI.
- Credential routes must stay behind the family allowlist gate (verify before merge).

### In-site Spanish tutorial this Phase 0 needs

Same Next app, edition via `NEXT_PUBLIC_EMPIRE_EDITION`. One page, two hosts.

| Edition | Site | Route |
|---------|------|-------|
| Max-e | `https://amp.empirebox.store` | **`/ayuda/whatsapp`** |
| Maxine | `https://maxine.empirebox.store` | **`/ayuda/whatsapp`** |

Reuse the help shell from `empire-command-center/app/ayuda/dispositivos/page.tsx` + `app/lib/deviceAccess.mjs`. Link it from `app/ayuda/page.tsx`. Optional later: `/amp/empresas/entrevista?paso=whatsapp`.

**Content outline (Spanish) and checkpoints**

1. **Qué necesitas** — tu celular con WhatsApp, tu Facebook, el navegador. **Tu cuenta, no la de Rafael.** ✓ brother confirmed.
2. **Meta for Developers** — crear cuenta / iniciar sesión. ✓
3. **App tipo Negocios + producto WhatsApp.** ✓
4. **Número de prueba de Meta** — verificar **tu** celular (código de 6 dígitos). Juan Diego: destino del allowlist **+57 317 443 7313**. Camilo: **+57 312 284 2350**. ✓
5. **Copiar** Phone Number ID, token (24 h), App Secret. Never paste into chat with Rafael’s Max. ✓
6. **Webhook** — pegar la URL que muestre **esta** instancia (`https://amp.empirebox.store/api/v1/whatsapp/webhook` or `https://wa-amp…` if ops created it; Maxine analog). Verify token. Suscribir `messages`. Verificar y guardar. ✓ handshake (`webhook_verified`).
7. **En el centro de mando** — `WHATSAPP_OWNER_NUMBERS` = only that brother’s digits; Guardar; Probar conexión (Graph **read-only**, no send). ✓
8. **Probar desde tu celular** al número de prueba (optional; do not message clients). ✓ inbound from owner only.
9. **Después (not Phase 0 send)** — token permanente de system user; SIM real; plantillas 24 h. Phase 2: llamadas.
10. **Límites** — borrador solamente; 20% de uso; MiniMax incluido; nada se publica ni se manda a clientes.

---

## 4. Phased implementation plan (still no deploy)

Mocks only. Reuse `backend/tests/_live_data_guard.py` (already refuses `/data/amp`, `/data/maxine`, live Graph).

### Phase 0.0 — this audit (docs only)

- Land `docs/FAMILY_WHATSAPP_ISOLATION_AUDIT.md` on a docs branch from `feature/amp-edition`.
- No code, no env, no Meta, no merge.

### Phase 0.1 — isolation hardening on `feature/amp-edition` (code later)

- Point `inbox.py` `INBOX_DIR` and `api/v1/chats.py` `CHATS_DIR` through `edition.require_data_root()` / `data_paths.data_root()` when `is_family_edition()`.
- Tests: family `EMPIRE_EDITION=amp` + tmp `EMPIRE_DATA_DIR` cannot `open` `~/empire-repo/backend/data/inbox` or `backend/data/chats` (live-data guard already fails those writes).
- Add `WHATSAPP_*` **placeholders** (no values) and commented `WHATSAPP_OWNER_NUMBERS` to `deploy/empire-amp.env.example` / `empire-maxine.env.example`. Do not commit real tokens or the brothers’ numbers in git if Rafael prefers them only on the Dell.
- Fail closed if family `whatsapp_cloud._state_path()` would land in `~/empire-data`.

### Phase 0.2 — decide the WhatsApp engine

| Option | Work | Tests |
|--------|------|-------|
| **A. Keep `whatsapp_cloud.py` on family** | Finish PR #80 extract (credentials file + entrevista step) onto amp-edition. Leave #94 on Workroom. | Existing `test_whatsapp_cloud.py` + `test_whatsapp_setup.py` (from #80) |
| **B. Port PR #94 stack onto family checkouts** | Cherry-pick `whatsapp_log.py`, `whatsapp_folders.py`, channel bits; keep `is_founder_edition()`; **do not** load repo aliases; **do not** use Workroom `business.json` as family allowlist (edition `labels.json` + `WHATSAPP_OWNER_NUMBERS` / `WHATSAPP_FOUNDER_PHONES` only). Move `_state_path()` under `EMPIRE_DATA_DIR`. Set `EMPIRE_PORTAL_INTERNAL_URL` to the family API, not `:3005`. | Port `test_whatsapp_filing.py` family cases already on #94 (`test_family_editions_do_not_read_repo_aliases`) |

Recommendation for Phase 0: **A first** (family already runs `whatsapp_cloud.py`). Port #94 filing only when brothers need job folders.

### Phase 0.3 — Spanish `/ayuda/whatsapp`

- New page + ayuda index link; inject `webhook_url` from `GET /api/v1/whatsapp/status` or credentials (masked).
- Tests: render copy contains “no la de Rafael”; no token/secret strings in HTML; amp vs maxine webhook host differs.

### Phase 0.4 — PR #80 merge (draft → ready) after 0.1–0.3

- Keep interview step; add `?paso=whatsapp`; persist `whatsapp_setup_status`.
- Confirm credential POST is allowlist-gated.
- Tests: already on #80; add edition isolation (amp file not readable when `EMPIRE_DATA_DIR` is maxine).

### Phase 0.5 — Workroom #94 stays Workroom

- Do not merge PR #94 into `feature/amp-edition` as a blob (it would pull chats-viewer + LuxeForge intake docs and the other WhatsApp engine).
- If filing is needed later, port **files**, not the branch.

### What Rafael does by hand (Dell / DNS / Meta Business — not this PR)

1. Keep Workroom on **8000** / `studio.empirebox.store` / `backend/.env`. Do not point amp/maxine units at that file.
2. Confirm `/data/amp` and `/data/maxine` exist and units load `/home/rg/empire-amp.env` and `/home/rg/empire-maxine.env`.
3. Publish **distinct** public webhook hosts (amp:8011 and maxine:8012). If using PR #80 names, create `wa-amp.empirebox.store` and `wa-maxine.empirebox.store` (or set `WHATSAPP_WEBHOOK_BASE_URL`). Document the URL each brother pastes — do not put tokens in the doc.
4. Put **only** Juan Diego’s number in Max-e `WHATSAPP_OWNER_NUMBERS` (`3174437313` / `+573174437313`). **Only** Camilo’s in Maxine (`3122842350` / `+573122842350`). Never Rafael’s Workroom number in those files.
5. Set each brother’s `AMP_OWNER_EMAIL` / allowlist to **his** login, not `empirebox2026@gmail.com`, unless he truly uses that mailbox.
6. Optional distinct `FOUNDER_PIN` / `AMP_JWT_SECRET` per env file.
7. Do not deploy this audit. Do not send WhatsApp to clients. Do not raise usage caps above 20%. Do not enable non-included models on family.

### What Juan Diego (Max-e) does by hand

1. Log in at `https://amp.empirebox.store/login` with **his** allowlisted email.
2. Open `/ayuda/whatsapp` (once built) or the entrevista WhatsApp step (once #80 lands).
3. Create **his** Meta developer app and **his** test number; verify **+57 317 443 7313**.
4. Paste IDs into **his** instance only. Confirm status card: channel ready, owner last4 matches, `documents_auto_send` false.
5. Send himself one test message to the Meta test number. Confirm Max-e answers in Spanish and does not create Workroom jobs or open Dahlia / Nehal.
6. Leave drafts unsent. Stay on MiniMax / 20%.

### What Camilo (Maxine) does by hand

Same as Juan Diego on `https://maxine.empirebox.store`, number **+57 312 284 2350**, data `/data/maxine`, port 8012. Confirm Argos/construction photos stay on **his** timeline, not Rafael’s jobs.

### Tests to add when code starts (mocks only)

| Test | Assert |
|------|--------|
| `test_family_whatsapp_state_stays_under_data_dir` | amp/maxine `_state_path()` is under tmp `EMPIRE_DATA_DIR`, never `~/empire-data` |
| `test_family_inbox_route_not_workroom_checkout` | family `INBOX_DIR` ≠ `~/empire-repo/backend/data/inbox` |
| `test_family_owner_numbers_ignore_other_brother` | amp owner list does not accept Camilo’s digits; maxine ignores Juan Diego |
| `test_family_ignores_rafael_phone_id` | inbound with Workroom `PHONE_NUMBER_ID` dropped |
| `test_family_aliases_do_not_resolve_dahlia` | after #94 port: `dahlia` / `9408 old courthouse` / `emma vita` unknown (already on #94) |
| `test_no_client_send_without_confirm` | existing `documents_auto_send is False`; send without confirm refused |
| `test_ayuda_whatsapp_has_no_secrets` | page HTML has no token/secret/PIN |

Do not run live Graph. Do not write `/data/amp` or `/data/maxine` in CI (`_live_data_guard.py`).

---

## Top findings (for the PR)

1. **PR #92 is on `feature/amp-edition`** (`bca37347`, 20:40 UTC 2026-10-10).
2. **PR #91 / #94 WhatsApp is not on this base.** Family today = `whatsapp_cloud.py`. `#94` is the other engine; `deploy/pr82-84-85` has only the channel half.
3. **Intended isolation is real** (separate data dirs, ports 8011/8012, env files, Meta IDs, 20% MiniMax, draft-only) **when systemd env is correct**.
4. **Highest leaks today:** checkout-hardcoded **inbox** (`routers/inbox.py`) and **legacy chats** (`api/v1/chats.py`) on Max-e’s shared `empire-repo` working directory; WhatsApp DB **fallback to `~/empire-data`**.
5. **Highest leaks after a naive #94 port:** repo `client_aliases.json` (already gated on #94), repo `business.json` allowlist, `whatsapp_channel_state.json` under `backend/data`, docs hub default `:3005`, shared `EMPIRE_TASK_DB`.
6. **PR #80** is the right brother-owned Meta tutorial but **unmerged**, interview-only, and missing `/ayuda/whatsapp` plus webhook DNS.
7. **Owner numbers are not in example env files.** Juan Diego `+57 317 443 7313` and Camilo `+57 312 284 2350` must be set by hand on the Dell; this audit does not write them into git secrets.

Nothing in this document is a deploy or a send.
