# Runtime Lane Separation

Date: 2026-05-15

## Lane map

### Main / Complete / Production-Stable

- Worktree: `/home/rg/empire-repo-main`
- Branch: `main`
- Frontend: `http://localhost:3005`
- Backend: `http://localhost:8000`
- Public: `studio.empirebox.store`, `luxe.empirebox.store`
- systemd: `empire-portal.service`, `empire-backend.service`

### Feature / Stable-Candidate

- Worktree: `/home/rg/empire-repo-feature`
- Branch: `feature/v10.0`
- Frontend: `http://localhost:3020`
- Backend: `http://localhost:8020`
- Public: not exposed
- systemd: `empire-portal-feature.service`, `empire-backend-feature.service`

### v10 Test Lane

- Worktree: `/home/rg/empire-repo-v10`
- Branch: `feature/v10.0-test-lane`
- Frontend: `http://localhost:3010`
- Backend: `http://localhost:8010`
- Public: `test-studio.empirebox.store`, `test-luxe.empirebox.store`
- systemd: `empire-portal-v10.service`, `empire-backend-v10.service`

## Cloudflare/public routing policy

- `studio.empirebox.store`
  - `/api/v1/*` -> `http://localhost:8000`
  - `/*` -> `http://localhost:3005`
- `luxe.empirebox.store`
  - `/api/v1/*` -> `http://localhost:8000`
  - `/*` -> `http://localhost:3005`
- `test-studio.empirebox.store`
  - `/api/v1/*` -> `http://localhost:8010`
  - `/*` -> `http://localhost:3010`
- `test-luxe.empirebox.store`
  - `/api/v1/*` -> `http://localhost:8010`
  - `/*` -> `http://localhost:3010`

Feature lane is intentionally local-only.

## What must never happen

- `3005/8000` must not run `feature/v10.0` or `feature/v10.0-test-lane`
- `3020/8020` must not silently target `8000` or `8010`
- `3010/8010` must remain the v10 test lane
- Public stable hostnames must not resolve to test or feature ports
- Public test hostnames must not resolve to stable or feature ports

## Promotion policy

1. Promote `feature/v10.0` to `main` only with explicit, reviewed commit selection.
2. Keep v10 test branch isolated; do not auto-promote v10 test commits.
3. Re-run lane verification commands before and after every promotion.

## Verification commands

```bash
systemctl --user daemon-reload
systemctl --user restart \
  empire-backend.service empire-portal.service \
  empire-backend-feature.service empire-portal-feature.service \
  empire-backend-v10.service empire-portal-v10.service

ss -ltnp | grep -E ':8000|:3005|:8020|:3020|:8010|:3010'

for p in 8000 3005 8020 3020 8010 3010; do
  pid=$(ss -ltnp | awk -v port=":$p" '$0 ~ port {if (match($0,/pid=[0-9]+/)) print substr($0,RSTART+4,RLENGTH-4)}' | head -1)
  echo "port $p pid $pid"
  readlink -f /proc/$pid/cwd
done

curl -s http://localhost:8000/api/v1/max/status | python3 -m json.tool
curl -s http://localhost:8020/api/v1/max/status | python3 -m json.tool
curl -s http://localhost:8010/api/v1/max/status | python3 -m json.tool

curl -s https://studio.empirebox.store/api/v1/max/status | python3 -m json.tool
curl -s https://test-studio.empirebox.store/api/v1/max/status | python3 -m json.tool
```
