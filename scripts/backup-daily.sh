#!/bin/bash
# Empire Daily Backup — Database files + git stash
# Runs nightly at 3 AM via cron
# Usage: bash ~/empire-repo/scripts/backup-daily.sh

TIMESTAMP=$(date +%Y%m%d)
DATETIME=$(date '+%Y-%m-%d %H:%M:%S')
BACKUP_DIR="$HOME/backups/$TIMESTAMP"
LOGFILE="$HOME/backups/backup.log"
DATA_DIR="$HOME/empire-repo/backend/data"
REPO_DIR="$HOME/empire-repo"

# Database files to back up
DB_FILES=(
    "empire.db"
    "empirebox.db"
    "intake.db"
    "token_usage.db"
    "amp.db"
)

echo "========================================" >> "$LOGFILE"
echo "[$DATETIME] Empire Daily Backup started" >> "$LOGFILE"

# Create today's backup directory
mkdir -p "$BACKUP_DIR"

# Copy database files
COPIED=0
for db in "${DB_FILES[@]}"; do
    SRC="$DATA_DIR/$db"
    if [ -f "$SRC" ]; then
        cp "$SRC" "$BACKUP_DIR/"
        SIZE=$(du -h "$SRC" | cut -f1)
        echo "[$DATETIME]   Backed up $db ($SIZE)" >> "$LOGFILE"
        COPIED=$((COPIED + 1))
    else
        echo "[$DATETIME]   Skipped $db (not found)" >> "$LOGFILE"
    fi
done

echo "[$DATETIME]   $COPIED database(s) copied to $BACKUP_DIR" >> "$LOGFILE"

# Git stash uncommitted changes if any
cd "$REPO_DIR"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    STASH_MSG="auto-backup ${TIMESTAMP}_$(date +%H%M)"
    git stash save "$STASH_MSG" >> "$LOGFILE" 2>&1
    echo "[$DATETIME]   Git stash created: $STASH_MSG" >> "$LOGFILE"
else
    echo "[$DATETIME]   No uncommitted changes — git stash skipped" >> "$LOGFILE"
fi

# Remove backups older than 30 days
find "$HOME/backups" -maxdepth 1 -type d -name '20*' -mtime +30 -exec rm -rf {} \; 2>/dev/null
echo "[$DATETIME]   Cleaned backups older than 30 days" >> "$LOGFILE"

# Summary
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
echo "[$DATETIME] Backup complete — $TOTAL_SIZE total in $BACKUP_DIR" >> "$LOGFILE"
echo "========================================" >> "$LOGFILE"
