#!/bin/sh
# Family-edition ExecStartPre: Workroom must be up, and this process
# must not take Workroom's primary-worker lock.
#
# Oct 23 2026: /tmp/empire_primary_worker.lock was unlinked (tmp cleanup)
# while Workroom still held flock on the old inode. The old guard ran
#   flock -n /tmp/empire_primary_worker.lock true
# which *creates* a new unlocked file, then treated Workroom as down and
# refused every Max-e / Maxine start.
#
# This script:
#   1. Refuses if EMPIRE_WORKER_LOCK is a Workroom path (or empty on Maxine).
#   2. Treats Workroom as ready if an *existing* lock file is held
#      (open without O_CREAT — never create the Workroom lock).
#   3. Otherwise accepts http://127.0.0.1:8000/health as proof Workroom
#      is up (same process, stale or missing lock name).
#   4. Never holds the Workroom lock after the check.
#
# Overrides for tests (never needed on the Dell):
#   EMPIRE_WORKROOM_LOCK, EMPIRE_WORKROOM_LOCK_LEGACY,
#   EMPIRE_WORKROOM_HEALTH_URL
set -eu

WORKROOM_LOCK="${EMPIRE_WORKROOM_LOCK:-/home/rg/empire-data/run/empire_primary_worker.lock}"
LEGACY_LOCK="${EMPIRE_WORKROOM_LOCK_LEGACY:-/tmp/empire_primary_worker.lock}"
HEALTH_URL="${EMPIRE_WORKROOM_HEALTH_URL:-http://127.0.0.1:8000/health}"
OUR_LOCK="${EMPIRE_WORKER_LOCK:-}"
EDITION="${EMPIRE_EDITION:-}"

is_workroom_lock() {
  case "$1" in
    "$WORKROOM_LOCK"|"$LEGACY_LOCK"|/tmp/empire_primary_worker.lock|/home/rg/empire-data/run/empire_primary_worker.lock)
      return 0
      ;;
  esac
  return 1
}

if [ -z "$OUR_LOCK" ]; then
  if [ "$EDITION" = "maxine" ] || [ "$EDITION" = "amp" ]; then
    echo "family edition must set EMPIRE_WORKER_LOCK to its own path (not the Workroom lock)" >&2
    exit 1
  fi
elif is_workroom_lock "$OUR_LOCK"; then
  echo "family edition must not use the Workroom lock: $OUR_LOCK" >&2
  exit 1
fi

# Open an existing lock only. flock FILE creates the file — that is the bug.
lock_is_held() {
  path="$1"
  [ -e "$path" ] || return 1
  (
    exec 3<"$path" || exit 1
    if flock -n 3; then
      exit 1
    fi
    exit 0
  )
}

if lock_is_held "$WORKROOM_LOCK" || lock_is_held "$LEGACY_LOCK"; then
  exit 0
fi

health_ok() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null
    return $?
  fi
  HEALTH_URL="$HEALTH_URL" python3 -c 'import os, urllib.request; urllib.request.urlopen(os.environ["HEALTH_URL"], timeout=2)'
}

if health_ok; then
  echo "Workroom lock path missing or unlocked; 127.0.0.1:8000 is healthy" >&2
  exit 0
fi

echo "Workroom not holding primary lock yet and 127.0.0.1:8000 is not healthy" >&2
exit 1
