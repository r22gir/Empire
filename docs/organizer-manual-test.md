# Empire Organizer — manual test checklist

The Organizer is **not Workroom-only**. It covers every life and business area
for the owner of this edition: Workroom, Empire, family, personal, other ventures
(and AMP on Max-e). One unified calendar. Jobs are one item type in one area,
not the product.

Draft only. Nothing on this list should send a message without the **owner's tap**.

Editions (isolated — never mix data):

| Edition | Assistant | Owner | Areas |
|---|---|---|---|
| `main` | Max | Rafael | Workroom, Empire, Family, Personal, Ventures |
| `max_e` | Max-e | Juan | AMP, Family, Personal, Ventures |
| `maxine` | Maxine | Camilo | Family, Personal, Ventures |

`EMPIRE_EDITION` is fail-closed: an unknown value is its own isolated bucket and
never maps onto Rafael's `main` / Workroom data. Maxine must never show Argos
Campestre legal or company details. Model is **grok-4.6** only.

## Desktop (Command Center)

1. Home (`/`) → Today card lists today’s Organizer items (or empty state) and **Open organizer** goes to `/?screen=calendar`.
2. Left nav **Organizer** opens the same screen. Workroom → Organizer tab does too (Workroom is one area, not the whole app).
3. Edition badge shows this process (Max · Rafael / Max-e · Juan / Maxine · Camilo). Area chips: **All areas** (unified) plus one colorful chip per life/business space (icon + accent). Double-tap a chip to change its icon/color. Organizer is never Workroom-only.
4. **Today** view (default) has three columns across every area: Overdue / Today / Upcoming. **Board** has Open / Doing / Done. Drag a card between columns on desktop (HTML5) and phone (pointer). Day / week / month still render. Drag an event to a new time; a double-booked person shows a **Not saved — conflict** banner (no silent overwrite). Cancel leaves the old time. “Keep anyway” writes after confirm. After a successful move, **Tell the crew?** offers a draft only.
5. Resize handle changes duration and hits the same conflict path.
6. Month: drag a chip to another day.
7. Lanes: each person has a row; unassigned people do not leak another person’s stops.
8. Filters (area / person / type / search, plus job only on Workroom + Max) update agenda + calendar together.
9. Quick-add `call Marley Friday 2pm` (Workroom) or `dentist Thursday 3pm` (Personal) opens a confirm draft (not saved). Confirm writes it. Space is picked when the words make it obvious. **Voice** uses `/organizer/transcribe` (existing Groq Whisper) and falls back to browser STT. **Photo** attaches via capture ingest. Command `move Marley's install to Friday and tell the crew` moves the event and drafts the crew text (not sent).
10. Job card **Schedule** (Max / Workroom only) opens `/?screen=calendar&job=<id>` with that job selected, a progress bar (`done/total` of linked tasks), and one-tap links to estimate / client / job / calendar. Family / Max-e / Maxine do not show job filters or job buttons.
11. Due dates save a row in `organizer_reminders`. Max’s notification system (`notify_founder`) fires when due. Nothing outbound is sent without the owner’s tap.
11. **Approve today** on the assistant’s proposed day marks the plan approved and does not send anything.
12. Route card lists stops + drive-minute estimates and **Open maps** uses Google Maps directions (no live-traffic claim).
13. Smart follow-ups (Workroom / Max only) show a pre-written nudge plus **Approve & Send**. Tapping it is the owner's tap. Without that tap, nothing is sent.
14. Every row has action buttons: stop → Navigate / Call / Text. Job buttons (Send quote / Order fabric / Request deposit / Book install) appear only on Workroom items in Max. File → Attach or Ask Max / Max-e / Maxine. Text/email/quote/deposit/crew stay drafts until Approve & Send.
15. ICS download opens a `.ics`. Subscribe-token note is read-only. Google Calendar status says no connector exists.
16. People: add anyone this life needs (family, friend, doctor, teacher, crew). Assign them on an event; map/call links work.
17. Hitting the edition usage cap shows a 429 toast and does not write.
18. **Pending messages** card (sidebar) and **messages** view list unanswered/waiting mail from this edition's connected Gmail/Outlook only. Each row shows area / job / person when linked, plus a suggested reply. **Open** opens the mailbox. **Draft reply** queues a draft (approval queue). **Snooze** hides it. **To-do / Follow-up** saves an Organizer item. Nothing is sent without **Approve & Send**. Maxine never shows Argos Campestre mail. Another edition's mailboxes never appear.

## iPhone (Safari, 390-wide)

1. Home Today card scrolls with the page; **Open organizer** is tappable.
2. Organizer page scrolls the whole screen (no trapped inner scroll that blocks the phone). Area chips wrap.
3. Day grid is usable; tap an event for the sheet. Navigate / Call / Text are tappable. Job buttons appear only on Workroom / Max.
4. Quick-add and filters wrap; add sheet is a bottom sheet that scrolls. Area picker is in the sheet.
5. Crew phone page `/organizer/crew?token=…` shows only that person’s stops + check-in.

## Capture / editions

1. Upload ingest rejects `.exe`. Allowed jpg/pdf stores with `public_url: null` and `edition` equal to this process (`main` / `max_e` / `maxine`).
2. WhatsApp image/document (if channel enabled) files into this edition’s store; reply still never emails a client.
3. Switch `EMPIRE_EDITION` to `max_e` or `maxine`: that backend sees only its own board. Rafael's Workroom jobs and Argos Campestre strings do not appear. An unknown `EMPIRE_EDITION` is isolated (fail-closed), never `main`.
4. Creating “Argos Campestre …” on Maxine is rejected (400). A family to-do on Maxine saves.
5. Each edition has its own daily usage caps. Crossing the cap returns 429.

## Pending messages (read-only email)

Reuses `gmail_reader.check_inbox` (`gmail.readonly`) and `outlook_reader.search_messages` (`Mail.Read`, GET only). Each edition reads only its own token files (`GMAIL_TOKEN_PATH` / `OUTLOOK_TOKEN_PATH` on Max; `GMAIL_TOKEN_PATH_{ED}` / `OUTLOOK_TOKEN_PATH_{ED}` or `~/.config/empirebox/{ed}/…` on Max-e / Maxine). A family edition pointing at Rafael's token is refused.

1. Command Center → Organizer → **messages**. Empty state if this edition has no connected mailbox.
2. With a connected mailbox: unanswered and waiting threads appear across Gmail and Outlook. Each row names the area, and a job/person when one matches.
3. Suggested reply is a draft for review (owner's name). **Open** is a mailbox link only.
4. **Draft reply** creates an approval-queue item (`source=organizer_mail`, `sent=false`). Status stays pending until the owner taps Approve & Send. The Organizer never calls Gmail/Outlook send or reply APIs.
5. **Snooze** hides the row until the snooze time. **Turn into to-do** / **follow-up** writes an Organizer item in this edition and removes it from Pending.
6. Switch `EMPIRE_EDITION` to `maxine`: Rafael's inbox is not read. Argos Campestre subjects/senders are dropped. Juan's Max-e mailbox is not visible either.
7. Unknown `EMPIRE_EDITION` has no mailbox sources and never falls through to `main`.

## Max / Max-e / Maxine chat

1. “schedule install for the Marley job Friday 10am” (Max) or “dentist Thursday 3pm” (any edition) uses `draft_organizer_item` and says it is a draft, not already on the calendar.
2. “move Marley's install to Friday and tell the crew” uses `run_organizer_command`, moves the event, and drafts the crew message. Nothing is sent without the owner's tap.
