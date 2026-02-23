#!/bin/bash
#══════════════════════════════════════════════════════════════
# EMPIRE VERSION RESTORE
# Run: ./scripts/restore-version.sh
#══════════════════════════════════════════════════════════════

cd ~/Empire

echo "🏰 EMPIRE VERSION RESTORE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Available versions:"
echo ""

# List versions
ls -1d versions/v* 2>/dev/null | while read dir; do
    version=$(basename "$dir")
    manifest="$dir/MANIFEST.txt"
    if [ -f "$manifest" ]; then
        desc=$(grep "Description:" "$manifest" | cut -d: -f2-)
        echo "  📦 $version -$desc"
    else
        echo "  📦 $version"
    fi
done

echo ""
echo -n "Enter version to restore (e.g., v1.0.0_20260223_120000): "
read VERSION_TO_RESTORE

if [ -d "versions/$VERSION_TO_RESTORE" ]; then
    echo ""
    echo "⚠️  This will overwrite current files. Continue? (y/n)"
    read CONFIRM
    if [ "$CONFIRM" = "y" ]; then
        # Backup current first
        BACKUP_DIR="versions/pre_restore_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp -r backend empire-control workroomforge founder_dashboard VERSION CHANGELOG.md "$BACKUP_DIR/" 2>/dev/null
        
        # Restore
        cp -r "versions/$VERSION_TO_RESTORE/"* ./
        echo "✅ Restored to $VERSION_TO_RESTORE"
        echo "📁 Pre-restore backup: $BACKUP_DIR"
    fi
else
    echo "❌ Version not found"
fi
