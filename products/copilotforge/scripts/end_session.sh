#!/bin/bash
# CoPilotForge - End Session

FORGE_DIR=~/Empire/products/copilotforge
DATA_DIR=$FORGE_DIR/data

echo ""
echo "🔷 CoPilotForge - End Session"
echo "═══════════════════════════════════════"
echo ""

# Kill autosave
if [ -f "$DATA_DIR/last_session.txt" ]; then
  PID=$(grep "autosave_pid:" "$DATA_DIR/last_session.txt" | cut -d' ' -f2)
  if [ -n "$PID" ]; then
    kill $PID 2>/dev/null
    echo "✅ Auto-save stopped"
  fi
fi

# Final save prompt
echo ""
echo "📋 Final save - Please:"
echo "   1. Go to browser"
echo "   2. Ctrl+A (select all chat)"
echo "   3. Ctrl+C (copy)"
echo ""
read -p "Press Enter when copied (or 's' to skip): " SKIP

if [ "$SKIP" != "s" ]; then
  # Find current session dir
  SESSION_DIR=$(ls -td "$DATA_DIR/chats"/*/ 2>/dev/null | head -1)
  
  if [ -d "$SESSION_DIR" ]; then
    FINAL_FILE="$SESSION_DIR/final.md"
    
    echo "# Final Chat Save" > "$FINAL_FILE"
    echo "Session ended: $(date)" >> "$FINAL_FILE"
    echo "" >> "$FINAL_FILE"
    xclip -selection clipboard -o >> "$FINAL_FILE"
    
    echo "✅ Final save: $FINAL_FILE"
  fi
fi

# Session notes
echo ""
read -p "📝 Quick session notes (optional): " NOTES

if [ -n "$NOTES" ]; then
  echo "" >> "$DATA_DIR/sessions.log"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] SESSION END" >> "$DATA_DIR/sessions.log"
  echo "Notes: $NOTES" >> "$DATA_DIR/sessions.log"
  echo "✅ Notes saved"
fi

# Update last session
echo "status: ended" >> "$DATA_DIR/last_session.txt"
echo "ended: $(date '+%Y-%m-%d %H:%M:%S')" >> "$DATA_DIR/last_session.txt"
echo "notes: $NOTES" >> "$DATA_DIR/last_session.txt"

echo ""
echo "═══════════════════════════════════════"
echo "✅ Session ended. See you next time!"
echo "═══════════════════════════════════════"
