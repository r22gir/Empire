# SESSION OPENER — paste into a fresh strategic Claude session

Two prompts. Fire OPENER first. Fire the second only after the overnight
checks come back.

---

## PROMPT 1 — OPENER (paste as the first message)

```
Fresh strategic session. Read the project files before responding; what
follows is orientation, not authority — disk wins.

WHERE THINGS STAND
Last session closed 2026-08-22. Pushed to feature/drawing-standard on
~/empire-repo-main: 798c650 (reports/R5_FIXES + R7_CAMPAIGN_ENGINE),
f6dbb9d (docs/ naming doctrine section VII).

PATH DOCTRINE — CORRECTED, SUPERSEDES CLAUDE.md AND STATE.md
~/empire-repo is NOT a stale fork. It was production until the lane moved and
is now FROZEN. It is the MAIN WORKTREE holding the shared git object store at
~/empire-repo/.git; ~/empire-repo-main is a LINKED worktree against it.
Deleting ~/empire-repo destroys both. claude/HANDOFF.md still says
"Eradication is a staged task" — that instruction is now dangerous. CLAUDE.md's
canonical-path paragraph needs the same correction: the RuntimeError
enforcement stays, its stated rationale is wrong. Doc sweep is queued, not done.

DELIBERATE CONFIG DRIFT — DO NOT LET THIS GET LOST
SendGrid: the empty SENDGRID_API_KEY= line is off disk, daemon-reload done,
backend NOT restarted. PID 980291 still holds the empty value and falls
through to SMTP. THE NEXT RESTART OF empire-backend ACTIVATES SENDGRID with
the real 69-char key ahead of SMTP — for any reason, including a reboot.
Founder ruled HOLD on 8/22. Recorded in reports/DECISIONS_2026-08-22.md.
Do NOT fix SendGrid by renaming provider-env.conf to load later: that would
also hand Gemini an invalid AQ.-format key and break scout routing for the
Aria (sales) and Elena (clients) desks.

TWO VERDICTS IN CONFLICT — NEITHER ACCEPTED
On the openclaw_tasks table (7,390 rows; 5,945 failed, 1,443 done):
  - Founder's reading from live error text: provider resolution returns the
    literal string "openclaw" as BOTH provider and model. No real model is
    ever selected.
  - M3's R7 Part 1 reading: reads misclassified into the code-task pipeline;
    the validator at code_task_runner.py:992 correctly rejects them.
M3's own evidence splits the corpus: the 5,504 stale-path failures are all
MAY, reading ~/empire-repo/. The 23 failures on 8/20 read ~/empire-repo-main/
— the NEW path — so they are not stale-path reads and the "dev probe noise"
verdict does not cover them. M3 also filed "why the validator doesn't
recognise read-only task types" under COULD NOT PROBE, then stated the
classifier mechanism as settled in its verdict table. That claim is inferred,
not traced. Treat May and August as two populations until proven one.

DO NOT WRITE A NEW OPENCLAW DISPATCH.
~/Downloads/claude_DISPATCH_R8_openclaw_provider.md ALREADY EXISTS. R8 is the
OpenClaw provider round — it is the round that got skipped when a session was
pointed at R7 by mistake. Two unrelated bodies of work were both labelled R7
on 8/22; that collision is what cost the round. Read R8 before proposing
anything in that lane.

NEW DOCTRINE — SECTION VII, committed at f6dbb9d
Rules 35-41: round labels globally unique and never reused; one round one
file; name format <YYYY-MM-DD>[_HHMMSS]_<ROUND>_<slug>_<h8>.md where h8 is the
first 8 hex of sha256 of the file's own bytes; strategic Claude supplies NO
HHMMSS because it cannot tell time and must not invent one; uniqueness is
enforced by docs/INDEX.jsonl + tools/newdoc.py + a suite test, none of which
exist yet; chat-born files are adopted on arrival; history is not
retro-labelled. Name every file you hand over this way, compute the hash for
real, and tell me the expected value so I can verify it.

QUEUE, IN ORDER
1. Overnight verification (below) — nothing else until it passes.
2. R8 OpenClaw — the existing dispatch, possibly needing an addendum for the
   May/August split and the provider=model finding.
3. Registry census — dispatch already written and downloaded:
   claude_DISPATCH_2026-08-22_registry.md. operating_registry.json knows 7
   modules, nav has 37, plus 14 orphan routers. Founder rulings encoded: MAX
   acts but sends only to founder; per-action gating; email splits into
   inbound/outbound; extend the status vocabulary. The deliverable that
   matters is the validator, not the JSON.
4. Doc sweep — the eradication language, sequenced behind the census because
   the census produces the carrier list.
5. tools/newdoc.py + INDEX.jsonl + the suite test — doctrine exists, mechanism
   does not.
6. H68 founder ruling — still open, still scopes everything in EmpireBox.

HOUSE RULES
Strategic Claude writes paste-ready dispatches; founder pastes into M3 on
EmpireDell; strategic audits the report against the dispatch; founder rules.
Single lane. Map before fix. 🛑 between phases. Files reach the machine by
download, never paste. Founder sends all client communication — never offer
to send, never present sending as an option. Say what you verified vs what you
inferred. A scoped test count is never suite green. Strategic Claude cannot
tell elapsed time between messages.

STANDING SHOP ITEMS — raise these, do not wait to be asked
Willard $1,450 deposit unpaid · CST-23 CO-1 ($7,500 wood-arm scope) void and
unrepriced · R6 holds on three cutting gates (COM leg height, wall-to-wall
width, baseboard height) · Eduardo Arias EST-2026-114 awaiting field
measurements and FR cert · when R6 wraps, remind me to send the material list
for the rolling workbench.
Bozzuto EST-2026-111 is SENT and awaiting response — do not flag it.

FIRST TASK: nothing. Confirm you have read the project files and tell me what
in this brief disagrees with what is on disk. Then wait.
```

---

## PROMPT 2 — AFTER THE OVERNIGHT CHECKS

Run these first:

```
ls -l  ~/empire-repo-main/max/memory.md      # mtime should be after 23:00 8/22
ls -la ~/backups/2026-08-23_0300/            # should exist, non-empty
```

**If either fails**, paste the output and say: *"Overnight verification failed
— this is the top item, everything else waits."* `brain_sync` writes
`max/memory.md` from `scheduler.py:287`; never commit that file.

**If both pass**, paste the contents of
`~/Downloads/claude_DISPATCH_R8_openclaw_provider.md` and say:

```
Both overnight checks passed. Here is the existing R8 dispatch. Tell me
whether it covers (a) tracing where the literal string "openclaw" is returned
as the model, and (b) separating the May population from the August one —
or whether it needs an addendum before it fires. Do not rewrite it if an
addendum will do.
```
