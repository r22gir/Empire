# Runtime Routing: Stable, Feature, and v10

Date: 2026-05-15

## Stable/main service ownership

- Frontend service: `empire-portal.service`
  - `WorkingDirectory=/home/rg/empire-repo-main/empire-command-center`
  - `ExecStart=/usr/bin/npx next start -p 3005`
- Backend service: `empire-backend.service`
  - `WorkingDirectory=/home/rg/empire-repo-main/backend`
  - `ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65`

## Feature service ownership (`feature/v10.0`)

- Frontend service: `empire-portal-feature.service`
  - `WorkingDirectory=/home/rg/empire-repo-feature/empire-command-center`
  - `ExecStart=/usr/bin/npx next start -p 3020`
- Backend service: `empire-backend-feature.service`
  - `WorkingDirectory=/home/rg/empire-repo-feature/backend`
  - `ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8020 --timeout-keep-alive 65`

## v10 test-lane service ownership

- Frontend service: `empire-portal-v10.service`
  - `WorkingDirectory=/home/rg/empire-repo-v10/empire-command-center`
  - `ExecStart=/usr/bin/npx next start -p 3010`
- Backend service: `empire-backend-v10.service`
  - `WorkingDirectory=/home/rg/empire-repo-v10/backend`
  - `ExecStart=/home/rg/empire-repo-v10/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --timeout-keep-alive 65`

## Public tunnel routing

The active public connector is system service `cloudflared.service` using tunnel `empire-main` (`8ff5514f-e950-4ad1-8518-90bc3e6f6605`).

- `studio.empirebox.store`:
  - `/api/v1/*` -> `http://localhost:8000`
  - `/*` -> `http://localhost:3005`
- `luxe.empirebox.store`:
  - `/api/v1/*` -> `http://localhost:8000`
  - `/*` -> `http://localhost:3005`
- `test-studio.empirebox.store`:
  - `/api/v1/*` -> `http://localhost:8010`
  - `/*` -> `http://localhost:3010`
- `test-luxe.empirebox.store`:
  - `/api/v1/*` -> `http://localhost:8010`
  - `/*` -> `http://localhost:3010`

Feature lane (`3020/8020`) is local-only and intentionally not exposed publicly.

## Verification commands

```bash
# systemd service targets
systemctl --user cat empire-backend.service
systemctl --user cat empire-portal.service
systemctl --user cat empire-backend-feature.service
systemctl --user cat empire-portal-feature.service
systemctl --user cat empire-backend-v10.service
systemctl --user cat empire-portal-v10.service

# active pids + cwd
ss -ltnp | grep -E ':8000|:3005|:8020|:3020|:8010|:3010'
for p in 8000 3005 8020 3020 8010 3010; do
  pid=$(ss -ltnp | awk -v port=":$p" '$0 ~ port {if (match($0,/pid=[0-9]+/)) print substr($0,RSTART+4,RLENGTH-4)}' | head -1)
  echo "port $p pid $pid"
  readlink -f /proc/$pid/cwd
done

# public stable + public v10
curl -s https://studio.empirebox.store/api/v1/max/status | python3 -m json.tool
curl -s https://test-studio.empirebox.store/api/v1/max/status | python3 -m json.tool
```
