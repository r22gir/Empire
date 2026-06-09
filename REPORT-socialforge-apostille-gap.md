# SocialForge Apostille Gap Report (Phase 3A)

**Status:** Read-only audit. No code changes, no branches.
**Date:** 2026-06-08
**Author:** Empire Completion Coordinator
**Scope:** `backend/app/routers/socialforge.py`, front-end `channels/` and `archiveforge/` dirs, MAX cross-references.

---

## 1. What exists today

### 1.1 The SocialForge backend (21 routes)

| Method | Path | Purpose |
|---|---|---|
| GET | `/socialforge/posts` | List all posts |
| POST | `/socialforge/posts` | Create a post |
| GET | `/socialforge/posts/{post_id}` | Get one post |
| PUT | `/socialforge/posts/{post_id}` | Update a post |
| DELETE | `/socialforge/posts/{post_id}` | Delete a post |
| GET | `/socialforge/campaigns` | List campaigns |
| POST | `/socialforge/campaigns` | Create a campaign |
| DELETE | `/socialforge/campaigns/{camp_id}` | Delete a campaign |
| POST | `/socialforge/generate` | AI content generation |
| POST | `/socialforge/post/instagram` | Publish to Instagram via Graph API |
| POST | `/socialforge/post/facebook` | Publish to Facebook Page via Graph API |
| GET | `/socialforge/connected-accounts` | List connected accounts |
| GET | `/socialforge/dashboard` | Dashboard summary |
| GET | `/socialforge/calendar` | Content calendar view |
| GET | `/socialforge/profile` | Business profile |
| PUT | `/socialforge/profile` | Update business profile |
| GET | `/socialforge/accounts` | List accounts |
| PUT | `/socialforge/accounts/{account_id}` | Update account |
| POST | `/socialforge/accounts/sync` | Sync an account |
| POST | `/socialforge/accounts/ai-guide` | AI guidance for platform account setup |
| (plus 1 more not enumerated) | | |

Storage is local JSON files in `~/empire-repo/backend/data/socialforge/{posts,campaigns}/`.

### 1.2 AI content generation

`POST /socialforge/generate` exists. Uses MAX's `ai_router` to produce post copy. Per-platform style guidance is hardcoded in the router:

```
instagram: "Use emojis, line breaks for readability, 20-25 hashtags, include a CTA"
facebook: "More conversational, shorter hashtag list (5-8), include a link or question"
linkedin: "Professional tone, industry insights, 3-5 hashtags, thought leadership"
```

(This is a stub of an i18n / style-engine — the guidance is in code, not in a config file. Adding a new platform or updating guidance requires a code change.)

### 1.3 Publishing

**Two publish endpoints exist:** `POST /socialforge/post/instagram` and `POST /socialforge/post/facebook`. Both call out to the Graph API. The status field on a post is `draft | scheduled | posted | failed`. There is no actual scheduling daemon — the `scheduled_for` field is stored but the code does not have a background worker that picks up due posts and publishes them. (This is consistent with the Founder's "no cron / no daemon" rule for this sprint.)

### 1.4 Front-end presence

There is **no `socialforge` top-level page** in `/home/rg/empire-repo-main/empire-command-center/app/`. There is a `channels/` directory (checked — it contains some shared UI primitives). There is no SocialForge-specific UI today. The 21 SocialForge routes are invisible to the founder team without manually constructing API calls or using a CLI.

### 1.5 Cross-references in MAX

`backend/app/services/max/telegram_bot.py`, `token_tracker.py`, `ecosystem_catalog.py`, `empire_module_knowledge.py` mention SocialForge. None of these actively publish SocialForge content; they only reference the module's existence.

### 1.6 Bilingual support

**No** native Spanish/English language support in the SocialForge backend. The `business_name` and `tagline` can be set to Spanish, but the platform-style guidance and the AI generation prompts are English-only.

### 1.7 Apostille hooks

**None.** The SocialForge router has zero references to apostille or apostapp. There is no link between a SocialForge campaign and an apostille landing page.

---

## 2. The 30-Day Apostille Content Calendar (draft)

The Founder said no auto-publishing, no scheduling without review. The calendar below is a **draft** for the Founder's review. Each entry includes the channel, language, topic, and CTA target.

| Day | Language | Channel | Topic | CTA |
|---|---|---|---|---|
| 1 | EN | Instagram | "Did you know? Documents signed in DC/MD/VA often need an apostille for international use." | Link to landing page `/apostille` |
| 2 | ES | Instagram | "¿Sabías? Muchos documentos firmados en DC/MD/VA necesitan apostilla para uso internacional." | Link to landing page `/apostille` (Spanish) |
| 3 | EN | Facebook | "Colombian documents and the apostille: a 3-step process." | Link to landing page `/apostille` |
| 4 | ES | Facebook | "Documentos colombianos y la apostilla: proceso de 3 pasos." | Link to landing page `/apostille` (Spanish) |
| 5 | EN | LinkedIn | "How small businesses in the DMV area use apostille services for international contracts." | Link to landing page `/apostille` |
| 6 | EN | Instagram | "School transcripts and apostille: what students need to know." | Link to landing page `/apostille` |
| 7 | ES | Instagram | "Transcripciones escolares y apostilla: lo que los estudiantes deben saber." | Link to landing page `/apostille` (Spanish) |
| 8 | EN | Facebook | "The difference between apostille and notarization (not legal advice)." | Link to landing page `/apostille` |
| 9 | ES | Facebook | "La diferencia entre apostilla y notarización (no es consejo legal)." | Link to landing page `/apostille` (Spanish) |
| 10 | EN | Instagram | "5 documents that commonly need an apostille." | Link to landing page `/apostille` |
| 11 | EN | LinkedIn | "How a local apostille service compares to mailing documents overseas." | Link to landing page `/apostille` |
| 12 | ES | Instagram | "5 documentos que comúnmente necesitan apostilla." | Link to landing page `/apostille` (Spanish) |
| 13 | EN | Facebook | "Pickup and dropoff convenience: how Empire Workroom handles your documents." | Link to landing page `/apostille` |
| 14 | ES | Facebook | "Recogida y entrega conveniente: cómo Empire Workroom maneja tus documentos." | Link to landing page `/apostille` (Spanish) |
| 15 | EN | Instagram | "Urgent service: same-day apostille for time-sensitive documents." | Link to landing page `/apostille` |
| 16 | EN | LinkedIn | "What an apostille actually does (and doesn't do)." | Link to landing page `/apostille` |
| 17 | ES | Instagram | "Servicio urgente: apostilla el mismo día para documentos urgentes." | Link to landing page `/apostille` (Spanish) |
| 18 | EN | Facebook | "3 things to bring to your apostille appointment." | Link to landing page `/apostille` |
| 19 | EN | Instagram | "Behind the scenes: what happens after you submit your documents." | Link to landing page `/apostille` |
| 20 | ES | Instagram | "Detrás de cámaras: qué pasa después de enviar tus documentos." | Link to landing page `/apostille` (Spanish) |
| 21 | EN | Facebook | "Why DMV-area professionals choose a local apostille service." | Link to landing page `/apostille` |
| 22 | ES | Facebook | "Por qué los profesionales del área DMV eligen un servicio local de apostillas." | Link to landing page `/apostille` (Spanish) |
| 23 | EN | LinkedIn | "Apostille vs. consular legalization: which do you need?" | Link to landing page `/apostille` |
| 24 | EN | Instagram | "Real customer story: how a DMV professional got their documents apostilled in 48 hours." | Link to landing page `/apostille` |
| 25 | ES | Instagram | "Historia real: cómo un profesional del DMV apostilló sus documentos en 48 horas." | Link to landing page `/apostille` (Spanish) |
| 26 | EN | Facebook | "Common mistakes people make when getting documents apostilled (and how to avoid them)." | Link to landing page `/apostille` |
| 27 | ES | Facebook | "Errores comunes al apostillar documentos (y cómo evitarlos)." | Link to landing page `/apostille` (Spanish) |
| 28 | EN | Instagram | "The 5-minute pre-check: do your documents even need an apostille?" | Link to landing page `/apostille` |
| 29 | EN | LinkedIn | "Empire Workroom's commitment to the DMV's Spanish-speaking business community." | Link to landing page `/apostille` |
| 30 | ES | Instagram | "El chequeo de 5 minutos: ¿tus documentos siquiera necesitan apostilla?" | Link to landing page `/apostille` (Spanish) |

**Disclaimer:** every post includes the "not legal advice" disclaimer in the body or in the bio link, in both languages.

---

## 3. Spanish / English Post Templates (reusable)

### 3.1 Template: Educational explainer (5 posts in the calendar use this)

**EN:**
```
Did you know? [TOPIC_FACT].
Here's a 3-step breakdown:
1. [STEP_1]
2. [STEP_2]
3. [STEP_3]
Not legal advice — see [BIO_LINK] for details.
#apostille #[CITY] #[LANGUAGE]
```

**ES:**
```
¿Sabías? [TOPIC_FACT].
Aquí un desglose de 3 pasos:
1. [STEP_1]
2. [STEP_2]
3. [STEP_3]
No es consejo legal — consulta [BIO_LINK] para más detalles.
#apostilla #[CIUDAD] #[IDIOMA]
```

### 3.2 Template: Customer story (3 posts in the calendar use this)

**EN:**
```
A [CUSTOMER_TYPE] came to us with [DOCUMENT_TYPE].
We [ACTION_TAKEN] in [TIMEFRAME].
Now their documents are ready for [DESTINATION].
Want the same? [BIO_LINK].
#apostille #[CITY]
```

**ES:**
```
Un(a) [CUSTOMER_TYPE] vino a nosotros con [DOCUMENT_TYPE].
[ACTION_TAKEN_PAST_TENSE] en [TIMEFRAME].
Ahora sus documentos están listos para [DESTINATION].
¿Lo quieres? [BIO_LINK].
#apostilla #[CIUDAD]
```

### 3.3 Template: Urgency / speed (2 posts in the calendar use this)

**EN:**
```
Time-sensitive documents?
We offer [SERVICE_LEVEL] apostille service — [TIMEFRAME] turnaround.
Same-day, next-day, or standard.
[CTA]: [BIO_LINK]
Not legal advice.
```

**ES:**
```
¿Documentos urgentes?
Ofrecemos servicio de apostilla [SERVICE_LEVEL] — entrega en [TIMEFRAME].
Mismo día, día siguiente, o estándar.
[CTA]: [BIO_LINK]
No es consejo legal.
```

### 3.4 Template: Trust / process (4 posts in the calendar use this)

**EN:**
```
Here's what happens after you [ACTION]:
1. [STEP_1]
2. [STEP_2]
3. [STEP_3]
We handle the government paperwork so you don't have to.
[CTA]: [BIO_LINK]
```

**ES:**
```
Esto es lo que pasa después de [ACTION]:
1. [STEP_1]
2. [STEP_2]
3. [STEP_3]
Nosotros manejamos el papeleo del gobierno para que tú no tengas que hacerlo.
[CTA]: [BIO_LINK]
```

### 3.5 Template: Local SEO / DMV (5 posts in the calendar use this)

**EN:**
```
[NEIGHBORHOOD] [ACTION_VERB] their documents with us.
[OFFER_LINE] — fast, local, Spanish/English.
[CTA]: [BIO_LINK]
#apostille #[CITY] #[NEIGHBORHOOD]
```

**ES:**
```
[NEIGHBORHOOD] [ACTION_VERB_PAST] sus documentos con nosotros.
[OFFER_LINE] — rápido, local, español/inglés.
[CTA]: [BIO_LINK]
#apostilla #[CIUDAD] #[NEIGHBORHOOD]
```

---

## 4. Short Video / Image Prompt Set

### 4.1 Image prompts (10)

1. **Document close-up on a desk, soft natural light, shallow depth of field** — for educational explainer posts. Hero subject: an open document with a stamp visible. Mood: trustworthy, calm.
2. **Hands holding a stack of documents, top-down view on a wooden desk** — for "bring your documents" posts. Mood: organized, professional.
3. **A pen signing a document, focus on the signature, soft office background** — for "what we do" posts. Mood: precise, careful.
4. **Two women (one in a DC professional outfit, one in casual Spanish-speaking attire) at a desk, smiling, with documents between them** — for trust / community posts. Mood: warm, multilingual, accessible.
5. **A coffee shop scene in Columbia Heights or Adams Morgan, with documents on the table** — for DMV-local posts. Mood: local, real, candid.
6. **A close-up of an apostille certificate with the gold seal visible** — for the "what does an apostille look like" educational post. Mood: official, credible.
7. **A smartphone showing the landing page (`/apostille`) with a CTA button highlighted** — for CTA-focused posts. Mood: clear, actionable.
8. **A person in business casual at a government building entrance, holding a folder** — for "what happens at the Secretary of State" posts. Mood: purposeful, clear.
9. **A flat-lay of documents, stamps, a translator's notebook, and a Spanish-English dictionary** — for translation posts. Mood: bilingual, thorough.
10. **An overhead shot of a calendar with dates circled in red, with a "same-day apostille" sticky note** — for urgency posts. Mood: time-aware, urgent but not panicked.

Style notes for all images: warm but not over-saturated; subjects look real (not stock-photo-y); Empire Workroom branding visible only when it makes sense (e.g. the landing-page shot, the certificate close-up).

### 4.2 Short video scripts (3–5, 30 seconds each)

**Video 1: "3 documents that need an apostille" (EN, 30s)**
- 0–5s: Woman at desk, "Hi, I'm [founder name] from Empire Workroom."
- 5–15s: Three documents appear on screen with text overlays: "Diploma", "Birth certificate", "Business contract".
- 15–25s: Each document gets a checkmark.
- 25–30s: Text: "Need one? Tap the link in bio. Not legal advice."

**Video 2: "Apostilla en 3 pasos" (ES, 30s)**
- 0–5s: Mujer en escritorio, "Hola, soy [nombre] de Empire Workroom."
- 5–15s: Tres documentos aparecen con texto: "Diploma", "Acta de nacimiento", "Contrato comercial".
- 15–25s: Cada documento recibe un check.
- 25–30s: Texto: "¿Necesitas una? Toca el enlace en bio. No es consejo legal."

**Video 3: "Same-day apostille — when you need it fast" (EN, 30s)**
- 0–5s: Quick cuts: phone ringing, email notification, calendar date highlighted.
- 5–15s: Founder walking with a folder.
- 15–25s: Founder at a desk, signing the apostille certificate, hand-off.
- 25–30s: Text: "Same-day apostille. Link in bio. Not legal advice."

**Video 4: "Lo que pasa después de enviar tus documentos" (ES, 30s)**
- 0–10s: Persona entregando documentos, "Recibimos tus documentos."
- 10–20s: Caracteres en pantalla: "Verificamos → Apostillamos → Notificamos".
- 20–30s: Texto: "Te avisamos cuando estén listos. Enlace en bio. No es consejo legal."

**Video 5: "DMV local apostille — why local matters" (EN, 30s)**
- 0–10s: Founder walking through a DMV neighborhood, coffee shop visible.
- 10–20s: Founder at a desk, opening a folder.
- 20–30s: Text: "Local. Fast. Spanish + English. Link in bio. Not legal advice."

---

## 5. Landing Page CTA Requirements

Every SocialForge post links to the new Apostille landing page. The landing page must have:

- A clear primary CTA: **"Get a Quote"** (button, top-fold)
- A secondary CTA: **"Hablar en español"** (link, top-right)
- A trust badge: **"Local DMV · Spanish + English · Not legal advice"** (small, in the footer)
- A 3-step "How it works" section
- An FAQ section (4–6 questions, bilingual)
- A "Not legal advice" disclaimer in the footer
- A contact form: name, email, phone, document type, destination country, urgency, message
- A clear "What we don't do" section (we don't provide legal advice, we don't represent clients in court, we don't prepare legal documents — we only apostille and translate)

---

## 6. SocialForge Integration Gap Report

### 6.1 What exists

- 21 backend API routes
- AI content generation endpoint
- Per-platform style guidance (hardcoded in router)
- Posts/campaigns in local JSON storage
- Two publish endpoints (Instagram Graph, Facebook Graph)
- Status field: `draft | scheduled | posted | failed`
- Business profile storage

### 6.2 What is missing

| Gap | Severity | v1 need? |
|---|---|---|
| No front-end UI for SocialForge | **P0** | YES — Founder cannot use it without manual API calls |
| No actual scheduler daemon (scheduled posts are stored, not published) | P2 | NO for v1 (Founder reviews and publishes manually) |
| No bilingual support (English-only AI prompts) | **P0** | YES — Apostille is a Spanish-speaking market |
| No apostille-specific content templates | **P0** | YES — Apostille themes are different from generic social |
| No campaign-level "link to apostille landing page" config | **P1** | YES — every post should link to `/apostille` |
| No local SEO hooks (location, neighborhood, language) | P1 | YES — DMV-local positioning |
| No tracking/referral tags (UTM parameters, link tracking) | P1 | YES — Founder needs to know which posts drive leads |
| No image generation endpoint | P2 | NO — Founder can generate images separately, then upload |
| No image storage / hosting | P2 | NO — Founder can use external image URLs |
| No auto-publishing (must be manual click-to-publish) | n/a | BY DESIGN — Founder's rule |
| No analytics / engagement tracking | P2 | NO for v1 |
| No link-in-bio management | P2 | NO for v1 |
| No hashtag suggestion engine (uses the 5 hardcoded ones) | P2 | NO for v1 |

### 6.3 What changes are needed for the Apostille campaign

1. **Add bilingual support** to the AI generation endpoint — accept a `language` field (`"en"` or `"es"`), pass to the AI router, and use language-specific system prompts.
2. **Add a content library** at `backend/app/services/socialforge/apostille_campaigns.py` — a module that stores the 30-day calendar + the templates + the image prompts + the video scripts. Read-only storage initially; the founder uses them as a reference.
3. **Add a campaign metadata field** to `POST /socialforge/campaigns` — `target_landing_page` (string), so every post in the campaign auto-fills its CTA link.
4. **Add a "marketing copy library"** for the apostille themes (the 9 themes from the 30-day calendar: geographic, Colombian, bilingual, business, school, etc.) — these are reference strings, not auto-published.
5. **Add a "publish confirmation" guard** — a future check before any post is auto-published, so Founder can review first. (This is the "no auto-publishing" rule.)

---

## 7. Branch / Worktree Proposal

- **Branch:** `feature/socialforge-apostille-campaigns`
- **Worktree:** `/home/rg/empire-repo-main-socialforge-apostille` (new, from `main` HEAD `2867978`)
- **Files to touch:**
  - New module: `backend/app/services/socialforge/apostille_campaigns.py` (content library, read-only)
  - Modify: `backend/app/routers/socialforge.py` (add `language` field, add `target_landing_page` to campaigns)
  - Modify: `backend/app/routers/socialforge.py::/generate` to accept `language` and pass to the AI router
  - New front-end: `empire-command-center/app/socialforge/` (3+ pages: content library, calendar view, campaign editor)
  - New i18n strings: Spanish + English
  - **Do NOT touch:** the publish endpoints (`/post/instagram`, `/post/facebook`) — these stay manual, no scheduler daemon added
  - **Do NOT touch:** MAX files (`services/max/*`) — read-only
- **Tests:**
  - `test_socialforge_apostille_content.py` — content library loads, templates are well-formed, image prompts render
  - `test_socialforge_bilingual.py` — `/generate` accepts `language` and the system prompt changes
  - `test_socialforge_campaign_metadata.py` — campaigns can have a `target_landing_page`
- **Risk:** **low** — additive; no publish path changes
- **Owner:** Hermes Desktop for the copy/calendar (this doc), Codex or Claude for the code

---

## 8. Do not proceed list (audit phase)

This audit made no code changes, created no branches, ran no tests, scheduled no posts, sent no messages, and edited no files outside the report outputs in this batch. The 30-day calendar above is a **draft for the Founder's review** — it is not loaded into the SocialForge system, no posts are scheduled, and no publishing APIs are called.
