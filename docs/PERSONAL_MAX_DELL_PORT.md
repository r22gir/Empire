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

`is_founder_edition()` treats unset, `main`, `workroom`, and `studio` as
Rafael’s Max. The meter logs all of those as `workroom`. Live Dell:
`EMPIRE_EDITION` is unset, `EMPIRE_DATA_DIR=/home/rg/empire-data`.

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
- `max/memory.md`

Use `git stash` for those three (below). Do not merge-then-restore.

## Origin vs the Dell’s 22 local commits

`origin/deploy/pr82-84-85` **does not have** the Dell’s local commits.

| Ref | SHA | On GitHub? |
|---|---|---|
| `origin/deploy/pr82-84-85` | `86f5889a` (`docs: deploy runbook for deploy/pr82-84-85`) | yes |
| Dell live HEAD | `92e3aeab` (`Merge PR #94 follow-up 9c34d3eb (family alias gate) locally`) | **no** |
| PR #94 follow-up | `9c34d3eb` (`Keep family editions off Rafael's repo aliases.`) | yes, only on `cursor/whatsapp-phase0-folders-8454` |

Checked 2026-10-11: `git cat-file` / GitHub API return no object for `92e3aeab`. `9c34d3eb` is not an ancestor of `origin/deploy/pr82-84-85`. PR #94 itself does **not** touch the three portal files — it is backend WhatsApp / alias-gate only. The three-file conflicts come from the Dell being **22 commits ahead of origin** (local merges + any other local portal edits on those hot files), not from GitHub.

Do **not** `git pull origin deploy/pr82-84-85` on the Dell before merging this PR: that would rewind or fight the 22 local commits. Stay on local `deploy/pr82-84-85` (`92e3aeab`) and merge the PR branch into it.

This PR now touches those three files only with **one-line hooks**. Screens, nav items, and screen ids live in:

- `empire-command-center/app/lib/founderScreens.ts`
- `empire-command-center/app/lib/founderPortal.tsx`

## Exact Dell conflict resolution (if merge still flags the three files)

Take **the Dell’s copy** of each file, then apply only the hunks below. Do not drop Dell-only screens / nav rows / union members.

### 1. `empire-command-center/app/lib/types.ts`

At the top of the file (first line):

```ts
import type { FounderScreenMode } from './founderScreens';
```

On the `ScreenMode` union, keep every Dell member and append `| FounderScreenMode`.

Origin-shaped line (if Dell did not add members):

```ts
export type ScreenMode = 'chat' | 'quote' | 'docs' | 'research' | 'video' | 'dashboard' | 'desks' | 'inbox' | 'memory-bank' | 'report' | 'tickets' | 'shipping' | 'costs' | 'mail' | 'tasks' | 'calendar' | 'telegram' | 'product-docs' | 'pricing' | 'pricing-studio' | 'business-profile' | 'presentation' | 'dev' | 'jobs' | 'invoices' | 'final-docs' | 'invoice' | FounderScreenMode;
```

If Dell already added members (example: `'whatsapp'`), resolved form is:

```ts
export type ScreenMode = 'chat' | /* …Dell members… */ | 'invoice' | 'whatsapp' | FounderScreenMode;
```

Do **not** replace Dell’s union with this PR’s origin-shaped list.

### 2. `empire-command-center/app/components/layout/LeftNav.tsx`

Keep the Dell `NAV_GROUPS` array unchanged (do not insert rows inside Command). Add the import next to the other local imports:

```ts
import { hookFounderNav } from '../../lib/founderPortal';
```

Immediately after the `NAV_GROUPS` closing `];`:

```ts
hookFounderNav(NAV_GROUPS);
```

That injects **Ayuda de ediciones familiares** and **Uso MiniMax** after `owner` without editing the Command items list. Safe if Dell already added other Command rows.

If a conflict marker lands inside the lucide import or the Command `items: [` block, take the Dell side of that block and keep only the two hook lines above.

### 3. `empire-command-center/app/CommandCenterApp.tsx`

Keep Dell’s screen import list and the long `if (activeScreen === …)` chain. Add one import under the types import:

```ts
import { hookFounderDeepLinks, renderFounderScreen } from './lib/founderPortal';
```

Immediately after `NAV_SCREEN_IDS` is created (after its closing `]);`):

```ts
hookFounderDeepLinks(SCREEN_DEEP_LINKS as Record<string, string>, NAV_SCREEN_IDS);
```

First lines of `renderCenterContent`:

```ts
  const renderCenterContent = () => {
    const founderScreen = renderFounderScreen(activeScreen);
    if (founderScreen) return founderScreen;
    // Dashboard renders product-specific pages
```

If conflict markers appear on the `SCREEN_DEEP_LINKS` / `NAV_SCREEN_IDS` literals or the inbox/memory-bank `if` chain, take the Dell side and keep only the three hook lines above. Do not add `FamilyHelpInbox` / `MinimaxUsageScreen` imports into this file.

Ready-to-run after the three files are resolved:

```bash
cd /home/rg/empire-repo-main
git add \
  empire-command-center/app/lib/types.ts \
  empire-command-center/app/components/layout/LeftNav.tsx \
  empire-command-center/app/CommandCenterApp.tsx
git status -sb   # expect the new founderScreens/founderPortal files from the PR, plus these three
```

## Exact Dell deploy steps (after Rafael approves)

On the Dell checkout `/home/rg/empire-repo-main`, edition studio,
port 8000, branch currently `deploy/pr82-84-85`. Founder process runs
as user `rg`. `/data/family-help` and `/data/minimax-meter` are owned
by `rg` with mode `700`.

```bash
# 1. Backup the live branch (do not switch to the family lane)
cd /home/rg/empire-repo-main
git status -sb
git branch backup/pr82-84-85-before-family-help-$(date +%Y%m%d)

# 2. Stash the three local files (do not copy/merge/restore)
git stash push -u -m "dell-local-before-family-help" -- \
  backend/app/config/business.json \
  backend/app/config/client_aliases.json \
  max/memory.md

# 3. Fetch and merge this draft branch into the Dell's local
#    deploy/pr82-84-85 (22 commits ahead of origin, HEAD 92e3aeab).
#    Do NOT git pull origin deploy/pr82-84-85 — that would rewind
#    the local commits. Do NOT checkout the family branch.
git fetch origin
git checkout deploy/pr82-84-85
git log -1 --oneline    # expect 92e3aeab (or later local HEAD)
git merge --no-ff origin/cursor/personal-max-family-meter-753b
# If the three portal files conflict, apply the hunks in
# "Exact Dell conflict resolution" above, then git add those files.

# 4. Put the three local files back
git stash pop

# 5. Env on the studio unit (systemd drop-in or backend/.env)
#    FAMILY_HELP_INBOX_DIR=/data/family-help
#    MINIMAX_METER_DIR=/data/minimax-meter
#    MINIMAX_H3_ENABLED=0
#    MINIMAX_FAMILY_TTS=0
#    EMPIRE_EDITION may stay unset (founder). Never amp/maxine.
# Dirs already exist on the Dell: owner rg, mode 700.
# mkdir -p /data/family-help/amp /data/family-help/maxine /data/minimax-meter
# chmod 700 /data/family-help /data/family-help/amp /data/family-help/maxine /data/minimax-meter
# chown rg:rg /data/family-help /data/minimax-meter

# 6. Python deps in the live venv on this checkout
cd /home/rg/empire-repo-main/backend
source /home/rg/empire-repo-main/backend/venv/bin/activate
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

After this PR’s MiniMax-M3.1-Flash-Preview commit: `systemctl --user restart empire-backend` (no portal rebuild; UI files unchanged — the dropdown reads the registry).

## How to test (before Dell)

```bash
cd backend && PYTHONPATH=. pytest tests/test_family_help.py tests/test_minimax_meter.py tests/test_minimax_meter_gates.py -q
cd empire-command-center && node --experimental-strip-types --test app/lib/familyHelp.test.ts app/lib/minimaxUsage.test.ts app/lib/founderScreens.test.ts
```

Studio click-through after deploy:

1. Owner’s Desk → **Ayuda de ediciones familiares**. Empty is OK if Max-e /
   Maxine have not filed tickets yet. A Maxine ticket must hide attachments
   until **Abrir adjuntos**. Reply only via **Sí, enviar**.
2. **Uso MiniMax** shows workroom / amp / maxine rows. Plan bar warning if
   `/token_plan/remains` is unread (founder text still works). H3 generate
   needs **Aprobar**.
3. Workroom jobs/quotes/invoices unchanged. Chat still works.

## Open questions

- MiniMax console Auto credit usage still ON (recommend OFF). H3/TTS stay
  off until `scripts/minimax_h3_probe.py --live`.
- H3 live probe uses the Pay-as-you-go v2 API: one POST
  `/v2/video_generation` (`content[]`, duration 4, 768P, 16:9), poll
  `/v2/query/video_generation/{task_id}` ~every 10s, download to the
  drafts folder (never post). `generated: true` means a real clip file
  exists. A subscription-key reject is printed (key redacted) and not
  retried. If credits cannot be read, the probe says so and records the
  local $0.32 / 4s 768P estimate.
- Cloudflare Access already fronts studio.empirebox.store; this PR does
  not add a second login gate.
