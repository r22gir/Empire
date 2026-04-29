# EMPIREBOX ACCESS LANES STATUS

**Created:** 2026-04-29
**Updated:** 2026-04-29 (added empire-studio-test tunnel for v10 test lanes)
**Purpose:** Track stable vs v10 access lane separation

---

## OVERVIEW

All public lanes were running v10.0 when production should remain on stable.
Separation completed 2026-04-29. Two independent worktrees serve stable and v10.
Two Cloudflare Tunnels used: one for production, one for test.

---

## ACCESS LANES

| Lane | Hostname | Local Port | Worktree | Commit | Build ID | Tunnel |
|------|----------|------------|----------|--------|----------|--------|
| **studio** (prod) | studio.empirebox.store | 3005 | ~/empire-repo-stable | 966cd44 (stable/production) | build-1777489751379 | empire-studio-override |
| **luxe** (prod) | luxe.empirebox.store | 3005 | ~/empire-repo-stable | 966cd44 (stable/production) | build-1777489751379 | empire-studio-override |
| **api** (prod) | api.empirebox.store | 8000 | (backend, not Next.js) | — | — | empire-studio-override |
| **test-studio** | test-studio.empirebox.store | 3010 | ~/empire-repo-v10 | dce7b68 (feature/v10.0) | build-1777489912427 | empire-studio-test |
| **test-luxe** | test-luxe.empirebox.store | 3010 | ~/empire-repo-v10 | dce7b68 (feature/v10.0) | build-1777489912427 | empire-studio-test |

---

## WORKTREES

### ~/empire-repo-stable (Stable Production)
```
Branch: stable/production
HEAD:   966cd448e812a177d9e51ad694e51f38e8047466
Tag:    v4.0.0-544-g966cd44
Build:  /home/rg/empire-repo-stable/empire-command-center/.next/
```
- **Source:** Original stable Command Center from main branch
- **Serves:** Ports 3005 (Next.js production)
- **Systemd:** empire-portal.service (port 3005)
- **Cloudflare:** studio.empirebox.store, luxe.empirebox.store → :3005

### ~/empire-repo-v10 (v10.0 Test)
```
HEAD:   dce7b68902820deee90ffe73b2d6d34963c9ce51
Tag:    backup-v10-current-20260429-150556 (backup before separation)
Branch: feature/v10.0 (checked out in ~/empire-repo, not here)
Build:  /home/rg/empire-repo-v10/empire-command-center/.next/
```
- **Source:** feature/v10.0 branch (preserved, not merged)
- **Serves:** Port 3010 (Next.js production)
- **Systemd:** empire-portal-v10.service (port 3010)
- **Cloudflare:** test-studio.empirebox.store, test-luxe.empirebox.store → :3010

### ~/empire-repo (feature/v10.0)
```
Branch: feature/v10.0
HEAD:   dce7b68902820deee90ffe73b2d6d34963c9ce51
```
- **Status:** Idle worktree, feature/v10.0 checked out
- **NOT actively served** — do not point services here
- **Future:** Merge to stable when v10 is promoted

---

## SYSTEMD SERVICES

| Service | Worktree | Port | Status |
|---------|----------|------|--------|
| empire-portal.service | ~/empire-repo-stable | 3005 | active |
| empire-portal-v10.service | ~/empire-repo-v10 | 3010 | active |
| cloudflared-empire-studio-override.service | n/a | tunnel (prod) | active |
| cloudflared-empire-studio-test.service | n/a | tunnel (test v10) | active |

---

## CLOUDFLARE TUNNELS

### Tunnel 1: empire-studio-override (Production)
**Config:** ~/.cloudflared/empire-studio.yml
**Tunnel ID:** de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c
**Credentials:** /home/rg/.cloudflared/de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.json
**Status:** Active, 4 connections

#### Ingress Rules
```
hostname: studio.empirebox.store  path: api/v1/*  → localhost:8000
hostname: studio.empirebox.store                    → localhost:3005
hostname: luxe.empirebox.store    path: api/v1/*  → localhost:8000
hostname: luxe.empirebox.store                      → localhost:3005
hostname: api.empirebox.store                      → localhost:8000
                                                    → http_status:404
```

### Tunnel 2: empire-studio-test (v10 Test)
**Config:** ~/.cloudflared/empire-studio-test.yml
**Tunnel ID:** 97434c64-4176-47fa-bf8d-eef7739b44e0
**Credentials:** /home/rg/.cloudflared/97434c64-4176-47fa-bf8d-eef7739b44e0.json
**Status:** Active, 4 connections

#### Ingress Rules
```
hostname: test-studio.empirebox.store  path: api/v1/*  → localhost:8000
hostname: test-studio.empirebox.store                  → localhost:3010
hostname: test-luxe.empirebox.store    path: api/v1/*  → localhost:8000
hostname: test-luxe.empirebox.store                    → localhost:3010
                                                       → http_status:404
```

---

## DNS CONFIGURATION

All hostnames use CNAME records pointing to their respective tunnel endpoints:

| Hostname | CNAME Target | Proxy | Tunnel |
|----------|-------------|-------|--------|
| studio.empirebox.store | de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.cfargotunnel.com | proxied | empire-studio-override |
| luxe.empirebox.store | de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.cfargotunnel.com | proxied | empire-studio-override |
| api.empirebox.store | de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c.cfargotunnel.com | proxied | empire-studio-override |
| test-studio.empirebox.store | 97434c64-4176-47fa-bf8d-eef7739b44e0.cfargotunnel.com | proxied | empire-studio-test |
| test-luxe.empirebox.store | 97434c64-4176-47fa-bf8d-eef7739b44e0.cfargotunnel.com | proxied | empire-studio-test |

---

## PROMOTION RULES

When v10.0 is ready to promote to production:

1. **Test first:** Verify test-studio.empirebox.store and test-luxe.empirebox.store respond correctly
2. **Merge to stable:** `git checkout stable/production && git merge feature/v10.0` in ~/empire-repo (NOT in worktree)
3. **Build stable:** In ~/empire-repo-stable: `git pull && npm run build`
4. **Restart stable:** `systemctl --user restart empire-portal.service`
5. **Update DNS:** Point studio.empirebox.store and luxe.empirebox.store to new stable build (if different BUILD_ID)
6. **Verify:** curl both hostnames, confirm old-stable symptoms resolved
7. **Do NOT delete** ~/empire-repo-v10 until v10 is fully merged and verified

### Emergency Rollback
If promotion fails, revert to stable:
```
cd ~/empire-repo-stable
git log --oneline -3  # find last good commit
git checkout <commit-hash>
npm run build
systemctl --user restart empire-portal.service
```

---

## KNOWN ISSUES (RESOLVED)

- ~~test-studio.empirebox.store / test-luxe.empirebox.store: Cloudflare returns HTTP 404~~ — **RESOLVED 2026-04-29** by creating a separate tunnel (empire-studio-test) for test hostnames. Root cause: Cloudflare edge routing association for test hostnames was not properly established on the empire-studio-override tunnel, despite correct DNS CNAME records. Using a fresh tunnel (empire-studio-test) resolved the issue.

---

## HISTORY

- **2026-04-29 15:40 EDT:** Deleted old empire-studio tunnel (2f85176c). Created empire-studio-test tunnel (97434c64) for v10 test lanes. DNS CNAMEs updated for test-studio and test-luxe to point to new tunnel. All 4 hostnames now return 200.
- **2026-04-29 15:14 EDT:** Initial access lane separation: stable on port 3005, v10 on port 3010, empire-studio-override tunnel created for production routes.

---

## BACKUP REFERENCES

- v10 backup tag: `backup-v10-current-20260429-150556` (at dce7b68)
- v10 backup branch: `backup/v10-current-20260429-150556` (at dce7b68)
