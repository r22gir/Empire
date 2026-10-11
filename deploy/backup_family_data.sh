#!/usr/bin/env bash
# EmpireDell family-edition data backup.
# Packs /data/amp, /data/maxine, /data/minimax-meter, and /data/family-help
# (including memory.md and conversations.db) into a timestamped tar.zst.
#
# Env:
#   BACKUP_DIR       Destination root (default /mnt/backup)
#   DATA_ROOT        Source root (default /data)
#   RCLONE_REMOTE    If set, copy the new archive offsite with rclone
#                    (use a crypt remote for encryption, e.g. crypt:empire-family)
#   RCLONE_BIN       rclone binary (default rclone)
#   BACKUP_STAMP     Override timestamp (tests)
#   BACKUP_WEEKDAY   ISO weekday 1-7 (tests; 7 = Sunday weekly promote)
#   EMPIRE_OPS_TEST_MODE=1  Refuse live /data and /mnt/backup paths
#
# Exit: 0 on success; non-zero on any failure.
set -euo pipefail

umask 077

LOG_PREFIX="[family-backup]"

DATA_ROOT="${DATA_ROOT:-/data}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/backup}"
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
}

usage() {
  cat <<'EOF'
Usage: backup_family_data.sh [--help]

Nightly EmpireDell backup of family edition trees under DATA_ROOT
(amp, maxine, minimax-meter, family-help) to BACKUP_DIR.

  BACKUP_DIR=/mnt/backup ./deploy/backup_family_data.sh

Restore is documented in deploy/README.md.
EOF
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

[[ -d "$DATA_ROOT" ]] || die "DATA_ROOT does not exist: $DATA_ROOT"

DAILY_DIR="$BACKUP_DIR/daily"
WEEKLY_DIR="$BACKUP_DIR/weekly"
mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" || die "cannot create BACKUP_DIR=$BACKUP_DIR"

ARCHIVE_NAME="family-data-${BACKUP_STAMP}.tar.zst"
ARCHIVE_PATH="$DAILY_DIR/$ARCHIVE_NAME"
LISTING_PATH="${ARCHIVE_PATH}.listing.txt"

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
  local -a tar_args
  tar_args=(--ignore-failed-read -C "$DATA_ROOT")
  # Whole trees (amp, maxine, …) already contain memory.md / conversations.db
  # when those files live inside the trees. EXTRA_FILES covers copies that
  # exist at the documented relative paths even if a tree name was skipped.
  local -a members=("${SOURCES[@]}")
  local rel
  for rel in "${EXTRA_FILES[@]:-}"; do
    members+=("$rel")
  done

  log "creating $ARCHIVE_PATH from ${members[*]}"
  # tar --zstd writes the compressed archive in one step.
  if ! tar --zstd -cf "$ARCHIVE_PATH" "${tar_args[@]}" "${members[@]}"; then
    rm -f "$ARCHIVE_PATH"
    die "tar.zst create failed"
  fi
  [[ -s "$ARCHIVE_PATH" ]] || die "archive is empty: $ARCHIVE_PATH"
  log "archive size $(du -h "$ARCHIVE_PATH" | awk '{print $1}')"
}

restore_test() {
  log "restore-test: verifying archive integrity"
  zstd -t --quiet "$ARCHIVE_PATH" || die "zstd test failed for $ARCHIVE_PATH"

  log "restore-test: listing archive contents"
  if ! tar --zstd -tf "$ARCHIVE_PATH" >"$LISTING_PATH"; then
    die "tar list failed for $ARCHIVE_PATH"
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

  # Extract into a throwaway dir (never the live DATA_ROOT) and confirm readable.
  local extract_dir
  extract_dir="$(mktemp -d "${TMPDIR:-/tmp}/family-restore-test.XXXXXX")"
  # shellcheck disable=SC2064
  trap "rm -rf '$extract_dir'" RETURN
  tar --zstd -xf "$ARCHIVE_PATH" -C "$extract_dir" || die "restore-test extract failed"
  [[ -n "$(find "$extract_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]] \
    || die "restore-test extract produced no files"
  log "restore-test: extract ok in $extract_dir"
  rm -rf "$extract_dir"
  trap - RETURN
  log "restore-test: passed"
}

promote_weekly() {
  if [[ "$BACKUP_WEEKDAY" != "7" ]]; then
    log "weekday=$BACKUP_WEEKDAY (not Sunday); skip weekly promote"
    return 0
  fi
  local week_name weekly_path
  week_name="family-data-week-$(date +%G-W%V).tar.zst"
  if [[ -n "${BACKUP_WEEK_NAME:-}" ]]; then
    week_name="$BACKUP_WEEK_NAME"
  fi
  weekly_path="$WEEKLY_DIR/$week_name"
  cp -f "$ARCHIVE_PATH" "$weekly_path" || die "weekly promote copy failed"
  log "weekly promote -> $weekly_path"
}

prune_dir() {
  local dir="$1" keep="$2" pattern="$3"
  local -a files=()
  local f
  while IFS= read -r f; do
    [[ -n "$f" ]] && files+=("$f")
  done < <(find "$dir" -maxdepth 1 -type f -name "$pattern" -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk '{ $1=""; sub(/^ /,""); print }')

  if [[ ${#files[@]} -le "$keep" ]]; then
    log "retention: $dir has ${#files[@]} file(s) (keep $keep); nothing to prune"
    return 0
  fi
  local i
  for ((i=keep; i<${#files[@]}; i++)); do
    log "retention: removing ${files[$i]}"
    rm -f "${files[$i]}" "${files[$i]}.listing.txt"
  done
}

offsite_copy() {
  [[ -n "$RCLONE_REMOTE" ]] || { log "RCLONE_REMOTE unset; skip offsite copy"; return 0; }
  command -v "$RCLONE_BIN" >/dev/null 2>&1 || die "RCLONE_REMOTE is set but rclone not found: $RCLONE_BIN"
  log "offsite copy to $RCLONE_REMOTE (encrypted if the remote is a crypt: remote)"
  if ! "$RCLONE_BIN" copy "$ARCHIVE_PATH" "$RCLONE_REMOTE" --retries 3 --low-level-retries 3; then
    die "rclone copy to $RCLONE_REMOTE failed"
  fi
  log "offsite copy complete"
}

main() {
  log "start DATA_ROOT=$DATA_ROOT BACKUP_DIR=$BACKUP_DIR stamp=$BACKUP_STAMP"
  collect_sources
  include_critical_files
  create_archive
  restore_test
  promote_weekly
  prune_dir "$DAILY_DIR" "$KEEP_DAILY" "family-data-*.tar.zst"
  prune_dir "$WEEKLY_DIR" "$KEEP_WEEKLY" "family-data-*.tar.zst"
  offsite_copy
  log "success $ARCHIVE_PATH"
}

main
