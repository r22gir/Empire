#!/usr/bin/env bash
# Temp-dir tests for deploy/backup_family_data.sh. Never touches /data or /mnt/backup.
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=helpers.sh
source "$TEST_DIR/helpers.sh"

REPO_ROOT="$(cd "$TEST_DIR/../.." && pwd)"
SCRIPT="$REPO_ROOT/deploy/backup_family_data.sh"
assert_temp_path "${TMPDIR:-/tmp}/x"

ROOT="$(mktemp -d "${TMPDIR:-/tmp}/family-backup-test.XXXXXX")"
assert_temp_path "$ROOT"
assert_not_live_host_path "$ROOT"
trap 'rm -rf "$ROOT"' EXIT

DATA_ROOT="$ROOT/data"
BACKUP_DIR="$ROOT/backup"
mkdir -p \
  "$DATA_ROOT/amp/records" \
  "$DATA_ROOT/maxine" \
  "$DATA_ROOT/minimax-meter/state" \
  "$DATA_ROOT/family-help"
printf 'amp-row\n' >"$DATA_ROOT/amp/records/item.txt"
printf '# maxine memory\n' >"$DATA_ROOT/maxine/memory.md"
printf 'meter\n' >"$DATA_ROOT/minimax-meter/state/ok"
printf '# family memory\n' >"$DATA_ROOT/family-help/memory.md"
printf 'sqlite-placeholder\n' >"$DATA_ROOT/family-help/conversations.db"

export EMPIRE_OPS_TEST_MODE=1
export DATA_ROOT BACKUP_DIR
export TMPDIR="$ROOT"

echo "== backup: first nightly run =="
BACKUP_STAMP=20261011T031500 BACKUP_WEEKDAY=1 \
  "$SCRIPT" >"$ROOT/run1.log" 2>&1
expect_eq "$?" "0" "backup exits 0" || true

ARCHIVE="$BACKUP_DIR/daily/family-data-20261011T031500.tar.zst"
expect_file "$ARCHIVE" "timestamped tar.zst exists"
expect_file "${ARCHIVE}.listing.txt" "restore-test listing written"
expect_file_contains "${ARCHIVE}.listing.txt" "family-help/memory.md" "listing has family-help/memory.md"
expect_file_contains "${ARCHIVE}.listing.txt" "family-help/conversations.db" "listing has conversations.db"
expect_file_contains "${ARCHIVE}.listing.txt" "maxine/memory.md" "listing has maxine/memory.md"
expect_file_contains "${ARCHIVE}.listing.txt" "amp/records/item.txt" "listing has amp tree"

EXTRACT="$ROOT/extract"
mkdir -p "$EXTRACT"
tar --zstd -xf "$ARCHIVE" -C "$EXTRACT"
expect_file "$EXTRACT/family-help/memory.md" "extract restores memory.md"
expect_file "$EXTRACT/family-help/conversations.db" "extract restores conversations.db"
expect_file_contains "$ROOT/run1.log" "restore-test: passed" "restore-test logged pass"
expect_file_contains "$ROOT/run1.log" "skip weekly promote" "weekday 1 does not promote weekly"

echo "== backup: Sunday weekly promote =="
BACKUP_STAMP=20261012T031500 BACKUP_WEEKDAY=7 BACKUP_WEEK_NAME=family-data-week-2026-W41.tar.zst \
  "$SCRIPT" >"$ROOT/run2.log" 2>&1
expect_file "$BACKUP_DIR/weekly/family-data-week-2026-W41.tar.zst" "Sunday archive promoted to weekly"

echo "== backup: 14 daily + 8 weekly retention =="
# 13 more dailies (plus the two already created = 15) so prune keeps 14.
for i in $(seq -w 13 27); do
  BACKUP_STAMP="202610${i}T031500" BACKUP_WEEKDAY=1 \
    "$SCRIPT" >/dev/null
done
daily_count="$(find "$BACKUP_DIR/daily" -maxdepth 1 -name 'family-data-*.tar.zst' | wc -l | tr -d ' ')"
expect_eq "$daily_count" "14" "keeps 14 daily archives"

for w in 1 2 3 4 5 6 7 8 9; do
  BACKUP_STAMP="2026W${w}T031500" BACKUP_WEEKDAY=7 BACKUP_WEEK_NAME="family-data-week-2026-W0${w}.tar.zst" \
    "$SCRIPT" >/dev/null
done
weekly_count="$(find "$BACKUP_DIR/weekly" -maxdepth 1 -name 'family-data-*.tar.zst' | wc -l | tr -d ' ')"
expect_eq "$weekly_count" "8" "keeps 8 weekly archives"

echo "== backup: rclone offsite when RCLONE_REMOTE is set =="
FAKE_RCLONE="$ROOT/fake-rclone"
cat >"$FAKE_RCLONE" <<'EOF'
#!/usr/bin/env bash
echo "rclone $*" >> "${RCLONE_LOG}"
mkdir -p "${RCLONE_DEST_DIR}"
# mimic: rclone copy ARCHIVE REMOTE
src="$2"
cp "$src" "${RCLONE_DEST_DIR}/$(basename "$src")"
EOF
chmod +x "$FAKE_RCLONE"
export RCLONE_BIN="$FAKE_RCLONE"
export RCLONE_REMOTE="crypt:empire-family"
export RCLONE_LOG="$ROOT/rclone.log"
export RCLONE_DEST_DIR="$ROOT/offsite"
BACKUP_STAMP=20261101T031500 BACKUP_WEEKDAY=1 \
  "$SCRIPT" >"$ROOT/run-rclone.log" 2>&1
expect_file "$ROOT/offsite/family-data-20261101T031500.tar.zst" "rclone received archive copy"
expect_file_contains "$ROOT/rclone.log" "crypt:empire-family" "rclone targeted configured remote"
unset RCLONE_REMOTE RCLONE_BIN RCLONE_LOG RCLONE_DEST_DIR

echo "== backup: rclone failure is non-zero =="
FAIL_RCLONE="$ROOT/fail-rclone"
cat >"$FAIL_RCLONE" <<'EOF'
#!/usr/bin/env bash
exit 17
EOF
chmod +x "$FAIL_RCLONE"
set +e
RCLONE_BIN="$FAIL_RCLONE" RCLONE_REMOTE="crypt:broken" \
  BACKUP_STAMP=20261102T031500 BACKUP_WEEKDAY=1 \
  "$SCRIPT" >"$ROOT/run-rclone-fail.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "rclone failure exits non-zero ($rc)"
else
  fail "rclone failure should exit non-zero"
fi

echo "== backup: empty DATA_ROOT fails =="
EMPTY="$ROOT/empty-data"
mkdir -p "$EMPTY"
set +e
DATA_ROOT="$EMPTY" BACKUP_STAMP=20261103T031500 \
  "$SCRIPT" >"$ROOT/run-empty.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "missing family trees exit non-zero"
else
  fail "missing family trees should fail"
fi

echo "== backup: test mode refuses live paths =="
set +e
EMPIRE_OPS_TEST_MODE=1 DATA_ROOT=/data BACKUP_DIR="$BACKUP_DIR" \
  "$SCRIPT" >"$ROOT/run-live.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "test mode refuses /data"
else
  fail "test mode must refuse /data"
fi

set +e
EMPIRE_OPS_TEST_MODE=1 DATA_ROOT="$DATA_ROOT" BACKUP_DIR=/mnt/backup \
  "$SCRIPT" >"$ROOT/run-live-backup.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "test mode refuses /mnt/backup"
else
  fail "test mode must refuse /mnt/backup"
fi

finish
