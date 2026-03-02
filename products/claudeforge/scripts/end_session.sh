#!/bin/bash
# ClaudeForge v3 — One-Click End Session
# Saves final snapshot, generates session summary, updates context

FORGE_DIR=~/Empire/products/claudeforge
DATA_DIR=$FORGE_DIR/data
LAST_FILE=$DATA_DIR/last_session.txt
LOCK_FILE=/tmp/claudeforge.lock

GREEN='\033[0;32m'
GOLD='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

echo ""
echo -e "${GOLD}ClaudeForge — Ending Session${NC}"
echo -e "${GOLD}═══════════════════════════════════════${NC}"

# ── Kill autosave ────────────────────────────────────────────────────
if [ -f "$LAST_FILE" ]; then
    AUTOSAVE_PID=$(grep "^autosave_pid:" "$LAST_FILE" | awk '{print $2}')
    SESSION_DIR=$(grep "^session_dir:" "$LAST_FILE" | cut -d' ' -f2-)
    SESSION_ID=$(grep "^session_id:" "$LAST_FILE" | cut -d' ' -f2-)
    START_TIME=$(grep "^started:" "$LAST_FILE" | cut -d' ' -f2-)

    if [ -n "$AUTOSAVE_PID" ]; then
        kill "$AUTOSAVE_PID" 2>/dev/null
        echo -e "${GREEN}[1/5]${NC} Autosave stopped"
    fi
else
    echo -e "${RED}No active session found${NC}"
    exit 1
fi

# ── Final clipboard save ─────────────────────────────────────────────
echo -e "${GREEN}[2/5]${NC} Saving final clipboard snapshot..."
if [ -d "$SESSION_DIR" ] && command -v xclip &>/dev/null; then
    CLIP=$(xclip -selection clipboard -o 2>/dev/null)
    if [ -n "$CLIP" ] && [ ${#CLIP} -gt 50 ]; then
        FINAL_FILE="$SESSION_DIR/final.md"
        {
            echo "# ClaudeForge Session — Final Save"
            echo "Session: $SESSION_ID"
            echo "Ended: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
            echo "$CLIP"
        } > "$FINAL_FILE"
        cp "$FINAL_FILE" "$SESSION_DIR/current.md"
        echo -e "      ${DIM}Saved $(echo "$CLIP" | wc -l) lines${NC}"
    else
        echo -e "      ${DIM}Clipboard empty or too short, skipped${NC}"
    fi
fi

# ── Git status snapshot ──────────────────────────────────────────────
echo -e "${GREEN}[3/5]${NC} Saving git status..."
GIT_FILE="$SESSION_DIR/git_snapshot.md"
{
    echo "# Git Snapshot — $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "## Branch"
    cd ~/Empire && git branch --show-current 2>/dev/null
    echo ""
    echo "## Recent Commits (last 10)"
    git log --oneline -10 2>/dev/null
    echo ""
    echo "## Working Tree Status"
    git status --short 2>/dev/null || echo "clean"
} > "$GIT_FILE"

# ── System health snapshot ───────────────────────────────────────────
echo -e "${GREEN}[4/5]${NC} Saving system health..."
HEALTH_FILE="$SESSION_DIR/system_health.md"
{
    echo "# System Health — $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "## Memory"
    free -h | head -2
    echo ""
    echo "## Disk"
    df -h / | tail -1
    echo ""
    echo "## Running Services"
    ss -tlnp 2>/dev/null | grep -E ":[0-9]{4} " | awk '{print $4}' | sort -u
    echo ""
    echo "## CPU Load"
    uptime
    echo ""
    echo "## Temperatures"
    sensors 2>/dev/null | grep -E "Tctl|temp1" | head -3 || echo "sensors unavailable"
} > "$HEALTH_FILE"

# ── Generate session summary ─────────────────────────────────────────
echo -e "${GREEN}[5/5]${NC} Generating session summary..."
SUMMARY_FILE="$SESSION_DIR/session_summary.md"
{
    echo "# ClaudeForge Session Summary"
    echo ""
    echo "| Field | Value |"
    echo "|-------|-------|"
    echo "| Session ID | $SESSION_ID |"
    echo "| Started | $START_TIME |"
    echo "| Ended | $(date '+%Y-%m-%d %H:%M:%S') |"
    echo "| Chat saves | $(ls "$SESSION_DIR"/*.md 2>/dev/null | wc -l) files |"
    echo ""
    echo "## Git Activity During Session"
    cd ~/Empire
    # Show commits made since session start
    if [ -n "$START_TIME" ]; then
        COMMITS=$(git log --oneline --since="$START_TIME" 2>/dev/null)
        if [ -n "$COMMITS" ]; then
            echo '```'
            echo "$COMMITS"
            echo '```'
        else
            echo "No commits during this session."
        fi
    fi
    echo ""
    echo "## Files Changed"
    git diff --stat HEAD~5 HEAD 2>/dev/null | tail -5
} > "$SUMMARY_FILE"

# Also copy summary to the archive
mkdir -p ~/Empire/docs/CHAT_ARCHIVE
cp "$SUMMARY_FILE" ~/Empire/docs/CHAT_ARCHIVE/latest_claude.md

# ── Update last_session ──────────────────────────────────────────────
cat >> "$LAST_FILE" << SESS
ended: $(date '+%Y-%m-%d %H:%M:%S')
status: ended
saves: $(ls "$SESSION_DIR"/*.md 2>/dev/null | wc -l)
SESS

# ── Clean up lock ────────────────────────────────────────────────────
rm -f "$LOCK_FILE"

echo ""
echo -e "${GOLD}═══════════════════════════════════════${NC}"
echo -e "   Session saved to: ${DIM}$SESSION_DIR${NC}"
echo -e "   Files: $(ls "$SESSION_DIR"/*.md 2>/dev/null | wc -l) saves"
echo -e "${GOLD}═══════════════════════════════════════${NC}"
echo ""
