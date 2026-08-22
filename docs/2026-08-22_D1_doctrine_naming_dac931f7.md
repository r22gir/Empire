# DOCTRINE.md ADDENDUM — SECTION VII · NAMING AND IDENTIFIERS

**Written 2026-08-22, revised same day (v2 — uniqueness made enforceable
rather than conventional). Supersedes v1; delete v1.** Append to `DOCTRINE.md`
as a new section. Rule numbering continues from 34.

---

## VII · NAMING AND IDENTIFIERS

**35. A round label is globally unique and is never reused.**
On 2026-08-22 two unrelated bodies of work were both called R7: the
FOUNDER_PIN shadow remediation (written into `R5_FIXES_2026-08-22.md` under
the heading "R7 FIX"), and the OpenClaw autopsy dispatched as
`claude_DISPATCH_R7_campaign_engine.md`. **The session was pointed at the
wrong R7 and a round was skipped.** R8 Part 1 did not run.
A label means one thing for the life of the program. Follow-up work extends
the label — R7.1, R7.5 — it never restarts it.

**36. A file's name must not contradict its contents.**
`R5_FIXES_2026-08-22.md` grew to 1,767 lines containing R5, R7 and R7.5. Any
reader searching for the R7 report by filename fails to find it; any reader
opening the R5 file finds three rounds and must guess where one ends.
**One round, one file.**

**37. The name format.**

```
<YYYY-MM-DD>[_HHMMSS]_<ROUND>_<slug>_<h8>.md
```

| field | who supplies it | rule |
|---|---|---|
| `YYYY-MM-DD` | everyone | human ordering |
| `HHMMSS` | **only a writer with a system clock** — M3, scripts, cron | omitted where there is no clock |
| `ROUND` | the issuer | rule 35; unique for the life of the program |
| `slug` | the issuer | lowercase, underscores, human meaning |
| `h8` | **derived, never chosen** | first 8 hex of `sha256sum` of the file's own bytes |

`h8` is the unique id. It is **computed from the file, not invented for it** —
which is the whole point. Any reader can recompute it:
`sha256sum <file> | cut -c1-8`. A name whose `h8` does not match its contents
is a name that has drifted from the file it labels, and that is now a
detectable defect rather than an invisible one.

**Strategic Claude supplies no `HHMMSS`.** It knows the date, not the hour,
and cannot tell ten minutes from ten hours between messages. It supplies the
hash, because a hash is derived from bytes it actually wrote. Asking it for a
timestamp would produce an invented one — the exact failure this file exists
to prevent.

**38. A convention cannot guarantee uniqueness. A ledger and a gate can.**
Rule 37 makes collisions astronomically unlikely; it does not make them
*impossible*, and "unlikely" is the same promise the four hand-maintained
registries made. Make the wrong thing unreachable, not merely discouraged.

- `docs/INDEX.jsonl` — one append-only line per document:
  `{name, round, slug, h8, created, writer, supersedes}`.
- `tools/newdoc.py` allocates every name. It **refuses** if the round label is
  already claimed, or if `h8` already appears. Names are not typed by hand.
- A test in the suite fails the build if: any file in `reports/` or `claude/`
  is absent from the index · any two index entries share a `name` or an `h8` ·
  any file's recomputed `h8` disagrees with its name.

Uniqueness that is not enforced at creation is a habit, and habits do not
survive an agent naming hundreds of files at machine speed from prompt text.

**39. The one exception, and its cost.**
Files born in strategic chat cannot run `newdoc.py` — the tool is on
EmpireDell and the file is not there yet. Those files arrive named per rule
37 with a real hash, and are **adopted into the index on arrival**
(`newdoc.py --adopt <file>`), which re-verifies the hash and rejects a
collision at that moment instead of at creation. **The window between writing
and adoption is the only place a duplicate can exist**, and adoption closes it
before the file is committed. No other exception.

**40. History is not retro-labelled.**
Files committed before this section existed keep their names. The R5 and R7
reports cite each other by their current paths; renaming them breaks those
citations to satisfy a rule written after they were filed. The convention
applies forward from its commit. Rewriting the past to match a present rule is
its own kind of drift.

**41. The scar behind this section.**
Three of 2026-08-22's four naming failures were invisible while they were
happening. Nobody misread anything — the names were wrong. Browser downloads
rename to `(1)` rather than overwriting, and a stale STATE reached the project
that way once already. A convention that lives only in the head of whoever
named the last file is not a convention.
