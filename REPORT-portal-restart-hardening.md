# REPORT — Portal Restart Hardening

**Repo:** `/home/rg/empire-repo-main` · **Branch:** `main` (lane branch: `feature/portal-restart-hardening`) · **HEAD at lane start:** `736a54a fix(ui): clean command center truth indicators`
**Author:** Hermes, 2026-06-09 · **Scope:** small reliability lane, no business-logic or UI changes

## Problem

`empire-portal.service` (`/home/rg/.config/systemd/user/empire-portal.service`) has an `ExecStartPre` that rebuilds the Next.js app from source when `.next/server` or `.next/BUILD_ID` is missing:

```
ExecStartPre=/bin/sh -c 'if [ ! -d /home/rg/empire-repo-main/empire-command-center/.next/server ] || [ ! -f /home/rg/empire-repo-main/empire-command-center/.next/BUILD_ID ]; then /usr/bin/npm install && /usr/bin/npm run build; fi'
```

`/usr/bin/npm install` (no flags) installs in **production mode by default** and skips `devDependencies`. But `empire-command-center/package.json` declares the build-time PostCSS pipeline in `devDependencies`:

| Package | Where | Why needed at build time |
|---|---|---|
| `@tailwindcss/postcss` | `devDependencies` | PostCSS plugin loaded by Next.js during `next build` |
| `tailwindcss` | `devDependencies` | base config that the postcss plugin reads |

When the build is triggered from a state where `node_modules` has been pruned (or freshly cloned), the rebuild fails with:

```
Error: Cannot find module '@tailwindcss/postcss'
```

Because the unit is set to `Restart=always` + `RestartSec=5`, the failure restarts the unit immediately, which re-runs `ExecStartPre`, which fails again — a tight restart loop. Confirmed during the `feature/command-center-truth-cleanup` lane: restart counter reached 16 in ~10 seconds, only stopped by `systemctl --user stop` + `reset-failed`.

## Second issue discovered during this lane

After applying the devDep fix below, the rebuild still failed — but with a different error: `Error: ENOENT: no such file or directory, open '/home/rg/.../.next/prerender-manifest.json'`. The root cause: **the systemd default `TimeoutStartSec=90s` was killing the `ExecStartPre` mid-build**, leaving a partial `.next/` on disk. A real `next build --webpack` on this codebase routinely takes 90–120 seconds (TypeScript checking + page-data collection across ~70 routes uses 19 workers).

## Fix (two parts)

A systemd **drop-in override** at:

```
/home/rg/.config/systemd/user/empire-portal.service.d/rebuild-deps.conf
```

The drop-in:

1. **Replaces the upstream `ExecStartPre`** with one that passes `--include=dev --no-audit --no-fund` to `npm install`, so devDependencies are installed before the build runs.
2. **Adds `TimeoutStartSec=300`** so the rebuild has 5 minutes headroom instead of the 90s default.
3. **Defense-in-depth stub for `prerender-manifest.json`**: if the build completes but the file is still missing (e.g., a future Next.js version drops it), an empty stub is written so `next start` does not fail with ENOENT. Not triggered by today's Next.js 16.1.6, but cheap insurance.

```ini
[Service]
ExecStartPre=
ExecStartPre=/bin/sh -c 'cd /home/rg/empire-repo-main/empire-command-center && if [ ! -d .next/server ] || [ ! -f .next/BUILD_ID ]; then /usr/bin/npm install --include=dev --no-audit --no-fund && /usr/bin/npm run build && ( [ -f .next/prerender-manifest.json ] || echo "{\"version\":4,\"routes\":{},\"dynamicRoutes\":{},\"notFoundRoutes\":[],\"preview\":{\"previewModeId\":\"00000000-0000-0000-0000-000000000000\",\"previewModeSigningKey\":\"0000000000000000000000000000000000000000000000000000000000000000\",\"previewModeEncryptionKey\":\"0000000000000000000000000000000000000000000000000000000000000000\"}}" > .next/prerender-manifest.json ); fi'
TimeoutStartSec=300
```

Notes:
- The leading `ExecStartPre=` (empty value) **clears** the inherited line from the base unit. systemd requires this — you cannot override a single setting without clearing it.
- The drop-in lives in `~/.config/systemd/user/`, **outside** the Empire git repo. The fix is host config, not repo config.
- The base `empire-portal.service` file is untouched. If the drop-in is ever removed, the unit reverts to the original behavior cleanly.
- `--no-audit --no-fund` mirrors the `npm install` flags that work in the manual recovery path; they suppress network noise and prompt output that would otherwise break the systemd journal.
- `TimeoutStartSec=300` is the most important line in this file — without it, the devDep fix alone is not enough.

## Why not the other options

- **Option B — `npm ci --include=dev`** is faster and stricter but assumes the lockfile is in sync with `package.json`. If anyone runs `npm install` (which updates the lockfile) on a different machine, `npm ci` here could fail. Out of scope for this small lane.
- **Option C — move `@tailwindcss/postcss` and `tailwindcss` to `dependencies`** changes the production install footprint and contradicts the npm convention that build-time tools belong in `devDependencies`. Also doesn't generalize if Next.js or its plugin chain adds more build-time deps later.
- **Option D-lite — wrap the rebuild in a logging script + add `StartLimitBurst=3` + change `Restart=always` to `Restart=on-failure`** is the right long-term shape but expands scope beyond a small reliability lane. Worth a follow-up lane.

## Verification (from this lane)

- `systemctl --user daemon-reload` — reloaded the unit with the drop-in
- `systemctl --user stop empire-portal.service` — stopped cleanly
- `systemctl --user reset-failed empire-portal.service` — cleared failure state
- `rm -rf empire-command-center/.next` — simulated "fresh build required" state
- `systemctl --user start empire-portal.service` — `ExecStartPre` ran for ~2 minutes (well within `TimeoutStartSec=300`), produced a complete `.next/` (including `prerender-manifest.json`, `images-manifest.json`, `next-minimal-server.js.nft.json`, `next-server.js.nft.json`, `export-marker.json`), and the service came up `active`
- `curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:3005/` — `HTTP 200`
- `curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/health` — `HTTP 200`
- No restart loop. `systemctl --user show ... --property=NRestarts` reports `0`.

## Future hardening (deferred)

- Consider `Restart=on-failure` + `StartLimitBurst=3` + `StartLimitIntervalSec=60` for the unit, so a future regression in the build pipeline doesn't get a free pass to loop forever.
- Consider committing the `rebuild-deps.conf` drop-in to a small `host-config/` repo (out of scope here, but a clean place for "small systemd overrides that keep the Empire stack alive").
- If/when BusinessOps lands and the portal moves to a Docker image, the whole ExecStartPre rebuild path becomes unnecessary and this drop-in can be deleted.

**End of report. No push performed.**
