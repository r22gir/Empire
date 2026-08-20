# M-LANE — MAX CLIENT-WORK CAPABILITY

**Founder directive 2026-08-19:** *"I will handle direct communications. MAX
has to be trained and has to know how to handle this."*

Append to `claude/BACKLOG.md` as a new lane. This is the capability spec for
the handoff goal recorded in STATE v7.

---

## THE BOUNDARY — a role, not a prohibition

The register currently frames §9 CLIENT-FACING as *"founder actions, no
automation ever."* **That framing is now wrong and should be replaced.**

**New framing: FOUNDER SENDS · MAX PREPARES.**

The allowlist stays structurally founder-only — `send_email` must remain
incapable of reaching a client address, and no fix in this lane may weaken
it. What grows is everything *behind* the send: knowing the job state,
producing the artifact, knowing what is missing, drafting the message.

The distinction matters because a prohibition tells MAX what not to do and
teaches him nothing. A role tells him what the work is.

---

## PREREQUISITE — the senses come first, no exceptions

**None of M1–M5 can be built on an agent that cannot see.** Training on top
of broken senses produces a confident agent working from bad inputs, which is
worse than an agent that refuses.

Blocking, in order:
1. **H53** — he cannot hold a thread while his own context lies to him
   (reproduced live 8/19: could not distinguish founder authorization from
   injected replay scaffolding)
2. **H57 Phase 3** — canonical root; he cannot read the repo, and cannot
   tell a canonical tree from a stale fork
3. **H57 Phases 1–2** — the door; messages containing "drawing" never reach
   him at all
4. **H55** — founder-attested provenance; only meaningful once H53 makes the
   founder's words legible again

---

## THE LANE

| ID | Item | Depends on | Status |
|---|---|---|---|
| **M1** | **Read job state.** Which quotes are approved and unsent · which are blocked and on what · what is missing before a document can be produced · what has been sent and when. Through the shared canonical resolver, never a copy | Senses · shared `resolve_quote()` | NOT STARTED |
| **M2** | **Produce the artifact.** Call the document template engine for any of the five types. One service layer — MAX is ONE DOOR, same `build(spec)` the portal and quoting system call | P1-T·c + ·g | Engine in flight |
| **M3** | **Know what is missing and ask for it.** `SpecIncomplete(missing=[...])` becomes a question in his own voice, in context — not a raw field dump | P1-T·c | Interface being built now |
| **M4** | **Draft the message, never send.** Founder-to-send drafts in house voice. Model exists: the INOUYE reply draft to Jaye Langmaid | M1 · M2 · M5 | NOT STARTED |
| **M5** | **Hold the house voice.** "Cove fascia" never "cove trim"; "affixed / set / fit" never "glued"; no mitre references; no "bookshelf"; stiles run through, bands butt | — | ⚠️ See open question |
| **M6** | **Surface capability health proactively.** Token expiry, store reachability, tool availability — on the truth banner, BEFORE a client is waiting. I13 was discovered when a real client email could not be read | Senses | NOT STARTED |

---

## ⚠️ OPEN QUESTION — M5 contradicts doctrine rule 33

`DOCTRINE.md` rule 33 states: **the house voice belongs to the specialist, not
the orchestrator.** MAX says "produce the client pack"; the specialist knows
how to speak.

That rule was written when MAX's role was to delegate. **If MAX drafts
client-facing prose himself, he needs the voice** — and rule 33 either gets
an exception or gets revised.

Two coherent answers, founder's call:
- **(a)** MAX drafts, so MAX carries the voice. Rule 33 narrows to *generated
  documents* — where `client_pack.py` owns the language — and excludes
  correspondence.
- **(b)** A drafting specialist owns correspondence voice too, and MAX
  delegates to it. Rule 33 stands unchanged.

**(b) is more consistent** with everything else built here — one place per
concern, no capability duplicated across doors. **(a) is simpler** and ships
sooner. Do not resolve this by drifting into whichever is convenient at the
time; it is a doctrine decision.

---

## PER-JOB SPEC — what "prepare" means concretely

The current four client jobs, expressed as what MAX must be able to do. These
are the training targets, not tasks to dispatch.

**Bozzuto EST-2026-111** — recognise a quote as approved-and-unsent, surface
it unprompted with its age, assemble the package, draft the transmittal with
the deposit ask, hand it over. **Also flags V5**: the portal reads Accepted
Quotes = 0 while this quote was approved through the PIN modal — MAX reading
job state correctly would have caught that discrepancy.

**McLean / Whittington (C7)** — hold a measurement set at REV state, know
which openings are unresolved, produce the reissue through the template
engine, know whether a prior rev went out (REV A reissue vs REV B), and state
the count change in the transmittal.

**Hudson & Crane (INOUYE)** — hold two quotes with five open blockers, know
that one number (drapery rod/opening width) gates all yardage, know which
blockers need a human phone call (Fabricut 403s automated fetch) versus a
client answer, and draft the ask in the order the client asked. **Also flags
V7**: EST-2026-113 exists as a PDF and never entered the canonical store.

**R6 / WoodCraft** — hold three cutting gates and one unanswered shop
question, and refuse to produce a cut list until they clear. This is
`SpecIncomplete` applied to fabrication rather than documents.

---

## ACCEPTANCE — how we know he can do it

Not a demo. Two tests with answer keys fixed in advance:

1. **The audit test** (already staged, BACKLOG item 12): MAX reads the R3
   dispatch and `fc42fe3` from the repo himself and reports what is
   unaccounted for. Answer key was published before the test existed — the
   two real defects are the unprinted grommet/rod_pocket ASSUMED constants
   and the half-built fabric model.
2. **The job-state test:** asked "what is waiting on me?", MAX returns the
   approved-and-unsent quotes, the blocked jobs with their specific blockers,
   and says plainly what he could not verify. Scored the same way: finding
   the real items, distinguishing verified from inferred, and naming what he
   does not know.

**Failure modes to watch for, both already observed in this system:**
- Asserting job state he did not verify (the thing the honesty layer exists
  to prevent — it has held so far)
- Refusing everything because provenance is unclear (H55; honesty that
  blocks all work is a different failure, per doctrine rule 34)

---

## WHAT ALREADY WORKS — do not rebuild it

Observed live 2026-08-19 under real pressure: four consecutive refusals to
fabricate, no invented tool runs, no claimed access he lacked, and an honest
*"I don't know where that belief came from"* when challenged on a wrong repo
path.

**That is the expensive part and it is done.** This lane adds sight and
scope. It must not cost honesty — any change here that makes fabrication
easier is a regression regardless of what capability it buys.
