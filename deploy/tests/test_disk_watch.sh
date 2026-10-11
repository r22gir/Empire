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
export DISK_WATCH_MOUNTS="/ /data"
export DISK_USAGE_FILE="$USAGE"
export MAX_ALERT_HOOK="$HOOK"
export TMPDIR="$ROOT"
export TOP_N=5

echo "== disk_watch: below warn exits 0, no alert =="
printf '/ 10\n/data 20\n' >"$USAGE"
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
printf '/ 80\n/data 40\n' >"$USAGE"
set +e
"$SCRIPT" >"$ROOT/warn.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "1" "80% warn exits 1"
expect_file_contains "$ROOT/alerts.log" "EmpireDell disk warn" "warn alert delivered via hook"

echo "== disk_watch: 90% critical on /data exits 2 =="
printf '/ 10\n/data 90\n' >"$USAGE"
set +e
"$SCRIPT" >"$ROOT/crit.log" 2>&1
rc=$?
set -e
expect_eq "$rc" "2" "90% critical exits 2"
expect_file_contains "$ROOT/alerts.log" "EmpireDell disk critical" "critical alert delivered"

echo "== disk_watch: missing alert mechanism logs and exits non-zero =="
printf '/ 85\n/data 10\n' >"$USAGE"
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
