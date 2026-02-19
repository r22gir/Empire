#!/usr/bin/env bash
# EmpireBox Bluetooth LE Beacon Broadcaster
# Broadcasts an Eddystone-URL beacon so users can discover the device via BLE.
set -euo pipefail

CONFIG_DIR="/var/lib/empirebox"
LOG_FILE="/var/log/empirebox/bluetooth-beacon.log"
BEACON_INTERVAL_MS=1000  # 1 second

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

get_serial() {
    cat "$CONFIG_DIR/serial" 2>/dev/null || echo "UNKNOWN"
}

install_bluetooth_tools() {
    if ! command -v hciconfig &>/dev/null; then
        log "Installing bluetooth tools..."
        apt-get update -qq
        apt-get install -y bluez bluetooth
    fi
}

encode_eddystone_url() {
    # Encode URL for Eddystone-URL frame
    # URL prefix 0x03 = "https://"
    # URL: s.empirebox.com/{SERIAL}
    local serial="$1"
    local url_body="s.empirebox.com/${serial}"
    # Convert to hex bytes
    local encoded
    encoded=$(echo -n "$url_body" | xxd -p | tr -d '\n')
    echo "03${encoded}"
}

start_ble_beacon() {
    local serial="$1"
    local hci_device="${2:-hci0}"

    log "Starting BLE beacon for serial=$serial on $hci_device"

    # Check if HCI device is available
    if ! hciconfig "$hci_device" &>/dev/null; then
        log "ERROR: Bluetooth device $hci_device not found."
        exit 1
    fi

    # Bring up interface
    hciconfig "$hci_device" up

    # Encode Eddystone-URL payload
    local url_encoded
    url_encoded=$(encode_eddystone_url "$serial")
    local url_len=$(( ${#url_encoded} / 2 ))
    local service_data_len=$(( url_len + 4 ))  # 4 bytes for Eddystone-URL header
    local adv_len=$(( service_data_len + 7 ))   # total AD structure length

    # Set advertising data (Eddystone-URL format)
    # Frame type 0x10 = Eddystone-URL, TX Power 0x00
    hcitool -i "$hci_device" cmd 0x08 0x0008 \
        $(printf '%02x' $((adv_len + 1))) \
        02 01 06 \
        03 03 AA FE \
        $(printf '%02x' $((service_data_len + 1))) 16 AA FE 10 00 \
        $url_encoded \
        00 00 00 00 00 00 00 00 00 00 00 00 00 2>/dev/null || true

    # Set advertising parameters: interval ~1000ms (0x0640)
    hcitool -i "$hci_device" cmd 0x08 0x0006 \
        40 06 40 06 00 00 00 00 00 00 00 00 00 07 00 2>/dev/null || true

    # Enable advertising
    hcitool -i "$hci_device" cmd 0x08 0x000A 01 2>/dev/null || true

    log "BLE Eddystone-URL beacon active. URL: https://s.empirebox.com/${serial}"
    log "Beacon interval: ${BEACON_INTERVAL_MS}ms"
}

stop_ble_beacon() {
    local hci_device="${1:-hci0}"
    hcitool -i "$hci_device" cmd 0x08 0x000A 00 2>/dev/null || true
    log "BLE beacon stopped."
}

main() {
    mkdir -p "$(dirname "$LOG_FILE")"

    # Handle stop signal
    trap 'stop_ble_beacon; exit 0' SIGTERM SIGINT

    log "EmpireBox Bluetooth beacon script starting..."

    SERIAL=$(get_serial)
    install_bluetooth_tools
    start_ble_beacon "$SERIAL"

    # Keep running (beacon stays active)
    while true; do
        sleep 60
        # Re-enable advertising in case it timed out
        hcitool -i hci0 cmd 0x08 0x000A 01 2>/dev/null || true
    done
}

main "$@"
