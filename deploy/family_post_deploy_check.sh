#!/usr/bin/env bash
# Read-only post-deploy check for Max-e (amp) and Maxine.
# Loopback only. Never talks to Workroom :8000 / :3005.
# The only write is one disposable memory phrase on THIS instance.
# Do not source the env file. Prefer backend/venv/bin/python (jose).
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
PYTHONPATH_VALUE="${PYTHONPATH:-}:$BACKEND"
export PYTHONPATH="$PYTHONPATH_VALUE"

# jose lives in the instance venv. System python3 on the Dell does not.
if [ -x "$ROOT/backend/venv/bin/python" ]; then
  PYTHON="$ROOT/backend/venv/bin/python"
elif [ -x "$ROOT/backend/venv/bin/python3" ]; then
  PYTHON="$ROOT/backend/venv/bin/python3"
else
  PYTHON="$(command -v python3 || command -v python || true)"
fi
if [ -z "${PYTHON}" ]; then
  echo "no hay python (backend/venv/bin/python ni PATH)" >&2
  exit 2
fi

AMP_ENV_FILE="${AMP_ENV_FILE:-/home/rg/empire-amp.env}"
MAXINE_ENV_FILE="${MAXINE_ENV_FILE:-/home/rg/empire-maxine.env}"
AMP_BASE="${AMP_BASE:-http://127.0.0.1:8011}"
MAXINE_BASE="${MAXINE_BASE:-http://127.0.0.1:8012}"
CHAT_TIMEOUT="${CHAT_TIMEOUT:-120}"

TARGET="${1:-both}"
case "$TARGET" in
  amp|maxine|both|--self-test) ;;
  -h|--help)
    echo "uso: deploy/family_post_deploy_check.sh [amp|maxine|both|--self-test]" >&2
    exit 0
    ;;
  *)
    echo "uso: deploy/family_post_deploy_check.sh [amp|maxine|both|--self-test]" >&2
    exit 2
    ;;
esac

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); printf '  PASS  %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf '  FAIL  %s\n' "$1"; }
warn() { WARN=$((WARN + 1)); printf '  WARN  %s\n' "$1"; }

# KEY=VALUE only. Never source/eval the env file (SMTP_FROM=Name <addr>
# is unquoted on the Dell and breaks bash). Last assignment wins.
read_env_key() {
  local file="$1" want="$2"
  if [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON" - "$file" "$want" <<'PY'
import sys
path, want = sys.argv[1], sys.argv[2]
found = ""
with open(path, "r", encoding="utf-8", errors="replace") as fh:
    for raw in fh:
        line = raw.replace("\r", "").strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key != want:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        found = value
print(found, end="")
PY
}

json_get() {
  "$PYTHON" -c 'import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1],""))' "$1"
}

json_keys() {
  "$PYTHON" -c 'import json,sys; print(" ".join(sorted(json.load(sys.stdin).keys())))'
}

mint_token() {
  local env_file="$1"
  local secret email
  if [ ! -f "$env_file" ]; then
    echo "no existe $env_file" >&2
    return 1
  fi
  secret="$(read_env_key "$env_file" AMP_JWT_SECRET || true)"
  email="$(read_env_key "$env_file" AMP_OWNER_EMAIL || true)"
  if [ -z "${secret}" ]; then
    echo "AMP_JWT_SECRET vacío en $env_file" >&2
    return 1
  fi
  if [ -z "${email}" ]; then
    echo "AMP_OWNER_EMAIL vacío en $env_file" >&2
    return 1
  fi
  AMP_JWT_SECRET="$secret" AMP_OWNER_EMAIL="$email" \
    PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -c \
    'import os; from app.services.amp_access import create_session_token; print(create_session_token(os.environ["AMP_OWNER_EMAIL"]))'
}

chat() {
  local base="$1" token="$2" message="$3" conv="$4"
  "$PYTHON" - "$base" "$token" "$message" "$conv" "$CHAT_TIMEOUT" <<'PY'
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

WORKROOM_RECORD_LEAKS=(
  "frolich" "hyattsville" "workroom@" "woodcraft@" "5124"
  "nelma" "nehal" "dahlia" "rg's drapery" "the willard" "mclean whittington"
  "empire workroom" "9408 old courthouse"
)

scan_workroom_records() {
  local blob="$1"
  contains_any "$blob" "${WORKROOM_RECORD_LEAKS[@]}"
}

check_home_v3() {
  local label="$1" base="$2" token="$3" env_file="$4" expected_root="$5"
  local data_dir ed raw path status
  data_dir="$(read_env_key "$env_file" EMPIRE_DATA_DIR || true)"
  echo "  EMPIRE_DATA_DIR=$data_dir"
  if [ "$data_dir" != "$expected_root" ]; then
    fail "$label EMPIRE_DATA_DIR debe ser $expected_root"
  else
    pass "$label EMPIRE_DATA_DIR=$expected_root"
  fi

  ed="$(curl -sS -H "Authorization: Bearer $token" "$base/api/v1/edition")"
  path="$(printf '%s' "$ed" | "$PYTHON" -c 'import json,sys; d=json.load(sys.stdin); a=d.get("assistant") or {}; print(a.get("memory_path") or a.get("history_path") or "")')"
  if [ -n "$path" ]; then
    echo "  edition memory_path: $path"
    if printf '%s' "$path" | grep -q "^$expected_root"; then
      pass "$label home v3 memoria bajo $expected_root"
    else
      fail "$label home v3 memoria fuera de $expected_root"
    fi
  fi
  if printf '%s' "$ed" | grep -Eqi '/home/rg/empire-repo|/data/maxine|empire-data'; then
    fail "$label GET /edition apunta a otro árbol"
  fi

  local ep
  for ep in \
    "/api/v1/quotes-v2?limit=500" \
    "/api/v1/jobs?limit=500" \
    "/api/v1/leads/?limit=500" \
    "/api/v1/finance/dashboard" \
    "/api/v1/payments/overdue"
  do
    raw="$(curl -sS -w '\n%{http_code}' -H "Authorization: Bearer $token" "$base$ep")"
    status="${raw##*$'\n'}"
    raw="${raw%$'\n'*}"
    echo "  GET $ep → $status"
    if [ "$status" != "200" ]; then
      fail "$label home v3 $ep HTTP $status"
      continue
    fi
    if ! printf '%s' "$raw" | "$PYTHON" -c 'import json,sys; json.load(sys.stdin)' >/dev/null 2>&1; then
      fail "$label home v3 $ep no es JSON"
      continue
    fi
    if scan_workroom_records "$raw"; then
      fail "$label home v3 $ep devolvió registros del Workroom"
      continue
    fi
    pass "$label home v3 $ep solo datos de $expected_root"
  done
}

check_usage() {
  local label="$1" base="$2" token="$3"
  local raw keys
  raw="$(curl -sS -H "Authorization: Bearer $token" "$base/api/v1/edition/usage")"
  echo "$raw" | "$PYTHON" -c 'import json,sys; json.load(sys.stdin)' >/dev/null
  keys="$(printf '%s' "$raw" | json_keys)"
  echo "  usage keys: $keys"
  echo "  usage body: $raw"
  if printf '%s' "$keys" | grep -Eq '(^| )(baseline|baseline_basis|allowance|used|day|month|ratio|tokens|cost|usd)( |$)'; then
    fail "$label usage expone totales (solo porcentajes)"
    return
  fi
  if ! USAGE_JSON="$raw" "$PYTHON" -c '
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
  if contains_any "$reply" "${WORKROOM_RECORD_LEAKS[@]}"; then
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

  if [ "$edition" = "amp" ]; then
    check_home_v3 "$name" "$base" "$token" "$env_file" "/data/amp"
  fi

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

self_test() {
  local tmp got
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' RETURN
  printf '%s\n' \
    '# comment' \
    'AMP_JWT_SECRET=test-secret' \
    'AMP_OWNER_EMAIL=owner@example.com' \
    'SMTP_FROM=Empire <empirebox2026@gmail.com>' \
    'export EMPIRE_DATA_DIR=/data/amp' \
    'QUOTED="hello world"' \
    'AMP_JWT_SECRET=last-wins' \
    > "$tmp"
  got="$(read_env_key "$tmp" SMTP_FROM)"
  if [ "$got" != "Empire <empirebox2026@gmail.com>" ]; then
    echo "self-test SMTP_FROM got: $got" >&2
    return 1
  fi
  got="$(read_env_key "$tmp" AMP_JWT_SECRET)"
  if [ "$got" != "last-wins" ]; then
    echo "self-test AMP_JWT_SECRET got: $got" >&2
    return 1
  fi
  got="$(read_env_key "$tmp" EMPIRE_DATA_DIR)"
  if [ "$got" != "/data/amp" ]; then
    echo "self-test EMPIRE_DATA_DIR got: $got" >&2
    return 1
  fi
  got="$(read_env_key "$tmp" QUOTED)"
  if [ "$got" != "hello world" ]; then
    echo "self-test QUOTED got: $got" >&2
    return 1
  fi
  if ! "$PYTHON" -c 'import jose' >/dev/null 2>&1; then
    if [ -x "$ROOT/backend/venv/bin/python" ] || [ -x "$ROOT/backend/venv/bin/python3" ]; then
      echo "self-test: $PYTHON no importa jose (venv roto)" >&2
      return 1
    fi
    echo "self-test: PATH python sin jose (ok si no hay venv)"
  fi
  echo "self-test ok  python=$PYTHON"
}

echo "Chequeo post-deploy (solo lectura de Workroom; loopback)."
echo "Repo: $ROOT"
echo "Python: $PYTHON"

if [ "$TARGET" = "--self-test" ]; then
  self_test
  exit $?
fi

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
