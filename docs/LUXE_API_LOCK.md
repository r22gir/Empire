# Luxe API lock

Date: 2026-09-28

This closes the public door called out in the sunrise smoke (PR 61, `docs/SUNRISE_SMOKE_REPORT.md` on `cursor/sunrise-smoke-workroom-b1c0`).

## What was open

`luxe.empirebox.store` is a public hostname. It is not behind Cloudflare Access. `studio.empirebox.store` and `api.empirebox.store` are: an anonymous client there gets the Access sign-in page.

The tunnel `empire-main` publishes two origins for luxe (see `docs/RUNTIME_ROUTING_STABLE.md`):

- `/*` → Next.js on `localhost:3005`
- `/api/v1/*` → FastAPI on `localhost:8000`

The second rule never hits Next.js middleware. On `feature/drawing-standard` (the commit the live MAX status reported during the smoke), that middleware already hard-scopes luxe pages to `/intake`. The API rule skips it.

The backend had no auth middleware on quotes, invoices, payments, jobs, leads, pricing, CRM, or MAX. Anyone who could open the public URL could read them.

Confirmed again on 2026-09-28 from this workspace, anonymous GET, browser User-Agent, body discarded after the status check:

| URL | Result |
| --- | --- |
| `https://luxe.empirebox.store/api/v1/quotes?limit=1` | **200** `application/json` (quote list) |
| `https://luxe.empirebox.store/api/v1/max/health` | **200** `application/json` (`status: healthy`) |
| `https://luxe.empirebox.store/intake` | **200** HTML intake shell |
| `https://api.empirebox.store/api/v1/quotes?limit=1` | Access sign-in HTML (followed redirect) |
| `https://studio.empirebox.store/api/v1/quotes?limit=1` | Access sign-in HTML (followed redirect) |

A default Python User-Agent received Cloudflare **403** on the same URLs. That is a bot check, not auth. A normal browser was let through to the API.

Customer names, quote numbers, and amounts from that probe are intentionally not copied here.

`test-luxe.empirebox.store` uses the same shape of ingress toward port 8010. It was **521** during the smoke (origin down). The gate still treats that hostname as public so it cannot come back open.

## What changed

`backend/app/security/luxe_public_edge.py` runs on every request. If `Host`, `X-Forwarded-Host`, or `X-Original-Host` is `luxe.empirebox.store` or `test-luxe.empirebox.store`, the request is **401** unless it is on the intake allowlist below. Denial body:

```json
{"detail":"Authentication required","error":"luxe_public_edge_denied"}
```

Header: `X-Empire-Edge: luxe-public-denied`.

Allowed on those hosts (everything else, including `/health`, `/docs`, quotes, invoices, payments, jobs, leads, pricing, CRM, MAX, portal link lists, fabric catalog, and quote photo bytes, is denied):

| Method | Path | Why it stays |
| --- | --- | --- |
| POST | `/api/v1/intake/signup`, `/api/v1/intake/login` | Account capture. Already slowapi-limited (10/minute). |
| * | `/api/v1/intake/me`, `/api/v1/intake/projects` and subpaths | Client portal. Handlers require the intake JWT. Anonymous GET `/projects` is **401** from the handler, not a list. |
| * | `/api/v1/fabrics/intake-project/...` except `.../match` | Intake UI writes fabric rows for a project id. `.../match` is an owner action and is denied. |
| POST | `/api/v1/photos/upload` | Swatch upload from the intake form. Extra cap: 10/minute per IP. |
| GET | `/api/v1/photos/serve/intake/...` | Bytes for that swatch. Quote/telegram/craftforge photo URLs are denied. |
| GET | `/intake`, `/intake/*`, `/intake_uploads/*`, `/_next/*`, favicon, robots | The public page shell. |

Not allowed on the public edge, even though they sit under `/api/v1/intake`:

- `POST /api/v1/intake/reset-password` sets a new password with only an email. That is not capture.
- `/api/v1/intake/admin/*` lists users and projects. Operators use Tailscale or studio.

Public capture is also capped at 60 requests/minute per client IP (`CF-Connecting-IP`, else the first `X-Forwarded-For`, else the socket). Over the cap: **429** `luxe_public_edge_rate_limited`.

Private hosts are unchanged. `127.0.0.1`, LAN addresses, and Tailscale `100.x` addresses do not match the public set, so `curl http://127.0.0.1:8000/api/v1/quotes` still reaches the router. `studio.empirebox.store` is not in the set either; Access remains the studio wall.

`empire-command-center/middleware.ts` applies the same allowlist when a request actually hits Next. API paths get the same 401 JSON. Other paths 307 to `/intake`. That matches the page behavior already live on `feature/drawing-standard`, and it covers `test-luxe` as well. It does not replace the backend gate while the tunnel sends `/api/v1/*` straight to port 8000.

## What operators must set

No new secret is required. The gate is on by default.

1. Deploy this commit to the backend cloudflared is pointing at (`empire-backend.service`, port 8000). Restart that one service. Until that restart, the live URL stays open — this repo change does not edit Cloudflare.
2. If `test-luxe` is brought back, deploy the same commit to the v10 backend (port 8010) before the tunnel origin is healthy.
3. Leave the luxe `Host` header alone. Do **not** set cloudflared `httpHostHeader` (or an origin rewrite) to `localhost` / `127.0.0.1`. The gate trusts `Host`, `X-Forwarded-Host`, and `X-Original-Host`. Rewriting them to a private name makes the request look local and the door opens again.
4. Optional extra public hostnames (added to the defaults, never a replacement):

   ```bash
   LUXE_PUBLIC_EDGE_HOSTS=preview-luxe.empirebox.store
   LUXE_PUBLIC_EDGE_RATE_PER_MINUTE=60
   LUXE_PUBLIC_EDGE_UPLOAD_PER_MINUTE=10
   ```

   Do not put `studio`, `api`, `forge`, or a Tailscale IP in that list. Those are operator paths.

5. Do not put all of `luxe.empirebox.store` behind Cloudflare Access. The intake page is the public capture surface. Access stays on `studio` and `api`.
6. Optional later: delete the luxe ingress rule that sends `/api/v1/*` directly to port 8000, so API calls go through Next on port 3005. The backend gate still has to stay, because a direct tunnel is how this leaked. Do not reload cloudflared until the backend gate is running.

Local and Tailscale cash path (unchanged, run on EmpireDell):

```bash
curl -sS -D - -o /dev/null http://127.0.0.1:8000/health
curl -sS -o /dev/null -w "quotes %{http_code}\n" "http://127.0.0.1:8000/api/v1/quotes?limit=1"
curl -sS -o /dev/null -w "invoices %{http_code}\n" "http://127.0.0.1:8000/api/v1/finance/invoices?limit=1"
curl -sS -D - -o /dev/null http://127.0.0.1:3005/
curl -sS -D - -o /dev/null "http://127.0.0.1:3005/?screen=pricing-studio"
```

Those curls must not send `Host: luxe.empirebox.store` or `X-Forwarded-Host: luxe.empirebox.store`.

## How to verify

App-level proof (no live customer data). Against a process running this commit:

```bash
# Public edge, simulated the way the tunnel hits port 8000.
# Expect 401 and error=luxe_public_edge_denied. Bodies are not printed.
python3 backend/scripts/luxe_public_edge_smoke.py \
  --base-url http://127.0.0.1:8000 \
  --host luxe.empirebox.store

# Private cash path on the same process. Must not be the public-edge denial.
python3 backend/scripts/luxe_public_edge_smoke.py \
  --base-url http://127.0.0.1:8000 \
  --expect-open
```

Single-route curl, safe to paste (prints only the error fields):

```bash
curl -sS -H 'Host: luxe.empirebox.store' \
  'http://127.0.0.1:8000/api/v1/quotes?limit=1' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("error"), d.get("detail"))'

curl -sS -o /dev/null -w "local quotes %{http_code}\n" \
  'http://127.0.0.1:8000/api/v1/quotes?limit=1'

curl -sS -H 'Host: luxe.empirebox.store' \
  -H 'Content-Type: application/json' \
  -d '{}' \
  'http://127.0.0.1:8000/api/v1/intake/login' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("error"), d.get("detail"))'
```

Expected after this commit is loaded:

- first command: `luxe_public_edge_denied Authentication required`
- second command: not `401` from this gate (the router’s own status; on a machine with the quote DB this is often `200`)
- third command: not `luxe_public_edge_denied` (validation or “invalid email” from the intake handler)

After `empire-backend.service` is restarted on the tunnel origin, from outside the tailnet:

```bash
python3 backend/scripts/luxe_public_edge_smoke.py \
  --base-url https://luxe.empirebox.store
```

Until that restart, the public URL can still return `200` JSON. A passing local smoke does not mean the internet door is closed yet.

Tests:

```bash
cd backend && pytest tests/test_luxe_public_edge.py -q
```

## Out of scope

- No change to Cloudflare Access on studio, api, or forge.
- No change to ApostApp public routes. They are a different hostname.
- No landing-page or ad work.
- `POST /api/v1/intake/reset-password` remains callable on localhost and on studio. It is closed on the public luxe hosts. It still sets a password from an email alone; do not expose it on a new public hostname.
