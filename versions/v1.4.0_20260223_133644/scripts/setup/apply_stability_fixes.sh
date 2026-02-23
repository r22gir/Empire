#!/bin/bash
# Apply stability fixes for AZW EQ / Beelink EQR5 mini PC
# Must be run as root: sudo bash apply_stability_fixes.sh
#
# Fixes applied:
#   1. Blacklist kernel modules that cause hard locks (sensors-detect)
#   2. Auto-load safe k10temp sensor module on boot
#   3. Set up health-check cron job
#   4. Create log directory

set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root (sudo)." >&2
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== EmpireBox Stability Fix Script ==="
echo "Repo dir: $REPO_DIR"
echo ""

# 1. Module blacklist
echo "[1/4] Installing module blacklist..."
cp "$REPO_DIR/config/modprobe.d/empirebox-blacklist.conf" /etc/modprobe.d/empirebox-blacklist.conf
echo "      Installed: /etc/modprobe.d/empirebox-blacklist.conf"

# 2. Safe sensor module
echo "[2/4] Configuring k10temp auto-load..."
cp "$REPO_DIR/config/modules-load.d/empirebox-sensors.conf" /etc/modules-load.d/empirebox-sensors.conf
# Load it now without rebooting
modprobe k10temp 2>/dev/null && echo "      k10temp loaded" || echo "      k10temp already loaded or unavailable"

# 3. Log directory
echo "[3/4] Creating log directory..."
mkdir -p /var/log/empirebox
chmod 755 /var/log/empirebox

# 4. Health check cron
echo "[4/4] Installing health-check cron job..."
HEALTH_SCRIPT="/opt/empirebox/scripts/health_check.sh"
mkdir -p /opt/empirebox/scripts
cp "$REPO_DIR/scripts/stability/health_check.sh" "$HEALTH_SCRIPT"
chmod +x "$HEALTH_SCRIPT"

CRON_LINE="*/5 * * * * root $HEALTH_SCRIPT"
CRON_FILE="/etc/cron.d/empirebox-health"
echo "$CRON_LINE" > "$CRON_FILE"
chmod 644 "$CRON_FILE"
echo "      Cron installed: $CRON_FILE"

echo ""
echo "=== All fixes applied successfully ==="
echo ""
echo "IMPORTANT: Run 'sudo update-initramfs -u' to apply module blacklist on next boot."
echo "Reboot is recommended to fully apply all changes."
