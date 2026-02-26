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
