# WhatsApp channel — chat log (step one)

Workroom Max already replies to allowlisted founder phones over the Cloud API.
This step adds a **durable, per-edition chat log** and a **read-only Command Center viewer**. Attachment bytes and `~/jobs` filing are **not** in this step.

See also `backend/app/services/max/WHATSAPP_CLOUD.md` for webhook, allowlist, and send-gate rules.

## What is stored

Each inbound and outbound turn is written under this edition’s data directory:

`EMPIRE_DATA_DIR/whatsapp/whatsapp_chat_log.db`

Family editions (Max-e, Maxine) use their own `EMPIRE_DATA_DIR` and never see Rafael’s log.

Recorded fields:

- sender `wa_id` and display label (Rafael / Nelma from `business.json` `founder_phones`, plus last-10 fallbacks)
- direction, timestamp, WhatsApp message id
- type: text, voice-note marker (and transcript when present), document-sent marker (`filename` + doc/quote id), photo/location markers, call events
- delivery status from Meta status webhooks: `sent`, `delivered`, `read`, `failed` (with Meta error code)

Access tokens, app secrets, verify tokens, and `FOUNDER_PIN` are stripped before write.

## Read API (founder PIN)

All of these require `X-Founder-Pin`. They do not send WhatsApp messages and they do not delete.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/whatsapp/chats` | Conversations by sender, last message, last delivery status |
| `GET` | `/api/v1/whatsapp/chats/{wa_id}/messages` | Page a thread (`limit`, `offset`, optional `q`) |
| `GET` | `/api/v1/whatsapp/chats/search?q=` | Simple text search across this edition |

The existing webhook and explicit-confirm send routes are unchanged.

## Command Center

**WhatsApp Chats** (Growth / Channels, Quick Switch `H`) is Dark + Gold and phone-safe: conversation list, thread, search, failed deliveries marked in red. No composer, no edit, no delete.

## Safeguards

- Max emails of docs/invoices still go only to `empirebox2026@gmail.com`, never to clients.
- No deletes in this viewer.
- The chats page does not send outbound WhatsApp.
- Tests use `backend/tests/_live_data_guard.py` (tmp `EMPIRE_DATA_DIR`, no live Graph).

## Deferred

Saving inbound media and filing photos/documents into `~/jobs/<client-slug>/` is step two.
