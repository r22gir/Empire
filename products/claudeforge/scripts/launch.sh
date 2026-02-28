#!/bin/bash
# ClaudeForge v3 — One-Click Launch
# Generates context, copies to clipboard, opens Claude, starts autosave

FORGE_DIR=~/Empire/products/claudeforge
SCRIPTS_DIR=$FORGE_DIR/scripts
DATA_DIR=$FORGE_DIR/data
CHATS_DIR=$DATA_DIR/chats
LAST_FILE=$DATA_DIR/last_session.txt
LOCK_FILE=/tmp/claudeforge.lock

GREEN='\033[0;32m'
GOLD='\033[1;33m'
PURPLE='\033[0;35m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

# ── If already running, trigger end_session instead ──────────────────
if [ -f "$LOCK_FILE" ]; then
    RUNNING_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if kill -0 "$RUNNING_PID" 2>/dev/null; then
        echo -e "${GOLD}ClaudeForge is running — ending session...${NC}"
        "$SCRIPTS_DIR/end_session.sh"
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi

# Write lock
echo $$ > "$LOCK_FILE"
trap "rm -f '$LOCK_FILE'" EXIT

# ── Banner ───────────────────────────────────────────────────────────
echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo -e "${GOLD}|     ${PURPLE}ClaudeForge v3${GOLD}                                 |${NC}"
echo -e "${GOLD}|     ${NC}One-Click AI Session Manager${GOLD}                     |${NC}"
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo ""

# Show last session info
if [ -f "$LAST_FILE" ]; then
    LAST_TIME=$(grep "^started:" "$LAST_FILE" | cut -d' ' -f2-)
    LAST_NOTES=$(grep "^notes:" "$LAST_FILE" | cut -d' ' -f2-)
    if [ -n "$LAST_TIME" ]; then
        echo -e "${DIM}Last session: $LAST_TIME${NC}"
        [ -n "$LAST_NOTES" ] && echo -e "${DIM}Notes: $LAST_NOTES${NC}"
        echo ""
    fi
fi

# ── Step 1: Generate context ─────────────────────────────────────────
echo -e "${GREEN}[1/4]${NC} Generating context..."
"$SCRIPTS_DIR/generate_context.sh" 2>/dev/null
CONTEXT_LINES=$(wc -l < "$DATA_DIR/context.md" 2>/dev/null || echo 0)
echo -e "      ${DIM}Context: $CONTEXT_LINES lines${NC}"

# ── Step 2: Copy to clipboard ────────────────────────────────────────
echo -e "${GREEN}[2/4]${NC} Copying to clipboard..."
if command -v xclip &>/dev/null; then
    xclip -selection clipboard < "$DATA_DIR/context.md" 2>/dev/null
    echo -e "      ${DIM}Ready to paste (Ctrl+V)${NC}"
else
    echo -e "      ${RED}xclip not installed — copy manually from $DATA_DIR/context.md${NC}"
fi

# ── Step 3: Open Claude ──────────────────────────────────────────────
echo -e "${GREEN}[3/4]${NC} Opening Claude..."
xdg-open "https://claude.ai/new" 2>/dev/null &
disown

# ── Step 4: Start autosave ───────────────────────────────────────────
SESSION_ID=$(date +%Y-%m-%d)_session$$
SESSION_DIR="$CHATS_DIR/$SESSION_ID"
mkdir -p "$SESSION_DIR"

"$SCRIPTS_DIR/autosave.sh" "$SESSION_DIR" &
AUTOSAVE_PID=$!
disown $AUTOSAVE_PID
echo -e "${GREEN}[4/4]${NC} Autosave started (PID $AUTOSAVE_PID, every 5 min)"

# ── Write session file ───────────────────────────────────────────────
cat > "$LAST_FILE" << SESS
started: $(date '+%Y-%m-%d %H:%M:%S')
session_id: $SESSION_ID
session_dir: $SESSION_DIR
autosave_pid: $AUTOSAVE_PID
status: active
SESS

echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"
echo ""
echo "   Session ${PURPLE}$SESSION_ID${NC} started"
echo ""
echo "   Paste context into Claude (Ctrl+V)"
echo "   Autosave snapshots every 5 minutes"
echo ""
echo "   To end: click ClaudeForge again"
echo "           or run end_session.sh"
echo "           or press Enter here"
echo ""
echo -e "${GOLD}+-------------------------------------------------------+${NC}"

# ── Wait for user to end ─────────────────────────────────────────────
read -p ""
"$SCRIPTS_DIR/end_session.sh"
