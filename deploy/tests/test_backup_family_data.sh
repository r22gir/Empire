#!/usr/bin/env bash
# Temp-dir tests for deploy/backup_family_data.sh.
# Never touches /data or /media/rg/BACKUP1.
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
BACKUP_VOLUME="$ROOT/BACKUP1"
BACKUP_DIR="$BACKUP_VOLUME/family-backups"
KEY_FILE="$ROOT/empire-backup-key"
mkdir -p \
  "$DATA_ROOT/amp/records" \
  "$DATA_ROOT/maxine" \
  "$DATA_ROOT/minimax-meter/state" \
  "$DATA_ROOT/family-help" \
  "$BACKUP_VOLUME"
touch "$BACKUP_VOLUME/.mounted"
openssl rand -base64 32 >"$KEY_FILE"

printf 'amp-row\n' >"$DATA_ROOT/amp/records/item.txt"
printf '# maxine memory\n' >"$DATA_ROOT/maxine/memory.md"
printf 'meter\n' >"$DATA_ROOT/minimax-meter/state/ok"
printf '# family memory\n' >"$DATA_ROOT/family-help/memory.md"
printf 'sqlite-placeholder\n' >"$DATA_ROOT/family-help/conversations.db"

decrypt_to() {
  local src="$1" dest="$2"
  gpg --batch --yes --quiet --decrypt --pinentry-mode loopback \
    --passphrase-file "$KEY_FILE" -o "$dest" "$src" 2>/dev/null
}

export EMPIRE_OPS_TEST_MODE=1
export DATA_ROOT BACKUP_DIR BACKUP_VOLUME
export BACKUP_KEY_FILE="$KEY_FILE"
export TMPDIR="$ROOT"

echo "== backup: defaults target BACKUP1 family-backups =="
expect_file_contains "$SCRIPT" '/media/rg/BACKUP1/family-backups' \
  "script default BACKUP_DIR is /media/rg/BACKUP1/family-backups"
expect_file_contains "$SCRIPT" '/media/rg/BACKUP1' \
  "script default BACKUP_VOLUME is /media/rg/BACKUP1"

echo "== backup: first nightly run (encrypted) =="
set +e
BACKUP_STAMP=20261011T031500 BACKUP_WEEKDAY=1 \
  "$SCRIPT" >"$ROOT/run1.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  echo "---- run1.log ----"
  cat "$ROOT/run1.log"
  echo "---- end ----"
fi
expect_eq "$rc" "0" "backup exits 0"

ARCHIVE="$BACKUP_DIR/daily/family-data-20261011T031500.tar.zst.gpg"
expect_file "$ARCHIVE" "encrypted timestamped archive exists"
if [[ "$ARCHIVE" != *:* && "$(basename "$ARCHIVE")" != *:* ]]; then
  pass "dest filename has no colons"
else
  fail "dest filename must not contain colons: $ARCHIVE"
fi
bad_names="$(find "$BACKUP_DIR" -name '*:*' 2>/dev/null | wc -l | tr -d ' ')"
expect_eq "$bad_names" "0" "no colon filenames on dest volume"

PLAIN="$ROOT/plain1.tar.zst"
decrypt_to "$ARCHIVE" "$PLAIN"
LISTING="$ROOT/list1.txt"
tar --zstd -tf "$PLAIN" >"$LISTING"
expect_file_contains "$LISTING" "family-help/memory.md" "listing has family-help/memory.md"
expect_file_contains "$LISTING" "family-help/conversations.db" "listing has conversations.db"
expect_file_contains "$LISTING" "maxine/memory.md" "listing has maxine/memory.md"
expect_file_contains "$LISTING" "amp/records/item.txt" "listing has amp tree"

EXTRACT="$ROOT/extract"
mkdir -p "$EXTRACT"
tar --zstd -xf "$PLAIN" -C "$EXTRACT"
expect_file "$EXTRACT/family-help/memory.md" "extract restores memory.md"
expect_file "$EXTRACT/family-help/conversations.db" "extract restores conversations.db"
expect_file_contains "$ROOT/run1.log" "restore-test: passed" "restore-test logged pass"
expect_file_contains "$ROOT/run1.log" "skip weekly promote" "weekday 1 does not promote weekly"
expect_file_contains "$ROOT/run1.log" "encrypting" "encrypt step ran"

echo "== backup: Sunday weekly promote =="
BACKUP_STAMP=20261012T031500 BACKUP_WEEKDAY=7 BACKUP_WEEK_NAME=family-data-week-2026-W41 \
  "$SCRIPT" >"$ROOT/run2.log" 2>&1
expect_file "$BACKUP_DIR/weekly/family-data-week-2026-W41.tar.zst.gpg" \
  "Sunday encrypted archive promoted to weekly"

echo "== backup: 14 daily + 8 weekly retention =="
for i in $(seq -w 13 27); do
  BACKUP_STAMP="202610${i}T031500" BACKUP_WEEKDAY=1 \
    "$SCRIPT" >/dev/null
done
daily_count="$(find "$BACKUP_DIR/daily" -maxdepth 1 -name 'family-data-*.tar.zst.gpg' ! -name '*.part*' | wc -l | tr -d ' ')"
expect_eq "$daily_count" "14" "keeps 14 daily archives"

for w in 1 2 3 4 5 6 7 8 9; do
  BACKUP_STAMP="2026W${w}T031500" BACKUP_WEEKDAY=7 BACKUP_WEEK_NAME="family-data-week-2026-W0${w}" \
    "$SCRIPT" >/dev/null
done
weekly_count="$(find "$BACKUP_DIR/weekly" -maxdepth 1 -name 'family-data-*.tar.zst.gpg' ! -name '*.part*' | wc -l | tr -d ' ')"
expect_eq "$weekly_count" "8" "keeps 8 weekly archives"

echo "== backup: FAT split when over FAT_MAX_BYTES =="
# Grow the tree so the encrypted blob exceeds a tiny FAT cap.
dd if=/dev/urandom of="$DATA_ROOT/amp/records/chunk.bin" bs=1024 count=4 status=none
# Tiny limit forces split of the encrypted blob.
FAT_MAX_BYTES=200 BACKUP_STAMP=20261201T031500 BACKUP_WEEKDAY=1 \
  "$SCRIPT" >"$ROOT/run-split.log" 2>&1
SPLIT0="$BACKUP_DIR/daily/family-data-20261201T031500.tar.zst.gpg.part00"
SPLIT1="$BACKUP_DIR/daily/family-data-20261201T031500.tar.zst.gpg.part01"
expect_file "$SPLIT0" "FAT split wrote part00"
if [[ -f "$SPLIT1" ]]; then
  pass "FAT split wrote part01"
else
  # Encrypted payload might still fit in 200 bytes on a tiny fixture; force a larger tree.
  fail "expected a second FAT part at $SPLIT1"
fi
sz0="$(stat -c %s "$SPLIT0")"
if [[ "$sz0" -le 200 ]]; then
  pass "part00 is <= FAT_MAX_BYTES ($sz0)"
else
  fail "part00 exceeds FAT_MAX_BYTES: $sz0"
fi
expect_file_contains "$ROOT/run-split.log" "restore-test: passed" "restore-test works after split"
expect_file_contains "$ROOT/run-split.log" "splitting" "log says archive was split"

echo "== backup: rclone offsite when RCLONE_REMOTE is set =="
FAKE_RCLONE="$ROOT/fake-rclone"
cat >"$FAKE_RCLONE" <<'EOF'
#!/usr/bin/env bash
echo "rclone $*" >> "${RCLONE_LOG}"
mkdir -p "${RCLONE_DEST_DIR}"
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
expect_file "$ROOT/offsite/family-data-20261101T031500.tar.zst.gpg" "rclone received encrypted archive"
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

echo "== backup: unmounted BACKUP1 fails (no write to stub/root) =="
UNMOUNTED="$ROOT/unmounted-vol"
mkdir -p "$UNMOUNTED"
set +e
BACKUP_VOLUME="$UNMOUNTED" BACKUP_DIR="$UNMOUNTED/family-backups" \
  BACKUP_STAMP=20261104T031500 \
  "$SCRIPT" >"$ROOT/run-unmounted.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "unmounted BACKUP1 exits non-zero"
else
  fail "unmounted BACKUP1 should fail"
fi
expect_file_contains "$ROOT/run-unmounted.log" "not mounted" "clear unmounted error"
expect_file_contains "$ROOT/run-unmounted.log" "root disk" "refuses writing to the root disk"
if [[ ! -d "$UNMOUNTED/family-backups/daily" ]]; then
  pass "did not create dest tree on unmounted volume"
else
  fail "must not mkdir dest on unmounted volume"
fi

echo "== backup: missing key fails =="
set +e
BACKUP_KEY_FILE="$ROOT/missing-key" BACKUP_STAMP=20261105T031500 \
  "$SCRIPT" >"$ROOT/run-nokey.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "missing key exits non-zero"
else
  fail "missing key should fail"
fi
expect_file_contains "$ROOT/run-nokey.log" "backup key missing" "missing-key message"

echo "== backup: test mode refuses live paths =="
set +e
EMPIRE_OPS_TEST_MODE=1 DATA_ROOT=/data BACKUP_DIR="$BACKUP_DIR" BACKUP_VOLUME="$BACKUP_VOLUME" \
  "$SCRIPT" >"$ROOT/run-live.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "test mode refuses /data"
else
  fail "test mode must refuse /data"
fi

set +e
EMPIRE_OPS_TEST_MODE=1 DATA_ROOT="$DATA_ROOT" \
  BACKUP_DIR=/media/rg/BACKUP1/family-backups \
  BACKUP_VOLUME=/media/rg/BACKUP1 \
  "$SCRIPT" >"$ROOT/run-live-backup.log" 2>&1
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  pass "test mode refuses /media/rg/BACKUP1"
else
  fail "test mode must refuse /media/rg/BACKUP1"
fi

finish
