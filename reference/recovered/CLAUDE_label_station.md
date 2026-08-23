# Label Station + EmpireDell Ground Truth

*Append to `CLAUDE.md`, or add as Claude Project knowledge. Facts below were
verified by direct tool calls on 2026-07-26, not inferred. Where a belief was
wrong, the correction is stated plainly so it does not get re-learned.*

---

## 1. Label Station (module)

A weigh-and-label PWA for **Antojitos Reales** — Colombian food sold by weight.
Operator picks a product, enters weight in lb + oz, the app prices it and renders
a thermal label as a PNG. The phone saves that PNG to Photos; the operator prints
it from the **Katasymbol / SUPVAN T50M Pro** phone app.

**It is not a printer integration.** iOS Safari has no Web Bluetooth and browsers
have no raw sockets, so no web app can drive that printer directly. The two-step
hand-off through Katasymbol is deliberate, not unfinished. Do not propose
"connecting the printer" — the only path that removes the step is replacing the
hardware with an AirPrint label printer (e.g. Brother QL-810W, ~$170).

### Paths

| Thing | Path |
|---|---|
| Module | `/home/rg/empire-repo-main/backend/app/modules/label_station.py` |
| App (single HTML file) | `.../backend/app/modules/static/weigh-and-label.html` |
| Package marker | `.../backend/app/modules/__init__.py` (empty, required) |
| Wired in | `backend/app/main.py` — `from app.modules.label_station import router as label_station_router` |

### URLs

- App: **`https://label.empirebox.store/label/`** — the trailing `/label/` is
  required. The bare hostname hits the FastAPI root and returns the API JSON
  banner, which Chrome downloads as `document.txt`. This looks like a failure
  and is not.
- API: `/label/api/health`, `/label/api/catalog` (GET, PUT)

### Data

Table `label_catalog` in `/home/rg/empire-data/empire.db`, keyed on `business`
(currently `empire_workroom`). Products cap at 10. The catalog is **shared** —
anyone with the link can change prices for everyone.

The app degrades gracefully: if `./api/health` does not answer, it falls back to
on-device storage, so a backend outage never blocks a sale.

### Deploying an update

FastAPI serves the HTML with `FileResponse`, read fresh per request. **A UI
change is a file copy — no restart, no service touch:**

```bash
cp new-weigh-and-label.html \
   /home/rg/empire-repo-main/backend/app/modules/static/weigh-and-label.html
```

Changing `label_station.py` does require the backend process to restart — see §2.

---

## 2. EmpireDell ground truth

### Repo paths

- `/home/rg/empire-repo-main` and `/ssd/rg/empire-repo-main` are **the same
  filesystem** (bind mount, `/dev/sdb1`). Interchangeable.
- `/home/rg/empire-repo` is a **separate legacy tree**. Not a symlink. Stale.
  It is the path that has caused repeated confusion; treat any reference to it
  as drift.
- Active branch: `feature/drawing-standard`.

### Backend process

- Real FastAPI app entry is **`backend/app/main.py`**. `backend/main.py` is a
  26-line stub that constructs nothing — adding routers there is dead code.
- Routers load via `load_router("app.routers.<name>", "<prefix>", ["<tag>"])`
  or `app.include_router(...)` at the bottom of `app/main.py`.
- The live backend is a **hand-started background process**, not systemd.
  Relaunch pattern:

```bash
cd /home/rg/empire-repo-main/backend
nohup venv/bin/python3 -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --timeout-keep-alive 65 \
  > /tmp/empire-uvicorn.log 2>&1 &
```

- **`empire-backend.service` points at the legacy tree and is inactive.**
  Starting it launches the wrong code. Do not `systemctl restart empire-backend`.
  **On reboot, systemd will start the legacy tree and the label station will
  vanish.** This is the largest known fragility. See §4.

### Cloudflare tunnel — the expensive one

**Tunnel `empire-main` (`8ff5514f-e950-4ad1-8518-90bc3e6f6605`) is managed from
the Cloudflare Zero Trust dashboard. Its ingress comes from the control plane.
`/home/rg/.cloudflared/empire-main-local.yml` is decorative — editing it changes
nothing.**

This is not obvious. `ExecStart` uses `--config`, not `--token`, which looks
local. The tell is `version=N` in the cloudflared log line *"Updated to new
configuration"* — a version number only appears when ingress arrives from
Cloudflare. A valid YAML edit, a passing `ingress validate`, a matching
`ingress rule` check, and two clean restarts all produced no change before this
was found.

**To add or change a hostname:** Cloudflare dashboard → Zero Trust → Networks →
Tunnels → `empire-main` → **Routes** → Add route → Published application.
Connectors pick it up in under a minute. No terminal, no restart.

`cloudflared tunnel route dns` creates a **DNS record only**. It does not add an
ingress rule. Success there means nothing about routing.

### Module registries

Three exist and disagree. Canonical is
`backend/app/services/max/ecosystem_catalog.py` (`EMPIRE_CATALOG`, read by MAX's
system prompt). The other two —
`backend/app/routers/max/router.py` (`_EMPIRE_MODULES`) and
`backend/app/services/max/empire_module_knowledge.py` → `docs/EMPIRE_MODULE_REGISTRY.md`
— are drift. Register in the canonical one; report the others, do not silently
"fix" them mid-task.

### Environment gotchas

- **`sqlite3` CLI is not installed.** Use the venv python:
  `venv/bin/python3 -c "import sqlite3; ..."`. Do not apt-install it.
- `curl -I` sends HEAD. FastAPI routes declared GET-only answer **405**. That is
  correct behaviour, not a failure. Use `curl -sI -X GET` or plain `curl -s`.
- A background job logs `no such table: crypto_payments` every 15 minutes.
  Pre-existing, unrelated, ignorable.

---

## 3. Working conventions

- **Verify an edit landed; never assume a replacement matched.** A string
  replacement that silently no-ops looks identical to success. This exact
  failure shipped a broken catalog sync: the target function had been rewritten
  in an earlier pass, the patch matched nothing, and no error was raised.
  After editing, grep for the change.
- Pass tasks down, pass conclusions back up — and **verify conclusions with
  tool-level calls rather than trusting returned summaries.**
- Agents (MAX, Harry, M3) must **never send email to clients or customers**.
  Automated mail is limited to internal notices to the founder.
- Before any tunnel change: back up, `ingress validate`, then verify the
  *existing* hostnames still resolve. Rollback triggers on `studio`, `api`, or
  `forge` breaking — not just the new hostname.
- Prefer stopping and reporting over improvising when reality contradicts the
  instructions. A half-deployed change that appears to work is worse than a
  clean failure.

---

## 4. Open items

1. **systemd / supervision.** Give the label station its own unit and port
   (e.g. 8100) with its own tunnel route, so an EmpireBox restart or a reboot
   does not take down label printing. Separately, fix or retire
   `empire-backend.service` so a reboot stops launching the legacy tree.
   *This is the top infrastructure risk.*
2. **QR placeholder.** Labels currently encode `https://example.com/menu`.
   Replace with the real Antojitos Reales URL before selling anything with a
   label on it. Keep it under ~47 characters — at 203 dpi a longer URL drops
   below 3 dots per module and stops scanning reliably.
3. **Bare-hostname redirect.** Cloudflare → Rules → Redirect Rules: hostname
   `label.empirebox.store` AND path `/` → `https://label.empirebox.store/label/`,
   301. Scope to that hostname so `api` and `studio` are untouched.
4. **Landing page.** `antojitos-reales.html` built but not deployed. Photos are
   Wikimedia Commons CC BY-SA placeholders — replace with real food photos
   before publishing. Order email is a placeholder; Cloudflare Email Routing on
   `empirebox.store` is the cheapest route to a working `pedidos@` address.
5. **Duplicate cloudflared processes.** Two were serving the same config (user
   session + systemd). One was killed 2026-07-26. Worth confirming only the
   systemd instance remains.
