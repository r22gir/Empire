#!/bin/bash
#══════════════════════════════════════════════════════════════
# EMPIRE VERSION SAVE PROTOCOL
# Run: ./scripts/save-version.sh [version] [description]
# Example: ./scripts/save-version.sh 1.1.0 "Added inventory module"
#══════════════════════════════════════════════════════════════

set -e
cd ~/Empire

# Colors
GOLD='\033[0;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GOLD}"
echo "═══════════════════════════════════════════════════════════"
echo "🏰 EMPIRE VERSION SAVE PROTOCOL"
echo "═══════════════════════════════════════════════════════════"
echo -e "${NC}"

# Get current version
CURRENT_VERSION=$(cat VERSION 2>/dev/null || echo "0.0.0")
echo -e "Current version: ${BLUE}v${CURRENT_VERSION}${NC}"

# Get new version
if [ -n "$1" ]; then
    NEW_VERSION="$1"
else
    echo -n "Enter new version (or press Enter for patch bump): "
    read NEW_VERSION
    if [ -z "$NEW_VERSION" ]; then
        # Auto-bump patch version
        IFS='.' read -ra VER <<< "$CURRENT_VERSION"
        PATCH=$((${VER[2]} + 1))
        NEW_VERSION="${VER[0]}.${VER[1]}.$PATCH"
    fi
fi

# Get description
if [ -n "$2" ]; then
    DESCRIPTION="$2"
else
    echo -n "Enter version description: "
    read DESCRIPTION
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERSION_DIR="versions/v${NEW_VERSION}_${TIMESTAMP}"

echo ""
echo -e "${BLUE}Creating version: v${NEW_VERSION}${NC}"
echo -e "Description: ${DESCRIPTION}"
echo ""

# Create version directory
mkdir -p "$VERSION_DIR"

# Copy source files (excluding node_modules, .next, etc.)
echo "📦 Backing up source files..."
rsync -av --progress \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'versions' \
    --exclude '.git' \
    --exclude '*.log' \
    --exclude '*.zip' \
    --exclude '*.json.bak' \
    ./ "$VERSION_DIR/" 2>/dev/null || cp -r \
    backend \
    empire-control \
    workroomforge \
    founder_dashboard \
    scripts \
    VERSION \
    CHANGELOG.md \
    .env \
    "$VERSION_DIR/" 2>/dev/null

# Update VERSION file
echo "$NEW_VERSION" > VERSION
cp VERSION "$VERSION_DIR/"

# Create version manifest
cat > "$VERSION_DIR/MANIFEST.txt" << MANIFEST
═══════════════════════════════════════════════════════════
EMPIRE VERSION MANIFEST
═══════════════════════════════════════════════════════════

Version:     v${NEW_VERSION}
Created:     $(date '+%Y-%m-%d %H:%M:%S')
Description: ${DESCRIPTION}

Previous Version: v${CURRENT_VERSION}

Files Included:
$(find "$VERSION_DIR" -type f | wc -l) files

Apps:
- Empire Control Center (port 3000)
- WorkroomForge (port 3001)
- MAX Interface (port 3009)
- Backend API (port 8000)

════════════════════════════════════════════════��══════════
MANIFEST

# Git operations
echo ""
echo "📤 Pushing to GitHub..."
git add -A 2>/dev/null || true
git commit -m "🏰 Empire v${NEW_VERSION}: ${DESCRIPTION}" 2>/dev/null || true
git tag -a "v${NEW_VERSION}" -m "${DESCRIPTION}" 2>/dev/null || true
git push origin main --tags 2>/dev/null || echo "⚠️  Git push skipped (not configured or offline)"

# Log the version save
mkdir -p logs
echo "[$(date '+%Y-%m-%d %H:%M:%S')] v${NEW_VERSION} - ${DESCRIPTION}" >> logs/version_history.log

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ VERSION v${NEW_VERSION} SAVED SUCCESSFULLY${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "📁 Local backup: ~/Empire/${VERSION_DIR}"
echo "🏷️  Git tag: v${NEW_VERSION}"
echo ""
echo "To restore this version:"
echo "  cp -r ${VERSION_DIR}/* ~/Empire/"
echo ""
