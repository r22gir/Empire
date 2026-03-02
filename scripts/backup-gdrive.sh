#!/bin/bash
# Empire → Google Drive backup
# Usage: ./backup-gdrive.sh
# Account: empirebox2026@gmail.com

set -euo pipefail

GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  Empire → Google Drive Backup"
echo "  Account: empirebox2026@gmail.com"
echo "========================================"
echo ""

# Check rclone
if ! command -v rclone &>/dev/null; then
    echo "rclone not installed. Run: sudo apt install rclone"
    exit 1
fi

# Check remote
if ! rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    echo "gdrive remote not configured. Run: rclone config"
    exit 1
fi

# Show what we're backing up
LOCAL="/home/rg/Empire"
SIZE=$(du -sh --exclude='node_modules' --exclude='venv' --exclude='.venv' --exclude='.git' --exclude='.next' --exclude='__pycache__' "$LOCAL" 2>/dev/null | cut -f1)
echo -e "Source: $LOCAL (${YELLOW}$SIZE${NC} excluding deps)"
echo "Target: gdrive:EmpireBackup"
echo ""

# Sync
rclone sync "$LOCAL" gdrive:EmpireBackup \
    --exclude 'node_modules/**' \
    --exclude 'venv/**' \
    --exclude '.venv/**' \
    --exclude '.next/**' \
    --exclude '.git/**' \
    --exclude '__pycache__/**' \
    --exclude '.claude/**' \
    --transfers 4 \
    --progress

echo ""
echo -e "${GREEN}Backup complete.${NC}"
echo "Timestamp: $(date)"

# Save timestamp locally
date > "$LOCAL/data/.last_gdrive_backup"
echo "Saved timestamp to $LOCAL/data/.last_gdrive_backup"

# Show drive usage
echo ""
rclone about gdrive:
