#!/bin/bash
TIMESTAMP=$(date +%Y%m%d-%H%M)
DEST="/media/rg/BACKUP1/Empire/backups"
echo "🔄 Backing up Empire to external drive..."
tar czf "$DEST/empire-backup-$TIMESTAMP.tar.gz" \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='__pycache__' \
  -C ~/ Empire/
echo "✅ Backup saved: $DEST/empire-backup-$TIMESTAMP.tar.gz"
# Keep only last 5 backups
ls -t "$DEST"/empire-backup-*.tar.gz | tail -n +6 | xargs rm -f 2>/dev/null
echo "🧹 Old backups cleaned (keeping last 5)"
