# NEXT SESSION — OPENING PROMPT

Paste the fenced block below as the FIRST message of a fresh strategic Claude
session, with the project files attached as usual.

---

```
Fresh strategic session, continuing EmpireBox.

READ FIRST, in this order, before responding:
  1. claude/2026-08-24_D21_handoff_session_859d1fdb.md  ← the full handoff
  2. CLAUDE.md — but see the corrections in §"CORRECTIONS THAT SUPERSEDE
     CLAUDE.md" of the handoff. Acting on the stale claims is dangerous.
  3. docs/2026-08-23_D12_history_email_record_v2_0d35af52.md — the project's
     history. Read it before forming judgments about MAX. The last session ran
     eleven rounds before reading it and built a defect-shaped picture as a
     result.

Branch feature/drawing-standard, HEAD c1b43ed, everything pushed.

THE THREE THINGS THAT MATTER MOST, from the handoff:

1. ~/empire-repo is NOT a stale fork. It is the MAIN WORKTREE — it owns the shared object store and still receives data writes under backend/data/ holding
   the shared git object store. Deleting it destroys every local branch and
   stash. The D21 handoff no longer carries "Eradication is a staged task";
   see CLAUDE.md's "OPEN HAZARD (H73)" note — the path-doctrine enforcement
   is unsafe until H73 closes, its rationale is wrong even where it is right.
   The doc sweep is still not done.

2. My actual goal: dispatches that run unattended and email me when they hit a
   decision. Executor works, outbound works, inbound works as of yesterday,
   remote oversight works. TWO things remain — persistence (the code-task path
   keeps state in an in-memory dict lost on every restart, R11 §13, ~80 lines)
   and the park-and-ask primitive. Everything else in the queue is downstream
   of those.

3. The pattern behind most of the defects: a surface that reports more
   confidence than it has. The morning brief frozen at "194 items" for eleven
   weeks, the Verified badge, the hardcoded date stamp, H68. The honesty layer
   was built in February for the model's OUTPUT and has never been applied to
   the system's own REPORTING surfaces.

HOW WE WORK: you write paste-ready dispatches, I paste them into MiniMax-M3
Claude Code sessions on EmpireDell, M3 reports, you audit the report against
the dispatch, I rule. Single lane. Map before fix. 🛑 between phases. Files
reach the machine by download, never paste — name them per doctrine §VII
(<YYYY-MM-DD>_<ID>_<slug>_<h8>.md, h8 = first 8 hex of the file's own sha256,
computed for real, never invented). You cannot tell elapsed time; do not
supply timestamps.

I send all client communication. Agents draft; I send. Never offer to send.

WHEN AUDITING M3: always demand the pre-change test baseline FIRST — the suite
sits at ~104 pre-existing failures and a post-change count means nothing
without it. When a guard is added, demand proof it CATCHES, not just that it
passes. Watch for tests edited to tolerate failure, mechanisms filed under
COULD NOT PROBE and then asserted in a verdict table, and summary tables that
contradict their own prose. All three have happened.

DISPATCHES WRITTEN AND WAITING (read the dispatch, not the summary, before
firing):
  R13   claude/2026-08-23_D15_dispatch_r13_woodwork_port_213bac7a.md
  R14v2 claude/2026-08-23_D18_dispatch_r14v2_document_catalogue_2a365bbb.md
  R15   claude/2026-08-23_D17_dispatch_r15_sourced_knowledge_37ac04a3.md
  R16   claude/2026-08-23_D19_dispatch_r16_woodcraft_products_696f80bf.md

STANDING CLIENT ITEMS — raise these, don't wait to be asked: Willard $1,450
deposit unpaid · CST-23 CO-1 ($7,500) void and unrepriced · R6 holds on three
cutting gates (COM leg height, wall-to-wall width, baseboard height) · Eduardo
Arias EST-2026-114 awaiting field measurements and FR cert. Bozzuto
EST-2026-111 is SENT — do not flag it.

FIRST TASK: nothing. Confirm you have read all three documents, then tell me
what in the handoff disagrees with what is on disk — CLAUDE.md and STATE.md
both still carry claims the handoff corrects, so there WILL be disagreements.
Then wait for my ruling on what to run.
```

---

## WHAT TO ASK FOR AFTER THAT

Pick one. The first is the one that unlocks the rest.

**A · Persistence + park-and-ask** — the two rounds that make everything else
run without you. Say: *"Write the persistence round. R11 §13 scoped it at ~80
lines. Then the park-and-ask primitive on top of it."*

**B · The drawing layout decision** — R12 stopped on seven open issues, two of
which need your eye with the golden reference in hand: the viewport that cannot
hold a wide shade, and the Drapery `pinch_pleat` fold-pattern bug computing
0.007" where 0.944" is expected. Also still unaddressed: your note that the
dimension numbers must be larger and the lines heavier.

**C · R14 v2 — the document catalogue.** Renders one of every document type,
including quotes and invoices, so you can see in an afternoon which are
client-ready. Its Phase 0 also sweeps the box for more delivered work outside
git.

**D · The tools-accuracy pass** — the frozen 194, the pairing card pointing at
a dead LAN address, the disk figure that disagrees with itself across two
pages, dead port probes. Productization, not hygiene: these are what a customer
sees on day one.

**E · Token rotation** — owed since June. The inbox holds nine credentials in
plaintext including the opencode password emailed on 8/22.

My read: **A**, then **C**. A makes the queue self-running; C tells you what
you actually have to sell.
