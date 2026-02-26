#!/bin/bash
# ClaudeForge - Session Launcher
FORGE_DIR=~/Empire/products/claudeforge
SCRIPTS_DIR=$FORGE_DIR/scripts
DATA_DIR=$FORGE_DIR/data

GREEN='\033[0;32m'
GOLD='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo -e "${GOLD}|                                                       |${NC}"
echo -e "${GOLD}|     ${PURPLE}ClaudeForge${GOLD}                                    |${NC}"
echo -e "${GOLD}|     ${NC}MAX AI Session Manager${GOLD}                          |${NC}"
echo -e "${GOLD}|                                                       |${NC}"
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo ""

# Check for recent session
LAST_SESSION_FILE="$DATA_DIR/last_session.txt"
if [ -f "$LAST_SESSION_FILE" ]; then
  LAST_TIME=$(grep "time:" "$LAST_SESSION_FILE" | cut -d' ' -f2-)
  echo -e "${GOLD}Recent session: $LAST_TIME${NC}"
  echo ""
fi

echo -e "${GREEN}Generating context...${NC}"
$SCRIPTS_DIR/generate_context.sh

echo ""
echo -e "${GREEN}Copying context to clipboard...${NC}"
cat "$DATA_DIR/context.md" | xclip -selection clipboard 2>/dev/null
echo "   Context copied to clipboard!"

echo ""
echo -e "${GREEN}Opening Claude...${NC}"
xdg-open "https://claude.ai/new" &

echo ""
echo -e "${GREEN}Starting auto-save (every 5 min)...${NC}"
# DISABLED: $SCRIPTS_DIR/autosave.sh &
AUTOSAVE_PID=""

cat > "$LAST_SESSION_FILE" << SESS
url: https://claude.ai
time: $(date '+%Y-%m-%d %H:%M:%S')
autosave_pid: $AUTOSAVE_PID
SESS

echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo ""
echo "   Session started!"
echo ""
echo "   1. Claude is opening in browser"
echo "   2. Click + to attach file"
echo "   3. Upload: ~/Empire/max/memory.md"
echo "   4. Type: Load this brain and say Empire Ready"
echo ""
echo "   OR just paste (Ctrl+V) - context is on clipboard"
echo ""
echo "   Auto-save running every 5 minutes"
echo "   To end: $SCRIPTS_DIR/end_session.sh"
echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"

# Keep terminal open
read -p "Press Enter to end session..."
kill $AUTOSAVE_PID 2>/dev/null
echo "Session ended. Auto-save stopped."
