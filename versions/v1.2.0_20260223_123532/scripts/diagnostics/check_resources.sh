#!/bin/bash
# Real-time resource monitor for EmpireBox
# Alerts if memory, swap, or Docker resources exceed safe thresholds
# Device: AZW EQ mini PC (Beelink EQR5)

MEM_WARN_PCT=70
MEM_CRIT_PCT=85
DOCKER_MEM_WARN_PCT=20  # warn if a single container uses this % of host memory
LOG_FILE="/var/log/empirebox/resources.log"
INTERVAL=${1:-5}  # seconds between checks, default 5

mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null

log() {
    local level="$1"
    local msg="$2"
    local entry="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $msg"
    echo "$entry"
    echo "$entry" >> "$LOG_FILE" 2>/dev/null
}

check_memory() {
    local total used pct
    total=$(free -m | awk '/^Mem:/{print $2}')
    used=$(free -m  | awk '/^Mem:/{print $3}')
    pct=$(( used * 100 / total ))

    if [ "$pct" -ge "$MEM_CRIT_PCT" ]; then
        log "CRITICAL" "Memory usage ${pct}% (${used}MB / ${total}MB) — above critical threshold ${MEM_CRIT_PCT}%"
        return 2
    elif [ "$pct" -ge "$MEM_WARN_PCT" ]; then
        log "WARN" "Memory usage ${pct}% (${used}MB / ${total}MB) — above warning threshold ${MEM_WARN_PCT}%"
        return 1
    else
        log "OK" "Memory usage ${pct}% (${used}MB / ${total}MB)"
        return 0
    fi
}

check_swap() {
    local total used
    total=$(free -m | awk '/^Swap:/{print $2}')
    used=$(free -m  | awk '/^Swap:/{print $3}')
    if [ "$total" -gt 0 ]; then
        local pct=$(( used * 100 / total ))
        if [ "$pct" -ge 50 ]; then
            log "WARN" "Swap usage ${pct}% (${used}MB / ${total}MB) — high swap suggests memory pressure"
        fi
    fi
}

check_docker() {
    if ! command -v docker &>/dev/null; then
        return
    fi
    local count
    count=$(docker ps -q 2>/dev/null | wc -l)
    log "INFO" "Docker running containers: $count"

    # Check for containers using excessive memory
    docker stats --no-stream --format "{{.Name}}\t{{.MemPerc}}" 2>/dev/null | while IFS=$'\t' read -r name mem_pct; do
        # Strip the % sign
        local pct="${mem_pct//%/}"
        if [ -n "$pct" ] && awk "BEGIN{exit !($pct >= $DOCKER_MEM_WARN_PCT)}"; then
            log "WARN" "Container '$name' using ${mem_pct} of host memory"
        fi
    done
}

log "INFO" "=== EmpireBox Resource Monitor started (interval: ${INTERVAL}s) ==="

while true; do
    check_memory
    check_swap
    check_docker
    sleep "$INTERVAL"
done
