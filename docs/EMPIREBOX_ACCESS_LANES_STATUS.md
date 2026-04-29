# EMPIREBOX ACCESS LANES STATUS

**Created:** 2026-04-29
**Purpose:** Track stable vs v10 access lane separation

---

## OVERVIEW

All public lanes were running v10.0 when production should remain on stable.
Separation completed 2026-04-29. Two independent worktrees serve stable and v10.

---

## ACCESS LANES

| Lane | Hostname | Local Port | Worktree | Commit | Build ID |
|------|----------|------------|----------|--------|----------|
| **studio** (prod) | studio.empirebox.store | 3005 | ~/empire-repo-stable | 966cd44 (stable/production) | build-1777489751379 |
| **luxe** (prod) | luxe.empirebox.store | 3005 | ~/empire-repo-stable | 966cd44 (stable/production) | build-1777489751379 |
| **api** (prod) | api.empirebox.store | 8000 | (backend, not Next.js) | — | — |
| **test-studio** | test-studio.empirebox.store | 3010 | ~/empire-repo-v10 | dce7b68 (feature/v10.0) | build-1777489912427 |
| **test-luxe** | test-luxe.empirebox.store | 3010 | ~/empire-repo-v10 | dce7b68 (feature/v10.0) | build-1777489912427 |

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
| cloudflared-empire-studio-override.service | n/a | tunnel | active |

---

## CLOUDFLARE TUNNEL

**Config:** ~/.cloudflared/empire-studio.yml
**Tunnel ID:** de194be2-b4a8-40f2-a7d2-8cf2c55e1e6c
**Tunnel Name:** empire-studio-override

### Ingress Rules
```
hostname: studio.empirebox.store  path: api/v1/*  → localhost:8000
hostname: studio.empirebox.store                    → localhost:3005
hostname: luxe.empirebox.store    path: api/v1/*  → localhost:8000
hostname: luxe.empirebox.store                      → localhost:3005
hostname: test-studio.empirebox.store  path: api/v1/* → localhost:8000
hostname: test-studio.empirebox.store                → localhost:3010
hostname: test-luxe.empirebox.store  path: api/v1/*   → localhost:8000
hostname: test-luxe.empirebox.store                  → localhost:3010
hostname: api.empirebox.store                        → localhost:8000
                                                    → http_status:404
```

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

## KNOWN ISSUES

- **test-studio.empirebox.store / test-luxe.empirebox.store:** Cloudflare returns HTTP 404 for requests despite valid SSL cert and correct DNS. This is a Cloudflare edge routing issue. DNS CNAMEs point to Cloudflare, SSL certs provision correctly, but Cloudflare cannot route to the tunnel. Requires Cloudflare Dashboard investigation.

---

## BACKUP REFERENCES

- v10 backup tag: `backup-v10-current-20260429-150556` (at dce7b68)
- v10 backup branch: `backup/v10-current-20260429-150556` (at dce7b68)
