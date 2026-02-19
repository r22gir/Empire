#!/usr/bin/env bash
# EmpireBox First Boot Initialization Script
# Detects first boot, starts all discovery services, and waits for configuration.
set -euo pipefail

FLAG_FILE="/var/lib/empirebox/first-boot-done"
CONFIG_DIR="/var/lib/empirebox"
LOG_FILE="/var/log/empirebox/first-boot.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

get_device_serial() {
    local serial
    # Try DMI board serial first, then system serial, then generate from MAC
    serial=$(cat /sys/class/dmi/id/board_serial 2>/dev/null | tr -d '[:space:]')
    if [[ -z "$serial" || "$serial" == "None" || "$serial" == "Default string" ]]; then
        serial=$(cat /sys/class/dmi/id/product_serial 2>/dev/null | tr -d '[:space:]')
    fi
    if [[ -z "$serial" || "$serial" == "None" || "$serial" == "Default string" ]]; then
        serial=$(ip link show | grep -m1 'ether' | awk '{print $2}' | tr -d ':')
    fi
    if [[ -z "$serial" ]]; then
        serial=$(cat /proc/sys/kernel/random/uuid | tr -d '-' | cut -c1-12)
    fi
    echo "${serial^^}"
}

generate_device_id() {
    local serial="$1"
    # Create a deterministic device ID based on serial
    echo "EB-$(echo "$serial" | sha256sum | cut -c1-8 | tr '[:lower:]' '[:upper:]')"
}

main() {
    mkdir -p "$CONFIG_DIR" "$(dirname "$LOG_FILE")"

    log "EmpireBox first-boot script starting..."

    if [[ -f "$FLAG_FILE" ]]; then
        log "First boot already completed. Exiting."
        exit 0
    fi

    log "First boot detected — initializing EmpireBox..."

    # Get hardware identity
    SERIAL=$(get_device_serial)
    DEVICE_ID=$(generate_device_id "$SERIAL")
    log "Device serial: $SERIAL"
    log "Device ID: $DEVICE_ID"

    # Persist identity
    echo "$SERIAL" > "$CONFIG_DIR/serial"
    echo "$DEVICE_ID" > "$CONFIG_DIR/device-id"

    # Start discovery services
    log "Starting discovery services..."
    systemctl start empirebox-discovery.service 2>/dev/null || log "WARN: mDNS discovery service not found"
    systemctl start empirebox-bluetooth.service 2>/dev/null  || log "WARN: Bluetooth service not found"
    systemctl start empirebox-usb-watch.service 2>/dev/null  || log "WARN: USB watcher service not found"

    log "Setup portal available at:"
    log "  http://EmpireBox-${SERIAL}.local:8080"
    log "  https://setup.empirebox.com/device/${DEVICE_ID}"

    # Wait for config to appear (from any discovery method)
    CONFIG_FILE="$CONFIG_DIR/empirebox-config.json"
    log "Waiting for configuration..."
    max_wait=3600  # Wait up to 1 hour
    elapsed=0
    while [[ ! -f "$CONFIG_FILE" && $elapsed -lt $max_wait ]]; do
        sleep 5
        elapsed=$((elapsed + 5))
    done

    if [[ ! -f "$CONFIG_FILE" ]]; then
        log "ERROR: Timed out waiting for configuration."
        exit 1
    fi

    log "Configuration received — starting bulk install..."
    bash "$(dirname "$0")/bulk-install.sh" "$CONFIG_FILE"

    # Mark first boot as done
    touch "$FLAG_FILE"
    log "First boot setup completed successfully."
}

main "$@"
