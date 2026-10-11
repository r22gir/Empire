#!/usr/bin/env bash
# EmpireDell family-edition data backup onto BACKUP1 (external FAT32).
# Packs /data/amp, /data/maxine, /data/minimax-meter, and /data/family-help
# (including memory.md and conversations.db) into an encrypted tar.zst.
#
# Every *.db is copied with sqlite3 .backup (VACUUM INTO fallback) so a live
# backend cannot produce a torn conversations.db in the archive. Restore-test
# opens each restored db and runs PRAGMA integrity_check.
#
# Destination is the vfat/FAT32 drive BACKUP1 (~931G) at /media/rg/BACKUP1.
# That filesystem has no Unix permissions, a 4GiB-1 max file size, and may
# be unplugged. This script refuses to write if the volume is not mounted
# (so backups never land on the root disk), encrypts because FAT cannot
# protect files, splits chunks over 4GiB-1, and uses colon-free names.
#
# Env:
#   BACKUP_VOLUME    Mount to require (default /media/rg/BACKUP1)
#   BACKUP_DIR       Dest root (default /media/rg/BACKUP1/family-backups)
#   BACKUP_KEY_FILE  Symmetric key (default ~/.config/empire-backup/key)
#   BACKUP_KEY_COPY_MARKER  Touch-file after you copy the key off-box
#                    (default ~/.config/empire-backup/key-copied)
#   FAT_MAX_BYTES    Max dest file size (default 4294967295 = 4GiB-1)
#   RCLONE_REMOTE    If set, copy encrypted dest files offsite
#   RCLONE_BIN       rclone binary (default rclone)
#   BACKUP_STAMP     Override timestamp (tests; no colons)
#   BACKUP_WEEKDAY   ISO weekday 1-7 (tests; 7 = Sunday weekly promote)
#   BACKUP_INCLUDE_MAX=1  Also write a SEPARATE Max/Workroom archive
#   MAX_DATA_ROOT    Workroom /data root (default /data)
#   MAX_BACKUP_DIR   Dest for Max set (default /media/rg/BACKUP1/max-backups)
#   MAX_KEY_FILE     Separate Max key (default ~/.config/empire-backup/max-key)
#   MAX_DB_PATHS     Extra Max/Workroom db files (default ~/empire-data/empire.db)
#   EMPIRE_OPS_TEST_MODE=1  Refuse live /data and BACKUP1 paths
#
# Exit: 0 on success; non-zero on any failure.
set -euo pipefail

# umask applies to the local work dir (ext4/tmpfs), not FAT dest files.
# Never chmod/chown anything on BACKUP_DIR — vfat ignores Unix mode.
umask 077

LOG_PREFIX="[family-backup]"

BACKUP_VOLUME="${BACKUP_VOLUME:-/media/rg/BACKUP1}"
BACKUP_DIR="${BACKUP_DIR:-/media/rg/BACKUP1/family-backups}"
BACKUP_KEY_FILE="${BACKUP_KEY_FILE:-${HOME}/.config/empire-backup/key}"
BACKUP_KEY_COPY_MARKER="${BACKUP_KEY_COPY_MARKER:-${HOME}/.config/empire-backup/key-copied}"
# FAT32 hard limit is 4GiB-1. Stay at/under that so copy never fails mid-file.
FAT_MAX_BYTES="${FAT_MAX_BYTES:-4294967295}"
DATA_ROOT="${DATA_ROOT:-/data}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"
RCLONE_BIN="${RCLONE_BIN:-rclone}"
KEEP_DAILY="${KEEP_DAILY:-14}"
KEEP_WEEKLY="${KEEP_WEEKLY:-8}"
BACKUP_STAMP="${BACKUP_STAMP:-$(date +%Y%m%dT%H%M%S)}"
BACKUP_WEEKDAY="${BACKUP_WEEKDAY:-$(date +%u)}"
BACKUP_INCLUDE_MAX="${BACKUP_INCLUDE_MAX:-0}"
MAX_DATA_ROOT="${MAX_DATA_ROOT:-/data}"
MAX_BACKUP_DIR="${MAX_BACKUP_DIR:-/media/rg/BACKUP1/max-backups}"
MAX_KEY_FILE="${MAX_KEY_FILE:-${HOME}/.config/empire-backup/max-key}"
MAX_KEY_COPY_MARKER="${MAX_KEY_COPY_MARKER:-${HOME}/.config/empire-backup/max-key-copied}"
MAX_DB_PATHS="${MAX_DB_PATHS:-${HOME}/empire-data/empire.db}"
MAX_SOURCE_NAMES_DEFAULT="workroom empire max"

FAMILY_SOURCE_NAMES=(amp maxine minimax-meter family-help)
FAMILY_CRITICAL_REL_PATHS=(
  "family-help/memory.md"
  "family-help/conversations.db"
  "maxine/memory.md"
  "maxine/conversations.db"
)

# Per-set state (filled by run_one_set).
WORK_DIR=""
PLAIN_ARCHIVE=""
CRYPT_ARCHIVE=""
CRYPT_EXT="gpg"
DEST_CRYPT=""
LISTING_PATH=""
PUBLISHED=()
SOURCE_NAMES=()
CRITICAL_REL_PATHS=()
EXTRA_DB_PATHS=()
SET_DATA_ROOT=""
SET_BACKUP_DIR=""
SET_KEY_FILE=""
SET_PREFIX=""
STAGE_DIR=""

log() { printf '%s %s %s\n' "$(date -Iseconds)" "$LOG_PREFIX" "$*"; }
die() { log "ERROR: $*"; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

path_is_temp() {
  local p="$1"
  case "$p" in
    /tmp/*|/var/tmp/*) return 0 ;;
    *)
      if [[ -n "${TMPDIR:-}" ]]; then
        case "$p" in
          "${TMPDIR%/}"/*) return 0 ;;
        esac
      fi
      return 1
      ;;
  esac
}

assert_test_safe() {
  [[ "${EMPIRE_OPS_TEST_MODE:-}" == "1" ]] || return 0
  path_is_temp "$DATA_ROOT" || die "EMPIRE_OPS_TEST_MODE refuses live DATA_ROOT=$DATA_ROOT"
  path_is_temp "$BACKUP_DIR" || die "EMPIRE_OPS_TEST_MODE refuses live BACKUP_DIR=$BACKUP_DIR"
  path_is_temp "$BACKUP_VOLUME" || die "EMPIRE_OPS_TEST_MODE refuses live BACKUP_VOLUME=$BACKUP_VOLUME"
  if [[ "$BACKUP_INCLUDE_MAX" == "1" ]]; then
    path_is_temp "$MAX_DATA_ROOT" || die "EMPIRE_OPS_TEST_MODE refuses live MAX_DATA_ROOT=$MAX_DATA_ROOT"
    path_is_temp "$MAX_BACKUP_DIR" || die "EMPIRE_OPS_TEST_MODE refuses live MAX_BACKUP_DIR=$MAX_BACKUP_DIR"
  fi
}

usage() {
  cat <<'EOF'
Usage: backup_family_data.sh [--help] [--include-max]

Nightly EmpireDell backup of family edition trees under DATA_ROOT
to the BACKUP1 external drive (vfat/FAT32 at /media/rg/BACKUP1).

  ./deploy/backup_family_data.sh

Every *.db is sqlite3 .backup'd (or VACUUM INTO) before tar so a live
backend cannot tear conversations.db. Restore-test runs PRAGMA integrity_check.

Fails non-zero if BACKUP1 is not mounted (will not write to the root disk).
Archives are encrypted with ~/.config/empire-backup/key (never commit that file).
Copy that key to a second safe place once, then:
  date -Iseconds > ~/.config/empire-backup/key-copied

  --include-max   Also back up personal Max / Workroom /data dirs and db
                  into a SEPARATE archive under max-backups, encrypted with
                  a SEPARATE key (~/.config/empire-backup/max-key).
                  Off by default; same as BACKUP_INCLUDE_MAX=1.

Restore is documented in deploy/README.md.
EOF
}

cleanup_work() {
  if [[ -n "${WORK_DIR:-}" && -d "${WORK_DIR:-}" ]]; then
    rm -rf "$WORK_DIR"
  fi
}

# Copy onto vfat without chmod/chown. GNU cp --no-preserve avoids a chmod
# syscall that FAT cannot honor and that some mounts treat as an error.
fat_cp() {
  local src="$1" dest="$2"
  if cp --no-preserve=mode,ownership -f "$src" "$dest" 2>/dev/null; then
    return 0
  fi
  cat "$src" >"$dest"
}

volume_is_mounted() {
  local vol="$1"
  if [[ -n "${MOUNTPOINT_BIN:-}" ]]; then
    "$MOUNTPOINT_BIN" -q "$vol"
    return $?
  fi
  if [[ "${EMPIRE_OPS_TEST_MODE:-}" == "1" ]]; then
    [[ -f "$vol/.mounted" ]]
    return $?
  fi
  if command -v mountpoint >/dev/null 2>&1; then
    mountpoint -q "$vol"
    return $?
  fi
  findmnt -n --target "$vol" >/dev/null 2>&1
}

require_backup_volume() {
  local vol="$BACKUP_VOLUME"
  [[ "$BACKUP_STAMP" != *:* ]] || die "BACKUP_STAMP must not contain colons (FAT32 filenames): $BACKUP_STAMP"

  if [[ "${EMPIRE_OPS_TEST_MODE:-}" == "1" ]]; then
    if ! volume_is_mounted "$vol"; then
      die "BACKUP1 is not mounted at $vol. Plug in the external drive BACKUP1 (~931G, vfat/FAT32) and mount it at $vol. Refusing to write family backups onto the root disk."
    fi
  else
    if [[ ! -d "$vol" ]] || ! volume_is_mounted "$vol"; then
      die "BACKUP1 is not mounted at $vol. Plug in the external drive BACKUP1 (~931G, vfat/FAT32) and mount it at $vol. Refusing to write family backups onto the root disk."
    fi
    local vol_dev root_dev
    vol_dev="$(stat -c %d "$vol")"
    root_dev="$(stat -c %d /)"
    if [[ "$vol_dev" == "$root_dev" ]]; then
      die "BACKUP1 path $vol is on the root filesystem — the drive is not mounted. Refusing to write family backups onto the root disk."
    fi
  fi

  case "$BACKUP_DIR" in
    "$vol"|"$vol"/*) ;;
    *)
      die "BACKUP_DIR=$BACKUP_DIR is not under BACKUP1 volume $vol (refusing to write elsewhere)"
      ;;
  esac
  if [[ "$BACKUP_INCLUDE_MAX" == "1" ]]; then
    case "$MAX_BACKUP_DIR" in
      "$vol"|"$vol"/*) ;;
      *)
        die "MAX_BACKUP_DIR=$MAX_BACKUP_DIR is not under BACKUP1 volume $vol"
        ;;
    esac
  fi
}

require_key() {
  local key="$1" label="$2"
  [[ -f "$key" ]] || die "$label key missing: $key — create one (never commit it): mkdir -p ~/.config/empire-backup && openssl rand -base64 32 > $key && chmod 600 $key"
  [[ -s "$key" ]] || die "$label key is empty: $key"
}

warn_if_key_not_copied() {
  local marker="$1" key="$2" label="$3"
  if [[ -f "$marker" && -s "$marker" ]]; then
    log "$label key-copy marker present: $marker"
    return 0
  fi
  log "WARN: no key-copy marker for $label at $marker. The encryption key $key has no second copy recorded. Copy it once to a second safe place (not BACKUP1 — a password manager, paper in a safe, or another encrypted stick), then: date -Iseconds > $marker"
}

# Prefer age when the key is an age identity; otherwise gpg symmetric.
detect_crypt() {
  local key="$1"
  if [[ -n "${BACKUP_CRYPT:-}" ]]; then
    CRYPT_EXT="$BACKUP_CRYPT"
    return
  fi
  if command -v age >/dev/null 2>&1 && grep -q '^AGE-SECRET-KEY-' "$key" 2>/dev/null; then
    CRYPT_EXT="age"
    return
  fi
  require_cmd gpg
  CRYPT_EXT="gpg"
}

encrypt_file() {
  local src="$1" dest="$2" key="$3"
  case "$CRYPT_EXT" in
    age)
      require_cmd age
      require_cmd age-keygen
      local recip
      recip="$(age-keygen -y "$key")"
      age -e -r "$recip" -o "$dest" "$src" || die "age encrypt failed"
      ;;
    gpg)
      require_cmd gpg
      gpg --batch --yes --quiet --symmetric --cipher-algo AES256 \
        --pinentry-mode loopback \
        --passphrase-file "$key" \
        -o "$dest" "$src" || die "gpg encrypt failed"
      ;;
    *)
      die "unsupported BACKUP_CRYPT=$CRYPT_EXT (use age or gpg)"
      ;;
  esac
  [[ -s "$dest" ]] || die "encrypted archive is empty: $dest"
}

decrypt_file() {
  local src="$1" dest="$2" key="$3"
  case "$src" in
    *.age)
      require_cmd age
      age -d -i "$key" -o "$dest" "$src" || die "age decrypt failed"
      ;;
    *)
      require_cmd gpg
      gpg --batch --yes --quiet --decrypt --pinentry-mode loopback \
        --passphrase-file "$key" \
        -o "$dest" "$src" || die "gpg decrypt failed"
      ;;
  esac
}

# Consistent snapshot of a live SQLite file. Never tar the open file.
sqlite_hot_copy() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  rm -f "$dest"
  local dest_sql
  dest_sql="${dest//\'/\'\'}"
  if sqlite3 "$src" ".backup '${dest_sql}'" 2>/dev/null && [[ -s "$dest" ]]; then
    log "sqlite hot-copy .backup $src -> $dest"
    return 0
  fi
  rm -f "$dest"
  if sqlite3 "$src" "VACUUM INTO '${dest_sql}';" 2>/dev/null && [[ -s "$dest" ]]; then
    log "sqlite hot-copy VACUUM INTO $src -> $dest"
    return 0
  fi
  die "sqlite hot-copy failed for $src (need sqlite3 .backup or VACUUM INTO). Is the file a SQLite database?"
}

pragma_integrity_check() {
  local db="$1"
  local result
  result="$(sqlite3 "$db" "PRAGMA integrity_check;")" || die "could not open restored db $db"
  if [[ "$result" != "ok" ]]; then
    die "PRAGMA integrity_check failed for $db: $result"
  fi
  log "PRAGMA integrity_check ok: $db"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--include-max" ]]; then
  BACKUP_INCLUDE_MAX=1
  shift
fi

assert_test_safe
require_cmd tar
require_cmd zstd
require_cmd find
require_cmd date
require_cmd stat
require_cmd split
require_cmd sqlite3

[[ -d "$DATA_ROOT" ]] || die "DATA_ROOT does not exist: $DATA_ROOT"
require_backup_volume
require_key "$BACKUP_KEY_FILE" "family"
warn_if_key_not_copied "$BACKUP_KEY_COPY_MARKER" "$BACKUP_KEY_FILE" "family"

if [[ "$BACKUP_INCLUDE_MAX" == "1" ]]; then
  require_key "$MAX_KEY_FILE" "max"
  if [[ "$(readlink -f "$MAX_KEY_FILE")" == "$(readlink -f "$BACKUP_KEY_FILE")" ]]; then
    die "MAX_KEY_FILE must be a SEPARATE file from the family key (got $MAX_KEY_FILE)"
  fi
  warn_if_key_not_copied "$MAX_KEY_COPY_MARKER" "$MAX_KEY_FILE" "max"
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/family-backup-work.XXXXXX")"
trap cleanup_work EXIT
mkdir -p "$WORK_DIR/gnupg"
chmod 700 "$WORK_DIR/gnupg"
export GNUPGHOME="$WORK_DIR/gnupg"

collect_sources() {
  local name path
  SOURCES=()
  MISSING=()
  for name in "${SOURCE_NAMES[@]}"; do
    path="$SET_DATA_ROOT/$name"
    if [[ -d "$path" ]]; then
      SOURCES+=("$name")
    else
      MISSING+=("$name")
    fi
  done
  if [[ ${#SOURCES[@]} -eq 0 && ${#EXTRA_DB_PATHS[@]} -eq 0 ]]; then
    die "no $SET_PREFIX data directories found under $SET_DATA_ROOT (${SOURCE_NAMES[*]})"
  fi
  if [[ ${#MISSING[@]} -gt 0 ]]; then
    log "WARN: missing $SET_PREFIX source dirs (will skip): ${MISSING[*]}"
  fi
}

include_critical_files() {
  local rel path
  EXTRA_FILES=()
  for rel in "${CRITICAL_REL_PATHS[@]:-}"; do
    path="$SET_DATA_ROOT/$rel"
    if [[ -f "$path" ]]; then
      EXTRA_FILES+=("$rel")
      log "including critical file $rel"
    fi
  done
}

# Build a local stage: trees minus live *.db, then sqlite hot-copies in place.
stage_tree() {
  STAGE_DIR="$WORK_DIR/stage-$SET_PREFIX"
  rm -rf "$STAGE_DIR"
  mkdir -p "$STAGE_DIR"

  local name
  for name in "${SOURCES[@]:-}"; do
    mkdir -p "$STAGE_DIR/$name"
    # Copy everything except live sqlite files (those come from .backup).
    tar -C "$SET_DATA_ROOT" --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' \
      --exclude='*.db-journal' --ignore-failed-read -cf - "$name" \
      | tar -C "$STAGE_DIR" -xf -
  done

  local rel path
  for rel in "${EXTRA_FILES[@]:-}"; do
    path="$SET_DATA_ROOT/$rel"
    [[ -f "$path" ]] || continue
    mkdir -p "$STAGE_DIR/$(dirname "$rel")"
    if [[ "$rel" == *.db ]]; then
      sqlite_hot_copy "$path" "$STAGE_DIR/$rel"
    else
      cp -f "$path" "$STAGE_DIR/$rel"
    fi
  done

  # Every remaining *.db under the source trees.
  local db dest
  if [[ ${#SOURCES[@]} -gt 0 ]]; then
    while IFS= read -r db; do
      [[ -n "$db" ]] || continue
      rel="${db#"$SET_DATA_ROOT"/}"
      dest="$STAGE_DIR/$rel"
      if [[ -f "$dest" ]]; then
        continue
      fi
      mkdir -p "$(dirname "$dest")"
      sqlite_hot_copy "$db" "$dest"
    done < <(find "${SOURCES[@]/#/$SET_DATA_ROOT/}" -type f -name '*.db' 2>/dev/null || true)
  fi

  local extra base
  for extra in "${EXTRA_DB_PATHS[@]:-}"; do
    [[ -n "$extra" ]] || continue
    if [[ ! -f "$extra" ]]; then
      log "WARN: extra db missing (skip): $extra"
      continue
    fi
    base="$(basename "$extra")"
    mkdir -p "$STAGE_DIR/db"
    sqlite_hot_copy "$extra" "$STAGE_DIR/db/$base"
  done
}

create_archive() {
  stage_tree
  local -a members=()
  local name
  for name in "${SOURCES[@]:-}"; do
    [[ -e "$STAGE_DIR/$name" ]] && members+=("$name")
  done
  [[ -d "$STAGE_DIR/db" ]] && members+=("db")

  if [[ ${#members[@]} -eq 0 ]]; then
    die "stage for $SET_PREFIX is empty"
  fi

  log "creating work archive $PLAIN_ARCHIVE from staged ${members[*]}"
  if ! tar --zstd -cf "$PLAIN_ARCHIVE" -C "$STAGE_DIR" "${members[@]}"; then
    die "tar.zst create failed"
  fi
  [[ -s "$PLAIN_ARCHIVE" ]] || die "archive is empty: $PLAIN_ARCHIVE"
  log "plain archive size $(du -h "$PLAIN_ARCHIVE" | awk '{print $1}')"
}

encrypt_archive() {
  log "encrypting $SET_PREFIX with $CRYPT_EXT key file $SET_KEY_FILE (FAT has no permissions)"
  encrypt_file "$PLAIN_ARCHIVE" "$CRYPT_ARCHIVE" "$SET_KEY_FILE"
  log "encrypted size $(du -h "$CRYPT_ARCHIVE" | awk '{print $1}')"
}

publish_to_volume() {
  local sz dest_name
  sz="$(stat -c %s "$CRYPT_ARCHIVE")"
  dest_name="$(basename "$DEST_CRYPT")"
  [[ "$dest_name" != *:* ]] || die "refusing colon in FAT filename: $dest_name"

  PUBLISHED=()
  if (( sz <= FAT_MAX_BYTES )); then
    fat_cp "$CRYPT_ARCHIVE" "$DEST_CRYPT"
    PUBLISHED+=("$DEST_CRYPT")
    log "published $DEST_CRYPT ($sz bytes)"
  else
    log "encrypted archive $sz bytes exceeds FAT max $FAT_MAX_BYTES; splitting"
    local prefix="$DEST_CRYPT.part"
    [[ "$(basename "$prefix")" != *:* ]] || die "refusing colon in FAT split prefix"
    split -b "$FAT_MAX_BYTES" -d -a 2 "$CRYPT_ARCHIVE" "$prefix"
    local part
    for part in "$prefix"[0-9][0-9]; do
      [[ -f "$part" ]] || die "split produced no parts at $prefix"
      local psz
      psz="$(stat -c %s "$part")"
      (( psz <= FAT_MAX_BYTES )) || die "split part still too large for FAT32: $part ($psz)"
      [[ "$(basename "$part")" != *:* ]] || die "split part name contains a colon: $part"
      PUBLISHED+=("$part")
      log "published part $part ($psz bytes)"
    done
  fi
}

assemble_from_dest() {
  local out="$1"
  if [[ -f "$DEST_CRYPT" ]]; then
    cat "$DEST_CRYPT" >"$out"
    return
  fi
  local -a parts=()
  local p
  for p in "$DEST_CRYPT".part[0-9][0-9]; do
    [[ -f "$p" ]] && parts+=("$p")
  done
  if [[ ${#parts[@]} -eq 0 ]]; then
    die "no encrypted dest files at $DEST_CRYPT"
  fi
  local sorted
  sorted="$(printf '%s\n' "${parts[@]}" | sort)"
  # shellcheck disable=SC2086
  cat $sorted >"$out"
}

restore_test() {
  log "restore-test: assembling dest blob and decrypting"
  local assembled decrypted
  assembled="$WORK_DIR/assembled-${SET_PREFIX}.${CRYPT_EXT}"
  decrypted="$WORK_DIR/restored-${SET_PREFIX}.tar.zst"
  assemble_from_dest "$assembled"
  decrypt_file "$assembled" "$decrypted" "$SET_KEY_FILE"

  log "restore-test: verifying archive integrity"
  zstd -t --quiet "$decrypted" || die "zstd test failed after decrypt"

  log "restore-test: listing archive contents"
  if ! tar --zstd -tf "$decrypted" >"$LISTING_PATH"; then
    die "tar list failed after decrypt"
  fi
  [[ -s "$LISTING_PATH" ]] || die "archive listing is empty"

  local count
  count="$(wc -l <"$LISTING_PATH" | tr -d ' ')"
  log "restore-test: $count entries"
  sed -n '1,40p' "$LISTING_PATH" | while IFS= read -r line; do
    log "  $line"
  done

  local rel found
  for rel in "${EXTRA_FILES[@]:-}"; do
    found=0
    if grep -qxF "$rel" "$LISTING_PATH" || grep -qxF "./$rel" "$LISTING_PATH"; then
      found=1
    elif grep -qE "(^|/)${rel}$" "$LISTING_PATH"; then
      found=1
    fi
    [[ "$found" -eq 1 ]] || die "restore-test: critical file missing from archive: $rel"
  done

  local extract_dir
  extract_dir="$(mktemp -d "${TMPDIR:-/tmp}/family-restore-test.XXXXXX")"
  tar --zstd -xf "$decrypted" -C "$extract_dir" || die "restore-test extract failed"
  [[ -n "$(find "$extract_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]] \
    || die "restore-test extract produced no files"
  log "restore-test: extract ok in $extract_dir"

  local db
  while IFS= read -r db; do
    [[ -n "$db" ]] || continue
    pragma_integrity_check "$db"
  done < <(find "$extract_dir" -type f -name '*.db' -print)

  rm -rf "$extract_dir"
  log "restore-test: passed"
}

promote_weekly() {
  local daily_dir="$1" weekly_dir="$2" prefix="$3"
  if [[ "$BACKUP_WEEKDAY" != "7" ]]; then
    log "weekday=$BACKUP_WEEKDAY (not Sunday); skip weekly promote ($prefix)"
    return 0
  fi
  local week_stem week_crypt
  week_stem="${prefix}-week-$(date +%G-W%V)"
  if [[ "$prefix" == "family-data" && -n "${BACKUP_WEEK_NAME:-}" ]]; then
    week_stem="${BACKUP_WEEK_NAME}"
    week_stem="${week_stem%.tar.zst.gpg}"
    week_stem="${week_stem%.tar.zst.age}"
    week_stem="${week_stem%.tar.zst}"
  fi
  if [[ "$prefix" == "max-data" && -n "${MAX_BACKUP_WEEK_NAME:-}" ]]; then
    week_stem="${MAX_BACKUP_WEEK_NAME}"
    week_stem="${week_stem%.tar.zst.gpg}"
    week_stem="${week_stem%.tar.zst.age}"
    week_stem="${week_stem%.tar.zst}"
  fi
  [[ "$week_stem" != *:* ]] || die "weekly name contains a colon: $week_stem"
  week_crypt="$weekly_dir/${week_stem}.tar.zst.${CRYPT_EXT}"

  if [[ -f "$DEST_CRYPT" ]]; then
    fat_cp "$DEST_CRYPT" "$week_crypt"
  else
    local part dest_part
    for part in "$DEST_CRYPT".part[0-9][0-9]; do
      [[ -f "$part" ]] || continue
      dest_part="$weekly_dir/${week_stem}.tar.zst.${CRYPT_EXT}.part${part##*.part}"
      fat_cp "$part" "$dest_part"
    done
  fi
  log "weekly promote -> $weekly_dir/${week_stem}.tar.zst.${CRYPT_EXT}"
}

stem_from_filename() {
  local base="$1"
  printf '%s\n' "$base" | sed -E 's/\.listing\.txt$//; s/\.tar\.zst\.(gpg|age)(\.part[0-9]+)?$//'
}

prune_dir() {
  local dir="$1" keep="$2" prefix="$3"
  local -a stems=()
  local f base stem
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    base="$(basename "$f")"
    stem="$(stem_from_filename "$base")"
    [[ -n "$stem" ]] || continue
    if [[ " ${stems[*]} " != *" $stem "* ]]; then
      stems+=("$stem")
    fi
  done < <(find "$dir" -maxdepth 1 -type f \( -name "${prefix}-*.tar.zst.gpg" -o -name "${prefix}-*.tar.zst.age" -o -name "${prefix}-*.tar.zst.gpg.part[0-9][0-9]" -o -name "${prefix}-*.tar.zst.age.part[0-9][0-9]" \) -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk '{ $1=""; sub(/^ /,""); print }')

  if [[ ${#stems[@]} -le "$keep" ]]; then
    log "retention: $dir has ${#stems[@]} $prefix backup(s) (keep $keep); nothing to prune"
    return 0
  fi
  local i
  for ((i=keep; i<${#stems[@]}; i++)); do
    log "retention: removing stem ${stems[$i]}"
    rm -f "$dir/${stems[$i]}.tar.zst.gpg" \
      "$dir/${stems[$i]}.tar.zst.age" \
      "$dir/${stems[$i]}.listing.txt" \
      "$dir/${stems[$i]}.tar.zst.gpg.part"[0-9][0-9] \
      "$dir/${stems[$i]}.tar.zst.age.part"[0-9][0-9]
  done
}

offsite_copy() {
  [[ -n "$RCLONE_REMOTE" ]] || { log "RCLONE_REMOTE unset; skip offsite copy"; return 0; }
  command -v "$RCLONE_BIN" >/dev/null 2>&1 || die "RCLONE_REMOTE is set but rclone not found: $RCLONE_BIN"
  local f
  for f in "${PUBLISHED[@]}"; do
    log "offsite copy $(basename "$f") to $RCLONE_REMOTE"
    if ! "$RCLONE_BIN" copy "$f" "$RCLONE_REMOTE" --retries 3 --low-level-retries 3; then
      die "rclone copy to $RCLONE_REMOTE failed"
    fi
  done
  log "offsite copy complete"
}

run_one_set() {
  SET_PREFIX="$1"
  SET_DATA_ROOT="$2"
  SET_BACKUP_DIR="$3"
  SET_KEY_FILE="$4"
  detect_crypt "$SET_KEY_FILE"

  local daily_dir weekly_dir
  daily_dir="$SET_BACKUP_DIR/daily"
  weekly_dir="$SET_BACKUP_DIR/weekly"
  mkdir -p "$daily_dir" "$weekly_dir" || die "cannot create $SET_BACKUP_DIR on BACKUP1"

  local stem
  stem="${SET_PREFIX}-${BACKUP_STAMP}"
  [[ "$stem" != *:* ]] || die "internal name contains a colon: $stem"

  PLAIN_ARCHIVE="$WORK_DIR/${stem}.tar.zst"
  CRYPT_ARCHIVE="$WORK_DIR/${stem}.tar.zst.${CRYPT_EXT}"
  DEST_CRYPT="$daily_dir/${stem}.tar.zst.${CRYPT_EXT}"
  LISTING_PATH="$WORK_DIR/${stem}.listing.txt"

  log "start set=$SET_PREFIX DATA_ROOT=$SET_DATA_ROOT DEST=$SET_BACKUP_DIR stamp=$BACKUP_STAMP"
  collect_sources
  include_critical_files
  create_archive
  encrypt_archive
  publish_to_volume
  restore_test
  promote_weekly "$daily_dir" "$weekly_dir" "$SET_PREFIX"
  prune_dir "$daily_dir" "$KEEP_DAILY" "$SET_PREFIX"
  prune_dir "$weekly_dir" "$KEEP_WEEKLY" "${SET_PREFIX}-week"
  # Also prune weeklies that share the prefix (family-data-week-*).
  prune_dir "$weekly_dir" "$KEEP_WEEKLY" "$SET_PREFIX"
  offsite_copy
  log "success $SET_PREFIX ${PUBLISHED[*]}"
}

main() {
  SOURCE_NAMES=("${FAMILY_SOURCE_NAMES[@]}")
  CRITICAL_REL_PATHS=("${FAMILY_CRITICAL_REL_PATHS[@]}")
  EXTRA_DB_PATHS=()
  run_one_set "family-data" "$DATA_ROOT" "$BACKUP_DIR" "$BACKUP_KEY_FILE"

  if [[ "$BACKUP_INCLUDE_MAX" != "1" ]]; then
    log "BACKUP_INCLUDE_MAX is off; skip personal Max/Workroom archive"
    return 0
  fi

  local -a max_names=()
  local n
  # shellcheck disable=SC2086
  for n in ${MAX_SOURCE_NAMES:-$MAX_SOURCE_NAMES_DEFAULT}; do
    max_names+=("$n")
  done
  SOURCE_NAMES=("${max_names[@]}")
  CRITICAL_REL_PATHS=()
  EXTRA_DB_PATHS=()
  local db
  for db in $MAX_DB_PATHS; do
    EXTRA_DB_PATHS+=("$db")
  done
  run_one_set "max-data" "$MAX_DATA_ROOT" "$MAX_BACKUP_DIR" "$MAX_KEY_FILE"
}

main
