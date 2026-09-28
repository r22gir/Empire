# LeadForge → ForgeCRM → Workroom quote

Updated 2026-09-28. Stage 0 (manual capture) is the door that ships now.
Stage 1 (public form on a published landing) stays closed until the host is
honest and reachable. Do not publish the marketing site from this spec.

## Goal

One Workroom inbound becomes a LeadForge prospect, a ForgeCRM contact, and a
path to open a Workroom quote — without retyping, and without a second field list.

## Stage 0 — in repo now

Founder capture on `/workroom/capture` posting to `POST /api/v1/workroom-capture/intake`. The public LeadForge alias `POST /api/v1/leadforge/intake` stays on the #69 ad/Luxe path.

1. Fields below, `business=workroom`, source enum, explicit consent.
2. On submit: upsert ForgeCRM by email, create a new LeadForge lead event, store the intake row. Return `{lead_id, customer_id}`.
3. Founder sees the row on the capture page (deep link `/workroom/capture?intake={id}`). No email and no Telegram are sent.
4. **Create Workroom quote** prefills client name, email, phone, message, location, source, UTM, and photo links.
5. Public hostname and ads are out of scope. The mailto / inbox path in the [inbox runbook](./INBOX_RUNBOOK.md) remains the designer-facing contact.

Runbook: [MANUAL_CAPTURE_BRIDGE.md](./MANUAL_CAPTURE_BRIDGE.md).

## Stage 1 — not this change

Public form on a published Workroom landing, founder notification on every submit, and a public URL that returns 200 without an access wall. Do not claim those until they are tested on the real host.

## Form fields

| Field | Required | Notes |
|-------|----------|-------|
| full_name | yes | designer or firm contact |
| email | yes | unique CRM key |
| phone | no | |
| firm_name | no | |
| city_region | no | Mid-Atlantic vs national |
| job_type | yes | `drapery_romans`, `banquette`, `soft_seating`, `headboard`, `mixed`, `other` |
| message | yes | brief / room notes |
| photo_urls | no | links; file upload can wait |
| source | yes | `meta_ad`, `instagram`, `houzz`, `outreach`, `web`, `referral`, `other` |
| utm_campaign | no | pass from ads or the thread |
| consent_contact | yes | `yes` / `no` / `unknown` |

Tags on every row: `business=workroom`, and `campaign=workroom_national_48h` unless a later campaign is typed in. Never apostille or contractor on this door.

## API

Live router: `backend/app/routers/workroom_capture.py` (extends LeadForge + ForgeCRM; no new product).

1. `POST /api/v1/workroom-capture/intake` with the fields above.
2. Service upserts `customers` by email, inserts `lf_leads`, inserts `lf_workroom_intakes`, returns `{lead_id, customer_id, intake}`.
3. `POST /api/v1/workroom-capture/intake/{id}/quote` writes the Workroom quote draft (`quotes` JSON, `customer_id` + notes). It does not call the quote sender.

Idempotency choice: **one CRM contact, a new lead event per submit.** A repeated click on Create quote does not create a second quote.

## Acceptance

Stage 0, covered by `backend/tests/test_workroom_manual_capture.py`:

- [x] Submit twice with the same email → one CRM contact, two lead events
- [x] Create Workroom quote from the lead prefills name, email, phone, and message
- [x] Source and UTM are stored on the intake and copied onto the quote
- [x] Capture page copy is Workroom intake, not ApostApp or EmpireBox OS
- [x] No outbound email is sent by the intake or quote action

Still open for Stage 1:

- [ ] Founder notification fires once per new submit (Telegram or MAX)
- [ ] Public URL returns 200 without an access wall for the form ads would use
- [ ] “Leads work” on a published landing — do not claim this yet

## Out of scope

SocialForge scheduler, multi-tenant BusinessOps, auto email sequences, ShipForge, drawing-quality rewrite, and any send-from-app mail.
