# Personal Max (studio :8000) — family-help inbox + MiniMax meter

Draft port onto `deploy/pr82-84-85`. **Do not merge or deploy from this note
until Rafael reviews.** This is the founder / Workroom lane. Do **not**
check out `cursor/minimax-family-meter-9e48` (PRs #100 → #101 → #102) on
the live Dell Workroom.

## What this branch adds

1. Founder inbox **Ayuda de ediciones familiares** — read and reply to
   Max-e (`amp/`) and Maxine (`maxine/`) tickets under
   `FAMILY_HELP_INBOX_DIR=/data/family-help`. Reply needs the **Sí, enviar**
   button (`X-Family-Help-Confirm: si-enviar`). Voice playback +
   transcript. Maxine attachments stay hidden until **Abrir adjuntos**.
   Founder reads both stores; editions never read each other.
2. **Uso MiniMax** — shared meter for Rafael’s own Max: reserved share,
   fail-closed hard stop at ~80% of the plan bar, per-edition files under
   `/data/minimax-meter`, founder aggregator, image-01 through the meter,
   H3/TTS flags default OFF, video only via `X-Minimax-Video-Confirm: aprobar`,
   LLM tool drafts only.

Review fixes from #101 / #102 are kept: extension+MIME upload checks,
`html.escape` on notify HTML, fail-closed quota, reservation locks, no
LLM-triggered spend.

## What this branch does **not** bring

- Family login gate / Cloudflare AMP session middleware
- AMP / Maxine edition features (Ask Max help chat button, edition nav,
  module hiding)
- 20% `INSTANCE_USAGE_CAP_PCT` enforcement on the studio process
- Family env examples (`deploy/empire-amp.env.example`,
  `deploy/empire-maxine.env.example`)

Studio edition is **not** limited by the family 20% text share. That cap
applies only when `EMPIRE_EDITION` is `amp` or `maxine`.

## Dell local files — do not touch

These are uncommitted local edits on `/home/rg/empire-repo-main`. This
PR does not include them and deploy must not overwrite them:

- `backend/app/config/business.json`
- `backend/app/config/client_aliases.json`
- `backend/app/services/max/memory.md` (or the live `max/memory.md` path)

If `git pull` reports a conflict on those three, abort and keep the Dell
copies.

## Exact Dell deploy steps (after Rafael approves)

On the Dell checkout `/home/rg/empire-repo-main`, edition `studio`,
port 8000, branch currently `deploy/pr82-84-85`:

```bash
# 1. Backup the live branch (do not switch to the family lane)
cd /home/rg/empire-repo-main
git status -sb
git branch backup/pr82-84-85-before-family-help-$(date +%Y%m%d)

# 2. Stash or copy the three local files if they are dirty
cp -a backend/app/config/business.json /tmp/dell-business.json
cp -a backend/app/config/client_aliases.json /tmp/dell-client_aliases.json
# memory.md path as it exists on the box:
cp -a backend/app/services/max/memory.md /tmp/dell-max-memory.md 2>/dev/null || true

# 3. Fetch and merge this draft branch into deploy/pr82-84-85
#    (only after Rafael says to). Do NOT checkout the family branch.
git fetch origin
git checkout deploy/pr82-84-85
git pull origin deploy/pr82-84-85
git merge --no-ff origin/cursor/personal-max-family-meter-753b

# 4. Restore local files if git touched them
cp -a /tmp/dell-business.json backend/app/config/business.json
cp -a /tmp/dell-client_aliases.json backend/app/config/client_aliases.json
cp -a /tmp/dell-max-memory.md backend/app/services/max/memory.md 2>/dev/null || true

# 5. Env on the studio unit (systemd drop-in or backend/.env)
#    FAMILY_HELP_INBOX_DIR=/data/family-help
#    MINIMAX_METER_DIR=/data/minimax-meter
#    MINIMAX_H3_ENABLED=0
#    MINIMAX_FAMILY_TTS=0
#    EMPIRE_EDITION=workroom   # or unset / main — never amp/maxine
sudo mkdir -p /data/family-help/amp /data/family-help/maxine /data/minimax-meter
sudo chmod 700 /data/family-help /data/family-help/amp /data/family-help/maxine /data/minimax-meter

# 6. Python deps (no new pins expected; still run it)
cd /home/rg/empire-repo-main/backend
# use the live venv on the box
source /home/rg/empire-repo/backend/venv/bin/activate
pip install -r requirements.txt

# 7. Restart backend (one service at a time)
systemctl --user restart empire-backend
systemctl --user status empire-backend --no-pager

# 8. Rebuild portal and restart
cd /home/rg/empire-repo-main/empire-command-center
npm run build
systemctl --user restart empire-portal
systemctl --user status empire-portal --no-pager
```

Do **not** start a second uvicorn on :8000.

## How to test (before Dell)

```bash
cd backend && PYTHONPATH=. pytest tests/test_family_help.py tests/test_minimax_meter.py tests/test_minimax_meter_gates.py -q
cd empire-command-center && node --experimental-strip-types --test app/lib/familyHelp.test.ts app/lib/minimaxUsage.test.ts
```

Studio click-through after deploy:

1. Owner’s Desk → **Ayuda de ediciones familiares**. Empty is OK if Max-e /
   Maxine have not filed tickets yet. A Maxine ticket must hide attachments
   until **Abrir adjuntos**. Reply only via **Sí, enviar**.
2. **Uso MiniMax** shows workroom / amp / maxine rows. Plan bar warning if
   `/token_plan/remains` is unread. H3 generate needs **Aprobar**.
3. Workroom jobs/quotes/invoices unchanged. Chat still works.

## Open questions

- Live `/data/family-help` and `/data/minimax-meter` ownership on the Dell
  (which OS user runs empire-backend vs amp vs maxine). Founder process
  must be able to read both edition folders.
- Whether Auto credit usage is still ON in the MiniMax console (recommend
  OFF). H3/TTS stay off until `scripts/minimax_h3_probe.py --live`.
- Cloudflare Access already fronts studio.empirebox.store; this PR does
  not add a second login gate.
