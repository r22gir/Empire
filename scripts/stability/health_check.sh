#!/bin/bash
# EmpireBox Health Check — run every 5 minutes via cron
# Monitors memory, swap, and native services
# Docker is disabled — deployment planned for future use only
#
# Automated install: sudo bash scripts/setup/apply_stability_fixes.sh
# Manual install:    sudo crontab -e
#                    */5 * * * * /opt/empirebox/scripts/health_check.sh

LOG_DIR="/var/log/empirebox"
LOG_FILE="$LOG_DIR/health.log"
MEM_WARN_PCT=80
MEM_CRIT_PCT=90

mkdir -p "$LOG_DIR"

log() {
    local level="$1"
    local msg="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $msg" | tee -a "$LOG_FILE"
}

get_mem_pct() {
    free -m | awk '/^Mem:/{printf "%d", $3*100/$2}'
}

check_memory() {
    local pct
    pct=$(get_mem_pct)

    if [ "$pct" -ge "$MEM_CRIT_PCT" ]; then
        log "CRITICAL" "Memory at ${pct}% — manual intervention required"
    elif [ "$pct" -ge "$MEM_WARN_PCT" ]; then
        log "WARN" "Memory at ${pct}% — elevated"
    else
        log "OK" "Memory at ${pct}% — within safe limits"
    fi
}

check_ollama() {
    if systemctl is-active --quiet ollama.service 2>/dev/null; then
        log "OK" "Ollama service running"
    else
        log "WARN" "Ollama service not running — attempting restart"
        systemctl start ollama.service 2>/dev/null && log "INFO" "Ollama service started" \
            || log "ERROR" "Failed to start Ollama service"
    fi
}

check_temperatures() {
    if command -v sensors &>/dev/null; then
        local cpu_temp
        cpu_temp=$(sensors 2>/dev/null | grep -i "Tctl" | awk '{print $2}' | tr -d '+°C')
        if [ -n "$cpu_temp" ]; then
            if awk "BEGIN{exit !($cpu_temp >= 85)}"; then
                log "WARN" "CPU temperature ${cpu_temp}°C is elevated"
            else
                log "OK" "CPU temperature ${cpu_temp}°C is normal"
            fi
        fi
    fi
}

log "INFO" "=== Health check started ==="
check_memory
check_ollama
check_temperatures
log "INFO" "=== Health check complete ==="
