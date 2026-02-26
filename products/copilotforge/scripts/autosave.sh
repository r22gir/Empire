#!/bin/bash
# CoPilotForge - Auto-Save Service
# Runs in background, prompts to save every 5 minutes

SAVE_DIR=~/Empire/products/copilotforge/data/chats
SESSION_ID=$(date +%Y-%m-%d)_session$$
SESSION_DIR="$SAVE_DIR/$SESSION_ID"
INTERVAL=300  # 5 minutes in seconds
HOUR_CLEANUP=3600  # 1 hour in seconds

mkdir -p "$SESSION_DIR"

log() {
  echo "[$(date '+%H:%M:%S')] $1"
}

save_chat() {
  TIMESTAMP=$(date +%H-%M)
  SAVE_FILE="$SESSION_DIR/$TIMESTAMP.md"
  
  # Check if clipboard has content
  CLIPBOARD=$(xclip -selection clipboard -o 2>/dev/null)
  
  if [ -n "$CLIPBOARD" ]; then
    echo "# Chat Save - $TIMESTAMP" > "$SAVE_FILE"
    echo "Saved: $(date)" >> "$SAVE_FILE"
    echo "" >> "$SAVE_FILE"
    echo "$CLIPBOARD" >> "$SAVE_FILE"
    
    # Also save as current.md (always latest)
    cp "$SAVE_FILE" "$SESSION_DIR/current.md"
    
    log "💾 Saved: $SAVE_FILE"
    return 0
  else
    log "⚠️ Clipboard empty, skipping save"
    return 1
  fi
}

cleanup_hourly() {
  CURRENT_HOUR=$(date +%H)
  
  # Keep only the last file from previous hour
  PREV_HOUR=$(printf "%02d" $((10#$CURRENT_HOUR - 1)))
  
  # Find files from previous hour
  PREV_FILES=$(ls "$SESSION_DIR" 2>/dev/null | grep "^$PREV_HOUR-")
  
  if [ -n "$PREV_FILES" ]; then
    # Get the last one
    LAST_FILE=$(echo "$PREV_FILES" | tail -1)
    
    # Rename to hour snapshot
    mv "$SESSION_DIR/$LAST_FILE" "$SESSION_DIR/hour_$PREV_HOUR.md" 2>/dev/null
    
    # Delete others from that hour
    for f in $PREV_FILES; do
      [ "$f" != "$LAST_FILE" ] && rm -f "$SESSION_DIR/$f" 2>/dev/null
    done
    
    log "🧹 Cleanup: Kept hour_$PREV_HOUR.md, removed old saves"
  fi
}

notify_save() {
  notify-send -u normal -t 10000 \
    "🔷 CoPilotForge" \
    "Time to save!\n\n1. Go to browser\n2. Ctrl+A (select all)\n3. Ctrl+C (copy)\n4. Come back here" \
    --action="Save Now" 2>/dev/null
}

log "🚀 CoPilotForge Auto-Save Started"
log "📁 Session: $SESSION_ID"
log "⏰ Interval: $((INTERVAL/60)) minutes"

LAST_CLEANUP=$(date +%s)

while true; do
  sleep $INTERVAL
  
  # Notify user
  notify_save
  
  # Wait a moment for user to copy
  sleep 5
  
  # Try to save
  save_chat
  
  # Check if hour passed for cleanup
  NOW=$(date +%s)
  if [ $((NOW - LAST_CLEANUP)) -ge $HOUR_CLEANUP ]; then
    cleanup_hourly
    LAST_CLEANUP=$NOW
  fi
done
