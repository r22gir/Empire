#!/bin/bash
# EmpireBox Health Check — run every 5 minutes via cron
# Monitors memory, swap, and Docker; restarts services if needed
#
# Automated install: sudo bash scripts/setup/apply_stability_fixes.sh
# Manual install:    sudo crontab -e
#                    */5 * * * * /opt/empirebox/scripts/health_check.sh

LOG_DIR="/var/log/empirebox"
LOG_FILE="$LOG_DIR/health.log"
MEM_RESTART_PCT=80   # restart non-essential Docker containers above this
MEM_CRIT_PCT=90      # emergency stop above this

mkdir -p "$LOG_DIR"

log() {
    local level="$1"
    local msg="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $msg" | tee -a "$LOG_FILE"
}

get_mem_pct() {
    free -m | awk '/^Mem:/{printf "%d", $3*100/$2}'
}

restart_docker_if_needed() {
    local pct
    pct=$(get_mem_pct)

    if [ "$pct" -ge "$MEM_CRIT_PCT" ]; then
        log "CRITICAL" "Memory at ${pct}% — stopping all Docker containers for emergency recovery"
        docker ps -q | xargs -r docker stop 2>/dev/null
        log "CRITICAL" "All containers stopped. Manual intervention required."
    elif [ "$pct" -ge "$MEM_RESTART_PCT" ]; then
        log "WARN" "Memory at ${pct}% — restarting Docker daemon to reclaim memory"
        systemctl restart docker 2>/dev/null && log "INFO" "Docker daemon restarted" \
            || log "ERROR" "Failed to restart Docker daemon (not running as root?)"
    else
        log "OK" "Memory at ${pct}% — within safe limits"
    fi
}

check_docker_daemon() {
    if ! systemctl is-active --quiet docker 2>/dev/null; then
        log "WARN" "Docker daemon is not running — attempting restart"
        systemctl start docker 2>/dev/null && log "INFO" "Docker daemon started" \
            || log "ERROR" "Failed to start Docker daemon"
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
check_docker_daemon
restart_docker_if_needed
check_temperatures
log "INFO" "=== Health check complete ==="
