#!/usr/bin/env bash
# EmpireBox Bulk Install Script
# Reads config JSON and installs all selected products and AI models.
set -euo pipefail

CONFIG_FILE="${1:-/var/lib/empirebox/empirebox-config.json}"
INSTALL_DIR="/opt/empirebox"
LOG_FILE="/var/log/empirebox/bulk-install.log"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

read_config() {
    python3 -c "import json,sys; data=json.load(open('$CONFIG_FILE')); print(json.dumps(data))"
}

get_config_value() {
    python3 -c "import json; data=json.load(open('$CONFIG_FILE')); print(data.get('$1',''))"
}

get_config_array() {
    python3 -c "import json; data=json.load(open('$CONFIG_FILE')); print(' '.join(data.get('$1',[])))"
}

install_system_packages() {
    log "Updating system packages..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get upgrade -y -qq
    apt-get install -y curl wget git jq python3 python3-pip ca-certificates gnupg lsb-release
}

install_docker() {
    if command -v docker &>/dev/null; then
        log "Docker already installed: $(docker --version)"
        return
    fi

    log "Installing Docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    log "Docker installed: $(docker --version)"
}

install_ollama() {
    if command -v ollama &>/dev/null; then
        log "Ollama already installed."
        return
    fi

    log "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    systemctl enable ollama
    systemctl start ollama
    log "Ollama installed."
}

pull_ollama_models() {
    local models
    models=$(get_config_array "ollamaModels")
    if [[ -z "$models" ]]; then
        log "No Ollama models specified."
        return
    fi

    log "Pulling Ollama models: $models"
    local pids=()
    for model in $models; do
        log "  Pulling $model..."
        ollama pull "$model" &
        pids+=($!)
    done
    local failed=0
    for pid in "${pids[@]}"; do
        wait "$pid" || { log "WARN: A model pull failed (PID $pid)"; failed=$((failed + 1)); }
    done
    if [[ $failed -gt 0 ]]; then
        log "WARN: $failed model pull(s) failed."
    fi
    log "Ollama model pulls finished."
}

declare -A PRODUCT_IMAGES=(
    [marketforge]="empirebox/marketforge:latest"
    [supportforge]="empirebox/supportforge:latest"
    [contractorforge]="empirebox/contractorforge:latest"
    [luxeforge]="empirebox/luxeforge:latest"
    [leadforge]="empirebox/leadforge:latest"
    [shipforge]="empirebox/shipforge:latest"
    [forgecrm]="empirebox/forgecrm:latest"
    [relistapp]="empirebox/relistapp:latest"
    [socialforge]="empirebox/socialforge:latest"
    [llcfactory]="empirebox/llcfactory:latest"
    [apostapp]="empirebox/apostapp:latest"
    [empireassist]="empirebox/empireassist:latest"
)

generate_docker_compose() {
    local products
    products=$(get_config_array "selectedProducts")
    local timezone
    timezone=$(get_config_value "timezone")
    timezone="${timezone:-America/New_York}"

    log "Generating docker-compose.yml for products: $products"
    mkdir -p "$INSTALL_DIR"

    cat > "$COMPOSE_FILE" <<YAML
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    restart: unless-stopped
    depends_on:
$(for product in $products; do
    echo "      - $product"
done)

YAML

    local port=8001
    for product in $products; do
        local image="${PRODUCT_IMAGES[$product]:-empirebox/${product}:latest}"
        cat >> "$COMPOSE_FILE" <<YAML
  $product:
    image: $image
    environment:
      - TZ=$timezone
      - LICENSE_KEY=\${LICENSE_KEY}
    ports:
      - "$port:8080"
    restart: unless-stopped
    volumes:
      - ${product}_data:/data

YAML
        port=$((port + 1))
    done

    # Add volumes section
    echo "volumes:" >> "$COMPOSE_FILE"
    for product in $products; do
        echo "  ${product}_data:" >> "$COMPOSE_FILE"
    done

    log "docker-compose.yml generated at $COMPOSE_FILE"
}

create_env_file() {
    local license_key
    license_key=$(get_config_value "licenseKey")
    local account_email
    account_email=$(get_config_value "accountEmail")

    cat > "$INSTALL_DIR/.env" <<EOF
LICENSE_KEY=$license_key
ACCOUNT_EMAIL=$account_email
EOF
    chmod 600 "$INSTALL_DIR/.env"
    log ".env file created."
}

configure_autostart() {
    log "Configuring autostart..."
    cat > /etc/systemd/system/empirebox.service <<EOF
[Unit]
Description=EmpireBox Services
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable empirebox.service
    log "Autostart configured."
}

configure_wifi() {
    local ssid
    ssid=$(python3 -c "import json; data=json.load(open('$CONFIG_FILE')); wifi=data.get('wifi',{}); print(wifi.get('ssid',''))" 2>/dev/null || echo "")
    local password
    password=$(python3 -c "import json; data=json.load(open('$CONFIG_FILE')); wifi=data.get('wifi',{}); print(wifi.get('password',''))" 2>/dev/null || echo "")

    if [[ -z "$ssid" ]]; then
        log "No WiFi config specified, skipping."
        return
    fi

    log "Configuring WiFi: $ssid"
    if command -v nmcli &>/dev/null; then
        nmcli dev wifi connect "$ssid" password "$password" 2>/dev/null || log "WARN: WiFi connection failed"
    elif command -v wpa_supplicant &>/dev/null; then
        wpa_passphrase "$ssid" "$password" >> /etc/wpa_supplicant/wpa_supplicant.conf
        wpa_cli -i wlan0 reconfigure 2>/dev/null || true
    fi
}

report_completion() {
    local device_id
    device_id=$(cat /var/lib/empirebox/device-id 2>/dev/null || echo "UNKNOWN")
    log "Reporting completion to setup portal..."
    curl -sfSL -X POST "https://setup.empirebox.com/api/device/${device_id}/complete" \
        -H "Content-Type: application/json" \
        -d '{"status":"complete","timestamp":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}' \
        2>/dev/null || log "WARN: Could not report completion (no internet?)"
}

main() {
    mkdir -p "$INSTALL_DIR" "$(dirname "$LOG_FILE")"
    log "===== EmpireBox Bulk Install Starting ====="
    log "Config: $CONFIG_FILE"

    if [[ ! -f "$CONFIG_FILE" ]]; then
        log "ERROR: Config file not found: $CONFIG_FILE"
        exit 1
    fi

    install_system_packages
    install_docker
    configure_wifi
    generate_docker_compose
    create_env_file
    install_ollama
    pull_ollama_models

    log "Starting Docker services..."
    cd "$INSTALL_DIR"
    docker compose pull
    docker compose up -d

    configure_autostart
    report_completion

    log "===== EmpireBox Bulk Install Complete ====="
}

main "$@"
