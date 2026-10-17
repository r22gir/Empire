#!/usr/bin/env bash
# EmpireDell disk watch for /, /data, and BACKUP1 (/media/rg/BACKUP1).
# Warn at 80%, critical at 90%. Logs top space users and known growers.
# Cleanup mode is dry-run only: it lists candidates and never deletes.
# BACKUP1 is vfat and may be unplugged — an unmounted volume is a warning,
# not a df of the empty /media/rg/BACKUP1 stub on the root disk.
# BACKUP1 is df/mount-only by default (thousands of recup_dir.* trees). Set
# DISK_WATCH_SCAN_BACKUP=1 to also du/find it. Top-N pipelines consume all
# input so systemd IgnoreSIGPIPE cannot turn a closed head pipe into exit 2.
#
# Env:
#   DISK_WATCH_MOUNTS   Space-separated mounts (default "/ /data /media/rg/BACKUP1")
#   WARN_PCT / CRIT_PCT Thresholds (default 80 / 90)
#   DISK_USAGE_FILE     Mock df table for tests (lines: "<mount> <pct|unmounted>")
#   SCAN_ROOTS          Roots for du / grower scan (default "/ /data")
#   DISK_WATCH_SCAN_BACKUP=1  Also du/find BACKUP1 (off by default)
#   DU_TIMEOUT_S        Bound du/find seconds (default 60)
#   DU_DEPTH            du -d depth (default 2)
#   GROWER_MAXDEPTH     find -maxdepth (default 6)
#   MAX_NOTIFY_URL      Max internal notification endpoint
#   ALERT_EMAIL         Forced to empirebox2026@gmail.com outside tests
#   EMPIRE_OPS_TEST_MODE=1  Refuse live mounts / require temp SCAN_ROOTS
#
# Exit:
#   0  all mounts below warn
#   1  warning threshold hit (or alert could not be delivered)
#   2  critical threshold hit (usage only — never a scan/pipe failure)
#   3  usage collection failure (df/mock table). Scan problems log and continue.
set -euo pipefail

umask 077

LOG_PREFIX="[disk-watch]"
WARN_PCT="${WARN_PCT:-80}"
CRIT_PCT="${CRIT_PCT:-90}"
DISK_WATCH_MOUNTS="${DISK_WATCH_MOUNTS:-/ /data /media/rg/BACKUP1}"
BACKUP_WATCH_VOLUME="${BACKUP_WATCH_VOLUME:-/media/rg/BACKUP1}"
SCAN_ROOTS="${SCAN_ROOTS:-/ /data}"
DISK_USAGE_FILE="${DISK_USAGE_FILE:-}"
DU_TIMEOUT_S="${DU_TIMEOUT_S:-60}"
DU_DEPTH="${DU_DEPTH:-2}"
GROWER_MAXDEPTH="${GROWER_MAXDEPTH:-6}"
FIND_TIMEOUT_S="${FIND_TIMEOUT_S:-$DU_TIMEOUT_S}"
MAX_NOTIFY_URL="${MAX_NOTIFY_URL:-http://127.0.0.1:8000/api/v1/notifications/internal}"
HARD_ALERT_EMAIL="empirebox2026@gmail.com"
TOP_N="${TOP_N:-20}"
MODE="check"

log() { printf '%s %s %s\n' "$(date -Iseconds)" "$LOG_PREFIX" "$*"; }
die() { log "ERROR: $*"; exit 3; }

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
  local root
  for root in $SCAN_ROOTS; do
    path_is_temp "$root" || die "EMPIRE_OPS_TEST_MODE refuses live SCAN_ROOT=$root"
  done
  if [[ -n "$DISK_USAGE_FILE" ]]; then
    path_is_temp "$DISK_USAGE_FILE" || die "EMPIRE_OPS_TEST_MODE refuses live DISK_USAGE_FILE"
  else
    die "EMPIRE_OPS_TEST_MODE requires DISK_USAGE_FILE (never read live df)"
  fi
}

usage() {
  cat <<'EOF'
Usage: disk_watch.sh [--cleanup] [--help]

  (default)  Check /, /data, and /media/rg/BACKUP1 (df/mount). Warn at 80%, critical at 90%.
             du/find only /, /data unless DISK_WATCH_SCAN_BACKUP=1.
  --cleanup  Dry-run only: list reclaim candidates, do not delete.

Alerts go to Max notifications / Max email (empirebox2026@gmail.com)
when those mechanisms are configured. Otherwise the script logs the
alert and exits non-zero.
EOF
}

alert_email() {
  if [[ "${EMPIRE_OPS_TEST_MODE:-}" == "1" && -n "${ALERT_EMAIL_OVERRIDE:-}" ]]; then
    printf '%s' "$ALERT_EMAIL_OVERRIDE"
    return
  fi
  printf '%s' "$HARD_ALERT_EMAIL"
}

# Existing Max mechanisms (see backend/app/routers/notifications.py and
# backend/app/services/max/email_service.py). We never invent a new mailer.
notify_max_http() {
  local title="$1" message="$2" priority="$3"
  command -v curl >/dev/null 2>&1 || return 1
  curl -sfS --max-time 8 -X POST "$MAX_NOTIFY_URL" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c 'import json,sys; print(json.dumps({"source":"System","type":"system_alert","title":sys.argv[1],"message":sys.argv[2],"priority":sys.argv[3]}))' "$title" "$message" "$priority")" \
    >/dev/null
}

notify_max_email() {
  local title="$1" message="$2"
  local to
  to="$(alert_email)"
  local repo_root backend_dir
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  backend_dir="$repo_root/backend"
  [[ -d "$backend_dir/app/services/max" ]] || return 1

  # Only attempt when an existing Max email backend is actually configured.
  if [[ -z "${SENDGRID_API_KEY:-}" && ( -z "${SMTP_USER:-}" || -z "${SMTP_PASSWORD:-}" ) ]]; then
    return 1
  fi

  PYTHONPATH="${backend_dir}${PYTHONPATH:+:$PYTHONPATH}" python3 - "$to" "$title" "$message" <<'PY'
import os, sys
to, title, body = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.environ.get("PYTHONPATH", "").split(os.pathsep)[0])
try:
    from app.services.max.email_service import EmailService
except Exception:
    sys.exit(1)
svc = EmailService()
if not svc.is_configured:
    sys.exit(1)
html = "<pre>" + body.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"
ok = svc.send(to=to, subject=title, body_html=html)
sys.exit(0 if ok else 1)
PY
}

deliver_alert() {
  local title="$1" message="$2" priority="$3"
  if [[ -n "${MAX_ALERT_HOOK:-}" ]]; then
    if [[ -x "${MAX_ALERT_HOOK}" ]] && "$MAX_ALERT_HOOK" "$title" "$message" "$priority"; then
      return 0
    fi
    log "WARN: no Max notification/email mechanism available; logging alert only"
    log "ALERT to $(alert_email): $title"
    log "$message"
    return 1
  fi

  local sent=0
  if notify_max_http "$title" "$message" "$priority"; then
    log "alert posted to Max notifications ($MAX_NOTIFY_URL)"
    sent=1
  fi
  if notify_max_email "$title" "$message"; then
    log "alert emailed via Max email service to $(alert_email)"
    sent=1
  fi
  if [[ "$sent" -eq 1 ]]; then
    return 0
  fi
  log "WARN: no Max notification/email mechanism available; logging alert only"
  log "ALERT to $(alert_email): $title"
  log "$message"
  return 1
}

volume_is_mounted() {
  local vol="$1"
  if [[ -n "${MOUNTPOINT_BIN:-}" ]]; then
    "$MOUNTPOINT_BIN" -q "$vol"
    return $?
  fi
  if command -v mountpoint >/dev/null 2>&1; then
    mountpoint -q "$vol"
    return $?
  fi
  findmnt -n --target "$vol" >/dev/null 2>&1
}

mount_pct() {
  local mount="$1"
  if [[ -n "$DISK_USAGE_FILE" ]]; then
    awk -v m="$mount" '$1==m {print $2; found=1} END{if(!found) exit 1}' "$DISK_USAGE_FILE"
    return
  fi
  # Never df the BACKUP1 stub directory on / — that reports root-disk usage.
  if [[ "$mount" == "$BACKUP_WATCH_VOLUME" ]] || [[ "$mount" == /media/rg/BACKUP1 ]]; then
    if ! volume_is_mounted "$mount"; then
      printf '%s\n' "unmounted"
      return 0
    fi
  fi
  df -P "$mount" | awk 'NR==2 { gsub(/%/,"",$5); print $5 }'
}

is_backup_watch_volume() {
  local p="$1"
  [[ "$p" == "$BACKUP_WATCH_VOLUME" || "$p" == /media/rg/BACKUP1 ]]
}

scan_backup_enabled() {
  [[ "${DISK_WATCH_SCAN_BACKUP:-0}" == "1" ]]
}

should_du_or_find() {
  local root="$1"
  if is_backup_watch_volume "$root" && ! scan_backup_enabled; then
    return 1
  fi
  return 0
}

# Run a command with timeout + nice/ionice. Never use `head` on this output:
# systemd IgnoreSIGPIPE=yes turns EPIPE from `head` into sort exit 2, and
# pipefail then aborts the script with the critical usage code.
_run_bounded() {
  local timeout_s="$1"
  shift
  local -a cmd=()
  if command -v timeout >/dev/null 2>&1; then
    cmd+=(timeout "$timeout_s")
  fi
  if command -v nice >/dev/null 2>&1; then
    cmd+=(nice -n 19)
  fi
  if command -v ionice >/dev/null 2>&1; then
    cmd+=(ionice -c3)
  fi
  cmd+=("$@")
  "${cmd[@]}"
}

_bounded_du() {
  local root="$1"
  _run_bounded "$DU_TIMEOUT_S" du -x -d "$DU_DEPTH" --exclude='recup_dir.*' "$root"
}

# awk prints the first n lines and keeps reading the rest so sort never
# hits a closed pipe (unlike `head -n`, which exits early).
_top_n_consume() {
  awk -v n="$TOP_N" 'NR<=n {print}'
}

log_top_space_users() {
  local root="$1"
  [[ -d "$root" ]] || { log "skip du: $root is not a directory"; return 0; }
  if ! should_du_or_find "$root"; then
    log "skip du: $root (BACKUP1 scan disabled; set DISK_WATCH_SCAN_BACKUP=1 to enable)"
    return 0
  fi
  if [[ "${EMPIRE_OPS_TEST_MODE:-}" != "1" ]]; then
    if is_backup_watch_volume "$root" && ! volume_is_mounted "$root"; then
      log "skip du: $root is not mounted"
      return 0
    fi
  fi
  log "top ${TOP_N} space users under $root"

  # Finish du (or time it out) before ranking. Never `head` the pipe:
  # systemd IgnoreSIGPIPE=yes turns that EPIPE into sort exit 2, which
  # pipefail used to report as a critical usage failure.
  local raw out line rc=0
  raw="$(mktemp "${TMPDIR:-/tmp}/disk-watch-du.XXXXXX")"
  out="$(mktemp "${TMPDIR:-/tmp}/disk-watch-top.XXXXXX")"
  set +e
  _bounded_du "$root" >"$raw" 2>/dev/null
  rc=$?
  set -e
  if [[ "$rc" -eq 124 ]]; then
    log "du timed out for $root"
    rm -f "$raw" "$out"
    return 0
  fi
  set +o pipefail
  sort -nr "$raw" | _top_n_consume >"$out" || true
  set -o pipefail
  while IFS= read -r line; do
    [[ -n "$line" ]] && log "  du $line"
  done <"$out"
  rm -f "$raw" "$out"
  return 0
}

_bounded_find() {
  local root="$1"
  shift
  _run_bounded "$FIND_TIMEOUT_S" find "$root" -xdev -maxdepth "$GROWER_MAXDEPTH" "$@"
}

grower_candidates() {
  local root
  for root in $SCAN_ROOTS; do
    [[ -d "$root" ]] || continue
    if ! should_du_or_find "$root"; then
      continue
    fi
    # Timeouts / unreadable dirs are ignored; never abort the watch.
    # node_modules and npm caches
    _bounded_find "$root" -type d \( -name node_modules -o -name '.npm' -o -name 'npm-cache' \) 2>/dev/null || true
    # Next.js build output
    _bounded_find "$root" -type d -name '.next' 2>/dev/null || true
    # pip cache
    _bounded_find "$root" -type d \( -path '*/.cache/pip' -o -name 'pip-cache' \) 2>/dev/null || true
    # uploads
    _bounded_find "$root" -type d -name uploads 2>/dev/null || true
    # tmp trees
    if [[ "$root" == "/tmp" || "$root" == */tmp ]]; then
      printf '%s\n' "$root"
    else
      _bounded_find "$root" -type d -name tmp 2>/dev/null || true
    fi
  done
  # Host-wide known growers (skipped in test mode — live paths).
  if [[ "${EMPIRE_OPS_TEST_MODE:-}" != "1" ]]; then
    [[ -d "${HOME:-}/.npm" ]] && printf '%s\n' "${HOME}/.npm"
    [[ -d "${HOME:-}/.cache/pip" ]] && printf '%s\n' "${HOME}/.cache/pip"
    [[ -d /tmp ]] && printf '%s\n' /tmp
    if command -v journalctl >/dev/null 2>&1; then
      printf '%s\n' "journald:$(journalctl --disk-usage 2>/dev/null | tr '\n' ' ')"
    fi
  fi
}

log_known_growers() {
  log "known growers"
  local path size
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    if [[ "$path" == journald:* ]]; then
      log "  $path"
      continue
    fi
    if [[ -e "$path" ]]; then
      size="$(_run_bounded "${DU_TIMEOUT_S}" du -sh "$path" 2>/dev/null | awk '{print $1}')" || true
      log "  ${size:-?}  $path"
    fi
  done < <(grower_candidates | sort -u) || true
}

cleanup_list() {
  log "cleanup dry-run (list only; nothing will be deleted)"
  local path size
  local listed=0
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    if [[ "$path" == journald:* ]]; then
      log "  CANDIDATE  $path"
      listed=1
      continue
    fi
    if [[ -e "$path" ]]; then
      size="$(_run_bounded "${DU_TIMEOUT_S}" du -sh "$path" 2>/dev/null | awk '{print $1}')" || true
      log "  CANDIDATE  ${size:-?}  $path"
      listed=1
    fi
  done < <(grower_candidates | sort -u)
  if [[ "$listed" -eq 0 ]]; then
    log "no cleanup candidates found under: $SCAN_ROOTS"
  fi
  log "cleanup dry-run complete — no files removed"
}

check_mounts() {
  local mount pct worst=0 status="ok" title message priority
  local -a warnings=() criticals=()
  for mount in $DISK_WATCH_MOUNTS; do
    if ! pct="$(mount_pct "$mount")"; then
      die "could not read usage for $mount"
    fi
    if [[ "$pct" == "unmounted" ]]; then
      log "WARN: $mount is not mounted (BACKUP1 absent — not writing/reading the root-disk stub)"
      warnings+=("$mount unmounted")
      if [[ "$status" != "critical" ]]; then
        status="warn"
      fi
      continue
    fi
    log "usage $mount ${pct}%"
    if (( pct >= CRIT_PCT )); then
      criticals+=("$mount ${pct}%")
      (( pct > worst )) && worst=$pct
      status="critical"
    elif (( pct >= WARN_PCT )); then
      warnings+=("$mount ${pct}%")
      if [[ "$status" != "critical" ]]; then
        status="warn"
      fi
      (( pct > worst )) && worst=$pct
    fi
  done

  for mount in $SCAN_ROOTS; do
    log_top_space_users "$mount"
  done
  log_known_growers

  if [[ "$status" == "ok" ]]; then
    log "all mounts below ${WARN_PCT}%"
    return 0
  fi

  title="EmpireDell disk ${status}: ${worst}%"
  message="Host disk watch ${status} (warn=${WARN_PCT}% crit=${CRIT_PCT}%)."
  if [[ ${#criticals[@]} -gt 0 ]]; then
    message+=" Critical: ${criticals[*]}."
  fi
  if [[ ${#warnings[@]} -gt 0 ]]; then
    message+=" Warning: ${warnings[*]}."
  fi
  message+=" Review journal / disk_watch logs for top du paths and known growers."
  priority="high"
  [[ "$status" == "critical" ]] && priority="critical"

  local alert_rc=0
  if ! deliver_alert "$title" "$message" "$priority"; then
    alert_rc=1
  fi

  if [[ "$status" == "critical" ]]; then
    log "CRITICAL threshold reached"
    exit 2
  fi
  log "WARN threshold reached"
  # Non-zero when warn fires, or when the alert could not be delivered.
  exit 1
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --cleanup) MODE="cleanup"; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "unknown argument: $1" ;;
    esac
  done

  assert_test_safe
  log "start mode=$MODE mounts=$DISK_WATCH_MOUNTS warn=${WARN_PCT} crit=${CRIT_PCT}"

  if [[ "$MODE" == "cleanup" ]]; then
    cleanup_list
    exit 0
  fi

  check_mounts
}

main "$@"
