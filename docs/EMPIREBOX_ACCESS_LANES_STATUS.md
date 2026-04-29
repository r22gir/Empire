# EMPIREBOX ACCESS LANES STATUS

**Created:** 2026-04-29
**Last Updated:** 2026-04-29
**Status:** COMPLETE — all lanes operational

---

## OVERVIEW

Stable production and v10 test lanes are fully separated into distinct Git worktrees,
distinct ports, distinct Cloudflare Tunnels, and distinct systemd services.

---

## ACCESS LANES

| Lane | Hostname | Local Port | Build ID | HTTP |
|------|----------|------------|----------|------|
| studio (prod) | studio.empirebox.store | 3005 | build-1777489751379 | 200 |
| luxe (prod) | luxe.empirebox.store | 3005 | build-1777489751379 | 200 |
| api (prod) | api.empirebox.store | 8000 | — | via tunnel |
| test-studio (v10) | test-studio.empirebox.store | 3010 | build-1777489912427 | 200 |
| test-luxe (v10) | test-luxe.empirebox.store | 3010 | build-1777489912427 | 200 |

---

## WORKTREES

### ~/empire-repo-stable (Stable Production)
```
Path:    ~/empire-repo-stable
Branch:  stable/production
HEAD:    1396d4688ba0ac39b16b31f475e5d84b0f54a3c9
Build:   /home/rg/empire-repo-stable/empire-command-center/.next/
Build ID: build-1777489751379
```
- **Source:** Original stable Command Center from main@966cd44
- **Serves:** Ports 3005 (Next.js production)
- **Service:** empire-portal.service
- **Cloudflare Tunnel:** empire-studio-override → :3005

### ~/empire-repo-v10 (v10.0 Test)
```
Path:    ~/empire-repo-v10
Branch:  feature/v10.0-test-lane
HEAD:    dce7b68902820deee90ffe73b2d6d34963c9ce51
Build:   /home/rg/empire-repo-v10/empire-command-center/.next/
Build ID: build-1777489912427
```
- **Source:** feature/v10.0 branch (preserved, not merged)
- **Serves:** Port 3010 (Next.js production)
- **Service:** empire-portal-v10.service
- **Cloudflare Tunnel:** empire-studio-test → :3010

### ~/empire-repo (feature/v10.0) — IDLE
```
Path:    ~/empire-repo
Branch:  feature/v10.0
HEAD:    dce7b68902820deee90ffe73b2d6d34963c9ce51
```
- **Status:** IDLE — NOT served by any production service
- **Do NOT point any service here**
- **Future:** Merge to stable when v10 is promoted and approved

---

## SYSTEMD SERVICES

| Service | WorkingDirectory | Port | Status |
|---------|-----------------|------|--------|
| empire-portal.service | ~/empire-repo-stable/empire-command-center | 3005 | active |
| empire-portal-v10.service | ~/empire-repo-v10/empire-command-center | 3010 | active |
| empire-backend.service | ~/empire-repo/backend | 8000 | active |
| empire-openclaw.service | ~/Empire/openclaw | 7878 | auto-restart |
| cloudflared-empire-studio-override.service | n/a | tunnel (prod) | active |
| cloudflared-empire-studio-test.service | n/a | tunnel (test v10) | active |

**No service uses ~/empire-repo for production.**

---

## CLOUDFLARE TUNNELS

### empire-studio-override (Production — studio, luxe, api)
```
Config:     ~/.cloudflared/empire-studio.yml
Tunnel ID:  de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c
Credentials: /home/rg/.cloudflared/de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.json
Status:     Active (4 edge connections)
```
**Ingress:**
```
studio.empirebox.store /api/v1/* → localhost:8000
studio.empirebox.store           → localhost:3005
luxe.empirebox.store /api/v1/*  → localhost:8000
luxe.empirebox.store             → localhost:3005
api.empirebox.store              → localhost:8000
                                   → http_status:404
```

### empire-studio-test (v10 Test — test-studio, test-luxe)
```
Config:     ~/.cloudflared/empire-studio-test.yml
Tunnel ID:  97434c64-4176-47fa-bf8d-eef7739b44e0
Credentials: /home/rg/.cloudflared/97434c64-4176-47fa-bf8d-eef7739b44e0.json
Status:     Active (4 edge connections)
```
**Ingress:**
```
test-studio.empirebox.store /api/v1/* → localhost:8000
test-studio.empirebox.store           → localhost:3010
test-luxe.empirebox.store /api/v1/*  → localhost:8000
test-luxe.empirebox.store             → localhost:3010
                                      → http_status:404
```

---

## DNS RECORDS

| Hostname | CNAME Target | Proxy | Tunnel |
|----------|-------------|-------|--------|
| studio.empirebox.store | de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.cfargotunnel.com | proxied | empire-studio-override |
| luxe.empirebox.store | de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.cfargotunnel.com | proxied | empire-studio-override |
| api.empirebox.store | de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.cfargotunnel.com | proxied | empire-studio-override |
| test-studio.empirebox.store | 97434c64-4176-47fa-bf8d-eef7739b44e0.cfargotunnel.com | proxied | empire-studio-test |
| test-luxe.empirebox.store | 97434c64-4176-47fa-bf8d-eef7739b44e0.cfargotunnel.com | proxied | empire-studio-test |

---

## PROMOTION RULES

**v10 CANNOT merge or promote to production 3005 without explicit founder approval.**

Promotion sequence (when authorized):
1. Verify test-studio.empirebox.store and test-luxe.empirebox.store return 200 with v10 build
2. Merge feature/v10.0 into stable/production in ~/empire-repo
3. In ~/empire-repo-stable: `git pull && npm run build`
4. Restart: `systemctl --user restart empire-portal.service`
5. Verify studio.empirebox.store and luxe.empirebox.store return 200 with new build
6. Do NOT delete ~/empire-repo-v10 until fully verified

**Emergency rollback:**
```
cd ~/empire-repo-stable
git log --oneline -3
git checkout <last-good-commit>
npm run build
systemctl --user restart empire-portal.service
```

---

## HISTORY

- **2026-04-29 15:41 EDT:** Access lane separation finalized. v10 worktree converted to branch feature/v10.0-test-lane. All 6 hostnames return 200.
- **2026-04-29 15:40 EDT:** Fixed Cloudflare edge 404 for test hostnames — created separate empire-studio-test tunnel (97434c64) for v10 test lanes.
- **2026-04-29 15:14 EDT:** Initial access lane separation: stable on port 3005, v10 on port 3010.

---

## BACKUP REFERENCES

- v10 backup tag: `backup-v10-current-20260429-150556` (at dce7b68)
- v10 backup branch: `backup/v10-current-20260429-150556` (at dce7b68)
