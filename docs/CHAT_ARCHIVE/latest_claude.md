# Claude Chat Save - 16-55
Saved: Thu Feb 26 04:55:28 PM EST 2026

rg@EmpireBox:~$ # Check the desktop shortcut
cat ~/Desktop/ClaudeForge.desktop

# List the ClaudeForge directory
ls -la ~/Empire/products/claudeforge/
[Desktop Entry]
Version=1.0
Type=Application
Name=🧠 ClaudeForge
Comment=AI Session Manager - opens Claude with Empire context
Exec=gnome-terminal -- bash -c "$HOME/Empire/products/claudeforge/scripts/launch.sh; exec bash"
Icon=utilities-terminal
Terminal=false
Categories=Development;
total 20
drwxrwxr-x 5 rg rg 4096 Feb 25 20:48 .
drwxrwxr-x 4 rg rg 4096 Feb 25 20:48 ..
drwxrwxr-x 2 rg rg 4096 Feb 25 20:48 assets
drwxrwxr-x 3 rg rg 4096 Feb 25 20:50 data
drwxrwxr-x 2 rg rg 4096 Feb 25 22:17 scripts
rg@EmpireBox:~$ # List and show all scripts
ls -la ~/Empire/products/claudeforge/scripts/
cat ~/Empire/products/claudeforge/scripts/*.sh
total 24
drwxrwxr-x 2 rg rg 4096 Feb 25 22:17 .
drwxrwxr-x 5 rg rg 4096 Feb 25 20:48 ..
-rwxr-xr-x 1 rg rg 1038 Feb 25 22:17 autosave.sh
-rwxr-xr-x 1 rg rg  311 Feb 25 20:48 end_session.sh
-rwxr-xr-x 1 rg rg 1661 Feb 25 22:09 generate_context.sh
-rwxr-xr-x 1 rg rg 2244 Feb 25 20:48 launch.sh
#!/bin/bash
# ClaudeForge - Auto-Save Service
SAVE_DIR=~/Empire/products/claudeforge/data/chats
SESSION_ID=$(date +%Y-%m-%d)_session$$
SESSION_DIR="$SAVE_DIR/$SESSION_ID"
INTERVAL=60
mkdir -p "$SESSION_DIR"

log() { echo "[$(date '+%H:%M:%S')] $1"; }

save_chat() {
  TIMESTAMP=$(date +%H-%M)
  SAVE_FILE="$SESSION_DIR/$TIMESTAMP.md"
  CLIPBOARD=$(xclip -selection clipboard -o 2>/dev/null)
  if [ -n "$CLIPBOARD" ]; then
    echo "# Claude Chat Save - $TIMESTAMP" > "$SAVE_FILE"
    echo "Saved: $(date)" >> "$SAVE_FILE"
    echo "" >> "$SAVE_FILE"
    echo "$CLIPBOARD" >> "$SAVE_FILE"
    cp "$SAVE_FILE" "$SESSION_DIR/current.md"
    cp "$SAVE_FILE" ~/Empire/docs/CHAT_ARCHIVE/latest_claude.md
    log "Saved: $SAVE_FILE"
  else
    log "Clipboard empty, skipping"
  fi
}

log "ClaudeForge Auto-Save Started"
log "Session: $SESSION_ID"

while true; do
  sleep $INTERVAL
  notify-send -u normal -t 10000 "ClaudeForge" "Time to save! Select all in Claude (Ctrl+A), copy (Ctrl+C), then come back." 2>/dev/null
  sleep 5
  save_chat
done
#!/bin/bash
# Kill autosave
LAST=~/Empire/products/claudeforge/data/last_session.txt
if [ -f "$LAST" ]; then
  PID=$(grep "autosave_pid:" "$LAST" | awk '{print $2}')
  kill $PID 2>/dev/null
  echo "Auto-save stopped (PID: $PID)"
fi
echo "Session ended. Chats saved in ~/Empire/products/claudeforge/data/chats/"
#!/bin/bash
# ClaudeForge - Context Generator v2
OUTPUT=~/Empire/products/claudeforge/data/context.md
ARCHIVE=~/Empire/docs/CHAT_ARCHIVE
BRAIN=~/Empire/max/memory.md

# Start with brain
cat "$BRAIN" > "$OUTPUT"

# Add system status
echo "" >> "$OUTPUT"
echo "## LIVE SYSTEM STATUS (auto-generated)" >> "$OUTPUT"
echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> "$OUTPUT"
echo "### Memory" >> "$OUTPUT"
free -h | head -2 >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "### Running Servers" >> "$OUTPUT"
ss -tlnp 2>/dev/null | grep -E "300[0-9]|8000|8080" | awk '{print $4}' >> "$OUTPUT" 2>/dev/null
echo "" >> "$OUTPUT"
echo "### Disk" >> "$OUTPUT"
df -h / | tail -1 >> "$OUTPUT"

# Add LATEST session summary from archive
echo "" >> "$OUTPUT"
echo "## LAST SESSION SUMMARY" >> "$OUTPUT"
LATEST=$(ls -t "$ARCHIVE"/*.md 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
  echo "Source: $LATEST" >> "$OUTPUT"
  echo "" >> "$OUTPUT"
  cat "$LATEST" >> "$OUTPUT"
else
  echo "No session archives found." >> "$OUTPUT"
fi

# Add second latest for extra context
SECOND=$(ls -t "$ARCHIVE"/*.md 2>/dev/null | sed -n '2p')
if [ -n "$SECOND" ]; then
  echo "" >> "$OUTPUT"
  echo "## PREVIOUS SESSION" >> "$OUTPUT"
  echo "Source: $SECOND" >> "$OUTPUT"
  echo "" >> "$OUTPUT"
  head -30 "$SECOND" >> "$OUTPUT"
  echo "..." >> "$OUTPUT"
fi

echo "" >> "$OUTPUT"
echo "## INSTRUCTIONS" >> "$OUTPUT"
echo "You are MAX, the AI for EmpireBox. Read everything above." >> "$OUTPUT"
echo "Say: Empire Ready. Then state the last task from the session summary." >> "$OUTPUT"
echo "Ask what we are building today." >> "$OUTPUT"

echo "Context generated: $OUTPUT ($(wc -l < "$OUTPUT") lines)"
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
$SCRIPTS_DIR/autosave.sh &
AUTOSAVE_PID=$!

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
rg@EmpireBox:~$ 
