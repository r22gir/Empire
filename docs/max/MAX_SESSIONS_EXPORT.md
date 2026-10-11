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
- Under pytest the journal is off unless `EMPIRE_MAX_JOURNAL_DB` is set. The test conftest
  always forces it to a temp DB (see `docs/TEST_ISOLATION.md`).

## Traffic tags: Rafael vs automated/test (2026-10-04)

No rows are ever dropped. Each exchange is *tagged*. The user row's `metadata_json` gets
`traffic` (`real` | `automated` | `test`), `reasons`, and, for HTTP calls, `client`
(`ip`, `forwarded_for`, `user_agent`). The `/max` router captures the caller through a
FastAPI dependency. A turn counts as automated when any of these holds:

- `continuity_audit_prompt`: the text is the Studio Continuity panel's "Run audit"
  command, `what continuity packet is loaded`.
- `local_host_client`: the client address is the server itself (loopback, or EmpireDell's
  own LAN/Tailscale address, e.g. 100.110.233.75). That means scripts and headless browsers
  on the Dell, not Rafael's phone or laptop.
- `automated_user_agent`: the user agent is HeadlessChrome, Playwright, curl,
  python-requests/httpx, node-fetch and similar.

The turn is tagged `test` when the client is a test client (`testclient`).

A session is left out of "Rafael's sessions" only when **every** user turn is
automated/test. Older rows that have no tag are judged by the prompt rule.

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
archived. Two kinds of session go under `excluded_sessions`, each with a `reason`
(`counts.excluded_by_reason` totals them), and `--include-tests` keeps both:
automated/test sessions (traffic tags above, e.g. `automated:continuity_audit_prompt`),
and sessions where every user line is a verbatim string from `backend/tests`
(`suspected_test_traffic`).

Run it for a date:

```
cd ~/empire-repo-main/backend
venv/bin/python scripts/export_max_sessions.py --date 2026-10-04   # or --yesterday, default today
curl -X POST 'http://127.0.0.1:8000/api/v1/max/sessions/export?date=2026-10-04'
```

Nightly: `max-sessions-export.timer` (user unit, copies in `systemd/`) runs at
23:55 and 00:20 ET. Each run exports yesterday and today.

## API

- `GET  /api/v1/max/sessions?days=7`: Rafael's recent journaled sessions, each with `traffic`.
  Automated/test sessions are hidden unless you pass `&include_automated=true`.
- `GET  /api/v1/max/sessions/{conversation_id}`: full turns, images as URLs
- `GET  /api/v1/max/sessions/attachment/{sha24}`: archived image/file
- `POST /api/v1/max/sessions/export?date=YYYY-MM-DD`: write the export (403 in a family edition)

## Studio UI

Max chat → History (clock) → **LOG** tab lists journaled sessions (studio, Telegram,
voice). Click one to reopen it in the chat with its images. It keeps the same
conversation id, so you can keep going. Images sent in the live chat now show in the
user bubble, and the portal auto-save keeps the `image` field, so reopened WEB chats show them too.
