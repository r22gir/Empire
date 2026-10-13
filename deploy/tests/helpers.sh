#!/usr/bin/env bash
# Shared assertions for EmpireDell ops tests. Never point at live host paths.
set -euo pipefail

PASS=0
FAIL=0

is_temp_path() {
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

assert_temp_path() {
  local p="$1"
  is_temp_path "$p" || {
    echo "REFUSING non-temp path: $p" >&2
    exit 99
  }
}

assert_not_live_host_path() {
  local p="$1"
  case "$p" in
    /data|/data/*|/mnt/backup|/mnt/backup/*|/media/rg/BACKUP1|/media/rg/BACKUP1/*|/)
      echo "REFUSING live host path: $p" >&2
      exit 99
      ;;
  esac
}

pass() { echo "  PASS  $*"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL  $*"; FAIL=$((FAIL + 1)); }

expect_eq() {
  local got="$1" want="$2" msg="$3"
  if [[ "$got" == "$want" ]]; then
    pass "$msg"
  else
    fail "$msg (got='$got' want='$want')"
  fi
}

expect_file() {
  local f="$1" msg="$2"
  if [[ -f "$f" ]]; then
    pass "$msg"
  else
    fail "$msg (missing $f)"
  fi
}

expect_dir() {
  local d="$1" msg="$2"
  if [[ -d "$d" ]]; then
    pass "$msg"
  else
    fail "$msg (missing $d)"
  fi
}

expect_contains() {
  local haystack="$1" needle="$2" msg="$3"
  if grep -q -- "$needle" <<<"$haystack"; then
    pass "$msg"
  else
    fail "$msg (missing '$needle')"
  fi
}

expect_file_contains() {
  local f="$1" needle="$2" msg="$3"
  if grep -q -- "$needle" "$f"; then
    pass "$msg"
  else
    fail "$msg (missing '$needle' in $f)"
  fi
}

finish() {
  echo
  echo "Results: $PASS passed, $FAIL failed"
  [[ "$FAIL" -eq 0 ]]
}
