# Marley's mockup miss — Max research/Unsplash path (2026-10-06 ~10:44 PM ET)

## What happened (live session bc8c0f0b)
1. Rafael: "…Best possible solution is a 4 panel basket weave v 8 panel…"
   → live `is_factual_question` True (EVERGREEN matched lone **best**)
   → pre_search ran `web_search` + `web_read` (textile weave / YouTube)
   → Max admitted misroute but still used Verified/Inferred formatting.
2. Rafael: "Show me mick up drwings or something for bisual reference"
   → not factual, but model called `search_images` ×4 (all failed) and still pasted Unsplash sofa URLs + yarn warp/weft lecture.
3. Never called `find_files`. Local assets already on Dell were ignored:
   - `/home/rg/jobs/marleys-hyattsville/comparison-4vs8-2026-10-06/` (PDF + previews)
   - `/home/rg/marleys-hyattsville/site-photos/ref-basketweave-2022.png`
   - `/home/rg/marleys-hyattsville/correct-preview/bw-check/mockup-6.png` etc.

## Root cause (plain words)
Live Max still routes "sounds like a public fact question" into web research, and the tool prompt steers any visual ask to Unsplash. Job context (constructed padded-bar basketweave, 2 pieces = 1 square) loses to textile yarn articles + stock photos. Prior simplify commits (ddf190b0, f06f020a) are on live for self-status/shortcuts, but `answer_policy.py` model-first + job-visual preference had not landed.

## Patch applied (worktree only — NOT live)
Branch: `max/simplify-wip` at `/home/rg/worktrees/max-simplify`
- `factual_guard.py` — job/client terms → INTERNAL; drop lone `best|recommended` from evergreen
- `answer_policy.py` — expand personal/business block; style says find_files for job visuals
- `router.py` — wrap pre_search + post factual auto-web with `should_pre_search`
- `system_prompt.py` + `tool_executor.py` — job mockups → find_files first; no Unsplash for live jobs
- `tests/test_job_visual_no_web.py` — 4 passed against tonight's messages

## Brief gap
`~/empire-data/brain/chief_e_brief.md` mentions Marley's invoices but NOT constructed basketweave / no-web-for-job-visuals. Suggested bullet (do not write live until Rafael yes):
> Marley's (Hyattsville) constructed padded-bar basketweave: 2 pieces = 1 square (V-set / H-set). Job visuals live under `/home/rg/jobs/marleys-hyattsville/` and `/home/rg/marleys-hyattsville/` (comparison-4vs8, site-photos, correct-preview). Never web-search or Unsplash for those mockups.

## Ship rule
Tests on copy only. Live stays on `feature/drawing-standard`. Live tree has unrelated dirty `router.py` — do not merge/reset. Needs Rafael yes + clean cherry-pick/test-copy beat baseline before live.
