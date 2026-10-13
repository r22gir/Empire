# Cloud Migration Plan — Off the Dell

Short plan for moving EmpireBox off the current Dell host (`EmpireDell`) onto cloud infrastructure. No live cutover in this document. No live-data writes.

## Why

The Dell is the single production box: FastAPI (`:8000`), Command Center (`:3005`), SQLite `empire.db`, OpenClaw (`:7878`), Telegram bot, and local backups. One disk or power failure takes every tenant down. Cloud is the path to tenant isolation at rest, backups that survive the building, and a Stripe-ready public edge.

## What stays vs what moves

| Keep as-is until cutover | Move first | Leave on Dell as fallback |
|---|---|---|
| Stripe **TEST / sandbox** keys only | Postgres (replace SQLite) | Founder-only OpenClaw / Ollama |
| Module routers and `bo_*` schema | Backend + Command Center | Local RecoveryForge / image cache |
| Package catalog (`pkg_starter` … `pkg_founder`) | Secrets in a cloud secret manager | Telegram long-poll until webhook DNS is live |

Never copy `client_aliases.json`, `business.json`, or `.env` into git or a public bucket. Copy them out-of-band.

## Target shape

1. **Compute** — one small VM or container pair (API + Next.js). Same ports: 8000 / 3005.
2. **Database** — managed Postgres. `bo_businesses` / `bo_tenants` / `bo_packages` already use portable SQL. SQLite WAL stays the Dell fallback.
3. **Object storage** — apostille docs, drawings, backups. Prefix every key with `business_id` / `tenant_id`.
4. **Edge** — Cloudflare (or equivalent) in front of `studio.empirebox.store` and `api.empirebox.store`. Stripe webhooks hit the API host only.
5. **Secrets** — `STRIPE_SECRET_KEY` must stay `sk_test_` / `rk_test_` until a later live-mode approval. Reject `sk_live_` in BusinessOps checkout.

## Cutover sequence (no live writes until the Founder flips the switch)

1. Inventory Dell services, disk, and DNS. Snapshot the box. Do not mutate `empire.db`.
2. Stand up cloud Postgres + empty schema. Restore a **copy** of the snapshot, not the live file.
3. Point a staging hostname at the cloud API. Run BusinessOps signup + Stripe Checkout against TEST mode.
4. Rehearse tenant isolation: tenant A must 404 on tenant B’s `business_id`.
5. Freeze Dell writes. Final dump → cloud restore. Flip DNS TTL. Keep Dell read-only for 48 hours.
6. Verify Telegram, Stripe webhook signatures, and package checkout (`pkg_starter` $29, `pkg_growth` $79, `pkg_empire` $199, `pkg_apostille_only` $49). `pkg_founder` stays internal.

## Rollback

Leave Dell processes stopped but installed. If cloud fails, drop DNS back, start Dell services, and resume from the last snapshot. Do not dual-write.

## Out of scope here

Live Stripe mode, destructive deletes of canceled businesses, and merging this plan as a deploy. Draft PR only.
