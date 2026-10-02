#!/bin/sh
# Load an edition env file and run a command. Nothing is copied to /tmp.
#
# Login link (run from the repo root; the env path is the Dell file, not a copy):
#   scripts/edition_env_run.sh /path/to/empire-maxine.env \
#     ./backend/venv/bin/python backend/scripts/amp_allowlist.py login-link --email person@example.com
set -eu
if [ "$#" -lt 2 ]; then
  echo "usage: edition_env_run.sh ENV_FILE COMMAND [ARGS...]" >&2
  exit 2
fi
env_file=$1
shift
if [ ! -f "$env_file" ]; then
  echo "env file not found: $env_file" >&2
  exit 2
fi
set -a
# shellcheck disable=SC1090
. "$env_file"
set +a
exec "$@"
