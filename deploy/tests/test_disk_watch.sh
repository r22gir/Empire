#!/usr/bin/env bash
# Temp-dir tests for deploy/disk_watch.sh. Never reads live df or /data.
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=helpers.sh
source "$TEST_DIR/helpers.sh"

REPO_ROOT="$(cd "$TEST_DIR/../.." && pwd)"
SCRIPT="$REPO_ROOT/deploy/disk_watch.sh"

ROOT="$(mktemp -d "${TMPDIR:-/tmp}/disk-watch-test.XXXXXX")"
assert_temp_path "$ROOT"
assert_not_live_host_path "$ROOT"
trap 'rm -rf "$ROOT"' EXIT

SCAN="$ROOT/scan"
mkdir -p \
  "$SCAN/proj/node_modules/pkg" \
  "$SCAN/app/.next/cache" \
  "$SCAN/home/.cache/pip" \
  "$SCAN/site/uploads" \
  "$SCAN/tmp"
printf 'blob\n' >"$SCAN/proj/node_modules/pkg/index.js"
printf 'build\n' >"$SCAN/app/.next/cache/x"
printf 'wheel\n' >"$SCAN/home/.cache/pip/x"
printf 'photo\n' >"$SCAN/site/uploads/a.jpg"
printf 'tmp\n' >"$SCAN/tmp/junk"

USAGE="$ROOT/usage.txt"
HOOK="$ROOT/alert-hook.sh"
ALERT_LOG="$ROOT/alerts.log"
cat >"$HOOK" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "$ALERT_LOG"
exit 0
EOF
chmod +x "$HOOK"

export EMPIRE_OPS_TEST_MODE=1
export SCAN_ROOTS="$SCAN"
export DISK_WATCH_MOUNTS="/ /data /media/rg/BACKUP1"
export DISK_USAGE_FILE="$USAGE"
export MAX_ALERT_HOOK="$HOOK"
export TMPDIR="$ROOT"
export TOP_N=5

echo "== disk_watch: defaults include BACKUP1 =="
expect_file_contains "$SCRIPT" '/media/rg/BACKUP1' \
  "default mounts include /media/rg/BACKUP1"
expect_file_contains "$SCRIPT" 'SCAN_ROOTS="${SCAN_ROOTS:-/ /data}"' \
  "default SCAN_ROOTS is / and /data, not BACKUP1"

echo "== disk_watch: below warn exits 0, no alert =="
printf '/ 10\n/data 20\n/media/rg/BACKUP1 15\n' >"$USAGE"
set +e
"$SCRIPT" >"$ROOT/ok.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "0" "healthy disk exits 0"
if [[ ! -f "$ALERT_LOG" ]]; then
  pass "no alert when disk is healthy"
else
  fail "alert hook should not run when healthy"
fi
expect_file_contains "$ROOT/ok.log" "top 5 space users under $SCAN" "logs du top space users"
expect_file_contains "$ROOT/ok.log" "node_modules" "logs node_modules grower"

echo "== disk_watch: 80% warn exits 1 and alerts =="
printf '/ 80\n/data 40\n/media/rg/BACKUP1 15\n' >"$USAGE"
set +e
"$SCRIPT" >"$ROOT/warn.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "1" "80% warn exits 1"
expect_file_contains "$ROOT/alerts.log" "EmpireDell disk warn" "warn alert delivered via hook"

echo "== disk_watch: 90% critical on /data exits 2 =="
printf '/ 10\n/data 90\n/media/rg/BACKUP1 15\n' >"$USAGE"
set +e
"$SCRIPT" >"$ROOT/crit.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "2" "90% critical exits 2"
expect_file_contains "$ROOT/alerts.log" "EmpireDell disk critical" "critical alert delivered"

echo "== disk_watch: missing alert mechanism logs and exits non-zero =="
printf '/ 85\n/data 10\n/media/rg/BACKUP1 15\n' >"$USAGE"
set +e
MAX_ALERT_HOOK="$ROOT/missing-hook" \
  "$SCRIPT" >"$ROOT/no-alert.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "unavailable alert path exits non-zero ($rc)"
else
  fail "unavailable alert path should exit non-zero"
fi
expect_file_contains "$ROOT/no-alert.log" "no Max notification/email mechanism available" \
  "logs when Max notify/email is absent"
expect_file_contains "$ROOT/no-alert.log" "empirebox2026@gmail.com" \
  "logged alert names empirebox2026@gmail.com"

echo "== disk_watch: BACKUP1 90% is critical =="
printf '/ 10\n/data 10\n/media/rg/BACKUP1 90\n' >"$USAGE"
set +e
"$SCRIPT" >"$ROOT/backup1-crit.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "2" "BACKUP1 90% exits 2"
expect_file_contains "$ROOT/backup1-crit.log" "/media/rg/BACKUP1 90%" "logs BACKUP1 usage"

echo "== disk_watch: unmounted BACKUP1 is a warning =="
printf '/ 10\n/data 10\n/media/rg/BACKUP1 unmounted\n' >"$USAGE"
set +e
"$SCRIPT" >"$ROOT/backup1-unmounted.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "1" "unmounted BACKUP1 exits 1 (warn)"
expect_file_contains "$ROOT/backup1-unmounted.log" "not mounted" "logs BACKUP1 unmounted"

echo "== disk_watch: cleanup is dry-run and does not delete =="
set +e
"$SCRIPT" --cleanup >"$ROOT/cleanup.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "0" "cleanup dry-run exits 0"
expect_file_contains "$ROOT/cleanup.log" "CANDIDATE" "cleanup lists candidates"
expect_file_contains "$ROOT/cleanup.log" "node_modules" "cleanup lists node_modules"
expect_file_contains "$ROOT/cleanup.log" ".next" "cleanup lists .next"
expect_file_contains "$ROOT/cleanup.log" ".cache/pip" "cleanup lists pip cache"
expect_file_contains "$ROOT/cleanup.log" "uploads" "cleanup lists uploads"
expect_file "$SCAN/proj/node_modules/pkg/index.js" "cleanup did not delete node_modules"
expect_file "$SCAN/app/.next/cache/x" "cleanup did not delete .next"
expect_file "$SCAN/site/uploads/a.jpg" "cleanup did not delete uploads"

echo "== disk_watch: SIGPIPE-safe top-N on a fat tree, healthy usage =="
python3 - "$SCAN/many" <<'PY'
import os, sys
root = sys.argv[1]
os.makedirs(root, exist_ok=True)
for i in range(5500):
    d = os.path.join(root, f"d{i}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "f"), "w", encoding="utf-8") as fh:
        fh.write("x")
PY
printf '/ 10\n/data 10\n/media/rg/BACKUP1 15\n' >"$USAGE"
rm -f "$ALERT_LOG"
set +e
trap '' PIPE
"$SCRIPT" >"$ROOT/sigpipe.log" 2>&1
rc=$?
trap - PIPE
set -e
expect_eq "$rc" "0" "fat-tree scan under ignored SIGPIPE exits 0"
if grep -q "Broken pipe" "$ROOT/sigpipe.log"; then
  fail "fat-tree scan must not log Broken pipe"
else
  pass "fat-tree scan has no Broken pipe"
fi
top_n_lines="$(grep -c " du " "$ROOT/sigpipe.log" || true)"
if [[ "${top_n_lines:-0}" -ge 1 ]]; then
  pass "fat-tree scan logged top-N du lines ($top_n_lines)"
else
  fail "fat-tree scan should log top-N du lines"
fi
expect_file_contains "$ROOT/sigpipe.log" "top 5 space users under $SCAN" \
  "fat-tree scan still logs the top-N header"

echo "== disk_watch: du timeout logs and continues, exit 0 =="
TIMEOUT_SCAN="$ROOT/timeout-scan"
mkdir -p "$TIMEOUT_SCAN/leaf"
printf 'x\n' >"$TIMEOUT_SCAN/leaf/f"
STUB_BIN="$ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/du" <<'EOF'
#!/usr/bin/env bash
sleep 30
exit 0
EOF
chmod +x "$STUB_BIN/du"
printf '/ 10\n/data 10\n/media/rg/BACKUP1 15\n' >"$USAGE"
set +e
PATH="$STUB_BIN:$PATH" DU_TIMEOUT_S=1 SCAN_ROOTS="$TIMEOUT_SCAN" \
  "$SCRIPT" >"$ROOT/timeout.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "0" "du timeout continues and exits 0"
expect_file_contains "$ROOT/timeout.log" "du timed out for $TIMEOUT_SCAN" \
  "logs du timed out for the scan root"

echo "== disk_watch: BACKUP1 is not du/find'd unless DISK_WATCH_SCAN_BACKUP=1 =="
BACKUP_FAKE="$ROOT/backup1"
mkdir -p "$BACKUP_FAKE/recup_dir.1" "$BACKUP_FAKE/keep"
printf 'blob\n' >"$BACKUP_FAKE/recup_dir.1/x"
printf 'keep\n' >"$BACKUP_FAKE/keep/y"
printf '/ 10\n/data 10\n/media/rg/BACKUP1 15\n' >"$USAGE"
set +e
BACKUP_WATCH_VOLUME="$BACKUP_FAKE" \
  SCAN_ROOTS="$SCAN $BACKUP_FAKE" \
  DISK_WATCH_SCAN_BACKUP=0 \
  "$SCRIPT" >"$ROOT/backup-skip.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "0" "BACKUP1 skip path exits 0"
expect_file_contains "$ROOT/backup-skip.log" "BACKUP1 scan disabled" \
  "logs that BACKUP1 du/find is skipped"
if grep -q "top 5 space users under $BACKUP_FAKE" "$ROOT/backup-skip.log"; then
  fail "BACKUP1 must not be du'd when DISK_WATCH_SCAN_BACKUP is unset"
else
  pass "BACKUP1 was not du'd by default"
fi
if grep -q "recup_dir" "$ROOT/backup-skip.log"; then
  fail "BACKUP1 recup_dir must not appear in grower/du output by default"
else
  pass "BACKUP1 recup_dir was not scanned by default"
fi

set +e
BACKUP_WATCH_VOLUME="$BACKUP_FAKE" \
  SCAN_ROOTS="$SCAN $BACKUP_FAKE" \
  DISK_WATCH_SCAN_BACKUP=1 \
  "$SCRIPT" >"$ROOT/backup-scan.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "0" "BACKUP1 opt-in scan exits 0"
expect_file_contains "$ROOT/backup-scan.log" "top 5 space users under $BACKUP_FAKE" \
  "DISK_WATCH_SCAN_BACKUP=1 dus BACKUP1"

echo "== disk_watch: unit ExecStart/Documentation stay on empire-ops =="
UNIT="$REPO_ROOT/deploy/systemd/user/empire-disk-watch.service"
TIMER="$REPO_ROOT/deploy/systemd/user/empire-disk-watch.timer"
expect_file_contains "$UNIT" 'ExecStart=%h/empire-ops/deploy/disk_watch.sh' \
  "unit ExecStart is ~/empire-ops/deploy/disk_watch.sh"
expect_file_contains "$UNIT" 'Documentation=file://%h/empire-ops/deploy/README.md' \
  "unit Documentation points at the ops README copy"
expect_file_contains "$UNIT" \
  'Documentation=file://%h/empire-ops/docs/runbooks/empiredell-family-data.md' \
  "unit Documentation points at the ops runbook copy"
expect_file_contains "$TIMER" 'Documentation=file://%h/empire-ops/deploy/README.md' \
  "timer Documentation points at the ops README copy"
if grep -q 'empire-repo' "$UNIT"; then
  fail "disk-watch unit must not point at ~/empire-repo"
else
  pass "disk-watch unit does not mention empire-repo"
fi

echo "== disk_watch: test mode refuses live scan / live df =="
set +e
SCAN_ROOTS=/ DATA_ROOT=/ \
  "$SCRIPT" >"$ROOT/live-scan.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "test mode refuses live SCAN_ROOT=/"
else
  fail "test mode must refuse live /"
fi

set +e
unset DISK_USAGE_FILE
DISK_USAGE_FILE="" SCAN_ROOTS="$SCAN" \
  "$SCRIPT" >"$ROOT/live-df.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "test mode refuses live df"
else
  fail "test mode must require DISK_USAGE_FILE"
fi

finish
