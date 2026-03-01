#!/bin/bash
# Backup Sync — Auto-detect backup drive and sync Empire

DEST=""
for d in /media/rg/BACKUP12 /media/rg/BACKUP1 /media/rg/BACKUP11; do
    if [ -d "$d" ]; then
        DEST="$d/EMPIRE"
        break
    fi
done

if [ -z "$DEST" ]; then
    echo "No backup drive found! Mount a drive first."
    sleep 5
    exit 1
fi

echo "Syncing ~/Empire/ to $DEST ..."
rsync -av --delete --exclude='node_modules' --exclude='.next' --exclude='venv' --exclude='__pycache__' --exclude='.git' ~/Empire/ "$DEST/"
notify-send 'Backup Complete' "Empire synced to $DEST"
echo ""
echo "Backup complete!"
sleep 3
