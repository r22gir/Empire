#!/usr/bin/env bash
# EmpireBox Post-Installation Script
# Run as root or with sudo on Ubuntu 24.04 LTS
# Usage: sudo bash hardware/configs/post-install.sh

set -euo pipefail

echo "=== EmpireBox Post-Install Setup ==="

# ── 1. System update ──────────────────────────────────────────────────────────
echo "[1/7] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# ── 2. Essential packages ──────────────────────────────────────────────────────
echo "[2/7] Installing essential packages..."
apt-get install -y -qq \
  curl wget git htop unzip \
  build-essential python3-pip python3-venv \
  net-tools ufw ca-certificates gnupg lsb-release

# ── 3. Docker ──────────────────────────────────────────────────────────────────
echo "[3/7] Installing Docker..."
if ! command -v docker &>/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  # Allow current user to run Docker without sudo
  usermod -aG docker "${SUDO_USER:-$(whoami)}"
  echo "Docker installed. You may need to log out and back in for group changes."
else
  echo "Docker already installed — skipping."
fi

# ── 4. Docker Compose (standalone) ────────────────────────────────────────────
echo "[4/7] Checking Docker Compose..."
if ! docker compose version &>/dev/null; then
  COMPOSE_VERSION=$(curl -fsSL https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d'"' -f4)
  curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  echo "Docker Compose installed."
else
  echo "Docker Compose already available — skipping."
fi

# ── 5. Firewall ────────────────────────────────────────────────────────────────
echo "[5/7] Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 7878/tcp  # OpenClaw
ufw --force enable
echo "Firewall configured."

# ── 6. Automatic security updates ─────────────────────────────────────────────
echo "[6/7] Enabling automatic security updates..."
apt-get install -y -qq unattended-upgrades
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

# ── 7. SSD TRIM ───────────────────────────────────────────────────────────────
echo "[7/7] Enabling SSD TRIM..."
systemctl enable fstrim.timer
systemctl start fstrim.timer

echo ""
echo "=== EmpireBox Post-Install Complete ==="
echo "Next steps:"
echo "  1. Clone Empire repo:  git clone https://github.com/r22gir/Empire.git"
echo "  2. Configure .env:     cp Empire/.env.example Empire/.env && nano Empire/.env"
echo "  3. Start stack:        cd Empire && docker compose up -d"
echo "  4. Health check:       curl http://localhost:8000/health"
