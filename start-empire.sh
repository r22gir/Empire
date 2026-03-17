#!/usr/bin/env bash
# start-empire.sh — Launch all Empire services via systemd
set -uo pipefail

G='\033[0;32m' R='\033[0;31m' Y='\033[1;33m' C='\033[0;36m' N='\033[0m'

log() { echo -e "${C}[Empire]${N} $1"; }
ok()  { echo -e "${G}[OK]${N} $1"; }
err() { echo -e "${R}[FAIL]${N} $1"; }

# ── Ensure service files are installed ───────────────────────────
SYSTEMD_DIR="/etc/systemd/system"
REPO_DIR="$HOME/empire-repo/systemd"

for svc in empire-backend empire-cc empire-openclaw; do
    if [ ! -f "$SYSTEMD_DIR/${svc}.service" ]; then
        log "Installing ${svc}.service..."
        sudo cp "$REPO_DIR/${svc}.service" "$SYSTEMD_DIR/"
    fi
done
sudo systemctl daemon-reload

# ── Start/restart services ───────────────────────────────────────
log "Starting Empire services..."

for svc in empire-backend empire-cc empire-openclaw; do
    if systemctl is-active --quiet "$svc"; then
        log "Restarting $svc..."
        sudo systemctl restart "$svc"
    else
        log "Starting $svc..."
        sudo systemctl start "$svc"
    fi
done

# Wait for services to come up
sleep 3

# ── Status ───────────────────────────────────────────────────────
echo ""
echo -e "${Y}=============================================${N}"
echo -e "${Y}         Empire Services Status              ${N}"
echo -e "${Y}=============================================${N}"
for pair in "empire-backend:Backend API:8000" "empire-cc:Command Center:3005" "empire-openclaw:OpenClaw AI:7878" "ollama:Ollama:11434"; do
    svc="${pair%%:*}"; rest="${pair#*:}"; name="${rest%%:*}"; port="${rest##*:}"
    if systemctl is-active --quiet "$svc"; then
        echo -e "  ${G}*${N} $name — :$port (systemd: active)"
    else
        echo -e "  ${R}*${N} $name — :$port (systemd: inactive)"
    fi
done

echo -e "\n  Logs:   ${C}journalctl -u empire-backend -f${N}"
echo -e "  Stop:   ${C}sudo systemctl stop empire-backend empire-cc empire-openclaw${N}"
echo -e "  Status: ${C}systemctl status empire-backend empire-cc empire-openclaw${N}"
echo -e "${Y}=============================================${N}"
