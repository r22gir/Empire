# Max sessions — full journal + daily export (2026-10-04)

Rafael wants every Max session (studio chat, live voice, Telegram) kept in full,
images included, so Chief e can review them daily. Main studio only. Family
editions (AMP 8011, Maxine 8012) are separate checkouts with their own
`EMPIRE_DATA_DIR` and are never read.

## Where things are stored

| What | Where |
|---|---|
| Full turn journal (new) | `~/empire-data/brain/max_session_journal.db`, table `max_session_turns` |
| Archived images/files (new) | `~/empire-data/max-sessions-archive/attachments/<sha[:2]>/<sha[:24]>.<ext>` |
| Daily export (new) | `~/empire-data/max-sessions/YYYY-MM-DD/` |
| Legacy cross-channel ledger | `~/empire-data/brain/unified_messages.db` (still written, unchanged) |
| Legacy uploads | `~/empire-repo/backend/data/uploads/images/` (`/files/upload`, Telegram photos) |

Each journal row: conversation id, channel (`studio`/`telegram`/`voice`/`whatsapp`),
raw input channel, role, full text (no cap), model, tool calls
(`tool`, `success`, `error`, short `summary`, redacted `args`), attachments
(copied file + sha256), status (`ok`/`error`/`interrupted`), endpoint, latency,
UTC timestamp and America/New_York date, edition.

Hooks:
- `/max/chat/stream`: the whole SSE response is wrapped (`journal_stream`), so
  every path counts, including guardrail refusals, link intel, direct routes, GPU guard,
  "what's new", inventory clarification, IMAGE_NOT_AVAILABLE. It records what was shown.
- `_chat_with_max_service` (used by `/max/chat`, Telegram in-process, avatar, WhatsApp):
  wrapper journals the reply or the exception.
- Live voice: `VoiceTranscript._write` mirrors every user/Max line, tool call and
  call start/end/summary into the journal.
- Under pytest the journal is off unless `EMPIRE_MAX_JOURNAL_DB` is set.

## Daily export

```
~/empire-data/max-sessions/2026-10-04/
  1432_studio_ab12cd34.jsonl   header line + one line per turn
  1432_studio_ab12cd34.md      the same session, readable, images inline
  images/                      copies of every image/file sent that day
  summary.json                 sessions, turns, by_channel, images, tool_errors,
                               refusals, cant_replies, repeats, corrections,
                               excluded_sessions, session_index
```

Sources: journal first. For older dates, or turns from before the journal existed,
`unified_messages` is used and referenced images are found in the upload dirs and
archived. Sessions where *every* user line is a verbatim string from
`backend/tests` are treated as test traffic and listed under `excluded_sessions`
(`--include-tests` keeps them).

Run it for a date:

```
cd ~/empire-repo-main/backend
venv/bin/python scripts/export_max_sessions.py --date 2026-10-04   # or --yesterday, default today
curl -X POST 'http://127.0.0.1:8000/api/v1/max/sessions/export?date=2026-10-04'
```

Nightly: `max-sessions-export.timer` (user unit, copies in `systemd/`) runs at
23:55 and 00:20 ET. Each run exports yesterday and today.

## API

- `GET  /api/v1/max/sessions?days=7`: recent journaled sessions
- `GET  /api/v1/max/sessions/{conversation_id}`: full turns, images as URLs
- `GET  /api/v1/max/sessions/attachment/{sha24}`: archived image/file
- `POST /api/v1/max/sessions/export?date=YYYY-MM-DD`: write the export (403 in a family edition)

## Studio UI

Max chat → History (clock) → **LOG** tab lists journaled sessions (studio, Telegram,
voice). Click one to reopen it in the chat with its images. It keeps the same
conversation id, so you can keep going. Images sent in the live chat now show in the
user bubble, and the portal auto-save keeps the `image` field, so reopened WEB chats show them too.
