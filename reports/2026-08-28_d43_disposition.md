# D43 · Disposition (founder rulings executed) — 2026-08-28

Resolves the three OPEN rulings from
`reports/2026-08-27_d43_step2.md` §OPEN.

---

## R1 — Archive the stale-tree files ✅

`~/empire-repo-main/backend/data/vision_inputs/` (162 files at archive
time, 163 by mtime accounting) moved to:

```
~/empire-repo-main/backend/data/vision_inputs.stale-2026-08-28/files/
```

The original `vision_inputs/` directory was removed (was empty after the
move). The archive directory contains:
- `files/` — all 163 original files, untouched (md5-preserved)
- `NOTES.md` — breadcrumb explaining what is in here and why

`backend/.gitignore` updated to ignore the archive directory so the
~14 MB of binary evidence does not enter git. Source code, tests, and
this report remain git-tracked.

The cache of canonical fake-shape source: the 146 136-byte files all
md5 to `15fe71a9789c5579a89bb6d83e253610` — byte-identical to the
fixture defined at `tests/test_vision_mmx_cli.py:12,17` (now gated
behind `EMPIRE_VISION_TEST_BAD_PAYLOAD_ALLOWED`).

## R2 — `.EVIDENCE` rename the 2 live fakes ✅

Two files in the live data root
`/home/rg/empire-data/vision_inputs/`:

| Old | New |
|-----|-----|
| `vision-input-1782445148-6008b80e.png` | `vision-input-1782445148-6008b80e.EVIDENCE.png` |
| `vision-input-1782445277-47e8091c.png` | `vision-input-1782445277-47e8091c.EVIDENCE.png` |

Both are 60 bytes of literal `X` characters, identical md5
(`5b29c5fd3fab5494f9825323a320418f`), written 2026-06-25 23:39 and 23:41
EDT — a **different writer** than the stale-tree's PNG-magic+128-'x'
fixture (different shape entirely; 60 chars of literal uppercase X, no
PNG header at all). They sit untouched and clearly marked.

The live data root was determined by:
- `cat /proc/<empire-backend-pid>/environ | grep EMPIRE_DATA_DIR`
  → `EMPIRE_DATA_DIR=/home/rg/empire-data`
- `data_root()` at `services/data_paths.py:16` honors that env var
- the running empire-backend (PID 1786099, restarted 2026-08-27 21:00:52)
  wrote to `/home/rg/empire-data/vision_inputs/`

## R3 — Re-scope the re-render audit to the 2 live fakes ✅

The "10 weeks of vision-derived claims" framing from the dispatch
evaporates. The stale-tree writes were at an un-`EMPIRE_DATA_DIR`'d path
used by a backend process that is no longer active. They never reached
the live data root and never reached a downstream quote in the current
canon.

The re-render audit is now bounded by:
- The 2 `.EVIDENCE.png` files (60 bytes each, 2-minute window on
  2026-06-25 23:39–23:41 EDT)
- Any MAX output that consumed those 2 files (if any)

How to enumerate such output:
- The 2 files were written by direct HTTP POST to `/api/v1/vision/*`
  (the runner-id pattern fits a logged-in session, not a script — body
  had no PNG magic so the magic-byte check at line 158 raised 400
  *before* STEP 1a — the file was never actually written down the
  decode path; they took a fallback write path. That fallback is no
  longer reachable.)
- Any MAX chat that received a citation referencing these 2 file IDs
  in window 23:39 → 23:41 → 00:30 EDT
- Any quote_v2 row that incorporates a measurement whose source image
  has a hash matching one of the 2 file md5s

The first round of the audit finds nothing — no quote from that
window references these files. The cost is bounded, even if a future
round finds something: scope is at most 2 minutes of MAX chat and
zero quote rows.

---

## R4 — 24-hour writer watch → ship ✅ in progress

Per the dispatch OPEN hypothesis:
> "After 1a the posts will start failing with a 4xx, which will make the
> caller visible in the journal — but it is a founder ruling, not an
> assumption to build on."

**24-hour window**: 2026-08-27 21:08 EDT → 2026-08-28 21:08 EDT.

**Observations during the window**:

The current check (2026-08-28 17:40 EDT, ~3.5 hours before window close):
- Zero `POST /api/v1/vision/*` in `journalctl --user -u empire-backend`
  for the entire window (only the curl smoke-tests of D43 itself at
  21:01–21:08 yesterday).
- Zero new files in either `vision_inputs/` path.
- The 2 fake write paths are both **silent** since 21:00:52 EDT
  yesterday — both on the stale tree (which is now archived) and on the
  live data root.

**Implication**: either the writer is gone or it has stopped firing. If
the writer has stopped firing because STEP 1a made all its downstream
work unhealthy and it killed itself, we won't see it in the journal —
we'll just see silence. That is acceptable for the D43 charter:

> "If 24 hours pass without a 4xx surfacing the caller, ship as-is,
> accept the writer is unknown."

**Action at window close** (2026-08-28 21:08 EDT): commit the D43 work
on `feature/drawing-standard`. No push (per CLAUDE.md). The 1a guard
remains in place. If the writer resurfaces after shipping, the 4xx in
the journal will surface the caller at that time.

## Files changed in this disposition

| File | Change | Purpose |
|------|--------|---------|
| `~/empire-repo-main/backend/data/vision_inputs/` | directory removed | clear the stale path |
| `~/empire-repo-main/backend/data/vision_inputs.stale-2026-08-28/files/` | 163 files moved in | evidence archive |
| `~/empire-repo-main/backend/data/vision_inputs.stale-2026-08-28/NOTES.md` | new file | breadcrumb for future self |
| `~/empire-repo-main/backend/.gitignore` | +6 lines | ignore the archive in git |
| `reports/2026-08-28_d43_disposition.md` | this file | ruling-execution record |
| `~/.claude/projects/-home-rg/memory/...` | (later) | save the 24h-check lesson |

## Open after this disposition

- The writer identity remains unknown.
- STEP 1a's guard is in place; if the writer resumes, the next 4xx in
  the journal names the source.
- The 24-hour window ends at 2026-08-28 21:08 EDT. After that, commit
  on `feature/drawing-standard`.

(no actions by me until the window closes; the auto-check fires at
21:08 EDT.)
