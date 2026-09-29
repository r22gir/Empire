# DECISIONS — 2026-08-22

Lands at `reports/DECISIONS_2026-08-22.md`. Commit with the next push.

---

## D1 · SENDGRID — HOLD, DO NOT RESTART TO ACTIVATE

**Ruled by founder 2026-08-22: hold.**

State as of tonight — **disk and process disagree deliberately**:

| | value |
|---|---|
| `empire-backend-smtp.env` | empty `SENDGRID_API_KEY=` line REMOVED (285 → 267 bytes) |
| Backup | `~/backups/20260822/empire-backend-smtp.env.pre-r7-fix.20260822_152120` |
| `daemon-reload` | done |
| Restart | **NOT done** — PID 980291 still holds the empty value |
| Live behaviour | `_sendgrid_configured()` False → falls through to SMTP. Unchanged. |

**What the fix actually accomplished:** it removed the *silent-override
landmine*. Before, a real key added to `empire-backend.env` would have been
shadowed to empty by `smtp.conf` loading later, and future SendGrid
provisioning would have failed silently with no signal. That is closed.

**What was deliberately NOT done:** activating SendGrid. That is a separate
decision.

⚠️ **THE NEXT RESTART OF `empire-backend` ACTIVATES SENDGRID** — for any
reason, including an unrelated restart or a reboot. `SENDGRID_API_KEY` will go
from empty to the real 69-char key in `empire-backend.env`, and
`sender.py:147-150` will try SendGrid FIRST, with SMTP as fallback. The first
real outbound email is the test of whether that key is valid.

**Before the next restart, decide:** activate on purpose (and send one internal
founder-address test immediately after), or re-suppress by putting an explicit
`SENDGRID_API_KEY=` back with a comment saying it is intentional.

This is H61's shape — config on disk differs from config in force. The
difference here is that it is intentional and written down. That is the only
thing separating it from the nine unintentional instances.

---

## D2 · GEMINI — NO ACTION, VESTIGE CONFIRMED

`gemini.env` holds an `AQ.`-format server token (mtime 2026-05-31), superseded
by the `AIza` key in `empire-backend.env`. Merge order already favours the
valid one. `gemini.conf` is dead weight; retiring it is optional and has no
urgency.

⚠️ **Do not rename `provider-env.conf` to load later** (e.g. to
`zz-provider-env.conf`). That was floated as one way to fix SendGrid. It would
also hand Gemini the invalid `AQ.` key and break scout routing for the Aria
(sales) and Elena (clients) desks. The SendGrid fix was correctly done at the
env-file level instead.

---

## D3 · OPENCLAW — TWO VERDICTS IN CONFLICT, NEITHER ACCEPTED

Founder's reading (from live error text): provider resolution returns the
literal string `openclaw` as BOTH provider and model — no real model is ever
selected.

M3's R7 Part 1 reading: reads are misclassified into the code-task pipeline and
the validator correctly rejects them.

**Neither is accepted yet, because M3's own evidence splits the corpus:**

- The 5,504 stale-path failures are **May**, reading `/home/rg/empire-repo/`.
- The 8/20 failures read `~/empire-repo-main/` — the NEW path. They are not
  stale-path reads, so the "dev probe noise" verdict does not cover them.
- M3 lists *"why the validator doesn't recognize read-only task types"* under
  **COULD NOT PROBE**, then states the classifier mechanism as settled in its
  verdict table. The routing claim is **inferred, not traced**.

Next dispatch resolves this: trace where the literal `openclaw` string is
returned as the model, and treat May and August as two populations until proven
one.

---

## D4 · OVERNIGHT VERIFICATION — RUN FIRST TOMORROW

```
ls -l  ~/empire-repo-main/max/memory.md      # mtime should be after 23:00 8/22
ls -la ~/backups/2026-08-23_0300/            # should exist, non-empty
```

`brain_sync` at 23:00 and first canonical backup at 03:00 are both unverified.
If either fails, that is the top item and everything else waits. Never commit
`max/memory.md`.

---

## STATE AT CLOSE

```
Pushed:    798c650 (reports/R5_FIXES + R7_CAMPAIGN_ENGINE) on feature/drawing-standard
Backend:   ACTIVE, PID 980291, NOT restarted
Portal:    ACTIVE, HTTP 200
OpenClaw:  ACTIVE, untouched
Terminal:  safe to close — nothing held by the session
```

## QUEUE

1. **OpenClaw dispatch** — provider-resolution trace + May/August split. Moved
   ahead of the registry: two contradictory verdicts on the same table should be
   settled before further mapping work depends on what the machine reports.
2. **Registry census** — dispatch written, `claude_DISPATCH_2026-08-22_registry.md`.
3. **R8 Part 1** — never fired; the session was pointed at R7 by mistake.
4. **Doc sweep** — `~/empire-repo` eradication language in `claude/HANDOFF.md`
   and CLAUDE.md's canonical-path paragraph. Sequence behind the census, which
   produces the carrier list.

## STANDING SHOP ITEMS

Willard $1,450 deposit unpaid · CST-23 CO-1 ($7,500 wood-arm scope) void and
unrepriced · R6 holds on three cutting gates (COM leg height, wall-to-wall
width, baseboard height) · Eduardo Arias EST-2026-114 awaiting field
measurements and FR cert.
