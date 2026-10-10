# WhatsApp channel — chat log, media, and job filing

Workroom Max replies to allowlisted founder phones over the Cloud API.
This edition keeps a **durable chat log**, stores inbound media immediately
(Meta URLs expire), and files photos/documents into job folders when the
client is known.

See also `backend/app/services/max/WHATSAPP_CLOUD.md` for webhook, allowlist, and send-gate rules.

## What is stored

Each inbound and outbound turn lives under this edition’s data directory:

`EMPIRE_DATA_DIR/whatsapp/whatsapp_chat_log.db`

Family editions (Max-e, Maxine) use their own `EMPIRE_DATA_DIR` and never see Rafael’s log.

Recorded fields:

- sender `wa_id` and display label (Rafael / Nelma from `business.json` `founder_phones`)
- direction, timestamp, WhatsApp message id
- type: text, voice-note (marker + stored audio), document (filename + doc/quote id), photo, video, sticker, location, call
- delivery status from Meta status webhooks: `sent`, `delivered`, `read`, `failed` (Meta error code)
- attachment metadata: filename, MIME, size, local path, job slug, filed path

Access tokens, app secrets, verify tokens, and `FOUNDER_PIN` are stripped before write.

## Media

Inbound photos, PDFs/documents, voice notes, video, stickers, and locations are downloaded as soon as the webhook arrives and saved under:

`EMPIRE_DATA_DIR/whatsapp/media/`

Outbound Final Docs PDFs Max sends back to the founder are stored the same way and referenced by doc/quote id.

| Variable | Default | Role |
| --- | --- | --- |
| `WHATSAPP_MAX_ATTACHMENT_SIZE_BYTES` | 52428800 (50 MB) | Skip storing oversize files |
| `WHATSAPP_RETENTION_DAYS` | 365 | Purge edition `media/` and `inbox/` (never `~/jobs`) |
| `WHATSAPP_JOBS_ROOT` | `~/jobs` | Job folders the Final Docs hub indexes |

## Job filing

Photos go to `~/jobs/<client-slug>/photos/`. Documents go to `~/jobs/<client-slug>/received/`.

Resolution order (`app/services/max/doc_lookup.py` + `client_aliases.json`):

1. Caption or message names one client, nickname, address, or quote number → that job (and it becomes the conversation’s active job).
2. More than one match → **do not guess**. Park in `EMPIRE_DATA_DIR/whatsapp/inbox/` and Max asks which job.
3. No name, but this conversation already has an active job → use that job.
4. Unknown → inbox + ask.

Existing files are never overwritten (UTC timestamp suffix). The chat log records `filed_path` / `filing_status`. Rafael can move a file from the chat page (`POST /api/v1/whatsapp/attachments/{id}/refile`). That is the only write on that page.

## Read API (founder PIN)

All of these require `X-Founder-Pin`. They do not send WhatsApp messages and they do not delete.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/whatsapp/chats` | Conversations, last message, active job |
| `GET` | `/api/v1/whatsapp/chats/{wa_id}/messages` | Page a thread (`limit`, `offset`, optional `q`) |
| `GET` | `/api/v1/whatsapp/chats/search?q=` | Text search |
| `GET` | `/api/v1/whatsapp/media/{attachment_id}` | Download stored media |
| `GET` | `/api/v1/whatsapp/jobs` | Job folders for the move-to-job control |
| `POST` | `/api/v1/whatsapp/attachments/{id}/refile` | Move a file into a job (`{job_slug}`) |
| `GET` | `/api/v1/whatsapp/chats/{wa_id}/copy` | Plain-text conversation |
| `GET` | `/api/v1/whatsapp/chats/{wa_id}/export` | PDF (or `?format=txt`) |

The existing webhook and explicit-confirm send routes are unchanged.

## Command Center

**WhatsApp Chats** (Growth / Channels, Quick Switch `H`) is Dark + Gold and phone-safe:

- conversation list, thread, search, failed deliveries in red
- image thumbnails (tap for full size), voice-note player, PDF/doc open + save
- Export chat as PDF, Copy conversation, print-friendly layout
- move-to-job on each attachment (only write)

No composer, no share, no send-to-client.

## Safeguards

- Max emails of docs/invoices still go only to `empirebox2026@gmail.com`, never to clients.
- No deletes in this viewer.
- The chats page does not send outbound WhatsApp.
- Tests use `backend/tests/_live_data_guard.py` (tmp `EMPIRE_DATA_DIR` and `WHATSAPP_JOBS_ROOT`, no live Graph).
