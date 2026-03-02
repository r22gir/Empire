#!/bin/bash
# ClaudeForge v3 — Autosave Service
# Runs in background, saves clipboard every 5 minutes silently
# Only saves when clipboard content has changed and is substantial

SESSION_DIR="$1"
INTERVAL=300  # 5 minutes

if [ -z "$SESSION_DIR" ] || [ ! -d "$SESSION_DIR" ]; then
    echo "Usage: autosave.sh <session_dir>"
    exit 1
fi

LAST_HASH=""

log() { echo "[$(date '+%H:%M:%S')] autosave: $1"; }

save_clip() {
    if ! command -v xclip &>/dev/null; then
        return
    fi

    CLIP=$(xclip -selection clipboard -o 2>/dev/null)

    # Skip if empty or too short (less than 50 chars = not a chat)
    if [ -z "$CLIP" ] || [ ${#CLIP} -lt 50 ]; then
        return
    fi

    # Skip if content hasn't changed
    HASH=$(echo "$CLIP" | md5sum | awk '{print $1}')
    if [ "$HASH" = "$LAST_HASH" ]; then
        return
    fi
    LAST_HASH="$HASH"

    TIMESTAMP=$(date +%H-%M)
    SAVE_FILE="$SESSION_DIR/${TIMESTAMP}.md"
    {
        echo "# ClaudeForge Auto-Save"
        echo "Saved: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        echo "$CLIP"
    } > "$SAVE_FILE"

    # Keep a "current" pointer
    cp "$SAVE_FILE" "$SESSION_DIR/current.md"

    log "Saved ${#CLIP} chars → $SAVE_FILE"
}

log "Started (interval: ${INTERVAL}s)"

while true; do
    sleep $INTERVAL
    save_clip
done
