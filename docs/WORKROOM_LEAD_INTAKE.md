# Workroom LeadForge intake

One Workroom inbound becomes a ForgeCRM contact, a LeadForge lead, a founder notice, and (when someone clicks it) a Workroom quote. LuxeForge rich intake uses this same path. There is not a second CRM.

Contact address for CTAs: `workroom@empirebox.store` (routes to empirebox2026@gmail.com).

## How to hit it

Command Center → LeadForge → **Workroom Intake**.

The Workroom landing form is on `/workroom#workroom-lead` and posts to the same API.

```bash
curl -s -X POST "$API/api/v1/leads/intake" \
  -H 'Content-Type: application/json' \
  -d '{
    "full_name": "Ada Designer",
    "email": "ada@studio.example",
    "phone": "555-0100",
    "firm_name": "Ada Studio",
    "city_region": "Mid-Atlantic",
    "job_type": "drapery_romans",
    "message": "Living room panels, four windows.",
    "photo_urls": ["https://cdn.example/room.jpg"],
    "source": "meta_ad",
    "utm_campaign": "spring_drapery",
    "consent_contact": true,
    "business": "workroom",
    "capture_surface": "workroom_form"
  }'
```

`$API` is the backend origin that Command Center already proxies (`/api/v1` → local FastAPI). Alias with the same body: `POST /api/v1/leadforge/intake`.

Field contract (including the LuxeForge object): `GET /api/v1/leads/intake/contract`.

Open the quote (prefilled name, email, phone, room notes, photo URLs):

```bash
curl -s -X POST "$API/api/v1/leads/LEAD_ID/workroom-quote"
```

Repeat quote calls return the same draft.

### Idempotency

Email is the customer key, case-insensitive. Two submits with the same email keep **one** ForgeCRM customer and insert **two** LeadForge leads (and two prospects), so a second inquiry is not thrown away. Founder notification fires **once per submit**. The first customer `source` stays; later source/utm values are on the new lead and in tags.

Tags always include `business=workroom`. Campaign defaults to `workroom_national_48h` unless `campaign` is sent. This form rejects any `business` other than `workroom`.

### LuxeForge handoff

Post the same endpoint with `capture_surface` set to `luxeforge` and optional:

`brief`, `room_count`, `measure_urls`, `designer_portfolio_url`, `project_timeline`, `photo_notes`.

Put the shared room notes in `message`. Extra keys are stored on the lead `intake_payload`. Quote create copies the brief into notes and measure URLs onto the quote photos. Do not invent another customer table.

### Founder notice

Each accepted submit writes an in-app founder notification (`event=workroom_lead_intake`) with the lead id, customer id, and a Command Center deep link. Telegram is attempted only when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_FOUNDER_CHAT_ID` are set. Otherwise the response says `telegram: not_configured`. A missing bot does not fail the intake.

## Public host

`workroom.` and `cc.` public hosts have been returning **521**, and operator hosts sit behind **Cloudflare Access**. This API is what Command Center and a reachable backend can call. It is not an ad destination until a public URL returns 200 without an Access wall.

Until that is true, ads should use `mailto:workroom@empirebox.store` (or Instagram DM) and a person enters the lead in Command Center. Do not claim a public self-serve portal.

## Tests

```bash
cd backend
python -m pytest tests/test_workroom_lead_intake.py -q
```

Covers double-submit of the same email, quote prefill, and source/utm on the lead.
