# WhatsApp Business Cloud API — Workroom Max

The channel is off until all four variables are set. Status never includes their values.

| Variable | Role |
| --- | --- |
| `WHATSAPP_ACCESS_TOKEN` | Graph API bearer token for the WhatsApp Business account |
| `WHATSAPP_PHONE_NUMBER_ID` | Phone number id used in `/{id}/messages` |
| `WHATSAPP_APP_SECRET` | App secret for `X-Hub-Signature-256` |
| `WHATSAPP_VERIFY_TOKEN` | Token Meta sends as `hub.verify_token` |

Empty or missing values leave the channel disabled. `GET /api/v1/whatsapp/status` and Hermes “whatsapp status” both say `disabled` and list the missing names.

## Meta setup

1. In the Meta app, add the WhatsApp product and copy the phone number id and a system-user token into the env vars above. Do not commit them.
2. Set a verify token of your choosing and the same value in `WHATSAPP_VERIFY_TOKEN`.
3. Set the callback URL to `https://<your-api-host>/api/v1/whatsapp/webhook`.
4. Subscribe the webhook to the `messages` field.
5. Meta’s GET challenge is answered only when `hub.mode=subscribe` and the verify token matches. The response body is the raw `hub.challenge`.
6. Every POST must carry `X-Hub-Signature-256: sha256=<hmac of the raw body with the app secret>`. A bad signature is rejected and not processed.

Graph calls use `https://graph.facebook.com/v21.0`.

## Who can message Max

Only the founder numbers on file. Today that is the workroom phone in `backend/app/config/business.json` (`business_phone`). Optional `founder_phones` or `owner_phones` arrays in that file are included when present. Everyone else is ignored and gets no reply. This is not a fifth env var.

## What each message does

- Voice notes and audio are transcribed with the existing STT service and appended to the voice-to-quote/drawing draft (`session key whatsapp:<number>`).
- Photos go through Photo Analyzer and, when it finds items, become a draft quote. The quote stays `draft`.
- Other text goes to Max chat. Text that is a quote, a “done”, or a follow-up on an open WhatsApp draft stays on that draft instead of starting a second chat turn.
- Saying “send it” records the request and does not email or WhatsApp the client document.

## Reply style

`WHATSAPP_REPLY_MODE` is per instance. Unset means `voice_text`.

| Mode | What Rafael hears and reads |
| --- | --- |
| `voice_text` | A voice note plus a text summary of the same reply. This is the default. |
| `text` | The reply as text only. |
| `match` | Voice note plus summary when he sent a voice note. Text only when he sent text or a photo. |

The voice note uses the existing TTS service, encoded as OGG/Opus, and is uploaded as WhatsApp audio with `voice: true`. The text message is a short summary (a short reply is left whole). If TTS or the OGG encode fails, Max sends the full text and starts it with “Voice note unavailable (TTS failed). Text only.”

Quote and drawing PDFs go out as document messages on that same reply. They are drafts back to the founder. They are not emailed.

## Outbound

- A session reply is allowed only inside 24 hours of that founder’s last inbound message, and only to an allowlisted number. The webhook uses this for the acknowledgement back to Rafael.
- Outside that window the only send is an already-approved template, and only through `POST /api/v1/whatsapp/send` with `confirmed: true` and `template_name`.
- `confirmed: false` is refused. The inbound webhook never calls the send route and never calls the mailer.

## Same module on the family editions

Copy these without changing the function names or the routes:

- `backend/app/services/max/whatsapp_channel.py`
- `backend/app/routers/whatsapp.py`
- this file

`hermes_phase3.py` only reports `channel_status()`. The default handlers call Workroom voice, Photo Analyzer, and Max chat; another edition can pass its own handlers into `process_webhook` without forking the webhook, signature, allowlist, window, or confirm gate.
