# Deploy runbook: deploy/pr82-84-85 -> EmpireDell live (/home/rg/empire-repo-main)

Run on the Dell as user `rg`. The backend and portal are USER systemd units, so use
`systemctl --user` (no sudo needed). Rollback assets: /data/rg/scratch/predeploy-20261009/

Branch contents: running branch feature/drawing-standard @766c5163 + the 34 uncommitted/untracked
Dell files (customer files under uploads/ and workroom_inputs/ were deliberately NOT pushed to
GitHub; they stay in place in the live checkout and in predeploy-20261009/untracked.tgz)
+ PR #85 + PR #82 + PR #84 + PR #86, with conflicts resolved and the channel rule fixed.

## 1. Fresh backup (code + DB + memory)
```bash
set -e
cd /home/rg/empire-repo-main
B=/data/rg/scratch/predeploy-$(date +%Y%m%d-%H%M); mkdir -p $B
git rev-parse HEAD > $B/head.txt; git status --short > $B/status.txt; git diff > $B/uncommitted.patch
cp max/memory.md $B/memory.md.live
python3 - "$B" <<'PY'
import sqlite3,sys
s=sqlite3.connect('/home/rg/empire-data/empire.db'); d=sqlite3.connect(sys.argv[1]+'/empire.db'); s.backup(d); d.close(); s.close()
PY
echo "backup in $B"; echo "export B=$B" > /data/rg/scratch/last-backup.env
```

## 2. Switch the checkout to the deploy branch (services still running old code in memory)
```bash
cd /home/rg/empire-repo-main
git fetch origin deploy/pr82-84-85:refs/remotes/origin/deploy/pr82-84-85
# park the 34 working changes that are already contained in the branch (tracked edits + the 3 untracked code files)
git stash push -u -m "pre-deploy-20261009" -- \
  backend/app/config/business.json backend/app/config/client_aliases.json backend/app/main.py \
  backend/app/routers/max/router.py empire-command-center/app/api/docs/read/route.ts \
  empire-command-center/app/api/docs/serve/route.ts empire-command-center/app/globals.css max/memory.md \
  backend/app/routers/review_addons.py empire-command-center/app/api/docs/doc-access.ts empire-command-center/app/review
git checkout -B deploy/pr82-84-85 origin/deploy/pr82-84-85
source /data/rg/scratch/last-backup.env; cp $B/memory.md.live max/memory.md   # keep Max's live memory (newer than the branch copy)
git status --short | head        # expect only max/memory.md modified + the untracked uploads/ and workroom_inputs/ files
```

## 3. Python deps (3 new packages for the 3D engine) and import check
```bash
cd /home/rg/empire-repo-main/backend
venv/bin/pip install "trimesh>=4.0.0" "shapely>=2.0.0" "mapbox-earcut>=2.0.0"
venv/bin/python -c "import app.main; print('import ok')" 2>&1 | tail -3
```

## 4. Build the frontend (before restarting anything)
```bash
cd /home/rg/empire-repo-main/empire-command-center
npm run build            # `next build --webpack`; takes about 1-3 min, no package.json changes so no npm install
```

## 5. Restart (backend first, then portal) and health checks
```bash
systemctl --user restart empire-backend
sleep 8; curl -s localhost:8000/health
systemctl --user restart empire-portal
sleep 8; curl -s -o /dev/null -w "portal %{http_code}\n" localhost:3005/
curl -s -o /dev/null -w "jobs kanban %{http_code}\n" localhost:8000/api/v1/jobs/kanban
curl -s -o /dev/null -w "schedule %{http_code}\n" localhost:8000/api/v1/schedule/events
curl -s -o /dev/null -w "costs %{http_code}\n" localhost:8000/api/v1/costs/summary
systemctl --user status empire-backend empire-portal --no-pager | grep -E "Active|Loaded"
journalctl --user -u empire-backend -n 40 --no-pager | grep -iE "error|traceback" | head
```
Then open Max: / (home), `?screen=jobs` (job board), `?screen=calendar` (schedule), Costs -> Free tiers.
Do NOT load the six live jobs yet: backend/data/seeds/live_jobs.json does not exist in the repo
(the seed script needs that file; dry-run was only verified with a synthetic 6-name template).

## Rollback (code)
```bash
systemctl --user stop empire-portal empire-backend
cd /home/rg/empire-repo-main
git checkout -f feature/drawing-standard          # back to 766c5163
git stash pop                                      # restores the 34 pre-deploy working changes (the stash above)
source /data/rg/scratch/last-backup.env; cp $B/memory.md.live max/memory.md
cd empire-command-center && npm run build          # rebuild old frontend (or restore a saved .next)
systemctl --user start empire-backend; sleep 8; systemctl --user start empire-portal
curl -s localhost:8000/health
```
If `git stash pop` complains, the full pre-deploy state is also at
/data/rg/scratch/predeploy-20261009/{uncommitted.patch,untracked.tgz}: `git apply uncommitted.patch; tar xzf untracked.tgz`.

## Rollback (database, only if a migration broke data; this loses writes made after the backup)
```bash
systemctl --user stop empire-backend
cp /home/rg/empire-data/empire.db /data/rg/scratch/empire.db.broken-$(date +%s)
cp /data/rg/scratch/predeploy-20261009/empire.db /home/rg/empire-data/empire.db     # or $B/empire.db for the fresh backup
systemctl --user start empire-backend
```
The deploy only adds tables (schedule_events, pickup_dropoff_logs, free-tier quota tables) and columns
via CREATE IF NOT EXISTS / safe ALTER, so a code rollback normally needs no DB restore.
