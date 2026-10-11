# Workroom Organizer — manual test checklist

Draft only. Nothing on this list should send a message to a customer.

## Desktop (Command Center)

1. Home (`/`) → Today card lists today’s Organizer items (or empty state) and **Open organizer** goes to `/?screen=calendar`.
2. Left nav **Organizer** opens the same screen. Workroom → Organizer tab does too.
3. Day / week / month views render. Drag an event to a new time; a double-booked person shows a **Not saved — conflict** banner (no silent overwrite). Cancel leaves the old time. “Keep anyway” writes after confirm. After a successful move, **Tell the crew?** offers a draft only.
4. Resize handle changes duration and hits the same conflict path.
5. Month: drag a chip to another day.
6. Lanes: each crew member has a row; unassigned people do not leak another installer’s stops.
7. Filters (job / person / type / search) update agenda + calendar together.
8. Quick-add `call Marley Friday 2pm` opens a confirm draft (not saved). Confirm writes it. Voice button drafts or says the browser cannot listen. Command `move Marley's install to Friday and tell the crew` moves the event and drafts the crew text (not sent).
9. Job card **Schedule** opens `/?screen=calendar&job=<id>` with that job selected and the timeline strip visible.
10. **Approve today** on Max’s proposed day marks the plan approved and does not send anything.
11. Route card lists stops + drive-minute estimates and **Open maps** uses Google Maps directions (no live-traffic claim).
12. Smart follow-ups show a pre-written nudge plus **Approve & Send**. Tapping it is the founder tap. Without that tap, nothing is sent.
13. Every row has action buttons: stop → Navigate / Call / Text; job → Send quote / Order fabric / Request deposit / Book install; file → Attach to email/quote or Ask Max. Text/email/quote/deposit/crew stay drafts until Approve & Send.
14. ICS download opens a `.ics`. Subscribe-token note is read-only. Google Calendar status says no connector exists.
15. People: add an installer with phone + weekday availability. Assign them on an event; map/call links work.

## iPhone (Safari, 390-wide)

1. Home Today card scrolls with the page; **Open organizer** is tappable.
2. Organizer page scrolls the whole screen (no trapped inner scroll that blocks the phone).
3. Day grid is usable; tap an event for the sheet. Navigate / Call / Text and job buttons (Send quote, Order fabric, Request deposit, Book install) are tappable.
4. Quick-add and filters wrap; add sheet is a bottom sheet that scrolls.
5. Crew phone page `/organizer/crew?token=…` shows only that person’s stops + check-in.

## Capture / editions

1. Upload ingest rejects `.exe`. Allowed jpg/pdf stores with `public_url: null`.
2. WhatsApp image/document (if channel enabled) files into this edition’s store; reply still never emails a client.
3. Max-e / Maxine backends (`EMPIRE_EDITION`) see an empty Workroom board — isolation holds.

## Max chat

1. “schedule install for the Marley job Friday 10am” uses `draft_organizer_item` and says it is a draft, not already on the calendar.
2. “move Marley's install to Friday and tell the crew” uses `run_organizer_command`, moves the event, and drafts the crew message. Nothing is sent.
