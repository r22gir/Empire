#!/bin/bash
# Empire Backup Check — compare external drive vs local, then sync
# Usage: ./backup-check.sh [sync]
#   No args  = inventory + diff only (safe, read-only)
#   sync     = rsync local → external after confirmation

set -euo pipefail

LOCAL="/home/rg/Empire"
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

# Find the external drive — check all /media/rg/ mounts
EXT=""
for candidate in /media/rg/BACKUP*/EMPIRE /media/rg/BACKUP*; do
    if [ -d "$candidate" ] && mountpoint -q "$(dirname "$candidate")" 2>/dev/null; then
        EXT="$candidate"
        break
    fi
done

# Also check /mnt/empire-backup if set up via fstab
if [ -z "$EXT" ] && [ -d "/mnt/empire-backup/EMPIRE" ]; then
    EXT="/mnt/empire-backup/EMPIRE"
fi

if [ -z "$EXT" ]; then
    echo -e "${RED}No external drive detected.${NC}"
    echo "Plug in the drive and try again."
    echo ""
    echo "Mounted volumes in /media/rg/:"
    ls -la /media/rg/ 2>/dev/null || echo "  (none)"
    echo ""
    echo "Active mounts:"
    mount | grep -E "/media|/mnt" || echo "  (none)"
    exit 1
fi

DRIVE_MOUNT=$(df "$EXT" | tail -1 | awk '{print $NF}')
DRIVE_DEV=$(df "$EXT" | tail -1 | awk '{print $1}')
DRIVE_SIZE=$(df -h "$EXT" | tail -1 | awk '{print $2}')
DRIVE_USED=$(df -h "$EXT" | tail -1 | awk '{print $3}')
DRIVE_AVAIL=$(df -h "$EXT" | tail -1 | awk '{print $4}')

echo "========================================"
echo "  Empire Backup Check"
echo "========================================"
echo -e "External: ${GREEN}$EXT${NC}"
echo "Device:   $DRIVE_DEV"
echo "Mount:    $DRIVE_MOUNT"
echo "Size:     $DRIVE_SIZE (used: $DRIVE_USED, free: $DRIVE_AVAIL)"
echo ""

# Inventory external drive
echo "=== External Drive Contents ==="
if [ -d "$EXT" ]; then
    du -h --max-depth=1 "$EXT" 2>/dev/null | sort -rh | head -25
else
    ls -la "$(dirname "$EXT")" 2>/dev/null
fi
echo ""

# Count files on each side
LOCAL_COUNT=$(find "$LOCAL" -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/venv/*" -not -path "*/.next/*" 2>/dev/null | wc -l)
EXT_COUNT=$(find "$EXT" -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/venv/*" -not -path "*/.next/*" 2>/dev/null | wc -l)
echo "Local files (excluding node_modules/venv/.git/.next): $LOCAL_COUNT"
echo "External files (same exclusions): $EXT_COUNT"
echo ""

# Check for files ONLY on external (not on local)
echo "=== Files only on external (not on local) ==="
diff <(cd "$EXT" && find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/venv/*" -not -path "*/.next/*" 2>/dev/null | sort) \
     <(cd "$LOCAL" && find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/venv/*" -not -path "*/.next/*" 2>/dev/null | sort) \
     | grep "^< " | sed 's/^< /  /' | head -50
echo "(showing first 50)"
echo ""

# Check for files ONLY on local (not on external)
echo "=== Files only on local (not on external) ==="
diff <(cd "$EXT" && find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/venv/*" -not -path "*/.next/*" 2>/dev/null | sort) \
     <(cd "$LOCAL" && find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/venv/*" -not -path "*/.next/*" 2>/dev/null | sort) \
     | grep "^> " | sed 's/^> /  /' | wc -l
echo "files only on local (these will be synced if you run: $0 sync)"
echo ""

# Check MAX brain specifically
echo "=== MAX Brain Check ==="
LOCAL_BRAIN="$LOCAL/backend/data/brain"
EXT_BRAIN="$EXT/../ollama/brain"
if [ -d "$LOCAL_BRAIN" ]; then
    echo -e "Local brain:    ${GREEN}$(ls -la "$LOCAL_BRAIN"/*.db 2>/dev/null | wc -l) db files, $(du -sh "$LOCAL_BRAIN" 2>/dev/null | cut -f1)${NC}"
else
    echo -e "Local brain:    ${RED}not found${NC}"
fi
if [ -d "$EXT_BRAIN" ]; then
    echo -e "External brain: ${GREEN}$(ls -la "$EXT_BRAIN"/*.db 2>/dev/null | wc -l) db files, $(du -sh "$EXT_BRAIN" 2>/dev/null | cut -f1)${NC}"
else
    echo -e "External brain: ${YELLOW}not found (will be created on sync)${NC}"
fi
echo ""

# Sync mode
if [ "${1:-}" = "sync" ]; then
    echo -e "${YELLOW}=== SYNC: Local → External ===${NC}"
    echo "This will rsync ~/Empire/ to the external drive."
    echo "Excludes: node_modules, .git, venv, .next, __pycache__"
    echo ""
    read -p "Proceed? (y/N) " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rsync -av --delete \
            --exclude='node_modules' \
            --exclude='.git' \
            --exclude='venv' \
            --exclude='.venv' \
            --exclude='.next' \
            --exclude='__pycache__' \
            --exclude='.claude' \
            "$LOCAL/" "$EXT/"

        # Also backup brain DBs
        mkdir -p "$(dirname "$EXT")/ollama/brain"
        cp -v "$LOCAL/backend/data/brain/"*.db "$(dirname "$EXT")/ollama/brain/" 2>/dev/null || true

        echo ""
        echo -e "${GREEN}Sync complete.${NC}"
        date > "$EXT/.last_sync"
        echo "Timestamp saved to $EXT/.last_sync"
    else
        echo "Cancelled."
    fi
else
    echo "----------------------------------------"
    echo "To sync local → external, run:"
    echo "  $0 sync"
    echo "----------------------------------------"
fi
