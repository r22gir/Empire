# DOCTRINE.md ADDENDUM — SECTION VIII · CODE BORN IN CHAT

**Written 2026-08-23. Earned the same day.** Append to `DOCTRINE.md`. Rule
numbering continues from 41.

---

## VIII · CODE BORN IN CHAT

**42. Code born in a strategic session is committed the same day, or it does
not exist.**
On 2026-08-23 a search established that five working generators — `arch.py`,
`client.py`, `present.py`, `shop.py`, `lab.py` — appeared **nowhere on disk and
nowhere in git history.** Zero commits on 2026-08-18. Zero hits for `walnut`,
`sofa surround`, `WoodworkSpec`, `R6-CLIENT-PACK`. They had produced a
**delivered client document** — the R6 REV G pack, seven sheets, $2,390.80 —
and they survived only inside a chat log.

The same day, four more untracked generators were found loose in `~/Downloads`:
`drawing_set_generator.py`, `label_generator.py`, `willard_drawing.py`, and a
7/31 session summary. All had produced real work. None was in git.

**`~/Downloads` is a staging area, not storage.** It gets cleared.

**43. The documentation survived and the code did not.**
`EMPIRE_CLIENT_DOC_STANDARD.md` was written, amended eight times, and
committed. `claude_DISPATCH_2026-08-18_woodwork_presentation.md` was written and
committed. Both describe the five generators in detail — signatures, line
counts, hand-verified fixtures. **Neither contains the code.**

A dispatch that says *"attached separately"* is a record of an intention. It
reads exactly like a record of a fact, and it was read that way — by strategic
Claude, on this date, before the search was run. That is §3.2 of the June
ecosystem assessment recurring inside the correction process itself.

**44. An artifact is not evidence that its source exists.**
A delivered PDF proves a generator ran once. It does not prove the generator is
anywhere. Before planning a refactor of code, confirm the code is on disk —
`ls`, not inference from a document about it.

**45. What the rule requires, concretely.**
- A strategic session that produces runnable code ends with that code committed
  under `reference/` on `feature/drawing-standard`. Not attached. Not
  downloaded. Committed.
- Filenames follow §VII. The founder verifies the hash on arrival.
- A dispatch that references source files states their **committed path**, not
  "attached separately." If there is no committed path, the dispatch is not
  ready to fire.
- `.gitignore` patterns are checked against what they will actually exclude.
  `reference/**/*.pdf`, added on 2026-08-22 to keep one 14 MB binary out,
  silently excluded a REV G power guide the next day. The commit reported
  success and landed one fewer file than it named.

**46. The scar behind this section.**
Nine generators, every one of which produced work a client received, spent
weeks in a Downloads folder and a chat history. Recovering them took an
afternoon and depended entirely on the founder still having the conversations
open. The next agent will produce code faster than any human reviews it. If
"where does the code live" is answered by a habit rather than a rule, the
answer will eventually be "nowhere."
