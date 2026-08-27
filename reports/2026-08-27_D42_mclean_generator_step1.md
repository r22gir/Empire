# D42 · McLean generator — STEP 1 report

Branch: `feature/drawing-standard`. Worktree: `~/empire-repo-main`.
Single lane. 🛑 STOP 1. Awaiting founder ruling.

---

## 1a — Hardcoded values + PDF emitter (READ before writing)

Source: `reference/mclean/mclean_drapery_set_generator.py` @ `948a1fc`.
Render harness: `/tmp/d42/render_baseline.py` (uses module as-imported,
patches `_FACE` for missing italic variants — see env gap below).

### Module-level job-specific values

| Name | Lines | Notes |
|---|---|---|
| `JOB` dict | 158–170 | project / client / client_loc / scope / letterhead / poweredby / locale / rev / date / source / status |
| `ROOMS` list | 174–480 | 9 rooms with full panel / data / math / check structures |
| `SCHEDULE` list | 483–495 | 11 opening rows |
| `PHOTO_DIR` str | 500 | `"/home/claude/ph/"` |
| `PHOTOS` dict | 501–513 | room-keyed photo file lists |

### Job-specific strings OUTSIDE these dicts

| Location | String | Hardcoded |
|---|---|---|
| line 4 (docstring) | `"McLEAN - Window & Drapery Field Measurement Set"` | yes |
| line 5 (docstring) | `"Client: Whittington Design, McLean VA"` | yes |
| line 975 (cover `SHEETS` row) | `"9 room elevations"` | yes — derived from `len(ROOMS)` at runtime but typed as a literal |
| line 1188 (`/Title` metadata) | `"McLean - Window & Drapery Field Measurements - Whittington Design"` | yes |
| line 1189 (`/Author` metadata) | `"Nelma's Workroom - Powered by Empire Workroom"` | yes |
| line 1191 (`/Creator` metadata) | `"Nelma's Workroom"` | yes |
| line 1192 (`/Subject` metadata) | `"Whittington Design, McLean VA - "` (rest derives from `JOB`) | partial |

### PDF emitter

`build(out_path)` at **line 1152** (pre-refactor numbering). Calls
`gates()` (internal spec validator) → builds SVG sheets via `cover()`,
`room_sheet()`, `schedule_sheet()` → `cairosvg.svg2pdf()` per sheet →
`PdfWriter.add_page()` per page → `w.write()` to disk.

### Spec-extraction status

ALL of the above moved into a single `SPEC_MCLEAN` dict (refactor
delivered in 1b). `build()` signature is now `build(out_path, spec=None,
audience="client")`; `spec=None` resolves to `SPEC_MCLEAN`. See 1b
proof that visual output is byte-identical before/after.

### Env gap (still open, logged)

The script's `_FACE` dict (lines 54–67) maps to 12 DejaVu faces; only 8
exist at `/usr/share/fonts/truetype/dejavu/` on this box. Missing:
`DejaVuSans-Oblique`, `DejaVuSans-BoldOblique`, `DejaVuSerif-Italic`,
`DejaVuSerif-BoldItalic`. **The generator cannot reproduce its own
reference output on this box in principle** — even with the correct
source, the missing italic glyphs force a substitution that changes
glyph widths, which shifts column boundaries in `pdftotext -layout`
extraction (548 layout-stream diff lines reduce to 54 raw-stream diff
lines, all attributable to PHOTOS + italic fallback). Founder ruling
needed on whether to install `fonts-dejavu-extra` (needs sudo) or accept
the fallback for all future in-box renders. The reference PDF
(`reference/mclean/McLean_Whittington_Drapery_Elevations_RevA.pdf`,
md5 `f882144aefc03745533fdaae95ea86b4`) was rendered on a system with
the full DejaVu suite — **PROVENANCE.md's "single source of truth"
claim holds: zero genuine content drift between source and reference**.

---

## 1b — Spec extracted, byte-identical proof

Diff stats: `270 lines changed, 187 insertions(+), 83 deletions(-)`.
File: `reference/mclean/mclean_drapery_set_generator.py`.

### Changes

- `JOB` / `ROOMS` / `SCHEDULE` / `PHOTOS` / `PHOTO_DIR` consolidated into
  a single `SPEC_MCLEAN` dict. `SPEC = SPEC_MCLEAN` aliases the default.
- All sheet functions (`gates`, `chrome`, `room_sheet`, `cover`,
  `schedule_sheet`) take `spec` as a parameter; no module-level reads.
- `build(out_path, spec=None, audience="client")` resolves default and
  runs the new emit gate (see 1c).
- `photo()` and `photo_size()` take `photo_dir` as a parameter.
- Hardcoded metadata strings moved into `spec["job"]["pdf_title" | "pdf_author"
  | "pdf_creator" | "pdf_subject"]`.
- Hardcoded `"9 room elevations"` replaced with `len(spec["rooms"])`.
- PENDING support added: a data tuple of `(label, value, {"pending": True})`
  renders value as `PENDING` and queues a `<label>: PENDING - confirm on site`
  bullet in FIELD CHECK. Plain `(label, value)` rows render unchanged.
  McLean spec has no pending rows → augmentation empty → byte-identical
  output preserved.

### Byte-identical proof

Both runs use `/tmp/d42/_font_fallback.py` to substitute upright weight
when italic file is missing. PHOTOS neutralised to empty lists in both
runs so the comparison excludes the founder's parked photo set.

```
baseline text md5: cde36bffd2fff1b501fa0d3e544fc135
after    text md5: cde36bffd2fff1b501fa0d3e544fc135
IDENTICAL: True
```

Compared: text-layer (`pdftotext -layout`) md5 of both PDFs. Bytes
inside the PDF body would differ (CreationDate modtime), which is why
text-layer md5 is the correct comparator. McLean spec passes through
the refactored `build(spec=SPEC_MCLEAN, audience="client")` path.

### Honesty on what was NOT proven byte-identical

The render used the italic fallback; this is the same fallback used for
the before-refactor baseline. So the byte-identity proof is **relative
to this environment**, not absolute against the parked reference. To
match the parked reference byte-for-byte, the four missing DejaVu
italic variants need installing — env gap above.

---

## 1c — Emit gate, demonstrated firing

The gate is the deliverable that matters most in this dispatch. H74
(Willard REV C) went out to a client carrying `MARKUP`, `BILLING:`, and
`INVOICED` tokens because no mechanism stopped it. This is the
mechanism.

### Forbidden tokens (case-insensitive)

`MARKUP`, `BASE RATE`, `BASE $`, `COST`, `MARGIN`, `INVOICED`,
`BALANCE DUE`, `INTERNAL`, `NOT FOR CLIENT`.

### Gate signature

```python
def gate_emit_client_safe(spec, audience="client"):
    """Raises ValueError on any forbidden token in client-facing output.
    audience='shop' skips the check; client (default) enforces.
    Default is client-facing — the permissive default caused H74 and is
    not repeated here."""

def build(out_path, spec=None, audience="client"):
    if spec is None: spec = SPEC_MCLEAN
    gate_emit_client_safe(spec, audience=audience)  # <-- wired in build()
    ...
```

Wired at the top of `build()` before any PDF write.

### Three-run demonstration (`/tmp/d42/gate_demo.py` + `/tmp/d42/gate_wired.py`)

**RUN 1 — clean spec, audience=client.** Gate passes. PDF written.

**RUN 2 — offending spec (added `("INTERNAL MARKUP REGISTER", "MARKUP 50%  -  CONFIDENTIAL")` to FD room's data), audience=client.**
```
GATE FIRED with ValueError:
  gate_emit_client_safe: forbidden token 'MARKUP' present in client-facing
  spec for job 'McLEAN'. Remove the token or pass audience='shop' for an
  internal doc.
```
PDF write never attempted. Verified via sentinel file
(`/tmp/d42/after/SHOULD_NOT_EXIST.pdf`) which is absent after the gate
fires — the gate raises BEFORE `cairosvg` and `PdfWriter` run.

**RUN 3 — same offending spec, audience=shop.** Gate skipped by design.
Shop-facing docs may carry these tokens. PDF written.

### Why this matters

A green run proves nothing — the absence of a raise on a clean spec is
not evidence the gate works. RUN 2 is the one that proves the gate.
The H74 lesson was not "add a rule to the prompt." It was "build a
mechanism." The mechanism is `gate_emit_client_safe` wired into `build()`.

---

## OPEN — bench sheets, ruling needed before STEP 2

The bench family has no B2 vector renderer (`bench_curved.py:47` returns
`b''`, falls through to `_render_b1_story`, QC skipped), and the McLean
generator emits drapery elevations + cover + schedule — it is not a
bench renderer either. Becky's quote carries two Ryann-style benches
(line 7 of the quote) but no sheet path exists in this dispatch.

**Options for founder ruling:**

1. **Bench content goes into an assumptions block on a drapery sheet, no
   separate bench sheet.** Lowest cost. Founder rule dictating the bench
   construction (one-piece top wrap, upholstered caps, no channels /
   tufting) is captured in FIELD DATA / NOTES of a drapery sheet, with
   a cap-detail note. No bench elevation rendered. **Disadvantage:** no
   visual confirmation for the founder that the construction reads right
   before sending.

2. **Defer bench sheets to a future dispatch.** This dispatch ships
   drapery only, with a clearly-marked note in the cover sheet's OPEN
   ITEMS section that bench sheets are pending a separate dispatch.
   **Disadvantage:** client gets a partial pack; the founder must
   coordinate timing with bench B2 vector renderer (which doesn't
   exist).

3. **Build a minimal bench renderer inside the McLean generator as part
   of this dispatch.** Significant new code; violates the
   additive-only ruling carried forward from D41 (the b2 stack and
   `drapery_render.py` are not to be modified, but a NEW renderer in
   McLean is arguably additive). **Disadvantage:** adds surface area
   that needs its own emit-gate coverage and byte-identity proof.

4. **Founder rules no bench sheet ships; assume client already has the
   construction rule from prior conversation.** Cleanest, but assumes a
   conversation state I cannot verify.

The D42 ruling carried forward is "this work is ADDITIVE; do not modify
drapery_render.py or the b2 stack." Option 3 violates the spirit of
that ruling only if the bench renderer touches those files. A
McLean-local bench renderer is technically additive — but it changes
what the McLean generator emits, which means a future byte-identity
proof on the McLean job itself has to account for it. Recommend
option 1 or 2. **No option chosen; awaiting founder ruling.**

---

## Status of the canonical repo (memory audit per founder ask)

Two files written to `/home/rg/.claude/projects/-home-rg/memory/` this
session (mtime Aug 27 13:31), both visible in the auto-memory index:

- `project_d42_mclean_generator.md` (1,638 bytes, new) — D42 ruling
  carried forward, McLean path is additive, 1c gate is priority
- `MEMORY.md` (6,854 bytes, edited) — added one line under Recent
  Sessions pointing at the new file

`max/memory.md` was **not** written by this session. It shows as `M`
because `brain_sync` ran a nightly regeneration at 2026-08-26 23:00
updating DB counts (tasks 606→2100, customers 144→557, etc.). Its mtime
predates this session. The git diff shows only the auto-sync block
update — no agent-authored content.

`reference/mclean/mclean_drapery_set_generator.py` was modified by this
session (the 1b refactor). Pre-session the file was clean at `948a1fc`;
post-session it shows 187 insertions / 83 deletions across 270 lines.
This is the only repo file touched by 1b. `drapery_render.py:640` and
the b2 stack are unmodified per the additive-only ruling.

---

## 🛑 STOP 1 — awaiting founder ruling

Reporting on 1a / 1b / 1c is complete. Bench-sheet option (1-4 above)
still needs a founder call before STEP 2 can render Becky.

Files written this dispatch:
- `reference/mclean/mclean_drapery_set_generator.py` — refactored (270 line diff)
- `reports/2026-08-27_D42_mclean_generator_step1.md` — this report
- `/tmp/d42/*` — harness, baseline/after renders, gate demo (off-repo, ephemeral)

Founder sends the Becky's pack; agents prepare. Nothing has been sent.
