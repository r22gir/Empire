#!/bin/bash
# Emergency stop script for EmpireBox
# Gracefully stops non-essential Docker containers when system is under stress
# Usage: sudo bash emergency_stop.sh [--all]

LOG_FILE="/var/log/empirebox/health.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [EMERGENCY] $*" | tee -a "$LOG_FILE"
}

STOP_ALL=false
if [ "${1:-}" = "--all" ]; then
    STOP_ALL=true
fi

log "Emergency stop triggered. Memory before:"
free -h | tee -a "$LOG_FILE"

if $STOP_ALL; then
    log "Stopping ALL Docker containers..."
    docker ps -q | xargs -r docker stop 2>/dev/null
    log "All containers stopped."
else
    # Stop containers that are not marked as essential
    # Essential containers: postgres, redis (data services)
    ESSENTIAL="postgres redis"
    log "Stopping non-essential Docker containers (keeping: $ESSENTIAL)..."

    docker ps --format "{{.Names}}" 2>/dev/null | while read -r name; do
        essential=false
        for e in $ESSENTIAL; do
            if echo "$name" | grep -qi "$e"; then
                essential=true
                break
            fi
        done
        if ! $essential; then
            log "Stopping container: $name"
            docker stop "$name" 2>/dev/null
        else
            log "Keeping essential container: $name"
        fi
    done
fi

log "Memory after emergency stop:"
free -h | tee -a "$LOG_FILE"

echo ""
echo "Emergency stop complete. Check $LOG_FILE for details."
echo "To restart services: docker compose up -d"
