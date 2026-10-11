# Instance usage cap

Family editions (`EMPIRE_EDITION=amp` and `EMPIRE_EDITION=maxine`) each track their own LLM use and may spend at most a configured share of EmpireBox's measured AI use for the month. The default share is **20%**. The cap is enforced by default. No `EMPIRE_USAGE_BASELINE_*` variable is required. Do not ask Rafael for a measured invoice.

## Formula

```
allowance         = INSTANCE_USAGE_CAP_PCT / 100 × baseline
used_percent      = instance used this UTC month / baseline × 100
remaining_percent = max(0, cap_percent − used_percent)
```

`used_percent` is this instance's **share of EmpireBox total**, not "percent of the 20% slice". The cap means Max-e / Maxine may use at most 20% of total. Example: 13.1% used + 20% cap + 6.9% remaining is healthy (`level=ok`). A reading of `used_percent=65.7` next to `cap_percent=20` was the old allowance-relative meter and is wrong.

`INSTANCE_USAGE_CAP_PCT` defaults to 20.

Baseline, first one that is set:

1. `EMPIRE_USAGE_BASELINE_MONTHLY_USD` — optional override from a provider invoice. `used` is this instance's estimated USD.
2. `EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS` — optional override. `used` is this instance's input + output tokens.
3. **Auto (default):** sum of recorded tokens this UTC month across every readable edition `usage/usage.db` (this instance, `/data/amp`, `/data/maxine`, Workroom `backend/data`, plus `EMPIRE_USAGE_PEER_DATA_DIRS`). Every provider in those files counts. The baseline is `max(recorded_total, floor)`.

The floor is `EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS` (default **5,000,000** tokens). Why 5M: token basis matches stored MiniMax use; 5M ≈ $1.50 at the operator estimate $0.30/M, so 20% = **1,000,000 tokens (~$0.30) per instance** — daily WhatsApp and short chat, not a runaway loop. Conservative on purpose. Not a customer or lot price. Dell overrides with (1) or (2) when the real bill is known.

Workroom often has no `usage/usage.db`. `data_root_or_none()` is `None` when `EMPIRE_DATA_DIR` is unset (the Workroom default), so `usage_db_path()` returns `None` and Workroom does not write a usage file. The auto baseline still reads `/data/amp`, `/data/maxine`, `backend/data`, `~/empire-repo/backend/data`, and `EMPIRE_USAGE_PEER_DATA_DIRS` when those files exist. If none of them exist — or they have no rows this UTC month — `recorded_total` is 0 and the baseline is the **5,000,000** token floor.

Estimated USD, for display and for case 1:

```
(input_tokens + output_tokens) / 1_000_000 × MINIMAX_USD_PER_MILLION_TOKENS
```

`MINIMAX_USD_PER_MILLION_TOKENS` defaults to `0.30` so the card has a number. Replace it with the rate on the MiniMax invoice. It is not a price for a lot or a customer.

## What is stored

`EMPIRE_DATA_DIR/usage/usage.db`, table `llm_usage`: UTC day, UTC month, model, input tokens, output tokens, estimated USD. Day and month totals are sums of that table. The cap period is the calendar month. The day figure is informational.

Simli avatar sessions write into the same table (`provider=simli`, `model=simli-avatar`, `kind=avatar`). Output tokens are the capped session seconds. There is no separate Simli price; the estimator above turns those seconds into the USD figure the cap already uses.

`GET /api/v1/edition/usage` is owner-only and returns **percentages only** for this instance: `used_percent` (share of EmpireBox total), `remaining_percent` (room left until the cap, also a share of total), `level`, `message`, plus the Spanish policy note. It does **not** include `baseline`, `baseline_basis`, `allowance`, or absolute token/cost totals — those would let anyone derive EmpireBox-wide usage (`allowance = 0.2 × total`). Enforcement still uses the internal totals.

When `used_percent` is under the cap, `used_percent + remaining_percent = cap_percent`.

| used % of EmpireBox total | level | behavior |
| --- | --- | --- |
| under 80% of the cap (under 16 when cap is 20) | `ok` | calls proceed |
| 80% of the cap to under the cap (16 to under 20) | `warn` | calls proceed; the card shows remaining % of total in Spanish |
| at or over the cap (`used_percent` ≥ `cap_percent`) | `blocked` | heavy work is refused in Spanish; a short chat reply still runs and is counted |
| this instance used the whole baseline (`total_spend_hit`) | `blocked` | even short chats pause |

A request is heavy when it is a desk job, a tool call, an image, a generation (`source=generate`), a WhatsApp model call, or the user text is longer than `INSTANCE_SHORT_REPLY_CHARS` (default 400). Anything shorter, with none of those, is a short reply.

Inbound WhatsApp checks the cap **before ingest and before STT**. At or over the cap — or if usage data cannot be read — the owner gets a Spanish refusal and no model is called. Nothing is sent beyond the owner.

## Fail-open (chat only)

The chat cap is enforced when the checker runs. If the checker itself raises (missing usage DB, parse error, import failure), `_family_chat_prep` logs a **warning** (`usage cap check failed open; chat proceeds without a cap refusal`) and the chat continues. A broken checker must not silence Max-e chat.

WhatsApp inbound that would call a model **fails closed** on the same outage.

## Model

Family editions force the selector to MiniMax, model `MiniMax-M3` (`MINIMAX_MODEL` overrides the model id only). Fallback to other providers is off for that process.
