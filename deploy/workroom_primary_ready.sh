#!/bin/sh
# Family-edition ExecStartPre: Workroom must be up, and this process
# must not take Workroom's primary-worker lock.
#
# Oct 23 2026: /tmp/empire_primary_worker.lock was unlinked (tmp cleanup)
# while Workroom still held flock on the old inode. The old guard ran
#   flock -n /tmp/empire_primary_worker.lock true
# which *creates* a new unlocked file (and can briefly steal Workroom's
# exclusive lock), then treated Workroom as down.
#
# This script never flocks Workroom's file. It:
#   1. Refuses if EMPIRE_WORKER_LOCK is a Workroom path (realpath;
#      empty is refused on amp/maxine). Extra slashes like /tmp// fail too.
#   2. Treats Workroom as ready if /proc/locks or lslocks shows a holder
#      on an *existing* Workroom lock inode (read-only; never flock).
#   3. Otherwise accepts http://127.0.0.1:8000/health.
#
# Overrides for tests (never needed on the Dell):
#   EMPIRE_WORKROOM_LOCK, EMPIRE_WORKROOM_LOCK_LEGACY,
#   EMPIRE_WORKROOM_HEALTH_URL
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
HEALTH_URL="${EMPIRE_WORKROOM_HEALTH_URL:-http://127.0.0.1:8000/health}"
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

# Read-only: does some process hold an exclusive flock/posix lock on this inode?
# Never flock the file — that would steal Workroom's exclusive lock.
lock_is_held() {
  path="$1"
  [ -e "$path" ] || return 1
  LOCK_PATH="$path" python3 -c '
import os, subprocess, sys

path = os.environ["LOCK_PATH"]
try:
    st = os.stat(path)
except OSError:
    sys.exit(1)
maj, min_ = os.major(st.st_dev), os.minor(st.st_dev)
ino = st.st_ino
needles = {
    f"{maj:x}:{min_:x}:{ino}",
    f"{maj}:{min_}:{ino}",
    f"{maj:02x}:{min_:02x}:{ino}",
}
try:
    with open("/proc/locks", encoding="ascii", errors="replace") as fh:
        for line in fh:
            for needle in needles:
                if needle in line.split():
                    sys.exit(0)
except OSError:
    pass
try:
    out = subprocess.check_output(["lslocks", "-u", "-n", "-o", "INODE,PATH"], text=True)
except (OSError, subprocess.CalledProcessError):
    sys.exit(1)
real = os.path.realpath(path)
for line in out.splitlines():
    parts = line.split(None, 1)
    if len(parts) != 2:
        continue
    if parts[0] == str(ino) and os.path.realpath(parts[1]) == real:
        sys.exit(0)
sys.exit(1)
'
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
