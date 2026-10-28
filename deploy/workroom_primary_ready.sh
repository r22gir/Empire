#!/bin/sh
# Family-edition ExecStartPre: refuse Workroom lock paths.
# Does not wait on Workroom's lock or health. Max-e (8011) and Maxine
# (8012) start even when empire-backend (port 8000) is down.
#
# Oct 23 2026: /tmp/empire_primary_worker.lock was unlinked (tmp cleanup)
# while Workroom still held flock on the old inode. The old guard ran
#   flock -n /tmp/empire_primary_worker.lock true
# which *creates* a new unlocked file (and can briefly steal Workroom's
# exclusive lock).
#
# This script never flocks Workroom's file. It only:
#   1. Refuses if EMPIRE_WORKER_LOCK is a Workroom path (realpath;
#      empty is refused on amp/maxine). Extra slashes like /tmp// fail too.
#   2. Exits 0. Family start does not depend on /proc/locks or
#      http://127.0.0.1:8000/health.
#
# Overrides for tests (never needed on the Dell):
#   EMPIRE_WORKROOM_LOCK, EMPIRE_WORKROOM_LOCK_LEGACY
set -eu

canon() {
  # realpath -m: missing files still collapse /tmp// and ..
  if command -v realpath >/dev/null 2>&1; then
    realpath -m -- "$1"
  else
    python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$1"
  fi
}

WORKROOM_LOCK="$(canon "${EMPIRE_WORKROOM_LOCK:-/home/rg/empire-data/run/empire_primary_worker.lock}")"
LEGACY_LOCK="$(canon "${EMPIRE_WORKROOM_LOCK_LEGACY:-/tmp/empire_primary_worker.lock}")"
OUR_LOCK="${EMPIRE_WORKER_LOCK:-}"
EDITION="${EMPIRE_EDITION:-}"

is_workroom_lock() {
  [ -z "$1" ] && return 1
  got="$(canon "$1")"
  [ "$got" = "$WORKROOM_LOCK" ] && return 0
  [ "$got" = "$LEGACY_LOCK" ] && return 0
  [ "$got" = "$(canon /tmp/empire_primary_worker.lock)" ] && return 0
  [ "$got" = "$(canon /home/rg/empire-data/run/empire_primary_worker.lock)" ] && return 0
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

echo "family lock path is not a Workroom lock; start does not wait on Workroom" >&2
exit 0
