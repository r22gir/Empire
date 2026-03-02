#!/bin/bash
# Empire Backup — Zips entire Empire folder to external 1TB drive
# Usage: bash ~/Empire/scripts/backup.sh
# Schedule: Run before major changes or weekly via cron

BACKUP_DIR="/media/rg/BACKUP1/EmpireBackups"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
BACKUP_FILE="$BACKUP_DIR/empire_backup_$TIMESTAMP.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "╔══════════════════════════════════════╗"
echo "║     EMPIRE BACKUP — $TIMESTAMP       ║"
echo "╚══════════════════════════════════════╝"

# Check external drive
if [ ! -d "/media/rg/BACKUP1" ]; then
    echo "❌ External drive not mounted at /media/rg/BACKUP1"
    echo "   Plug in the 1TB drive and try again."
    exit 1
fi

# Check space (need at least 1GB free)
AVAIL=$(df --output=avail /media/rg/BACKUP1 | tail -1)
if [ "$AVAIL" -lt 1048576 ]; then
    echo "❌ Less than 1GB free on external drive"
    exit 1
fi

echo "📦 Backing up ~/Empire..."
echo "   Excluding: node_modules, .next, __pycache__, .venv, .git objects"

tar -czf "$BACKUP_FILE" \
    --exclude='node_modules' \
    --exclude='.next' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='.git/objects' \
    --exclude='*.pyc' \
    -C "$HOME" Empire

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo "✅ Backup complete!"
echo "   File: $BACKUP_FILE"
echo "   Size: $SIZE"
echo ""

# Keep last 10 backups, remove older ones
echo "🧹 Cleaning old backups (keeping last 10)..."
ls -t "$BACKUP_DIR"/empire_backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm
TOTAL=$(ls "$BACKUP_DIR"/empire_backup_*.tar.gz 2>/dev/null | wc -l)
echo "   $TOTAL backups stored"

# Show backup drive space
echo ""
df -h /media/rg/BACKUP1 | tail -1 | awk '{print "📁 External drive: "$3" used / "$2" total ("$5" full)"}'
