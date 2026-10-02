# Instance usage cap

Family editions (`EMPIRE_EDITION=amp` and `EMPIRE_EDITION=maxine`) each track their own LLM use and may spend at most a configured share of EmpireBox's measured AI use for the month. The default share is **20%**.

## Formula

```
allowance = INSTANCE_USAGE_CAP_PCT / 100 × baseline
ratio     = used this UTC month / allowance
```

`INSTANCE_USAGE_CAP_PCT` defaults to 20.

Baseline, first one that is set:

1. `EMPIRE_USAGE_BASELINE_MONTHLY_USD` — the measured EmpireBox AI spend for the month (provider invoice or the sum across instances). `used` is this instance's estimated USD.
2. `EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS` — the measured EmpireBox token total for the month. `used` is this instance's input + output tokens.

Estimated USD, for display and for case 1:

```
(input_tokens + output_tokens) / 1_000_000 × MINIMAX_USD_PER_MILLION_TOKENS
```

`MINIMAX_USD_PER_MILLION_TOKENS` defaults to `0.30` so the card has a number. Replace it with the rate on the MiniMax invoice. It is not a price for a lot or a customer.

If neither baseline is set, calls are still stored and the cap is not enforced. The Uso card says the baseline is missing.

## What is stored

`EMPIRE_DATA_DIR/usage/usage.db`, table `llm_usage`: UTC day, UTC month, model, input tokens, output tokens, estimated USD. Day and month totals are sums of that table. The cap period is the calendar month. The day figure is informational.

Simli avatar sessions write into the same table (`provider=simli`, `model=simli-avatar`, `kind=avatar`). Output tokens are the capped session seconds. There is no separate Simli price; the estimator above turns those seconds into the USD figure the cap already uses.

`GET /api/v1/edition/usage` returns both periods, the allowance, the ratio, and `level`:

| ratio | level | behavior |
| --- | --- | --- |
| under 80% | `ok` | calls proceed |
| 80% to under 100% | `warn` | calls proceed, the card shows the warning |
| 100% or more | `blocked` | heavy work is refused in Spanish; a short chat reply still runs and is counted |

A request is heavy when it is a desk job, a tool call, an image, a generation (`source=generate`), or the user text is longer than `INSTANCE_SHORT_REPLY_CHARS` (default 400). Anything shorter, with none of those, is a short reply.

## Model

Family editions force the selector to MiniMax, model `MiniMax-M3` (`MINIMAX_MODEL` overrides the model id only). Fallback to other providers is off for that process.
