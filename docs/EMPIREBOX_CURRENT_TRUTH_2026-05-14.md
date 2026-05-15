# EMPIREBOX CURRENT TRUTH 2026-05-14

Last updated: May 14, 2026
Source: Founder current-truth brief
Scope: Stable/live path first (`~/empire-repo-main`, branch `main`)

## Stable/Live Runtime

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3005`
- Public studio: `https://studio.empirebox.store`
- Public API routing: `https://studio.empirebox.store/api/v1/* -> localhost:8000`

## Lane Separation (2026-05-15)

- Main/stable (production path): `main` on `3005/8000` from `/home/rg/empire-repo-main`
- Feature review lane: `feature/v10.0` on `3020/8020` from `/home/rg/empire-repo-feature`
- v10 test lane: `feature/v10.0-test-lane` on `3010/8010` from `/home/rg/empire-repo-v10`
- Public stable hostnames map to `3005/8000`; public test hostnames map to `3010/8010`

## Module vs Service Truth

Empire modules/products are not the same thing as Linux/systemd services.

- Module question example: "what is going on with ArchiveForge?"
- Service health example: "what services are online?"

MAX must answer module questions from module/docs truth, and service questions from runtime/service health.

## Empire Module Snapshot

### ArchiveForge

- Module purpose: archive and magazine workflows (LIFE magazine focus).
- UI route: `/archiveforge-life`
- Compatibility route: `/archiveforge` redirects to `/archiveforge-life`
- Stable public route: `https://studio.empirebox.store/archiveforge-life`
- API surface: `/api/v1/archiveforge/*`
- Core workflow verified complete on stable/live:
  - intake
  - metadata review/edit
  - cover lookup with confidence/relevance handling
  - listing draft generation/save
  - save/list/detail lifecycle
  - publish gating
- Publish truth:
  - internal/staged publish only
  - `approval_confirmed=true` required
  - real `marketforge_category_id` required (UUID)
  - real `marketforge_ships_from_zip` required (5-digit ZIP)
  - external marketplace go-live intentionally gated
- Validation truth:
  - backend ArchiveForge tests passed
  - smoke script passed
  - stable local and public paths verified

### MarketForge

- MarketForge in this workflow is the internal product target used by ArchiveForge staged publish.
- ArchiveForge publish success means internal record creation (not external go-live marketplace publication by default).

### Workroom

- Workroom is an active Empire product/module in Command Center, not a standalone Linux service concept.

### Drawing Studio

- Drawing Studio remains an Empire module workflow and should not override ArchiveForge intent when the request is clearly about archive/LIFE workflows.

### RecoveryForge

- RecoveryForge is a module in Empire workflows; status should come from module/runtime truth, not guessed from generic chat memory.

### RelistApp

- RelistApp is an Empire module; treat module status as product truth, separate from Linux service process state.

### VendorOps

- VendorOps is an Empire module; answer with module truth and current docs/runtime evidence.

### SocialForge

- SocialForge is an Empire module; answer from current module/runtime truth.

### Hermes

- Hermes is an Empire internal assistant/workflow layer under MAX orchestration.

### OpenClaw

- OpenClaw is an execution subsystem/gateway used by MAX task workflows (service/runtime truth applies when asked for health).

## Resolver Grounding Priority

For ArchiveForge responses, grounding priority is:

1. `docs/EMPIREBOX_CURRENT_TRUTH_2026-05-14.md`
2. `docs/ARCHIVEFORGE_STATUS.md`
3. `docs/ARCHIVEFORGE_WORKFLOW.md`
4. `docs/EMPIRE_MODULE_REGISTRY.md`
