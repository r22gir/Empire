#!/bin/bash
# Quiet portal deploy (2026-10-04).
#
# Old way: `npm run build` inside the live app dir overwrote .next while empire-portal kept
# serving it, so pages and route handlers broke for ~2 minutes mid-use (Final Docs showed
# "Could not load the document index" at 7:40 PM), then a restart.
#
# New way: build a copy of the sources in a staging dir on the same disk (live keeps serving
# the old build untouched), wait briefly for a quiet moment, swap the finished .next in with
# two renames, restart (Next is ready in <1s), verify, and roll back automatically on failure.
#
# usage: scripts/quiet-deploy.sh <tag> [extra routes to check...]
#   STAGE_PATCH='cmd'  run in the staging copy before building
#   WAIT_IDLE=120  max seconds to wait for ~30s without phone/remote traffic (0 = don't wait)
set -u
APP=/home/rg/empire-repo-main/empire-command-center
STAGE=/home/rg/empire-repo-main/.portal-stage
TAG=${1:-deploy}; shift || true
L=/tmp/build-$TAG.log
WAIT_IDLE=${WAIT_IDLE:-120}
cd "$APP" || exit 1

timeout 300 npx tsc --noEmit -p . > /tmp/tsc-$TAG.log 2>&1; T=$?; echo "TSC=$T"; [ $T -ne 0 ] && head -20 /tmp/tsc-$TAG.log && exit 1

mkdir -p "$STAGE"
rsync -a --delete --exclude node_modules --exclude .next --exclude .git "$APP/" "$STAGE/"
# node_modules: hard links into the stage (same disk, no extra space); refreshed each run
rm -rf "$STAGE/node_modules" && cp -al "$APP/node_modules" "$STAGE/node_modules"
rm -rf "$STAGE/.next"
# optional one-off tweak of the staged copy only (never the working tree), e.g. to leave out unfinished work
[ -n "${STAGE_PATCH:-}" ] && (cd "$STAGE" && bash -c "$STAGE_PATCH")

(cd "$STAGE" && TMPDIR=/home/rg/tmp-archive/next NODE_ENV=production NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 EMPIRE_LANE=main npm run build > "$L" 2>&1; echo "BUILD_EXIT=$?" >> "$L")
tail -1 "$L"; grep -q "BUILD_EXIT=0" "$L" || { grep -n "rror" "$L" | head -20; echo "build failed; live untouched"; exit 1; }
[ -f "$STAGE/.next/prerender-manifest.json" ] && [ -f "$STAGE/.next/BUILD_ID" ] || { echo "incomplete build; live untouched"; exit 1; }

# Wait (bounded) for ~30s with no remote client requests reaching the backend.
if [ "$WAIT_IDLE" -gt 0 ]; then
  waited=0
  while [ $waited -lt "$WAIT_IDLE" ]; do
    n=$(journalctl --user -u empire-backend --since "-30s" --no-pager -o cat 2>/dev/null | grep -E '^INFO: +[0-9.]+:[0-9]+ - "' | grep -vcE '^INFO: +127\.0\.0\.1:')
    [ "${n:-0}" -eq 0 ] && break
    sleep 10; waited=$((waited + 10))
  done
  echo "idle-wait=${waited}s (remote requests in last 30s: ${n:-0})"
fi

PREV="$APP/.next.prev"
rm -rf "$PREV"
mv "$APP/.next" "$PREV" && mv "$STAGE/.next" "$APP/.next" || { echo "swap failed"; [ -d "$PREV" ] && [ ! -d "$APP/.next" ] && mv "$PREV" "$APP/.next"; exit 1; }
systemctl --user restart empire-portal.service
for i in $(seq 1 40); do c=$(curl -s -o /dev/null -w "%{http_code}" localhost:3005/); [ "$c" = 200 ] && break; sleep 0.5; done
if [ "$c" != 200 ]; then
  echo "new build not healthy (home=$c); rolling back"
  rm -rf "$APP/.next.bad"; mv "$APP/.next" "$APP/.next.bad" && mv "$PREV" "$APP/.next"
  systemctl --user restart empire-portal.service; sleep 2
  echo "rolled back: home=$(curl -s -o /dev/null -w '%{http_code}' localhost:3005/)"; exit 1
fi
echo "home=$c active=$(systemctl --user is-active empire-portal.service) build=$(cat "$APP/.next/BUILD_ID")"
for u in / /classic /intake /api/v1/max/health /api/v1/docs-hub?group=1 "$@"; do printf "%s %s\n" "$(curl -s -o /dev/null -w '%{http_code}' "localhost:3005$u")" "$u"; done | tr '\n' ' '; echo
