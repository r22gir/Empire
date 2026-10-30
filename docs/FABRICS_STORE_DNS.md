# Empire Fine Fabrics — DNS / Cloudflare tunnel

The store is served at **fabrics.empirebox.store**, the same way
`workroom.empirebox.store` is a public host on the `empire-main` tunnel.

This document is the operator step. **Do not change Cloudflare or deploy
from this PR.** The app and the Next.js host rule land first; DNS is a
separate founder action.

## Intended routing (mirror the workroom / studio pattern)

Tunnel: `empire-main` (`8ff5514f-e950-4ad1-8518-90bc3e6f6605`)
Config: `/home/rg/.cloudflared/empire-main-local.yml` (live box)

Add an ingress hostname:

```yaml
- hostname: fabrics.empirebox.store
  service: http://localhost:3005
  originRequest:
    # Do NOT set httpHostHeader to localhost. The public-edge gate
    # and Next middleware read Host / X-Forwarded-Host.
    noTLSVerify: false
```

If `/api/v1/*` is already split off the portal (studio/luxe style), add
the same split for this host:

```yaml
- hostname: fabrics.empirebox.store
  path: /api/v1/*
  service: http://localhost:8000
- hostname: fabrics.empirebox.store
  service: http://localhost:3005
```

DNS (Cloudflare dashboard or CLI, founder-only):

```bash
# Creates the CNAME only. It does not add an ingress rule.
cloudflared tunnel route dns empire-main fabrics.empirebox.store
```

Optional test host, same shape as `test-luxe`:

- `test-fabrics.empirebox.store` → v10 / feature ports (`3010` / `8010`)

## What the app already does

- Next middleware (`empire-command-center/app/lib/fabricsHost.ts`)
  rewrites `fabrics.empirebox.store/` → `/fine-fabrics` and 404s
  operator screens (`/workroom`, `/max`, `/intake`, …).
- FastAPI `fabrics_public_edge` allows only catalog, product, photo,
  preview, samples, and test-mode checkout on that hostname.
- Owner CSV import and swatch uploads stay on studio / localhost.

## After DNS exists (not this PR)

1. Confirm ingress + CNAME.
2. `curl -sI https://fabrics.empirebox.store/` → 200 from the store.
3. `curl -s https://fabrics.empirebox.store/api/v1/fine-fabrics/health`
4. Confirm `/api/v1/finance` and `/api/v1/max` return 401 on this host.
