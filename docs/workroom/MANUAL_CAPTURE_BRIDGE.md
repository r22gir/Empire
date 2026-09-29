# Manual capture bridge — Workroom

Stage 0 backup while the public LeadForge form is not the live ad door.
This is a founder capture path inside Command Center. It is not a public
“powered by LeadForge” form and it does not publish the marketing site.

Field contract: [LEADFORGE_WORKROOM_INTAKE_SPEC.md](./LEADFORGE_WORKROOM_INTAKE_SPEC.md).
Inbox steps: [INBOX_RUNBOOK.md](./INBOX_RUNBOOK.md).

## Click path

1. Open **Workroom → Inbox capture**, or go directly to `/workroom/capture` on the command center host (studio or local). The public apex returns 404 for that path.
2. Triage `workroom@empirebox.store` in Gmail (it routes to `empirebox2026@gmail.com`). The page links the same search.
3. Enter the lead with the LeadForge fields. Submit creates:
   - one ForgeCRM customer, idempotent on email
   - one new LeadForge lead event (`lf_leads`, `business_unit=workroom`)
   - one intake row (`lf_workroom_intakes`) that is the system of record for this inbound
4. Click **Create Workroom quote**. That writes a draft quote JSON the existing quote screen can open (`/quote/{id}`), prefilled with name, email, phone, firm, city/region, message, source, UTM, and photo links.
5. Price it in the quote draft. Reply from the workroom mailbox yourself. Then mark the row `quoted` or `needs_info` and set the next action.

Nothing in steps 3–5 sends email.

## One door

Founder capture lives at `POST /api/v1/workroom-capture/intake` so it does not collide with the public LeadForge alias `POST /api/v1/leadforge/intake`.

| Field | Required | Allowed / notes |
|-------|----------|-----------------|
| full_name | yes | designer or firm contact |
| email | yes | CRM unique key, case-insensitive |
| phone | no | blank stays blank |
| firm_name | no | |
| city_region | no | |
| job_type | yes | `drapery_romans`, `banquette`, `soft_seating`, `headboard`, `mixed`, `other` |
| message | yes | brief / room notes |
| photo_urls | no | list of links, upload later is fine |
| source | yes | `meta_ad`, `instagram`, `houzz`, `outreach`, `web`, `referral`, `other` |
| utm_campaign | no | pass through from the ad or thread |
| consent_contact | yes | `yes`, `no`, or `unknown` — never invented |
| business | locked | `workroom` only. Apostille and contractor are rejected |
| campaign | default | `workroom_national_48h` |
| owner | default | `Rafael` when blank |
| notes | no | extra founder notes |
| next_action | default | acknowledge today and collect quote facts |

Also:

- `GET /api/v1/workroom-capture/intake` — recent rows
- `GET /api/v1/workroom-capture/intake/{id}`
- `PATCH /api/v1/workroom-capture/intake/{id}` — status, next action, notes, owner, last contacted. Does not send.
- `POST /api/v1/workroom-capture/intake/{id}/quote` — open the draft. A second click returns the same quote.

## Idempotency

Submitting twice with the same email:

- **one** ForgeCRM customer (`customers`, matched on `LOWER(email)`)
- **two** LeadForge lead events
- **two** intake rows

Empty phone, firm, or city on the customer are filled from a later submit. A later submit does not overwrite a value that is already stored. The first email casing is kept on the customer. Each lead event keeps the email as typed on that submit.

Opening a quote twice returns `quote_outcome=already_open` and does not write a second file.

## Quote draft

The draft is a Workroom quote (`business_unit=workroom`, `pricing_mode=flat`, status `draft`) with a zero-dollar pending line. Notes carry the brief, consent, source, campaign, UTM, photo links, and the questions still required for a real price. `sent_at` stays empty.

The capture row moves to `quoting` and stores `quote_id`.

## Honesty

- Stage 0 is this human door. It is ready when the founder can open `/workroom/capture`, save a prospect, and open a draft quote.
- Do not tell a designer the public LeadForge form is live.
- Do not start ad spend from this bridge. Hero consent and publish yes are still required.
- Founder notification for this door is the capture page itself (`notification=in_app_only`). Telegram and email are not fired.
