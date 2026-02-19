#!/usr/bin/env bash
# EmpireBox Network Discovery Script (mDNS/Avahi)
# Broadcasts the device on the local network so users can discover it.
set -euo pipefail

CONFIG_DIR="/var/lib/empirebox"
AVAHI_SERVICES_DIR="/etc/avahi/services"
LOG_FILE="/var/log/empirebox/network-discovery.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

get_serial() {
    cat "$CONFIG_DIR/serial" 2>/dev/null || echo "UNKNOWN"
}

get_device_id() {
    cat "$CONFIG_DIR/device-id" 2>/dev/null || echo "UNKNOWN"
}

get_firmware_version() {
    cat "$CONFIG_DIR/firmware-version" 2>/dev/null || echo "1.0.0"
}

install_avahi() {
    if ! command -v avahi-daemon &>/dev/null; then
        log "Installing avahi-daemon..."
        apt-get update -qq
        apt-get install -y avahi-daemon avahi-utils
    fi
}

configure_avahi() {
    local serial="$1"
    local device_id="$2"
    local firmware="$3"

    log "Configuring Avahi for serial=$serial device_id=$device_id"

    # Set hostname
    hostnamectl set-hostname "EmpireBox-${serial}" 2>/dev/null || true

    # Update /etc/avahi/avahi-daemon.conf if needed
    if [[ -f /etc/avahi/avahi-daemon.conf ]]; then
        sed -i "s/^#host-name=.*/host-name=EmpireBox-${serial}/" /etc/avahi/avahi-daemon.conf
    fi

    # Create mDNS service file
    mkdir -p "$AVAHI_SERVICES_DIR"
    cat > "$AVAHI_SERVICES_DIR/empirebox.service" <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">EmpireBox-${serial}</name>
  <service>
    <type>_empirebox._tcp</type>
    <port>8080</port>
    <txt-record>serial=${serial}</txt-record>
    <txt-record>device_id=${device_id}</txt-record>
    <txt-record>setup_url=https://setup.empirebox.com/device/${device_id}</txt-record>
    <txt-record>firmware=${firmware}</txt-record>
    <txt-record>model=EmpireBox-Mini-Ryzen7</txt-record>
  </service>
  <service>
    <type>_http._tcp</type>
    <port>8080</port>
    <txt-record>path=/setup</txt-record>
  </service>
</service-group>
EOF
    log "mDNS service file written to $AVAHI_SERVICES_DIR/empirebox.service"
}

start_avahi() {
    systemctl enable avahi-daemon
    systemctl restart avahi-daemon
    log "Avahi daemon started."
}

main() {
    mkdir -p "$(dirname "$LOG_FILE")"
    log "EmpireBox network discovery starting..."

    SERIAL=$(get_serial)
    DEVICE_ID=$(get_device_id)
    FIRMWARE=$(get_firmware_version)

    install_avahi
    configure_avahi "$SERIAL" "$DEVICE_ID" "$FIRMWARE"
    start_avahi

    log "Device discoverable as EmpireBox-${SERIAL}.local:8080"
    log "Setup URL: https://setup.empirebox.com/device/${DEVICE_ID}"
}

main "$@"
