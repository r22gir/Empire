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
        if curl -sf -o /dev/null "http://localhost:$port" 2>/dev/null; then return 0; fi
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
log "Clearing ports 8000, 3009, 3000, 3001..."
fuser -k 8000/tcp 2>/dev/null
fuser -k 3009/tcp 2>/dev/null
fuser -k 3000/tcp 2>/dev/null
fuser -k 3001/tcp 2>/dev/null
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

# ── 2. Founder Dashboard (port 3009) ─────────────────────────────
ensure_node_modules "$EMPIRE/founder_dashboard"
log "Starting Founder Dashboard on port 3009..."
cd "$EMPIRE/founder_dashboard"
nohup npx next dev -p 3009 \
    > "$LOG_DIR/founder_dashboard_${TS}.log" 2>&1 &

if wait_port 3009; then
    ok "Founder Dashboard — http://localhost:3009"
else
    err "Founder Dashboard — check $LOG_DIR/founder_dashboard_${TS}.log"
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

# ── 4. WorkroomForge (port 3001) ─────────────────────────────────
ensure_node_modules "$EMPIRE/workroomforge"
log "Starting WorkroomForge on port 3001..."
cd "$EMPIRE/workroomforge"
nohup npx next dev -p 3001 \
    > "$LOG_DIR/workroomforge_${TS}.log" 2>&1 &

if wait_port 3001; then
    ok "WorkroomForge — http://localhost:3001"
else
    err "WorkroomForge — check $LOG_DIR/workroomforge_${TS}.log"
fi

# ── Open browsers ────────────────────────────────────────────────
sleep 1
xdg-open "http://localhost:3009" 2>/dev/null &
xdg-open "http://localhost:3000" 2>/dev/null &
xdg-open "http://localhost:3001" 2>/dev/null &

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo -e "${Y}=============================================${N}"
echo -e "${Y}         Empire Services Status              ${N}"
echo -e "${Y}=============================================${N}"
for pair in "Backend API:8000" "Founder Dashboard:3009" "Empire App:3000" "WorkroomForge:3001"; do
    name="${pair%%:*}"; port="${pair##*:}"
    if curl -sf -o /dev/null "http://localhost:$port" 2>/dev/null; then
        echo -e "  ${G}*${N} $name — :$port"
    else
        echo -e "  ${R}*${N} $name — :$port (down)"
    fi
done
echo -e "\n  Logs: ${C}$LOG_DIR/${N}"
echo -e "  Stop: ${C}$EMPIRE/stop-empire.sh${N}"
echo -e "${Y}=============================================${N}"
