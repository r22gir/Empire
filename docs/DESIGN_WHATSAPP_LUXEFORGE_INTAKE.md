# Design: WhatsApp → LuxeForge central intake

Date: 2026-10-10  
Status: **design only** — Rafael approved the direction and the decisions in §0. No implementation in this PR.  
Base for this note: `deploy/pr82-84-85`, plus WhatsApp filing rules as fixed in PR #91.

WhatsApp is a capture channel. **Max is a general assistant**, not only Empire Workroom. Every inbound photo batch is filed into a **folder** (client job, or personal / insurance / store). A **LuxeForge job and a quote** happen only for **client work** and only when **Rafael asks for a quote**. Identify → measure-by-method → then at most one draft. Nothing is auto-sent to a client.

---

## 0. DECIDED (Rafael, 2026-10-10)

These replace the former open questions. Do not re-ask.

1. **Folders vs jobs.** Every photo batch gets a folder: a **client job** folder, or **personal / insurance / store**. Max stays a general assistant. A LuxeForge job **and** a quote happen **only for client work and only when Rafael asks for a quote**. Personal / insurance / store folders **never** create a LuxeForge job or a LeadForge lead.
2. **Measure gate is by METHOD, not a self-rated percent.** Grade is **HIGH** only if (a) Rafael typed the dimension, (b) a **calibrated known reference** is in frame, or (c) the dimension comes from a **3D / Polycam / plan file with confirmed units**. Anything else is **ESTIMATE**: show it labeled `estimated` and ask for **ONE named dimension** before any quote. A model score of **85 is only a secondary check on top, never sufficient alone**.
3. **Polycam / STL.** Rafael may **type sizes as a last resort**. Max **names the exact dimension** needed. The 3D files are **uploaded and linked** to the (client) job. They do not pass HIGH unless units are confirmed.
4. **Who is asked.** At first Max asks **only Rafael** for a missing dimension. Other people (Nelma, etc.) only **later, after review**.
5. **First named dimension (per item).** All values in **fractions, never decimals**. One named dimension at a time. Record whether each is **measured** (and **how**: typed / calibrated reference / 3D-or-plan with units) or **estimated**.
   - **Drapery:** finished panel length first (else floor-to-hardware, else floor-to-ceiling), then window/rod width, plus fullness/pleat style, lined or not.
   - **Roman shade:** width, drop, inside vs outside mount, fold style.
   - **Bench / banquette:** each section length, depth, seat height, back height and thickness, straight vs curved (radius/bow), return lengths for U/L.
   - **Seat cushion:** length × width × thickness, shape/corners.
   - **Channels / back:** channel width and total length; two labeled sizes: **wood/board cut** (true size, no add-ons) = foam cut, and a separate **fabric cut** (foam width + 2 to 3 in for stapling).
   - **Upholstery / other:** each area’s width × height.
6. **Ownership and send.** Records are owned by **Rafael’s founder/owner account**. Branding is **Empire Workroom** by default; **Nelma’s Workroom / Square only when he asks**. Max **never sends to clients**. Docs/invoices email **only** `empirebox2026@gmail.com`.
7. **Deposit** default **50%**, editable per quote.
8. **LeadForge lead** only on **conversion / when a quote is asked**, **not** in phase 0. Never for personal / insurance / store.
9. **Numbers.** **LF job number at LuxeForge job creation** (client work + Rafael asked for a quote). **EST number only after the measure gate passes** and that quote ask is in effect.
10. **Pricing columns.**
    - **Upholstery only:** sq ft × price per sq ft, grouped by area. Columns: Description, Qty, Unit, Sq ft per item, Price per sq ft, Total, subtotal per area, grand total, deposit, balance.
    - **Drapery:** priced **per width** (e.g. re-line with bump $150/width, without bump $125/width, lining $10.50/yd, napped $12.50/yd) **plus labor/hardware lines**. **Never** default drapery to sq ft.

### Hard rules (still in force)

1. **No estimate from photos unless explicitly asked** (PR #91): quote words must be in **this photo’s caption / same message**. Nearby “send me a quote for Emma” does not mint drafts. “Rafael asks” here means that same-message / explicit ask, not a leftover nearby text.
2. **At most one draft per WhatsApp photo batch.**
3. **Family editions stay isolated** (`EMPIRE_DATA_DIR` / `WHATSAPP_JOBS_ROOT`).
4. **Never lose a file.** Persist on the Max edition first; enqueue if LuxeForge is down; retry. Dedup Meta `wa_message_id` before ingest.
5. **Never auto-create a quote without the measure gate** (HIGH by method, or Rafael’s typed dimension). ESTIMATE is shown labeled `estimated` and is not enough to mint an EST.
6. **No new public Luxe endpoints.** PR #71 / `docs/LUXE_API_LOCK.md` (repo cites PR 61 for the same gate in `luxe_public_edge.py`). WhatsApp → LuxeForge is **authenticated server-to-server on the private cash path**.

---

## 1. Current-state audit

Today WhatsApp and LuxeForge are **two production intake paths**. They both can create a `quotes_v2` draft. They do not share a job id. WhatsApp filing already parks unnamed photos and can file into a client slug; it does **not** yet have personal / insurance / store as first-class folders, and it can still jump to a photo quote without the method gate.

### What to reuse

| Piece | Path | Reuse how |
| --- | --- | --- |
| WhatsApp webhook, allowlist, 24h window, `_seen` dedup | `backend/app/services/max/whatsapp_channel.py` | Keep as the only Meta ingress. After persist/batch, file the folder; call LuxeForge **only** on client + quote ask. |
| Photo batch, job ask, SQLite TTL | `backend/app/services/max/whatsapp_log.py` | Keep file-only default, one ask, `asked==1` gate, expiry on load. Extend folder resolve to personal / insurance / store. |
| Quote gate (caption only, one draft/batch) | `wants_photo_quote`, `mark_photo_batch_quoted`; `docs/WHATSAPP_CHANNEL.md` | Do not regress PR #91. Still not enough: measure gate must pass before EST. |
| Job name resolve | `backend/app/services/max/doc_lookup.py`, `backend/app/config/client_aliases.json` | Unique client name → client folder. Personal / insurance / store are **not** aliases of a client. |
| LuxeForge project row | `backend/app/routers/intake_auth.py` (`intake_projects`) | **Hub for client+quote-ask jobs only.** Owner = Rafael founder account. |
| Designer submit → Workroom | `backend/app/services/luxeforge_intake_handoff.py` | Reuse attach-files. **Do not** `create_quote` until HIGH / typed dimension. Lead only when quote is asked. |
| Shared lead/CRM brief | `backend/app/services/workroom_lead_intake.py`, `POST /api/v1/leadforge/intake` | Call **only** on conversion / quote ask, never phase 0, never personal/insurance/store. |
| Photo item ID | `backend/app/services/quote_engine/item_analyzer.py`, `backend/app/routers/vision.py` | Identify items. A vision score of 85 is **secondary**, never HIGH by itself. |
| Photo → quote lines | `backend/app/services/quote_engine/photo_quote_lines.py` | After gate. Split **drapery (per width)** vs **upholstery (sq ft)**. |
| Calibrate / pixel → inch | `backend/app/routers/luxeforge_measurements.py`, `backend/app/models/luxeforge_measurement.py` | Method (b): calibrated known reference in frame → HIGH. |
| Fractions (never shop decimals) | `backend/app/services/pricing/dimensions.py` (`format_inches_plain`) | All dimensions: `26 3/4"`, not `26.75`. |
| Deposit / balance | `backend/app/services/quote_service.py` (`deposit_percent` default 50) | Default 50%, editable per quote. |
| Area-grouped financials | `quote_service._area_grouped_financials` | **Upholstery only** for sq ft columns. |
| Empire Workroom branding | `backend/app/services/quote_pdf_service.py` | Default. Nelma’s Workroom / Square only when Rafael asks. |
| Unified job board | `backend/app/routers/jobs_unified.py` | Link a board row when an LF job is created (client + quote ask), not for personal folders. |
| Job folders | `$EMPIRE_DATA_DIR/jobs/<slug>/…` plus new personal / insurance / store roots | Every batch files somewhere. |
| Public Luxe lock | `backend/app/security/luxe_public_edge.py`, `docs/LUXE_API_LOCK.md` | Internal writer **off** the public allowlist. |
| Founder PIN / founder JWT | `backend/app/accounts/founder.py` | Record owner is Rafael’s founder account. |
| 3D upload extract | `backend/app/routers/photos.py` | Store and **link** STL/Polycam to the LF job. HIGH only with confirmed units. |
| WhatsApp Chats / LuxeForge admin | Command Center screens | Chats show folder + optional `intake_code`. Admin only for LF jobs. |

### What is missing

| Gap | Why it matters |
| --- | --- |
| No first-class personal / insurance / store folders | Every batch must file; those kinds must not create LF jobs or leads. |
| WhatsApp never writes `intake_projects` | Client+quote-ask still has no shared LF id for Max / board. |
| No internal S2S intake API + service token | Required for LF job create; must stay off public luxe. |
| Measure gate is not method-based | Today photo_quote can mint EST from vision items with no typed / calibrated / unit-confirmed source. |
| `luxeforge_measurements` not bound to intake | Calibrate exists but is not the gate. |
| Polycam / STL / PDF units | Files store; units often unknown → ESTIMATE until Rafael types or units are confirmed. |
| Drapery vs upholstery line schemas | Sq ft columns must not be the drapery default. Drapery width rates (bump / no bump / lining yd) are not a single intake schema. |
| Per-item first-dimension script | No ordered ask list (panel length, roman width, section length, …). |
| No durable retry queue | LF down must not lose client+quote-ask writes; folder persist already comes first. |

### Parallel sinks

1. **Folders** (always) — client slug **or** personal / insurance / store  
2. `intake_projects` — LuxeForge, **only** client + quote ask  
3. `quotes_v2` — EST **only** after method gate  
4. `jobs_unified` — board card for LF jobs  
5. `lf_leads` — **only** on conversion / quote ask  
6. WhatsApp SQLite — channel log  

---

## 2. Data model

### Folder (always, every batch)

| Kind | Where | Creates LF job? | Creates lead? | Creates EST? |
| --- | --- | --- | --- | --- |
| `client` | `$EMPIRE_DATA_DIR/jobs/<client-slug>/` | Only if Rafael asks for a quote | Only if quote asked / conversion | Only after method gate |
| `personal` | edition `personal/` (exact slug TBD) | No | No | No |
| `insurance` | edition `insurance/` | No | No | No |
| `store` | edition `store/` | No | No | No |

Unknown client name → ask once (PR #91) or file personal/insurance/store if Rafael says so. Do not guess a client.

### LuxeForge job (`intake_projects`, client + quote ask only)

| Field | Purpose |
| --- | --- |
| `id` | UUID (`intake_id`). Max, board, folder, chat log. |
| `intake_code` | **LF-YYYY-NNN assigned at job creation** (this moment). |
| `owner_account` | Rafael founder/owner. |
| `edition` | Family isolation. |
| `source` | `whatsapp` \| `designer_portal` \| `leadforge`. |
| `folder_kind` | Always `client` on this row. |
| `status` | `received` → `identified` → `measuring` → `measured` → `quote_draft`. Never `sent` from automation. |
| `job_slug` | Client folder. |
| `job_id` | `jobs_unified` id when the LF job exists. |
| `quote_id` / `quote_number` | **Empty until** method gate HIGH (or typed sizes) **and** quote ask. Then EST. |
| `lead_id` | Set only on conversion / quote ask. |
| `wa_id`, `wa_batch_id` | Channel keys. |
| `branding` | Default `empire_workroom`. `nelma_workroom` / Square only when Rafael asks. |
| `business` | Default `workroom`. |

### Attachments (`intake_attachments` on an LF job; folder files always)

Same as before (`kind`, `sha256`, `local_path`, `wa_message_id`, 3D linked). 3D/Polycam/PDF are **uploaded and linked** even when grade is ESTIMATE.

### Measurements (`intake_measurements`)

| Field | Purpose |
| --- | --- |
| `item_type` | `drapery` \| `roman` \| `banquette` \| `cushion` \| `channel` \| `upholstery` \| … |
| `name` | The **one named dimension** (e.g. `finished_panel_length`, `roman_width`, `section_length`, `wood_board_cut`, `fabric_cut`). |
| `value_sixteenths` / display | Fractions via `format_inches_plain` only. |
| `grade` | `HIGH` \| `ESTIMATE`. |
| `method` | `rafael_typed` \| `calibrated_reference` \| `3d_or_plan_confirmed_units` \| `vision_only` \| `uncalibrated_photo`. |
| `how` | Human note of how it was measured (for HIGH) or `estimated`. |
| `vision_score` | Optional 0–100. **85 is secondary.** Never sets HIGH alone. |
| `gate_pass` | True only if `grade=HIGH` (method a/b/c). ESTIMATE + ask outstanding → false. |

HIGH iff method is (a), (b), or (c). Vision-only, no reference, unconfirmed-unit STL → ESTIMATE, labeled `estimated`, ask one named dimension.

### Quote drafts

Create **one** `quotes_v2` draft per batch, only when: client folder + Rafael asked + every priced item `gate_pass` + not already quoted.

**Upholstery** (grouped by area): Description, Qty, Unit, Sq ft per item, Price per sq ft, Total, subtotal per area, grand total, deposit (50% default, editable), balance.

**Drapery** (never sq ft by default): per-width lines (re-line with bump $150/width, without bump $125/width) + lining $10.50/yd, napped $12.50/yd + labor/hardware. Then grand total, deposit, balance.

Branding: Empire Workroom unless Rafael asks for Nelma’s Workroom / Square.

### Links

```
folder (always)
  client slug ──┬── intake_id (only if quote asked)
                ├── LF-YYYY-NNN
                ├── jobs_unified.job_id
                ├── quotes_v2 EST-…     (after method gate)
                ├── lf_leads.id         (quote ask / conversion)
                └── wa attachments + 3D
personal | insurance | store ── files + wa log only
```

---

## 3. Auth (Max backend → LuxeForge)

Unchanged intent: **no public ingest.** Private

```
POST /api/v1/internal/luxeforge/jobs
POST /api/v1/internal/luxeforge/jobs/{id}/attachments
POST /api/v1/internal/luxeforge/jobs/{id}/measurements
GET  /api/v1/internal/luxeforge/jobs/{id}
```

`/api/v1/internal/` denied on `luxe.empirebox.store` / `test-luxe`. Service token `LUXEFORGE_INTAKE_SERVICE_TOKEN` (+ `TOKEN_PREVIOUS`), scopes `intake:write|attach|measure|read`, `hmac.compare_digest`, never log. Owner of created rows is Rafael’s founder account, not a synthetic WhatsApp user.

If the token is missing, folder persist still happens; LF create is queued.

---

## 4. Flow

```mermaid
sequenceDiagram
    participant Meta
    participant WA as whatsapp_channel
    participant Disk as folder (client or personal/insurance/store)
    participant Q as intake_retry_queue
    participant LF as LuxeForge job
    participant Board as jobs_unified
    participant Max
    participant Quote as quotes_v2

    Meta->>WA: webhook (photo/PDF/STL + text)
    WA->>WA: _seen(wa_message_id)? drop if yes
    WA->>Disk: persist + file folder (never lose)
    Note over Disk: personal/insurance/store: stop here (no job, no lead)
    alt client work AND Rafael asked for a quote
        WA->>LF: S2S create job (LF number now)
        LF->>Board: job_id
        Note over LF: 3D/Polycam uploaded and linked
        Note over Max: identify; grade HIGH only by method
        alt grade ESTIMATE
            Max->>Max: ask Rafael ONE named dimension
            Max->>LF: rafael_typed → HIGH
        end
        alt method gate HIGH AND not already quoted
            LF->>Quote: ONE EST draft (drapery per width / upholstery sq ft)
            Quote-->>Max: draft for Rafael (not sent)
        end
    else client file-only or Max chat
        Max-->>Max: general assistant / file only
    end
    alt LuxeForge down on client+quote-ask
        WA->>Q: enqueue; retry; file already on disk
    end
```

Max asks **Rafael only** for the missing named dimension (see §0.5). Not Nelma, not the album sender, until a later reviewed phase.

---

## 5. Failure behavior

| Case | Behavior |
| --- | --- |
| **ESTIMATE (not HIGH)** | Show value labeled `estimated`. Ask Rafael **one named** dimension for that item (script in §0.5). No EST. |
| **Vision score 85, no method** | Still ESTIMATE. 85 never passes the gate alone. |
| **Unknown / ambiguous client** | PR #91: park or ask once. Do not invent a client. Personal/insurance/store if Rafael files there. `hello` / schedule → Max chat. |
| **Personal / insurance / store** | Folder only. No LF job, no lead, no EST, even if caption says “quote”. |
| **Duplicate Meta delivery** | `_seen` before persist; upsert `(edition, wa_message_id)` / sha256. |
| **LuxeForge down** | Folder already written. Queue LF create only when client+quote-ask. Retry; never drop the file. |
| **Polycam/STL, units unknown** | Link files to the job. Grade ESTIMATE. Max names the exact dimension; Rafael may type sizes last resort. |
| **Quote path** | Never send to a client. Email of docs **only** `empirebox2026@gmail.com`. |
| **Caption did not ask** | Client folder only. No LF job, no lead, no EST. |
| **Second photo in a quoted batch** | File + attach only. |

### 5.1 Polycam / STL / PDF-plan gaps

Unchanged technically: we can store files; we cannot yet confirm units or extract openings. **DECIDED:** that is ESTIMATE until Rafael types or units are confirmed; files still upload and link.

---

## 6. Phases (each independently shippable)

### Phase 0 — Smallest useful step (folders only)

Persist every batch into a **client or personal/insurance/store folder**. No LuxeForge job, no lead, no EST. Dedup `wamid`. Max remains general chat.

**Done when:** mocked 3 photos + “Maggie” file under `maggie-frolich`; 3 photos + “personal” (or equivalent) file under personal and create **zero** `intake_projects` / `lf_leads` / `quotes_v2`; duplicate `wamid` is a no-op.

### Phase 1 — LuxeForge job when Rafael asks (client only)

On client folder **and** explicit quote ask: S2S-create `intake_projects` with **LF-YYYY-NNN**, owner = Rafael, link 3D/photos, `jobs_unified` card. Still **no EST**. Optional LeadForge lead **now** (quote asked). Queue if LF is down.

**Done when:** quote-caption on Maggie → one LF row + folder + board id; same photos in `store/` → still no LF row; personal batch never gets a lead.

### Phase 2 — Method measure gate

Grade HIGH only by method (a)(b)(c). ESTIMATE labeled `estimated`; Max asks Rafael **one named** dimension per §0.5. Vision 85 without a method does not pass. No `create_quote`.

**Done when:** uncalibrated photo → ask `finished_panel_length` (drapery) or the matching first name; typed `54 1/2"` → HIGH `rafael_typed`; 85-only fixture stays ESTIMATE.

### Phase 3 — One EST after the gate

If HIGH + quote ask + not already quoted: one draft. **Upholstery** = area sq ft columns. **Drapery** = per-width + lining/labor/hardware, **not** sq ft. Deposit 50% editable. Empire Workroom default. Not sent.

**Done when:** PR #91 tests still pass; drapery fixture has no “sq ft per item” default; measure-fail blocks EST.

### Phase 4 — 3D / PDF unit extractors (optional)

Confirm units on Polycam/STL/plan → method (c) HIGH. Until then: link files, Rafael types last resort.

---

## 7. Tests per phase (mocks only)

No live Graph, no live `EMPIRE_DATA_DIR`, stub `MAX_CLIENT_ALIASES_PATH`. Reuse `tests/_live_data_guard.py`.

| Phase | Tests |
| --- | --- |
| 0 | File to client folder; file to personal/insurance/store with **no** intake/lead/quote rows; duplicate `wamid`; family edition isolation. |
| 1 | Client + quote ask → one LF-YYYY-NNN, owner founder; store/personal + “quote” caption → **no** LF job; S2S 401 without token; 403 on `Host: luxe.empirebox.store`; LF 503 → queue, file kept; lead created only on quote ask, not on file-only. |
| 2 | `rafael_typed` / calibrated reference / unit-confirmed 3D → HIGH; vision 85 only → ESTIMATE + one named ask to Rafael (not Nelma); fractions only; drapery first ask is finished panel length (else fallbacks). |
| 3 | Caption + HIGH → **one** EST; nearby quote text + 7 photos → 0 EST; drapery lines are per-width not sq ft; upholstery has sq ft columns; deposit 50; `create_quote` not called on ESTIMATE. |
| 4 | STL/Polycam linked; unconfirmed units → ESTIMATE; Rafael-typed size → HIGH. |

---

## 8. Open questions

The ten questions from the first draft are **DECIDED** (§0). Left for implementation, not product direction:

- Exact edition slugs/paths for `personal` / `insurance` / `store` (names only; behavior is decided).
- How a vision “85” is computed when used as the **secondary** check (never as the gate).
- The later review step that allows Max to ask Nelma (process only).

---

## 9. Out of scope / do not do

- Merge or deploy this design.  
- New routes on `luxe.empirebox.store`.  
- Auto-send quotes, invoices, or WhatsApp documents to clients.  
- Email docs anywhere except `empirebox2026@gmail.com`.  
- LuxeForge job or lead from personal / insurance / store.  
- EST from ESTIMATE or from a vision score alone.  
- Default drapery pricing to sq ft.  
- Delete or reuse EST-2026-300..306.  
- Shared jobs tree across family editions.  
- Multiple inbound WhatsApp workers on one edition DB.  

---

## Pointers

- WhatsApp spec: `docs/WHATSAPP_CHANNEL.md`  
- Public lock: `docs/LUXE_API_LOCK.md`  
- Designer → Workroom: `docs/WORKROOM_LEAD_INTAKE.md`, `luxeforge_intake_handoff.py`  
- Quote fractions: `backend/tests/test_measurement_fractions_rule.py`  
