#!/usr/bin/env bash
# EmpireBox USB Auto-Configuration Watcher
# Watches for a USB drive containing empirebox-config.json and triggers setup.
set -euo pipefail

CONFIG_DIR="/var/lib/empirebox"
WATCH_DIR="/media"
CONFIG_FILENAME="empirebox-config.json"
SCHEMA_FILE="$(dirname "$(realpath "$0")")/../config/config-schema.json"
LOG_FILE="/var/log/empirebox/usb-autoconfig.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

install_deps() {
    local missing=()
    command -v inotifywait &>/dev/null || missing+=(inotify-tools)
    command -v python3    &>/dev/null || missing+=(python3)

    if [[ ${#missing[@]} -gt 0 ]]; then
        log "Installing dependencies: ${missing[*]}"
        apt-get update -qq
        apt-get install -y "${missing[@]}"
    fi
}

validate_config() {
    local config_file="$1"
    log "Validating config: $config_file"

    python3 - "$config_file" <<'PYEOF'
import json, sys

config_file = sys.argv[1]
with open(config_file) as f:
    config = json.load(f)

required_fields = ["licenseKey", "accountEmail", "selectedProducts"]
missing = [field for field in required_fields if field not in config]
if missing:
    print(f"ERROR: Missing required fields: {missing}", file=sys.stderr)
    sys.exit(1)

license_key = config.get("licenseKey", "")
if not license_key.startswith("EMPIRE-") or len(license_key.split("-")) != 5:
    print("ERROR: Invalid license key format. Expected EMPIRE-XXXX-XXXX-XXXX-XXXX", file=sys.stderr)
    sys.exit(1)

account_email = config.get("accountEmail", "")
if "@" not in account_email:
    print("ERROR: Invalid accountEmail format", file=sys.stderr)
    sys.exit(1)

print("Config validation passed.")
PYEOF
}

process_config() {
    local usb_config="$1"
    local dest="$CONFIG_DIR/empirebox-config.json"

    log "Valid config found at: $usb_config"
    cp "$usb_config" "$dest"
    log "Config copied to $dest"

    # Trigger bulk install
    log "Triggering bulk install..."
    bash "$(dirname "$(realpath "$0")")/bulk-install.sh" "$dest" &
    log "Bulk install started (PID: $!)"
}

watch_for_config() {
    log "Watching $WATCH_DIR for USB drives containing $CONFIG_FILENAME..."

    # Also check if a USB is already mounted
    find "$WATCH_DIR" -maxdepth 3 -name "$CONFIG_FILENAME" 2>/dev/null | while read -r found; do
        if validate_config "$found" 2>&1 | grep -q "passed"; then
            process_config "$found"
            return
        fi
    done

    # Use inotifywait to watch for new mounts
    inotifywait -m -r --event create --event moved_to --format '%w%f' "$WATCH_DIR" 2>/dev/null | \
    while read -r filepath; do
        if [[ "$(basename "$filepath")" == "$CONFIG_FILENAME" ]]; then
            log "Detected $CONFIG_FILENAME at $filepath"
            if validate_config "$filepath" 2>&1 | grep -q "passed"; then
                process_config "$filepath"
            else
                log "WARN: Config validation failed for $filepath"
            fi
        fi
    done
}

main() {
    mkdir -p "$CONFIG_DIR" "$(dirname "$LOG_FILE")"
    log "EmpireBox USB auto-config watcher starting..."
    install_deps
    watch_for_config
}

main "$@"
