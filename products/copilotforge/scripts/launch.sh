#!/bin/bash
# CoPilotForge - Session Launcher
# Main entry point

FORGE_DIR=~/Empire/products/copilotforge
SCRIPTS_DIR=$FORGE_DIR/scripts
DATA_DIR=$FORGE_DIR/data

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                               ║${NC}"
echo -e "${BLUE}║     🔷 ${GREEN}CoPilotForge${BLUE}                                          ║${NC}"
echo -e "${BLUE}║        ${NC}Empire Tools${BLUE}                                           ║${NC}"
echo -e "${BLUE}║                                                               ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check for recent session
LAST_SESSION_FILE="$DATA_DIR/last_session.txt"
if [ -f "$LAST_SESSION_FILE" ]; then
  LAST_URL=$(grep "url:" "$LAST_SESSION_FILE" | cut -d' ' -f2)
  LAST_TIME=$(grep "time:" "$LAST_SESSION_FILE" | cut -d' ' -f2-)
  
  echo -e "${YELLOW}📂 Recent session found:${NC}"
  echo "   Last active: $LAST_TIME"
  echo ""
  echo "   [1] Continue previous session"
  echo "   [2] Start new session"
  echo ""
  read -p "   Choice (1/2): " CHOICE
  
  if [ "$CHOICE" = "1" ] && [ -n "$LAST_URL" ]; then
    URL="$LAST_URL"
  else
    URL="https://github.com/copilot"
  fi
else
  URL="https://github.com/copilot"
fi

echo ""
echo -e "${GREEN}🔄 Generating context...${NC}"
$SCRIPTS_DIR/generate_context.sh

echo ""
echo -e "${GREEN}📋 Copying context to clipboard...${NC}"
cat "$DATA_DIR/context.md" | xclip -selection clipboard
echo "   ✅ Context copied! Ready to paste (Ctrl+V)"

echo ""
echo -e "${GREEN}🌐 Opening Copilot...${NC}"
firefox "$URL" &

echo ""
echo -e "${GREEN}💾 Starting auto-save service...${NC}"
$SCRIPTS_DIR/autosave.sh &
AUTOSAVE_PID=$!
echo "   Auto-save PID: $AUTOSAVE_PID"

# Save session info
cat > "$LAST_SESSION_FILE" << SESS
url: $URL
time: $(date '+%Y-%m-%d %H:%M:%S')
autosave_pid: $AUTOSAVE_PID
SESS

echo ""
echo -e "${BLUE}══════��════════════════════════════════════════════════════════${NC}"
echo ""
echo "   ✅ Session started!"
echo ""
echo "   📋 Paste context into Copilot (Ctrl+V)"
echo "   💾 Auto-save running every 5 minutes"
echo "   🔔 You'll get notifications to save"
echo ""
echo "   To end session: ./scripts/end_session.sh"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
