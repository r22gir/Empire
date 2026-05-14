# Runtime Routing: Stable + v10

Date: 2026-05-14

## Stable service ownership

- Frontend service: `empire-portal.service`
  - `WorkingDirectory=/home/rg/empire-repo/empire-command-center`
  - `ExecStart=/usr/bin/npx next start -p 3005`
- Backend service: `empire-backend.service`
  - `WorkingDirectory=/home/rg/empire-repo/backend`
  - `ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65`

## v10 service ownership

- Frontend service: `empire-portal-v10.service`
  - `WorkingDirectory=/home/rg/empire-repo-v10/empire-command-center`
  - `ExecStart=/usr/bin/npx next start -p 3010`
- Backend service: `empire-backend-v10.service`
  - `WorkingDirectory=/home/rg/empire-repo-v10/backend`
  - `ExecStart=/home/rg/empire-repo-v10/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --timeout-keep-alive 65`

## Active public tunnel

The active public connector is system service `cloudflared.service` using tunnel `empire-main` (`8ff5514f-e950-4ad1-8518-90bc3e6f6605`).

Updated ingress (remote tunnel config version 7):

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

Disabled stale user tunnel services that were failing `Unauthorized: Tunnel not found`:

- `cloudflared-empire-studio-override.service`
- `cloudflared-empire-studio-test.service`

## Verification commands

```bash
# systemd service targets
systemctl --user cat empire-portal.service
systemctl --user cat empire-backend.service
systemctl --user cat empire-portal-v10.service
systemctl --user cat empire-backend-v10.service

# active pids + cwd
ss -ltnp | grep -E ':8000|:3005|:8010|:3010'
for p in 8000 3005 8010 3010; do
  pid=$(ss -ltnp | awk -v port=":$p" '$0 ~ port {if (match($0,/pid=[0-9]+/)) print substr($0,RSTART+4,RLENGTH-4)}' | head -1)
  echo "port $p pid $pid"
  readlink -f /proc/$pid/cwd
done

# public stable
curl -I https://studio.empirebox.store/max
curl -s https://studio.empirebox.store/api/v1/max/status | python3 -m json.tool
curl -s -X POST https://studio.empirebox.store/api/v1/max/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"who are you?","history":[],"channel":"public-stable-route-test"}' \
  | python3 -m json.tool

# public v10
curl -s https://test-studio.empirebox.store/api/v1/max/status | python3 -m json.tool
curl -s -X POST https://test-studio.empirebox.store/api/v1/max/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"who are you?","history":[],"channel":"public-v10-route-test"}' \
  | python3 -m json.tool
```
