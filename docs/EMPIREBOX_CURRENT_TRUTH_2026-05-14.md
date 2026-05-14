# EMPIREBOX CURRENT TRUTH 2026-05-14

Last updated: May 14, 2026
Source: Founder current-truth brief

## Module vs Service Truth

Empire modules/products are not the same thing as Linux/systemd services.

- Module question example: "what is going on with ArchiveForge?"
- Service health example: "what services are online?"

MAX must answer module questions from module/docs truth, and service questions from runtime/service health.

## ArchiveForge Truth (Stable/Live Reference)

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

## Resolver Grounding Priority

For ArchiveForge responses, grounding priority is:

1. `docs/EMPIREBOX_CURRENT_TRUTH_2026-05-14.md`
2. `docs/ARCHIVEFORGE_STATUS.md`
3. `docs/ARCHIVEFORGE_WORKFLOW.md`
4. `docs/EMPIRE_MODULE_REGISTRY.md`
