#!/usr/bin/env bash
# Run EmpireDell ops shell tests. All cases use temp dirs only.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TMPDIR="${TMPDIR:-/tmp}"

fail=0
for t in "$DIR"/test_backup_family_data.sh "$DIR"/test_disk_watch.sh; do
  echo
  echo "######## $(basename "$t") ########"
  if bash "$t"; then
    echo "OK $(basename "$t")"
  else
    echo "FAILED $(basename "$t")"
    fail=1
  fi
done
exit "$fail"
