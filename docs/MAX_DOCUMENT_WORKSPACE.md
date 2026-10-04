# Max: document workspace (quotes, invoices, final docs)

Added 2026-10-04 at Rafael's request. Max's system prompt links here (`system_prompt.py`, the Quote System section).

## What the founder sees
- **Quotes and invoices open as a page that looks like the client PDF.** That page is the editor. Tabs:
  - **Document** (default): the WYSIWYG page.
  - **Actual PDF**: the real generated PDF, plus the saved FINAL file when one exists in the job folder.
  - **Details**: quotes only. Gauges, photos, verification, proposals and deposit link.
  - **Docs**: every saved file for the job.
- **Editing on the Document tab:**
  - Click a line to edit its description, qty, unit or rate.
  - Drag a line to another room, or use "Move to room".
  - Use "+ Add a line" under a room, or "Add room".
  - Totals, discount, tax and deposit update live. Save writes the lines in room order.
  - The client PDF prints the same room sections, in the same order.
- **Locks:**
  - Quotes in sent, accepted, in_production or completed status are locked (Sprint 1c immutability).
  - Invoices can be edited only while they are in draft.
- **Action bar** (top on desktop, bottom on phones): Preview · Print · Download PDF · Share (copy link / WhatsApp / email draft) · Copy link · Versions.
- **Convert to invoice** (on the quote toolbar):
  - Asks for confirmation, then calls `POST /api/v1/quotes-v2/{id}/to-invoice`.
  - Creates a **draft** invoice that carries over the lines with rooms, unit, client, and deposit required/received. It then opens the invoice page.
  - Only works on sent or accepted quotes. Drafts need founder approval (PIN) and a send first.
  - Nothing is emailed.
- **Deep links:** `/?screen=quote&id=<quote id>` and `/?screen=invoice&id=<invoice id>`.

## Max tools
| Tool | What it does | Safety |
|---|---|---|
| `open_final_doc` | Finds a saved job document (final estimate, presentation, invoice, drawing, photos) through the Final Docs hub and returns an in-app viewer link. Prefers job-folder FINAL files. | Read-only |
| `open_record` | Opens a quote or invoice on the document page. Accepts `type` plus `quote_id`/`quote_number`, `invoice_id`/`invoice_number`, or `query` (client or project words). Aliases: open_quote, open_invoice, show_quote, show_invoice. | Read-only |
| `edit_quote_lines` | Edits a draft quote's lines by room. `operations`: `move` (line, room), `update` (line, description/quantity/unit/unit_price/room), `add` (room, description, quantity, unit, unit_price), `remove` (line). Lines are referenced by the line number shown on the page, `item_id`, or a unique `match` text. | Refuses locked quotes. `remove` returns a preview until `confirm=true`. Line numbers are renumbered in room order afterwards. |
| `convert_quote_to_invoice` | Quote to **draft** invoice through the canonical endpoint. | Without `confirm=true` it only previews (lines, rooms, total, deposit). If an invoice already exists for the quote, it opens that invoice instead of creating a duplicate. Never sends anything. |

### Room names
Rooms are stored as text, e.g. `LIVING ROOM — 1. Installation` (room — part).
- Saying "office" while moving a `... — 4. Materials` line lands it in `OFFICE — 4. Materials`.
- When a room has several parts and Max is adding a line, he must name the part. The tool error lists the available parts.

### Conversation rules
1. "Open Nehal's quote": call `open_record` (type quote, query "Nehal" or the EST number). The chat shows a card that opens the page.
2. "Move the batons to the living room": call `edit_quote_lines` with a move. Report the new room subtotals and total.
3. "Make the invoice": call `convert_quote_to_invoice` without confirm, read the preview back, wait for a yes, then call again with `confirm=true`. Tell the founder the invoice is a **draft and not sent**. Sending remains a separate founder step.
4. "Show me the final estimate / presentation": call `open_final_doc`.
5. Never send email, WhatsApp or Telegram as part of these tools. Share links are drafts the founder sends.

## Where documents come from (read-only index, nothing moved)
- `~/empire-data/quotes/pdf`
- `backend/data/quotes/pdf`
- `backend/data/invoices/pdf`
- `~/empire-data/presentations`
- `~/jobs/<client>` job folders, the curated FINAL files
- DB records: invoices, drawing_versions, job_documents photos

## Known limits
- Room photos chosen on the document page are stored only on that device (localStorage).
- A full quote save from the page re-prices lines through the pricing engine. Structural fields (item_type, dimensions, drawing_svg) are not round-tripped by the full-save endpoint. This is pre-existing behaviour.
- The legacy `/finance/invoices/from-quote/{id}` endpoint reads old JSON quotes. The UI and Max now use `/quotes-v2/{id}/to-invoice`.
