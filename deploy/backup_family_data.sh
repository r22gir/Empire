#!/usr/bin/env bash
# EmpireDell family-edition data backup onto BACKUP1 (external FAT32).
# Packs /data/amp, /data/maxine, /data/minimax-meter, and /data/family-help
# (including memory.md and conversations.db) into an encrypted tar.zst.
#
# Destination is the vfat/FAT32 drive BACKUP1 (~931G) at /media/rg/BACKUP1.
# That filesystem has no Unix permissions, a 4GiB-1 max file size, and may
# be unplugged. This script refuses to write if the volume is not mounted
# (so backups never land on the root disk), encrypts because FAT cannot
# protect files, splits chunks over 4GiB-1, and uses colon-free names.
#
# Env:
#   BACKUP_VOLUME    Mount to require (default /media/rg/BACKUP1)
#   BACKUP_DIR       Dest root (default $BACKUP_VOLUME/family-backups)
#   BACKUP_KEY_FILE  Symmetric key (default ~/.config/empire-backup/key)
#   FAT_MAX_BYTES    Max dest file size (default 4294967295 = 4GiB-1)
#   RCLONE_REMOTE    If set, copy encrypted dest files offsite
#   RCLONE_BIN       rclone binary (default rclone)
#   BACKUP_STAMP     Override timestamp (tests; no colons)
#   BACKUP_WEEKDAY   ISO weekday 1-7 (tests; 7 = Sunday weekly promote)
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
# FAT32 hard limit is 4GiB-1. Stay at/under that so copy never fails mid-file.
FAT_MAX_BYTES="${FAT_MAX_BYTES:-4294967295}"
DATA_ROOT="${DATA_ROOT:-/data}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"
RCLONE_BIN="${RCLONE_BIN:-rclone}"
KEEP_DAILY="${KEEP_DAILY:-14}"
KEEP_WEEKLY="${KEEP_WEEKLY:-8}"
BACKUP_STAMP="${BACKUP_STAMP:-$(date +%Y%m%dT%H%M%S)}"
BACKUP_WEEKDAY="${BACKUP_WEEKDAY:-$(date +%u)}"

SOURCE_NAMES=(amp maxine minimax-meter family-help)
CRITICAL_REL_PATHS=(
  "family-help/memory.md"
  "family-help/conversations.db"
  "maxine/memory.md"
  "maxine/conversations.db"
)

# Filled during the run.
WORK_DIR=""
PLAIN_ARCHIVE=""
CRYPT_ARCHIVE=""
CRYPT_EXT="gpg"
DEST_CRYPT=""
LISTING_PATH=""
PUBLISHED=()

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
}

usage() {
  cat <<'EOF'
Usage: backup_family_data.sh [--help]

Nightly EmpireDell backup of family edition trees under DATA_ROOT
to the BACKUP1 external drive (vfat/FAT32 at /media/rg/BACKUP1).

  ./deploy/backup_family_data.sh

Fails non-zero if BACKUP1 is not mounted (will not write to the root disk).
Archives are encrypted with ~/.config/empire-backup/key (never commit that file).

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
  # Fallback: stream bytes only (no metadata).
  cat "$src" >"$dest"
}

volume_is_mounted() {
  local vol="$1"
  if [[ -n "${MOUNTPOINT_BIN:-}" ]]; then
    "$MOUNTPOINT_BIN" -q "$vol"
    return $?
  fi
  if [[ "${EMPIRE_OPS_TEST_MODE:-}" == "1" ]]; then
    # Tests mark a fake volume with .mounted (never touch live BACKUP1).
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
    # Unmounted /media/rg/BACKUP1 is often an empty dir on /. Refuse that.
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
}

require_key() {
  [[ -f "$BACKUP_KEY_FILE" ]] || die "backup key missing: $BACKUP_KEY_FILE — create one (never commit it): mkdir -p ~/.config/empire-backup && openssl rand -base64 32 > ~/.config/empire-backup/key && chmod 600 ~/.config/empire-backup/key"
  [[ -s "$BACKUP_KEY_FILE" ]] || die "backup key is empty: $BACKUP_KEY_FILE"
}

# Prefer age when the key is an age identity; otherwise gpg symmetric.
detect_crypt() {
  if [[ -n "${BACKUP_CRYPT:-}" ]]; then
    CRYPT_EXT="$BACKUP_CRYPT"
    return
  fi
  if command -v age >/dev/null 2>&1 && grep -q '^AGE-SECRET-KEY-' "$BACKUP_KEY_FILE" 2>/dev/null; then
    CRYPT_EXT="age"
    return
  fi
  require_cmd gpg
  CRYPT_EXT="gpg"
}

encrypt_file() {
  local src="$1" dest="$2"
  case "$CRYPT_EXT" in
    age)
      require_cmd age
      require_cmd age-keygen
      local recip
      recip="$(age-keygen -y "$BACKUP_KEY_FILE")"
      age -e -r "$recip" -o "$dest" "$src" || die "age encrypt failed"
      ;;
    gpg)
      require_cmd gpg
      gpg --batch --yes --quiet --symmetric --cipher-algo AES256 \
        --pinentry-mode loopback \
        --passphrase-file "$BACKUP_KEY_FILE" \
        -o "$dest" "$src" || die "gpg encrypt failed"
      ;;
    *)
      die "unsupported BACKUP_CRYPT=$CRYPT_EXT (use age or gpg)"
      ;;
  esac
  [[ -s "$dest" ]] || die "encrypted archive is empty: $dest"
}

decrypt_file() {
  local src="$1" dest="$2"
  case "$src" in
    *.age)
      require_cmd age
      age -d -i "$BACKUP_KEY_FILE" -o "$dest" "$src" || die "age decrypt failed"
      ;;
    *)
      require_cmd gpg
      gpg --batch --yes --quiet --decrypt --pinentry-mode loopback \
        --passphrase-file "$BACKUP_KEY_FILE" \
        -o "$dest" "$src" || die "gpg decrypt failed"
      ;;
  esac
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

assert_test_safe
require_cmd tar
require_cmd zstd
require_cmd find
require_cmd date
require_cmd stat
require_cmd split

[[ -d "$DATA_ROOT" ]] || die "DATA_ROOT does not exist: $DATA_ROOT"
require_backup_volume
require_key
detect_crypt

DAILY_DIR="$BACKUP_DIR/daily"
WEEKLY_DIR="$BACKUP_DIR/weekly"
mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" || die "cannot create BACKUP_DIR=$BACKUP_DIR on BACKUP1"

STEM="family-data-${BACKUP_STAMP}"
[[ "$STEM" != *:* ]] || die "internal name contains a colon: $STEM"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/family-backup-work.XXXXXX")"
trap cleanup_work EXIT
mkdir -p "$WORK_DIR/gnupg"
chmod 700 "$WORK_DIR/gnupg"
# Isolate gpg from ~/.gnupg. chmod here is on the local work dir, never FAT.
export GNUPGHOME="$WORK_DIR/gnupg"
PLAIN_ARCHIVE="$WORK_DIR/${STEM}.tar.zst"
CRYPT_ARCHIVE="$WORK_DIR/${STEM}.tar.zst.${CRYPT_EXT}"
DEST_CRYPT="$DAILY_DIR/${STEM}.tar.zst.${CRYPT_EXT}"
LISTING_PATH="$WORK_DIR/${STEM}.listing.txt"

collect_sources() {
  local name path
  SOURCES=()
  MISSING=()
  for name in "${SOURCE_NAMES[@]}"; do
    path="$DATA_ROOT/$name"
    if [[ -d "$path" ]]; then
      SOURCES+=("$name")
    else
      MISSING+=("$name")
    fi
  done
  if [[ ${#SOURCES[@]} -eq 0 ]]; then
    die "no family data directories found under $DATA_ROOT (${SOURCE_NAMES[*]})"
  fi
  if [[ ${#MISSING[@]} -gt 0 ]]; then
    log "WARN: missing source dirs (will skip): ${MISSING[*]}"
  fi
}

include_critical_files() {
  local rel path
  EXTRA_FILES=()
  for rel in "${CRITICAL_REL_PATHS[@]}"; do
    path="$DATA_ROOT/$rel"
    if [[ -f "$path" ]]; then
      EXTRA_FILES+=("$rel")
      log "including critical file $rel"
    fi
  done
}

create_archive() {
  local -a tar_args members
  tar_args=(--ignore-failed-read -C "$DATA_ROOT")
  members=("${SOURCES[@]}")
  local rel
  for rel in "${EXTRA_FILES[@]:-}"; do
    members+=("$rel")
  done

  log "creating work archive $PLAIN_ARCHIVE from ${members[*]}"
  if ! tar --zstd -cf "$PLAIN_ARCHIVE" "${tar_args[@]}" "${members[@]}"; then
    die "tar.zst create failed"
  fi
  [[ -s "$PLAIN_ARCHIVE" ]] || die "archive is empty: $PLAIN_ARCHIVE"
  log "plain archive size $(du -h "$PLAIN_ARCHIVE" | awk '{print $1}')"
}

encrypt_archive() {
  log "encrypting with $CRYPT_EXT key file $BACKUP_KEY_FILE (FAT has no permissions)"
  encrypt_file "$PLAIN_ARCHIVE" "$CRYPT_ARCHIVE"
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
  # Sort so part00, part01, … concatenate in order.
  local sorted
  sorted="$(printf '%s\n' "${parts[@]}" | sort)"
  # shellcheck disable=SC2086
  cat $sorted >"$out"
}

restore_test() {
  log "restore-test: assembling dest blob and decrypting"
  local assembled decrypted
  assembled="$WORK_DIR/assembled.${CRYPT_EXT}"
  decrypted="$WORK_DIR/restored.tar.zst"
  assemble_from_dest "$assembled"
  decrypt_file "$assembled" "$decrypted"

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
  rm -rf "$extract_dir"
  log "restore-test: passed"
}

promote_weekly() {
  if [[ "$BACKUP_WEEKDAY" != "7" ]]; then
    log "weekday=$BACKUP_WEEKDAY (not Sunday); skip weekly promote"
    return 0
  fi
  local week_stem week_crypt
  week_stem="family-data-week-$(date +%G-W%V)"
  if [[ -n "${BACKUP_WEEK_NAME:-}" ]]; then
    week_stem="${BACKUP_WEEK_NAME}"
    week_stem="${week_stem%.tar.zst.gpg}"
    week_stem="${week_stem%.tar.zst.age}"
    week_stem="${week_stem%.tar.zst}"
  fi
  [[ "$week_stem" != *:* ]] || die "weekly name contains a colon: $week_stem"
  week_crypt="$WEEKLY_DIR/${week_stem}.tar.zst.${CRYPT_EXT}"

  if [[ -f "$DEST_CRYPT" ]]; then
    fat_cp "$DEST_CRYPT" "$week_crypt"
  else
    local part dest_part
    for part in "$DEST_CRYPT".part[0-9][0-9]; do
      [[ -f "$part" ]] || continue
      dest_part="$WEEKLY_DIR/${week_stem}.tar.zst.${CRYPT_EXT}.part${part##*.part}"
      fat_cp "$part" "$dest_part"
    done
  fi
  log "weekly promote -> $WEEKLY_DIR/${week_stem}.tar.zst.${CRYPT_EXT}"
}

stem_from_filename() {
  local base="$1"
  printf '%s\n' "$base" | sed -E 's/\.listing\.txt$//; s/\.tar\.zst\.(gpg|age)(\.part[0-9]+)?$//'
}

prune_dir() {
  local dir="$1" keep="$2"
  local -a stems=()
  local f base stem
  # Newest first by mtime of each unique backup stem.
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    base="$(basename "$f")"
    stem="$(stem_from_filename "$base")"
    [[ -n "$stem" ]] || continue
    if [[ " ${stems[*]} " != *" $stem "* ]]; then
      stems+=("$stem")
    fi
  done < <(find "$dir" -maxdepth 1 -type f \( -name 'family-data-*.tar.zst.gpg' -o -name 'family-data-*.tar.zst.age' -o -name 'family-data-*.tar.zst.gpg.part[0-9][0-9]' -o -name 'family-data-*.tar.zst.age.part[0-9][0-9]' \) -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk '{ $1=""; sub(/^ /,""); print }')

  if [[ ${#stems[@]} -le "$keep" ]]; then
    log "retention: $dir has ${#stems[@]} backup(s) (keep $keep); nothing to prune"
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

main() {
  log "start DATA_ROOT=$DATA_ROOT BACKUP_VOLUME=$BACKUP_VOLUME BACKUP_DIR=$BACKUP_DIR stamp=$BACKUP_STAMP"
  collect_sources
  include_critical_files
  create_archive
  encrypt_archive
  publish_to_volume
  restore_test
  promote_weekly
  prune_dir "$DAILY_DIR" "$KEEP_DAILY"
  prune_dir "$WEEKLY_DIR" "$KEEP_WEEKLY"
  offsite_copy
  log "success ${PUBLISHED[*]}"
}

main
