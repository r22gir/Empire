# MAX Whitespace Streaming Fix (v10)

Date: 2026-05-14

## First Bad Stage

- Lane: `v10` (`localhost:8010`)
- First bad stage: none reproduced across traced stages for local v10 path.
- Observed: streamed chunks preserved boundary whitespace from backend through frontend render.

## Root Cause Context

The confirmed whitespace collapse root cause was in the stable/live lane stream path where chunk sanitization trimmed edge whitespace per chunk. v10 local stream path did not reproduce that behavior in this verification run.

## Fix Applied in v10

1. Added direct provider-identity route in [backend/app/routers/max/router.py](/home/rg/empire-repo-v10/backend/app/routers/max/router.py) for:
   - `what ai?`
   - `what model are you using?`
   - `who powers you?`
2. Ensured the identity direct route is not blocked by desk defaults so browser `/max` requests receive the expected explicit model/provider answer.
3. Added whitespace regression test in [backend/tests/test_max_whitespace_streaming.py](/home/rg/empire-repo-v10/backend/tests/test_max_whitespace_streaming.py).

## Affected Lanes

- v10/test: provider identity route corrected; whitespace remained intact in traced local path.
- stable/live: whitespace stream sanitization fix applied separately in stable repo.

## Verification Summary

- Backend non-streaming (`/max/chat`): normal spacing.
- Backend streaming (`/max/chat/stream`): boundary spaces preserved.
- Browser (`http://localhost:3010/max`): responses render with normal spacing and expected provider identity text.
- Public (`https://test-studio.empirebox.store/api/v1/max/chat`): spacing is normal.

## Regression Rule

Never trim or sanitize partial streaming chunks in a way that removes token-boundary whitespace.
