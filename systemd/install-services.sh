#!/usr/bin/env bash
# install-services.sh — Install Empire systemd services
# Run with: sudo bash ~/empire-repo/systemd/install-services.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing Empire systemd services ==="

# Stop Ollama (not needed until RecoveryForge)
echo "Stopping and disabling Ollama..."
systemctl stop ollama 2>/dev/null || true
systemctl disable ollama 2>/dev/null || true

# Kill any existing nohup processes on Empire ports
echo "Clearing old processes on ports 8000, 3005, 7878..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3005/tcp 2>/dev/null || true
fuser -k 7878/tcp 2>/dev/null || true
sleep 2

# Copy service files
echo "Installing service files..."
cp "$DIR/empire-backend.service" /etc/systemd/system/
cp "$DIR/empire-cc.service" /etc/systemd/system/
cp "$DIR/empire-openclaw.service" /etc/systemd/system/

# Reload, enable, start
systemctl daemon-reload
echo "Enabling services for boot..."
systemctl enable empire-backend empire-cc empire-openclaw

echo "Starting services..."
systemctl start empire-backend
sleep 2
systemctl start empire-cc
systemctl start empire-openclaw
sleep 3

# Verify
echo ""
echo "=== Service Status ==="
for svc in empire-backend empire-cc empire-openclaw ollama; do
    status=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    enabled=$(systemctl is-enabled "$svc" 2>/dev/null || echo "disabled")
    printf "  %-20s %s (%s)\n" "$svc" "$status" "$enabled"
done

echo ""
echo "Done! Services will survive reboots and terminal disconnects."
echo "View logs: journalctl -u empire-backend -f"
echo "           journalctl -u empire-cc -f"
echo "           journalctl -u empire-openclaw -f"
