# Install price comparison — 2026-10-23

Max compares past installation prices ($/window and $/LF) against a new quote,
writes an Empire Workroom PDF table to the job's documents, and does **not**
send Telegram / email / WhatsApp (and does **not** use the `present` tool).

## Found

Quote/invoice lines had no install tag, no window count, no linear-foot field.
Max had no tool for "compare Willard and Le Midi install prices against EST-xxxx".
The `present` path is a separate Telegram-capable report tool and must not be
used for this table.

## Changed

- `quote_line_items.windows` (int, nullable) and `lf` (real, nullable)
- On quote/invoice line save: descriptions like install / removal and
  installation / remove existing track and install / hourly install get
  `item_type='installation'`; LF from width inches / 12 (`160" wall` → 13 1/3 ft)
- Backfill: `backend/scripts/backfill_install_lines.py` (dry-run default;
  `--apply --yes` backs up DB first; refuses CI). Includes imported historical
  docs (812-C, 838, 897, 909, 803-A)
- Max tool `compare_install_prices` (read-only compare + PDF save)
- Send default OFF; never routes through `present`

## Tests

```
python3 -m pytest tests/test_install_line_tagging.py \
  tests/test_install_price_compare.py \
  tests/test_backfill_install_lines.py -q
# 15 passed
```

Frontend: `npx tsc --noEmit` exit 0; `npm run build` exit 0.

## Proof (mock data only, no send)

`execute_tool("compare_install_prices", {quote_numbers: [Willard, Le Midi], new_quote: EST-2026-003})`

- `sent=False` `telegram_sent=False` `email_sent=False` `whatsapp_sent=False` `used_present_tool=False`
- PDF saved on mock job `job-new` as `document_type=install_compare`
- Render: `reports/2026-10-23_install_price_compare.pdf`
- Raster: `reports/2026-10-23_install_price_compare.png`

Willard 10 windows / 13 1/3 ft / $1,450 → $145/window, $108.75/LF
Le Midi 8 windows / 20 ft / $2,000 → $250/window, $100/LF
New EST 9 windows / 16 ft / $1,800 → $200/window, $112.50/LF
