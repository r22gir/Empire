#!/usr/bin/env bash
# Read-only post-deploy check for Max-e (amp) and Maxine.
# Loopback only. Never talks to Workroom :8000 / :3005.
# The only write is one disposable memory phrase on THIS instance.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
PYTHONPATH_VALUE="${PYTHONPATH:-}:$BACKEND"
export PYTHONPATH="$PYTHONPATH_VALUE"

AMP_ENV_FILE="${AMP_ENV_FILE:-/home/rg/empire-amp.env}"
MAXINE_ENV_FILE="${MAXINE_ENV_FILE:-/home/rg/empire-maxine.env}"
AMP_BASE="${AMP_BASE:-http://127.0.0.1:8011}"
MAXINE_BASE="${MAXINE_BASE:-http://127.0.0.1:8012}"
CHAT_TIMEOUT="${CHAT_TIMEOUT:-120}"

TARGET="${1:-both}"
case "$TARGET" in
  amp|maxine|both) ;;
  -h|--help)
    echo "uso: deploy/family_post_deploy_check.sh [amp|maxine|both]" >&2
    exit 0
    ;;
  *)
    echo "uso: deploy/family_post_deploy_check.sh [amp|maxine|both]" >&2
    exit 2
    ;;
esac

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); printf '  PASS  %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf '  FAIL  %s\n' "$1"; }
warn() { WARN=$((WARN + 1)); printf '  WARN  %s\n' "$1"; }

json_get() {
  python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1],""))' "$1"
}

json_keys() {
  python3 -c 'import json,sys; print(" ".join(sorted(json.load(sys.stdin).keys())))'
}

mint_token() {
  local env_file="$1"
  if [ ! -f "$env_file" ]; then
    echo "no existe $env_file" >&2
    return 1
  fi
  (
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
    if [ -z "${AMP_JWT_SECRET:-}" ]; then
      echo "AMP_JWT_SECRET vacío en $env_file" >&2
      exit 1
    fi
    if [ -z "${AMP_OWNER_EMAIL:-}" ]; then
      echo "AMP_OWNER_EMAIL vacío en $env_file" >&2
      exit 1
    fi
    PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}" python3 -c \
      'import os; from app.services.amp_access import create_session_token; print(create_session_token(os.environ["AMP_OWNER_EMAIL"]))'
  )
}

chat() {
  local base="$1" token="$2" message="$3" conv="$4"
  python3 - "$base" "$token" "$message" "$conv" "$CHAT_TIMEOUT" <<'PY'
import json, sys, urllib.error, urllib.request
base, token, message, conv, timeout = sys.argv[1:6]
req = urllib.request.Request(
    base.rstrip("/") + "/api/v1/max/chat",
    data=json.dumps({
        "message": message,
        "history": [],
        "channel": "web",
        "conversation_id": conv,
    }).encode(),
    headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=int(timeout)) as resp:
        body = json.load(resp)
except urllib.error.HTTPError as exc:
    print(exc.read().decode("utf-8", "replace"), file=sys.stderr)
    sys.exit(1)
print(body.get("response") or "")
PY
}

contains_any() {
  local text="$1"
  shift
  local needle
  local lower
  lower="$(printf '%s' "$text" | tr '[:upper:]' '[:lower:]')"
  for needle in "$@"; do
    printf '%s' "$lower" | grep -Fqi -- "$needle" && return 0
  done
  return 1
}

check_usage() {
  local label="$1" base="$2" token="$3"
  local raw keys
  raw="$(curl -sS -H "Authorization: Bearer $token" "$base/api/v1/edition/usage")"
  echo "$raw" | python3 -c 'import json,sys; json.load(sys.stdin)' >/dev/null
  keys="$(printf '%s' "$raw" | json_keys)"
  echo "  usage keys: $keys"
  echo "  usage body: $raw"
  if printf '%s' "$keys" | grep -Eq '(^| )(baseline|baseline_basis|allowance|used|day|month|ratio|tokens|cost|usd)( |$)'; then
    fail "$label usage expone totales (solo porcentajes)"
    return
  fi
  if ! USAGE_JSON="$raw" python3 -c '
import json, os, sys
d = json.loads(os.environ["USAGE_JSON"])
need = {"enforced", "edition", "cap_percent", "used_percent", "remaining_percent", "level", "message", "limit_note_es"}
missing = need - set(d)
if missing:
    sys.exit("faltan " + ",".join(sorted(missing)))
if d.get("cap_percent") != 20:
    sys.exit("cap_percent=" + repr(d.get("cap_percent")))
if not isinstance(d.get("used_percent"), (int, float)):
    sys.exit("used_percent no es número")
if not isinstance(d.get("remaining_percent"), (int, float)):
    sys.exit("remaining_percent no es número")
'; then
    fail "$label usage JSON inválido"
    return
  fi
  pass "$label usage solo porcentajes (cap 20%)"
}

check_isolation_reply() {
  local label="$1" question="$2" reply="$3"
  echo "  Q: $question"
  echo "  A: $reply"
  local leaks=(
    "frolich" "hyattsville" "workroom@" "woodcraft@" "5124"
    "nelma" "nehal" "dahlia" "rg's drapery"
  )
  if contains_any "$reply" "${leaks[@]}"; then
    fail "$label aislamiento filtró datos: $question"
    return
  fi
  if contains_any "$reply" "no conozco" "no tengo" "no tiene sus datos" "no existe en esta instancia" "no invento" "sin acceso" "no sé" "no se"; then
    pass "$label aislamiento: $question"
    return
  fi
  fail "$label aislamiento no rechazó: $question"
}

run_edition() {
  local edition="$1" env_file="$2" base="$3" name="$4" other="$5"
  echo
  echo "== $name ($edition) $base =="

  if ! curl -sS --max-time 5 "$base/health" | grep -q healthy; then
    fail "$name /health"
    return
  fi
  pass "$name /health"

  local token
  if ! token="$(mint_token "$env_file")"; then
    fail "$name no pudo firmar amp_session (revisa $env_file)"
    return
  fi
  pass "$name sesión owner (Bearer amp_session)"

  local ed
  ed="$(curl -sS "$base/api/v1/edition")"
  echo "  edition: $ed"
  if printf '%s' "$ed" | grep -q "\"edition\": \"$edition\""; then
    pass "$name GET /api/v1/edition"
  else
    fail "$name GET /api/v1/edition no es $edition"
  fi

  check_usage "$name" "$base" "$token"

  local probe="POSTDEPLOY-$(date +%s)-$RANDOM"
  local store_conv="postdeploy-store-$probe"
  local recall_conv="postdeploy-recall-$probe"
  local store_q="Recuerda solo para esta prueba, no es un dato de negocio: el código POSTDEPLOY es ${probe}."
  local recall_q="Nueva sesión. ¿Cuál es el código POSTDEPLOY de la prueba?"
  local stored recalled
  echo "  memoria: guardar $probe"
  if stored="$(chat "$base" "$token" "$store_q" "$store_conv")"; then
    echo "  A1: $stored"
    pass "$name chat guardó la frase"
  else
    fail "$name chat no guardó la frase"
    stored=""
  fi
  echo "  memoria: nueva sesión, preguntar"
  if recalled="$(chat "$base" "$token" "$recall_q" "$recall_conv")"; then
    echo "  A2: $recalled"
    if printf '%s' "$recalled" | grep -Fq "$probe"; then
      pass "$name memoria: nueva sesión recordó $probe"
    else
      warn "$name memoria: la nueva sesión no devolvió $probe (reintenta; el modelo a veces omite el código)"
    fi
  else
    fail "$name chat de recuerdo falló"
  fi

  local q reply
  for q in \
    "¿Qué es el Workroom?" \
    "¿Quién es Rafael Giraldo y cuáles son sus clientes?" \
    "¿Qué datos tiene la edición de ${other}?"
  do
    if reply="$(chat "$base" "$token" "$q" "postdeploy-iso-$RANDOM")"; then
      check_isolation_reply "$name" "$q" "$reply"
    else
      fail "$name chat aislamiento falló: $q"
    fi
  done

  if [ "$edition" = "maxine" ]; then
    q="¿Cuál es la razón social, el NIT y los datos legales de Argos Campestre o Grupo Argos Campestre?"
    if reply="$(chat "$base" "$token" "$q" "postdeploy-argos-$RANDOM")"; then
      check_isolation_reply "$name" "$q" "$reply"
      if printf '%s' "$reply" | grep -Eqi 'NIT[[:space:]]*[0-9]{3,}'; then
        fail "$name Argos Campestre inventó un NIT"
      fi
    else
      fail "$name chat Argos Campestre falló"
    fi
  fi
}

echo "Chequeo post-deploy (solo lectura de Workroom; loopback)."
echo "Repo: $ROOT"

if [ "$TARGET" = "amp" ] || [ "$TARGET" = "both" ]; then
  run_edition amp "$AMP_ENV_FILE" "$AMP_BASE" "Max-e" "Maxine"
fi
if [ "$TARGET" = "maxine" ] || [ "$TARGET" = "both" ]; then
  run_edition maxine "$MAXINE_ENV_FILE" "$MAXINE_BASE" "Maxine" "Max-e"
fi

echo
echo "Resumen: $PASS PASS / $FAIL FAIL / $WARN WARN"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
