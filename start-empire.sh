#!/usr/bin/env bash
# start-empire.sh — Launch all Empire services
set -uo pipefail

EMPIRE="$HOME/empire-repo"
LOG_DIR="$EMPIRE/logs"
VENV_PYTHON="$EMPIRE/backend/venv/bin/python3"
TS=$(date +%Y%m%d_%H%M%S)

mkdir -p "$LOG_DIR"

G='\033[0;32m' R='\033[0;31m' Y='\033[1;33m' C='\033[0;36m' N='\033[0m'

log() { echo -e "${C}[Empire]${N} $1"; }
ok()  { echo -e "${G}[OK]${N} $1"; }
err() { echo -e "${R}[FAIL]${N} $1"; }

wait_port() {
    local port=$1 i=0
    while [ $i -lt 40 ]; do
        local code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null)
        if [ "$code" = "200" ] || [ "$code" = "404" ]; then return 0; fi
        code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" 2>/dev/null)
        if [ "$code" = "200" ] || [ "$code" = "307" ]; then return 0; fi
        sleep 1; i=$((i + 1))
    done
    return 1
}

ensure_node_modules() {
    local dir=$1
    if [ ! -d "$dir/node_modules" ]; then
        log "Installing dependencies in $(basename "$dir")..."
        (cd "$dir" && npm install --loglevel=error 2>&1 | tail -3)
    fi
}

# ── Kill existing ────────────────────────────────────────────────
log "Clearing ports 8000, 3005, 3000, 7878..."
fuser -k 8000/tcp 2>/dev/null
fuser -k 3005/tcp 2>/dev/null
fuser -k 3000/tcp 2>/dev/null
fuser -k 7878/tcp 2>/dev/null
sleep 2
ok "Ports cleared"

# ── 1. Backend API (port 8000) ───────────────────────────────────
log "Starting Backend API on port 8000..."
cd "$EMPIRE/backend"
nohup "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/backend_${TS}.log" 2>&1 &

if wait_port 8000; then
    ok "Backend API — http://localhost:8000"
else
    err "Backend — check $LOG_DIR/backend_${TS}.log"
fi

# ── 2. Empire Command Center (port 3005) ─────────────────────────
ensure_node_modules "$EMPIRE/empire-command-center"
log "Starting Empire Command Center on port 3005..."
cd "$EMPIRE/empire-command-center"
# Remove stale lock if present
rm -f "$EMPIRE/empire-command-center/.next/dev/lock"
nohup npx next dev -p 3005 \
    > "$LOG_DIR/command_center_${TS}.log" 2>&1 &

if wait_port 3005; then
    ok "Empire Command Center — http://localhost:3005"
else
    err "Empire Command Center — check $LOG_DIR/command_center_${TS}.log"
fi

# ── 3. Empire App (port 3000) ────────────────────────────────────
ensure_node_modules "$EMPIRE/empire-app"
log "Starting Empire App on port 3000..."
cd "$EMPIRE/empire-app"
nohup npx next dev -p 3000 \
    > "$LOG_DIR/empire_app_${TS}.log" 2>&1 &

if wait_port 3000; then
    ok "Empire App — http://localhost:3000"
else
    err "Empire App — check $LOG_DIR/empire_app_${TS}.log"
fi

# ── WorkroomForge (:3001) and LuxeForge (:3002) retired ──────────
# Replaced by Command Center (:3005)

# ── 4. OpenClaw AI Server (port 7878) ──────────────────────────
log "Starting OpenClaw AI on port 7878..."
cd "$EMPIRE/openclaw"
nohup "$VENV_PYTHON" server.py \
    > "$LOG_DIR/openclaw_${TS}.log" 2>&1 &

if wait_port 7878; then
    ok "OpenClaw AI — http://localhost:7878"
else
    err "OpenClaw — check $LOG_DIR/openclaw_${TS}.log"
fi

# ── Open browser (Command Center only — Empire App is secondary) ──
sleep 1
xdg-open "http://localhost:3005" 2>/dev/null &

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo -e "${Y}=============================================${N}"
echo -e "${Y}         Empire Services Status              ${N}"
echo -e "${Y}=============================================${N}"
for pair in "Backend API:8000" "Command Center:3005" "Empire App:3000" "OpenClaw AI:7878" "Ollama:11434"; do
    name="${pair%%:*}"; port="${pair##*:}"
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null)
    [ "$code" = "000" ] && code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" 2>/dev/null)
    if [ "$code" = "200" ] || [ "$code" = "307" ] || [ "$code" = "404" ]; then
        echo -e "  ${G}*${N} $name — :$port"
    else
        echo -e "  ${R}*${N} $name — :$port (down)"
    fi
done
echo -e "\n  Logs: ${C}$LOG_DIR/${N}"
echo -e "  Stop: ${C}$EMPIRE/stop-empire.sh${N}"
echo -e "${Y}=============================================${N}"
