# MAX Whitespace Streaming Fix (Stable)

Date: 2026-05-14

## First Bad Stage

- Lane: `stable` (`localhost:8000`)
- First bad stage: backend stage 2 (`sanitize_output` on streaming chunks)
- Proven symptom (pre-fix): chunk join produced merged words like `The useris ...` because leading/trailing chunk whitespace was stripped before SSE emit.

## Root Cause

`/api/v1/max/chat/stream` sanitized each partial chunk with `sanitize_output`, which called `strip_reasoning_tags(...).strip()`.  
When a chunk started with a boundary space (for example `" is asking"`), `.strip()` removed it, so concatenation merged words.

## Fix

1. Added streaming-safe sanitizer in [backend/app/services/max/guardrails.py](/home/rg/empire-repo/backend/app/services/max/guardrails.py):
   - `strip_reasoning_tags(text, trim_edges=False)` support
   - `sanitize_output_streaming(...)` that preserves chunk-edge whitespace
2. Updated stream path in [backend/app/routers/max/router.py](/home/rg/empire-repo/backend/app/routers/max/router.py) to use `sanitize_output_streaming` for streamed text chunks.
3. Added direct provider-identity route for:
   - `what ai?`
   - `what model are you using?`
   - `who powers you?`
   so stable answers match live `/api/v1/max/status` provider policy.

## Affected Lanes

- Stable/main: fixed.
- v10/test: whitespace issue not reproduced in current local backend stream path (already streaming-safe), but provider-identity route parity added.

## Verification Summary

- Backend non-streaming (`/max/chat`): spacing normal.
- Backend raw SSE (`/max/chat/stream`): boundary spaces preserved post-fix.
- Browser (`http://localhost:3005/max`): normal spacing in new timestamped responses; no merged-word artifacts from chunk boundaries.
- Public:
  - `https://test-studio.empirebox.store/api/v1/max/chat` responded normally with spacing.
  - `https://studio.empirebox.store/api/v1/max/chat` returned HTTP 404 in this run (route unavailable at public edge), so stable public API validation is currently blocked by deployment routing, not local code.

## Regression Rule

Never trim or sanitize partial streaming chunks in a way that removes token-boundary whitespace.
