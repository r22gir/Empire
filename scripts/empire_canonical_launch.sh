#!/usr/bin/env bash
set -euo pipefail

REPO="${EMPIRE_REPO:-$HOME/empire-repo}"
PORTAL_URL="${EMPIRE_PORTAL_URL:-http://127.0.0.1:3005/}"
API_URL="${EMPIRE_API_URL:-http://127.0.0.1:8000/api/v1}"
OPEN_BROWSER=1
RESTART=0

for arg in "$@"; do
  case "$arg" in
    --no-open) OPEN_BROWSER=0 ;;
    --restart) RESTART=1 ;;
    --help|-h)
      printf 'Usage: empire [--restart] [--no-open]\n'
      exit 0
      ;;
  esac
done

if [ ! -d "$REPO/.git" ]; then
  printf 'Empire repo not found at %s\n' "$REPO" >&2
  exit 1
fi

unit_exists() {
  systemctl --user list-unit-files "$1" --no-legend 2>/dev/null | grep -q "^$1"
}

ensure_unit() {
  local unit="$1"
  if ! unit_exists "$unit"; then
    printf '%s: missing\n' "$unit"
    return 1
  fi

  if [ "$RESTART" -eq 1 ]; then
    systemctl --user restart "$unit"
  elif ! systemctl --user is-active --quiet "$unit"; then
    systemctl --user start "$unit"
  fi

  local state
  state="$(systemctl --user is-active "$unit" 2>/dev/null || true)"
  printf '%s: %s\n' "$unit" "${state:-unknown}"
}

printf 'Empire canonical launch\n'
printf 'repo: %s\n' "$REPO"
printf 'commit: %s\n' "$(git -C "$REPO" rev-parse --short HEAD)"
printf 'portal: %s\n' "$PORTAL_URL"
printf 'api: %s\n' "$API_URL"

ensure_unit empire-backend.service
ensure_unit empire-portal.service
ensure_unit empire-openclaw.service || true

python3 - <<'PY'
import json
import urllib.request

checks = {
    "api_git": "http://127.0.0.1:8000/api/v1/dev/git",
    "max_status": "http://127.0.0.1:8000/api/v1/max/status",
}
for name, url in checks.items():
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if name == "api_git":
            print(f"{name}: {payload.get('last_commit_hash')}")
        else:
            print(f"{name}: ok")
    except Exception as exc:
        print(f"{name}: failed ({exc})")
PY

if [ "$OPEN_BROWSER" -eq 1 ]; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$PORTAL_URL" >/dev/null 2>&1 || true
  fi
fi
