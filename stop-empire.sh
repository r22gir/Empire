#!/usr/bin/env bash
# stop-empire.sh — Cleanly stop all Empire services by port
G='\033[0;32m' C='\033[0;36m' N='\033[0m'

echo -e "${C}[Empire]${N} Stopping services..."
for pair in "Backend API:8000" "Founder Dashboard:3009" "Empire App:3000" "WorkroomForge:3001"; do
    name="${pair%%:*}"; port="${pair##*:}"
    if fuser "$port/tcp" >/dev/null 2>&1; then
        fuser -k "$port/tcp" >/dev/null 2>&1
        echo -e "  ${G}*${N} $name (:$port) — stopped"
    else
        echo "  o $name (:$port) — not running"
    fi
done
echo -e "${C}[Empire]${N} Done."
