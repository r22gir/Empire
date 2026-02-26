#!/bin/bash
# Kill autosave
LAST=~/Empire/products/claudeforge/data/last_session.txt
if [ -f "$LAST" ]; then
  PID=$(grep "autosave_pid:" "$LAST" | awk '{print $2}')
  kill $PID 2>/dev/null
  echo "Auto-save stopped (PID: $PID)"
fi
echo "Session ended. Chats saved in ~/Empire/products/claudeforge/data/chats/"
