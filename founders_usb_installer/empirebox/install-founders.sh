#!/bin/bash
# EmpireBox Founders Unit - Master Install Script
# Target: Beelink EQR5 - Ubuntu Server 24.04
# Version: 1.0.0

set -euo pipefail

INSTALL_PATH="/opt/empirebox"
LOG_FILE="/var/log/empirebox-install.log"
ENV_FILE="${INSTALL_PATH}/.env"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
die() { log "ERROR: $*"; exit 1; }

# ──────────────────────────────────────────────
# 1. SYSTEM SETUP
# ──────────────────────────────────────────────
log "=== EmpireBox Founders Install Started ==="

hostnamectl set-hostname empirebox-founders
apt-get update -y
apt-get upgrade -y
apt-get install -y curl wget git jq htop vim net-tools avahi-daemon ufw \
  ca-certificates gnupg lsb-release software-properties-common

# ──────────────────────────────────────────────
# 2. DOCKER
# ──────────────────────────────────────────────
log "=== Installing Docker ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  usermod -aG docker empirebox
  systemctl enable --now docker
fi
log "Docker $(docker --version)"

# ──────────────────────────────────────────────
# 3. GENERATE CREDENTIALS
# ──────────────────────────────────────────────
log "=== Generating Credentials ==="
gen_secret() { openssl rand -hex 32; }

DB_PASSWORD=$(gen_secret)
REDIS_PASSWORD=$(gen_secret)
JWT_SECRET=$(gen_secret)
CONTROL_API_KEY=$(gen_secret)
OPENCLAW_SECRET=$(gen_secret)

mkdir -p "${INSTALL_PATH}"
cat > "${ENV_FILE}" << EOF
# EmpireBox Founders Unit — Generated $(date)
# KEEP THIS FILE SECURE — chmod 600

FOUNDERS_MODE=true
HOSTNAME=empirebox-founders
INSTALL_PATH=${INSTALL_PATH}

# Database
POSTGRES_DB=empirebox
POSTGRES_USER=empirebox
POSTGRES_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql://empirebox:${DB_PASSWORD}@postgres:5432/empirebox

# Redis
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379

# Auth
JWT_SECRET=${JWT_SECRET}

# Control Center
CONTROL_API_KEY=${CONTROL_API_KEY}

# OpenClaw
OPENCLAW_SECRET=${OPENCLAW_SECRET}
OPENCLAW_MODE=founders

# Ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_DEFAULT_MODEL=llama3.1:8b

# Docker network
DOCKER_NETWORK=empirebox
EOF
chmod 600 "${ENV_FILE}"
log "Credentials written to ${ENV_FILE}"

# ──────────────────────────────────────────────
# 4. OLLAMA
# ──────────────────────────────────────────────
log "=== Installing Ollama ==="
if ! command -v ollama &>/dev/null; then
  curl -fsSL https://ollama.ai/install.sh | sh
  systemctl enable --now ollama
fi
sleep 5
# NOTE: Model downloads can take 10-45 minutes depending on internet speed.
# llama3.1:8b ~4.7GB, codellama:7b ~3.8GB, nomic-embed-text ~274MB
log "Pulling Ollama models (this may take 30-45 minutes on first run)..."
for model in llama3.1:8b codellama:7b nomic-embed-text; do
  log "Pulling Ollama model: ${model}"
  ollama pull "${model}" || log "WARN: Failed to pull ${model}, retry with: ollama pull ${model}"
done

# ──────────────────────────────────────────────
# 5. DOCKER NETWORK
# ──────────────────────────────────────────────
log "=== Creating Docker Network ==="
docker network create empirebox 2>/dev/null || true

# ──────────────────────────────────────────────
# 6. EMPIREBOX CORE SERVICES
# ──────────────────────────────────────────────
log "=== Starting Core Services ==="
cd "${INSTALL_PATH}"
# Load env
set -a; source "${ENV_FILE}"; set +a
docker compose -f docker-compose.yml up -d
log "Core services started"

# ──────────────────────────────────────────────
# 7. EBOX CLI
# ──────────────────────────────────────────────
log "=== Installing ebox CLI ==="
cp "${INSTALL_PATH}/scripts/ebox" /usr/local/bin/ebox
chmod +x /usr/local/bin/ebox
log "ebox CLI installed at /usr/local/bin/ebox"

# ──────────────────────────────────────────────
# 8. FIREWALL
# ──────────────────────────────────────────────
log "=== Configuring Firewall ==="
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp    # Dashboard
ufw allow 443/tcp   # HTTPS
ufw allow 7878/tcp  # OpenClaw
ufw allow 8000/tcp  # API Gateway
ufw allow 8001/tcp  # Control Center
ufw allow 8010:8130/tcp  # Products
ufw allow 9000/tcp  # Portainer
ufw allow 11434/tcp # Ollama
ufw --force enable
log "Firewall configured"

# ──────────────────────────────────────────────
# 9. WAIT FOR SERVICES
# ──────────────────────────────────────────────
log "=== Waiting for services to be healthy ==="
sleep 30

# ──────────────────────────────────────────────
# 10. DONE
# ──────────────────────────────────────────────
IP=$(hostname -I | awk '{print $1}')
log "=== EmpireBox Founders Install Complete ==="
log ""
log "  Dashboard:      http://${IP}"
log "  OpenClaw:       http://${IP}:7878"
log "  Control Center: http://${IP}:8001"
log "  API Gateway:    http://${IP}:8000"
log "  Portainer:      http://${IP}:9000"
log "  Ollama:         http://${IP}:11434"
log ""
log "  Credentials:    ${ENV_FILE}"
log "  Logs:           ${LOG_FILE}"
log ""
log "  Run 'ebox list' to see all products"
log "  Run 'ebox bundle full' to start all products"
